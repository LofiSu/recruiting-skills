from pathlib import Path

import httpx
import pytest

from researcher_recruiting.sources.arxiv import (
    parse_arxiv_id,
    parse_atom_feed,
    resolve_paper,
)


def test_parse_arxiv_id_accepts_abs_pdf_and_version():
    assert parse_arxiv_id("https://arxiv.org/abs/1706.03762v7") == "1706.03762"
    assert parse_arxiv_id("https://arxiv.org/pdf/1706.03762.pdf") == "1706.03762"


def test_parse_atom_feed_preserves_author_order(load_fixture):
    paper = parse_atom_feed(load_fixture("arxiv_single.xml"))[0]
    assert paper.arxiv_id == "1706.03762"
    assert paper.title == "Attention Is All You Need"
    assert [author.name for author in paper.authors[:2]] == [
        "Ashish Vaswani",
        "Noam Shazeer",
    ]
    assert paper.authors[0].coauthors[0] == "Noam Shazeer"


@pytest.mark.asyncio
async def test_resolve_title_uses_encoded_search_query(respx_mock):
    fixture_xml = Path("tests/fixtures/arxiv_single.xml").read_text(encoding="utf-8")
    route = respx_mock.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=fixture_xml)
    )
    async with httpx.AsyncClient() as client:
        paper = await resolve_paper("Attention Is All You Need", client)
    assert route.calls[0].request.url.params["search_query"] == (
        'ti:"Attention Is All You Need"'
    )
    assert paper.arxiv_id == "1706.03762"
