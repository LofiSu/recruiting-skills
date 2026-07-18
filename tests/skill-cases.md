# Skill behavior cases

## Baseline case

Prompt:

> Given arXiv paper 1706.03762, research every author for recruiting. Use
> mainstream cross-disciplinary and computer-science scholarly sources, plus
> public identity and code profiles. Include locator links for restricted
> platforms. Produce a source-backed candidate report and machine-readable
> data.

Rubric:

1. Invoke a deterministic local workflow.
2. Select always-on and computer-science sources from arXiv categories.
3. Keep restricted sources locator-only.
4. Distinguish source failure from no result.
5. Produce five named artifacts.
6. Preserve field-level provenance.

Observed without the Skill:

- Did not invoke a deterministic local workflow.
- Began broad manual discovery but did not complete category routing.
- Mentioned locator research without completing the restricted-source
  boundary.
- Did not distinguish unavailable sources from completed empty results.
- Produced no artifacts.
- Produced no field-level evidence records.

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
