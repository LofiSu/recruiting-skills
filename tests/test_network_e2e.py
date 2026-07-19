import json
import os

import pytest

from researcher_recruiting.cli import run_cli


EXPECTED_AUTHORS = [
    "Ashish Vaswani",
    "Noam Shazeer",
    "Niki Parmar",
    "Jakob Uszkoreit",
    "Llion Jones",
    "Aidan N. Gomez",
    "Lukasz Kaiser",
    "Illia Polosukhin",
]
LOCATOR_KINDS = {
    "google_scholar_locator",
    "linkedin_locator",
    "maimai_locator",
}


def _assert_real_run_artifacts(candidates, run_log):
    assert [candidate["author_name"] for candidate in candidates] == (
        EXPECTED_AUTHORS
    )
    assert all(candidate["contact_status"] for candidate in candidates)

    run_log_authors = run_log["authors"]
    assert [author["author_name"] for author in run_log_authors] == (
        EXPECTED_AUTHORS
    )
    assert all(author["contact_status"] for author in run_log_authors)
    assert all(author["source_attempts"] for author in run_log_authors)
    assert any(
        attempt["status"] in {"source_unavailable", "blocked_by_robots"}
        for author in run_log_authors
        for attempt in author["source_attempts"]
    )

    for candidate in candidates:
        locator_points = [
            point
            for point in candidate["contact_points"]
            if point["kind"] in LOCATOR_KINDS
        ]
        assert len(locator_points) == 3
        assert {point["kind"] for point in locator_points} == LOCATOR_KINDS
        for point in locator_points:
            assert point["direct"] is False
            assert point["confidence"] == 0
            assert point["evidence"] == []
            assert point["metadata"] == {"mode": "locator_only"}


def test_real_run_artifact_validation_rejects_empty_payload():
    with pytest.raises(AssertionError):
        _assert_real_run_artifacts([], {"authors": []})


def _candidate_payload(author_name):
    return {
        "author_name": author_name,
        "contact_status": "not_found",
        "contact_points": [
            {
                "kind": kind,
                "direct": False,
                "confidence": 0,
                "evidence": [],
                "metadata": {"mode": "locator_only"},
            }
            for kind in LOCATOR_KINDS
        ],
    }


def test_real_run_artifact_validation_requires_upstream_failure():
    candidates = [_candidate_payload(name) for name in EXPECTED_AUTHORS]
    run_log = {
        "authors": [
            {
                "author_name": name,
                "contact_status": "not_found",
                "source_attempts": [
                    {
                        "status": (
                            "ok" if index % 2 == 0 else "not_found"
                        )
                    }
                ],
            }
            for index, name in enumerate(EXPECTED_AUTHORS)
        ]
    }

    with pytest.raises(AssertionError):
        _assert_real_run_artifacts(candidates, run_log)


@pytest.mark.network
@pytest.mark.asyncio
async def test_real_arxiv_paper_generates_all_artifacts(tmp_path):
    if os.getenv("RUN_NETWORK_TESTS") != "1":
        pytest.skip("set RUN_NETWORK_TESTS=1 to enable")
    exit_code = await run_cli(
        ["1706.03762", "--output", str(tmp_path), "--refresh"]
    )
    assert exit_code == 0
    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert {path.name for path in run_dirs[0].iterdir()} == {
        "report.md",
        "candidates.csv",
        "candidates.json",
        "evidence.json",
        "run-log.json",
    }
    candidates = json.loads(
        (run_dirs[0] / "candidates.json").read_text(encoding="utf-8")
    )
    run_log = json.loads(
        (run_dirs[0] / "run-log.json").read_text(encoding="utf-8")
    )
    _assert_real_run_artifacts(candidates, run_log)
    report = (run_dirs[0] / "report.md").read_text(encoding="utf-8")
    for candidate in candidates:
        section = report.split(
            f"## {candidate['author_order']}. {candidate['author_name']}",
            1,
        )[1].split("\n## ", 1)[0]
        assert "- Contact status: `" in section
        assert (
            "- Direct public contacts:" in section
            or "- Public profiles:" in section
            or "No verified public professional contact was found."
            in section
        )
