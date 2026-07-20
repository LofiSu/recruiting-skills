import os
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).parents[1]


def _installation_selector() -> str:
    text = (ROOT / "references/installation.md").read_text(encoding="utf-8")
    assert "## Select Python" in text
    section = text.split("## Select Python", 1)[1].split("## Install", 1)[0]
    return section.split("```bash", 1)[1].split("```", 1)[0]


def _write_fake_python(path: Path, *, version: str, compatible: bool) -> None:
    probe_exit = 0 if compatible else 1
    path.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"-c\" ]; then exit {probe_exit}; fi\n"
        f"if [ \"$1\" = \"--version\" ]; then echo 'Python {version}'; exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_selector(tmp_path: Path, *, python_bin: str = ""):
    return subprocess.run(
        [
            "/bin/sh",
            "-c",
            _installation_selector() + '\nprintf "%s" "$PYTHON_BIN"\n',
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": str(tmp_path), "PYTHON_BIN": python_bin},
    )


def test_skill_frontmatter_matches_agent_skills_core():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "researcher-recruiting-skill"
    assert len(metadata["description"]) <= 1024
    assert "public professional contact" in metadata["description"].lower()
    assert len(body.splitlines()) < 500


def test_core_skill_has_no_platform_specific_runtime_instructions():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8").casefold()
    forbidden = (
        "codex app",
        "workspace-dependencies",
        "/private/tmp",
        "request network access",
        "allowedtools",
        "dangerously-skip-permissions",
    )
    assert not any(item in text for item in forbidden)


def test_skill_uses_relative_bundled_paths():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "scripts/researcher_recruiting.py" in text
    assert "references/installation.md" in text
    assert "run-log.json" in text


def test_required_commands_reuse_selected_python_launcher():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    installation = (ROOT / "references/installation.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert '"$PYTHON_BIN" scripts/researcher_recruiting.py' in skill
    assert '"$PYTHON_BIN" -m pip install .' in installation
    assert '"$PYTHON_BIN" -m pip install -e \'.[dev]\'' in installation
    assert '"$PYTHON_BIN" scripts/researcher_recruiting.py' in installation
    assert '"$PYTHON_BIN" -m pip install .' in readme


def test_python_launcher_discovery_and_version_validation_are_documented():
    text = (ROOT / "references/installation.md").read_text(encoding="utf-8")

    assert "user-supplied `PYTHON_BIN`" in text
    assert "python3.14 python3.13 python3.12 python3.11 python3 python" in text
    assert "Python 3.11 or newer" in text
    assert '"$PYTHON_BIN" -c' in text


def test_launcher_discovery_supports_path_with_only_python311(tmp_path):
    launcher = tmp_path / "python3.11"
    _write_fake_python(
        launcher,
        version="3.11.9",
        compatible=True,
    )
    result = _run_selector(tmp_path)

    assert result.returncode == 0
    assert result.stdout.endswith(str(launcher))


def test_launcher_discovery_skips_incompatible_earlier_candidate(tmp_path):
    old_python = tmp_path / "python3"
    compatible_python = tmp_path / "python"
    _write_fake_python(old_python, version="3.9.18", compatible=False)
    _write_fake_python(
        compatible_python,
        version="3.11.9",
        compatible=True,
    )

    result = _run_selector(tmp_path)

    assert result.returncode == 0
    assert result.stdout.endswith(str(compatible_python))


def test_explicit_incompatible_launcher_fails_without_fallback(tmp_path):
    old_python = tmp_path / "old-python"
    compatible_python = tmp_path / "python3.11"
    _write_fake_python(old_python, version="3.9.18", compatible=False)
    _write_fake_python(
        compatible_python,
        version="3.11.9",
        compatible=True,
    )

    result = _run_selector(tmp_path, python_bin=str(old_python))

    assert result.returncode != 0
    assert "must run Python 3.11 or newer" in result.stderr
