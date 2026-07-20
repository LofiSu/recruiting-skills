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


def _assert_real_run_report(report):
    for author in EXPECTED_AUTHORS:
        assert author in report
    assert "source_unavailable" in report or "blocked_by_robots" in report


def test_real_run_report_validation_rejects_empty_payload():
    with pytest.raises(AssertionError):
        _assert_real_run_report("")


def test_real_run_report_validation_requires_upstream_failure():
    report = "\n".join(EXPECTED_AUTHORS)
    with pytest.raises(AssertionError):
        _assert_real_run_report(report)


@pytest.mark.network
@pytest.mark.asyncio
async def test_real_arxiv_paper_generates_html_report(tmp_path):
    if os.getenv("RUN_NETWORK_TESTS") != "1":
        pytest.skip("set RUN_NETWORK_TESTS=1 to enable")
    exit_code = await run_cli(
        ["1706.03762", "--output", str(tmp_path), "--refresh"]
    )
    assert exit_code == 0
    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert {path.name for path in run_dirs[0].iterdir()} == {"report.html"}
    report = (run_dirs[0] / "report.html").read_text(encoding="utf-8")
    _assert_real_run_report(report)
