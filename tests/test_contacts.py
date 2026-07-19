from researcher_recruiting.contacts import attach_contacts
from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactStatus,
    Evidence,
    IdentityMatch,
    IdentityState,
    SourceResult,
    SourceStatus,
)


def item(
    field,
    value,
    source="github",
    url="https://example.test/profile",
):
    return Evidence(
        source=source,
        field=field,
        value=value,
        url=url,
        collected_at="2026-07-19T00:00:00Z",
        candidate_id="candidate:ada",
        metadata={"visibility": "public_professional"},
    )


def match(state=IdentityState.PROBABLE, evidence=()):
    return IdentityMatch(
        author=AuthorSeed(
            name="Ada Lovelace",
            affiliation="Analytical Engines",
        ),
        state=state,
        confidence=70,
        reasons=("paper overlap",),
        evidence=tuple(evidence),
    )


def test_contacts_deduplicate_normalized_public_email_and_keep_evidence():
    result = attach_contacts(
        match(
            evidence=(
                item("email", " Ada@Example.org "),
                item(
                    "email",
                    "ada@example.org",
                    source="orcid",
                    url="https://orcid.org/0000",
                ),
            )
        ),
        (
            SourceResult("github", SourceStatus.OK),
            SourceResult("orcid", SourceStatus.OK),
        ),
    )
    emails = [
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    ]
    assert len(emails) == 1
    assert emails[0].value == "ada@example.org"
    assert len(emails[0].evidence) == 2
    assert emails[0].direct is True
    assert result.contact_status is ContactStatus.FOUND


def test_ambiguous_identity_does_not_promote_direct_contact():
    result = attach_contacts(
        match(
            state=IdentityState.AMBIGUOUS,
            evidence=(item("email", "ada@example.org"),),
        ),
        (SourceResult("github", SourceStatus.OK),),
    )
    email = next(
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )
    assert email.direct is False
    assert result.contact_status is ContactStatus.AMBIGUOUS


def test_locator_links_do_not_count_as_found():
    result = attach_contacts(
        match(state=IdentityState.NOT_FOUND),
        (
            SourceResult("github", SourceStatus.NOT_FOUND),
            SourceResult("openreview", SourceStatus.NOT_FOUND),
            SourceResult("orcid", SourceStatus.NOT_FOUND),
            SourceResult("public_web", SourceStatus.NOT_FOUND),
        ),
    )
    locator_kinds = {
        ContactKind.GOOGLE_SCHOLAR_LOCATOR,
        ContactKind.LINKEDIN_LOCATOR,
        ContactKind.MAIMAI_LOCATOR,
    }
    locator_points = [
        point
        for point in result.contact_points
        if point.kind in locator_kinds
    ]
    assert locator_kinds <= {point.kind for point in locator_points}
    assert all(
        point.collected_at and point.collected_at.endswith("Z")
        for point in locator_points
    )
    assert result.contact_status is ContactStatus.NOT_FOUND


def test_unavailable_direct_source_is_distinct_from_not_found():
    result = attach_contacts(
        match(state=IdentityState.NOT_FOUND),
        (
            SourceResult("github", SourceStatus.SOURCE_UNAVAILABLE),
            SourceResult("openreview", SourceStatus.NOT_FOUND),
            SourceResult("orcid", SourceStatus.NOT_FOUND),
            SourceResult("public_web", SourceStatus.NOT_FOUND),
        ),
    )
    assert result.contact_status is ContactStatus.SOURCES_UNAVAILABLE
