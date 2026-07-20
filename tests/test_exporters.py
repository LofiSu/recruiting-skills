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
    assert "Evidence" in report
    assert "Source attempts" in report
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
