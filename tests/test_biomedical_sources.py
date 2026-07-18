import pytest

from researcher_recruiting.models import AuthorSeed, SourceStatus
from researcher_recruiting.sources.europe_pmc import EuropePmcSource
from researcher_recruiting.sources.pubmed import PubmedSource
from researcher_recruiting.sources.unpaywall import UnpaywallEnricher
from tests.helpers import (
    StubCrawler,
    fixture_crawler,
    sequential_fixture_crawler,
)


@pytest.mark.asyncio
async def test_pubmed_emits_pmid_doi_orcid_and_titles(load_fixture):
    crawler = sequential_fixture_crawler(
        {
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi": (
                load_fixture("pubmed_search.json")
            ),
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi": (
                load_fixture("pubmed_summary.json")
            ),
        }
    )
    enriched = await PubmedSource(crawler, api_key=None).enrich(
        AuthorSeed(name="Ada Lovelace")
    )
    fields = {item.field for item in enriched.evidence}
    assert {"pmid", "doi", "orcid", "paper_title"} <= fields
    assert crawler.requests[0].params["term"] == "Ada Lovelace[Author]"
    assert "api_key" not in crawler.requests[0].params


@pytest.mark.asyncio
async def test_europe_pmc_emits_life_science_author_records(load_fixture):
    enriched = await EuropePmcSource(
        fixture_crawler(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            load_fixture("europe_pmc_search.json"),
        )
    ).enrich(AuthorSeed(name="Ada Lovelace"))
    fields = {item.field for item in enriched.evidence}
    assert {"europe_pmc", "pmid", "doi", "orcid"} <= fields


@pytest.mark.asyncio
async def test_unpaywall_requires_contact_email():
    enriched = await UnpaywallEnricher(
        StubCrawler({}), email=None
    ).enrich_dois(("10.1000/example",))
    assert enriched.status is SourceStatus.SOURCE_UNAVAILABLE
    assert enriched.error and "UNPAYWALL_EMAIL" in enriched.error


@pytest.mark.asyncio
async def test_unpaywall_without_dois_does_not_require_email():
    enriched = await UnpaywallEnricher(
        StubCrawler({}), email=None
    ).enrich_dois(())
    assert enriched.status is SourceStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_unpaywall_emits_lawful_open_access_location(load_fixture):
    crawler = fixture_crawler(
        "https://api.unpaywall.org/v2/10.1000/example",
        load_fixture("unpaywall_doi.json"),
    )
    enriched = await UnpaywallEnricher(
        crawler, email="maintainer@example.com"
    ).enrich_dois(("10.1000/example",))
    assert enriched.status is SourceStatus.OK
    assert any(
        item.field == "open_access_url" for item in enriched.evidence
    )
    assert crawler.last_params["email"] == "maintainer@example.com"
