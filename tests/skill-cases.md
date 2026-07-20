# Skill behavior cases

## Baseline case

Prompt:

> Given arXiv paper 1706.03762, identify every author and find public
> professional contact routes for each. Preserve evidence, distinguish missing
> contacts from unavailable sources, and do not directly crawl Google Scholar,
> LinkedIn, or Maimai. Produce one self-contained HTML report.

Rubric:

1. Invoke the repository CLI.
2. Include every author.
3. Create only `report.html`.
4. Distinguish contact statuses.
5. Preserve locator-only boundaries.

Observed without the Skill:

- Repository CLI invoked: **PASS**.
- Every author included: **FAIL**.
- Self-contained HTML report created: **FAIL**.
- Contact statuses distinguished: **FAIL**.
- Locator-only boundaries preserved: **FAIL**.
- The evaluator first used system Python 3.9, which failed on union type
  syntax, then found Python 3.11 without `httpx`. No report was generated.
  This demonstrates that generic installation and dependency instructions must
  be explicit.

## Forward case

Use the same prompt prefixed with:

> Use $researcher-recruiting-skill at `<repository-path>` to complete the
> request.

Pass only when the agent runs the bundled CLI, opens `report.html`, inspects
each author's source-attempt section, retains locator-only boundaries, and
returns a link to the sole report file.

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

### Legacy revised-Skill outcome (pre-HTML)

The following record is historical evidence from before the HTML-only
contract. It does not satisfy the current forward-case artifact criterion.

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
- The five legacy artifacts were created: `report.md`, `candidates.csv`,
  `candidates.json`, `evidence.json`, and `run-log.json`: **PASS under the
  pre-HTML rubric only**.
- `run-log.json` was inspected: **PASS under the pre-HTML rubric only**.
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

All six legacy criteria passed. Execution/artifact generation and fresh-Agent
inspection were split across controller and child processes solely because
network grants did not propagate to the child sandbox; this was not a
single-process forward run.

The root repository remained on the old plan commit throughout this forward
case. It was only the parent of the output destination above; it was not the
source of the loaded Skill or executed code.

## Legacy root end-to-end result (pre-HTML)

This historical run used the five-artifact contract. The final legacy forward
case was executed from the repository with:

```bash
RUN_NETWORK_TESTS=1 python -m pytest tests/test_network_e2e.py -m network -v
```

It passed against arXiv `1706.03762` and produced `report.md`,
`candidates.csv`, `candidates.json`, `evidence.json`, and `run-log.json`. The
run retained eight authors, field-level evidence, computer-science source
routing, and locator-only links. Its run log separately recorded successful
sources, `not_found`, `source_unavailable`, and `blocked_by_robots` outcomes.

The live run also exposed two sandbox-specific failure modes now covered by
regression tests:

- An unwritable user cache directory falls back to a temporary cache.
- A server's excessive `Retry-After` value cannot hold the workflow beyond the
  configured retry budget.

## Earlier HTML-only validation evidence (pre-final head)

Task 3 validated branch `feat/html-only-report` at revision `b1cfc64` before
recording this evidence. The opt-in public-network smoke test passed:

```bash
RUN_NETWORK_TESTS=1 \
  /private/tmp/researcher-recruiting-venv/bin/python -m pytest \
  tests/test_network_e2e.py -m network -q
```

The real `arXiv:2601.21998` CLI run produced:

```text
/Users/sulin/Documents/Codex/2026-07-16/agent-arxiv-open-review-github-claude/outputs/2601.21998-html/2601.21998-20260720T061544986256Z
```

That run directory contains exactly `report.html`. The self-contained report
retains all 12 paper authors in paper order: Lin Li, Qihang Zhang, Yiming Luo,
Shuai Yang, Ruilin Wang, Fei Han, Mingrui Yu, Zelin Gao, Nan Xue, Xing Zhu,
Yujun Shen, and Yinghao Xu. It contains 12 candidate cards and 12 corresponding
Source attempts sections. The 180 live source attempts had mixed outcomes:
25 `ok`, 60 `not_found`, 83
`source_unavailable`, and 12 `blocked_by_robots`. All 12 authors have the
aggregate contact status `sources_unavailable` because each had applicable
unavailable sources and no verified contact. That aggregate status does not
mean every individual source attempt was unavailable.

This was fresh execution evidence for the initial HTML-only artifact
criterion. It is preserved as historical evidence and superseded by the
final-head validation below. The earlier records above remain truthfully
labeled as legacy pre-HTML evidence.

## Final-head HTML-only validation evidence

The final report was generated from code head `24746cb`. Before successful
generation, two normal final-head CLI attempts were bounded-stopped at 300
seconds while queued behind DBLP's serialized domain lock. Atomic publication
worked as designed: neither stopped attempt left a partial output directory.

The bounded final validation harness then used the same production pipeline
and exporter with real `arXiv:2601.21998`, a three-second request timeout, and
all normal always-on sources. It set `category_routes={}` to omit only DBLP
and avoid the external serialized-lock delay. Production defaults and
production code were not changed.

The final output is:

```text
/Users/sulin/Documents/Codex/2026-07-16/agent-arxiv-open-review-github-claude/outputs/2601.21998-html-final/2601.21998-20260720T074934496393Z/report.html
```

Read-only inspection confirmed:

- the run directory contains exactly one file, `report.html`;
- the report is 1,333,715 bytes;
- all 12 authors appear in paper order;
- 168 source attempts are scoped under their corresponding authors;
- those attempts contain 1,657 source-evidence entries;
- 36 complete contact-point provenance records are present;
- the Contact-point provenance section is present;
- source-attempt outcomes are 24 `ok`, 60 `not_found`, 72
  `source_unavailable`, and 12 `blocked_by_robots`;
- all 12 authors have aggregate contact status `sources_unavailable`;
- no unsafe `href` values or external assets are present.

Final-head Playwright validation confirmed the expected report title,
searching for `Qihang Zhang` reduces the visible results to one author, the
`sources_unavailable` filter works, and the layout is responsive at 390×844.
The only browser error was the test server's implicit favicon request
returning 404; the report itself does not reference a favicon.

The production public-network smoke test had already passed. After the
fail-closed URL fix, all 25 exporter tests and all 200 selected non-network
tests passed.
