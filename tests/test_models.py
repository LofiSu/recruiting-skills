from dataclasses import FrozenInstanceError

import pytest

from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactPoint,
    ContactStatus,
    Evidence,
    IdentityMatch,
    IdentityState,
    SourceResult,
    SourceStatus,
)


def test_author_seed_requires_name_and_coauthors_are_immutable():
    seed = AuthorSeed(name="Yann LeCun", coauthors=("Geoffrey Hinton",))
    assert seed.name == "Yann LeCun"
    assert seed.coauthors == ("Geoffrey Hinton",)


def test_evidence_has_provenance_and_collection_time():
    item = Evidence(
        source="orcid",
        field="orcid",
        value="0000-0001-2345-6789",
        url="https://orcid.org/0000-0001-2345-6789",
        collected_at="2026-07-18T00:00:00Z",
    )
    assert item.url.startswith("https://")
    assert IdentityState.CONFIRMED.value == "confirmed"


def test_contact_point_is_frozen_and_keeps_structured_provenance():
    evidence = Evidence(
        source="orcid",
        field="email",
        value="ada@example.org",
        url="https://orcid.org/0000",
        collected_at="2026-07-19T00:00:00Z",
    )
    point = ContactPoint(
        kind=ContactKind.PROFESSIONAL_EMAIL,
        value="ada@example.org",
        source="orcid",
        source_url=evidence.url,
        collected_at=evidence.collected_at,
        confidence=70,
        direct=True,
        evidence=(evidence,),
        metadata={"visibility": "public_professional"},
    )

    assert point.evidence == (evidence,)
    with pytest.raises(FrozenInstanceError):
        point.value = "other@example.org"


def test_extended_models_keep_backward_compatible_contact_defaults():
    source_result = SourceResult("github", SourceStatus.NOT_FOUND)
    identity_match = IdentityMatch(
        author=AuthorSeed(name="Ada Lovelace"),
        state=IdentityState.NOT_FOUND,
        confidence=0,
        reasons=(),
        evidence=(),
    )

    assert source_result.author_name is None
    assert identity_match.contact_status is ContactStatus.NOT_FOUND
    assert identity_match.contact_points == ()
