from dataclasses import replace

from researcher_recruiting.models import (
    ContactKind,
    ContactPoint,
    ContactStatus,
    IdentityMatch,
    IdentityState,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.search_links import build_locator_links
from researcher_recruiting.sources.base import collected_at

_FIELD_KINDS = {
    "email": ContactKind.PROFESSIONAL_EMAIL,
    "contact_form": ContactKind.CONTACT_FORM,
    "homepage": ContactKind.HOMEPAGE,
    "github": ContactKind.GITHUB,
    "openreview": ContactKind.OPENREVIEW,
}
_LOCATOR_KINDS = {
    "google_scholar": ContactKind.GOOGLE_SCHOLAR_LOCATOR,
    "linkedin": ContactKind.LINKEDIN_LOCATOR,
    "maimai": ContactKind.MAIMAI_LOCATOR,
}
_DIRECT_SOURCE_NAMES = {"github", "openreview", "orcid", "public_web"}
_UNAVAILABLE = {
    SourceStatus.SOURCE_UNAVAILABLE,
    SourceStatus.BLOCKED_BY_ROBOTS,
}


def _normalized(kind: ContactKind, value: str) -> str:
    value = value.strip()
    if kind is ContactKind.PROFESSIONAL_EMAIL:
        return value.casefold()
    return value.rstrip("/")


def build_contact_points(match: IdentityMatch) -> tuple[ContactPoint, ...]:
    grouped: dict[tuple[ContactKind, str], list] = {}
    identity_is_usable = match.state in {
        IdentityState.CONFIRMED,
        IdentityState.PROBABLE,
    }
    for evidence in match.evidence:
        kind = _FIELD_KINDS.get(evidence.field)
        if kind is None or not evidence.value.strip():
            continue
        value = (
            evidence.url
            if kind in {ContactKind.GITHUB, ContactKind.OPENREVIEW}
            else evidence.value
        )
        normalized = _normalized(kind, value)
        key = (kind, normalized)
        grouped.setdefault(key, []).append(evidence)

    points = []
    for (kind, value), evidence_items in grouped.items():
        first = evidence_items[0]
        direct_kind = kind in {
            ContactKind.PROFESSIONAL_EMAIL,
            ContactKind.CONTACT_FORM,
        }
        points.append(
            ContactPoint(
                kind=kind,
                value=value,
                source=first.source,
                source_url=first.url,
                collected_at=first.collected_at,
                confidence=match.confidence,
                direct=direct_kind and identity_is_usable,
                evidence=tuple(evidence_items),
                metadata={"identity_state": match.state.value},
            )
        )

    locator_timestamp = collected_at()
    locator_links = build_locator_links(match.author)
    for locator_name, kind in _LOCATOR_KINDS.items():
        url = locator_links[locator_name]
        points.append(
            ContactPoint(
                kind=kind,
                value=url,
                source="locator_links",
                source_url=url,
                collected_at=locator_timestamp,
                confidence=0,
                direct=False,
                metadata={"mode": "locator_only"},
            )
        )
    return tuple(points)


def calculate_contact_status(
    match: IdentityMatch,
    points: tuple[ContactPoint, ...],
    source_results: tuple[SourceResult, ...],
) -> ContactStatus:
    verified = [
        point
        for point in points
        if point.kind not in set(_LOCATOR_KINDS.values())
    ]
    if verified and match.state in {
        IdentityState.CONFIRMED,
        IdentityState.PROBABLE,
    }:
        return ContactStatus.FOUND
    if verified or match.state is IdentityState.AMBIGUOUS:
        return ContactStatus.AMBIGUOUS
    applicable = [
        result
        for result in source_results
        if result.source in _DIRECT_SOURCE_NAMES
    ]
    if any(result.status in _UNAVAILABLE for result in applicable):
        return ContactStatus.SOURCES_UNAVAILABLE
    return ContactStatus.NOT_FOUND


def attach_contacts(
    match: IdentityMatch,
    source_results: tuple[SourceResult, ...],
) -> IdentityMatch:
    points = build_contact_points(match)
    return replace(
        match,
        contact_points=points,
        contact_status=calculate_contact_status(
            match,
            points,
            source_results,
        ),
    )
