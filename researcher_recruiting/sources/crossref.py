import re
import unicodedata
from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

CROSSREF_WORKS = "https://api.crossref.org/works"


def _normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.casefold()))


def _contributor_name(contributor: dict[str, Any]) -> str:
    return " ".join(
        part for part in (contributor.get("given"), contributor.get("family")) if part
    )


class CrossrefSource:
    name = "crossref"

    def __init__(self, crawler: Any, mailto: str | None) -> None:
        self.crawler = crawler
        self.mailto = mailto

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        params = {
            "query.author": seed.name,
            "rows": "25",
            "select": (
                "DOI,title,author,published,container-title,relation,reference"
            ),
        }
        if self.mailto:
            params["mailto"] = self.mailto
        response = await self.crawler.fetch(CROSSREF_WORKS, params=params)
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            records = decode_json(response.body)["message"]["items"]
            if not isinstance(records, list):
                raise ValueError
        except (KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )

        wanted = {_normalized_name(seed.name)}
        wanted.update(_normalized_name(name) for name in seed.name_variants)
        items = []
        for work in records:
            if not isinstance(work, dict):
                continue
            contributor = next(
                (
                    author
                    for author in work.get("author") or []
                    if isinstance(author, dict)
                    and _normalized_name(_contributor_name(author)) in wanted
                ),
                None,
            )
            doi = work.get("DOI")
            if contributor is None or not doi:
                continue
            orcid = contributor.get("ORCID")
            identity_key = (
                str(orcid).rstrip("/").rsplit("/", 1)[-1]
                if orcid
                else _normalized_name(_contributor_name(contributor)).replace(" ", "-")
            )
            candidate_id = f"crossref:{identity_key}"
            work_url = f"https://doi.org/{doi}"
            items.append(
                evidence(
                    source=self.name,
                    field="doi",
                    value=doi,
                    url=work_url,
                    candidate_id=candidate_id,
                )
            )
            titles = work.get("title") or []
            if isinstance(titles, list) and titles:
                items.append(
                    evidence(
                        source=self.name,
                        field="paper_title",
                        value=titles[0],
                        url=work_url,
                        candidate_id=candidate_id,
                        metadata={
                            "published": work.get("published"),
                            "container_title": work.get("container-title"),
                        },
                    )
                )
            items.append(
                evidence(
                    source=self.name,
                    field="name",
                    value=_contributor_name(contributor),
                    url=work_url,
                    candidate_id=candidate_id,
                )
            )
            if orcid:
                orcid_id = str(orcid).rstrip("/").rsplit("/", 1)[-1]
                items.append(
                    evidence(
                        source=self.name,
                        field="orcid",
                        value=orcid_id,
                        url=f"https://orcid.org/{orcid_id}",
                        candidate_id=candidate_id,
                    )
                )
            for affiliation in contributor.get("affiliation") or []:
                if isinstance(affiliation, dict) and affiliation.get("name"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="affiliation",
                            value=affiliation["name"],
                            url=work_url,
                            candidate_id=candidate_id,
                        )
                    )
        if not items:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
