# Skill behavior cases

## Baseline case

Prompt:

> Given arXiv paper 1706.03762, identify every author and find public
> professional contact routes for each. Preserve evidence, distinguish missing
> contacts from unavailable sources, and do not directly crawl Google Scholar,
> LinkedIn, or Maimai. Produce reusable machine-readable artifacts.

Rubric:

1. Invoke the repository CLI.
2. Include every author.
3. Create all five artifacts.
4. Distinguish contact statuses.
5. Preserve locator-only boundaries.

Observed without the Skill:

- Repository CLI invoked: **PASS**.
- Every author included: **FAIL**.
- Five artifacts created: **FAIL**.
- Contact statuses distinguished: **FAIL**.
- Locator-only boundaries preserved: **FAIL**.
- The evaluator first used system Python 3.9, which failed on union type
  syntax, then found Python 3.11 without `httpx`. No artifacts were generated.
  This demonstrates that generic installation and dependency instructions must
  be explicit.

## Forward case

Use the same prompt prefixed with:

> Use $researcher-recruiting-skill at `<repository-path>` to complete the
> request.

Pass only when the agent runs the bundled CLI, inspects `run-log.json`, retains
locator-only boundaries, and returns links to `report.md` and
`candidates.csv` while preserving all five artifacts.

First forward-test failure:

- Assumed `python` existed, then fell back to an incompatible system Python
  3.9.
- Reused a repository-local `.venv` in a cloud-synced directory and stalled
  during dependency imports.

The Skill now requires an explicit Python 3.11+ check and a temporary
out-of-repository virtual environment before running the same case again.

Second forward-test environment result:

- Correctly selected Python 3.11.
- Could not proceed because the isolated evaluator's network permission request
  was cancelled before setup or CLI execution.

The Skill now reuses a validated temporary environment and requests network
only when dependency installation or public API access actually needs it.

## Root end-to-end result

The final forward case was executed from the repository with:

```bash
RUN_NETWORK_TESTS=1 python -m pytest tests/test_network_e2e.py -m network -v
```

It passed against arXiv `1706.03762` and produced `report.md`,
`candidates.csv`, `candidates.json`, `evidence.json`, and `run-log.json`.
The run retained eight authors, field-level evidence, computer-science source
routing, and locator-only links. Its run log separately recorded successful
sources, `not_found`, `source_unavailable`, and `blocked_by_robots` outcomes.

The live run also exposed two sandbox-specific failure modes now covered by
regression tests:

- An unwritable user cache directory falls back to a temporary cache.
- A server's excessive `Retry-After` value cannot hold the workflow beyond the
  configured retry budget.
