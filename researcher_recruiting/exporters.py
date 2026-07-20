import ipaddress
import os
import re
import shutil
import tempfile
import unicodedata
from collections import Counter
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
            return '<span class="muted">未记录。</span>'
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
            return '<span class="muted">未记录。</span>'
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
        ("来源", _text(item["source"])),
        ("字段", _text(field)),
        ("值", rendered_value),
        ("链接", evidence_url),
        ("采集时间", _text(item["collected_at"])),
        ("候选人 ID", _text(item["candidate_id"])),
        ("元数据", _render_metadata(item["metadata"])),
    )
    return (
        f'<li class="{_text(css_class)}">'
        f"{_render_audit_fields(fields)}</li>"
    )


def _render_evidence_list(
    evidence: Iterable[dict[str, Any]],
    *,
    css_class: str = "evidence-item",
    empty: str = "未记录公开身份依据。",
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
        ("类型", _text(point["kind"])),
        ("值", _render_contact_value(point)),
        ("来源", _text(point["source"])),
        ("来源链接", source_url),
        ("采集时间", _text(point["collected_at"])),
        ("置信度", _text(point["confidence"])),
        ("是否直接联系", _text(_display_scalar(point["direct"]))),
        ("元数据", _render_metadata(point["metadata"])),
    )
    nested_evidence = _render_evidence_list(
        point["evidence"],
        css_class="contact-evidence",
        empty="未记录联系方式证据。",
    )
    return (
        '<li class="contact-point">'
        f"{_render_audit_fields(fields)}"
        f"<h4>证据</h4>{nested_evidence}</li>"
    )


def _render_contact_provenance(
    contact_points: Iterable[dict[str, Any]],
) -> str:
    items = [_render_contact_point(point) for point in contact_points]
    content = (
        '<ul class="audit-list">' + "".join(items) + "</ul>"
        if items
        else '<p class="muted">未记录联系方式溯源。</p>'
    )
    return (
        '<details class="contact-provenance">'
        f"<summary>联系方式溯源</summary>{content}</details>"
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
        empty="此来源未返回证据。",
    )
    return (
        '<li class="source-attempt" '
        f'data-source="{_text(attempt["source"])}">'
        f"<p><strong>{_text(attempt['source'])}</strong>: "
        f"{_text(attempt['status'])} "
        f"（{_text(attempt['evidence_count'])} 条证据）"
        f"{error}</p>{evidence}</li>"
    )


def _render_source_attempts(
    attempts: Iterable[dict[str, Any]],
) -> str:
    items = [_render_source_attempt(attempt) for attempt in attempts]
    if not items:
        return '<p class="muted">未记录来源尝试。</p>'
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


def _report_summary(
    candidates: list[dict[str, Any]],
    source_attempts: list[dict[str, object]],
) -> dict[str, int]:
    identity_counts = Counter(
        str(candidate["identity_state"]) for candidate in candidates
    )
    unavailable_statuses = {
        "source_unavailable",
        "blocked_by_robots",
    }
    unavailable_attempts = sum(
        1
        for author in source_attempts
        for attempt in author["source_attempts"]
        if attempt["status"] in unavailable_statuses
    )
    return {
        "authors": len(candidates),
        "contacts_found": sum(
            candidate["contact_status"] == "found"
            for candidate in candidates
        ),
        "confirmed": identity_counts["confirmed"],
        "probable": identity_counts["probable"],
        "ambiguous": identity_counts["ambiguous"],
        "not_found": identity_counts["not_found"],
        "unavailable_attempts": unavailable_attempts,
    }


def _render_author_index(
    candidates: Iterable[dict[str, Any]],
) -> str:
    items = []
    for index, candidate in enumerate(candidates, start=1):
        order = candidate["author_order"] or index
        items.append(
            '<li class="author-index-item" '
            f'data-contact-status="{_text(candidate["contact_status"])}">'
            f'<a class="author-index-link" href="#author-{_text(order)}">'
            f'<span class="author-index-order">{_text(order).zfill(2)}</span>'
            f'<span class="author-index-name">'
            f'{_text(candidate["author_name"])}</span>'
            f'<span class="author-index-status">'
            f'{_text(candidate["contact_status"])}</span>'
            f'<span class="author-index-confidence">'
            f'{_text(candidate["confidence"])}/100</span>'
            "</a></li>"
        )
    return '<ol class="author-index-list">' + "".join(items) + "</ol>"


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
            _link("联系表单", str(candidate["contact_form"]))
            if candidate["contact_form"]
            else "",
        ]
        profile_links = [
            _link(label, str(candidate[field]))
            for label, field in (
                ("个人主页", "homepage"),
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
                "未找到经验证的公开职业联系方式。"
                "</p>"
            )
        )
        locator_html = _list_items(
            locator_links,
            "没有可用的定位链接。",
        )
        reason_html = _list_items(
            (_text(reason) for reason in candidate["reasons"]),
            "未记录身份匹配理由。",
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
    <p class="eyebrow">作者 {_text(order)}</p>
    <h2>{_text(candidate['author_name'])}</h2>
    <p>{_text(candidate['original_affiliation'])}</p>
  </header>
  <dl class="facts">
    <div><dt>身份匹配</dt><dd>{_text(candidate['identity_state'])}</dd></div>
    <div><dt>置信度</dt><dd>{_text(candidate['confidence'])}/100</dd></div>
    <div><dt>联系状态</dt><dd>{_text(candidate['contact_status'])}</dd></div>
  </dl>
  <section><h3>公开联系方式与资料</h3>{contact_html}</section>
  <section><h3>仅用于定位的链接</h3>{locator_html}</section>
  {contact_provenance_html}
  <details><summary>身份匹配理由</summary>{reason_html}</details>
  <details><summary>证据</summary>{evidence_html}</details>
  <details><summary>来源尝试</summary>{attempts_html}</details>
</article>"""
        )

    summary = _report_summary(candidates, source_attempts)
    author_index = _render_author_index(candidates)
    tldr = (
        f"共 {_text(summary['authors'])} 位作者；"
        f"{_text(summary['contacts_found'])} 位找到公开职业联系方式；"
        f"身份确认 {_text(summary['confirmed'])} 位，"
        f"大概率匹配 {_text(summary['probable'])} 位，"
        f"存在歧义 {_text(summary['ambiguous'])} 位，"
        f"未找到 {_text(summary['not_found'])} 位；"
        f"{_text(summary['unavailable_attempts'])} 次来源访问不可用或受限。"
    )
    paper_link = _link("arXiv 原文", paper["source_url"])
    return f"""\
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>研究者招聘情报报告：{_text(paper["title"])}</title>
  <style>
    :root {{
      --paper: #f7f7f5;
      --paper-edge: #efefea;
      --ink: #1a1a1a;
      --ink-soft: #4a4a4a;
      --ink-faint: #7a7a7a;
      --rule: #d8d8d2;
      --rule-soft: #e8e8e2;
      --accent: #a5523d;
      --accent-soft: #ead9d3;
      --accent-faint: #f4ece9;
      --warn: #9a7136;
      --warn-soft: #f5ecdc;
    }}
    body {{
      margin: 0;
      padding: 48px 24px 96px;
      background: var(--paper);
      color: var(--ink);
      font-family: ui-serif, Charter, Georgia, "Songti SC",
        "Source Han Serif SC", serif;
      line-height: 1.6;
    }}
    .doc {{ max-width: 1180px; margin: 0 auto; }}
    .doc-eyebrow, .doc-meta, .tldr-label, .num,
    .author-index, dt, summary, button, input, select {{
      font-family: ui-monospace, "SF Mono", Menlo,
        "PingFang SC", monospace;
    }}
    .doc-header {{
      border-bottom: 1px solid var(--rule);
      padding-bottom: 28px;
      margin-bottom: 32px;
    }}
    .doc-title {{
      font-size: clamp(28px, 5vw, 46px);
      line-height: 1.12;
    }}
    .doc-meta {{ display: flex; flex-wrap: wrap; gap: 12px 24px; }}
    .tldr {{
      background: var(--accent-faint);
      border-left: 2px solid var(--accent);
      padding: 20px 24px;
      margin-bottom: 40px;
    }}
    h2 {{ border-bottom: 1px solid var(--rule); padding-bottom: 10px; }}
    h2 .num {{ color: var(--ink-faint); margin-right: 14px; }}
    .report-controls {{
      display: grid;
      gap: .75rem;
      grid-template-columns: 2fr 1fr;
      margin: 1.5rem 0;
    }}
    input, select {{
      border: 1px solid var(--rule);
      background: var(--paper);
      color: var(--ink);
      font: inherit;
      padding: .7rem;
    }}
    .recruiting-workspace {{
      display: grid;
      grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
      gap: 48px;
      align-items: start;
    }}
    .author-index {{ position: sticky; top: 20px; }}
    .author-index-list {{ list-style: none; margin: 0; padding: 0; }}
    .author-index-link {{
      display: grid;
      grid-template-columns: 2.5em 1fr auto;
      gap: 6px 10px;
      padding: 10px 0;
      border-bottom: 1px solid var(--rule-soft);
      color: var(--ink);
      text-decoration: none;
    }}
    .author-index-status {{ grid-column: 2; color: var(--ink-faint); }}
    .author-index-confidence {{ grid-column: 3; color: var(--ink-faint); }}
    .candidate-card {{
      scroll-margin-top: 24px;
      border-top: 1px solid var(--rule);
      padding: 30px 0 42px;
    }}
    h1, h2, h3 {{ line-height: 1.2; }}
    .eyebrow, dt {{ color: var(--ink-faint); font-size: .8rem; font-weight: 700;
      letter-spacing: .06em; text-transform: uppercase; }}
    .facts {{ display: grid; gap: .75rem; grid-template-columns: repeat(3, 1fr); }}
    .facts div {{ background: var(--paper-edge); padding: .75rem; }}
    .facts dd {{ margin: .25rem 0 0; }}
    .link-list {{ display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; }}
    .audit-list {{ list-style: none; padding: 0; }}
    .audit-list > li {{ border-left: .2rem solid var(--rule);
      margin: .75rem 0; padding-left: .75rem; }}
    .audit-fields {{ display: grid; gap: .5rem; }}
    .audit-fields div {{ display: grid; gap: .25rem;
      grid-template-columns: minmax(8rem, 12rem) 1fr; }}
    .audit-fields dd {{ margin: 0; overflow-wrap: anywhere; }}
    details {{ border-top: 1px solid var(--rule); margin-top: 1rem; padding-top: 1rem; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    .muted {{ color: var(--ink-faint); }}
    [hidden] {{ display: none !important; }}
    @media (max-width: 760px) {{
      body {{ padding: 28px 16px 64px; }}
      .recruiting-workspace {{ grid-template-columns: 1fr; gap: 28px; }}
      .author-index {{
        position: static;
        overflow-x: auto;
        padding-bottom: 8px;
      }}
      .author-index-list {{ display: flex; min-width: max-content; }}
      .author-index-item {{ width: 220px; margin-right: 18px; }}
      .report-controls, .facts {{ grid-template-columns: 1fr; }}
      .audit-fields div {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <article class="doc">
    <header class="doc-header">
      <div class="doc-eyebrow">
        <span class="mascot"></span>研究者招聘情报报告
      </div>
      <h1 class="doc-title">{_text(paper["title"])}</h1>
      <p class="doc-subtitle">
        按论文作者顺序整理的公开职业身份、联系路径与来源证据
      </p>
      <div class="doc-meta">
        <span>ARXIV · {_text(paper["arxiv_id"])}</span>
        <span>分类 · {_text(", ".join(paper["categories"]))}</span>
        <span>生成时间 · {_text(generated_at.isoformat())}</span>
        <span>{paper_link}</span>
      </div>
    </header>
    <div class="tldr">
      <div class="tldr-label">TL;DR</div>
      <p>{tldr}</p>
    </div>
    <section class="paper-context">
      <h2><span class="num">01</span>论文概览</h2>
      <p>{_text(paper["abstract"])}</p>
    </section>
    <section class="author-section">
      <h2><span class="num">02</span>作者招聘档案</h2>
      <div class="report-controls" aria-label="作者筛选">
        <input id="candidate-search" type="search" placeholder="搜索作者"
               aria-label="搜索作者">
        <select id="contact-filter" aria-label="按联系方式状态筛选">
          <option value="">全部联系方式状态</option>
          <option value="found">found</option>
          <option value="not_found">not_found</option>
          <option value="ambiguous">ambiguous</option>
          <option value="sources_unavailable">sources_unavailable</option>
        </select>
      </div>
      <div class="recruiting-workspace">
        <nav class="author-index" aria-label="作者索引">
          {author_index}
        </nav>
        <div class="author-dossiers">{''.join(cards)}</div>
      </div>
    </section>
    <section class="compliance">
      <h2><span class="num">03</span>合规与采集边界</h2>
      <p>
        仅收录公开职业联系方式和公开身份依据。Google Scholar、
        ResearchGate、Academia.edu、LinkedIn、脉脉及未授权商业数据库
        仅提供定位链接；未绕过登录、CAPTCHA、付费墙、robots 限制或
        其他访问控制。
      </p>
    </section>
  </article>
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
