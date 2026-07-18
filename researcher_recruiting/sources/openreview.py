from typing import Any
from urllib.parse import quote

from researcher_recruiting.models import (
    AuthorSeed,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.sources.base import (
    content_value,
    decode_json,
    evidence,
)

OPENREVIEW_PROFILE_SEARCH = "https://api2.openreview.net/profiles/search"


class OpenReviewSource:
    name = "openreview"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        response = await self.crawler.fetch(
            OPENREVIEW_PROFILE_SEARCH,
            params={
                "term": seed.name,
                "limit": "10",
                "select": (
                    "id,content.names,content.history,content.homepage,"
                    "content.semanticScholar,content.gscholar,"
                    "content.linkedin"
                ),
            },
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            profiles = decode_json(response.body).get("profiles", [])
            if not isinstance(profiles, list):
                raise ValueError
        except (AttributeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_response",
            )
        if not profiles:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for profile in profiles:
            if not isinstance(profile, dict) or not profile.get("id"):
                continue
            profile_id = str(profile["id"])
            candidate_id = f"openreview:{profile_id}"
            profile_url = (
                "https://openreview.net/profile?id=" + quote(profile_id)
            )
            content = profile.get("content")
            if not isinstance(content, dict):
                content = {}
            items.append(
                evidence(
                    source=self.name,
                    field="openreview",
                    value=profile_id,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            names = content_value(content, "names") or []
            for name in names if isinstance(names, list) else []:
                if isinstance(name, dict) and name.get("fullname"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="name",
                            value=name["fullname"],
                            url=profile_url,
                            candidate_id=candidate_id,
                        )
                    )
            homepage = content_value(content, "homepage")
            if homepage:
                items.append(
                    evidence(
                        source=self.name,
                        field="homepage",
                        value=homepage,
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            linked_fields = {
                "semanticScholar": "semantic_scholar",
                "gscholar": "google_scholar",
                "linkedin": "linkedin",
            }
            for content_key, field in linked_fields.items():
                value = content_value(content, content_key)
                if value:
                    items.append(
                        evidence(
                            source=self.name,
                            field=field,
                            value=value,
                            url=profile_url,
                            candidate_id=candidate_id,
                        )
                    )
            history = content_value(content, "history") or []
            for role in history if isinstance(history, list) else []:
                institution = (
                    role.get("institution", {})
                    if isinstance(role, dict)
                    else {}
                )
                if isinstance(institution, dict) and institution.get("name"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="affiliation",
                            value=institution["name"],
                            url=profile_url,
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
