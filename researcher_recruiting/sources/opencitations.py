from typing import Any
from urllib.parse import quote

from researcher_recruiting.models import SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

OPENCITATIONS_BASE = (
    "https://opencitations.net/index/coci/api/v1/citations"
)


class OpenCitationsEnricher:
    name = "opencitations"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich_dois(self, dois: tuple[str, ...]) -> SourceResult:
        if not dois:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        items = []
        unavailable = False
        for doi in dict.fromkeys(dois):
            url = f"{OPENCITATIONS_BASE}/{quote(doi)}"
            response = await self.crawler.fetch(url)
            if response.status is not SourceStatus.OK:
                unavailable = True
                continue
            try:
                citations = decode_json(response.body)
                if not isinstance(citations, list):
                    raise ValueError
            except (UnicodeError, ValueError):
                unavailable = True
                continue
            for citation in citations:
                if not isinstance(citation, dict) or not citation.get("citing"):
                    continue
                citing = citation["citing"]
                items.append(
                    evidence(
                        source=self.name,
                        field="citation_doi",
                        value=citing,
                        url=f"https://doi.org/{citing}",
                        candidate_id=f"doi:{doi.casefold()}",
                        metadata={
                            "cited_doi": doi,
                            "creation": citation.get("creation"),
                            "timespan": citation.get("timespan"),
                            "strength": "context_only",
                        },
                    )
                )
        if items:
            return SourceResult(self.name, SourceStatus.OK, tuple(items))
        if unavailable:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="citation_lookup_unavailable",
            )
        return SourceResult(self.name, SourceStatus.NOT_FOUND)
