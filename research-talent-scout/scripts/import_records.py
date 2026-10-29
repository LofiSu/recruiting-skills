#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict

try:
    from scripts.init_index import connect, initialize
except ModuleNotFoundError:
    from init_index import connect, initialize


VENUE_NAMES = {
    "ACL": ["ACL", "Annual Meeting of the Association for Computational Linguistics"],
    "ICML": ["ICML", "International Conference on Machine Learning"],
    "ICLR": ["ICLR", "International Conference on Learning Representations"],
    "NeurIPS": ["NeurIPS", "NIPS", "Neural Information Processing Systems"],
    "EMNLP": ["EMNLP", "Empirical Methods in Natural Language Processing"],
    "CVPR": ["CVPR", "Computer Vision and Pattern Recognition"],
    "AAAI": ["AAAI", "AAAI Conference on Artificial Intelligence"],
    "ICCV": ["ICCV", "International Conference on Computer Vision"],
    "MLSys": ["MLSys", "Conference on Machine Learning and Systems"],
    "OSDI": ["OSDI", "Operating Systems Design and Implementation"],
    "EuroSys": ["EuroSys"],
    "ASPLOS": ["ASPLOS"],
    "ISCA": ["ISCA", "International Symposium on Computer Architecture"],
    "SC": ["SC", "Supercomputing"],
    "PPoPP": ["PPoPP", "Principles and Practice of Parallel Programming"],
}
VENUE_ALIASES = {
    alias.casefold(): canonical
    for canonical, aliases in VENUE_NAMES.items()
    for alias in aliases
}
DEGREES = {"phd", "masters"}
GRADUATION_STATES = {"confirmed", "likely_needs_verification", "unknown", "stale", "conflict"}
IDENTITY_STATES = {"verified", "ambiguous"}
CATEGORIES = {"main_first", "co_first", "findings", "workshop", "short", "demo", "unclassified"}


def normalize_venue(value: str) -> str:
    try:
        return VENUE_ALIASES[value.strip().casefold()]
    except KeyError as error:
        raise ValueError(f"unsupported venue: {value}") from error


def _validate(record: dict) -> None:
    candidate = record["candidate"]
    if candidate["degree"] not in DEGREES:
        raise ValueError(f"unsupported degree: {candidate['degree']}")
    if candidate["graduation_state"] not in GRADUATION_STATES:
        raise ValueError(f"unsupported graduation state: {candidate['graduation_state']}")
    if candidate["identity_state"] not in IDENTITY_STATES:
        raise ValueError(f"unsupported identity state: {candidate['identity_state']}")
    for publication in record.get("publications", []):
        if publication["category"] not in CATEGORIES:
            raise ValueError(f"unsupported authorship category: {publication['category']}")
        normalize_venue(publication["venue"])
    for evidence in record.get("evidence", []):
        if evidence["state"] not in GRADUATION_STATES:
            raise ValueError(f"unsupported evidence state: {evidence['state']}")
    if candidate["graduation_state"] == "confirmed":
        supported = any(
            item.get("field") == "graduation_year"
            and item.get("state") == "confirmed"
            and item.get("url", "").startswith(("https://", "http://"))
            for item in record.get("evidence", [])
        )
        if not supported:
            raise ValueError("confirmed graduation evidence requires a public URL")


def import_file(connection, path: str) -> Dict[str, int]:
    summary = {"candidates": 0, "publications": 0, "duplicate_publications": 0, "evidence": 0}
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            _validate(record)
        except (KeyError, TypeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"line {line_number}: {error}") from error
        candidate = record["candidate"]
        with connection:
            connection.execute(
                """INSERT INTO candidates
                (id, name, degree, institution, lab, graduation_year, graduation_state,
                 identity_state, homepage, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name, degree=excluded.degree, institution=excluded.institution,
                  lab=excluded.lab, graduation_year=excluded.graduation_year,
                  graduation_state=excluded.graduation_state,
                  identity_state=excluded.identity_state, homepage=excluded.homepage,
                  verified_at=excluded.verified_at""",
                (
                    candidate["id"], candidate["name"], candidate["degree"],
                    candidate.get("institution", ""), candidate.get("lab", ""),
                    candidate.get("graduation_year"), candidate["graduation_state"],
                    candidate["identity_state"], candidate.get("homepage", ""),
                    candidate["verified_at"],
                ),
            )
            summary["candidates"] += 1
            for publication in record.get("publications", []):
                exists = connection.execute(
                    "SELECT 1 FROM publications WHERE source_id = ?", (publication["source_id"],)
                ).fetchone()
                if exists:
                    summary["duplicate_publications"] += 1
                else:
                    summary["publications"] += 1
                connection.execute(
                    """INSERT INTO publications(source_id, title, year, normalized_venue, url)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                      title=excluded.title, year=excluded.year,
                      normalized_venue=excluded.normalized_venue, url=excluded.url""",
                    (
                        publication["source_id"], publication["title"], publication["year"],
                        normalize_venue(publication["venue"]), publication["url"],
                    ),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO authorships(candidate_id, publication_id, category) VALUES (?, ?, ?)",
                    (candidate["id"], publication["source_id"], publication["category"]),
                )
            for evidence in record.get("evidence", []):
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO evidence
                    (candidate_id, field, state, source_type, url, excerpt, retrieved_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        candidate["id"], evidence["field"], evidence["state"],
                        evidence["source_type"], evidence.get("url", ""),
                        evidence.get("excerpt", ""), evidence["retrieved_at"],
                    ),
                )
                summary["evidence"] += cursor.rowcount
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Import normalized researcher JSONL records")
    parser.add_argument("--db", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    connection = connect(args.db)
    initialize(connection)
    print(json.dumps(import_file(connection, args.input), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
