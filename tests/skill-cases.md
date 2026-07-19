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

### Earlier Skill iterations

First forward-test failure in an earlier iteration:

- Assumed `python` existed, then fell back to an incompatible system Python
  3.9.
- Reused a repository-local `.venv` in a cloud-synced directory and stalled
  during dependency imports.

At that earlier iteration, the then-current Skill required an explicit Python
3.11+ check and a temporary out-of-repository virtual environment before
running the same case again.

Second forward-test environment result in that earlier iteration:

- Correctly selected Python 3.11.
- Could not proceed because the isolated evaluator's network permission request
  was cancelled before setup or CLI execution.

At that earlier iteration, the then-current Skill reused a validated temporary
environment and requested network only when dependency installation or public
API access actually needed it.

### Revised-Skill outcome

At the initial revised forward invocation, the fresh Agent loaded exactly:

```text
/Users/sulin/Documents/Codex/2026-07-16/agent-arxiv-open-review-github-claude/.worktrees/cross-agent-contact-discovery/SKILL.md
```

That Skill and code were at commit `e422c04`; the loaded `SKILL.md` had
SHA-256
`a7e4289513207f252332b56e23e038fa041d9995d9e2b85684c05917e7b9b4be`.
The Agent invoked the bundled CLI without a Codex- or Claude-specific command.
Its child sandbox run failed with `ConnectError` because the controller's
network grant did not propagate into that sandbox.

The controller used the same worktree and commit, granted network access, and
ran that same platform-neutral CLI with the absolute output destination:

```text
/Users/sulin/Documents/Codex/2026-07-16/agent-arxiv-open-review-github-claude/outputs/1706.03762-recruiting
```

The successful run directory was:

```text
/Users/sulin/Documents/Codex/2026-07-16/agent-arxiv-open-review-github-claude/outputs/1706.03762-recruiting/1706.03762-20260719T102655744145Z
```

The fresh Agent inspected that run and observed:

- Bundled CLI invoked with a platform-neutral command: **PASS**.
- Every author retained, eight in paper order: **PASS**.
- Exactly five artifacts created: **PASS**.
- `run-log.json` inspected: **PASS**.
- Explicit per-author contact statuses reported: **PASS**.
- Scholar, LinkedIn, and Maimai kept locator-only: **PASS**.

The statuses were:

- Ashish Vaswani: `sources_unavailable`
- Noam Shazeer: `ambiguous`
- Niki Parmar: `sources_unavailable`
- Jakob Uszkoreit: `sources_unavailable`
- Llion Jones: `sources_unavailable`
- Aidan N. Gomez: `ambiguous`
- Lukasz Kaiser: `sources_unavailable`
- Illia Polosukhin: `sources_unavailable`

Restricted Scholar, LinkedIn, and Maimai points all had `direct=false`,
`confidence=0`, and `metadata.mode=locator_only`.

All six criteria passed. Execution/artifact generation and fresh-Agent
inspection were split across controller and child processes solely because
network grants did not propagate to the child sandbox; this was not a
single-process forward run.

The root repository remained on the old plan commit throughout this forward
case. It was only the parent of the output destination above; it was not the
source of the loaded Skill or executed code.

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
