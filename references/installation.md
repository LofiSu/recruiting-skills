# Installation

The repository follows the [Agent Skills open standard](https://agentskills.io/)
and uses one platform-neutral `SKILL.md`. Use Python 3.11 or newer.

## Install dependencies

From the skill directory, install the package into the selected Python
environment:

```bash
python --version
python -m pip install .
```

For development and verification, install the `dev` extra:

```bash
python -m pip install -e '.[dev]'
```

After installing dependencies, the core skill runs the bundled script from
this directory:

```bash
python scripts/researcher_recruiting.py "<paper>" --output results
```

## Agent discovery locations

Clone or symlink this repository into any supported discovery location:

| Scope | Location |
| --- | --- |
| Generic shared | `~/.agents/skills/researcher-recruiting-skill/` |
| Claude Code personal | `~/.claude/skills/researcher-recruiting-skill/` |
| Claude Code project | `.claude/skills/researcher-recruiting-skill/` |
| OpenCode personal | `~/.config/opencode/skills/researcher-recruiting-skill/` |
| OpenCode project | `.opencode/skills/researcher-recruiting-skill/` |
| Codex personal | `${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill/` |

Symlinking or cloning the same repository into a discovery location keeps one
implementation. Do not duplicate or maintain platform-specific `SKILL.md`
files.

## Standalone CLI

Agent skill discovery is optional. Install from the repository and invoke the
console command directly:

```bash
python -m pip install .
researcher-recruiting <paper> --output results
```
