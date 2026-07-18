from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


def _sparql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class WikidataSource:
    name = "wikidata"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        query = f"""
        SELECT ?item ?itemLabel ?orcid ?website ?employerLabel WHERE {{
          ?item wdt:P31 wd:Q5;
                rdfs:label ?itemLabel.
          FILTER(LANG(?itemLabel) = "en")
          FILTER(LCASE(STR(?itemLabel)) = LCASE("{_sparql_string(seed.name)}"))
          OPTIONAL {{ ?item wdt:P496 ?orcid. }}
          OPTIONAL {{ ?item wdt:P856 ?website. }}
          OPTIONAL {{
            ?item wdt:P108 ?employer.
            ?employer rdfs:label ?employerLabel.
            FILTER(LANG(?employerLabel) = "en")
          }}
        }}
        LIMIT 10
        """
        response = await self.crawler.fetch(
            WIKIDATA_SPARQL,
            params={"query": query, "format": "json"},
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            bindings = decode_json(response.body)["results"]["bindings"]
            if not isinstance(bindings, list):
                raise ValueError
        except (KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        items = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            item_url = (binding.get("item") or {}).get("value")
            if not item_url:
                continue
            entity_id = item_url.rstrip("/").rsplit("/", 1)[-1]
            candidate_id = f"wikidata:{entity_id}"
            fields = {
                "item": ("wikidata", entity_id),
                "itemLabel": (
                    "name",
                    (binding.get("itemLabel") or {}).get("value"),
                ),
                "orcid": ("orcid", (binding.get("orcid") or {}).get("value")),
                "website": (
                    "homepage",
                    (binding.get("website") or {}).get("value"),
                ),
                "employerLabel": (
                    "affiliation",
                    (binding.get("employerLabel") or {}).get("value"),
                ),
            }
            for _, (field, value) in fields.items():
                if value:
                    items.append(
                        evidence(
                            source=self.name,
                            field=field,
                            value=value,
                            url=item_url,
                            candidate_id=candidate_id,
                            metadata={"strength": "supporting"},
                        )
                    )
        if not items:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
