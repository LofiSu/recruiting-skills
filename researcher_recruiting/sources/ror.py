from typing import Any

from researcher_recruiting.models import Evidence, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

ROR_ORGANIZATIONS = "https://api.ror.org/v2/organizations"


class RorSource:
    name = "ror"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def normalize_affiliation(self, name: str) -> Evidence | None:
        response = await self.crawler.fetch(
            ROR_ORGANIZATIONS,
            params={"query": name},
        )
        if response.status is not SourceStatus.OK:
            return None
        try:
            organizations = decode_json(response.body).get("items", [])
        except (AttributeError, UnicodeError, ValueError):
            return None
        if not isinstance(organizations, list) or not organizations:
            return None
        organization = organizations[0]
        if not isinstance(organization, dict) or not organization.get("id"):
            return None
        names = organization.get("names") or []
        matched_name = next(
            (
                item.get("value")
                for item in names
                if isinstance(item, dict)
                and item.get("value")
                and {"ror_display", "label"} & set(item.get("types") or [])
            ),
            name,
        )
        locations = organization.get("locations") or []
        return evidence(
            source=self.name,
            field="ror",
            value=str(organization["id"]).rstrip("/").rsplit("/", 1)[-1],
            url=organization["id"],
            candidate_id=None,
            metadata={
                "query": name,
                "matched_name": matched_name,
                "locations": locations,
                "external_ids": organization.get("external_ids") or [],
            },
        )
