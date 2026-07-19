import pytest

from researcher_recruiting.crawling import FetchResult
from researcher_recruiting.models import AuthorSeed, SourceStatus
from researcher_recruiting.sources.github import GitHubSource
from researcher_recruiting.sources.orcid import OrcidSource
from tests.helpers import StubCrawler


class StaticTokenProvider:
    def __init__(self, token: str) -> None:
        self.token = token

    async def get_token(self, client_id: str, client_secret: str) -> str:
        return self.token


def fixture_result(url, body, content_type="application/json"):
    return FetchResult(
        SourceStatus.OK,
        url,
        200,
        content_type,
        body.encode(),
        False,
    )


@pytest.mark.asyncio
async def test_orcid_without_credentials_is_source_unavailable():
    crawler = StubCrawler({})
    enriched = await OrcidSource(
        crawler, StaticTokenProvider("unused"), None, None
    ).enrich(AuthorSeed(name="Ada Lovelace"))
    assert enriched.status is SourceStatus.SOURCE_UNAVAILABLE
    assert enriched.error and "ORCID_CLIENT_ID" in enriched.error
    assert crawler.requests == []


@pytest.mark.asyncio
async def test_orcid_public_search_and_record_are_normalized(load_fixture):
    search_url = "https://pub.orcid.org/v3.0/search/"
    record_url = (
        "https://pub.orcid.org/v3.0/0000-0001-2345-6789/record"
    )
    crawler = StubCrawler(
        {
            search_url: [
                fixture_result(
                    search_url,
                    load_fixture("orcid_search.json"),
                    "application/vnd.orcid+json",
                )
            ],
            record_url: [
                fixture_result(
                    record_url,
                    load_fixture("orcid_record.json"),
                    "application/vnd.orcid+json",
                )
            ],
        }
    )
    enriched = await OrcidSource(
        crawler,
        StaticTokenProvider("public-token"),
        "client-id",
        "client-secret",
    ).enrich(AuthorSeed(name="Ada Lovelace"))
    fields = {item.field for item in enriched.evidence}
    assert {"orcid", "homepage", "email", "affiliation", "doi"} <= fields
    email = next(
        item for item in enriched.evidence if item.field == "email"
    )
    assert email.metadata["visibility"] == "public_professional"
    assert "public-token" not in repr(enriched)
    assert all(
        request.headers["Authorization"] == "Bearer public-token"
        for request in crawler.requests
    )


@pytest.mark.asyncio
async def test_github_search_uses_name_and_fetches_public_profile(load_fixture):
    search_url = "https://api.github.com/search/users"
    profile_url = "https://api.github.com/users/ada"
    crawler = StubCrawler(
        {
            search_url: [
                fixture_result(
                    search_url, load_fixture("github_user_search.json")
                )
            ],
            profile_url: [
                fixture_result(profile_url, load_fixture("github_user.json"))
            ],
        }
    )
    enriched = await GitHubSource(crawler, token=None).enrich(
        AuthorSeed(
            name="Ada Lovelace", affiliation="Analytical Engines"
        )
    )
    assert crawler.requests[0].params["q"] == '"Ada Lovelace" in:fullname'
    fields = {item.field for item in enriched.evidence}
    assert {"github", "homepage", "affiliation", "email"} <= fields
    email = next(
        item for item in enriched.evidence if item.field == "email"
    )
    assert email.metadata["visibility"] == "public_professional"
    assert "Authorization" not in crawler.requests[0].headers


@pytest.mark.asyncio
async def test_github_token_is_header_only_and_never_evidence(load_fixture):
    search_url = "https://api.github.com/search/users"
    profile_url = "https://api.github.com/users/ada"
    crawler = StubCrawler(
        {
            search_url: [
                fixture_result(
                    search_url, load_fixture("github_user_search.json")
                )
            ],
            profile_url: [
                fixture_result(profile_url, load_fixture("github_user.json"))
            ],
        }
    )
    enriched = await GitHubSource(
        crawler, token="github-secret"
    ).enrich(AuthorSeed(name="Ada Lovelace"))
    assert all(
        request.headers["Authorization"] == "Bearer github-secret"
        for request in crawler.requests
    )
    assert "github-secret" not in repr(enriched)
