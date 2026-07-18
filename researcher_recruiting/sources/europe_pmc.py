import re
from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

EUROPE_PMC_SEARCH = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
)


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


class EuropePmcSource:
    name = "europe_pmc"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        response = await self.crawler.fetch(
            EUROPE_PMC_SEARCH,
            params={
                "query": f'AUTH:"{seed.name}"',
                "resultType": "core",
                "format": "json",
                "pageSize": "25",
            },
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            records = decode_json(response.body)["resultList"]["result"]
            if not isinstance(records, list):
                raise ValueError
        except (KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        wanted = {_normalize(seed.name)}
        wanted.update(_normalize(item) for item in seed.name_variants)
        items = []
        for record in records:
            if not isinstance(record, dict):
                continue
            authors = (record.get("authorList") or {}).get("author", [])
            matched = next(
                (
                    author
                    for author in authors
                    if isinstance(author, dict)
                    and _normalize(str(author.get("fullName", ""))) in wanted
                ),
                None,
            )
            record_id = record.get("id") or record.get("pmid")
            if matched is None or not record_id:
                continue
            author_identifier = matched.get("authorId")
            orcid = (
                author_identifier.get("value")
                if isinstance(author_identifier, dict)
                and str(author_identifier.get("type", "")).casefold() == "orcid"
                else None
            )
            candidate_id = f"europe_pmc:{orcid or record_id}"
            profile_url = (
                "https://europepmc.org/article/"
                + str(record_id).replace("/", "/")
            )
            items.append(
                evidence(
                    source=self.name,
                    field="europe_pmc",
                    value=record_id,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            fields = {
                "pmid": record.get("pmid"),
                "doi": record.get("doi"),
                "paper_title": record.get("title"),
                "name": matched.get("fullName"),
                "orcid": orcid,
            }
            for field, value in fields.items():
                if not value:
                    continue
                if field == "doi":
                    url = f"https://doi.org/{value}"
                elif field == "orcid":
                    url = f"https://orcid.org/{value}"
                else:
                    url = profile_url
                items.append(
                    evidence(
                        source=self.name,
                        field=field,
                        value=value,
                        url=url,
                        candidate_id=candidate_id,
                        metadata=(
                            {
                                "year": record.get("pubYear"),
                                "journal": record.get("journalTitle"),
                            }
                            if field == "paper_title"
                            else None
                        ),
                    )
                )
        if not items:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
