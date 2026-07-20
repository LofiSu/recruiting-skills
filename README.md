# researcher-recruiting-skill

An Agent Skills-standard skill and standalone Python CLI that turns an arXiv
paper into source-backed researcher recruiting leads, public professional
contact routes, deterministic identity resolution, and auditable provenance.

It uses public APIs and robots-permitted public pages. Google Scholar,
ResearchGate, Academia.edu, LinkedIn, Maimai, and unlicensed commercial
indexes remain locator-only.

## Setup

Requires Python 3.11 or newer. First select and validate `PYTHON_BIN` using
[the platform-neutral launcher instructions](references/installation.md#select-python).
Then, from the repository:

```bash
"$PYTHON_BIN" --version
"$PYTHON_BIN" -m pip install .
```

See [installation options](references/installation.md) for development setup,
the generic Agent Skills location, and optional Claude Code, OpenCode, and
Codex discovery paths.

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
If a sandbox cannot write the configured or platform-default cache directory,
the CLI falls back to a cache under the system temporary directory.

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
`blocked_by_robots`. Rate-limited sources are retried within a bounded delay;
an excessive server `Retry-After` value is recorded as unavailable instead of
holding the entire run.

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

## Install as an Agent Skill

Clone or symlink the same repository into one of the documented discovery
locations, refresh the agent's skill discovery, then invoke:

```text
Use $researcher-recruiting-skill on arXiv:1706.03762.
```

The optional `agents/openai.yaml` provides OpenAI UI metadata only; the
standard `SKILL.md`, bundled references, scripts, and CLI remain
platform-neutral.

## Verification

Fixture tests are network-free:

```bash
"$PYTHON_BIN" -m pytest -m "not network"
```

Run the opt-in public-network smoke test only when the environment permits:

```bash
RUN_NETWORK_TESTS=1 "$PYTHON_BIN" -m pytest tests/test_network_e2e.py -m network
```
