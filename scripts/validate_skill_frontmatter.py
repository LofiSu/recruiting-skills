#!/usr/bin/env python3
"""Validate Agent Skill frontmatter with the Python standard library.

This is a portable stand-in for skill-creator's ``quick_validate.py``.
It checks the same core contract (required ``name`` and ``description``,
kebab-case name, description limits, and allowed keys) without PyYAML or a
machine-local Codex install. Frontmatter must be a flat mapping of scalars.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
ALLOWED_PROPERTIES = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")
FRONTMATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)


def validate_skill(skill_path: Path) -> tuple[bool, str]:
    """Return whether ``skill_path`` contains a valid ``SKILL.md`` frontmatter."""
    skill_md = Path(skill_path) / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter, error = _parse_flat_frontmatter(match.group(1))
    if error:
        return False, error
    assert frontmatter is not None

    unexpected = sorted(set(frontmatter) - ALLOWED_PROPERTIES)
    if unexpected:
        allowed = ", ".join(sorted(ALLOWED_PROPERTIES))
        return (
            False,
            "Unexpected key(s) in SKILL.md frontmatter: "
            f"{', '.join(unexpected)}. Allowed properties are: {allowed}",
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter["name"].strip()
    if not name:
        return False, "Name must be a non-empty string"
    if not NAME_PATTERN.fullmatch(name):
        return (
            False,
            f"Name '{name}' should be kebab-case "
            "(lowercase letters, digits, and hyphens only)",
        )
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return (
            False,
            f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens",
        )
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return (
            False,
            f"Name is too long ({len(name)} characters). "
            f"Maximum is {MAX_SKILL_NAME_LENGTH} characters.",
        )

    description = frontmatter["description"].strip()
    if not description:
        return False, "Description must be a non-empty string"
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return (
            False,
            f"Description is too long ({len(description)} characters). "
            f"Maximum is {MAX_DESCRIPTION_LENGTH} characters.",
        )

    return True, "Skill is valid!"


def _parse_flat_frontmatter(text: str) -> tuple[dict[str, str] | None, str | None]:
    data: dict[str, str] = {}
    for offset, line in enumerate(text.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in {" ", "\t"}:
            return None, f"Unsupported nested YAML in frontmatter line {offset}"
        if ":" not in line:
            return None, f"Invalid frontmatter line {offset}"
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            return None, f"Invalid frontmatter line {offset}"
        if value in {"", "|", ">", "|-", ">-", "|+", ">+"}:
            return None, f"Unsupported multiline frontmatter value for '{key}'"
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        data[key] = value
    return data, None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "Usage: python3 scripts/validate_skill_frontmatter.py <skill_directory>",
            file=sys.stderr,
        )
        return 1
    valid, message = validate_skill(Path(args[0]))
    print(message)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
