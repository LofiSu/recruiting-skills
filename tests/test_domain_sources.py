import pytest

from researcher_recruiting.models import AuthorSeed
from researcher_recruiting.sources.dblp import DblpSource
from researcher_recruiting.sources.inspire import InspireSource
from tests.helpers import sequential_fixture_crawler


@pytest.mark.asyncio
async def test_dblp_emits_person_key_and_publications(load_fixture):
    crawler = sequential_fixture_crawler(
        {
            "https://dblp.org/search/author/api": load_fixture(
                "dblp_authors.json"
            ),
            "https://dblp.org/pid/12/345.xml": load_fixture(
                "dblp_person.xml"
            ),
        }
    )
    enriched = await DblpSource(crawler).enrich(
        AuthorSeed(name="Ada Lovelace")
    )
    fields = {item.field for item in enriched.evidence}
    assert {"dblp", "paper_title", "doi"} <= fields
    assert crawler.requests[0].params["q"] == "Ada Lovelace"


@pytest.mark.asyncio
async def test_inspire_emits_author_and_literature_ids(load_fixture):
    crawler = sequential_fixture_crawler(
        {
            "https://inspirehep.net/api/authors": load_fixture(
                "inspire_authors.json"
            ),
            "https://inspirehep.net/api/literature": load_fixture(
                "inspire_literature.json"
            ),
        }
    )
    enriched = await InspireSource(crawler).enrich(
        AuthorSeed(name="Ada Lovelace")
    )
    fields = {item.field for item in enriched.evidence}
    assert {"inspire", "orcid", "paper_title", "doi"} <= fields
    assert crawler.requests[1].params["q"] == "a 123456"
