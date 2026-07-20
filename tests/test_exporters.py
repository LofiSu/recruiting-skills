import json
from dataclasses import replace

import pytest

from researcher_recruiting.exporters import _jsonable, write_artifacts
from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactStatus,
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


def test_html_scopes_duplicate_names_by_author_id(
    tmp_path, duplicate_name_run
):
    report = _report(duplicate_name_run, tmp_path)
    first = report.index('id="author-1"')
    second = report.index('id="author-2"')
    assert first < second
    assert "github" in report[first:second]
    assert "orcid" in report[second:]


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
