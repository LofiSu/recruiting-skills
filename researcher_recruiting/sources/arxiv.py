import re
from xml.etree import ElementTree

import httpx

from researcher_recruiting.models import (
    PAPER_EMAIL_PROVENANCE,
    AuthorSeed,
    PaperRecord,
)

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_ID_RE = re.compile(
    r"(?:abs/|pdf/)?(\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?(?:\.pdf)?$",
    re.IGNORECASE,
)
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
_EMAIL_RE = re.compile(
    r"[A-Z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+",
    re.IGNORECASE | re.ASCII,
)


class PaperNotFound(LookupError):
    """Raised when arXiv returns no paper for the requested identifier or title."""


def parse_arxiv_id(value: str) -> str | None:
    match = ARXIV_ID_RE.search(value.strip())
    return match.group(1) if match else None


def _text(entry: ElementTree.Element, name: str) -> str:
    node = entry.find(f"{ATOM}{name}")
    return " ".join((node.text or "").split()) if node is not None else ""


def _explicit_author_email(
    author: ElementTree.Element,
) -> str | None:
    nodes = [
        *author.findall(f"{ATOM}email"),
        *author.findall(f"{ARXIV}email"),
    ]
    if len(nodes) != 1:
        return None
    value = nodes[0].text or ""
    if (
        not value
        or len(value) > 254
        or "," in value
        or ";" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or _EMAIL_RE.fullmatch(value) is None
    ):
        return None
    local, domain = value.rsplit("@", 1)
    if len(local) > 64 or len(domain) > 253:
        return None
    return value


def _parse_entry(entry: ElementTree.Element) -> PaperRecord:
    entry_id = _text(entry, "id")
    arxiv_id = parse_arxiv_id(entry_id)
    if arxiv_id is None:
        raise ValueError(f"Invalid arXiv entry id: {entry_id!r}")

    title = _text(entry, "title")
    author_data = []
    for author in entry.findall(f"{ATOM}author"):
        name = _text(author, "name")
        affiliation = author.find(f"{ARXIV}affiliation")
        email = _explicit_author_email(author)
        author_data.append(
            (
                name,
                " ".join((affiliation.text or "").split())
                if affiliation is not None
                else None,
                email,
            )
        )

    authors = tuple(
        AuthorSeed(
            name=name,
            affiliation=affiliation,
            email=email,
            coauthors=tuple(
                other for other, _, _ in author_data if other != name
            ),
            paper_title=title,
            email_provenance=(
                PAPER_EMAIL_PROVENANCE if email is not None else None
            ),
        )
        for name, affiliation, email in author_data
    )
    categories = tuple(
        category.attrib["term"]
        for category in entry.findall(f"{ATOM}category")
        if category.attrib.get("term")
    )
    return PaperRecord(
        arxiv_id=arxiv_id,
        title=title,
        abstract=_text(entry, "summary"),
        submitted_at=_text(entry, "published") or None,
        categories=categories,
        authors=authors,
        source_url=f"https://arxiv.org/abs/{arxiv_id}",
    )


def parse_atom_feed(xml: str) -> tuple[PaperRecord, ...]:
    root = ElementTree.fromstring(xml)
    return tuple(_parse_entry(entry) for entry in root.findall(f"{ATOM}entry"))


async def resolve_paper(value: str, client: httpx.AsyncClient) -> PaperRecord:
    arxiv_id = parse_arxiv_id(value)
    params = (
        {"id_list": arxiv_id}
        if arxiv_id
        else {
            "search_query": f'ti:"{value.strip()}"',
            "max_results": "5",
        }
    )
    response = await client.get(ARXIV_API, params=params, timeout=15)
    response.raise_for_status()
    papers = parse_atom_feed(response.text)
    if not papers:
        raise PaperNotFound(value)
    return papers[0]
