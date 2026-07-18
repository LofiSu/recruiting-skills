from typing import Any

from researcher_recruiting.models import (
    AuthorSeed,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.sources.base import decode_json, evidence

SEMANTIC_AUTHOR_SEARCH = (
    "https://api.semanticscholar.org/graph/v1/author/search"
)


class SemanticScholarSource:
    name = "semantic_scholar"

    def __init__(self, crawler: Any, api_key: str | None) -> None:
        self.crawler = crawler
        self.api_key = api_key

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        response = await self.crawler.fetch(
            SEMANTIC_AUTHOR_SEARCH,
            params={
                "query": seed.name,
                "limit": "10",
                "fields": (
                    "name,url,affiliations,homepage,"
                    "papers.title,papers.year"
                ),
            },
            headers=headers,
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            records = decode_json(response.body).get("data", [])
            if not isinstance(records, list):
                raise ValueError
        except (AttributeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        if not records:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for record in records:
            if not isinstance(record, dict) or not record.get("authorId"):
                continue
            author_id = str(record["authorId"])
            candidate_id = f"semantic_scholar:{author_id}"
            profile_url = record.get("url") or (
                f"https://www.semanticscholar.org/author/{author_id}"
            )
            items.append(
                evidence(
                    source=self.name,
                    field="semantic_scholar",
                    value=author_id,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            if record.get("name"):
                items.append(
                    evidence(
                        source=self.name,
                        field="name",
                        value=record["name"],
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            if record.get("homepage"):
                items.append(
                    evidence(
                        source=self.name,
                        field="homepage",
                        value=record["homepage"],
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            for affiliation in record.get("affiliations") or []:
                items.append(
                    evidence(
                        source=self.name,
                        field="affiliation",
                        value=affiliation,
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            for paper in record.get("papers") or []:
                if isinstance(paper, dict) and paper.get("title"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="paper_title",
                            value=paper["title"],
                            url=profile_url,
                            candidate_id=candidate_id,
                            metadata={"year": paper.get("year")},
                        )
                    )
        if not items:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
