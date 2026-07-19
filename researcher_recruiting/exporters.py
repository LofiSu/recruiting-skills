import csv
import json
import os
import re
import shutil
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from researcher_recruiting.models import (
    ContactKind,
    ContactPoint,
    Evidence,
    RunResult,
)
from researcher_recruiting.search_links import build_locator_links

ARTIFACT_NAMES = (
    "report.md",
    "candidates.csv",
    "candidates.json",
    "evidence.json",
    "run-log.json",
)

CSV_COLUMNS = (
    "arxiv_id",
    "paper_title",
    "author_order",
    "author_name",
    "original_affiliation",
    "identity_state",
    "confidence",
    "contact_status",
    "orcid",
    "email",
    "contact_form",
    "homepage",
    "github",
    "openreview",
    "google_scholar",
    "linkedin",
    "maimai",
    "reasons",
    "recruiting_notes",
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            key: _jsonable(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item) for key, item in value.items()
        }
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        redacted = re.sub(
            r"(?i)\bBearer\s+[^\s\"']+",
            "Bearer [REDACTED]",
            value,
        )
        redacted = re.sub(
            r"(?i)(?:token|api[_-]?key|client_secret)=([^&\s]+)",
            lambda match: match.group(0).split("=", 1)[0]
            + "=[REDACTED]",
            redacted,
        )
        return redacted
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _first_value(items: Iterable[Evidence], field: str) -> str:
    return next(
        (item.value for item in items if item.field == field),
        "",
    )


def _first_contact_value(
    points: Iterable[ContactPoint],
    kind: ContactKind,
    *,
    direct: bool | None = None,
) -> str:
    return next(
        (
            point.value
            for point in points
            if point.kind is kind
            and (direct is None or point.direct is direct)
        ),
        "",
    )


def _candidate_records(run: RunResult) -> list[dict[str, Any]]:
    records = []
    for order, match in enumerate(run.matches, start=1):
        links = build_locator_links(match.author)
        evidence_items = tuple(match.evidence)
        contact_points = tuple(match.contact_points)
        records.append(
            {
                "arxiv_id": run.paper.arxiv_id,
                "paper_title": run.paper.title,
                "author_order": order,
                "author_name": match.author.name,
                "original_affiliation": match.author.affiliation or "",
                "identity_state": match.state.value,
                "confidence": match.confidence,
                "contact_status": match.contact_status.value,
                "orcid": _first_value(evidence_items, "orcid"),
                "email": _first_contact_value(
                    contact_points,
                    ContactKind.PROFESSIONAL_EMAIL,
                    direct=True,
                ),
                "contact_form": _first_contact_value(
                    contact_points,
                    ContactKind.CONTACT_FORM,
                    direct=True,
                ),
                "homepage": _first_contact_value(
                    contact_points, ContactKind.HOMEPAGE
                )
                or _first_value(evidence_items, "homepage"),
                "github": _first_contact_value(
                    contact_points, ContactKind.GITHUB
                )
                or _first_value(evidence_items, "github"),
                "openreview": _first_contact_value(
                    contact_points, ContactKind.OPENREVIEW
                )
                or _first_value(evidence_items, "openreview"),
                "google_scholar": _first_contact_value(
                    contact_points,
                    ContactKind.GOOGLE_SCHOLAR_LOCATOR,
                )
                or links["google_scholar"],
                "linkedin": _first_contact_value(
                    contact_points,
                    ContactKind.LINKEDIN_LOCATOR,
                )
                or links["linkedin"],
                "maimai": _first_contact_value(
                    contact_points,
                    ContactKind.MAIMAI_LOCATOR,
                )
                or links["maimai"],
                "locator_links": links,
                "contact_points": _jsonable(contact_points),
                "reasons": list(match.reasons),
                "evidence": [_jsonable(item) for item in evidence_items],
                "recruiting_notes": "",
            }
        )
    return records


def _all_evidence(run: RunResult) -> list[Evidence]:
    items = [
        item
        for source_result in run.source_results
        for item in source_result.evidence
    ]
    items.extend(
        item for match in run.matches for item in match.evidence
    )
    deduplicated = []
    seen = set()
    for item in items:
        key = (
            item.source,
            item.field,
            item.value,
            item.url,
            item.candidate_id,
            item.collected_at,
        )
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


def _report_markdown(
    run: RunResult, candidates: list[dict[str, Any]]
) -> str:
    lines = [
        f"# Researcher recruiting report: {run.paper.title}",
        "",
        (
            f"[arXiv]({run.paper.source_url}) · "
            f"`{run.paper.arxiv_id}` · "
            f"categories: {', '.join(run.paper.categories)}"
        ),
        "",
        "## Candidates",
        "",
        "| # | Author | Affiliation | State | Confidence |",
        "| ---: | --- | --- | --- | ---: |",
    ]
    for record in candidates:
        lines.append(
            "| {author_order} | {author_name} | {original_affiliation} | "
            "{identity_state} | {confidence} |".format(**record)
        )
    for record in candidates:
        direct_contacts = []
        if record["email"]:
            direct_contacts.append(
                f"[email](mailto:{record['email']})"
            )
        if record["contact_form"]:
            direct_contacts.append(
                f"[contact form]({record['contact_form']})"
            )
        public_profiles = [
            f"[{label}]({record[field]})"
            for label, field in (
                ("Homepage", "homepage"),
                ("GitHub", "github"),
                ("OpenReview", "openreview"),
            )
            if record[field]
        ]
        contact_lines = [
            f"- Contact status: `{record['contact_status']}`"
        ]
        if direct_contacts:
            contact_lines.append(
                "- Direct public contacts: "
                + ", ".join(direct_contacts)
            )
        if public_profiles:
            contact_lines.append(
                "- Public profiles: " + ", ".join(public_profiles)
            )
        if not direct_contacts and not public_profiles:
            contact_lines.append(
                "No verified public professional contact was found."
            )
        contact_lines.append(
            "- Locator-only: "
            f"[Google Scholar]({record['google_scholar']}), "
            f"[LinkedIn]({record['linkedin']}), "
            f"[Maimai]({record['maimai']})"
        )
        lines.extend(
            [
                "",
                f"## {record['author_order']}. {record['author_name']}",
                "",
                f"- Identity: `{record['identity_state']}` "
                f"({record['confidence']}/100)",
                "- Reasons: "
                + (
                    "; ".join(record["reasons"])
                    if record["reasons"]
                    else "none"
                ),
                *contact_lines,
                "",
                "### Evidence",
                "",
            ]
        )
        if record["evidence"]:
            for item in record["evidence"]:
                lines.append(
                    f"- `{item['source']}` / `{item['field']}`: "
                    f"[{item['value']}]({item['url']})"
                )
        else:
            lines.append("- No public identity evidence.")
    lines.extend(
        [
            "",
            "## Compliance",
            "",
            (
                "Google Scholar, ResearchGate, Academia.edu, LinkedIn, "
                "Maimai, and unlicensed commercial databases are "
                "locator-only. No login, CAPTCHA, paywall, or access-control "
                "bypass was attempted."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            _redact(_jsonable(value)),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_artifacts(run: RunResult, output_root: Path) -> Path:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=".researcher-recruiting-", dir=output_root)
    )
    timestamp = datetime.now(timezone.utc)
    final_name = (
        f"{run.paper.arxiv_id.replace('/', '-')}-"
        f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}"
    )
    final_path = output_root / final_name
    try:
        candidates = _candidate_records(run)
        (temporary / "report.md").write_text(
            _report_markdown(run, candidates),
            encoding="utf-8",
        )
        with (temporary / "candidates.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for record in candidates:
                row = {
                    key: (
                        "; ".join(record[key])
                        if key == "reasons"
                        else record.get(key, "")
                    )
                    for key in CSV_COLUMNS
                }
                writer.writerow(row)
        _write_json(temporary / "candidates.json", candidates)
        _write_json(
            temporary / "evidence.json",
            _all_evidence(run),
        )
        _write_json(
            temporary / "run-log.json",
            {
                "generated_at": timestamp.isoformat(),
                "paper": {
                    "arxiv_id": run.paper.arxiv_id,
                    "title": run.paper.title,
                    "categories": run.paper.categories,
                },
                "source_results": [
                    {
                        "source": item.source,
                        "status": item.status,
                        "evidence_count": len(item.evidence),
                        "error": item.error,
                    }
                    for item in run.source_results
                ],
                "authors": [
                    {
                        "author_name": match.author.name,
                        "contact_status": match.contact_status,
                        "source_attempts": [
                            {
                                "source": item.source,
                                "status": item.status,
                                "evidence_count": len(item.evidence),
                                "error": item.error,
                            }
                            for item in run.source_results
                            if item.author_name == match.author.name
                        ],
                    }
                    for match in run.matches
                ],
                "artifact_names": ARTIFACT_NAMES,
            },
        )
        os.replace(temporary, final_path)
        return final_path
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
