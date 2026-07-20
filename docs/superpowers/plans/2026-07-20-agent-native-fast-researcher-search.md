# Agent-Native Fast Researcher Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Python crawler with a portable Agent Skill that uses the host's native web search, returns a chat summary, and writes a compact static HTML report in approximately 10–20 seconds.

**Architecture:** `SKILL.md` becomes the executable contract: read arXiv, batch native web searches under a global time budget, verify public professional fields against evidence URLs, then populate a reusable static template. The final repository contains no Python runtime, package, CLI, source adapters, or exhaustive audit UI.

**Tech Stack:** Agent Skills Markdown, host-native web search/browser tools, static HTML/CSS, shell-based repository validation.

## Global Constraints

- A normal user invocation must not check for, install, or run Python.
- There is one default native-search workflow; no quick, standard, audit, or Python fallback modes.
- Target an approximately 20-second global enrichment budget and return partial results at the budget.
- Preserve the exact arXiv author order.
- Collect only public professional data and never guess an email address.
- Google Scholar, LinkedIn, Maimai, ResearchGate, and Academia.edu remain locator-only.
- Produce a chat summary and exactly `outputs/<arxiv-id>/report.html`.
- The HTML is self-contained, contains no JavaScript, and contains no search, status-filter, audit-toggle, sticky-index, or source-attempt UI.
- Generated `outputs/` files remain untracked.

---

### Task 1: Replace the Skill behavior contract

**Files:**
- Modify: `tests/skill-cases.md`
- Modify: `SKILL.md`

**Interfaces:**
- Consumes: an arXiv URL, identifier, or exact paper title plus host Agent web and file capabilities.
- Produces: ordered `AuthorResult` rows with `name`, `institution`, `email`, `profiles`, `evidence_urls`, and `state`, plus a chat table and `outputs/<arxiv-id>/report.html`.

- [ ] **Step 1: Write the failing behavior case**

Replace `tests/skill-cases.md` with a compact RED/GREEN rubric containing this baseline:

```markdown
# Skill behavior cases

## RED: legacy ENPIRE behavior

Prompt:

> Find every author of https://arxiv.org/abs/2606.19980, their institution,
> homepage, public professional email, and evidence. Return immediately and
> generate one HTML report. Do not install or run Python.

Observed legacy failure:

- Required Python 3.11+ and a local CLI.
- Took several minutes across the exhaustive API matrix.
- Produced all 17 names but no verified public contact route.
- Rendered search, status, audit, index, and source-log UI the user rejected.

## GREEN: native web behavior

Pass when:

1. No Python, package manager, CLI, or repository script is invoked.
2. The official arXiv page supplies all 17 authors in exact order.
3. Native searches are batched/parallelized and stop near the 20-second budget.
4. Every non-empty institution, email, or profile has a public evidence URL.
5. The chat response and `outputs/2606.19980/report.html` contain the same
   ordered authors.
6. The HTML has no JavaScript or interactive audit/filter controls.

## GREEN: host without web search

Pass when the Agent preserves the arXiv author list, emits Scholar/LinkedIn/
Maimai locator links, marks every row `未执行网页检索`, and still produces the
chat summary and HTML without invoking Python.
```

- [ ] **Step 2: Verify the old Skill fails the new contract**

Run:

```bash
rg -n 'Python|scripts/researcher_recruiting.py|bundled CLI' SKILL.md
rg -n 'candidate-search|audit-toggle|source-attempt' researcher_recruiting/exporters.py
```

Expected: both commands return matches, proving the legacy implementation violates the accepted design.

- [ ] **Step 3: Rewrite `SKILL.md` with the native workflow**

Use this structure and operational contract:

```markdown
---
name: researcher-recruiting-skill
description: Use when finding the authors, institutions, public professional contact routes, homepages, GitHub or OpenReview profiles, and evidence for an arXiv paper or exact research-paper title.
---

# Researcher Recruiting

Return useful author leads quickly. Use the host Agent's native web search and
browsing tools; never install or invoke a local runtime.

## Workflow

1. Read `references/compliance.md` and `references/search.md`.
2. Open the official arXiv page. Preserve its exact title and ordered authors.
3. Start a roughly 20-second enrichment budget.
4. Search all authors in the largest parallel batches the host supports.
5. Accept a professional field only with a clickable supporting public page.
6. Stop at the budget; retain every author and mark unknown values explicitly.
7. Copy `assets/report-template.html` to `outputs/<arxiv-id>/report.html`,
   replace its example content with escaped results, and keep it self-contained.
8. Return the ordered chat table and link the HTML.

## Search contract

For each author, issue one focused query:

`"<exact author name>" "<paper title or distinctive acronym>"`

Use at most one follow-up:

`"<exact author name>" (university OR lab OR GitHub OR homepage OR email)`

Prefer personal, institutional, laboratory, project, GitHub, and OpenReview
pages. Search snippets can locate evidence but cannot alone verify a field.

## States

- `已核验`: exact person and field supported by relevant public evidence.
- `可能匹配`: plausible result with unresolved identity ambiguity.
- `暂未找到`: no usable result inside the time budget.
- `未执行网页检索`: host lacks web search.

## No-web fallback

Read arXiv when possible, retain every author, create Scholar/LinkedIn/Maimai
locator URLs, mark `未执行网页检索`, and still create the chat table and HTML.
Never request Python installation or substitute a scraper.

## Output

Write only `outputs/<arxiv-id>/report.html`. Keep chat and HTML values aligned.
Escape all collected text; allow only `http`, `https`, and `mailto` links.
```

- [ ] **Step 4: Run the GREEN static contract**

Run:

```bash
! rg -n 'python|pip|uv run|researcher_recruiting.py|CLI' SKILL.md
rg -n 'native web|20-second|outputs/<arxiv-id>/report.html|未执行网页检索' SKILL.md
```

Expected: the negative search exits zero; the positive search reports the native workflow and fallback.

- [ ] **Step 5: Commit Task 1**

```bash
git add SKILL.md tests/skill-cases.md
git commit -m "feat: make native web search the skill default"
```

### Task 2: Add the search and safety references

**Files:**
- Modify: `references/compliance.md`
- Create: `references/search.md`
- Delete: `references/installation.md`
- Delete: `references/identity-matching.md`
- Delete: `references/sources.md`

**Interfaces:**
- Consumes: the Skill's paper title, author name, remaining time budget, and host search capabilities.
- Produces: bounded queries, evidence selection rules, and safe fallback behavior.

- [ ] **Step 1: Add failing reference assertions**

Run before editing:

```bash
test -f references/search.md
! test -f references/installation.md
! rg -n 'Python|pip install|API matrix' references
```

Expected: at least the first two checks fail because the native-search reference does not exist and installation guidance remains.

- [ ] **Step 2: Write `references/search.md`**

Include:

```markdown
# Native web search

## Time budget

Start with the arXiv page, then spend approximately 20 seconds on enrichment.
Batch independent authors in parallel. Stop at the budget and render partial
results; do not wait for one slow site.

## Query sequence

Primary: `"<author>" "<paper title or acronym>"`

One optional follow-up:
`"<author>" (university OR lab OR GitHub OR homepage OR email)`

## Evidence priority

1. personal professional homepage;
2. institution, laboratory, or project page;
3. GitHub or OpenReview;
4. exact scholarly profile;
5. restricted-platform locator.

Public email requires a directly supporting page. A snippet or guessed address
is not evidence. Conflicting identities remain `可能匹配`.

## Batch behavior

Use the largest batch supported by the host. Do not serially wait for every
author when parallel search is available. Do not repeat failed query variants.
```

- [ ] **Step 3: Simplify `references/compliance.md`**

Retain only public-professional-data rules, email non-guessing, restricted-platform locator-only rules, uncertainty handling, and no automated employment decisions. Remove Python, API credential, cache, crawler, and adapter guidance.

- [ ] **Step 4: Delete obsolete references**

Delete `references/installation.md`, `references/identity-matching.md`, and `references/sources.md`.

- [ ] **Step 5: Verify references**

Run:

```bash
test -f references/search.md
! test -f references/installation.md
! test -f references/identity-matching.md
! test -f references/sources.md
! rg -n 'Python|pip install|SQLite|API key' references
rg -n '20 seconds|parallel|Public email|locator' references/search.md references/compliance.md
```

Expected: all commands exit zero.

- [ ] **Step 6: Commit Task 2**

```bash
git add references
git commit -m "docs: define bounded native author search"
```

### Task 3: Replace the rejected report with a static compact template

**Files:**
- Create: `assets/report-template.html`
- Test: `tests/skill-cases.md`

**Interfaces:**
- Consumes: escaped paper metadata and ordered author rows from the Agent.
- Produces: a self-contained, responsive, printable HTML file with no JavaScript.

- [ ] **Step 1: Write the failing template checks**

Run:

```bash
test -f assets/report-template.html
```

Expected: FAIL because the template does not exist.

- [ ] **Step 2: Create `assets/report-template.html`**

The complete template must contain:

- `lang="zh-CN"`, UTF-8, responsive viewport;
- example tokens `{{PAPER_TITLE}}`, `{{ARXIV_URL}}`, `{{PAPER_META}}`,
  `{{SUMMARY}}`, and `{{AUTHOR_ROWS}}`;
- a compact table with columns `作者`, `机构`, `公开联系路径`, `状态`, `证据`;
- paper-white background, dark readable text, subtle rules, and one restrained accent;
- a mobile breakpoint that converts each row to a stacked card using
  `data-label`;
- print rules that use black text on white and preserve URLs;
- no `<script>`, input, select, button, details, sticky position, or fixed position.

Use this row contract in an HTML comment:

```html
<!--
<tr>
  <th scope="row" data-label="作者">EXACT_AUTHOR_NAME</th>
  <td data-label="机构">INSTITUTION_OR_暂未找到</td>
  <td data-label="公开联系路径">SAFE_LINKS_OR_暂未找到</td>
  <td data-label="状态"><span class="state state-verified">已核验</span></td>
  <td data-label="证据">EVIDENCE_LINKS</td>
</tr>
-->
```

- [ ] **Step 3: Verify the template contract**

Run:

```bash
rg -n '\\{\\{PAPER_TITLE\\}\\}|\\{\\{AUTHOR_ROWS\\}\\}|data-label="作者"|@media.*max-width|@media print' assets/report-template.html
! rg -n '<script|<input|<select|<button|<details|position: *(sticky|fixed)' assets/report-template.html
```

Expected: required tokens and responsive/print CSS are found; forbidden UI and JavaScript are absent.

- [ ] **Step 4: Commit Task 3**

```bash
git add assets/report-template.html
git commit -m "feat: add compact static researcher report template"
```

### Task 4: Rewrite distribution metadata and remove the Python product

**Files:**
- Modify: `README.md`
- Modify: `agents/openai.yaml`
- Modify: `.gitignore`
- Delete: `researcher_recruiting/`
- Delete: `scripts/`
- Delete: `pyproject.toml`
- Delete: all Python tests and fixtures under `tests/`, retaining only `tests/skill-cases.md`
- Delete: legacy files under `docs/superpowers/`, temporarily retaining only
  the current native-search design and implementation plan until final review

**Interfaces:**
- Consumes: the final Skill, references, and HTML template.
- Produces: a minimal Agent Skills repository requiring no local runtime.

- [ ] **Step 1: Write the failing repository-shape checks**

Run:

```bash
! test -d researcher_recruiting
! test -d scripts
! test -f pyproject.toml
! find tests -type f ! -name skill-cases.md | grep .
```

Expected: the first three checks fail and the final command prints legacy Python tests/fixtures.

- [ ] **Step 2: Rewrite `README.md`**

Document:

- no Python, package installation, local CLI, keys, cache, or hosted service;
- installation by cloning/symlinking the Skill into any Agent Skills discovery directory;
- example invocation with an arXiv URL;
- native web search, approximately 20-second best-effort behavior, no-web fallback;
- chat summary plus `outputs/<arxiv-id>/report.html`;
- locator-only restricted platforms and public-professional-data boundary.

- [ ] **Step 3: Update `agents/openai.yaml`**

Set:

```yaml
interface:
  display_name: "Researcher Recruiting"
  short_description: "Quickly find paper authors and public contact evidence"
  default_prompt: "Use $researcher-recruiting-skill to quickly find every author of this arXiv paper, their institution, public professional contact routes, and evidence, then generate the compact HTML report."
```

- [ ] **Step 4: Update `.gitignore`**

Retain environment ignores that remain harmless and add:

```gitignore
outputs/
```

Remove Python-only ignores after the Python product is deleted.

- [ ] **Step 5: Delete the legacy implementation**

Delete the complete `researcher_recruiting/` and `scripts/` trees, `pyproject.toml`, every test/fixture except `tests/skill-cases.md`, and all superseded `docs/superpowers/` design/plan files after recording their commit history.

Temporarily retain only:

```text
docs/superpowers/specs/2026-07-20-agent-native-fast-researcher-search-design.md
docs/superpowers/plans/2026-07-20-agent-native-fast-researcher-search.md
```

- [ ] **Step 6: Verify the minimal repository shape**

Run:

```bash
! test -d researcher_recruiting
! test -d scripts
! test -f pyproject.toml
test "$(find tests -type f | sort)" = "tests/skill-cases.md"
test -f SKILL.md
test -f README.md
test -f agents/openai.yaml
test -f assets/report-template.html
test -f references/compliance.md
test -f references/search.md
! rg -n 'pip install|Python 3|uv run|researcher-recruiting ' SKILL.md README.md references agents assets tests
```

Expected: all commands exit zero.

- [ ] **Step 7: Commit Task 4**

```bash
git add -A
git commit -m "refactor: remove the Python recruiting pipeline"
```

### Task 5: Validate the final Skill and forward-test ENPIRE

**Files:**
- Modify if required by findings: `SKILL.md`
- Modify if required by findings: `references/search.md`
- Modify if required by findings: `assets/report-template.html`
- Create only as ignored output: `outputs/2606.19980/report.html`

**Interfaces:**
- Consumes: the final repository and ENPIRE arXiv URL.
- Produces: evidence-backed chat results and the final compact report.

- [ ] **Step 1: Validate Skill metadata without product dependencies**

Run the environment-owned validator:

```bash
python3 /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Expected: `Skill is valid!`. This development check does not become a user runtime dependency.

- [ ] **Step 2: Run static safety and shape checks**

Run:

```bash
git diff --check
! rg -n '<script|candidate-search|contact-filter|audit-toggle|source-attempt' assets/report-template.html SKILL.md
! rg -n 'Python|pip|uv run|researcher_recruiting.py' SKILL.md README.md references agents assets tests
git status --short
```

Expected: no tracked implementation changes beyond intentional final fixes; forbidden runtime and UI strings are absent.

- [ ] **Step 3: Execute the ENPIRE forward scenario**

Apply the final Skill to:

```text
https://arxiv.org/abs/2606.19980
```

Use native web search only. Do not invoke the removed implementation. Record elapsed wall time when the host exposes it. Write `outputs/2606.19980/report.html`.

- [ ] **Step 4: Verify ENPIRE output**

Confirm:

- exact title `ENPIRE: Agentic Robot Policy Self-Improvement in the Real World`;
- exactly 17 author rows in official arXiv order;
- each non-empty professional field has a safe evidence link;
- unknown or ambiguous fields are labeled, not guessed;
- chat and HTML contain the same 17 ordered names;
- the report has no JavaScript or rejected controls;
- only `outputs/2606.19980/report.html` exists for the new run;
- elapsed search behavior is time-bounded rather than exhaustive.

- [ ] **Step 5: Run the no-web capability scenario**

Inspect the Skill instructions as a host with no web-search tool. Confirm it:

- does not request Python;
- preserves the arXiv list when page access exists;
- emits locator URLs;
- marks `未执行网页检索`;
- still produces chat and HTML.

- [ ] **Step 6: Fix findings through RED/GREEN cycles**

For every behavioral defect, first add the failing expectation to `tests/skill-cases.md`, observe the mismatch, then minimally update `SKILL.md`, a reference, or the template and rerun the relevant checks.

- [ ] **Step 7: Commit final fixes**

```bash
git add SKILL.md README.md agents assets references tests .gitignore
git commit -m "test: verify native researcher search workflow"
```

### Task 6: Final review and delivery

**Files:**
- No new permanent files; review the final branch diff and ignored output.

**Interfaces:**
- Consumes: the complete branch against base `d5fab56`.
- Produces: an evidence-backed merge-readiness verdict and user handoff.

- [ ] **Step 1: Review requirements against the accepted design**

Check every acceptance criterion in
`docs/superpowers/specs/2026-07-20-agent-native-fast-researcher-search-design.md`
against the final tree or its deletion commit in history.

- [ ] **Step 2: Review the complete branch diff**

Run:

```bash
git diff --stat d5fab56..HEAD
git diff d5fab56..HEAD
git log --oneline d5fab56..HEAD
```

Confirm no Python runtime remains, the native workflow is unambiguous, and the template is safe and compact.

- [ ] **Step 3: Run final verification**

Run:

```bash
git diff --check
python3 /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
! find . -path './.git' -prune -o -path './outputs' -prune -o -type f \\( -name '*.py' -o -name 'pyproject.toml' \\) -print | grep .
! rg -n '<script|candidate-search|contact-filter|audit-toggle|source-attempt' assets/report-template.html SKILL.md
git status --short --branch
```

Expected: validation passes, no product Python files exist, forbidden UI is absent, and only ignored generated output is outside the committed tree.

- [ ] **Step 4: Remove development-only planning documents**

After the requirements and branch review are complete, delete the entire
`docs/superpowers/` tree so the distributed repository contains only runtime
Skill files, references, template, metadata, README, `.gitignore`, and behavior
cases. Preserve the approved design and plan in git history.

Commit:

```bash
git add -A docs/superpowers
git commit -m "chore: remove development planning artifacts"
```

- [ ] **Step 5: Re-run the final repository-shape checks**

Run:

```bash
! test -d docs/superpowers
! test -d researcher_recruiting
! test -d scripts
! test -f pyproject.toml
test "$(find tests -type f | sort)" = "tests/skill-cases.md"
git diff --check
git status --short --branch
```

Expected: all commands exit zero and no generated output appears because
`outputs/` is ignored.

- [ ] **Step 6: Present the result**

Report the final branch, commits, removed runtime requirement, ENPIRE elapsed behavior, forward-test findings, and a clickable `outputs/2606.19980/report.html`.
