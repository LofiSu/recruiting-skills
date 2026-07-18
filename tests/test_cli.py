from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from researcher_recruiting.cli import build_pipeline, run_cli
from researcher_recruiting.sources.arxiv import PaperNotFound


@pytest.mark.asyncio
async def test_cli_returns_two_for_unresolvable_paper(monkeypatch, capsys):
    class FailingPipeline:
        async def run(self, paper_input, refresh=False):
            raise PaperNotFound(paper_input)

    monkeypatch.setattr(
        "researcher_recruiting.cli.build_pipeline",
        lambda settings: FailingPipeline(),
    )
    assert await run_cli(["unknown paper"]) == 2
    assert "could not resolve paper" in capsys.readouterr().err.lower()


@pytest.mark.asyncio
async def test_cli_passes_refresh_output_and_explicit_sources(
    monkeypatch, tmp_path, run_result
):
    class RecordingPipeline:
        def __init__(self):
            self.call = None

        async def run(
            self, paper_input, refresh=False, requested_sources=()
        ):
            self.call = (
                paper_input,
                refresh,
                tuple(requested_sources),
            )
            return run_result

    pipeline = RecordingPipeline()
    monkeypatch.setattr(
        "researcher_recruiting.cli.build_pipeline",
        lambda settings: pipeline,
    )
    code = await run_cli(
        [
            "1706.03762",
            "--refresh",
            "--output",
            str(tmp_path),
            "--sources",
            "dblp,pubmed",
        ]
    )
    assert code == 0
    assert pipeline.call == (
        "1706.03762",
        True,
        ("dblp", "pubmed"),
    )
    assert next(tmp_path.iterdir()).is_dir()


@pytest.mark.asyncio
async def test_cli_unknown_source_returns_two(monkeypatch, capsys):
    class RejectingPipeline:
        async def run(
            self, paper_input, refresh=False, requested_sources=()
        ):
            raise ValueError("unknown source: made_up")

    monkeypatch.setattr(
        "researcher_recruiting.cli.build_pipeline",
        lambda settings: RejectingPipeline(),
    )
    assert (
        await run_cli(["1706.03762", "--sources", "made_up"]) == 2
    )
    assert "unknown source" in capsys.readouterr().err.lower()


def test_default_pipeline_registers_only_callable_sources(settings):
    pipeline = build_pipeline(settings)
    selected = pipeline.source_registry.select(("cs.CL",))
    assert selected
    assert all(callable(getattr(source, "enrich", None)) for source in selected)
    assert Path(settings.cache_path).exists()


def test_script_wrapper_does_not_shadow_package():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/researcher_recruiting.py",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "researcher-recruiting" in completed.stdout


def test_default_pipeline_falls_back_when_user_cache_is_unwritable(
    monkeypatch, settings
):
    attempted = []

    class DenyingFirstCache:
        def __init__(self, path):
            attempted.append(Path(path))
            if len(attempted) == 1:
                raise PermissionError("sandbox denied user cache")

    monkeypatch.setattr(
        "researcher_recruiting.cli.SqliteCache", DenyingFirstCache
    )
    build_pipeline(settings)
    assert attempted[0] == settings.cache_path
    assert attempted[1].is_relative_to(Path(tempfile.gettempdir()))
