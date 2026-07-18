import json

import pytest

from researcher_recruiting.crawling import FetchResult
from researcher_recruiting.models import AuthorSeed, SourceStatus
from researcher_recruiting.sources.openreview import OpenReviewSource
from researcher_recruiting.sources.semantic_scholar import SemanticScholarSource
from tests.helpers import StubCrawler


def result(url: str, payload: dict) -> FetchResult:
    return FetchResult(
        SourceStatus.OK,
        url,
        200,
        "application/json",
        json.dumps(payload).encode(),
        False,
    )


@pytest.mark.asyncio
async def test_semantic_scholar_emits_paper_and_homepage_evidence(load_fixture):
    url = "https://api.semanticscholar.org/graph/v1/author/search"
    crawler = StubCrawler(
        {
            url: [
                FetchResult(
                    SourceStatus.OK,
                    url,
                    200,
                    "application/json",
                    load_fixture("semantic_author_search.json").encode(),
                    False,
                )
            ]
        }
    )
    source = SemanticScholarSource(crawler, api_key=None)
    enriched = await source.enrich(AuthorSeed(name="Ada Lovelace"))
    assert enriched.status is SourceStatus.OK
    assert {(item.field, item.source) for item in enriched.evidence} >= {
        ("semantic_scholar", "semantic_scholar"),
        ("paper_title", "semantic_scholar"),
        ("homepage", "semantic_scholar"),
    }
    assert crawler.last_params["query"] == "Ada Lovelace"
    assert "x-api-key" not in crawler.requests[-1].headers


@pytest.mark.asyncio
async def test_openreview_searches_term_and_exposes_public_profile_fields(
    load_fixture,
):
    url = "https://api2.openreview.net/profiles/search"
    crawler = StubCrawler(
        {
            url: [
                FetchResult(
                    SourceStatus.OK,
                    url,
                    200,
                    "application/json",
                    load_fixture("openreview_profiles.json").encode(),
                    False,
                )
            ]
        }
    )
    enriched = await OpenReviewSource(crawler).enrich(
        AuthorSeed(name="Ada Lovelace")
    )
    assert crawler.last_params["term"] == "Ada Lovelace"
    assert any(item.field == "openreview" for item in enriched.evidence)
    assert any(item.field == "homepage" for item in enriched.evidence)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_class", "url", "payload"),
    [
        (
            SemanticScholarSource,
            "https://api.semanticscholar.org/graph/v1/author/search",
            {"data": []},
        ),
        (
            OpenReviewSource,
            "https://api2.openreview.net/profiles/search",
            {"profiles": []},
        ),
    ],
)
async def test_empty_academic_search_is_not_found(source_class, url, payload):
    crawler = StubCrawler({url: [result(url, payload)]})
    source = (
        source_class(crawler, api_key=None)
        if source_class is SemanticScholarSource
        else source_class(crawler)
    )
    enriched = await source.enrich(AuthorSeed(name="Nobody"))
    assert enriched.status is SourceStatus.NOT_FOUND
    assert enriched.evidence == ()


@pytest.mark.asyncio
async def test_malformed_openreview_profile_is_source_unavailable():
    url = "https://api2.openreview.net/profiles/search"
    crawler = StubCrawler({url: [result(url, {"profiles": [{"content": {}}]})]})
    enriched = await OpenReviewSource(crawler).enrich(
        AuthorSeed(name="Ada Lovelace")
    )
    assert enriched.status is SourceStatus.SOURCE_UNAVAILABLE
    assert enriched.error == "malformed_response"
