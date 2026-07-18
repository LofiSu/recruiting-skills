import pytest

from researcher_recruiting.models import AuthorSeed, SourceStatus
from researcher_recruiting.sources.datacite import DataCiteSource
from researcher_recruiting.sources.opencitations import OpenCitationsEnricher
from researcher_recruiting.sources.ror import RorSource
from researcher_recruiting.sources.wikidata import WikidataSource
from tests.helpers import fixture_crawler


@pytest.mark.asyncio
async def test_datacite_emits_research_output_dois(load_fixture):
    source = DataCiteSource(
        fixture_crawler(
            "https://api.datacite.org/dois",
            load_fixture("datacite_dois.json"),
        )
    )
    enriched = await source.enrich(AuthorSeed(name="Ada Lovelace"))
    assert enriched.status is SourceStatus.OK
    assert any(item.field == "doi" for item in enriched.evidence)
    assert any(item.field == "orcid" for item in enriched.evidence)
    assert all(
        item.candidate_id and item.candidate_id.startswith("datacite:")
        for item in enriched.evidence
    )


@pytest.mark.asyncio
async def test_ror_normalizes_affiliation_without_identifying_person(load_fixture):
    source = RorSource(
        fixture_crawler(
            "https://api.ror.org/v2/organizations",
            load_fixture("ror_organizations.json"),
        )
    )
    item = await source.normalize_affiliation("University of Example")
    assert item is not None
    assert item.field == "ror"
    assert item.candidate_id is None
    assert item.metadata["matched_name"] == "University of Example"


@pytest.mark.asyncio
async def test_wikidata_is_supporting_evidence_only(load_fixture):
    source = WikidataSource(
        fixture_crawler(
            "https://query.wikidata.org/sparql",
            load_fixture("wikidata_bindings.json"),
        )
    )
    enriched = await source.enrich(AuthorSeed(name="Ada Lovelace"))
    assert enriched.evidence
    assert all(
        item.metadata["strength"] == "supporting"
        for item in enriched.evidence
    )


@pytest.mark.asyncio
async def test_opencitations_enriches_only_discovered_dois(load_fixture):
    source = OpenCitationsEnricher(
        fixture_crawler(
            "https://opencitations.net/index/coci/api/v1/citations/10.1000/example",
            load_fixture("opencitations_citations.json"),
        )
    )
    enriched = await source.enrich_dois(("10.1000/example",))
    assert any(item.field == "citation_doi" for item in enriched.evidence)
    assert all(
        item.metadata["strength"] == "context_only"
        for item in enriched.evidence
    )


@pytest.mark.asyncio
async def test_opencitations_does_not_request_without_discovered_doi():
    from tests.helpers import StubCrawler

    crawler = StubCrawler({})
    enriched = await OpenCitationsEnricher(crawler).enrich_dois(())
    assert enriched.status is SourceStatus.NOT_FOUND
    assert crawler.requests == []
