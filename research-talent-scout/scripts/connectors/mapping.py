"""Map public scholarly metadata into the talent-scout JSONL contract.

Graduation year is never marked confirmed. ``--degree`` is stored as a caller
label so the row can sit in the index; the evidence excerpt says the source
did not provide it. Email addresses are not read, even if a payload contains
them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

try:
    from scripts.import_records import DEGREES, VENUE_ALIASES, _validate
except ModuleNotFoundError:
    from import_records import DEGREES, VENUE_ALIASES, _validate


PROFILE_HOSTS = ("openalex.org", "semanticscholar.org", "api.semanticscholar.org")
_EMAIL = re.compile(r"\b[^\s@/]+@[^\s@/]+\.[^\s@/]+\b")
_WORKSHOP = "workshop"
_FINDINGS = "finding"
_SHORT = "short"
_DEMO = "demo"


@dataclass
class PublicationDraft:
    source_id: str
    title: str
    year: int
    venue: str
    category: str
    url: str


@dataclass
class AuthorDraft:
    source: str
    author_id: str
    name: str
    profile_url: str
    institution: str = ""
    institution_year: int = 0
    institution_url: str = ""
    institution_excerpt: str = ""
    homepage: str = ""
    publications: list = field(default_factory=list)


def canonical_venue(value: str) -> Optional[str]:
    """Return a supported venue, or None when the string is not one of ours.

    Short aliases such as ``SC`` match only as a whole value. Longer official
    names may match inside a proceedings title. Workshop and findings strings
    still resolve when they name a supported conference; category assignment
    is separate and does not treat them as main-conference papers.
    """
    text = " ".join((value or "").split())
    if not text:
        return None
    try:
        return VENUE_ALIASES[text.casefold()]
    except KeyError:
        pass
    folded = text.casefold()
    aliases = sorted(VENUE_ALIASES, key=len, reverse=True)
    for alias in aliases:
        if len(alias) < 8 and " " not in alias:
            continue
        if alias in folded:
            return VENUE_ALIASES[alias]
    return None


def authorship_category(raw_venue: str, is_first: bool) -> str:
    """Classify from the venue string and author position only.

    Equal contribution is not inferred. A non-first author on a main venue
    stays ``unclassified``.
    """
    folded = (raw_venue or "").casefold()
    if _WORKSHOP in folded:
        return "workshop"
    if _FINDINGS in folded:
        return "findings"
    if f" {_SHORT} " in f" {folded} " or folded.endswith(" short"):
        return "short"
    if f" {_DEMO} " in f" {folded} " or folded.endswith(" demo"):
        return "demo"
    if is_first:
        return "main_first"
    return "unclassified"


def strip_emails(value: str) -> str:
    """Remove email-shaped tokens. Connectors do not collect contact addresses."""
    return " ".join(_EMAIL.sub(" ", value or "").split())


def https_url(value: Optional[str]) -> str:
    if not value:
        return ""
    text = value.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return ""


def personal_homepage(value: Optional[str]) -> str:
    """Keep a personal or lab URL. API profile pages are evidence, not homepages."""
    url = https_url(value)
    if not url:
        return ""
    host = (urlparse(url).hostname or "").lower()
    if any(host == blocked or host.endswith("." + blocked) for blocked in PROFILE_HOSTS):
        return ""
    return url


def remember_author(buckets: dict, draft: AuthorDraft) -> AuthorDraft:
    current = buckets.get(draft.author_id)
    if current is None:
        buckets[draft.author_id] = draft
        return draft
    if draft.name and not current.name:
        current.name = draft.name
    if draft.homepage and not current.homepage:
        current.homepage = draft.homepage
    if draft.institution and draft.institution_year >= current.institution_year:
        current.institution = draft.institution
        current.institution_year = draft.institution_year
        current.institution_url = draft.institution_url or current.institution_url
        current.institution_excerpt = draft.institution_excerpt or current.institution_excerpt
    current.publications.extend(draft.publications)
    return current


def to_records(
    drafts: list,
    *,
    degree: str,
    retrieved_at: str,
    graduation_year: Optional[int] = None,
) -> list:
    if degree not in DEGREES:
        raise ValueError(f"unsupported degree: {degree}")
    if not retrieved_at:
        raise ValueError("retrieved_at is required")
    records = []
    for draft in sorted(drafts, key=lambda item: (item.source, item.author_id)):
        publications = _dedupe_publications(draft.publications)
        if not publications or not draft.author_id or not draft.name:
            continue
        institution = strip_emails(draft.institution)
        name = strip_emails(draft.name)
        if not name:
            continue
        year_note = (
            f"Caller supplied graduation year {graduation_year}, which this source does not confirm."
            if graduation_year is not None
            else "The source does not state a graduation year."
        )
        evidence = [
            {
                "field": "graduation_year",
                "state": "unknown",
                "source_type": f"{draft.source}_author",
                "url": draft.profile_url,
                "excerpt": (
                    f"{year_note} Degree label '{degree}' was supplied by the caller "
                    "for indexing and is not a confirmed fact. No email address was collected."
                ),
                "retrieved_at": retrieved_at,
            }
        ]
        if institution and draft.institution_url:
            evidence.append(
                {
                    "field": "institution",
                    "state": "confirmed",
                    "source_type": f"{draft.source}_work",
                    "url": draft.institution_url,
                    "excerpt": strip_emails(draft.institution_excerpt or institution),
                    "retrieved_at": retrieved_at,
                }
            )
        record = {
            "candidate": {
                "id": f"{draft.source}:{draft.author_id}",
                "name": name,
                "degree": degree,
                "institution": institution,
                "lab": "",
                "graduation_year": graduation_year,
                "graduation_state": "unknown",
                "identity_state": "verified",
                "homepage": draft.homepage,
                "verified_at": retrieved_at,
            },
            "publications": publications,
            "evidence": evidence,
        }
        _validate(record)
        records.append(record)
    return records


def caller_warnings(source: str, degree: str, graduation_year: Optional[int]) -> list:
    warnings = [
        (
            f"{source}: degree '{degree}' is a caller-supplied index label, not a fact from the API. "
            "graduation_state is unknown, so these rows are not confirmed graduates."
        ),
        f"{source}: identity_state verified means the row is one source author id, not a hiring check.",
        f"{source}: no email addresses are requested or stored.",
    ]
    if graduation_year is not None:
        warnings.append(
            f"{source}: graduation_year {graduation_year} was supplied by the caller and is not confirmed."
        )
    return warnings


def _dedupe_publications(publications: list) -> list:
    chosen = {}
    for publication in publications:
        chosen.setdefault(publication.source_id, publication)
    rows = []
    for publication in sorted(chosen.values(), key=lambda item: (item.year, item.source_id)):
        rows.append(
            {
                "source_id": publication.source_id,
                "title": strip_emails(publication.title),
                "year": publication.year,
                "venue": publication.venue,
                "category": publication.category,
                "url": publication.url,
            }
        )
    return rows
