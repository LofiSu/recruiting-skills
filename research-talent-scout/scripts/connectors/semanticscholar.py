"""Fetch Semantic Scholar papers and authors into talent-scout records.

Uses the public Academic Graph API only:

- ``GET /graph/v1/paper/search`` for a venue and year
- ``GET /graph/v1/author/search`` and ``GET /graph/v1/author/{id}/papers``

Relevance search is not a complete venue census. It returns at most 1,000
hits, and this client defaults to a much smaller page. The bulk search
endpoint is not called.

Authentication and pace
-----------------------
``S2_API_KEY`` is optional. When set, it is sent as the ``x-api-key`` header.
Semantic Scholar's introductory key limit is 1 request/second across
endpoints. Unauthenticated calls share one public pool and are throttled when
that pool is busy. The default CLI pause is 1.1 seconds. HTTP 429 and 503
responses are retried up to three times using ``Retry-After``.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

try:
    from scripts.connectors.mapping import (
        AuthorDraft,
        PublicationDraft,
        authorship_category,
        caller_warnings,
        canonical_venue,
        https_url,
        personal_homepage,
        remember_author,
        to_records,
    )
    from scripts.import_records import VENUE_NAMES
except ModuleNotFoundError:
    from connectors.mapping import (
        AuthorDraft,
        PublicationDraft,
        authorship_category,
        caller_warnings,
        canonical_venue,
        https_url,
        personal_homepage,
        remember_author,
        to_records,
    )
    from import_records import VENUE_NAMES


API_ROOT = "https://api.semanticscholar.org/graph/v1"
PAPER_FIELDS = ",".join(
    [
        "paperId",
        "title",
        "year",
        "venue",
        "publicationVenue",
        "url",
        "externalIds",
        "openAccessPdf",
        "authors",
    ]
)
AUTHOR_FIELDS = "authorId,name,affiliations,homepage,url,externalIds"
MAX_PAGES = 10


def fetch_semanticscholar(
    client,
    *,
    degree: str,
    retrieved_at: str,
    api_key_present: bool,
    venue: Optional[str] = None,
    year: Optional[int] = None,
    author: Optional[str] = None,
    author_id: Optional[str] = None,
    graduation_year: Optional[int] = None,
    max_works: int = 25,
    max_authors: int = 3,
) -> tuple:
    _require_mode(venue, year, author, author_id, max_works, max_authors)
    warnings = caller_warnings("semanticscholar", degree, graduation_year)
    if api_key_present:
        warnings.append(
            "semanticscholar: S2_API_KEY is set. Keep the pause at or above 1 second "
            "unless Semantic Scholar has granted a higher limit. The introductory key limit is 1 request/second."
        )
    else:
        warnings.append(
            "semanticscholar: S2_API_KEY is unset. Unauthenticated calls share the public pool "
            "(documented as a shared 1000 requests/second, and often slower when the pool is busy). "
            "Set S2_API_KEY for a dedicated 1 request/second budget. The default pause is 1.1 seconds."
        )
    warnings.append(
        "semanticscholar: paper search is relevance-ranked and not a complete venue census."
    )
    if author_id or author:
        drafts, fetch_warnings = _authors_mode(
            client,
            author=author,
            author_id=author_id,
            year=year,
            max_works=max_works,
            max_authors=max_authors,
        )
    else:
        drafts, fetch_warnings = _venue_mode(client, venue=venue, year=year, max_works=max_works)
    warnings.extend(fetch_warnings)
    records = to_records(
        drafts,
        degree=degree,
        retrieved_at=retrieved_at,
        graduation_year=graduation_year,
    )
    if not records:
        warnings.append(
            "semanticscholar: no importable records. Unsupported venues and authors without an id are skipped."
        )
    return records, warnings


def _require_mode(venue, year, author, author_id, max_works, max_authors) -> None:
    if max_works < 1 or max_authors < 1:
        raise ValueError("max_works and max_authors must be positive")
    modes = [bool(venue), bool(author), bool(author_id)]
    if sum(modes) != 1:
        raise ValueError("provide exactly one of --venue, --author, or --author-id")
    if venue and year is None:
        raise ValueError("--year is required with --venue")
    if venue and canonical_venue(venue) is None:
        raise ValueError(f"unsupported venue: {venue}")


def _venue_mode(client, *, venue, year, max_works) -> tuple:
    canonical = canonical_venue(venue)
    papers, warnings = _paper_search(client, canonical, year, max_works)
    drafts, map_warnings = papers_to_drafts(papers)
    warnings.extend(map_warnings)
    return drafts, warnings


def _authors_mode(client, *, author, author_id, year, max_works, max_authors) -> tuple:
    warnings = []
    profiles = []
    if author_id:
        profiles.append({"authorId": str(author_id).strip(), "name": author or "", "affiliations": [], "homepage": ""})
    else:
        payload = client.get_json(
            _url("/author/search", {"query": author, "limit": str(max_authors), "fields": AUTHOR_FIELDS})
        )
        profiles = list(payload.get("data") or [])
        if len(profiles) > 1:
            warnings.append(
                "semanticscholar: author search returned multiple source ids. "
                "Each id is a separate row; they are not merged by name."
            )
        profiles = profiles[:max_authors]
    drafts = []
    if not profiles:
        warnings.append("semanticscholar: author search returned no author id.")
        return [], warnings
    for profile in profiles:
        author_short = str(profile.get("authorId") or "").strip()
        if not author_short:
            continue
        papers, page_warnings = _author_papers(client, author_short, year, max_works)
        warnings.extend(page_warnings)
        author_drafts, map_warnings = papers_to_drafts(
            papers,
            only_author_id=author_short,
            profile=profile,
        )
        warnings.extend(map_warnings)
        drafts.extend(author_drafts)
    return drafts, warnings


def _paper_search(client, canonical: str, year: int, max_works: int) -> tuple:
    longest = max(VENUE_NAMES.get(canonical, [canonical]), key=len)
    venue_param = canonical if longest.casefold() == canonical.casefold() else f"{canonical},{longest}"
    papers = []
    warnings = []
    seen = set()
    offset = 0
    for _page in range(MAX_PAGES):
        limit = min(100, max_works - len(papers))
        payload = client.get_json(
            _url(
                "/paper/search",
                {
                    "query": canonical,
                    "venue": venue_param,
                    "year": str(year),
                    "limit": str(limit),
                    "offset": str(offset),
                    "fields": PAPER_FIELDS,
                },
            )
        )
        batch = payload.get("data") or []
        if not isinstance(batch, list):
            raise ValueError("semanticscholar response data must be a list")
        for paper in batch:
            paper_id = paper.get("paperId")
            if paper_id in seen:
                continue
            seen.add(paper_id)
            papers.append(paper)
            if len(papers) >= max_works:
                return papers, warnings
        nxt = payload.get("next")
        if not batch or nxt is None:
            break
        offset = int(nxt)
    else:
        warnings.append(f"semanticscholar: stopped after {MAX_PAGES} pages.")
    return papers, warnings


def _author_papers(client, author_id: str, year: Optional[int], max_works: int) -> tuple:
    papers = []
    warnings = []
    seen = set()
    offset = 0
    for _page in range(MAX_PAGES):
        limit = min(100, max_works - len(papers))
        payload = client.get_json(
            _url(
                f"/author/{author_id}/papers",
                {"limit": str(limit), "offset": str(offset), "fields": PAPER_FIELDS},
            )
        )
        batch = payload.get("data") or []
        if not isinstance(batch, list):
            raise ValueError("semanticscholar response data must be a list")
        for paper in batch:
            if year is not None and paper.get("year") != year:
                continue
            paper_id = paper.get("paperId")
            if paper_id in seen:
                continue
            seen.add(paper_id)
            papers.append(paper)
            if len(papers) >= max_works:
                return papers, warnings
        nxt = payload.get("next")
        if not batch or nxt is None:
            break
        offset = int(nxt)
    else:
        warnings.append(f"semanticscholar: stopped after {MAX_PAGES} pages.")
    return papers, warnings


def papers_to_drafts(
    papers: list,
    only_author_id: Optional[str] = None,
    profile: Optional[dict] = None,
) -> tuple:
    buckets = {}
    warnings = []
    skipped_venue = 0
    skipped_author = 0
    profile = profile or {}
    profile_id = str(profile.get("authorId") or "").strip()
    profile_affiliations = [item.strip() for item in (profile.get("affiliations") or []) if isinstance(item, str) and item.strip()]
    profile_homepage = personal_homepage(profile.get("homepage"))
    for paper in papers:
        raw_venue, venue = _venue(paper)
        if venue is None:
            skipped_venue += 1
            continue
        title = (paper.get("title") or "").strip()
        year = paper.get("year")
        paper_id = str(paper.get("paperId") or "").strip()
        paper_url = _paper_url(paper, paper_id)
        if not title or not isinstance(year, int) or not paper_id or not paper_url:
            skipped_venue += 1
            continue
        authors = paper.get("authors") or []
        for index, author in enumerate(authors):
            author_short = str(author.get("authorId") or "").strip()
            name = (author.get("name") or "").strip()
            if not author_short or not name:
                skipped_author += 1
                continue
            if only_author_id and author_short != only_author_id:
                continue
            affiliations = [
                item.strip()
                for item in (author.get("affiliations") or [])
                if isinstance(item, str) and item.strip()
            ]
            if author_short == profile_id and not affiliations:
                affiliations = profile_affiliations
            institution = affiliations[0] if affiliations else ""
            homepage = profile_homepage if author_short == profile_id else personal_homepage(author.get("homepage"))
            draft = AuthorDraft(
                source="s2",
                author_id=author_short,
                name=name or (profile.get("name") or ""),
                profile_url=https_url(profile.get("url")) or f"https://www.semanticscholar.org/author/{author_short}",
                institution=institution[:300],
                institution_year=year,
                institution_url=paper_url if institution else "",
                institution_excerpt=(
                    f"Semantic Scholar affiliation: {institution}" if institution else ""
                )[:500],
                homepage=homepage,
                publications=[
                    PublicationDraft(
                        source_id=f"s2:{paper_id}",
                        title=title,
                        year=year,
                        venue=venue,
                        category=authorship_category(raw_venue, index == 0),
                        url=paper_url,
                    )
                ],
            )
            remember_author(buckets, draft)
    if skipped_venue:
        warnings.append(
            f"semanticscholar: skipped {skipped_venue} papers with unsupported or incomplete venue metadata."
        )
    if skipped_author:
        warnings.append(
            f"semanticscholar: skipped {skipped_author} authors that had no stable author id."
        )
    return list(buckets.values()), warnings


def _venue(paper: dict) -> tuple:
    publication_venue = paper.get("publicationVenue") or {}
    texts = []
    for candidate in (paper.get("venue"), publication_venue.get("name")):
        if isinstance(candidate, str) and candidate.strip():
            texts.append(candidate.strip())
    for candidate in publication_venue.get("alternate_names") or []:
        if isinstance(candidate, str) and candidate.strip():
            texts.append(candidate.strip())
    canonical = None
    for text in texts:
        canonical = canonical_venue(text)
        if canonical:
            break
    if canonical is None:
        return "", None
    raw = next((text for text in texts if authorship_category(text, True) != "main_first"), texts[0])
    return raw, canonical


def _paper_url(paper: dict, paper_id: str) -> str:
    open_access = paper.get("openAccessPdf") or {}
    pdf = https_url(open_access.get("url") if isinstance(open_access, dict) else "")
    if pdf:
        return pdf
    external = paper.get("externalIds") or {}
    arxiv = external.get("ArXiv") or external.get("arxiv")
    if isinstance(arxiv, str) and arxiv.strip():
        return f"https://arxiv.org/abs/{arxiv.strip()}"
    url = https_url(paper.get("url"))
    if url:
        return url
    doi = external.get("DOI")
    if isinstance(doi, str) and doi.strip():
        if doi.startswith("http://") or doi.startswith("https://"):
            return doi
        return f"https://doi.org/{doi.strip()}"
    if paper_id:
        return f"https://www.semanticscholar.org/paper/{paper_id}"
    return ""


def _url(path: str, params: dict) -> str:
    return f"{API_ROOT}{path}?{urlencode(params)}"
