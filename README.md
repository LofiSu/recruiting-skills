# researcher-recruiting-skill

A Codex Skill and standalone Python CLI that turns an arXiv paper into
source-backed researcher recruiting leads with deterministic identity
resolution and auditable provenance.

It uses public APIs and robots-permitted public pages. Google Scholar,
ResearchGate, Academia.edu, LinkedIn, Maimai, and unlicensed commercial
indexes remain locator-only.

## Setup

Requires Python 3.11 or newer. In Codex App, use its workspace Python when the
system `python3` is older. On cloud-synced workspaces, keep the virtual
environment in `/private/tmp` to avoid slow small-file imports.

```bash
PYTHON_BIN=python3.12  # or another Python 3.11+
"$PYTHON_BIN" -m venv /private/tmp/researcher-recruiting-venv
/private/tmp/researcher-recruiting-venv/bin/python -m pip install -e '.[dev]'
```

Optional environment variables:

| Variable | Purpose |
| --- | --- |
| `GITHUB_TOKEN` | Higher GitHub API quota |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key |
| `OPENALEX_API_KEY` | OpenAlex API key |
| `NCBI_API_KEY` | Higher PubMed quota |
| `UNPAYWALL_EMAIL` | Required when enriching discovered DOIs |
| `CROSSREF_MAILTO` | Crossref polite-pool contact |
| `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET` | ORCID public API |
| `HTTP_PROXY`, `HTTPS_PROXY` | Optional network proxy |
| `RESEARCHER_RECRUITING_CACHE` | SQLite cache location |

Secrets are not written to reports, evidence, logs, or response-cache keys.

## CLI

```bash
researcher-recruiting 1706.03762 --output results
researcher-recruiting "Attention Is All You Need" --refresh
researcher-recruiting 1706.03762 --sources dblp
```

`--refresh` bypasses cached responses. `--sources` is an explicit override;
normal field-specific routing comes from arXiv categories.

Every partial or complete run atomically creates:

- `report.md`
- `candidates.csv`
- `candidates.json`
- `evidence.json`
- `run-log.json`

Inspect `run-log.json` to distinguish `not_found`, `source_unavailable`, and
`blocked_by_robots`.

## Source matrix

- Cross-disciplinary: OpenAlex, Crossref, Semantic Scholar, ORCID, DataCite,
  ROR, Wikidata, GitHub, OpenReview.
- Computer science and engineering: DBLP for `cs.*`, `stat.ML`, and `eess.*`.
- Biomedicine: PubMed and Europe PMC for `q-bio.*`.
- High-energy and nuclear physics: INSPIRE for `hep-*` and `nucl-*`.
- DOI enrichment: OpenCitations and Unpaywall.
- Locator-only: Google Scholar, ResearchGate, Academia.edu, LinkedIn, Maimai,
  Scopus, Web of Science, Dimensions, Lens, NASA ADS, IEEE Xplore, and
  Springer Nature unless a licensed official adapter is configured.

See [source behavior](references/sources.md) and
[compliance boundaries](references/compliance.md).

## Install as a Codex Skill

Clone or symlink this repository into your personal skills directory:

```bash
ln -s /absolute/path/to/researcher-recruiting-skill \
  "${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill"
```

Restart or refresh Codex skill discovery, then invoke:

```text
Use $researcher-recruiting-skill on arXiv:1706.03762.
```

## Verification

Fixture tests are network-free:

```bash
python -m pytest -m "not network"
```

Run the opt-in public-network smoke test only when the environment permits:

```bash
RUN_NETWORK_TESTS=1 python -m pytest tests/test_network_e2e.py -m network
```
