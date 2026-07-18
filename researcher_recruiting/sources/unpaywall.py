from typing import Any
from urllib.parse import quote

from researcher_recruiting.models import SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

UNPAYWALL_BASE = "https://api.unpaywall.org/v2"


class UnpaywallEnricher:
    name = "unpaywall"

    def __init__(self, crawler: Any, email: str | None) -> None:
        self.crawler = crawler
        self.email = email

    async def enrich_dois(self, dois: tuple[str, ...]) -> SourceResult:
        if not dois:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        if not self.email:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="UNPAYWALL_EMAIL is required",
            )
        items = []
        unavailable = False
        for doi in dict.fromkeys(dois):
            url = f"{UNPAYWALL_BASE}/{quote(doi)}"
            response = await self.crawler.fetch(
                url, params={"email": self.email}
            )
            if response.status is not SourceStatus.OK:
                unavailable = True
                continue
            try:
                record = decode_json(response.body)
                if not isinstance(record, dict):
                    raise ValueError
            except (UnicodeError, ValueError):
                unavailable = True
                continue
            location = record.get("best_oa_location")
            if not isinstance(location, dict):
                continue
            candidate_id = f"doi:{doi.casefold()}"
            for key in ("url", "url_for_pdf"):
                if location.get(key):
                    items.append(
                        evidence(
                            source=self.name,
                            field="open_access_url",
                            value=location[key],
                            url=location[key],
                            candidate_id=candidate_id,
                            metadata={
                                "doi": doi,
                                "license": location.get("license"),
                                "host_type": location.get("host_type"),
                                "oa_status": record.get("oa_status"),
                            },
                        )
                    )
        if items:
            return SourceResult(self.name, SourceStatus.OK, tuple(items))
        if unavailable:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="open_access_lookup_unavailable",
            )
        return SourceResult(self.name, SourceStatus.NOT_FOUND)
