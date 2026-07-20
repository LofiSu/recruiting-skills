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


def test_parse_atom_feed_preserves_only_explicit_author_email():
    paper = parse_atom_feed(
        """\
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1706.03762v7</id>
            <title>Paper</title>
            <author>
              <name>Ada Lovelace</name>
              <email>Ada@University.Example</email>
            </author>
            <author><name>Charles Babbage</name></author>
          </entry>
        </feed>
        """
    )[0]

    assert paper.authors[0].email == "Ada@University.Example"
    assert paper.authors[0].email_provenance is not None
    assert "email_provenance" not in repr(paper.authors[0])
    assert paper.authors[1].email is None
    assert paper.authors[1].email_provenance is None


@pytest.mark.parametrize(
    "email_xml",
    (
        "<email>not-an-email</email>",
        "<email>ada@example.org,bob@example.org</email>",
        "<email>ada@example.org;bob@example.org</email>",
        "<email>ada@example.org&#10;bob@example.org</email>",
        f"<email>{'a' * 245}@example.org</email>",
        "<email>ada@example.org</email><email>bob@example.org</email>",
    ),
)
def test_parse_atom_feed_rejects_malformed_or_multiple_author_email(
    email_xml,
):
    paper = parse_atom_feed(
        f"""\
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1706.03762v7</id>
            <title>Paper</title>
            <author>
              <name>Ada Lovelace</name>
              {email_xml}
            </author>
          </entry>
        </feed>
        """
    )[0]

    assert paper.authors[0].email is None
    assert paper.authors[0].email_provenance is None


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
