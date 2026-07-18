import csv
import json

from researcher_recruiting.exporters import write_artifacts
from researcher_recruiting.models import SourceResult, SourceStatus


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


def test_run_log_redacts_secret_bearing_errors(tmp_path, run_result):
    unsafe = type(run_result)(
        paper=run_result.paper,
        matches=run_result.matches,
        source_results=(
            SourceResult(
                "unsafe",
                SourceStatus.SOURCE_UNAVAILABLE,
                error="Authorization: Bearer super-secret-token",
            ),
        ),
    )
    run_dir = write_artifacts(unsafe, tmp_path)
    log = (run_dir / "run-log.json").read_text(encoding="utf-8")
    assert "super-secret-token" not in log
    assert "[REDACTED]" in log
