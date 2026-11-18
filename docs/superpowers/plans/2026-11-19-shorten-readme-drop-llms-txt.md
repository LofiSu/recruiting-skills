# Shorten README and Drop llms.txt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the bilingual README to keep only purpose/install/demo/safety content, move detail into docs, and delete `llms.txt` and all references to it.

**Architecture:** Four tasks execute in order: (1) create docs that absorb displaced content, (2) rewrite README to be short and bilingual-aligned, (3) delete llms.txt and remove all recommendations for it, (4) verify and commit. No new features. No changes to SKILL.md, scripts, or test assertions beyond removing the llms.txt check.

**Tech Stack:** Bash, Markdown, `bash tests/verify-all.sh` (Python 3.12 under the hood).

**Spec:** The goal description in the session-start prompt (the block beginning "## Goal: Rewrite the bilingual homepage README").

## Global Constraints

- `tests/verify-skill.sh` requires README.md to contain `https://github.com/LofiSu/recruiting-skills.git` and `cd recruiting-skills`. Do NOT remove them.
- `tests/verify-skill.sh` must NOT find `https://github.com/LofiSu/researcher-recruiting-skill.git` in README.md.
- Do not change SKILL.md frontmatter, script behavior, examples, templates, or sample records.
- Do not git push. No PR. No remote changes. No global git config.
- One local commit if and only if `bash tests/verify-all.sh` passes.
- Commit author: existing local config (`LofiSu` / `163713803+LofiSu@users.noreply.github.com`). End commit message with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
- Do not invent capabilities or present goals as features.
- Chinese must be concise, professional, natural. English must be equally tight and parallel.
- Both language halves must have the same section order and equivalent content.
- Keep one bilingual README.md (not two separate files).
- Do not modify REPO_META.md except to remove the llms.txt line.
- Do not touch real candidate data, do not run live connectors, do not publish.

## Review Focus

- README must still contain exactly the clone URL `https://github.com/LofiSu/recruiting-skills.git` and the string `cd recruiting-skills` after the rewrite — verify-skill.sh checks both.
- Internal Markdown links added to README or docs must resolve to paths that actually exist in the repo (not invented paths).
- Chinese and English section order must be identical — a structural drift would violate the spec; verify by reading both halves back-to-back.
- `llms.txt` references must be gone from every file in the working tree; a stale pointer in a comment or test would leave a broken recommendation.
- `bash tests/verify-all.sh` runs Python test suites in addition to the shell checks; verify real output, not assumed output.

---

## Task 1: Create docs that absorb README detail

**Files:**
- Create: `docs/usage-examples.md`
- Create: `docs/collaboration-contract.md`
- Create: `docs/local-index-quickstart.md`
- Create: `docs/importing-openalex-semantic-scholar.md`
- Create: `docs/verification.md`
- Create: `docs/github-pages.md`
- Create: `docs/repo-conventions.md`

**Interfaces:**
- Produces: seven bilingual doc files at the paths above. The README rewrite in Task 2 links to exactly these paths.

- [ ] **Step 1: Write `docs/usage-examples.md`**

Content (bilingual, Chinese first then `## English`):
- Chinese section `## 使用示例` with paper investigation prompts (the `Use $researcher-recruiting-skill on https://arxiv.org/abs/2606.19980` block plus the full cohort-scouting prompt) and the "全部候选人" clarification.
- English section `## Examples` with the equivalent English blocks from README lines 336–353.
- No FAQ format. No new capabilities.

- [ ] **Step 2: Write `docs/collaboration-contract.md`**

Content (bilingual):
- Chinese: the full workflow ASCII diagram (README lines 22–35), ownership description (`research-talent-scout` vs `researcher-recruiting-skill`), `batch_id` / `candidate_id` / `deadline_at` semantics, no coauthor expansion, no overwriting stronger evidence.
- English: equivalent English content from README lines 266–278.

- [ ] **Step 3: Write `docs/local-index-quickstart.md`**

Content (bilingual):
- Chinese: the `cd research-talent-scout` → `init_index.py` → `import_records.py` → `query_candidates.py` command block (README lines 138–155) plus note that fixture data is synthetic (`research-talent-scout/tests/fixtures/records.jsonl`).
- English: equivalent English "Demo index" block from README lines 415–431.

- [ ] **Step 4: Write `docs/importing-openalex-semantic-scholar.md`**

Content (bilingual):
- Chinese: connector location, `fetch_records.py` caveat paragraph (lines 159–199) including rate limits table and env var table and example commands.
- English: equivalent English block from README lines 355–396.
- Keep the real commands, caveats, and both tables verbatim.

- [ ] **Step 5: Write `docs/verification.md`**

Content (bilingual):
- Chinese: `bash tests/verify-all.sh` command plus the description of what it checks (lines 215–221).
- English: equivalent English block from README lines 435–441.

- [ ] **Step 6: Write `docs/github-pages.md`**

Content (bilingual):
- Chinese: the Pages publishing detail (branch, file path, URL pattern), collection home URL, generator scripts, and the note about fallback to local if Pages unavailable (lines 223–236).
- English: equivalent English block from README lines 443–456.

- [ ] **Step 7: Write `docs/repo-conventions.md`**

Content (bilingual):
- Chinese: the repo-convention bullet list (lines 43–49), the note about registering new Skills in catalog table, install instructions, and `tests/verify-all.sh`; the note that About/topics live in `REPO_META.md` and are not applied by git; the trending-notes link.
- English: equivalent English "Repository convention" block (lines 272–279) plus the same notes.

- [ ] **Step 8: Verify all seven files exist and contain no invented paths**

Run: `ls docs/usage-examples.md docs/collaboration-contract.md docs/local-index-quickstart.md docs/importing-openalex-semantic-scholar.md docs/verification.md docs/github-pages.md docs/repo-conventions.md`
Expected: all seven listed without error.

---

## Task 2: Rewrite README.md

**Files:**
- Modify: `README.md` (full replacement)

**Interfaces:**
- Consumes: seven doc files from Task 1 (links to them must use exact paths from Task 1).
- Produces: short bilingual README with sections in identical order for both languages.

Target section order (same for both Chinese and English):
1. Title + badges + language switch
2. Purpose paragraph (2-3 sentences)
3. Skills catalog table
4. When to use which Skill (1–2 sentences)
5. Install
6. Demo
7. Data and compliance boundaries
8. Links (Contributing, CoC, Security, License, docs)

- [ ] **Step 1: Draft the Chinese half**

Must contain:
- Badges: CI, License, Stars (copy from current README line 3–5).
- Language switch: `中文 | [English](#english)`.
- Purpose (2-3 sentences): what the two Skills do, that they ship with index engine and synthetic fixtures, no live candidate database. No slogans.
- Catalog table: same two rows as current (Skill name, 适用场景, 主要输出), tightened to fit in a compact README.
- When-to-use sentence.
- Install section with: clone URL `https://github.com/LofiSu/recruiting-skills.git` and `cd recruiting-skills`, host table, symlink block (both links), four important notes (only first link for paper-only; both needed for cohort+enrichment; new session after install; do not symlink into own `.cursor/skills/`). The root install name `researcher-recruiting-skill` and the clone directory `recruiting-skills` distinction must be explicit.
- Demo section: link to `examples/demo-report/index.html`, one sentence to open in browser, link to `docs/local-index-quickstart.md` for the index demo.
- Data/compliance section (the six bullet points from lines 240–245, stated briefly).
- Links section: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, LICENSE, and all seven new docs files.

- [ ] **Step 2: Draft the English half**

Must contain the same sections in the same order as the Chinese half. English must be independent and tight, not a stiff translation. All the same factual constraints apply (clone URL, cd, install names, notes).

- [ ] **Step 3: Verify README passes verify-skill.sh constraints**

Checks (run mentally before writing, verify by grep after writing):
- Contains `https://github.com/LofiSu/recruiting-skills.git` ✓
- Contains `cd recruiting-skills` ✓
- Does NOT contain `https://github.com/LofiSu/researcher-recruiting-skill.git` ✓
- Does NOT contain `llms.txt` ✓

- [ ] **Step 4: Write the new README.md**

Replace the full file content with the drafted bilingual README.

- [ ] **Step 5: Spot-check internal Markdown links**

For each `[text](path)` in README, confirm the target path exists:
- `examples/demo-report/index.html`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `LICENSE`
- `REPO_META.md`
- `docs/usage-examples.md`
- `docs/collaboration-contract.md`
- `docs/local-index-quickstart.md`
- `docs/importing-openalex-semantic-scholar.md`
- `docs/verification.md`
- `docs/github-pages.md`
- `docs/repo-conventions.md`
- `docs/trending-notes-2026-10-29.md`

Run: `for f in examples/demo-report/index.html CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md LICENSE REPO_META.md docs/usage-examples.md docs/collaboration-contract.md docs/local-index-quickstart.md docs/importing-openalex-semantic-scholar.md docs/verification.md docs/github-pages.md docs/repo-conventions.md docs/trending-notes-2026-10-29.md; do [ -e "$f" ] && echo "OK $f" || echo "MISSING $f"; done`
Expected: all OK.

---

## Task 3: Delete llms.txt and remove all references

**Files:**
- Delete: `llms.txt`
- Modify: `REPO_META.md` (remove llms.txt line only)
- Already handled in Task 2: `README.md`
- Already handled in Task 1: none of the new docs should mention llms.txt

**Interfaces:**
- Produces: no llms.txt in working tree; no recommendation to add or use one.

- [ ] **Step 1: Delete `llms.txt`**

Run: `rm llms.txt`
Expected: file gone.

- [ ] **Step 2: Remove the llms.txt line from `REPO_META.md`**

The line to remove is line 26 (the Discovery notes bullet starting "Agent index: [`llms.txt`](llms.txt)..."). Remove that bullet line only. Do not change the suggested description, topics, or remaining discovery notes.

- [ ] **Step 3: Search the entire repo for remaining llms.txt references**

Run: `grep -r "llms\.txt" --include="*.md" --include="*.sh" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.txt" . 2>/dev/null`
Expected: no matches (outside `.git/`).

- [ ] **Step 4: Confirm no test depends on llms.txt**

Run: `grep -r "llms" tests/ scripts/ .github/ 2>/dev/null`
Expected: no matches.

---

## Task 4: Verify and commit

**Files:**
- No new file changes.

**Interfaces:**
- Consumes: all prior tasks' changes.
- Produces: a local commit if and only if `bash tests/verify-all.sh` passes.

- [ ] **Step 1: Run the full test suite**

Run: `bash tests/verify-all.sh` from repo root.
Record the actual output verbatim — do not assume PASS.

- [ ] **Step 2: If any test fails, diagnose before committing**

If `verify-skill.sh` fails: check that README still contains the clone URL and `cd recruiting-skills`, and does not contain the old URL. Fix README only.
If frontmatter tests fail: do not change SKILL.md. Report the failure.
If other tests fail: report without fixing unless the failure is directly caused by the llms.txt deletion or README rewrite.

- [ ] **Step 3: Check all internal Markdown links in README and new docs resolve**

Run the link-check loop from Task 2 Step 5. Report any MISSING entries.

- [ ] **Step 4: Confirm llms.txt is gone**

Run: `find . -name "llms.txt" -not -path "./.git/*"`
Expected: no output.

- [ ] **Step 5: Report README line count before and after**

Before: 462 lines (confirmed by read).
Run: `wc -l README.md`
Report the after count.

- [ ] **Step 6: If and only if tests passed, commit**

```bash
git add README.md REPO_META.md docs/usage-examples.md docs/collaboration-contract.md \
  docs/local-index-quickstart.md docs/importing-openalex-semantic-scholar.md \
  docs/verification.md docs/github-pages.md docs/repo-conventions.md
git rm llms.txt
git commit -m "docs: shorten bilingual README and drop llms.txt

Move usage examples, collaboration contract, local index quickstart,
OpenAlex/Semantic Scholar import details, verification, GitHub Pages,
and repo conventions into docs/. README now keeps only purpose, install,
demo entry point, and safety/data boundaries, bilingual and
structurally aligned.

Delete llms.txt and all recommendations pointing to it.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

- [ ] **Step 7: List every modified, added, and deleted file**

Run: `git show --stat HEAD`
Report verbatim.
