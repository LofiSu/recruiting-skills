# Security policy

This repository ships Agent Skills and Python 3 standard-library scripts for
public researcher recruiting. It does not ship a candidate database. The
connectors read public scholarly metadata (OpenAlex, Semantic Scholar). Paper
mode can, when a host is authorized, publish a static HTML report to the
`gh-pages` branch.

## Reporting a vulnerability

Do not open a public GitHub issue, pull request, or discussion for a
vulnerability. A public report can expose credential handling, HTML injection
in a published report, or a path that writes outside `outputs/` before a fix
exists.

Use GitHub private vulnerability reporting:

[https://github.com/LofiSu/recruiting-skills/security/advisories/new](https://github.com/LofiSu/recruiting-skills/security/advisories/new)

If that form is unavailable, contact the maintainer
[LofiSu](https://github.com/LofiSu) through the private contact on that
profile. Send a pointer to a write-up that is not committed in this
repository. Do not include exploit traffic, live API keys, or real candidate
records in the report.

### What to include

- The path you believe is affected. Typical surfaces are `SKILL.md`,
  `assets/report-template.html`, `scripts/build_pages_index.py`,
  `scripts/render_demo_report.py`, and
  `research-talent-scout/scripts/connectors/`.
- What a local user, a misbehaving agent, or a viewer of a published report
  can do, and what they already need (a checkout, an environment variable, a
  published `gh-pages` file).
- A short reproduction that uses the synthetic fixtures already in the
  repository:
  `research-talent-scout/tests/fixtures/records.jsonl`,
  `research-talent-scout/examples/sample-records.jsonl`, or
  `examples/demo-report/`. The connector tests under
  `research-talent-scout/tests/fixtures/` are offline HTTP fixtures.
- The commit SHA you tested, and whether `bash tests/verify-all.sh` still
  passes.

Stop once the issue is reproducible. Do not probe third-party accounts, do
not attempt to access arXiv, OpenAlex, Semantic Scholar, or GitHub beyond a
normal public request, and do not include `OPENALEX_API_KEY` or `S2_API_KEY`
values.

## In scope

- **Secrets.** `OPENALEX_API_KEY` and `S2_API_KEY` are environment variables.
  They are supposed to leave the process only as an `Authorization: Bearer`
  header (OpenAlex) or an `x-api-key` header (Semantic Scholar). A bug that
  copies either value into argv, logs, JSONL, the SQLite index, an HTML
  report, or a git commit is in scope.
- **Report HTML.** Paper reports and the Pages index are static files.
  Tokens inserted into `assets/report-template.html` are supposed to escape
  `&`, `<`, `>`, `"`, and `'`, and link targets are supposed to allow only
  `http`, `https`, and `mailto`. Script, external stylesheets, unexpected
  URL schemes, or unescaped author-controlled markup are in scope. The same
  bar applies to `scripts/build_pages_index.py`.
- **Filesystem writes.** Import, query, demo render, and publish paths should
  write only the database path the caller passed, `outputs/<arxiv-id>/`, or
  the `gh-pages` report path `<arxiv-id>/index.html` plus the branch root
  `index.html`. Writing elsewhere, or treating a paper id as a path that
  escapes that directory, is in scope.
- **Evidence boundary.** `references/compliance.md` forbids guessed email
  addresses, login or access-control bypass, and treating a search snippet as
  `已核验`. A code or skill-contract change that fabricates a professional
  email, marks an unresolved same-name identity as verified, or instructs a
  host to bypass a login wall is a security defect, not a feature.
- **CI.** `.github/workflows/ci.yml` checks out the repository with
  `contents: read` and runs `bash tests/verify-all.sh`. A workflow change
  that grants write permissions, passes secrets into the job, or executes
  untrusted code beyond that suite is in scope.

## Out of scope

- Ordinary skill bugs and feature requests. Use the issue templates described
  in [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Availability, pricing, or rate limits of arXiv, OpenAlex, Semantic Scholar,
  or GitHub Pages. The clients already back off on HTTP 429 and 503.
- Facts a researcher has already published on arXiv or on their own homepage.
- The absence of a live candidate database. The repository is not supposed to
  contain one. Local `data/*.sqlite` files and `outputs/` reports are
  gitignored.

## Response

The maintainer aims to acknowledge a private report within 7 days and to
coordinate either a fix or a documented rejection before any public write-up.
There is no bounty program. Please allow a reasonable window to ship a fix
before discussing the issue in public.

Supported line: the `main` branch. This repository does not publish version
tags as of 2026-10-29; pin the commit you install. Older clones should be
updated rather than patched in place.

After a fix lands, the advisory can move to a public GitHub Security
Advisory. Credit is offered unless you ask to stay anonymous.
