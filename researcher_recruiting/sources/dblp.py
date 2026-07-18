from typing import Any
from xml.etree import ElementTree

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

DBLP_AUTHOR_SEARCH = "https://dblp.org/search/author/api"


class DblpSource:
    name = "dblp"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        response = await self.crawler.fetch(
            DBLP_AUTHOR_SEARCH,
            params={"q": seed.name, "format": "json", "h": "10"},
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            hits = decode_json(response.body)["result"]["hits"].get("hit", [])
            if not isinstance(hits, list):
                raise ValueError
        except (AttributeError, KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        if not hits:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for hit in hits:
            info = hit.get("info") if isinstance(hit, dict) else None
            if not isinstance(info, dict) or not info.get("url"):
                continue
            profile_url = str(info["url"])
            person_key = profile_url.rstrip("/").split("/pid/", 1)[-1]
            candidate_id = f"dblp:{person_key}"
            items.append(
                evidence(
                    source=self.name,
                    field="dblp",
                    value=person_key,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            if info.get("author"):
                items.append(
                    evidence(
                        source=self.name,
                        field="name",
                        value=info["author"],
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            aliases = info.get("aliases", {}).get("alias", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases if isinstance(aliases, list) else []:
                items.append(
                    evidence(
                        source=self.name,
                        field="name_variant",
                        value=alias,
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )

            xml_response = await self.crawler.fetch(f"{profile_url}.xml")
            if xml_response.status is not SourceStatus.OK:
                continue
            try:
                root = ElementTree.fromstring(xml_response.body)
            except ElementTree.ParseError:
                continue
            for record in root.findall("./r/*"):
                title = record.findtext("title")
                if not title:
                    continue
                publication_url = record.findtext("ee") or profile_url
                items.append(
                    evidence(
                        source=self.name,
                        field="paper_title",
                        value=" ".join(title.split()),
                        url=publication_url,
                        candidate_id=candidate_id,
                        metadata={
                            "year": record.findtext("year"),
                            "dblp_key": record.attrib.get("key"),
                        },
                    )
                )
                if "doi.org/" in publication_url:
                    items.append(
                        evidence(
                            source=self.name,
                            field="doi",
                            value=publication_url.split("doi.org/", 1)[-1],
                            url=publication_url,
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
