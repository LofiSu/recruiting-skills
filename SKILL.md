---
name: researcher-recruiting-skill
description: Use when Codex needs to identify, enrich, or disambiguate authors of an arXiv paper for recruiting, talent research, academic sourcing, or researcher due diligence.
---

# Researcher Recruiting

Turn an arXiv URL, identifier, or exact title into reproducible,
evidence-backed recruiting artifacts. Use the bundled CLI as the source of
record; do not replace it with ad hoc searches.

## Workflow

1. Read [references/compliance.md](references/compliance.md). Read
   [references/sources.md](references/sources.md) when selecting, explaining,
   or troubleshooting sources.
2. Select Python 3.11 or newer. Try `python3.12`, then `python3.11`. In
   Codex App, use the Python path returned by the workspace-dependencies tool
   when system Python is older. Check with `"$PYTHON_BIN" --version`.
3. Reuse `/private/tmp/researcher-recruiting-venv` when
   `bin/python -c "import httpx, bs4, platformdirs"` succeeds. Otherwise,
   request network access for dependency installation and create the virtual
   environment outside a cloud-synced repository:

   ```bash
   "$PYTHON_BIN" -m venv /private/tmp/researcher-recruiting-venv
   /private/tmp/researcher-recruiting-venv/bin/python -m pip install -e '.[dev]'
   ```

4. From this skill directory, run:

   ```bash
   /private/tmp/researcher-recruiting-venv/bin/python scripts/researcher_recruiting.py "<arXiv URL, id, or title>" --output results
   ```

5. Add `--refresh` only when the user explicitly asks for fresh data. Let
   arXiv categories select field-specific indexes. Add
   `--sources name,name` only for an explicit user override.
6. Open the generated `run-log.json` before interpreting a blank field.
   Distinguish `not_found`, `source_unavailable`, and `blocked_by_robots`.
7. Review ambiguous matches and their evidence. Never upgrade an identity
   because names alone match.
8. Present `report.md` and `candidates.csv`. Mention the run directory and
   summarize unavailable sources. Preserve the JSON artifacts for audit or
   downstream automation.

## Required output contract

Every successful or partial run produces exactly:

- `report.md`
- `candidates.csv`
- `candidates.json`
- `evidence.json`
- `run-log.json`

Keep `recruiting_notes` blank unless the user asks for an assessment. Do not
send outreach or mutate external profiles.

## Boundaries

Google Scholar, ResearchGate, Academia.edu, LinkedIn, Maimai, and unlicensed
commercial indexes are locator-only. Never fetch or parse their result/profile
pages. Never request cookies, shared-account credentials, CAPTCHA solving,
paywall bypass, browser-fingerprint evasion, or access-control bypass.

If a public source fails, retain the author, record the source status, and
continue. Do not silently substitute a prohibited scraper.
