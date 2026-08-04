#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Dict, Optional, Tuple

try:
    from scripts.import_records import CATEGORIES, VENUE_ALIASES
    from scripts.init_index import connect, initialize
except ModuleNotFoundError:
    from import_records import CATEGORIES, VENUE_ALIASES
    from init_index import connect, initialize


CANONICAL_VENUES = frozenset(VENUE_ALIASES.values())
GRADUATION_STATES = frozenset(
    {"confirmed", "likely_needs_verification", "unknown", "stale", "conflict"}
)


@dataclass(frozen=True)
class Query:
    graduation_years: Tuple[int, ...]
    degree_thresholds: Dict[str, int]
    venues: Tuple[str, ...]
    categories: Tuple[str, ...]
    graduation_states: Tuple[str, ...]
    strictly_greater: bool = False
    institutions: Tuple[str, ...] = ()
    max_evidence_age_days: Optional[int] = 365


def _validate(query: Query) -> None:
    unsupported_venues = set(query.venues) - CANONICAL_VENUES
    if unsupported_venues:
        raise ValueError(f"unsupported venue: {sorted(unsupported_venues)[0]}")
    unsupported_categories = set(query.categories) - CATEGORIES
    if unsupported_categories:
        raise ValueError(f"unsupported category: {sorted(unsupported_categories)[0]}")
    unsupported_states = set(query.graduation_states) - GRADUATION_STATES
    if unsupported_states:
        raise ValueError(f"unsupported graduation state: {sorted(unsupported_states)[0]}")
    if set(query.degree_thresholds) - {"phd", "masters"}:
        raise ValueError("degree thresholds support only phd and masters")


def _placeholders(values) -> str:
    return ",".join("?" for _ in values)


def query_candidates(connection, query: Query) -> dict:
    _validate(query)
    if not query.graduation_years or not query.venues or not query.categories:
        return _empty_result(connection, ["Query contains an empty required filter."])

    candidate_sql = f"""
        SELECT * FROM candidates
        WHERE graduation_year IN ({_placeholders(query.graduation_years)})
          AND graduation_state IN ({_placeholders(query.graduation_states)})
    """
    params = list(query.graduation_years) + list(query.graduation_states)
    if query.institutions:
        candidate_sql += f" AND institution IN ({_placeholders(query.institutions)})"
        params.extend(query.institutions)

    confirmed = []
    inferred = []
    warnings = []
    for candidate in connection.execute(candidate_sql, params).fetchall():
        if candidate["identity_state"] != "verified":
            warnings.append(f"Excluded ambiguous identity: {candidate['id']}")
            continue
        publication_sql = f"""
            SELECT p.source_id, p.title, p.year, p.normalized_venue, p.url, a.category
            FROM authorships a
            JOIN publications p ON p.source_id = a.publication_id
            WHERE a.candidate_id = ?
              AND p.normalized_venue IN ({_placeholders(query.venues)})
              AND a.category IN ({_placeholders(query.categories)})
            ORDER BY p.year DESC, p.title, p.source_id
        """
        publications = connection.execute(
            publication_sql,
            [candidate["id"], *query.venues, *query.categories],
        ).fetchall()
        threshold = query.degree_thresholds.get(candidate["degree"])
        if threshold is None:
            continue
        qualifies = len(publications) > threshold if query.strictly_greater else len(publications) >= threshold
        if not qualifies:
            continue
        counts = {category: 0 for category in query.categories}
        for publication in publications:
            counts[publication["category"]] += 1
        evidence = [
            dict(row)
            for row in connection.execute(
                """SELECT field, state, source_type, url, excerpt, retrieved_at
                FROM evidence WHERE candidate_id = ? ORDER BY retrieved_at DESC, id DESC""",
                (candidate["id"],),
            ).fetchall()
        ]
        effective_graduation_state = candidate["graduation_state"]
        graduation_evidence = [item for item in evidence if item["field"] == "graduation_year"]
        if query.max_evidence_age_days is not None and graduation_evidence:
            newest_date = max(date.fromisoformat(item["retrieved_at"][:10]) for item in graduation_evidence)
            if (date.today() - newest_date).days > query.max_evidence_age_days:
                effective_graduation_state = "stale"
                warnings.append(f"Graduation evidence is stale: {candidate['id']}")
        item = {
            "candidate_id": candidate["id"],
            "name": candidate["name"],
            "degree": candidate["degree"],
            "institution": candidate["institution"],
            "lab": candidate["lab"],
            "homepage": candidate["homepage"],
            "graduation_year": candidate["graduation_year"],
            "graduation_state": effective_graduation_state,
            "identity_state": candidate["identity_state"],
            "verified_at": candidate["verified_at"],
            "qualifying_count": len(publications),
            "counts_by_category": counts,
            "qualifying_publications": [dict(row) for row in publications],
            "evidence": evidence,
        }
        target = confirmed if effective_graduation_state == "confirmed" else inferred
        target.append(item)

    sort_key = lambda row: (-row["qualifying_count"], row["name"].casefold(), row["candidate_id"])
    confirmed.sort(key=sort_key)
    inferred.sort(key=sort_key)
    coverage = [dict(row) for row in connection.execute("SELECT * FROM coverage ORDER BY scope").fetchall()]
    if not coverage:
        warnings.append("Index coverage metadata is empty; absence of results is not proof of no candidates.")
    return {
        "confirmed": confirmed,
        "likely_needs_verification": inferred,
        "coverage": coverage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
    }


def _empty_result(connection, warnings):
    coverage = [dict(row) for row in connection.execute("SELECT * FROM coverage ORDER BY scope").fetchall()]
    return {
        "confirmed": [],
        "likely_needs_verification": [],
        "coverage": coverage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
    }


def _csv(value: str) -> Tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _thresholds(value: str) -> Dict[str, int]:
    result = {}
    for item in _csv(value):
        degree, raw_threshold = item.split("=", 1)
        result[degree] = int(raw_threshold)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Query an indexed researcher candidate database")
    parser.add_argument("--db", required=True)
    parser.add_argument("--graduation-years", required=True)
    parser.add_argument("--degree-threshold", required=True)
    parser.add_argument("--strictly-greater", action="store_true")
    parser.add_argument("--venues", required=True)
    parser.add_argument("--categories", required=True)
    parser.add_argument("--graduation-states", required=True)
    parser.add_argument("--institutions", default="")
    parser.add_argument("--max-evidence-age-days", type=int, default=365)
    args = parser.parse_args()
    query = Query(
        graduation_years=tuple(int(year) for year in _csv(args.graduation_years)),
        degree_thresholds=_thresholds(args.degree_threshold),
        venues=_csv(args.venues),
        categories=_csv(args.categories),
        graduation_states=_csv(args.graduation_states),
        strictly_greater=args.strictly_greater,
        institutions=_csv(args.institutions),
        max_evidence_age_days=args.max_evidence_age_days,
    )
    connection = connect(args.db)
    initialize(connection)
    print(json.dumps(query_candidates(connection, query), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
