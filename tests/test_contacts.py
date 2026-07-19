import pytest

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
    *,
    source="github",
    url="https://example.test/profile",
    visibility="public_professional",
):
    metadata = {}
    if visibility is not None:
        metadata["visibility"] = visibility
    return Evidence(
        source=source,
        field=field,
        value=value,
        url=url,
        collected_at="2026-07-19T00:00:00Z",
        candidate_id="candidate:ada",
        metadata=metadata,
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


@pytest.mark.parametrize(
    ("evidence", "kind", "value", "direct"),
    (
        (
            item("email", " Ada@Example.org ", source="orcid"),
            ContactKind.PROFESSIONAL_EMAIL,
            "ada@example.org",
            True,
        ),
        (
            item(
                "contact_form",
                "https://ada.test/contact/",
                source="public_web",
            ),
            ContactKind.CONTACT_FORM,
            "https://ada.test/contact",
            True,
        ),
        (
            item(
                "homepage",
                "https://ada.test/",
                source="semantic_scholar",
            ),
            ContactKind.HOMEPAGE,
            "https://ada.test",
            False,
        ),
        (
            item(
                "github",
                "ada",
                source="github",
                url="https://github.com/ada",
            ),
            ContactKind.GITHUB,
            "https://github.com/ada",
            False,
        ),
        (
            item(
                "openreview",
                "~Ada_Lovelace1",
                source="openreview",
                url="https://openreview.net/profile?id=~Ada_Lovelace1",
            ),
            ContactKind.OPENREVIEW,
            "https://openreview.net/profile?id=~Ada_Lovelace1",
            False,
        ),
    ),
)
def test_supported_public_evidence_maps_to_contact_points(
    evidence,
    kind,
    value,
    direct,
):
    result = attach_contacts(match(evidence=(evidence,)), ())
    point = next(
        point for point in result.contact_points if point.kind is kind
    )

    assert point.value == value
    assert point.direct is direct
    assert point.evidence == (evidence,)


@pytest.mark.parametrize("field", ("email", "contact_form"))
@pytest.mark.parametrize("visibility", (None, "private", "PUBLIC"))
def test_direct_contact_requires_public_professional_visibility(
    field,
    visibility,
):
    result = attach_contacts(
        match(
            evidence=(
                item(
                    field,
                    "ada@example.org",
                    source="public_web",
                    visibility=visibility,
                ),
            )
        ),
        (),
    )

    assert all(
        point.kind
        not in {
            ContactKind.PROFESSIONAL_EMAIL,
            ContactKind.CONTACT_FORM,
        }
        for point in result.contact_points
    )


@pytest.mark.parametrize(
    "evidence",
    (
        item("email", "ada@example.org", source="private_database"),
        item(
            "contact_form",
            "https://ada.test/contact",
            source="private_database",
        ),
        item(
            "homepage",
            "https://ada.test",
            source="private_database",
        ),
        item(
            "github",
            "ada",
            source="private_database",
            url="https://github.com/ada",
        ),
        item(
            "openreview",
            "~Ada1",
            source="private_database",
            url="https://openreview.net/profile?id=~Ada1",
        ),
    ),
)
def test_contact_fields_from_non_allowlisted_sources_are_suppressed(evidence):
    result = attach_contacts(match(evidence=(evidence,)), ())

    assert all(
        point.kind
        not in {
            ContactKind.PROFESSIONAL_EMAIL,
            ContactKind.CONTACT_FORM,
            ContactKind.HOMEPAGE,
            ContactKind.GITHUB,
            ContactKind.OPENREVIEW,
        }
        for point in result.contact_points
    )


@pytest.mark.parametrize(
    "evidence",
    (
        item("email", "  ", source="orcid"),
        item("contact_form", "\t", source="public_web"),
        item("homepage", "\n", source="semantic_scholar"),
        item("github", "", source="github"),
        item("openreview", "  ", source="openreview"),
        item("phone", "+1-555-0100", source="public_web"),
    ),
)
def test_blank_and_unsupported_evidence_is_suppressed(evidence):
    result = attach_contacts(match(evidence=(evidence,)), ())

    assert len(result.contact_points) == 3
    assert all(point.source == "locator_links" for point in result.contact_points)


def test_contacts_deduplicate_normalized_public_email_and_keep_evidence():
    github_email = item("email", " Ada@Example.org ", source="github")
    orcid_email = item(
        "email",
        "ada@example.org",
        source="orcid",
        url="https://orcid.org/0000",
    )
    result = attach_contacts(
        match(evidence=(github_email, orcid_email)),
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
    assert emails[0].evidence == (github_email, orcid_email)
    assert result.contact_status is ContactStatus.FOUND


def test_non_email_contacts_normalize_and_deduplicate():
    first = item(
        "homepage",
        " https://ada.test/research/ ",
        source="semantic_scholar",
    )
    second = item(
        "homepage",
        "https://ada.test/research",
        source="orcid",
        url="https://orcid.org/0000",
    )
    result = attach_contacts(match(evidence=(first, second)), ())
    homepages = [
        point
        for point in result.contact_points
        if point.kind is ContactKind.HOMEPAGE
    ]

    assert len(homepages) == 1
    assert homepages[0].value == "https://ada.test/research"
    assert homepages[0].evidence == (first, second)


@pytest.mark.parametrize(
    "state",
    (IdentityState.CONFIRMED, IdentityState.PROBABLE),
)
def test_usable_identity_promotes_eligible_direct_contact(state):
    result = attach_contacts(
        match(
            state=state,
            evidence=(item("email", "ada@example.org", source="paper"),),
        ),
        (),
    )
    email = next(
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )

    assert email.direct is True
    assert result.contact_status is ContactStatus.FOUND


def test_ambiguous_identity_does_not_promote_possible_direct_contact():
    result = attach_contacts(
        match(
            state=IdentityState.AMBIGUOUS,
            evidence=(item("email", "ada@example.org", source="orcid"),),
        ),
        (SourceResult("github", SourceStatus.SOURCE_UNAVAILABLE),),
    )
    email = next(
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )

    assert email.direct is False
    assert result.contact_status is ContactStatus.AMBIGUOUS


def test_locator_links_do_not_count_as_found_and_have_utc_timestamps():
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

    assert {point.kind for point in locator_points} == locator_kinds
    assert all(point.direct is False for point in locator_points)
    assert all(
        point.collected_at and point.collected_at.endswith("Z")
        for point in locator_points
    )
    assert result.contact_status is ContactStatus.NOT_FOUND


@pytest.mark.parametrize(
    "source_status",
    (SourceStatus.SOURCE_UNAVAILABLE, SourceStatus.BLOCKED_BY_ROBOTS),
)
@pytest.mark.parametrize(
    "state",
    (IdentityState.NOT_FOUND, IdentityState.AMBIGUOUS),
)
def test_no_contact_with_direct_source_outage_is_sources_unavailable(
    source_status,
    state,
):
    result = attach_contacts(
        match(state=state),
        (
            SourceResult("github", source_status),
            SourceResult("openreview", SourceStatus.NOT_FOUND),
            SourceResult("orcid", SourceStatus.NOT_FOUND),
            SourceResult("public_web", SourceStatus.NOT_FOUND),
        ),
    )

    assert result.contact_status is ContactStatus.SOURCES_UNAVAILABLE


def test_no_contact_true_ambiguity_without_outage_remains_ambiguous():
    result = attach_contacts(
        match(state=IdentityState.AMBIGUOUS),
        (
            SourceResult("github", SourceStatus.NOT_FOUND),
            SourceResult("openreview", SourceStatus.NOT_FOUND),
            SourceResult("orcid", SourceStatus.NOT_FOUND),
            SourceResult("public_web", SourceStatus.NOT_FOUND),
        ),
    )

    assert result.contact_status is ContactStatus.AMBIGUOUS
