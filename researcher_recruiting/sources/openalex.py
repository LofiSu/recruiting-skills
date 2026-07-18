from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

OPENALEX_AUTHORS = "https://api.openalex.org/authors"
OPENALEX_WORKS = "https://api.openalex.org/works"


def _short_openalex_id(value: object) -> str:
    return str(value).rstrip("/").rsplit("/", 1)[-1]


class OpenAlexSource:
    name = "openalex"

    def __init__(self, crawler: Any, api_key: str | None) -> None:
        self.crawler = crawler
        self.api_key = api_key

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        params = {
            "search": seed.name,
            "per-page": "10",
            "select": (
                "id,display_name,orcid,last_known_institutions,"
                "works_count,cited_by_count,summary_stats,x_concepts"
            ),
        }
        if self.api_key:
            params["api_key"] = self.api_key
        response = await self.crawler.fetch(OPENALEX_AUTHORS, params=params)
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            authors = decode_json(response.body).get("results", [])
            if not isinstance(authors, list):
                raise ValueError
        except (AttributeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        if not authors:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for author_index, author in enumerate(authors):
            if not isinstance(author, dict) or not author.get("id"):
                continue
            author_id = _short_openalex_id(author["id"])
            candidate_id = f"openalex:{author_id}"
            profile_url = str(author["id"])
            items.append(
                evidence(
                    source=self.name,
                    field="openalex",
                    value=author_id,
                    url=profile_url,
                    candidate_id=candidate_id,
                    metadata={
                        "works_count": author.get("works_count"),
                        "cited_by_count": author.get("cited_by_count"),
                        "summary_stats": author.get("summary_stats") or {},
                    },
                )
            )
            if author.get("display_name"):
                items.append(
                    evidence(
                        source=self.name,
                        field="name",
                        value=author["display_name"],
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            if author.get("orcid"):
                items.append(
                    evidence(
                        source=self.name,
                        field="orcid",
                        value=str(author["orcid"]).rstrip("/").rsplit("/", 1)[-1],
                        url=str(author["orcid"]),
                        candidate_id=candidate_id,
                    )
                )
            for institution in author.get("last_known_institutions") or []:
                if isinstance(institution, dict) and institution.get("display_name"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="affiliation",
                            value=institution["display_name"],
                            url=institution.get("id") or profile_url,
                            candidate_id=candidate_id,
                            metadata={
                                "ror": institution.get("ror"),
                                "openalex": institution.get("id"),
                            },
                        )
                    )
            for concept in author.get("x_concepts") or []:
                if isinstance(concept, dict) and concept.get("display_name"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="research_term",
                            value=concept["display_name"],
                            url=profile_url,
                            candidate_id=candidate_id,
                            metadata={"score": concept.get("score")},
                        )
                    )

            if author_index > 0:
                continue
            works_response = await self.crawler.fetch(
                OPENALEX_WORKS,
                params={
                    "filter": f"author.id:{author_id}",
                    "per-page": "25",
                    "select": (
                        "id,doi,display_name,publication_year,"
                        "cited_by_count,topics"
                    ),
                    **({"api_key": self.api_key} if self.api_key else {}),
                },
            )
            if works_response.status is not SourceStatus.OK:
                continue
            try:
                works = decode_json(works_response.body).get("results", [])
            except (AttributeError, UnicodeError, ValueError):
                continue
            for work in works if isinstance(works, list) else []:
                if not isinstance(work, dict) or not work.get("display_name"):
                    continue
                work_url = work.get("id") or profile_url
                items.append(
                    evidence(
                        source=self.name,
                        field="paper_title",
                        value=work["display_name"],
                        url=work_url,
                        candidate_id=candidate_id,
                        metadata={
                            "year": work.get("publication_year"),
                            "cited_by_count": work.get("cited_by_count"),
                        },
                    )
                )
                if work.get("doi"):
                    doi = str(work["doi"]).replace("https://doi.org/", "")
                    items.append(
                        evidence(
                            source=self.name,
                            field="doi",
                            value=doi,
                            url=str(work["doi"]),
                            candidate_id=candidate_id,
                        )
                    )
                for topic in work.get("topics") or []:
                    if isinstance(topic, dict) and topic.get("display_name"):
                        items.append(
                            evidence(
                                source=self.name,
                                field="research_term",
                                value=topic["display_name"],
                                url=work_url,
                                candidate_id=candidate_id,
                            )
                        )
        if not items:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
