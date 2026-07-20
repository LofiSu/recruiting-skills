---
name: researcher-recruiting-skill
description: Use when researching every author of an arXiv paper for recruiting, public professional contact discovery, talent sourcing, identity disambiguation, or evidence-backed researcher due diligence.
---

# Researcher Recruiting

Turn an arXiv URL, identifier, or exact title into reproducible,
evidence-backed recruiting reports. Use the bundled CLI as the source of
record rather than replacing it with ad hoc searches.

## Required workflow

1. Read [references/compliance.md](references/compliance.md) before collecting
   data. Read [references/sources.md](references/sources.md) when selecting,
   explaining, or troubleshooting sources.
2. Follow [references/installation.md](references/installation.md) to accept
   or discover `PYTHON_BIN`, verify Python 3.11 or newer, and install package
   dependencies with that exact executable. The reference also documents
   generic, standalone, and optional agent discovery installation paths.
3. From the skill directory, run:

   ```bash
   "$PYTHON_BIN" scripts/researcher_recruiting.py "<paper>" --output results
   ```

4. Add `--refresh` only when fresh data is explicitly requested. Let arXiv
   categories select field-specific indexes; add `--sources name,name` only
   for an explicit source override.
5. Open `report.html` and inspect each author's source-attempt section before
   interpreting a blank field or missing contact. Distinguish `not_found`,
   `source_unavailable`, and `blocked_by_robots`.
6. Retain every paper author, including authors with ambiguous identities,
   missing contacts, or unavailable sources. Report each author's explicit
   `contact_status`: `found`, `not_found`, `ambiguous`, or
   `sources_unavailable`.
7. Review identity evidence and never upgrade a match based on name alone.
8. Present `report.html`, mention the run directory, and summarize unavailable
   sources.

## Artifact contract

Every successful or partial run creates one self-contained file:

- `report.html`

Keep `recruiting_notes` blank unless an assessment is requested. Do not send
outreach or mutate external profiles.

## Collection boundaries

Google Scholar, ResearchGate, Academia.edu, LinkedIn, Maimai, and unlicensed
commercial indexes are locator-only. Generate locator URLs, but never fetch or
parse their result or profile pages.

Never request cookies, shared-account credentials, CAPTCHA solving, paywall
bypass, browser-fingerprint evasion, or access-control bypass. If a public
source fails, retain the author, record the source and contact status, and
continue without substituting a prohibited scraper.
