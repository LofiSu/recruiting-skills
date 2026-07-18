import pytest

from researcher_recruiting.identity import group_evidence, resolve_identity
from researcher_recruiting.models import AuthorSeed, IdentityState


def test_name_only_never_confirms(author_seed, evidence_factory):
    match = resolve_identity(
        author_seed,
        (evidence_factory(field="name", value=author_seed.name),),
        unavailable_sources=(),
    )
    assert match.state is not IdentityState.CONFIRMED


def test_matching_orcid_and_institution_confirms(
    author_seed, evidence_factory
):
    items = (
        evidence_factory(field="orcid", value="0000-0001-2345-6789"),
        evidence_factory(
            field="affiliation", value=author_seed.affiliation
        ),
    )
    match = resolve_identity(author_seed, items, unavailable_sources=())
    assert match.state is IdentityState.CONFIRMED
    assert match.confidence >= 80


def test_conflicting_orcids_force_ambiguous(
    author_seed, evidence_factory
):
    items = (
        evidence_factory(
            candidate_id="a", field="orcid", value="0000-0001"
        ),
        evidence_factory(
            candidate_id="b", field="orcid", value="0000-0002"
        ),
    )
    match = resolve_identity(author_seed, items, unavailable_sources=())
    assert match.state is IdentityState.AMBIGUOUS
    assert "conflicting ORCID" in " ".join(match.reasons)


def test_unavailable_sources_do_not_become_not_found(author_seed):
    match = resolve_identity(
        author_seed, (), unavailable_sources=("orcid", "github")
    )
    assert match.state is IdentityState.AMBIGUOUS
    assert "unavailable" in " ".join(match.reasons).lower()


def test_empty_successful_searches_become_not_found(author_seed):
    match = resolve_identity(author_seed, (), unavailable_sources=())
    assert match.state is IdentityState.NOT_FOUND


def test_same_doi_copied_by_multiple_indexes_counts_once(
    author_seed, evidence_factory
):
    items = (
        evidence_factory(
            source="openalex",
            field="doi",
            value="https://doi.org/10.1000/SHARED",
        ),
        evidence_factory(
            source="crossref", field="doi", value="10.1000/shared"
        ),
        evidence_factory(
            source="semantic_scholar",
            field="doi",
            value="doi:10.1000/shared",
        ),
    )
    match = resolve_identity(author_seed, items, unavailable_sources=())
    assert (
        match.reasons.count("exact paper overlap: 10.1000/shared") == 1
    )


@pytest.mark.parametrize(
    ("seed", "observed"),
    [
        (AuthorSeed(name="Ada Lovelace"), "Lovelace, Ada"),
        (
            AuthorSeed(name="张伟", name_variants=("Wei Zhang",)),
            "Zhang, Wei",
        ),
    ],
)
def test_name_order_and_declared_transliteration_match(
    seed, observed, evidence_factory
):
    match = resolve_identity(
        seed,
        (evidence_factory(field="name", value=observed),),
        unavailable_sources=(),
    )
    assert "name match" in match.reasons


def test_coauthor_paper_and_affiliation_make_probable(
    author_seed, evidence_factory
):
    items = (
        evidence_factory(
            field="coauthor", value=author_seed.coauthors[0]
        ),
        evidence_factory(
            field="paper_title", value=author_seed.paper_title
        ),
        evidence_factory(
            field="affiliation", value=author_seed.affiliation
        ),
    )
    match = resolve_identity(author_seed, items, unavailable_sources=())
    assert match.state in {
        IdentityState.PROBABLE,
        IdentityState.CONFIRMED,
    }
    assert match.confidence >= 50


def test_changed_institution_does_not_score_affiliation(
    author_seed, evidence_factory
):
    match = resolve_identity(
        author_seed,
        (
            evidence_factory(
                field="affiliation", value="Completely Different Lab"
            ),
        ),
        unavailable_sources=(),
    )
    assert not any(
        reason.startswith("affiliation match")
        for reason in match.reasons
    )


def test_shared_strong_identifier_merges_candidate_groups(evidence_factory):
    items = (
        evidence_factory(
            candidate_id="openalex:A1",
            field="orcid",
            value="0000-0001-2345-6789",
        ),
        evidence_factory(
            candidate_id="github:ada",
            field="orcid",
            value="https://orcid.org/0000-0001-2345-6789",
        ),
    )
    groups = group_evidence(items)
    assert len(groups) == 1
    assert len(next(iter(groups.values()))) == 2


def test_tied_plausible_candidates_are_ambiguous(evidence_factory):
    seed = AuthorSeed(name="Ada Lovelace", affiliation="Example Lab")
    items = tuple(
        item
        for candidate in ("candidate:a", "candidate:b")
        for item in (
            evidence_factory(
                candidate_id=candidate,
                field="name",
                value="Ada Lovelace",
            ),
            evidence_factory(
                candidate_id=candidate,
                field="affiliation",
                value="Example Lab",
            ),
            evidence_factory(
                candidate_id=candidate,
                field="doi",
                value=f"10.1000/{candidate[-1]}",
            ),
        )
    )
    match = resolve_identity(seed, items, unavailable_sources=())
    assert match.state is IdentityState.AMBIGUOUS
    assert "tied plausible candidates" in match.reasons
