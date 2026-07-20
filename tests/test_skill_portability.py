import os
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).parents[1]


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
    assert "python3.12 python3.11 python3 python" in text
    assert "Python 3.11 or newer" in text
    assert '"$PYTHON_BIN" -c' in text


def test_launcher_discovery_supports_path_with_only_python311(tmp_path):
    text = (ROOT / "references/installation.md").read_text(encoding="utf-8")
    assert "## Select Python" in text
    section = text.split("## Select Python", 1)[1].split("## Install", 1)[0]
    shell = section.split("```bash", 1)[1].split("```", 1)[0]

    launcher = tmp_path / "python3.11"
    launcher.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-c\" ]; then exit 0; fi\n"
        "if [ \"$1\" = \"--version\" ]; then echo 'Python 3.11.9'; exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    result = subprocess.run(
        ["/bin/sh", "-c", shell + '\nprintf "%s" "$PYTHON_BIN"\n'],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": str(tmp_path), "PYTHON_BIN": ""},
    )

    assert result.stdout.endswith(str(launcher))
