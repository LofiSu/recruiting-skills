# Installation

The repository follows the [Agent Skills open standard](https://agentskills.io/)
and uses one platform-neutral `SKILL.md`. Use Python 3.11 or newer.

## Select Python

Validate a nonempty user-supplied `PYTHON_BIN` and fail immediately if it is
incompatible. When `PYTHON_BIN` is unset or empty, try launchers in descending
preferred order and select the first one that runs Python 3.11 or newer:

```bash
if [ -n "${PYTHON_BIN:-}" ]; then
  if ! "$PYTHON_BIN" -c \
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
  then
    printf '%s\n' "$PYTHON_BIN must run Python 3.11 or newer." >&2
    exit 1
  fi
else
  for candidate in python3.14 python3.13 python3.12 python3.11 python3 python
  do
    if command -v "$candidate" >/dev/null 2>&1 &&
      "$candidate" -c \
        'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
    then
      PYTHON_BIN=$(command -v "$candidate")
      break
    fi
  done

  if [ -z "${PYTHON_BIN:-}" ]; then
    printf '%s\n' 'Python 3.11 or newer is required.' >&2
    exit 1
  fi
fi

export PYTHON_BIN
```

To override discovery, set `PYTHON_BIN` to a Python executable before running
the block, for example `PYTHON_BIN=/path/to/python3.11`. An incompatible
explicit override is an error and does not fall back to another launcher.

## Install dependencies

From the skill directory, use the selected executable for installation:

```bash
"$PYTHON_BIN" --version
"$PYTHON_BIN" -m pip install .
```

For development and verification, install the `dev` extra:

```bash
"$PYTHON_BIN" -m pip install -e '.[dev]'
```

After installing dependencies, use that same executable to run the bundled
script from this directory:

```bash
"$PYTHON_BIN" scripts/researcher_recruiting.py "<paper>" --output results
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
"$PYTHON_BIN" -m pip install .
researcher-recruiting <paper> --output results
```
