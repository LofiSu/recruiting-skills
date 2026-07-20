import ipaddress
import os
import re
import shutil
import tempfile
import unicodedata
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from html import escape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from researcher_recruiting.models import (
    ContactKind,
    ContactPoint,
    Evidence,
    RunResult,
    _is_paper_email_provenance,
)
from researcher_recruiting.search_links import build_locator_links

ARTIFACT_NAMES = ("report.html",)

_SECRET_KEY = re.compile(
    r"(?i)^(?:authorization|token|api[_-]?key|client[_-]?secret)$"
)
_BARE_EMAIL = re.compile(
    r"[^@\s<>:/?#\[\]\\\x00-\x1f\x7f]+"
    r"@(?:[^@\s<>:/?#\[\]\\\x00-\x1f\x7f]+\.)+"
    r"[^@\s<>:/?#\[\]\\\x00-\x1f\x7f]+"
)
_HOST_LABEL = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
)


def _jsonable(value: Any) -> Any:
    if _is_paper_email_provenance(value):
        return None
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
            (
                r"(?i)(token|api(?:[_-]|%5f|%2d)?key|"
                r"client(?:_|%5f)secret)(=|%3d)([^&\s]+)"
            ),
            lambda match: (
                match.group(1)
                + match.group(2)
                + "[REDACTED]"
            ),
            redacted,
        )
        return redacted
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if _SECRET_KEY.fullmatch(str(key))
                else _redact(item)
            )
            for key, item in value.items()
        }
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


def _stable_author_id(run: RunResult, author_order: int) -> str:
    return f"{run.paper.arxiv_id}:author:{author_order}"


def _match_scope(
    run: RunResult,
    match: Any,
    match_index: int,
) -> tuple[int | None, str | None]:
    author_order = match.author_order
    if author_order is None:
        identity_positions = [
            order
            for order, author in enumerate(run.paper.authors, start=1)
            if author is match.author
        ]
        equality_positions = [
            order
            for order, author in enumerate(run.paper.authors, start=1)
            if author == match.author
        ]
        name_positions = [
            order
            for order, author in enumerate(run.paper.authors, start=1)
            if author.name == match.author.name
        ]
        for positions in (
            identity_positions,
            equality_positions,
            name_positions,
        ):
            if len(positions) == 1:
                author_order = positions[0]
                break
        else:
            positionally_aligned = (
                len(run.matches) == len(run.paper.authors)
                and all(
                    candidate.author is author
                    for candidate, author in zip(
                        run.matches,
                        run.paper.authors,
                    )
                )
            )
            if positionally_aligned:
                author_order = match_index + 1
    author_id = match.author_id
    if author_id is None and author_order is not None:
        author_id = _stable_author_id(run, author_order)
    return author_order, author_id


def _candidate_records(run: RunResult) -> list[dict[str, Any]]:
    records = []
    for match_index, match in enumerate(run.matches):
        author_order, author_id = _match_scope(
            run,
            match,
            match_index,
        )
        links = build_locator_links(match.author)
        evidence_items = tuple(match.evidence)
        contact_points = tuple(match.contact_points)
        records.append(
            {
                "arxiv_id": run.paper.arxiv_id,
                "paper_title": run.paper.title,
                "author_order": author_order,
                "author_id": author_id,
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


def _safe_href(
    value: str, *, allow_mailto: bool = False
) -> str | None:
    if not value or any(
        char.isspace() or unicodedata.category(char) == "Cc"
        for char in value
    ):
        return None
    try:
        parsed = urlsplit(value)
    except (UnicodeError, ValueError):
        return None
    allowed = {"http", "https"}
    if allow_mailto:
        allowed.add("mailto")
    scheme = parsed.scheme.casefold()
    if scheme not in allowed:
        return None
    if scheme in {"http", "https"}:
        try:
            hostname = parsed.hostname
            parsed.port
        except (UnicodeError, ValueError):
            return None
        host_and_port = parsed.netloc.rsplit("@", 1)[-1]
        if (
            hostname is None
            or not _is_valid_hostname(hostname)
            or host_and_port.endswith(":")
        ):
            return None
    return value


def _is_valid_hostname(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        return True
    try:
        ascii_hostname = value.rstrip(".").encode("idna").decode("ascii")
    except UnicodeError:
        return False
    return (
        bool(ascii_hostname)
        and len(ascii_hostname) <= 253
        and all(
            _HOST_LABEL.fullmatch(label) is not None
            for label in ascii_hostname.split(".")
        )
    )


def _text(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _link(
    label: str, href: str, *, allow_mailto: bool = False
) -> str:
    safe = _safe_href(href, allow_mailto=allow_mailto)
    if safe is None:
        return ""
    return (
        f'<a href="{_text(safe)}" target="_blank" '
        f'rel="noopener noreferrer">{_text(label)}</a>'
    )


def _email_link(value: str) -> str:
    if _BARE_EMAIL.fullmatch(value) is None:
        return ""
    return _link(value, f"mailto:{value}", allow_mailto=True)


def _is_unsafe_evidence_url_value(field: str, value: str) -> bool:
    normalized_field = field.casefold()
    is_url_field = (
        normalized_field
        in {
            "contact_form",
            "email",
            "github",
            "homepage",
            "openreview",
            "orcid",
            "profile",
            "url",
            "website",
        }
        or normalized_field.endswith(("_link", "_uri", "_url"))
    )
    if not is_url_field:
        return False
    try:
        has_scheme = bool(urlsplit(value).scheme)
    except (UnicodeError, ValueError):
        return True
    if not has_scheme:
        return False
    return _safe_href(value) is None


def _list_items(items: Iterable[str], empty: str) -> str:
    rendered = [item for item in items if item]
    if not rendered:
        return f"<p class=\"muted\">{_text(empty)}</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in rendered) + "</ul>"


def _display_scalar(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _render_metadata(value: object) -> str:
    if isinstance(value, dict):
        if not value:
            return '<span class="muted">None recorded.</span>'
        return (
            '<dl class="audit-fields">'
            + "".join(
                (
                    f"<div><dt>{_text(key)}</dt>"
                    f"<dd>{_render_metadata(item)}</dd></div>"
                )
                for key, item in value.items()
            )
            + "</dl>"
        )
    if isinstance(value, list):
        if not value:
            return '<span class="muted">None recorded.</span>'
        return (
            "<ol>"
            + "".join(
                f"<li>{_render_metadata(item)}</li>" for item in value
            )
            + "</ol>"
        )
    return _text(_display_scalar(value))


def _render_audit_fields(
    fields: Iterable[tuple[str, str]],
) -> str:
    return (
        '<dl class="audit-fields">'
        + "".join(
            f"<div><dt>{_text(label)}</dt><dd>{value}</dd></div>"
            for label, value in fields
            if value
        )
        + "</dl>"
    )


def _render_evidence_item(
    item: dict[str, Any],
    *,
    css_class: str = "evidence-item",
) -> str:
    field = str(item["field"])
    value = str(item["value"])
    rendered_value = (
        ""
        if _is_unsafe_evidence_url_value(field, value)
        else _text(value)
    )
    evidence_url = _link(str(item["url"]), str(item["url"]))
    fields = (
        ("Source", _text(item["source"])),
        ("Field", _text(field)),
        ("Value", rendered_value),
        ("URL", evidence_url),
        ("Collected at", _text(item["collected_at"])),
        ("Candidate ID", _text(item["candidate_id"])),
        ("Metadata", _render_metadata(item["metadata"])),
    )
    return (
        f'<li class="{_text(css_class)}">'
        f"{_render_audit_fields(fields)}</li>"
    )


def _render_evidence_list(
    evidence: Iterable[dict[str, Any]],
    *,
    css_class: str = "evidence-item",
    empty: str = "No public identity evidence.",
) -> str:
    items = [
        _render_evidence_item(item, css_class=css_class)
        for item in evidence
    ]
    if not items:
        return f'<p class="muted">{_text(empty)}</p>'
    return '<ul class="audit-list">' + "".join(items) + "</ul>"


def _render_contact_value(point: dict[str, Any]) -> str:
    value = str(point["value"])
    if point["kind"] == ContactKind.PROFESSIONAL_EMAIL.value:
        return _email_link(value)
    return _link(value, value)


def _render_contact_point(point: dict[str, Any]) -> str:
    source_url = _link(
        str(point["source_url"]),
        str(point["source_url"]),
    )
    fields = (
        ("Kind", _text(point["kind"])),
        ("Value", _render_contact_value(point)),
        ("Source", _text(point["source"])),
        ("Source URL", source_url),
        ("Collected at", _text(point["collected_at"])),
        ("Confidence", _text(point["confidence"])),
        ("Direct", _text(_display_scalar(point["direct"]))),
        ("Metadata", _render_metadata(point["metadata"])),
    )
    nested_evidence = _render_evidence_list(
        point["evidence"],
        css_class="contact-evidence",
        empty="No contact evidence recorded.",
    )
    return (
        '<li class="contact-point">'
        f"{_render_audit_fields(fields)}"
        f"<h4>Evidence</h4>{nested_evidence}</li>"
    )


def _render_contact_provenance(
    contact_points: Iterable[dict[str, Any]],
) -> str:
    items = [_render_contact_point(point) for point in contact_points]
    content = (
        '<ul class="audit-list">' + "".join(items) + "</ul>"
        if items
        else '<p class="muted">No contact-point provenance recorded.</p>'
    )
    return (
        '<details class="contact-provenance">'
        f"<summary>Contact-point provenance</summary>{content}</details>"
    )


def _render_source_attempt(attempt: dict[str, Any]) -> str:
    error = (
        f" — {_text(attempt['error'])}"
        if attempt["error"]
        else ""
    )
    evidence = _render_evidence_list(
        attempt["evidence"],
        css_class="source-evidence",
        empty="No evidence returned by this source.",
    )
    return (
        '<li class="source-attempt" '
        f'data-source="{_text(attempt["source"])}">'
        f"<p><strong>{_text(attempt['source'])}</strong>: "
        f"{_text(attempt['status'])} "
        f"({_text(attempt['evidence_count'])} evidence)"
        f"{error}</p>{evidence}</li>"
    )


def _render_source_attempts(
    attempts: Iterable[dict[str, Any]],
) -> str:
    items = [_render_source_attempt(attempt) for attempt in attempts]
    if not items:
        return '<p class="muted">No source attempts recorded.</p>'
    return '<ul class="audit-list">' + "".join(items) + "</ul>"


def _source_result_matches_author(
    item: Any,
    *,
    author_id: str | None,
    author_order: int | None,
    author_name: str,
) -> bool:
    if item.author_id is not None:
        return author_id is not None and item.author_id == author_id
    if item.author_order is not None:
        return (
            author_order is not None
            and item.author_order == author_order
        )
    return item.author_name == author_name


def _source_attempt_records(
    run: RunResult,
) -> list[dict[str, object]]:
    scoped_matches = [
        (match, *_match_scope(run, match, match_index))
        for match_index, match in enumerate(run.matches)
    ]
    records = [
        {
            "author_order": author_order,
            "author_id": author_id,
            "author_name": match.author.name,
            "contact_status": match.contact_status,
            "source_attempts": [
                {
                    "source": item.source,
                    "status": item.status,
                    "evidence_count": len(item.evidence),
                    "evidence": item.evidence,
                    "error": item.error,
                }
                for item in run.source_results
                if _source_result_matches_author(
                    item,
                    author_id=author_id,
                    author_order=author_order,
                    author_name=match.author.name,
                )
            ],
        }
        for match, author_order, author_id in scoped_matches
    ]
    return _redact(_jsonable(records))


def _report_html(
    run: RunResult,
    candidates: list[dict[str, Any]],
    source_attempts: list[dict[str, object]],
    generated_at: datetime,
) -> str:
    render_data = _redact(
        _jsonable(
            {
                "paper": run.paper,
                "candidates": candidates,
                "source_attempts": source_attempts,
            }
        )
    )
    paper = render_data["paper"]
    candidates = render_data["candidates"]
    source_attempts = render_data["source_attempts"]
    attempts_by_id = {
        item["author_id"]: item
        for item in source_attempts
        if item["author_id"] is not None
    }
    cards = []
    for index, candidate in enumerate(candidates, start=1):
        order = candidate["author_order"] or index
        author_attempts = attempts_by_id.get(candidate["author_id"])
        if author_attempts is None and index <= len(source_attempts):
            author_attempts = source_attempts[index - 1]

        direct_links = [
            _email_link(str(candidate["email"]))
            if candidate["email"]
            else "",
            _link("Contact form", str(candidate["contact_form"]))
            if candidate["contact_form"]
            else "",
        ]
        profile_links = [
            _link(label, str(candidate[field]))
            for label, field in (
                ("Homepage", "homepage"),
                ("GitHub", "github"),
                ("OpenReview", "openreview"),
                ("ORCID", "orcid"),
            )
            if candidate[field]
        ]
        locator_links = [
            _link(label, str(candidate[field]))
            for label, field in (
                ("Google Scholar", "google_scholar"),
                ("LinkedIn", "linkedin"),
                ("Maimai", "maimai"),
            )
            if candidate[field]
        ]
        contacts = [item for item in direct_links + profile_links if item]
        contact_html = (
            "<ul class=\"link-list\">"
            + "".join(f"<li>{item}</li>" for item in contacts)
            + "</ul>"
            if contacts
            else (
                "<p class=\"muted\">"
                "No verified public professional contact was found."
                "</p>"
            )
        )
        locator_html = _list_items(
            locator_links,
            "No locator links were available.",
        )
        reason_html = _list_items(
            (_text(reason) for reason in candidate["reasons"]),
            "No identity reasons recorded.",
        )

        evidence_html = _render_evidence_list(
            candidate["evidence"],
        )
        contact_provenance_html = _render_contact_provenance(
            candidate["contact_points"],
        )
        attempts_html = _render_source_attempts(
            author_attempts["source_attempts"]
            if author_attempts is not None
            else []
        )

        cards.append(
            f"""\
<article id="author-{_text(order)}" class="candidate-card"
         data-contact-status="{_text(candidate['contact_status'])}">
  <header>
    <p class="eyebrow">Author {_text(order)}</p>
    <h2>{_text(candidate['author_name'])}</h2>
    <p>{_text(candidate['original_affiliation'])}</p>
  </header>
  <dl class="facts">
    <div><dt>Identity</dt><dd>{_text(candidate['identity_state'])}</dd></div>
    <div><dt>Confidence</dt><dd>{_text(candidate['confidence'])}/100</dd></div>
    <div><dt>Contact status</dt><dd>{_text(candidate['contact_status'])}</dd></div>
  </dl>
  <section><h3>Public contacts and profiles</h3>{contact_html}</section>
  <section><h3>Locator-only links</h3>{locator_html}</section>
  {contact_provenance_html}
  <details><summary>Identity reasons</summary>{reason_html}</details>
  <details><summary>Evidence</summary>{evidence_html}</details>
  <details><summary>Source attempts</summary>{attempts_html}</details>
</article>"""
        )

    paper_link = _link("arXiv source", paper["source_url"])
    paper_metadata = " · ".join(
        part
        for part in (
            _text(paper["arxiv_id"]),
            _text(", ".join(paper["categories"])),
            paper_link,
        )
        if part
    )
    return f"""\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Researcher recruiting report: {_text(paper["title"])}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f6f8; color: #17202a; }}
    main {{ width: min(72rem, calc(100% - 2rem)); margin: 0 auto; padding: 2rem 0; }}
    .paper-header, .candidate-card, .compliance {{
      background: white; border: 1px solid #dfe4e8; border-radius: .75rem;
      box-shadow: 0 .2rem .8rem rgb(0 0 0 / 8%); margin-bottom: 1rem; padding: 1.25rem;
    }}
    h1, h2, h3 {{ line-height: 1.2; }}
    .eyebrow, dt {{ color: #59636e; font-size: .8rem; font-weight: 700;
      letter-spacing: .06em; text-transform: uppercase; }}
    .controls {{ display: grid; gap: .75rem; grid-template-columns: 2fr 1fr;
      margin: 1.5rem 0; }}
    input, select {{ border: 1px solid #aeb8c2; border-radius: .4rem;
      font: inherit; padding: .7rem; }}
    .facts {{ display: grid; gap: .75rem; grid-template-columns: repeat(3, 1fr); }}
    .facts div {{ background: #f6f8fa; border-radius: .4rem; padding: .75rem; }}
    .facts dd {{ margin: .25rem 0 0; }}
    .link-list {{ display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; }}
    .audit-list {{ list-style: none; padding: 0; }}
    .audit-list > li {{ border-left: .2rem solid #dfe4e8;
      margin: .75rem 0; padding-left: .75rem; }}
    .audit-fields {{ display: grid; gap: .5rem; }}
    .audit-fields div {{ display: grid; gap: .25rem;
      grid-template-columns: minmax(8rem, 12rem) 1fr; }}
    .audit-fields dd {{ margin: 0; overflow-wrap: anywhere; }}
    details {{ border-top: 1px solid #dfe4e8; margin-top: 1rem; padding-top: 1rem; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    .muted {{ color: #59636e; }}
    [hidden] {{ display: none !important; }}
    @media (max-width: 40rem) {{
      .controls, .facts {{ grid-template-columns: 1fr; }}
      .audit-fields div {{ grid-template-columns: 1fr; }}
      main {{ width: min(100% - 1rem, 72rem); padding: .5rem 0; }}
    }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #111820; color: #e9eef3; }}
      .paper-header, .candidate-card, .compliance {{ background: #18222c; border-color: #34414d; }}
      .facts div {{ background: #202c37; }}
      .eyebrow, dt, .muted {{ color: #aeb8c2; }}
    }}
  </style>
</head>
<body>
<main>
  <header class="paper-header">
    <p class="eyebrow">Researcher recruiting report</p>
    <h1>{_text(paper["title"])}</h1>
    <p>{paper_metadata}</p>
    <p>{_text(paper["abstract"])}</p>
    <p class="muted">Generated {_text(generated_at.isoformat())}</p>
  </header>
  <section class="controls" aria-label="Candidate filters">
    <input id="candidate-search" type="search" placeholder="Search candidates"
           aria-label="Search candidates">
    <select id="contact-filter" aria-label="Filter by contact status">
      <option value="">All contact statuses</option>
      <option value="found">found</option>
      <option value="not_found">not_found</option>
      <option value="ambiguous">ambiguous</option>
      <option value="sources_unavailable">sources_unavailable</option>
    </select>
  </section>
  <section id="candidates" aria-label="Candidates">
    {''.join(cards)}
  </section>
  <section class="compliance">
    <h2>Compliance and collection boundaries</h2>
    <p>Only public professional contact information and public identity
    evidence are included. Google Scholar, ResearchGate, Academia.edu,
    LinkedIn, Maimai, and unlicensed commercial databases are locator-only.
    No login, CAPTCHA, paywall, or access-control bypass was attempted.</p>
  </section>
</main>
<script>
(() => {{
  const search = document.querySelector("#candidate-search");
  const status = document.querySelector("#contact-filter");
  const cards = document.querySelectorAll(".candidate-card");
  const filter = () => {{
    const query = search.value.toLocaleLowerCase();
    for (const card of cards) {{
      const matchesText = card.textContent.toLocaleLowerCase().includes(query);
      const matchesStatus = !status.value ||
        card.dataset.contactStatus === status.value;
      card.hidden = !(matchesText && matchesStatus);
    }}
  }};
  search.addEventListener("input", filter);
  status.addEventListener("change", filter);
}})();
</script>
</body>
</html>
"""


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
        source_attempts = _source_attempt_records(run)
        (temporary / ARTIFACT_NAMES[0]).write_text(
            _report_html(
                run,
                candidates,
                source_attempts,
                timestamp,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, final_path)
        return final_path
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
