# Recruiting Skills Pages Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable GitHub Pages homepage that prioritizes Skill installation and automatically lists published reports.

**Architecture:** A dependency-free Python generator scans a Pages checkout for safe report directories and renders a static HTML homepage from a repository-owned template. The publishing contract runs the generator after copying a report, preserving all existing `gh-pages` content.

**Tech Stack:** Python 3 standard library, `unittest`, static HTML/CSS, shell-based repository verification.

## Global Constraints

- Keep the homepage installation-first and report-list-second.
- Do not add Jekyll, a frontend framework, or third-party Python dependencies.
- Never delete or rewrite published report files.
- Use relative report links and safely escape all generated HTML.
- Keep `gh-pages` configured at branch root and retain `.nojekyll`.

---

### Task 1: Homepage generator

**Files:**
- Create: `scripts/build_pages_index.py`
- Create: `assets/pages-index-template.html`
- Create: `tests/test_build_pages_index.py`

**Interfaces:**
- Consumes: a Pages directory supplied as `python3 scripts/build_pages_index.py <pages-directory>`.
- Produces: `discover_reports(pages_dir: Path) -> list[str]`, `render_index(report_ids: list[str]) -> str`, and `<pages-directory>/index.html`.

- [ ] **Step 1: Write failing discovery and rendering tests**

Create tests that import `scripts.build_pages_index`, construct a temporary Pages directory, and assert that:

```python
self.assertEqual(discover_reports(pages_dir), ["2401.00001", "2502.00002v2"])
self.assertIn('href="2401.00001/"', rendered)
self.assertIn("researcher-recruiting-skill", rendered)
self.assertIn("research-talent-scout", rendered)
```

The fixture must also contain `.hidden/index.html`, `missing-index/`, and a root file, and assert those entries are absent.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_build_pages_index -v
```

Expected: `ModuleNotFoundError` for `scripts.build_pages_index`.

- [ ] **Step 3: Implement minimal safe discovery**

Implement:

```python
REPORT_ID = re.compile(r"^[0-9]+(?:\.[0-9]+)+(?:v[0-9]+)?$")

def discover_reports(pages_dir: Path) -> list[str]:
    return sorted(
        child.name
        for child in pages_dir.iterdir()
        if child.is_dir()
        and REPORT_ID.fullmatch(child.name)
        and (child / "index.html").is_file()
    )
```

- [ ] **Step 4: Add the static homepage template and rendering**

Create a responsive single-file template containing the repository title, the two Skill cards, GitHub links, install/call examples, and a `{{REPORT_LIST}}` marker. Implement `render_index()` with `html.escape(..., quote=True)` and render an empty-state paragraph when the list is empty.

- [ ] **Step 5: Implement the CLI write path**

Validate that the supplied path exists and is a directory, then write UTF-8 HTML to `<pages-directory>/index.html`. On invalid input, print a concise error to stderr and return non-zero.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_build_pages_index -v
```

Expected: all tests pass with no warnings.

- [ ] **Step 7: Commit**

```bash
git add scripts/build_pages_index.py assets/pages-index-template.html tests/test_build_pages_index.py
git commit -m "feat: generate recruiting skills Pages home"
```

### Task 2: Publishing contract integration

**Files:**
- Modify: `references/publishing.md`
- Modify: `SKILL.md`
- Modify: `tests/verify-skill.sh`

**Interfaces:**
- Consumes: `scripts/build_pages_index.py <site_dir>` after a report is copied.
- Produces: a publication contract that stages `.nojekyll`, `index.html`, and `<arxiv-id>/index.html` without deleting existing content.

- [ ] **Step 1: Add a failing contract check**

Extend `tests/verify-skill.sh` to require all of these literal references:

```text
scripts/build_pages_index.py
index.html
gh-pages
```

Run:

```bash
bash tests/verify-skill.sh .
```

Expected: failure because the current publishing instructions do not invoke the generator.

- [ ] **Step 2: Update the Git-capable publication flow**

After copying the report and creating `.nojekyll`, add:

```sh
python3 scripts/build_pages_index.py "$site_dir"
```

Update staging to include `.nojekyll`, `index.html`, and `<arxiv-id>/index.html` explicitly.

- [ ] **Step 3: Update the API-capable flow and Skill instructions**

Require API-capable hosts to preserve the branch tree, create or update root `index.html`, and include the current report list. Update `SKILL.md` so a successful publication includes both the exact report URL and the collection homepage URL.

- [ ] **Step 4: Run contract and full repository checks**

Run:

```bash
bash tests/verify-skill.sh .
bash tests/verify-all.sh
python3 -m unittest discover -v
```

Expected: every command exits zero.

- [ ] **Step 5: Commit**

```bash
git add references/publishing.md SKILL.md tests/verify-skill.sh
git commit -m "docs: keep Pages home updated during publishing"
```

### Task 3: Publish and verify the live homepage

**Files:**
- Create on `gh-pages`: `index.html`
- Preserve on `gh-pages`: `.nojekyll` and every report directory

**Interfaces:**
- Consumes: the tested generator and the current remote `gh-pages` tree.
- Produces: `https://lofisu.github.io/recruiting-skills/` returning the generated homepage.

- [ ] **Step 1: Inspect exact remote state**

Read the current `gh-pages` branch head and enumerate its tree. Record the existing file paths and verify `.nojekyll` is a regular file. Do not publish if the branch cannot be read safely.

- [ ] **Step 2: Generate the homepage against an isolated Pages checkout**

Use a temporary clone or worktree, run:

```bash
python3 scripts/build_pages_index.py <isolated-pages-directory>
```

Then verify that only `index.html` is newly changed and no report file is deleted or modified.

- [ ] **Step 3: Publish `gh-pages/index.html`**

Commit only the generated root homepage and push `gh-pages`. If Git shell network access is unavailable, use the GitHub contents API to create or update only `index.html` on `gh-pages`.

- [ ] **Step 4: Push implementation commits to `main`**

Fast-forward local `main` to the reviewed implementation commits and run:

```bash
git push origin main
```

Expected: remote `main` points to the final verified commit.

- [ ] **Step 5: Verify repository and live site**

Verify the remote repository contains the generator, template, tests, and updated instructions. Poll the exact Pages URL with bounded retries until it returns HTTP 200 and contains both Skill names. If deployment remains pending, report the successful branch update without claiming the page is live.
