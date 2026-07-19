import asyncio
import re
from dataclasses import replace
from typing import Any, Iterable, Protocol

from researcher_recruiting.contacts import attach_contacts
from researcher_recruiting.identity import resolve_identity
from researcher_recruiting.models import (
    PAPER_EMAIL_PROVENANCE,
    AuthorSeed,
    Evidence,
    PaperRecord,
    RunResult,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.search_links import build_locator_links
from researcher_recruiting.sources.base import collected_at

_CREDIBLE_HOMEPAGE_SOURCES = {
    "github",
    "openalex",
    "openreview",
    "orcid",
    "semantic_scholar",
    "wikidata",
}


class PaperResolver(Protocol):
    async def __call__(self, paper_input: str) -> PaperRecord:
        ...


class WorkEnricher(Protocol):
    name: str

    async def enrich_dois(self, dois: tuple[str, ...]) -> SourceResult:
        ...


def _canonical_doi(value: str) -> str:
    return re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
        "",
        value.strip(),
        flags=re.IGNORECASE,
    ).casefold()


def _source_failure(source: str, error: BaseException) -> SourceResult:
    return SourceResult(
        source=source,
        status=SourceStatus.SOURCE_UNAVAILABLE,
        error=f"source_exception:{type(error).__name__}",
    )


class ResearchPipeline:
    def __init__(
        self,
        paper_resolver: PaperResolver,
        source_registry: Any,
        work_enrichers: tuple[WorkEnricher, ...],
        public_web_source: Any,
        *,
        max_author_concurrency: int = 4,
    ) -> None:
        self.paper_resolver = paper_resolver
        self.source_registry = source_registry
        self.work_enrichers = work_enrichers
        self.public_web_source = public_web_source
        self.max_author_concurrency = max_author_concurrency

    async def _enrich_source(
        self,
        source: Any,
        seed: AuthorSeed,
    ) -> SourceResult:
        try:
            return await source.enrich(seed)
        except Exception as error:
            return _source_failure(
                getattr(source, "name", type(source).__name__),
                error,
            )

    async def _enrich_work(
        self,
        enricher: WorkEnricher,
        dois: tuple[str, ...],
    ) -> SourceResult:
        try:
            return await enricher.enrich_dois(dois)
        except Exception as error:
            return _source_failure(
                getattr(enricher, "name", type(enricher).__name__),
                error,
            )

    @staticmethod
    def _locator_result(seed: AuthorSeed) -> SourceResult:
        candidate_id = "locator:" + "-".join(
            re.findall(r"[a-z0-9]+", seed.name.casefold())
        )
        timestamp = collected_at()
        items = tuple(
            Evidence(
                source="locator_links",
                field=field,
                value=url,
                url=url,
                collected_at=timestamp,
                candidate_id=candidate_id,
                metadata={"mode": "locator_only"},
            )
            for field, url in build_locator_links(seed).items()
        )
        return SourceResult(
            "locator_links",
            SourceStatus.OK,
            evidence=items,
        )

    @staticmethod
    def _scope_result(
        result: SourceResult,
        seed: AuthorSeed,
        author_order: int,
        author_id: str,
    ) -> SourceResult:
        return replace(
            result,
            author_name=seed.name,
            author_order=author_order,
            author_id=author_id,
        )

    @staticmethod
    def _paper_result(
        seed: AuthorSeed,
        paper: PaperRecord,
        author_order: int,
        author_id: str,
    ) -> SourceResult:
        evidence_items: tuple[Evidence, ...] = ()
        status = SourceStatus.NOT_FOUND
        if (
            seed.email
            and seed.email.strip()
            and seed.email_provenance == PAPER_EMAIL_PROVENANCE
        ):
            timestamp = collected_at()
            evidence_items = (
                Evidence(
                    source="paper",
                    field="email",
                    value=seed.email,
                    url=paper.source_url,
                    collected_at=timestamp,
                    candidate_id=author_id,
                    metadata={"visibility": "public_professional"},
                ),
                Evidence(
                    source="paper",
                    field="name",
                    value=seed.name,
                    url=paper.source_url,
                    collected_at=timestamp,
                    candidate_id=author_id,
                    metadata={"association": "paper_author"},
                ),
                Evidence(
                    source="paper",
                    field="paper_title",
                    value=paper.title,
                    url=paper.source_url,
                    collected_at=timestamp,
                    candidate_id=author_id,
                    metadata={"association": "paper_author"},
                ),
            )
            status = SourceStatus.OK
        return SourceResult(
            source="paper",
            status=status,
            evidence=evidence_items,
            author_name=seed.name,
            author_order=author_order,
            author_id=author_id,
        )

    @staticmethod
    def _reassociate_public_web_evidence(
        result: SourceResult,
        homepage_owners: dict[str, tuple[str, ...]],
    ) -> SourceResult:
        items = []
        for item in result.evidence:
            owners = ()
            if item.candidate_id:
                owners = homepage_owners.get(item.candidate_id, ())
            if owners:
                items.extend(
                    replace(item, candidate_id=owner)
                    for owner in owners
                )
            else:
                items.append(item)
        return replace(result, evidence=tuple(items))

    async def _run_author(
        self,
        seed: AuthorSeed,
        paper: PaperRecord,
        author_order: int,
        selected_sources: tuple[Any, ...],
        semaphore: asyncio.Semaphore,
    ) -> tuple[Any, tuple[SourceResult, ...]]:
        async with semaphore:
            author_id = f"{paper.arxiv_id}:author:{author_order}"
            paper_result = self._paper_result(
                seed,
                paper,
                author_order,
                author_id,
            )
            author_results = tuple(
                self._scope_result(
                    result,
                    seed,
                    author_order,
                    author_id,
                )
                for result in await asyncio.gather(
                    *(
                        self._enrich_source(source, seed)
                        for source in selected_sources
                    )
                )
            )
            source_results = [paper_result, *author_results]
            evidence_items = [
                item
                for result in source_results
                for item in result.evidence
            ]

            dois = tuple(
                dict.fromkeys(
                    _canonical_doi(item.value)
                    for item in evidence_items
                    if item.field == "doi" and item.value.strip()
                )
            )[:25]
            if self.work_enrichers:
                work_results = tuple(
                    self._scope_result(
                        result,
                        seed,
                        author_order,
                        author_id,
                    )
                    for result in await asyncio.gather(
                        *(
                            self._enrich_work(enricher, dois)
                            for enricher in self.work_enrichers
                        )
                    )
                )
                source_results.extend(work_results)
                evidence_items.extend(
                    item
                    for result in work_results
                    for item in result.evidence
                )

            homepage_urls = tuple(
                dict.fromkeys(
                    item.value
                    for item in evidence_items
                    if item.field == "homepage"
                    and item.source in _CREDIBLE_HOMEPAGE_SOURCES
                )
            )
            homepage_owners: dict[str, tuple[str, ...]] = {}
            for homepage_url in homepage_urls:
                owner_ids = tuple(
                    dict.fromkeys(
                        item.candidate_id
                        for item in evidence_items
                        if item.field == "homepage"
                        and item.value == homepage_url
                        and item.source in _CREDIBLE_HOMEPAGE_SOURCES
                        and item.candidate_id is not None
                    )
                )
                if owner_ids:
                    homepage_owners[f"public_web:{homepage_url}"] = owner_ids
            try:
                public_web_result = (
                    await self.public_web_source.enrich_urls(homepage_urls)
                )
            except Exception as error:
                public_web_result = _source_failure("public_web", error)
            public_web_result = self._reassociate_public_web_evidence(
                public_web_result,
                homepage_owners,
            )
            public_web_result = self._scope_result(
                public_web_result,
                seed,
                author_order,
                author_id,
            )
            source_results.append(public_web_result)
            evidence_items.extend(public_web_result.evidence)

            locator_result = self._scope_result(
                self._locator_result(seed),
                seed,
                author_order,
                author_id,
            )
            source_results.append(locator_result)
            evidence_items.extend(locator_result.evidence)
            unavailable = tuple(
                result.source
                for result in source_results
                if result.status
                in {
                    SourceStatus.SOURCE_UNAVAILABLE,
                    SourceStatus.BLOCKED_BY_ROBOTS,
                }
            )
            identity_evidence = tuple(
                item
                for item in evidence_items
                if item.metadata.get("mode") != "locator_only"
            )
            match = resolve_identity(
                seed,
                identity_evidence,
                unavailable_sources=unavailable,
            )
            match = replace(
                match,
                author_order=author_order,
                author_id=author_id,
            )
            scoped_results = tuple(source_results)
            match = attach_contacts(match, scoped_results)
            return match, scoped_results

    async def run(
        self,
        paper_input: str,
        refresh: bool = False,
        requested_sources: Iterable[str] = (),
    ) -> RunResult:
        paper = await self.paper_resolver(paper_input)
        selected_sources = tuple(
            self.source_registry.select(
                paper.categories,
                requested=tuple(requested_sources),
            )
        )
        refreshables = []
        for owner in (
            *selected_sources,
            *self.work_enrichers,
            self.public_web_source,
        ):
            crawler = getattr(owner, "crawler", None)
            if (
                crawler is not None
                and hasattr(crawler, "force_refresh")
                and all(crawler is not existing for existing, _ in refreshables)
            ):
                refreshables.append((crawler, crawler.force_refresh))
                crawler.force_refresh = refresh or crawler.force_refresh
        try:
            semaphore = asyncio.Semaphore(self.max_author_concurrency)
            author_outputs = await asyncio.gather(
                *(
                    self._run_author(
                        author,
                        paper,
                        author_order,
                        selected_sources,
                        semaphore,
                    )
                    for author_order, author in enumerate(
                        paper.authors,
                        start=1,
                    )
                )
            )
        finally:
            for crawler, previous in refreshables:
                crawler.force_refresh = previous
        return RunResult(
            paper=paper,
            matches=tuple(output[0] for output in author_outputs),
            source_results=tuple(
                result
                for output in author_outputs
                for result in output[1]
            ),
        )
