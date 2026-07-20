import json
from dataclasses import replace

import pytest
from bs4 import BeautifulSoup

from researcher_recruiting.exporters import (
    _jsonable,
    _report_summary,
    _safe_href,
    write_artifacts,
)
from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactPoint,
    ContactStatus,
    Evidence,
    IdentityMatch,
    IdentityState,
    PaperRecord,
    RunResult,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.sources.arxiv import parse_atom_feed


@pytest.fixture
def duplicate_name_run(run_result):
    first = run_result.matches[0]
    second_seed = AuthorSeed(
        name=first.author.name,
        affiliation="Different Institute",
    )
    second = IdentityMatch(
        author=second_seed,
        state=first.state,
        confidence=first.confidence,
        reasons=first.reasons,
        evidence=(),
        contact_status=ContactStatus.NOT_FOUND,
    )
    paper = PaperRecord(
        arxiv_id=run_result.paper.arxiv_id,
        title=run_result.paper.title,
        abstract=run_result.paper.abstract,
        submitted_at=run_result.paper.submitted_at,
        categories=run_result.paper.categories,
        authors=(first.author, second_seed),
        source_url=run_result.paper.source_url,
    )
    return RunResult(
        paper=paper,
        matches=(first, second),
        source_results=(
            SourceResult(
                "github",
                SourceStatus.OK,
                author_name=first.author.name,
                author_order=1,
                author_id="1706.03762:author:1",
            ),
            SourceResult(
                "orcid",
                SourceStatus.NOT_FOUND,
                author_name=second.author.name,
                author_order=2,
                author_id="1706.03762:author:2",
            ),
        ),
    )


def _report(run, tmp_path):
    return (
        write_artifacts(run, tmp_path) / "report.html"
    ).read_text(encoding="utf-8")


def test_report_summary_counts_recruiting_outcomes():
    candidates = [
        {
            "identity_state": "confirmed",
            "contact_status": "found",
        },
        {
            "identity_state": "ambiguous",
            "contact_status": "not_found",
        },
    ]
    attempts = [
        {
            "source_attempts": [
                {"status": "ok"},
                {"status": "source_unavailable"},
            ]
        },
        {
            "source_attempts": [
                {"status": "blocked_by_robots"},
            ]
        },
    ]

    assert _report_summary(candidates, attempts) == {
        "authors": 2,
        "contacts_found": 1,
        "confirmed": 1,
        "probable": 0,
        "ambiguous": 1,
        "not_found": 0,
        "unavailable_attempts": 2,
    }


def test_write_artifacts_creates_only_self_contained_html(
    tmp_path, run_result
):
    run_dir = write_artifacts(run_result, tmp_path)
    assert {path.name for path in run_dir.iterdir()} == {"report.html"}
    report = (run_dir / "report.html").read_text(encoding="utf-8")
    assert report.startswith("<!doctype html>")
    assert "<style>" in report
    assert "<script>" in report
    assert 'src="' not in report
    assert 'rel="stylesheet"' not in report


def test_html_contains_complete_candidate_and_audit_data(
    tmp_path, run_result
):
    report = _report(run_result, tmp_path)
    assert "Attention Is All You Need" in report
    assert "Ada Lovelace" in report
    assert "found" in report
    assert "ada@university.example" in report
    assert "https://example.test/contact" in report
    assert "Google Scholar" in report
    assert "LinkedIn" in report
    assert "Maimai" in report
    assert "证据" in report
    assert "各数据源尝试记录" in report
    assert "fixture" in report


def test_html_uses_chinese_article_design_and_original_content(
    tmp_path, run_result
):
    report = _report(run_result, tmp_path)
    soup = BeautifulSoup(report, "html.parser")

    assert soup.html["lang"] == "zh-CN"
    assert soup.select_one("article.doc")
    assert soup.select_one(".doc-header .doc-title").get_text(
        " ", strip=True
    ) == "Attention Is All You Need"
    assert "研究者招聘情报报告" in report
    assert "Fixture abstract" in report
    assert "--paper: #f7f7f5" in report
    assert "--ink: #1a1a1a" in report
    assert "ui-serif" in report
    assert "ui-monospace" in report


def test_html_localizes_all_static_dossier_and_audit_copy(
    tmp_path, run_result, monkeypatch
):
    monkeypatch.setattr(
        "researcher_recruiting.exporters.build_locator_links",
        lambda _author: {
            "google_scholar": "",
            "linkedin": "",
            "maimai": "",
        },
    )
    match = run_result.matches[0]
    normal_soup = BeautifulSoup(
        _report(run_result, tmp_path),
        "html.parser",
    )
    empty_report = _report(
        replace(
            run_result,
            matches=(
                replace(
                    match,
                    reasons=(),
                    evidence=(),
                    contact_points=(),
                ),
            ),
            source_results=(),
        ),
        tmp_path,
    )
    contact_without_evidence = replace(
        match.contact_points[0],
        evidence=(),
        metadata={},
    )
    nested_contact_evidence = Evidence(
        source="fixture",
        field="profile",
        value="Identity Evidence Value Direct Field Metadata",
        url="https://example.test/contact-evidence",
        collected_at="2026-07-20T05:06:07Z",
        candidate_id="nested-contact",
        metadata={"note": "Identity Evidence"},
    )
    source_without_evidence = replace(
        run_result.source_results[0],
        evidence=(),
    )
    homepage = ContactPoint(
        kind=ContactKind.HOMEPAGE,
        value="https://example.test/ada",
        source="fixture",
        source_url="https://example.test",
        collected_at="2026-07-20T05:06:07Z",
        confidence=90,
        direct=False,
        evidence=(nested_contact_evidence,),
        metadata={},
    )
    audit_report = _report(
        replace(
            run_result,
            matches=(
                replace(
                    match,
                    evidence=(),
                    contact_points=(
                        contact_without_evidence,
                        homepage,
                    ),
                ),
            ),
            source_results=(source_without_evidence,),
        ),
        tmp_path,
    )
    empty_soup = BeautifulSoup(empty_report, "html.parser")
    audit_soup = BeautifulSoup(audit_report, "html.parser")

    def node_text(node):
        assert node is not None
        return node.get_text(" ", strip=True)

    def direct_dt_labels(node):
        return [
            node_text(item)
            for item in node.select(
                ":scope > .audit-fields > div > dt"
            )
        ]

    def direct_sections(candidate):
        return {
            node_text(heading): heading.parent
            for heading in candidate.select(":scope > section > h3")
        }

    def direct_disclosures(candidate):
        return {
            node_text(summary): summary.parent
            for summary in candidate.select(
                ":scope > details > summary"
            )
        }

    candidate = normal_soup.select_one("#author-1")
    assert candidate is not None
    assert node_text(
        candidate.select_one(":scope > header > .eyebrow")
    ) == "作者 1"
    assert [
        node_text(item)
        for item in candidate.select(
            ":scope > .facts > div > dt"
        )
    ] == [
        "身份匹配",
        "置信度",
        "联系状态",
    ]

    sections = direct_sections(candidate)
    assert list(sections) == [
        "公开联系方式与资料",
        "仅用于定位的链接",
    ]
    assert [
        node_text(link)
        for link in sections["公开联系方式与资料"].select("a")
    ] == [
        "ada@university.example",
        "联系表单",
    ]
    assert [
        node_text(link)
        for link in sections["仅用于定位的链接"].select("a")
    ] == [
        "Google Scholar",
        "LinkedIn",
        "Maimai",
    ]

    disclosures = direct_disclosures(candidate)
    assert list(disclosures) == [
        "联系方式溯源",
        "身份匹配理由",
        "完整身份与联系证据",
        "各数据源尝试记录",
    ]
    assert "contact-provenance" in disclosures[
        "联系方式溯源"
    ]["class"]
    assert node_text(
        disclosures["身份匹配理由"].select_one(
            ":scope > ul > li"
        )
    ) == "paper overlap"

    evidence_item = disclosures["完整身份与联系证据"].select_one(
        ":scope > .audit-list > .evidence-item"
    )
    assert evidence_item is not None
    evidence_labels = [
        "来源",
        "字段",
        "值",
        "链接",
        "采集时间",
        "候选人 ID",
        "元数据",
    ]
    assert direct_dt_labels(evidence_item) == evidence_labels

    source_attempt = disclosures["各数据源尝试记录"].select_one(
        ':scope > .audit-list > .source-attempt[data-source="fixture"]'
    )
    assert source_attempt is not None
    source_evidence = source_attempt.select_one(
        ":scope > .audit-list > .source-evidence"
    )
    assert source_evidence is not None
    assert direct_dt_labels(source_evidence) == evidence_labels

    audit_candidate = audit_soup.select_one("#author-1")
    assert audit_candidate is not None
    audit_sections = direct_sections(audit_candidate)
    assert [
        node_text(link)
        for link in audit_sections[
            "公开联系方式与资料"
        ].select("a")
    ] == [
        "ada@university.example",
        "个人主页",
    ]
    audit_disclosures = direct_disclosures(audit_candidate)
    contact_points = audit_disclosures[
        "联系方式溯源"
    ].select(":scope > .audit-list > .contact-point")
    assert len(contact_points) == 2
    contact_labels = [
        "类型",
        "值",
        "来源",
        "来源链接",
        "采集时间",
        "置信度",
        "是否直接联系",
        "元数据",
    ]
    assert all(
        direct_dt_labels(point) == contact_labels
        for point in contact_points
    )
    assert node_text(
        contact_points[0].select_one(":scope > p.muted")
    ) == "未记录联系方式证据。"

    assert node_text(contact_points[1].select_one(":scope > h4")) == "证据"
    nested_evidence = contact_points[1].select_one(
        ":scope > .audit-list > .contact-evidence"
    )
    assert nested_evidence is not None
    assert direct_dt_labels(nested_evidence) == evidence_labels
    nested_fields = {
        node_text(item.select_one(":scope > dt")): node_text(
            item.select_one(":scope > dd")
        )
        for item in nested_evidence.select(
            ":scope > .audit-fields > div"
        )
    }
    assert nested_fields["值"] == (
        "Identity Evidence Value Direct Field Metadata"
    )
    assert nested_fields["元数据"] == "note Identity Evidence"

    metadata_field = next(
        item
        for item in contact_points[0].select(
            ":scope > .audit-fields > div"
        )
        if node_text(item.select_one(":scope > dt")) == "元数据"
    )
    assert node_text(
        metadata_field.select_one(":scope > dd > .muted")
    ) == "未记录。"

    audit_source_attempt = audit_disclosures[
        "各数据源尝试记录"
    ].select_one(
        ':scope > .audit-list > .source-attempt[data-source="fixture"]'
    )
    assert audit_source_attempt is not None
    assert node_text(
        audit_source_attempt.select_one(":scope > p > strong")
    ) == "fixture"
    assert node_text(
        audit_source_attempt.select_one(":scope > p")
    ).endswith("ok （0 条证据）")
    assert node_text(
        audit_source_attempt.select_one(":scope > p.muted")
    ) == "此来源未返回证据。"

    empty_candidate = empty_soup.select_one("#author-1")
    assert empty_candidate is not None
    empty_sections = direct_sections(empty_candidate)
    assert node_text(
        empty_sections["公开联系方式与资料"].select_one(
            ":scope > p.muted"
        )
    ) == "未找到经验证的公开职业联系方式。"
    assert node_text(
        empty_sections["仅用于定位的链接"].select_one(
            ":scope > p.muted"
        )
    ) == "没有可用的定位链接。"

    empty_disclosures = direct_disclosures(empty_candidate)
    assert node_text(
        empty_disclosures["联系方式溯源"].select_one(
            ":scope > p.muted"
        )
    ) == "未记录联系方式溯源。"
    assert node_text(
        empty_disclosures["身份匹配理由"].select_one(
            ":scope > p.muted"
        )
    ) == "未记录身份匹配理由。"
    assert node_text(
        empty_disclosures["完整身份与联系证据"].select_one(
            ":scope > p.muted"
        )
    ) == "未记录公开身份依据。"
    assert node_text(
        empty_disclosures["各数据源尝试记录"].select_one(
            ":scope > p.muted"
        )
    ) == "未记录来源尝试。"


def test_html_renders_deterministic_tldr_and_numbered_sections(
    tmp_path, run_result
):
    soup = BeautifulSoup(_report(run_result, tmp_path), "html.parser")
    tldr = soup.select_one(".tldr")

    assert tldr is not None
    assert "共 1 位作者" in tldr.get_text(" ", strip=True)
    assert "1 位找到公开职业联系方式" in tldr.get_text(
        " ", strip=True
    )
    assert [
        item.get_text(strip=True)
        for item in soup.select("h2 > .num")
    ] == ["01", "02", "03"]


def test_html_prioritizes_verified_email_as_best_contact(
    tmp_path, run_result
):
    soup = BeautifulSoup(_report(run_result, tmp_path), "html.parser")
    best = soup.select_one("#author-1 .best-contact")

    assert best is not None
    assert "最佳公开联系路径" in best.get_text(" ", strip=True)
    assert best.select_one(
        'a[href="mailto:ada@university.example"]'
    )


@pytest.mark.parametrize(
    ("identity_state", "contact_status"),
    (
        (IdentityState.AMBIGUOUS, ContactStatus.FOUND),
        (IdentityState.CONFIRMED, ContactStatus.NOT_FOUND),
    ),
)
def test_html_does_not_promote_unqualified_contact_route(
    tmp_path, run_result, identity_state, contact_status
):
    match = replace(
        run_result.matches[0],
        state=identity_state,
        contact_status=contact_status,
        contact_points=(
            ContactPoint(
                kind=ContactKind.HOMEPAGE,
                value="https://example.test/apparent-profile",
                source="fixture",
                source_url="https://example.test/evidence",
                collected_at="2026-07-20T03:04:05Z",
                confidence=80,
                direct=False,
            ),
        ),
    )

    soup = BeautifulSoup(
        _report(replace(run_result, matches=(match,)), tmp_path),
        "html.parser",
    )
    best = soup.select_one("#author-1 .best-contact")
    profiles = soup.select_one(
        "#author-1 section:nth-of-type(1)"
    )

    assert best is not None
    assert "未找到经过核验的公开职业联系方式。" in best.get_text(
        " ", strip=True
    )
    assert best.select_one("a") is None
    assert profiles is not None
    assert profiles.select_one(
        'a[href="https://example.test/apparent-profile"]'
    )


def test_html_renders_original_submission_value_when_present(
    tmp_path, run_result
):
    paper = replace(
        run_result.paper,
        submitted_at='2026-07-20 <original> "UTC"',
    )
    soup = BeautifulSoup(
        _report(replace(run_result, paper=paper), tmp_path),
        "html.parser",
    )

    metadata = soup.select_one(".doc-meta")
    assert metadata is not None
    assert "提交时间 · 2026-07-20 <original> \"UTC\"" in metadata.get_text(
        " ", strip=True
    )


def test_html_omits_submission_metadata_when_absent(
    tmp_path, run_result
):
    paper = replace(run_result.paper, submitted_at=None)
    report = _report(replace(run_result, paper=paper), tmp_path)

    assert "提交时间 ·" not in report


def test_html_links_bare_orcid_using_evidence_profile_url(
    tmp_path, run_result
):
    orcid = Evidence(
        source="orcid",
        field="orcid",
        value="0000-0001-2345-6789",
        url="https://orcid.org/0000-0001-2345-6789",
        collected_at="2026-07-20T03:04:05Z",
    )
    match = replace(
        run_result.matches[0],
        evidence=(orcid,),
        contact_points=(),
    )
    soup = BeautifulSoup(
        _report(replace(run_result, matches=(match,)), tmp_path),
        "html.parser",
    )

    author = soup.select_one("#author-1")
    assert author is not None
    public_profiles = next(
        section
        for section in author.find_all("section", recursive=False)
        if section.h3
        and section.h3.get_text(" ", strip=True)
        == "公开联系方式与资料"
    )
    profile = public_profiles.select_one(
        'a[href="https://orcid.org/0000-0001-2345-6789"]'
    )
    assert profile is not None
    assert profile.get_text(" ", strip=True) == "ORCID"
    evidence_details = author.select_one(
        'details[data-audit-kind="evidence"]'
    )
    assert evidence_details is not None
    value_label = evidence_details.find("dt", string="值")
    assert value_label is not None
    evidence_value = value_label.find_next_sibling("dd")
    assert evidence_value is not None
    assert evidence_value.get_text(
        " ", strip=True
    ) == "0000-0001-2345-6789"


def test_html_uses_accessible_faint_ink_token(tmp_path, run_result):
    report = _report(run_result, tmp_path)

    assert "--ink-faint: #626262" in report


def test_html_prints_all_audit_evidence_without_controls(
    tmp_path, run_result
):
    report = _report(run_result, tmp_path)

    assert "@media print" in report
    assert (
        ".report-controls, .back-to-top { display: none !important; }"
        in report
    )
    assert ".author-index { position: static; }" in report
    assert (
        "details.audit-disclosure > * { display: block !important; }"
        in report
    )
    assert (
        "details.audit-disclosure > summary { display: none !important; }"
        in report
    )


def test_html_keeps_audit_details_closed_by_default(
    tmp_path, run_result
):
    soup = BeautifulSoup(_report(run_result, tmp_path), "html.parser")
    audits = soup.select("#author-1 details.audit-disclosure")

    assert len(audits) == 3
    assert all(not item.has_attr("open") for item in audits)
    assert {item["data-audit-kind"] for item in audits} == {
        "contact-provenance",
        "evidence",
        "source-attempts",
    }


def test_html_includes_recruiting_filters_and_enhancement_controls(
    tmp_path, run_result
):
    report = _report(run_result, tmp_path)
    soup = BeautifulSoup(report, "html.parser")

    assert soup.select_one("#candidate-search")
    assert soup.select_one("#contact-filter")
    assert soup.select_one("#audit-toggle")
    assert soup.select_one("#back-to-top")
    assert "IntersectionObserver" in report
    assert "audit-disclosure" in report
    assert "@media (max-width: 760px)" in report


def test_html_indexes_every_author_to_a_stable_dossier(
    tmp_path, duplicate_name_run
):
    soup = BeautifulSoup(
        _report(duplicate_name_run, tmp_path),
        "html.parser",
    )

    links = soup.select(".author-index a.author-index-link")
    dossiers = soup.select(".candidate-card")
    assert [link["href"] for link in links] == [
        "#author-1",
        "#author-2",
    ]
    assert [item["id"] for item in dossiers] == [
        "author-1",
        "author-2",
    ]
    assert all(link.get_text(strip=True) for link in links)


def test_html_scopes_duplicate_names_by_author_id(
    tmp_path, duplicate_name_run
):
    report = _report(duplicate_name_run, tmp_path)
    first = report.index('id="author-1"')
    second = report.index('id="author-2"')
    assert first < second
    first_author = report[first:second]
    second_author = report[second:]
    assert "github" in first_author
    assert "orcid" not in first_author
    assert "orcid" in second_author
    assert "github" not in second_author


def test_html_renders_nonwinning_source_evidence_under_its_author_attempt(
    tmp_path, duplicate_name_run
):
    nonwinning_evidence = Evidence(
        source="orcid",
        field="profile",
        value="nonwinning-profile-token=source-secret",
        url="https://orcid.example/0000-0002",
        collected_at="2026-07-20T01:02:03Z",
        candidate_id="nonwinning-candidate",
        metadata={"match": "name-only", "api_key": "metadata-secret"},
    )
    second_attempt = replace(
        duplicate_name_run.source_results[1],
        status=SourceStatus.OK,
        evidence=(nonwinning_evidence,),
    )
    report = _report(
        replace(
            duplicate_name_run,
            source_results=(
                duplicate_name_run.source_results[0],
                second_attempt,
            ),
        ),
        tmp_path,
    )
    soup = BeautifulSoup(report, "html.parser")
    first_author = soup.select_one("#author-1")
    second_author = soup.select_one("#author-2")
    assert first_author is not None
    assert second_author is not None
    first_attempts = first_author.select(".source-attempt")
    second_attempts = second_author.select(".source-attempt")
    assert [item["data-source"] for item in first_attempts] == ["github"]
    assert [item["data-source"] for item in second_attempts] == ["orcid"]
    second_text = second_attempts[0].get_text(" ", strip=True)
    assert "profile" in second_text
    assert "nonwinning-profile-token=[REDACTED]" in second_text
    assert "2026-07-20T01:02:03Z" in second_text
    assert "nonwinning-candidate" in second_text
    assert "name-only" in second_text
    assert "metadata-secret" not in report
    assert "source-secret" not in report
    assert "nonwinning-profile-token" not in first_author.get_text()


def test_html_renders_complete_contact_point_provenance(
    tmp_path, run_result
):
    nested_evidence = Evidence(
        source="department_directory",
        field="email",
        value="ada@university.example",
        url="https://example.test/directory/ada",
        collected_at="2026-07-20T02:03:04Z",
        candidate_id="directory-ada",
        metadata={"visibility": "public_professional"},
    )
    contact = ContactPoint(
        kind=ContactKind.PROFESSIONAL_EMAIL,
        value="ada@university.example",
        source="department_directory",
        source_url="https://example.test/directory",
        collected_at="2026-07-20T03:04:05Z",
        confidence=97,
        direct=True,
        evidence=(nested_evidence,),
        metadata={
            "visibility": "public_professional",
            "token": "contact-secret",
        },
    )
    match = replace(
        run_result.matches[0],
        contact_points=(contact,),
    )
    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )
    soup = BeautifulSoup(report, "html.parser")
    author = soup.select_one("#author-1")
    assert author is not None
    provenance = author.select_one(".contact-point")
    assert provenance is not None
    text = provenance.get_text(" ", strip=True)
    for expected in (
        "professional_email",
        "ada@university.example",
        "department_directory",
        "https://example.test/directory",
        "2026-07-20T03:04:05Z",
        "97",
        "true",
        "email",
        "https://example.test/directory/ada",
        "2026-07-20T02:03:04Z",
        "directory-ada",
        "public_professional",
    ):
        assert expected in text
    assert provenance.select_one('a[href="mailto:ada@university.example"]')
    assert provenance.select_one(
        'a[href="https://example.test/directory"]'
    )
    assert "contact-secret" not in report


def test_html_escapes_content_and_omits_unsafe_evidence_url(
    tmp_path, run_result, evidence_factory
):
    unsafe = evidence_factory(
        field="paper_title",
        value="Research <Lab>",
        url="javascript:alert(2)",
    )
    match = replace(
        run_result.matches[0],
        author=replace(
            run_result.matches[0].author,
            affiliation="<img src=x onerror=alert(3)>",
        ),
        evidence=(unsafe,),
        contact_points=(),
    )
    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )
    assert "<img src=x onerror=alert(3)>" not in report
    assert "javascript:alert(2)" not in report
    assert "&lt;img src=x onerror=alert(3)&gt;" in report
    assert "Research &lt;Lab&gt;" in report


def test_html_publishes_while_omitting_malformed_evidence_urls(
    tmp_path, run_result, evidence_factory
):
    malformed = evidence_factory(
        field="homepage",
        value="https://[",
        url="https://exa mple.test/evidence",
    )
    match = replace(
        run_result.matches[0],
        evidence=(malformed,),
        contact_points=(),
    )

    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )

    assert "Attention Is All You Need" in report
    assert "https://[" not in report
    assert "https://exa mple.test/evidence" not in report


def test_html_publishes_while_omitting_malformed_contact_urls(
    tmp_path, run_result
):
    malformed = ContactPoint(
        kind=ContactKind.HOMEPAGE,
        value="https://exa mple.test/profile",
        source="department_directory",
        source_url="https://example.test:bad/profile",
        collected_at="2026-07-20T04:05:06Z",
        confidence=90,
        direct=False,
    )
    match = replace(
        run_result.matches[0],
        evidence=(),
        contact_points=(malformed,),
    )

    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )

    assert "Attention Is All You Need" in report
    assert "https://exa mple.test/profile" not in report
    assert "https://example.test:bad/profile" not in report
    assert "department_directory" in report


@pytest.mark.parametrize(
    "value",
    (
        "https://[",
        "https://exa mple.test/path",
        "https://example.test:bad/path",
        "https://example.test:99999/path",
        "https://:443/path",
        "https://example.test/control\x00path",
    ),
)
def test_safe_href_rejects_malformed_http_urls(value):
    assert _safe_href(value) is None


@pytest.mark.parametrize(
    "value",
    (
        "https://example.test/path?q=one",
        "https://例え.テスト/研究者",
    ),
)
def test_safe_href_preserves_valid_https_urls(value):
    assert _safe_href(value) == value


def test_html_omits_non_http_url_values_but_keeps_normal_evidence_text(
    tmp_path, run_result, evidence_factory
):
    evidence = (
        evidence_factory(
            field="homepage",
            value="ftp://example.test/profile",
        ),
        evidence_factory(
            field="github",
            value="mailto:researcher@example.test",
        ),
        evidence_factory(
            field="openreview",
            value="researcher-profile:ada",
        ),
        evidence_factory(
            field="orcid",
            value="0000-0001-2345-6789",
        ),
    )
    match = replace(
        run_result.matches[0],
        evidence=evidence,
        contact_points=(),
    )

    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )

    assert "ftp://example.test/profile" not in report
    assert "mailto:researcher@example.test" not in report
    assert "researcher-profile:ada" not in report
    assert "0000-0001-2345-6789" in report


def test_html_omits_malformed_email_instead_of_making_mailto_link(
    tmp_path, run_result
):
    email = replace(
        next(
            point
            for point in run_result.matches[0].contact_points
            if point.kind is ContactKind.PROFESSIONAL_EMAIL
        ),
        value="javascript:alert(1)",
    )
    match = replace(
        run_result.matches[0],
        contact_points=(email,),
    )

    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )

    assert "javascript:alert(1)" not in report
    assert "mailto:javascript" not in report


@pytest.mark.parametrize(
    "value",
    (
        "ada@example.test?subject=unsafe",
        "ada@example.test#fragment",
        "ada@example.test\x00",
        "ada@example.test\x1f",
    ),
)
def test_html_omits_email_with_uri_or_control_delimiters(
    tmp_path, run_result, value
):
    email = replace(
        next(
            point
            for point in run_result.matches[0].contact_points
            if point.kind is ContactKind.PROFESSIONAL_EMAIL
        ),
        value=value,
    )
    match = replace(
        run_result.matches[0],
        contact_points=(email,),
    )

    report = _report(
        replace(run_result, matches=(match,)),
        tmp_path,
    )

    assert "mailto:" not in report
    assert value not in report


def test_html_redacts_secrets_from_paper_and_candidate_data(
    tmp_path, run_result, evidence_factory
):
    paper = replace(
        run_result.paper,
        title="Report token=paper-secret",
        abstract="Authorization: Bearer abstract-secret",
    )
    evidence = evidence_factory(
        field="note",
        value="api_key=evidence-secret",
    )
    contact_form = replace(
        next(
            point
            for point in run_result.matches[0].contact_points
            if point.kind is ContactKind.CONTACT_FORM
        ),
        value="https://example.test/contact?client_secret=contact-secret",
    )
    match = replace(
        run_result.matches[0],
        author=replace(
            run_result.matches[0].author,
            affiliation="token=candidate-secret",
        ),
        reasons=("api-key=reason-secret",),
        evidence=(evidence,),
        contact_points=(contact_form,),
    )

    report = _report(
        replace(run_result, paper=paper, matches=(match,)),
        tmp_path,
    )

    for secret in (
        "paper-secret",
        "abstract-secret",
        "candidate-secret",
        "reason-secret",
        "evidence-secret",
        "contact-secret",
    ):
        assert secret not in report
    assert "[REDACTED]" in report


def test_html_redacts_secret_bearing_source_errors(
    tmp_path, run_result
):
    run = replace(
        run_result,
        source_results=(
            SourceResult(
                "unsafe",
                SourceStatus.SOURCE_UNAVAILABLE,
                error="Authorization: Bearer super-secret-token",
                author_name="Ada Lovelace",
            ),
        ),
    )
    report = _report(run, tmp_path)
    assert "super-secret-token" not in report
    assert "[REDACTED]" in report


def test_jsonable_redacts_opaque_paper_email_provenance():
    author = parse_atom_feed(
        """\
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1706.03762v7</id>
            <title>Paper</title>
            <author>
              <name>Ada Lovelace</name>
              <email>ada@example.org</email>
            </author>
          </entry>
        </feed>
        """
    )[0].authors[0]

    serialized = _jsonable(author)

    assert serialized["email_provenance"] is None
    json.dumps(serialized)
