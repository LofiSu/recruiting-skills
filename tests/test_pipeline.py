from unittest.mock import AsyncMock

import pytest

from researcher_recruiting.models import (
    AuthorSeed,
    Evidence,
    PaperRecord,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.pipeline import ResearchPipeline


class StaticSource:
    def __init__(self, name: str, result: SourceResult) -> None:
        self.name = name
        self.result = result

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        return self.result


class RaisingSource:
    name = "raising"

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        raise RuntimeError("Bearer should-never-leak")


class FakePublicWebSource:
    def __init__(self) -> None:
        self.requested_urls: tuple[str, ...] = ()

    async def enrich_urls(self, urls: tuple[str, ...]) -> SourceResult:
        self.requested_urls = urls
        return SourceResult("public_web", SourceStatus.NOT_FOUND)


class RecordingRegistry:
    def __init__(self, selected):
        self.selected = selected
        self.categories = ()
        self.requested = ()

    def select(self, categories, requested=()):
        self.categories = tuple(categories)
        self.requested = tuple(requested)
        return self.selected


class RecordingWorkEnricher:
    def __init__(self):
        self.dois = ()

    async def enrich_dois(self, dois):
        self.dois = tuple(dois)
        return SourceResult("work_enricher", SourceStatus.NOT_FOUND)


class RefreshAwareCrawler:
    def __init__(self):
        self.force_refresh = False


class RefreshAwareSource:
    name = "refresh_aware"

    def __init__(self):
        self.crawler = RefreshAwareCrawler()
        self.saw_refresh = False

    async def enrich(self, seed):
        self.saw_refresh = self.crawler.force_refresh
        return SourceResult(self.name, SourceStatus.NOT_FOUND)


@pytest.fixture
def fake_paper(author_seed):
    return PaperRecord(
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        abstract="Fixture",
        submitted_at="2017-06-12T00:00:00Z",
        categories=("cs.CL",),
        authors=(
            author_seed,
            AuthorSeed(
                name="Charles Babbage",
                affiliation="Analytical Engines",
                paper_title=author_seed.paper_title,
            ),
        ),
        source_url="https://arxiv.org/abs/1706.03762",
    )


@pytest.fixture
def successful_source(evidence_factory):
    return StaticSource(
        "openalex",
        SourceResult(
            "openalex",
            SourceStatus.OK,
            evidence=(
                evidence_factory(
                    field="name", value="Ada Lovelace"
                ),
            ),
        ),
    )


@pytest.fixture
def homepage_source(evidence_factory):
    return StaticSource(
        "orcid",
        SourceResult(
            "orcid",
            SourceStatus.OK,
            evidence=(
                evidence_factory(
                    field="homepage",
                    value="https://university.example/~ada/",
                    source="orcid",
                ),
            ),
        ),
    )


@pytest.fixture
def unavailable_source():
    return StaticSource(
        "github",
        SourceResult(
            "github",
            SourceStatus.SOURCE_UNAVAILABLE,
            error="rate_limited",
        ),
    )


@pytest.mark.asyncio
async def test_pipeline_keeps_all_authors_when_one_source_fails(
    fake_paper, successful_source, unavailable_source
):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(
            selected=(successful_source, unavailable_source)
        ),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    result = await pipeline.run("1706.03762")
    assert len(result.matches) == len(fake_paper.authors)
    assert any(
        item.status is SourceStatus.SOURCE_UNAVAILABLE
        for item in result.source_results
    )


@pytest.mark.asyncio
async def test_pipeline_crawls_only_homepages_from_credible_evidence(
    fake_paper, homepage_source
):
    public_web = FakePublicWebSource()
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(homepage_source,)),
        work_enrichers=(),
        public_web_source=public_web,
    )
    await pipeline.run("1706.03762")
    assert public_web.requested_urls == (
        "https://university.example/~ada/",
    )


@pytest.mark.asyncio
async def test_pipeline_routes_sources_from_arxiv_categories(fake_paper):
    registry = RecordingRegistry(
        selected=(
            StaticSource(
                "dblp", SourceResult("dblp", SourceStatus.NOT_FOUND)
            ),
        )
    )
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=registry,
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    await pipeline.run("1706.03762", requested_sources=("dblp",))
    assert registry.categories == fake_paper.categories
    assert registry.requested == ("dblp",)


@pytest.mark.asyncio
async def test_pipeline_runs_doi_enrichers_after_author_sources(
    fake_paper,
):
    doi_source = StaticSource(
        "crossref",
        SourceResult(
            "crossref",
            SourceStatus.OK,
            evidence=(
                Evidence(
                    source="crossref",
                    field="doi",
                    value="10.1000/example",
                    url="https://doi.org/10.1000/example",
                    collected_at="2026-07-18T00:00:00Z",
                    candidate_id="crossref:ada",
                ),
                Evidence(
                    source="openalex",
                    field="doi",
                    value="https://doi.org/10.1000/EXAMPLE",
                    url="https://doi.org/10.1000/example",
                    collected_at="2026-07-18T00:00:00Z",
                    candidate_id="openalex:A1",
                ),
            ),
        ),
    )
    enricher = RecordingWorkEnricher()
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(doi_source,)),
        work_enrichers=(enricher,),
        public_web_source=FakePublicWebSource(),
    )
    await pipeline.run("1706.03762")
    assert enricher.dois == ("10.1000/example",)


@pytest.mark.asyncio
async def test_pipeline_bounds_doi_enrichment_per_author(fake_paper):
    doi_source = StaticSource(
        "crossref",
        SourceResult(
            "crossref",
            SourceStatus.OK,
            evidence=tuple(
                Evidence(
                    source="crossref",
                    field="doi",
                    value=f"10.1000/work-{index}",
                    url=f"https://doi.org/10.1000/work-{index}",
                    collected_at="2026-07-18T00:00:00Z",
                    candidate_id="crossref:ada",
                )
                for index in range(30)
            ),
        ),
    )
    enricher = RecordingWorkEnricher()
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(doi_source,)),
        work_enrichers=(enricher,),
        public_web_source=FakePublicWebSource(),
    )
    await pipeline.run("1706.03762")
    assert len(enricher.dois) == 25


@pytest.mark.asyncio
async def test_pipeline_sanitizes_source_exceptions(fake_paper):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(RaisingSource(),)),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    result = await pipeline.run("1706.03762")
    failed = next(
        item for item in result.source_results if item.source == "raising"
    )
    assert failed.status is SourceStatus.SOURCE_UNAVAILABLE
    assert failed.error == "source_exception:RuntimeError"
    assert "Bearer" not in repr(result)


@pytest.mark.asyncio
async def test_pipeline_adds_locator_only_evidence(fake_paper):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=()),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    result = await pipeline.run("1706.03762")
    locators = [
        item
        for source in result.source_results
        if source.source == "locator_links"
        for item in source.evidence
    ]
    assert any(item.field == "google_scholar" for item in locators)
    assert all(item.metadata["mode"] == "locator_only" for item in locators)


@pytest.mark.asyncio
async def test_pipeline_refresh_temporarily_forces_source_crawlers(fake_paper):
    source = RefreshAwareSource()
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(source,)),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    await pipeline.run("1706.03762", refresh=True)
    assert source.saw_refresh is True
    assert source.crawler.force_refresh is False
