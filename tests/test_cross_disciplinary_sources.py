import pytest

from researcher_recruiting.models import AuthorSeed, SourceStatus
from researcher_recruiting.sources.crossref import CrossrefSource
from researcher_recruiting.sources.openalex import OpenAlexSource
from tests.helpers import fixture_crawler, sequential_fixture_crawler


@pytest.mark.asyncio
async def test_openalex_emits_author_institution_orcid_and_works(load_fixture):
    crawler = sequential_fixture_crawler(
        {
            "https://api.openalex.org/authors": load_fixture(
                "openalex_authors.json"
            ),
            "https://api.openalex.org/works": load_fixture(
                "openalex_works.json"
            ),
        }
    )
    enriched = await OpenAlexSource(crawler, api_key="free-key").enrich(
        AuthorSeed(name="Ada Lovelace", affiliation="Analytical Engines")
    )
    fields = {item.field for item in enriched.evidence}
    assert {"openalex", "affiliation", "orcid", "paper_title", "doi"} <= fields
    assert crawler.requests[0].params["search"] == "Ada Lovelace"
    assert crawler.requests[0].params["api_key"] == "free-key"
    assert crawler.requests[1].params["filter"] == "author.id:A123"


@pytest.mark.asyncio
async def test_crossref_emits_only_matched_contributor_works(load_fixture):
    crawler = fixture_crawler(
        "https://api.crossref.org/works",
        load_fixture("crossref_works.json"),
    )
    enriched = await CrossrefSource(
        crawler, mailto="maintainer@example.com"
    ).enrich(AuthorSeed(name="Ada Lovelace"))
    assert enriched.status is SourceStatus.OK
    assert any(item.field == "doi" for item in enriched.evidence)
    assert any(item.field == "orcid" for item in enriched.evidence)
    assert all(item.value != "10.1000/unrelated" for item in enriched.evidence)
    assert crawler.last_params["query.author"] == "Ada Lovelace"
    assert crawler.last_params["mailto"] == "maintainer@example.com"


@pytest.mark.asyncio
async def test_crossref_omits_mailto_and_returns_not_found_without_match(
    load_fixture,
):
    crawler = fixture_crawler(
        "https://api.crossref.org/works",
        load_fixture("crossref_works.json"),
    )
    enriched = await CrossrefSource(crawler, mailto=None).enrich(
        AuthorSeed(name="Grace Hopper")
    )
    assert enriched.status is SourceStatus.NOT_FOUND
    assert "mailto" not in crawler.last_params
