from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class SourceStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"


class IdentityState(str, Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


class ContactKind(str, Enum):
    PROFESSIONAL_EMAIL = "professional_email"
    CONTACT_FORM = "contact_form"
    HOMEPAGE = "homepage"
    GITHUB = "github"
    OPENREVIEW = "openreview"
    GOOGLE_SCHOLAR_LOCATOR = "google_scholar_locator"
    LINKEDIN_LOCATOR = "linkedin_locator"
    MAIMAI_LOCATOR = "maimai_locator"


class ContactStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    SOURCES_UNAVAILABLE = "sources_unavailable"


@dataclass(frozen=True)
class AuthorSeed:
    name: str
    name_variants: tuple[str, ...] = ()
    affiliation: str | None = None
    email: str | None = None
    coauthors: tuple[str, ...] = ()
    paper_title: str | None = None
    research_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperRecord:
    arxiv_id: str
    title: str
    abstract: str
    submitted_at: str | None
    categories: tuple[str, ...]
    authors: tuple[AuthorSeed, ...]
    source_url: str


@dataclass(frozen=True)
class Evidence:
    source: str
    field: str
    value: str
    url: str
    collected_at: str
    candidate_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ContactPoint:
    kind: ContactKind
    value: str
    source: str
    source_url: str
    collected_at: str
    confidence: int
    direct: bool
    evidence: tuple[Evidence, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceResult:
    source: str
    status: SourceStatus
    evidence: tuple[Evidence, ...] = ()
    error: str | None = None
    author_name: str | None = None


@dataclass(frozen=True)
class IdentityMatch:
    author: AuthorSeed
    state: IdentityState
    confidence: int
    reasons: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    contact_status: ContactStatus = ContactStatus.NOT_FOUND
    contact_points: tuple[ContactPoint, ...] = ()


@dataclass(frozen=True)
class RunResult:
    paper: PaperRecord
    matches: tuple[IdentityMatch, ...]
    source_results: tuple[SourceResult, ...]
