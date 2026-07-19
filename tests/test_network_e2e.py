import json
import os

import pytest

from researcher_recruiting.cli import run_cli


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
