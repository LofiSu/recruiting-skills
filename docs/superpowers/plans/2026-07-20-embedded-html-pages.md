# Embedded HTML and GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the standalone researcher recruiting Skill generate a complete article-to-html-style report and automatically publish it to a stable GitHub Pages URL without adding generated reports to `main`.

**Architecture:** The report design system is copied into `assets/report-template.html`, so generation remains Agent-native and dependency-free. `SKILL.md` defines local generation as the guaranteed result and a tool-agnostic GitHub Pages publication path through a dedicated `gh-pages` branch; `references/publishing.md` contains the operational contract. A POSIX shell contract test verifies the portable Skill contents without becoming a runtime dependency.

**Tech Stack:** Agent Skills Markdown, HTML5, inline CSS, POSIX shell contract tests, Git, GitHub Pages.

## Global Constraints

- Users install only `researcher-recruiting-skill`.
- Do not require Python, Node.js, browser drivers, external fonts, CDNs, or JavaScript.
- Use Agent-native web search and preserve the roughly 20-second enrichment budget.
- Generate only `outputs/<arxiv-id>/report.html` locally for each requested paper.
- Keep the interface Chinese while preserving paper titles, author names, quotations, and original evidence text.
- Every non-empty professional field requires a clickable public evidence URL.
- Store published reports only on `gh-pages`, at `<arxiv-id>/index.html`; keep them out of `main`.
- Do not claim an online URL until the push and live HTTP response are verified.

---

### Task 1: Portable contract test

**Files:**
- Create: `tests/verify-skill.sh`

**Interfaces:**
- Consumes: repository files from the current checkout.
- Produces: a zero-dependency executable contract check with exit status `0` on success.

- [ ] **Step 1: Write the failing contract test**

```sh
#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill="$root/SKILL.md"
template="$root/assets/report-template.html"
publishing="$root/references/publishing.md"

require() {
  file=$1
  pattern=$2
  label=$3
  if ! grep -Fq -- "$pattern" "$file"; then
    printf 'FAIL: %s\n' "$label" >&2
    exit 1
  fi
}

require "$template" '--paper: #f7f7f5' 'article paper token'
require "$template" 'class="doc"' 'article document shell'
require "$template" 'class="doc-header"' 'article header'
require "$template" 'class="tldr"' 'TLDR block'
require "$template" '<span class="num">01</span>' 'numbered section'
require "$template" '作者与公开联系路径' 'Chinese author section'
require "$template" '{{AUTHOR_ROWS}}' 'author rows token'
require "$skill" 'references/publishing.md' 'publishing instructions'
require "$skill" 'gh-pages' 'dedicated Pages branch'
require "$publishing" '<arxiv-id>/index.html' 'stable report path'

if grep -Eqi '<script|<link[^>]+stylesheet|url\\([[:space:]]*[\"'\"']?https?://' "$template"; then
  printf 'FAIL: template contains an external runtime or asset\n' >&2
  exit 1
fi

printf 'PASS: standalone Skill contract verified\n'
```

- [ ] **Step 2: Run it and verify RED**

Run: `sh tests/verify-skill.sh`

Expected: `FAIL: article paper token`, because the existing template is not the embedded article-to-html design.

- [ ] **Step 3: Commit the RED test**

```bash
git add tests/verify-skill.sh
git commit -m "test: define embedded report contract"
```

---

### Task 2: Embedded article report template

**Files:**
- Modify: `assets/report-template.html`

**Interfaces:**
- Consumes: escaped replacements for `PAPER_TITLE`, `ARXIV_URL`, `PAPER_META`, `TLDR_BODY`, `OVERVIEW_BODY`, `SUMMARY_CARDS`, `AUTHOR_ROWS`, `LIMITATIONS_BODY`, and `REFERENCE_ITEMS`.
- Produces: one self-contained static HTML report.

- [ ] **Step 1: Replace the template presentation layer**

Start from the complete `article-to-html/references/template.html` CSS and component structure. Adapt it to:

```html
<article class="doc">
  <header class="doc-header">...</header>
  <div class="tldr">...</div>
  <section>
    <h2><span class="num">01</span>论文概览</h2>
    {{OVERVIEW_BODY}}
    <div class="cards">{{SUMMARY_CARDS}}</div>
  </section>
  <section>
    <h2><span class="num">02</span>作者与公开联系路径</h2>
    <div class="table-wrap">
      <table>...{{AUTHOR_ROWS}}...</table>
    </div>
  </section>
  <section>
    <h2><span class="num">03</span>证据与边界</h2>
    <div class="callout warn">{{LIMITATIONS_BODY}}</div>
  </section>
  <footer><ul>{{REFERENCE_ITEMS}}</ul></footer>
</article>
```

Retain the article palette, serif body, monospace metadata, numbered sections,
cards, tables, callouts, footer, print rules, and mobile author-card layout.
Do not include forms, controls, scripts, external stylesheets, or external fonts.

- [ ] **Step 2: Run the contract test and verify the template portion is GREEN**

Run: `sh tests/verify-skill.sh`

Expected: failure advances to missing publishing instructions, proving the
template checks now pass.

- [ ] **Step 3: Commit**

```bash
git add assets/report-template.html
git commit -m "feat: embed article report design"
```

---

### Task 3: Skill generation and publication contract

**Files:**
- Modify: `SKILL.md`
- Create: `references/publishing.md`
- Modify: `README.md`
- Modify: `agents/openai.yaml`
- Modify: `tests/skill-cases.md`

**Interfaces:**
- Consumes: arXiv identifier, completed local report, a GitHub remote, and host-authorized GitHub write capability.
- Produces: local `outputs/<arxiv-id>/report.html` plus a verified Pages URL when publication succeeds.

- [ ] **Step 1: Add report composition rules to `SKILL.md`**

Specify all template tokens, HTML escaping, allowed URL protocols, exact author
ordering, original-text preservation, and the article document structure. State
that the embedded template is copied locally and no second Skill is required.

- [ ] **Step 2: Add automatic publication workflow**

Create `references/publishing.md` with this behavior:

1. Detect a GitHub `origin` and available Git/GitHub write capability.
2. Use a temporary checkout of `gh-pages`; create the orphan branch only when absent.
3. Copy only the generated report to `<arxiv-id>/index.html`.
4. Commit and push `gh-pages`, leaving `main` and the working tree unchanged.
5. Configure Pages to serve the root of `gh-pages` when host tooling permits.
6. Poll the expected URL with bounded retries.
7. Return the URL only after an HTTP success; otherwise return the local report and the concrete failure.

Include command examples, but require Agents to adapt them to their host tools
and never expose credentials.

- [ ] **Step 3: Update user-facing documentation and behavior cases**

Document one-Skill installation, local fallback, stable URL format, automatic
publication prerequisites, the absence of runtime dependencies, and failure
behavior. Add pass criteria for keeping generated reports off `main`.

- [ ] **Step 4: Run the contract test and verify GREEN**

Run: `sh tests/verify-skill.sh`

Expected: `PASS: standalone Skill contract verified`

- [ ] **Step 5: Commit**

```bash
git add SKILL.md README.md agents/openai.yaml references/publishing.md tests/skill-cases.md
git commit -m "feat: add automatic Pages publishing"
```

---

### Task 4: Representative report and visual verification

**Files:**
- Modify: `outputs/2606.19980/report.html` (ignored local artifact)

**Interfaces:**
- Consumes: the previously verified ENPIRE author evidence and the new template.
- Produces: a 17-author article-style report matching the Skill contract.

- [ ] **Step 1: Regenerate the ENPIRE report**

Populate every template token, retain all 17 authors in official order, preserve
the 13 verified email findings and evidence links, retain the unresolved Jalen
Lu row, and write only `outputs/2606.19980/report.html`.

- [ ] **Step 2: Verify report structure**

Run:

```bash
test "$(grep -c '<tr class=\"author-row\">' outputs/2606.19980/report.html)" -eq 17
! grep -Eqi '<script|<link[^>]+stylesheet' outputs/2606.19980/report.html
```

Expected: exit status `0`.

- [ ] **Step 3: Inspect desktop and mobile renders**

Open the report in a real browser, capture approximately `1440×1000` and
`390×844` views, and verify readable hierarchy, no overflow, no truncated
authors, clickable evidence, and a faithful article-to-html visual system.

---

### Task 5: Publish and verify

**Files:**
- Modify: Git branch `gh-pages` only for generated report content.

**Interfaces:**
- Consumes: `outputs/2606.19980/report.html`.
- Produces: `https://lofisu.github.io/researcher-recruiting-skill/2606.19980/`.

- [ ] **Step 1: Run all local verification**

Run:

```bash
sh tests/verify-skill.sh
git diff --check
git status --short
```

Expected: contract PASS, no whitespace errors, and only intentional changes.

- [ ] **Step 2: Push `main`**

```bash
git push origin main
```

Expected: GitHub accepts the new commits.

- [ ] **Step 3: Publish the report on `gh-pages`**

Use the documented temporary-checkout flow. Commit only
`2606.19980/index.html` on `gh-pages`, push it, and enable the Pages branch
source if necessary.

- [ ] **Step 4: Verify the live URL**

Request the expected URL with bounded retries.

Expected: HTTP `200` and response HTML containing the exact ENPIRE paper title.

- [ ] **Step 5: Final repository audit**

Run:

```bash
git status --short
git log --oneline -5
git ls-tree -r --name-only origin/main
```

Expected: clean `main`; no generated report in the `main` tree.

## Self-review

- Spec coverage: embedded visual system, one-Skill portability, dependency-free
  generation, Chinese/original-text rules, dedicated branch publication, fallback,
  and live verification each have an implementation and verification task.
- Placeholder scan: no `TBD`, deferred implementation, or unspecified error handling.
- Interface consistency: the local report path is always
  `outputs/<arxiv-id>/report.html`; the published path is always
  `<arxiv-id>/index.html`; the branch is always `gh-pages`.
