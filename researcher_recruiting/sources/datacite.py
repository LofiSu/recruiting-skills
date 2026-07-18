import re
from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

DATACITE_DOIS = "https://api.datacite.org/dois"


def _name_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


class DataCiteSource:
    name = "datacite"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        response = await self.crawler.fetch(
            DATACITE_DOIS,
            params={
                "query": f'creators.name:"{seed.name}"',
                "page[size]": "25",
            },
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
        wanted = _name_tokens(seed.name)
        items = []
        for record in records:
            if not isinstance(record, dict):
                continue
            attributes = record.get("attributes")
            if not isinstance(attributes, dict):
                continue
            creator = next(
                (
                    item
                    for item in attributes.get("creators") or []
                    if isinstance(item, dict)
                    and wanted <= _name_tokens(
                        " ".join(
                            str(part)
                            for part in (
                                item.get("name"),
                                item.get("givenName"),
                                item.get("familyName"),
                            )
                            if part
                        )
                    )
                ),
                None,
            )
            doi = attributes.get("doi") or record.get("id")
            if creator is None or not doi:
                continue
            orcid = None
            for identifier in creator.get("nameIdentifiers") or []:
                if (
                    isinstance(identifier, dict)
                    and str(identifier.get("nameIdentifierScheme", "")).casefold()
                    == "orcid"
                ):
                    orcid = str(identifier.get("nameIdentifier", "")).rstrip(
                        "/"
                    ).rsplit("/", 1)[-1]
                    break
            identity_key = orcid or str(doi).casefold()
            candidate_id = f"datacite:{identity_key}"
            doi_url = f"https://doi.org/{doi}"
            items.append(
                evidence(
                    source=self.name,
                    field="doi",
                    value=doi,
                    url=doi_url,
                    candidate_id=candidate_id,
                )
            )
            items.append(
                evidence(
                    source=self.name,
                    field="name",
                    value=creator.get("name") or seed.name,
                    url=doi_url,
                    candidate_id=candidate_id,
                )
            )
            if orcid:
                items.append(
                    evidence(
                        source=self.name,
                        field="orcid",
                        value=orcid,
                        url=f"https://orcid.org/{orcid}",
                        candidate_id=candidate_id,
                    )
                )
            for title in attributes.get("titles") or []:
                if isinstance(title, dict) and title.get("title"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="paper_title",
                            value=title["title"],
                            url=doi_url,
                            candidate_id=candidate_id,
                            metadata={
                                "publisher": attributes.get("publisher"),
                                "published": attributes.get("published"),
                            },
                        )
                    )
            for related in attributes.get("relatedIdentifiers") or []:
                if (
                    isinstance(related, dict)
                    and related.get("relatedIdentifier")
                ):
                    items.append(
                        evidence(
                            source=self.name,
                            field="related_identifier",
                            value=related["relatedIdentifier"],
                            url=doi_url,
                            candidate_id=candidate_id,
                            metadata={
                                "type": related.get("relatedIdentifierType"),
                                "relation": related.get("relationType"),
                            },
                        )
                    )
        if not items:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
