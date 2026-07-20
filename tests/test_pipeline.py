import json
from unittest.mock import AsyncMock

import pytest

from researcher_recruiting.exporters import write_artifacts
from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactStatus,
    Evidence,
    IdentityState,
    PaperRecord,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.pipeline import ResearchPipeline
from researcher_recruiting.sources.arxiv import parse_atom_feed


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


class StaticPublicWebSource:
    def __init__(self, result: SourceResult) -> None:
        self.result = result

    async def enrich_urls(self, urls: tuple[str, ...]) -> SourceResult:
        return self.result


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
async def test_pipeline_scopes_source_attempts_and_contacts_to_each_author(
    fake_paper, evidence_factory
):
    github = StaticSource(
        "github",
        SourceResult(
            "github",
            SourceStatus.OK,
            evidence=(
                evidence_factory(
                    field="name",
                    value="Ada Lovelace",
                    source="github",
                ),
                evidence_factory(
                    field="paper_title",
                    value=fake_paper.title,
                    source="github",
                ),
                evidence_factory(
                    field="orcid",
                    value="0000-0001-2345-6789",
                    source="github",
                ),
                evidence_factory(
                    field="email",
                    value="ada@university.example",
                    source="github",
                ),
            ),
        ),
    )
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(github,)),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    result = await pipeline.run("1706.03762")
    assert [match.author.name for match in result.matches] == [
        author.name for author in fake_paper.authors
    ]
    results_per_author, remainder = divmod(
        len(result.source_results),
        len(fake_paper.authors),
    )
    assert results_per_author > 0
    assert remainder == 0
    source_author_names = tuple(
        source.author_name for source in result.source_results
    )
    actual_author_blocks = tuple(
        source_author_names[start : start + results_per_author]
        for start in range(
            0,
            len(source_author_names),
            results_per_author,
        )
    )
    expected_author_blocks = tuple(
        (author.name,) * results_per_author
        for author in fake_paper.authors
    )
    assert actual_author_blocks == expected_author_blocks
    ada = result.matches[0]
    assert ada.contact_status is ContactStatus.FOUND
    assert any(
        point.kind is ContactKind.PROFESSIONAL_EMAIL
        for point in ada.contact_points
    )


@pytest.mark.asyncio
async def test_pipeline_marks_author_contacts_unavailable_without_dropping_authors(
    fake_paper, unavailable_source
):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(unavailable_source,)),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )

    result = await pipeline.run("1706.03762")

    assert [match.author.name for match in result.matches] == [
        author.name for author in fake_paper.authors
    ]
    assert all(
        match.contact_status is ContactStatus.SOURCES_UNAVAILABLE
        for match in result.matches
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
async def test_pipeline_reassociates_verified_homepage_email_to_candidate(
    fake_paper, evidence_factory
):
    homepage_url = "https://university.example/~ada/"
    orcid = StaticSource(
        "orcid",
        SourceResult(
            "orcid",
            SourceStatus.OK,
            evidence=(
                evidence_factory(
                    field="orcid",
                    value="0000-0001-2345-6789",
                    source="orcid",
                    candidate_id="orcid:0000-0001-2345-6789",
                ),
                evidence_factory(
                    field="homepage",
                    value=homepage_url,
                    source="orcid",
                    candidate_id="orcid:0000-0001-2345-6789",
                ),
            ),
        ),
    )
    public_web = StaticPublicWebSource(
        SourceResult(
            "public_web",
            SourceStatus.OK,
            evidence=(
                evidence_factory(
                    field="email",
                    value="ada@university.example",
                    source="public_web",
                    url=homepage_url,
                    candidate_id=f"public_web:{homepage_url}",
                ),
            ),
        )
    )
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(orcid,)),
        work_enrichers=(),
        public_web_source=public_web,
    )

    result = await pipeline.run("1706.03762")

    ada = result.matches[0]
    email = next(
        point
        for point in ada.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )
    assert email.value == "ada@university.example"
    assert email.direct is True
    assert email.evidence[0].candidate_id == "orcid:0000-0001-2345-6789"


@pytest.mark.asyncio
async def test_pipeline_starts_author_with_explicit_paper_email_evidence(
    tmp_path,
):
    paper = parse_atom_feed(
        """\
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1706.03762v7</id>
            <title>Attention Is All You Need</title>
            <author>
              <name>Ada Lovelace</name>
              <email>Ada@University.Example</email>
            </author>
          </entry>
        </feed>
        """
    )[0]
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=paper),
        source_registry=RecordingRegistry(selected=()),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )

    result = await pipeline.run("1706.03762")

    paper_result = result.source_results[0]
    assert paper_result.source == "paper"
    assert paper_result.status is SourceStatus.OK
    assert paper_result.author_order == 1
    assert paper_result.author_id == "1706.03762:author:1"
    assert {item.field for item in paper_result.evidence} == {
        "email",
        "name",
        "paper_title",
    }
    email = next(
        item for item in paper_result.evidence if item.field == "email"
    )
    assert email.field == "email"
    assert email.value == "Ada@University.Example"
    assert email.url == paper.source_url
    assert email.candidate_id == paper_result.author_id
    assert email.metadata["visibility"] == "public_professional"
    match = result.matches[0]
    assert match.author_order == 1
    assert match.author_id == paper_result.author_id
    assert match.state in {IdentityState.PROBABLE, IdentityState.CONFIRMED}
    assert match.contact_status is ContactStatus.FOUND
    contact = next(
        point
        for point in match.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )
    assert contact.direct is True
    candidates = json.loads(
        (
            write_artifacts(result, tmp_path) / "candidates.json"
        ).read_text(encoding="utf-8")
    )
    assert candidates[0]["email"] == "ada@university.example"


@pytest.mark.parametrize(
    "untrusted_provenance",
    (None, "arxiv_atom_author_email", object()),
)
@pytest.mark.asyncio
async def test_pipeline_rejects_unproven_programmatic_seed_email(
    fake_paper,
    untrusted_provenance,
):
    author = AuthorSeed(
        name="Ada Lovelace",
        email="ada@university.example",
        paper_title=fake_paper.title,
        email_provenance=untrusted_provenance,
    )
    paper = PaperRecord(
        arxiv_id=fake_paper.arxiv_id,
        title=fake_paper.title,
        abstract=fake_paper.abstract,
        submitted_at=fake_paper.submitted_at,
        categories=fake_paper.categories,
        authors=(author,),
        source_url=fake_paper.source_url,
    )
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=paper),
        source_registry=RecordingRegistry(selected=()),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )

    result = await pipeline.run("1706.03762")

    paper_result = result.source_results[0]
    assert paper_result.source == "paper"
    assert paper_result.status is SourceStatus.NOT_FOUND
    assert paper_result.evidence == ()


@pytest.mark.asyncio
async def test_pipeline_records_paper_not_found_without_guessing_email(
    fake_paper,
):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=()),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )

    result = await pipeline.run("1706.03762")

    paper_results = [
        item for item in result.source_results if item.source == "paper"
    ]
    assert len(paper_results) == len(fake_paper.authors)
    assert all(
        item.status is SourceStatus.NOT_FOUND and not item.evidence
        for item in paper_results
    )
    assert not any(
        evidence.field == "email"
        for item in result.source_results
        for evidence in item.evidence
    )


@pytest.mark.asyncio
async def test_pipeline_assigns_stable_scope_to_every_source_result(
    fake_paper,
):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(RaisingSource(),)),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )

    result = await pipeline.run("1706.03762")

    for order, author in enumerate(fake_paper.authors, start=1):
        author_results = [
            item
            for item in result.source_results
            if item.author_order == order
        ]
        assert author_results
        assert {item.author_name for item in author_results} == {author.name}
        assert {item.author_id for item in author_results} == {
            f"{fake_paper.arxiv_id}:author:{order}"
        }
        match = result.matches[order - 1]
        assert match.author_order == order
        assert match.author_id == f"{fake_paper.arxiv_id}:author:{order}"


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
