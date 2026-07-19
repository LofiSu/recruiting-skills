from pathlib import Path

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
