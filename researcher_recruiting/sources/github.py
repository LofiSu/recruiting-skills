from typing import Any
from urllib.parse import quote

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

GITHUB_USER_SEARCH = "https://api.github.com/search/users"


class GitHubSource:
    name = "github"

    def __init__(self, crawler: Any, token: str | None) -> None:
        self.crawler = crawler
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        headers = self._headers()
        response = await self.crawler.fetch(
            GITHUB_USER_SEARCH,
            params={
                "q": f'"{seed.name}" in:fullname',
                "per_page": "10",
            },
            headers=headers,
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            users = decode_json(response.body).get("items", [])
            if not isinstance(users, list):
                raise ValueError
        except (AttributeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_search_response",
            )
        if not users:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for user in users:
            if not isinstance(user, dict) or not user.get("login"):
                continue
            login = str(user["login"])
            profile_response = await self.crawler.fetch(
                f"https://api.github.com/users/{quote(login)}",
                headers=headers,
            )
            if profile_response.status is not SourceStatus.OK:
                continue
            try:
                profile = decode_json(profile_response.body)
                if not isinstance(profile, dict):
                    raise ValueError
            except (UnicodeError, ValueError):
                continue
            candidate_id = f"github:{login.casefold()}"
            profile_url = profile.get("html_url") or (
                f"https://github.com/{quote(login)}"
            )
            items.append(
                evidence(
                    source=self.name,
                    field="github",
                    value=login,
                    url=profile_url,
                    candidate_id=candidate_id,
                    metadata={
                        "github_id": profile.get("id"),
                        "public_repos": profile.get("public_repos"),
                        "followers": profile.get("followers"),
                    },
                )
            )
            field_map = {
                "name": "name",
                "blog": "homepage",
                "company": "affiliation",
                "location": "location",
                "email": "email",
                "bio": "bio",
            }
            for source_key, field in field_map.items():
                value = profile.get(source_key)
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
        if not items:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="public_profiles_unavailable",
            )
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
