import pytest

from researcher_recruiting.contacts import attach_contacts
from researcher_recruiting.crawling import FetchResult
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
from researcher_recruiting.sources.github import GitHubSource
from researcher_recruiting.sources.orcid import OrcidSource
from researcher_recruiting.sources.public_web import PublicWebSource
from tests.helpers import StubCrawler


class StaticTokenProvider:
    async def get_token(self, client_id, client_secret):
        return "public-token"


def fetched(url, body, content_type="application/json"):
    return FetchResult(
        SourceStatus.OK,
        url,
        200,
        content_type,
        body.encode(),
        False,
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
                    source="paper",
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


@pytest.mark.parametrize("source", ("github", "orcid"))
def test_sources_that_only_prove_public_email_do_not_prove_contact_form(
    source,
):
    result = attach_contacts(
        match(
            evidence=(
                item(
                    "contact_form",
                    "https://ada.test/contact",
                    source=source,
                    visibility=None,
                ),
            )
        ),
        (),
    )

    assert all(
        point.kind is not ContactKind.CONTACT_FORM
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


@pytest.mark.asyncio
async def test_github_source_contacts_keep_public_email_and_profile_url(
    load_fixture,
):
    search_url = "https://api.github.com/search/users"
    api_profile_url = "https://api.github.com/users/ada"
    crawler = StubCrawler(
        {
            search_url: [
                fetched(
                    search_url,
                    load_fixture("github_user_search.json"),
                )
            ],
            api_profile_url: [
                fetched(
                    api_profile_url,
                    load_fixture("github_user.json"),
                )
            ],
        }
    )
    enriched = await GitHubSource(crawler, token=None).enrich(
        AuthorSeed(name="Ada Lovelace")
    )

    result = attach_contacts(match(evidence=enriched.evidence), (enriched,))
    routes = {point.kind: point for point in result.contact_points}

    assert routes[ContactKind.PROFESSIONAL_EMAIL].value == "ada@example.org"
    assert routes[ContactKind.PROFESSIONAL_EMAIL].direct is True
    assert routes[ContactKind.GITHUB].value == "https://github.com/ada"


@pytest.mark.asyncio
async def test_orcid_source_contacts_keep_api_public_email(load_fixture):
    search_url = "https://pub.orcid.org/v3.0/search/"
    record_url = (
        "https://pub.orcid.org/v3.0/0000-0001-2345-6789/record"
    )
    crawler = StubCrawler(
        {
            search_url: [
                fetched(
                    search_url,
                    load_fixture("orcid_search.json"),
                    "application/vnd.orcid+json",
                )
            ],
            record_url: [
                fetched(
                    record_url,
                    load_fixture("orcid_record.json"),
                    "application/vnd.orcid+json",
                )
            ],
        }
    )
    enriched = await OrcidSource(
        crawler,
        StaticTokenProvider(),
        "client-id",
        "client-secret",
    ).enrich(AuthorSeed(name="Ada Lovelace"))

    result = attach_contacts(match(evidence=enriched.evidence), (enriched,))
    email = next(
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )

    assert email.value == "ada@example.org"
    assert email.direct is True


@pytest.mark.asyncio
async def test_public_web_source_contacts_keep_mailto_and_real_profile_url(
    load_fixture,
):
    homepage_url = "https://university.example/~ada/"
    crawler = StubCrawler(
        {
            homepage_url: [
                fetched(
                    homepage_url,
                    load_fixture("public_homepage.html"),
                    "text/html",
                )
            ]
        }
    )
    enriched = await PublicWebSource(crawler).enrich_urls((homepage_url,))

    result = attach_contacts(match(evidence=enriched.evidence), (enriched,))
    routes = {point.kind: point for point in result.contact_points}

    assert (
        routes[ContactKind.PROFESSIONAL_EMAIL].value
        == "ada@university.example"
    )
    assert (
        routes[ContactKind.OPENREVIEW].value
        == "https://openreview.net/profile?id=~Ada_Lovelace1"
    )
    assert ContactKind.GITHUB not in routes


@pytest.mark.parametrize(
    ("field", "kind", "value"),
    (
        (
            "github",
            ContactKind.GITHUB,
            "https://github.com/ada",
        ),
        (
            "openreview",
            ContactKind.OPENREVIEW,
            "https://openreview.net/profile?id=~Ada_Lovelace1",
        ),
    ),
)
def test_cross_link_profile_routes_use_absolute_evidence_value(
    field,
    kind,
    value,
):
    result = attach_contacts(
        match(
            evidence=(
                item(
                    field,
                    value,
                    source="public_web",
                    url="https://university.example/~ada/",
                ),
            )
        ),
        (),
    )

    point = next(
        point for point in result.contact_points if point.kind is kind
    )
    assert point.value == value


@pytest.mark.parametrize(
    ("field", "value"),
    (("github", "ada"), ("openreview", "~Ada_Lovelace1")),
)
def test_cross_link_profile_ids_without_route_are_suppressed(field, value):
    result = attach_contacts(
        match(
            evidence=(
                item(
                    field,
                    value,
                    source="public_web",
                    url="https://university.example/~ada/",
                ),
            )
        ),
        (),
    )

    assert all(
        point.kind not in {ContactKind.GITHUB, ContactKind.OPENREVIEW}
        for point in result.contact_points
    )
