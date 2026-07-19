import csv
import json
from dataclasses import replace

from researcher_recruiting.exporters import write_artifacts
from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactPoint,
    ContactStatus,
    IdentityMatch,
    PaperRecord,
    RunResult,
    SourceResult,
    SourceStatus,
)


def test_write_artifacts_always_creates_five_files(tmp_path, run_result):
    run_dir = write_artifacts(run_result, tmp_path)
    assert {path.name for path in run_dir.iterdir()} == {
        "report.md",
        "candidates.csv",
        "candidates.json",
        "evidence.json",
        "run-log.json",
    }


def test_candidates_csv_has_stable_recruiting_columns(
    tmp_path, run_result
):
    run_dir = write_artifacts(run_result, tmp_path)
    with (run_dir / "candidates.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        header = next(csv.reader(handle))
    assert header[:5] == [
        "arxiv_id",
        "paper_title",
        "author_order",
        "author_name",
        "original_affiliation",
    ]
    assert "recruiting_notes" in header
    assert "contact_status" in header
    assert "contact_form" in header


def test_json_artifacts_serialize_enums_and_keep_provenance(
    tmp_path, run_result
):
    run_dir = write_artifacts(run_result, tmp_path)
    candidates = json.loads(
        (run_dir / "candidates.json").read_text(encoding="utf-8")
    )
    evidence = json.loads(
        (run_dir / "evidence.json").read_text(encoding="utf-8")
    )
    assert candidates[0]["identity_state"] == "probable"
    assert evidence[0]["source"] == "fixture"
    assert evidence[0]["collected_at"].endswith("Z")


def test_markdown_contains_clickable_source_and_locator_links(
    tmp_path, run_result
):
    report = (
        write_artifacts(run_result, tmp_path) / "report.md"
    ).read_text(encoding="utf-8")
    assert "[arXiv](https://arxiv.org/abs/1706.03762)" in report
    assert "[Google Scholar](" in report
    assert "Evidence" in report
    assert "- Contact status: `found`" in report
    assert (
        "- Direct public contacts: "
        "[email](mailto:ada@university.example), "
        "[contact form](https://example.test/contact)"
    ) in report
    assert "- Locator-only: [Google Scholar](" in report


def test_candidates_export_structured_contacts_and_status(
    tmp_path, run_result
):
    run_dir = write_artifacts(run_result, tmp_path)
    candidates = json.loads(
        (run_dir / "candidates.json").read_text(encoding="utf-8")
    )
    record = candidates[0]
    assert record["contact_status"] == "found"
    assert record["email"] == "ada@university.example"
    assert record["contact_form"] == "https://example.test/contact"
    assert {
        point["kind"] for point in record["contact_points"]
    } >= {
        "professional_email",
        "google_scholar_locator",
        "linkedin_locator",
        "maimai_locator",
    }


def test_primary_contacts_require_direct_contact_points(
    tmp_path, run_result
):
    indirect_points = (
        ContactPoint(
            kind=ContactKind.PROFESSIONAL_EMAIL,
            value="private@example.test",
            source="inferred",
            source_url="https://example.test/inferred",
            collected_at="2026-07-18T00:00:00Z",
            confidence=10,
            direct=False,
        ),
        ContactPoint(
            kind=ContactKind.CONTACT_FORM,
            value="https://example.test/inferred-contact",
            source="inferred",
            source_url="https://example.test/inferred",
            collected_at="2026-07-18T00:00:00Z",
            confidence=10,
            direct=False,
        ),
    )
    match = replace(
        run_result.matches[0],
        contact_points=indirect_points
        + run_result.matches[0].contact_points,
    )
    run = replace(run_result, matches=(match,))
    candidates = json.loads(
        (
            write_artifacts(run, tmp_path) / "candidates.json"
        ).read_text(encoding="utf-8")
    )
    assert candidates[0]["email"] == "ada@university.example"
    assert (
        candidates[0]["contact_form"]
        == "https://example.test/contact"
    )


def test_profile_flat_fields_fall_back_to_legacy_evidence(
    tmp_path, run_result, evidence_factory
):
    homepage = evidence_factory(
        field="homepage",
        value="https://example.test/legacy-homepage",
    )
    match = replace(
        run_result.matches[0],
        evidence=run_result.matches[0].evidence + (homepage,),
    )
    run = replace(run_result, matches=(match,))
    candidates = json.loads(
        (
            write_artifacts(run, tmp_path) / "candidates.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        candidates[0]["homepage"]
        == "https://example.test/legacy-homepage"
    )


def test_report_explains_when_no_verified_contact_exists(
    tmp_path, run_result
):
    match = replace(
        run_result.matches[0],
        contact_status=ContactStatus.NOT_FOUND,
        contact_points=(),
    )
    run = replace(run_result, matches=(match,))
    report = (
        write_artifacts(run, tmp_path) / "report.md"
    ).read_text(encoding="utf-8")
    section = report.split("## 1. Ada Lovelace", 1)[1]
    assert "- Contact status: `not_found`" in section
    assert "No verified public professional contact was found." in section


def test_run_log_redacts_secret_bearing_errors(tmp_path, run_result):
    unsafe = type(run_result)(
        paper=run_result.paper,
        matches=run_result.matches,
        source_results=(
            SourceResult(
                "unsafe",
                SourceStatus.SOURCE_UNAVAILABLE,
                error="Authorization: Bearer super-secret-token",
                author_name="Ada Lovelace",
            ),
        ),
    )
    run_dir = write_artifacts(unsafe, tmp_path)
    log = (run_dir / "run-log.json").read_text(encoding="utf-8")
    assert "super-secret-token" not in log
    assert "[REDACTED]" in log


def test_run_log_groups_source_attempts_by_author(tmp_path, run_result):
    run_dir = write_artifacts(run_result, tmp_path)
    log = json.loads(
        (run_dir / "run-log.json").read_text(encoding="utf-8")
    )
    author = log["authors"][0]
    assert author["author_name"] == "Ada Lovelace"
    assert author["contact_status"] == "found"
    assert {attempt["status"] for attempt in author["source_attempts"]} == {
        "ok"
    }


def test_run_log_scopes_duplicate_names_by_author_id(tmp_path, run_result):
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
    run = RunResult(
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

    log = json.loads(
        (
            write_artifacts(run, tmp_path) / "run-log.json"
        ).read_text(encoding="utf-8")
    )

    assert [author["author_order"] for author in log["authors"]] == [1, 2]
    assert [author["author_id"] for author in log["authors"]] == [
        "1706.03762:author:1",
        "1706.03762:author:2",
    ]
    assert [
        [attempt["source"] for attempt in author["source_attempts"]]
        for author in log["authors"]
    ] == [["github"], ["orcid"]]


def test_exporters_use_legacy_author_alignment_when_matches_are_reversed(
    tmp_path, run_result
):
    first = run_result.matches[0]
    second_seed = AuthorSeed(
        name="Charles Babbage",
        affiliation="Analytical Engines",
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
    run = RunResult(
        paper=paper,
        matches=(second, first),
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

    run_dir = write_artifacts(run, tmp_path)
    candidates = json.loads(
        (run_dir / "candidates.json").read_text(encoding="utf-8")
    )
    log = json.loads(
        (run_dir / "run-log.json").read_text(encoding="utf-8")
    )

    assert [item["author_order"] for item in candidates] == [2, 1]
    assert [author["author_order"] for author in log["authors"]] == [2, 1]
    assert [
        [attempt["source"] for attempt in author["source_attempts"]]
        for author in log["authors"]
    ] == [["orcid"], ["github"]]
