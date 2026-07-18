from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

INSPIRE_AUTHORS = "https://inspirehep.net/api/authors"
INSPIRE_LITERATURE = "https://inspirehep.net/api/literature"


class InspireSource:
    name = "inspire"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        response = await self.crawler.fetch(
            INSPIRE_AUTHORS,
            params={"q": f'name.raw:"{seed.name}"', "size": "10"},
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            authors = decode_json(response.body)["hits"]["hits"]
            if not isinstance(authors, list):
                raise ValueError
        except (KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        if not authors:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for author in authors:
            if not isinstance(author, dict) or not author.get("id"):
                continue
            record_id = str(author["id"])
            candidate_id = f"inspire:{record_id}"
            profile_url = f"https://inspirehep.net/authors/{record_id}"
            metadata = author.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            items.append(
                evidence(
                    source=self.name,
                    field="inspire",
                    value=record_id,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            name = metadata.get("name")
            if isinstance(name, dict) and name.get("value"):
                items.append(
                    evidence(
                        source=self.name,
                        field="name",
                        value=name["value"],
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            if metadata.get("orcid"):
                items.append(
                    evidence(
                        source=self.name,
                        field="orcid",
                        value=metadata["orcid"],
                        url=f"https://orcid.org/{metadata['orcid']}",
                        candidate_id=candidate_id,
                    )
                )
            for position in metadata.get("positions") or []:
                if isinstance(position, dict) and position.get("institution"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="affiliation",
                            value=position["institution"],
                            url=profile_url,
                            candidate_id=candidate_id,
                            metadata={"current": position.get("current")},
                        )
                    )

            works_response = await self.crawler.fetch(
                INSPIRE_LITERATURE,
                params={"q": f"a {record_id}", "size": "25"},
            )
            if works_response.status is not SourceStatus.OK:
                continue
            try:
                works = decode_json(works_response.body)["hits"]["hits"]
            except (KeyError, TypeError, UnicodeError, ValueError):
                continue
            for work in works if isinstance(works, list) else []:
                work_id = str(work.get("id", ""))
                work_url = (
                    f"https://inspirehep.net/literature/{work_id}"
                    if work_id
                    else profile_url
                )
                work_metadata = work.get("metadata") or {}
                titles = work_metadata.get("titles") or []
                for title in titles:
                    if isinstance(title, dict) and title.get("title"):
                        items.append(
                            evidence(
                                source=self.name,
                                field="paper_title",
                                value=title["title"],
                                url=work_url,
                                candidate_id=candidate_id,
                                metadata={"inspire_literature_id": work_id},
                            )
                        )
                for doi in work_metadata.get("dois") or []:
                    if isinstance(doi, dict) and doi.get("value"):
                        items.append(
                            evidence(
                                source=self.name,
                                field="doi",
                                value=doi["value"],
                                url=f"https://doi.org/{doi['value']}",
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
