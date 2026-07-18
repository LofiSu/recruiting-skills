from researcher_recruiting.models import AuthorSeed, Evidence, IdentityState


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
