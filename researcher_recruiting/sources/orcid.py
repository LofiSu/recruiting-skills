from typing import Any, Protocol

import httpx

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

ORCID_SEARCH = "https://pub.orcid.org/v3.0/search/"
ORCID_TOKEN = "https://orcid.org/oauth/token"


class OrcidTokenProvider(Protocol):
    async def get_token(self, client_id: str, client_secret: str) -> str:
        ...


class HttpxOrcidTokenProvider:
    def __init__(self) -> None:
        self._token: str | None = None

    async def get_token(self, client_id: str, client_secret: str) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ORCID_TOKEN,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                    "scope": "/read-public",
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token


def _nested_value(mapping: Any, *keys: str) -> Any:
    current = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


class OrcidSource:
    name = "orcid"

    def __init__(
        self,
        crawler: Any,
        token_provider: OrcidTokenProvider,
        client_id: str | None,
        client_secret: str | None,
    ) -> None:
        self.crawler = crawler
        self.token_provider = token_provider
        self.client_id = client_id
        self.client_secret = client_secret

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        if not self.client_id or not self.client_secret:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error=(
                    "ORCID_CLIENT_ID and ORCID_CLIENT_SECRET are required"
                ),
            )
        try:
            token = await self.token_provider.get_token(
                self.client_id, self.client_secret
            )
        except Exception as error:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error=f"token_request_failed:{type(error).__name__}",
            )
        headers = {
            "Accept": "application/vnd.orcid+json",
            "Authorization": f"Bearer {token}",
        }
        response = await self.crawler.fetch(
            ORCID_SEARCH,
            params={"q": f'given-and-family-names:"{seed.name}"'},
            headers=headers,
        )
        if response.status is not SourceStatus.OK:
            return SourceResult(self.name, response.status, error=response.error)
        try:
            records = decode_json(response.body).get("result", [])
            if not isinstance(records, list):
                raise ValueError
        except (AttributeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_search_response",
            )
        if not records:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        items = []
        for search_record in records[:10]:
            orcid = _nested_value(
                search_record, "orcid-identifier", "path"
            )
            if not orcid:
                continue
            profile_url = f"https://orcid.org/{orcid}"
            record_url = (
                f"https://pub.orcid.org/v3.0/{orcid}/record"
            )
            record_response = await self.crawler.fetch(
                record_url, headers=headers
            )
            if record_response.status is not SourceStatus.OK:
                continue
            try:
                record = decode_json(record_response.body)
                if not isinstance(record, dict):
                    raise ValueError
            except (UnicodeError, ValueError):
                continue
            candidate_id = f"orcid:{orcid}"
            items.append(
                evidence(
                    source=self.name,
                    field="orcid",
                    value=orcid,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            person = record.get("person") or {}
            name = person.get("name") or {}
            credit_name = _nested_value(name, "credit-name", "value")
            given = _nested_value(name, "given-names", "value")
            family = _nested_value(name, "family-name", "value")
            display_name = credit_name or " ".join(
                part for part in (given, family) if part
            )
            if display_name:
                items.append(
                    evidence(
                        source=self.name,
                        field="name",
                        value=display_name,
                        url=profile_url,
                        candidate_id=candidate_id,
                    )
                )
            researcher_urls = (
                (person.get("researcher-urls") or {}).get(
                    "researcher-url", []
                )
            )
            for researcher_url in researcher_urls:
                value = _nested_value(researcher_url, "url", "value")
                if value:
                    items.append(
                        evidence(
                            source=self.name,
                            field="homepage",
                            value=value,
                            url=profile_url,
                            candidate_id=candidate_id,
                            metadata={
                                "label": _nested_value(
                                    researcher_url, "url-name", "value"
                                )
                            },
                        )
                    )
            emails = (person.get("emails") or {}).get("email", [])
            for email in emails:
                if (
                    isinstance(email, dict)
                    and email.get("email")
                    and email.get("visibility") == "PUBLIC"
                ):
                    items.append(
                        evidence(
                            source=self.name,
                            field="email",
                            value=email["email"],
                            url=profile_url,
                            candidate_id=candidate_id,
                            metadata={"verified": email.get("verified")},
                        )
                    )
            activities = record.get("activities-summary") or {}
            affiliation_groups = (
                (activities.get("employments") or {}).get(
                    "affiliation-group", []
                )
            )
            for group in affiliation_groups:
                for summary in group.get("summaries", []):
                    employment = summary.get("employment-summary") or {}
                    organization = employment.get("organization") or {}
                    if organization.get("name"):
                        items.append(
                            evidence(
                                source=self.name,
                                field="affiliation",
                                value=organization["name"],
                                url=profile_url,
                                candidate_id=candidate_id,
                                metadata={
                                    "role": employment.get("role-title")
                                },
                            )
                        )
            work_groups = (
                (activities.get("works") or {}).get("group", [])
            )
            for group in work_groups:
                for work in group.get("work-summary", []):
                    title = _nested_value(
                        work, "title", "title", "value"
                    )
                    if title:
                        items.append(
                            evidence(
                                source=self.name,
                                field="paper_title",
                                value=title,
                                url=profile_url,
                                candidate_id=candidate_id,
                            )
                        )
                    external_ids = (
                        (work.get("external-ids") or {}).get(
                            "external-id", []
                        )
                    )
                    for external_id in external_ids:
                        if (
                            external_id.get("external-id-type") == "doi"
                            and external_id.get("external-id-value")
                        ):
                            doi = external_id["external-id-value"]
                            items.append(
                                evidence(
                                    source=self.name,
                                    field="doi",
                                    value=doi,
                                    url=f"https://doi.org/{doi}",
                                    candidate_id=candidate_id,
                                )
                            )
        if not items:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="public_records_unavailable",
            )
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
