"""Fetch OpenAlex works and authors into talent-scout records.

Public metadata only: ``/sources``, ``/works``, and ``/authors``. This client
does not call the content or PDF endpoints.

Authentication and pace
-----------------------
Set ``OPENALEX_API_KEY``. Send it as ``Authorization: Bearer`` and never on
the query string. A free key allows 30 requests/second and about 100,000
credits/day; list calls cost about 10 credits. Without a key the API allows
only a small daily budget and rejects cursor paging, so this client requests
a single page and warns.

The default CLI pause is 0.2 seconds (5 requests/second), under both the
keyless cap of 10 requests/second and the free-key cap of 30.
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
        remember_author,
        to_records,
    )
    from import_records import VENUE_NAMES


API_ROOT = "https://api.openalex.org"
WORK_SELECT = "id,display_name,title,publication_year,doi,ids,primary_location,authorships,open_access"
AUTHOR_SELECT = "id,display_name,orcid,last_known_institutions"
MAX_PAGES = 10


def fetch_openalex(
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
    warnings = caller_warnings("openalex", degree, graduation_year)
    if not api_key_present:
        warnings.append(
            "OPENALEX_API_KEY is unset. OpenAlex expects a free key; the keyless "
            "budget is only enough for a few test calls, and cursor paging is disabled. "
            "This run requests one page."
        )
    if author_id or author:
        drafts, fetch_warnings = _authors_mode(
            client,
            author=author,
            author_id=author_id,
            year=year,
            max_works=max_works,
            max_authors=max_authors,
            api_key_present=api_key_present,
        )
    else:
        drafts, fetch_warnings = _venue_mode(
            client,
            venue=venue,
            year=year,
            max_works=max_works,
            api_key_present=api_key_present,
        )
    warnings.extend(fetch_warnings)
    records = to_records(
        drafts,
        degree=degree,
        retrieved_at=retrieved_at,
        graduation_year=graduation_year,
    )
    if not records:
        warnings.append("openalex: no importable records. Unsupported venues and authors without an id are skipped.")
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


def _venue_mode(client, *, venue, year, max_works, api_key_present) -> tuple:
    canonical = canonical_venue(venue)
    source_ids, warnings = _resolve_source_ids(client, canonical)
    if not source_ids:
        warnings.append(f"openalex: no source matched venue {canonical}.")
        return [], warnings
    params = {
        "filter": f"primary_location.source.id:{'|'.join(source_ids)},publication_year:{year}",
        "per-page": str(min(max_works, 50)),
        "select": WORK_SELECT,
    }
    works, page_warnings = _paginate(client, "/works", params, max_works, api_key_present)
    warnings.extend(page_warnings)
    drafts, map_warnings = works_to_drafts(works)
    warnings.extend(map_warnings)
    return drafts, warnings


def _authors_mode(client, *, author, author_id, year, max_works, max_authors, api_key_present) -> tuple:
    warnings = []
    if author_id:
        identities = [_short_id(author_id, "A")]
    else:
        payload = client.get_json(
            _url("/authors", {"search": author, "per-page": str(max_authors), "select": AUTHOR_SELECT})
        )
        identities = []
        for item in payload.get("results") or []:
            short = _short_id((item.get("id") or ""), "A")
            if short:
                identities.append(short)
        if len(identities) > 1:
            warnings.append(
                "openalex: author search returned multiple source ids. "
                "Each id is a separate row; they are not merged by name."
            )
        identities = identities[:max_authors]
        if not identities:
            warnings.append("openalex: author search returned no author id.")
            return [], warnings
    drafts = []
    for short in identities:
        params = {
            "filter": f"authorships.author.id:{short}",
            "per-page": str(min(max_works, 50)),
            "select": WORK_SELECT,
        }
        if year is not None:
            params["filter"] += f",publication_year:{year}"
        works, page_warnings = _paginate(client, "/works", params, max_works, api_key_present)
        warnings.extend(page_warnings)
        author_drafts, map_warnings = works_to_drafts(works, only_author_id=short)
        warnings.extend(map_warnings)
        drafts.extend(author_drafts)
    return drafts, warnings


def _resolve_source_ids(client, canonical: str) -> tuple:
    queries = [canonical]
    longest = max(VENUE_NAMES.get(canonical, [canonical]), key=len)
    if longest.casefold() != canonical.casefold():
        queries.append(longest)
    found = []
    warnings = []
    for query in queries:
        payload = client.get_json(_url("/sources", {"search": query, "per-page": "25"}))
        for source in payload.get("results") or []:
            names = [source.get("display_name") or ""]
            names.extend(source.get("alternate_titles") or [])
            if any(canonical_venue(name) == canonical for name in names):
                short = _short_id(source.get("id") or "", "S")
                if short and short not in found:
                    found.append(short)
        if found:
            break
    if len(found) > 20:
        warnings.append("openalex: truncated source id list to 20 matches.")
        found = found[:20]
    return found, warnings


def _paginate(client, path: str, params: dict, max_works: int, api_key_present: bool) -> tuple:
    works = []
    warnings = []
    seen = set()
    cursor = "*"
    for page in range(MAX_PAGES):
        query = dict(params)
        if api_key_present:
            query["cursor"] = cursor
        else:
            query["page"] = "1"
        payload = client.get_json(_url(path, query))
        batch = payload.get("results") or []
        if not isinstance(batch, list):
            raise ValueError("openalex response results must be a list")
        for work in batch:
            work_id = work.get("id")
            if work_id in seen:
                continue
            seen.add(work_id)
            works.append(work)
            if len(works) >= max_works:
                return works, warnings
        if not api_key_present:
            meta = payload.get("meta") or {}
            if meta.get("next_cursor"):
                warnings.append(
                    "openalex: stopped after the first page because OPENALEX_API_KEY is unset."
                )
            break
        cursor = (payload.get("meta") or {}).get("next_cursor")
        if not cursor or not batch:
            break
    else:
        warnings.append(f"openalex: stopped after {MAX_PAGES} pages.")
    return works, warnings


def works_to_drafts(works: list, only_author_id: Optional[str] = None) -> tuple:
    buckets = {}
    warnings = []
    skipped_venue = 0
    skipped_author = 0
    for work in works:
        raw_venue = _venue_name(work)
        venue = canonical_venue(raw_venue)
        if venue is None:
            skipped_venue += 1
            continue
        year = work.get("publication_year")
        title = (work.get("title") or work.get("display_name") or "").strip()
        work_short = _short_id(work.get("id") or "", "W")
        work_url = _work_url(work, work_short)
        if not title or not isinstance(year, int) or not work_short or not work_url:
            skipped_venue += 1
            continue
        authorships = work.get("authorships") or []
        for index, authorship in enumerate(authorships):
            author = authorship.get("author") or {}
            author_short = _short_id(author.get("id") or "", "A")
            name = (author.get("display_name") or "").strip()
            if not author_short or not name:
                skipped_author += 1
                continue
            if only_author_id and author_short != only_author_id:
                continue
            is_first = authorship.get("author_position") == "first" or (
                authorship.get("author_position") is None and index == 0
            )
            institution, excerpt = _institution(authorship)
            draft = AuthorDraft(
                source="openalex",
                author_id=author_short,
                name=name,
                profile_url=f"https://openalex.org/{author_short}",
                institution=institution,
                institution_year=year,
                institution_url=work_url if institution else "",
                institution_excerpt=excerpt,
                homepage="",
                publications=[
                    PublicationDraft(
                        source_id=f"openalex:{work_short}",
                        title=title,
                        year=year,
                        venue=venue,
                        category=authorship_category(raw_venue, is_first),
                        url=work_url,
                    )
                ],
            )
            remember_author(buckets, draft)
    if skipped_venue:
        warnings.append(f"openalex: skipped {skipped_venue} works with unsupported or incomplete venue metadata.")
    if skipped_author:
        warnings.append(f"openalex: skipped {skipped_author} authorships that had no stable author id.")
    return list(buckets.values()), warnings


def _venue_name(work: dict) -> str:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    return source.get("display_name") or ""


def _institution(authorship: dict) -> tuple:
    raw = authorship.get("raw_affiliation_strings") or []
    raw_text = next((item.strip() for item in raw if isinstance(item, str) and item.strip()), "")
    institutions = authorship.get("institutions") or []
    display = ""
    if institutions and isinstance(institutions[0], dict):
        display = (institutions[0].get("display_name") or "").strip()
    institution = raw_text or display
    if not institution:
        return "", ""
    excerpt = f"OpenAlex authorship affiliation: {institution}"
    if raw_text and display and raw_text != display:
        excerpt = f"OpenAlex raw affiliation: {raw_text}. Institution display name: {display}."
    return institution[:300], excerpt[:500]


def _work_url(work: dict, work_short: str) -> str:
    location = work.get("primary_location") or {}
    open_access = work.get("open_access") or {}
    for candidate in (
        location.get("landing_page_url"),
        open_access.get("oa_url"),
        work.get("doi"),
    ):
        url = https_url(candidate)
        if url:
            return url
    if work_short:
        return f"https://openalex.org/{work_short}"
    return ""


def _short_id(value: str, prefix: str) -> str:
    text = (value or "").rstrip("/").split("/")[-1].strip()
    if text.startswith(prefix) and len(text) > 1:
        return text
    return ""


def _url(path: str, params: dict) -> str:
    return f"{API_ROOT}{path}?{urlencode(params)}"
