import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from researcher_recruiting.models import (
    AuthorSeed,
    Evidence,
    IdentityMatch,
    IdentityState,
)

WEIGHTS = {
    "orcid_exact": 60,
    "institutional_cross_link": 50,
    "email_exact": 45,
    "paper_exact": 25,
    "affiliation_match": 20,
    "coauthor_overlap": 15,
    "email_domain_match": 15,
    "topic_overlap": 10,
    "name_match": 5,
}

CONFIRMED_THRESHOLD = 80
PROBABLE_THRESHOLD = 50
_STRONG_IDENTIFIER_FIELDS = {"orcid", "email", "github"}


@dataclass(frozen=True)
class CandidateScore:
    confidence: int
    reasons: tuple[str, ...]
    categories: frozenset[str]
    strong_categories: frozenset[str]


def _ascii_words(value: str) -> tuple[str, ...]:
    decomposed = unicodedata.normalize("NFKD", value)
    plain = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return tuple(re.findall(r"[a-z0-9]+", plain.casefold()))


def _name_key(value: str) -> tuple[str, ...]:
    return tuple(sorted(_ascii_words(value)))


def _canonical_identifier(field: str, value: str) -> str:
    normalized = value.strip()
    if field == "doi":
        normalized = re.sub(
            r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        return normalized.casefold()
    if field == "orcid":
        return normalized.rstrip("/").rsplit("/", 1)[-1].upper()
    if field == "pmid":
        return normalized.removeprefix("PMID:").strip()
    if field == "openalex":
        return normalized.rstrip("/").rsplit("/", 1)[-1].upper()
    if field == "dblp":
        return normalized.split("/pid/", 1)[-1].removesuffix(".html").strip("/")
    if field == "email":
        return normalized.casefold()
    if field == "github":
        return normalized.rstrip("/").rsplit("/", 1)[-1].casefold()
    return " ".join(_ascii_words(normalized))


def group_evidence(
    items: Iterable[Evidence],
) -> dict[str, tuple[Evidence, ...]]:
    materialized = tuple(items)
    candidate_ids = sorted(
        {
            item.candidate_id
            for item in materialized
            if item.candidate_id is not None
        }
    )
    parent = {candidate_id: candidate_id for candidate_id in candidate_ids}

    def find(candidate_id: str) -> str:
        while parent[candidate_id] != candidate_id:
            parent[candidate_id] = parent[parent[candidate_id]]
            candidate_id = parent[candidate_id]
        return candidate_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            keep, merge = sorted((left_root, right_root))
            parent[merge] = keep

    seen_identifiers: dict[tuple[str, str], str] = {}
    for item in materialized:
        if (
            item.candidate_id is None
            or item.field not in _STRONG_IDENTIFIER_FIELDS
        ):
            continue
        identifier = (
            item.field,
            _canonical_identifier(item.field, item.value),
        )
        existing = seen_identifiers.get(identifier)
        if existing:
            union(existing, item.candidate_id)
        else:
            seen_identifiers[identifier] = item.candidate_id

    grouped: dict[str, list[Evidence]] = {}
    for index, item in enumerate(materialized):
        key = (
            find(item.candidate_id)
            if item.candidate_id is not None
            else f"unscoped:{index}"
        )
        grouped.setdefault(key, []).append(item)
    return {key: tuple(value) for key, value in grouped.items()}


def _matches_affiliation(seed: str, observed: str) -> bool:
    seed_words = set(_ascii_words(seed))
    observed_words = set(_ascii_words(observed))
    if not seed_words or not observed_words:
        return False
    overlap = len(seed_words & observed_words)
    return overlap / min(len(seed_words), len(observed_words)) >= 0.6


def score_candidate(
    seed: AuthorSeed,
    items: Iterable[Evidence],
) -> CandidateScore:
    evidence_items = tuple(items)
    reasons: list[str] = []
    categories: set[str] = set()
    strong_categories: set[str] = set()

    def apply(
        category: str,
        reason: str,
        *,
        strong: bool = False,
    ) -> None:
        if category not in categories:
            categories.add(category)
            if strong:
                strong_categories.add(category)
        if reason not in reasons:
            reasons.append(reason)

    orcids = sorted(
        {
            _canonical_identifier("orcid", item.value)
            for item in evidence_items
            if item.field == "orcid" and item.value.strip()
        }
    )
    if orcids:
        apply("orcid_exact", f"ORCID present: {orcids[0]}", strong=True)

    if any(
        item.field == "institutional_profile"
        or item.metadata.get("institutional_cross_link") is True
        for item in evidence_items
    ):
        apply(
            "institutional_cross_link",
            "institutional profile cross-link",
            strong=True,
        )

    observed_emails = {
        _canonical_identifier("email", item.value)
        for item in evidence_items
        if item.field == "email" and "@" in item.value
    }
    seed_email = seed.email.casefold() if seed.email else None
    if seed_email and seed_email in observed_emails:
        apply("email_exact", f"exact email: {seed_email}", strong=True)

    dois = sorted(
        {
            _canonical_identifier("doi", item.value)
            for item in evidence_items
            if item.field == "doi" and item.value.strip()
        }
    )
    title_keys = {
        _name_key(item.value)
        for item in evidence_items
        if item.field == "paper_title"
    }
    paper_overlap = False
    for doi in dois:
        apply("paper_exact", f"exact paper overlap: {doi}")
        paper_overlap = True
    if seed.paper_title and _name_key(seed.paper_title) in title_keys:
        apply(
            "paper_exact",
            f"exact paper overlap: {seed.paper_title}",
        )
        paper_overlap = True
    if paper_overlap:
        categories.add("paper_exact")

    if seed.affiliation:
        matched_affiliation = next(
            (
                item.value
                for item in evidence_items
                if item.field == "affiliation"
                and _matches_affiliation(seed.affiliation, item.value)
            ),
            None,
        )
        if matched_affiliation:
            apply(
                "affiliation_match",
                f"affiliation match: {matched_affiliation}",
            )

    seed_coauthors = {_name_key(name) for name in seed.coauthors}
    matched_coauthor = next(
        (
            item.value
            for item in evidence_items
            if item.field in {"coauthor", "contributor_name"}
            and _name_key(item.value) in seed_coauthors
        ),
        None,
    )
    if matched_coauthor:
        apply(
            "coauthor_overlap",
            f"coauthor overlap: {matched_coauthor}",
        )

    if seed_email and "@" in seed_email:
        seed_domain = seed_email.rsplit("@", 1)[-1]
        if any(
            email.rsplit("@", 1)[-1] == seed_domain
            for email in observed_emails
        ) and seed_email not in observed_emails:
            apply(
                "email_domain_match",
                f"email domain match: {seed_domain}",
            )

    seed_topics = {_name_key(topic) for topic in seed.research_terms}
    matched_topic = next(
        (
            item.value
            for item in evidence_items
            if item.field == "research_term"
            and _name_key(item.value) in seed_topics
        ),
        None,
    )
    if matched_topic:
        apply("topic_overlap", f"topic overlap: {matched_topic}")

    acceptable_names = {_name_key(seed.name)}
    acceptable_names.update(_name_key(name) for name in seed.name_variants)
    if any(
        item.field in {"name", "name_variant"}
        and _name_key(item.value) in acceptable_names
        for item in evidence_items
    ):
        apply("name_match", "name match")

    confidence = min(
        100, sum(WEIGHTS[category] for category in categories)
    )
    return CandidateScore(
        confidence=confidence,
        reasons=tuple(reasons),
        categories=frozenset(categories),
        strong_categories=frozenset(strong_categories),
    )


def resolve_identity(
    seed: AuthorSeed,
    items: Iterable[Evidence],
    unavailable_sources: Iterable[str],
) -> IdentityMatch:
    evidence_items = tuple(items)
    unavailable = tuple(dict.fromkeys(unavailable_sources))
    if not evidence_items:
        if unavailable:
            return IdentityMatch(
                author=seed,
                state=IdentityState.AMBIGUOUS,
                confidence=0,
                reasons=(
                    "identity sources unavailable: " + ", ".join(unavailable),
                ),
                evidence=(),
            )
        return IdentityMatch(
            author=seed,
            state=IdentityState.NOT_FOUND,
            confidence=0,
            reasons=("no public identity evidence found",),
            evidence=(),
        )

    all_orcids = {
        _canonical_identifier("orcid", item.value)
        for item in evidence_items
        if item.field == "orcid" and item.value.strip()
    }
    groups = group_evidence(evidence_items)
    scored = sorted(
        (
            (score_candidate(seed, group), key, group)
            for key, group in groups.items()
        ),
        key=lambda item: (-item[0].confidence, item[1]),
    )
    best_score, _, best_evidence = scored[0]

    if len(all_orcids) > 1:
        return IdentityMatch(
            author=seed,
            state=IdentityState.AMBIGUOUS,
            confidence=best_score.confidence,
            reasons=best_score.reasons
            + ("conflicting ORCID identifiers",),
            evidence=evidence_items,
        )

    plausible = [
        item
        for item in scored
        if item[0].confidence >= PROBABLE_THRESHOLD
    ]
    if (
        len(plausible) > 1
        and plausible[0][0].confidence == plausible[1][0].confidence
    ):
        return IdentityMatch(
            author=seed,
            state=IdentityState.AMBIGUOUS,
            confidence=best_score.confidence,
            reasons=best_score.reasons + ("tied plausible candidates",),
            evidence=evidence_items,
        )

    non_name_categories = best_score.categories - {"name_match"}
    can_confirm = bool(best_score.strong_categories) or (
        len(non_name_categories) >= 3
    )
    if (
        best_score.confidence >= CONFIRMED_THRESHOLD
        and can_confirm
    ):
        state = IdentityState.CONFIRMED
    elif (
        best_score.confidence >= PROBABLE_THRESHOLD
        and non_name_categories
    ):
        state = IdentityState.PROBABLE
    else:
        state = IdentityState.AMBIGUOUS
    reasons = best_score.reasons
    if unavailable:
        reasons += (
            "additional sources unavailable: " + ", ".join(unavailable),
        )
    return IdentityMatch(
        author=seed,
        state=state,
        confidence=best_score.confidence,
        reasons=reasons,
        evidence=best_evidence,
    )
