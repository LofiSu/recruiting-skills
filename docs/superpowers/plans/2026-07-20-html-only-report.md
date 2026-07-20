# HTML-Only Recruiting Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each researcher-recruiting run emit exactly one secure, self-contained `report.html` containing the complete recruiting and audit result.

**Architecture:** Keep paper resolution, source collection, identity matching, and normalized candidate records unchanged. Replace the five sidecar writers in `researcher_recruiting/exporters.py` with an HTML renderer that combines candidate records and author-scoped source attempts, then atomically publishes a one-file timestamped run directory.

**Tech Stack:** Python 3.11+, standard-library `html`, `urllib.parse`, embedded HTML/CSS/JavaScript, pytest.

## Global Constraints

- A successful or partial run directory contains exactly `report.html`.
- The report has no remote runtime assets and remains readable without JavaScript.
- Render all authors, including ambiguous and contactless authors.
- Preserve `found`, `not_found`, `ambiguous`, and `sources_unavailable`.
- Redact secrets and opaque paper-email provenance before rendering.
- Make only `http`, `https`, and field-appropriate `mailto` values clickable.
- Preserve atomic directory publication and existing CLI exit codes.
- Do not add a legacy multi-file flag.

---

### Task 1: Define the HTML-only exporter contract

**Files:**
- Modify: `tests/test_exporters.py`
- Modify: `researcher_recruiting/exporters.py`

**Interfaces:**
- Consumes: `RunResult`, existing `_candidate_records(run)`, `_match_scope(...)`, `_source_result_matches_author(...)`, `_redact(...)`, and `_jsonable(...)`.
- Produces: `ARTIFACT_NAMES = ("report.html",)`, `_source_attempt_records(run) -> list[dict[str, object]]`, `_safe_href(value, *, allow_mailto=False) -> str | None`, `_report_html(run, candidates, source_attempts, generated_at) -> str`, and unchanged `write_artifacts(run, output_root) -> Path`.

- [ ] **Step 1: Replace file-shape tests with a failing HTML-only contract test**

  Replace the five-file assertion at the top of `tests/test_exporters.py` with:

  ```python
  def test_write_artifacts_creates_only_self_contained_html(
      tmp_path, run_result
  ):
      run_dir = write_artifacts(run_result, tmp_path)
      assert {path.name for path in run_dir.iterdir()} == {"report.html"}
      report = (run_dir / "report.html").read_text(encoding="utf-8")
      assert report.startswith("<!doctype html>")
      assert "<style>" in report
      assert "<script>" in report
      assert 'src="' not in report
      assert 'rel="stylesheet"' not in report
  ```

- [ ] **Step 2: Add failing content and scoping tests**

  Replace CSV/JSON/Markdown-specific assertions with tests that parse or inspect
  `report.html` and establish:

  ```python
  def _report(run, tmp_path):
      return (
          write_artifacts(run, tmp_path) / "report.html"
      ).read_text(encoding="utf-8")


  def test_html_contains_complete_candidate_and_audit_data(
      tmp_path, run_result
  ):
      report = _report(run_result, tmp_path)
      assert "Attention Is All You Need" in report
      assert "Ada Lovelace" in report
      assert "found" in report
      assert "ada@university.example" in report
      assert "https://example.test/contact" in report
      assert "Google Scholar" in report
      assert "LinkedIn" in report
      assert "Maimai" in report
      assert "Evidence" in report
      assert "Source attempts" in report
      assert "fixture" in report


  def test_html_scopes_duplicate_names_by_author_id(
      tmp_path, duplicate_name_run
  ):
      report = _report(duplicate_name_run, tmp_path)
      first = report.index('id="author-1"')
      second = report.index('id="author-2"')
      assert first < second
      assert "github" in report[first:second]
      assert "orcid" in report[second:]
  ```

  Build `duplicate_name_run` from the existing duplicate-name test setup so its
  two source attempts remain author-ID scoped.

- [ ] **Step 3: Add failing security tests**

  Add:

  ```python
  def test_html_escapes_content_and_rejects_unsafe_links(
      tmp_path, run_result, evidence_factory
  ):
      unsafe = evidence_factory(
          field="homepage",
          value='"><script>alert(1)</script>',
          url="javascript:alert(2)",
      )
      match = replace(
          run_result.matches[0],
          author=replace(
              run_result.matches[0].author,
              affiliation="<img src=x onerror=alert(3)>",
          ),
          evidence=(unsafe,),
          contact_points=(),
      )
      report = _report(
          replace(run_result, matches=(match,)),
          tmp_path,
      )
      assert "<script>alert(1)</script>" not in report
      assert "<img src=x onerror=alert(3)>" not in report
      assert "javascript:alert(2)" not in report
      assert "&lt;img src=x onerror=alert(3)&gt;" in report


  def test_html_redacts_secret_bearing_source_errors(
      tmp_path, run_result
  ):
      run = replace(
          run_result,
          source_results=(
              SourceResult(
                  "unsafe",
                  SourceStatus.SOURCE_UNAVAILABLE,
                  error="Authorization: Bearer super-secret-token",
                  author_name="Ada Lovelace",
              ),
          ),
      )
      report = _report(run, tmp_path)
      assert "super-secret-token" not in report
      assert "[REDACTED]" in report
  ```

  Retain the existing `_jsonable` paper-email-provenance unit test because the
  renderer reuses that boundary.

- [ ] **Step 4: Run the exporter tests and verify RED**

  Run:

  ```bash
  "$PYTHON_BIN" -m pytest tests/test_exporters.py -q
  ```

  Expected: failures show `report.html` is absent and the old five files are
  present.

- [ ] **Step 5: Implement normalized source-attempt records and safe links**

  In `researcher_recruiting/exporters.py`:

  ```python
  from html import escape
  from urllib.parse import urlsplit

  ARTIFACT_NAMES = ("report.html",)


  def _safe_href(value: str, *, allow_mailto: bool = False) -> str | None:
      if not value:
          return None
      parsed = urlsplit(value)
      allowed = {"http", "https"}
      if allow_mailto:
          allowed.add("mailto")
      if parsed.scheme.casefold() not in allowed:
          return None
      if parsed.scheme.casefold() in {"http", "https"} and not parsed.netloc:
          return None
      return value
  ```

  Extract the current per-author `source_attempts` comprehension into
  `_source_attempt_records(run)` and apply `_redact(_jsonable(...))` to the
  complete structure before rendering it.

- [ ] **Step 6: Implement the self-contained renderer**

  Add `_report_html(...)` using small escaping helpers:

  ```python
  def _text(value: object) -> str:
      return escape("" if value is None else str(value), quote=True)


  def _link(label: str, href: str, *, allow_mailto: bool = False) -> str:
      safe = _safe_href(href, allow_mailto=allow_mailto)
      if safe is None:
          return _text(label)
      return (
          f'<a href="{_text(safe)}" target="_blank" '
          f'rel="noopener noreferrer">{_text(label)}</a>'
      )
  ```

  Render semantic HTML with:

  - a paper header and metadata;
  - search input and contact-status select;
  - one `<article id="author-N" class="candidate-card">` per candidate;
  - contact/profile/locator link groups;
  - reasons, evidence, and author-scoped source-attempt `<details>` sections;
  - compliance text;
  - embedded responsive CSS;
  - a short embedded script that filters existing `.candidate-card` elements
    by their escaped text and `data-contact-status`.

  Do not serialize untrusted data into executable JavaScript. The script must
  operate only on already-rendered DOM nodes.

- [ ] **Step 7: Replace the five writes with one atomic HTML write**

  In `write_artifacts`, retain timestamped temporary-directory construction,
  compute candidates and source attempts in memory, then:

  ```python
  (temporary / "report.html").write_text(
      _report_html(
          run,
          candidates,
          source_attempts,
          timestamp,
      ),
      encoding="utf-8",
  )
  os.replace(temporary, final_path)
  ```

  Remove the CSV writer, Markdown renderer, and JSON sidecar writes. Remove
  imports and constants that have no remaining internal use.

- [ ] **Step 8: Run exporter tests and verify GREEN**

  Run:

  ```bash
  "$PYTHON_BIN" -m pytest tests/test_exporters.py -q
  ```

  Expected: all exporter tests pass.

- [ ] **Step 9: Commit the exporter behavior**

  ```bash
  git add researcher_recruiting/exporters.py tests/test_exporters.py
  git commit -m "feat: generate a single HTML recruiting report"
  ```

---

### Task 2: Align CLI, network smoke tests, and Skill documentation

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_network_e2e.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_skill_portability.py`
- Modify: `tests/skill-cases.md`
- Modify: `researcher_recruiting/cli.py`
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `references/sources.md`
- Modify: `references/installation.md`

**Interfaces:**
- Consumes: unchanged CLI arguments and exit codes.
- Produces: CLI help that says “report output root”, portability checks for `report.html`, and platform-neutral instructions that inspect the report’s source-attempt section.

- [ ] **Step 1: Update downstream tests first**

  Change CLI and network assertions to require one file:

  ```python
  run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
  assert len(run_dirs) == 1
  assert {path.name for path in run_dirs[0].iterdir()} == {"report.html"}
  report = (run_dirs[0] / "report.html").read_text(encoding="utf-8")
  for author in EXPECTED_AUTHORS:
      assert author in report
  assert "source_unavailable" in report or "blocked_by_robots" in report
  ```

  Update the portability test to assert `"report.html"` appears in `SKILL.md`
  and the five retired artifact names do not.

- [ ] **Step 2: Run focused downstream tests and verify RED**

  Run:

  ```bash
  "$PYTHON_BIN" -m pytest \
    tests/test_cli.py \
    tests/test_pipeline.py \
    tests/test_skill_portability.py \
    tests/test_network_e2e.py \
    -m "not network" -q
  ```

  Expected: documentation/output-contract assertions fail against the old
  wording and any old sidecar reads.

- [ ] **Step 3: Update CLI wording**

  In `researcher_recruiting/cli.py`, keep the option name and behavior but
  change help/error text:

  ```python
  help="report output root (default: ./results)"
  ```

  Use “Could not write report” and “Report invariant failure” for exporter
  errors.

- [ ] **Step 4: Update the reusable Skill contract**

  In `SKILL.md`, state the positive one-file recipe:

  ```markdown
  5. Open `report.html` and inspect each author's source-attempt section
     before interpreting a blank field or missing contact.
  8. Present `report.html`, mention the run directory, and summarize
     unavailable sources.

  ## Artifact contract

  Every successful or partial run creates one self-contained file:

  - `report.html`
  ```

  Preserve the existing trigger description, all-author retention rules,
  identity standard, and collection boundaries.

- [ ] **Step 5: Update user and reference documentation**

  In `README.md`, replace the five-file list and `run-log.json` guidance with
  `report.html` and its source-attempt section. In `references/sources.md`,
  change the partial-failure sentence to “Partial failures still produce the
  complete HTML report.” In `references/installation.md`, add one sentence
  after the run command stating that the timestamped directory contains only
  `report.html`. Rewrite `tests/skill-cases.md` success criteria and recorded
  artifact claims around the one-file contract.

- [ ] **Step 6: Run focused downstream tests and verify GREEN**

  Run:

  ```bash
  "$PYTHON_BIN" -m pytest \
    tests/test_cli.py \
    tests/test_pipeline.py \
    tests/test_skill_portability.py \
    tests/test_network_e2e.py \
    -m "not network" -q
  ```

  Expected: all selected non-network tests pass.

- [ ] **Step 7: Commit the contract update**

  ```bash
  git add \
    researcher_recruiting/cli.py \
    tests/test_cli.py \
    tests/test_pipeline.py \
    tests/test_skill_portability.py \
    tests/test_network_e2e.py \
    tests/skill-cases.md \
    SKILL.md README.md references/sources.md references/installation.md
  git commit -m "docs: make HTML the sole report artifact"
  ```

---

### Task 3: Validate and generate the real-paper deliverable

**Files:**
- Preserve: `outputs/2601.21998-recruiting/` existing results
- Create: `outputs/2601.21998-html/<timestamp>/report.html`

**Interfaces:**
- Consumes: the installed project or an isolated Python 3.11+ virtual
  environment and public network access.
- Produces: verified source code plus one user-facing HTML report for
  `arXiv:2601.21998`.

- [ ] **Step 1: Run the complete offline suite**

  ```bash
  "$PYTHON_BIN" -m pytest -m "not network" -q
  ```

  Expected: all selected tests pass.

- [ ] **Step 2: Run static and Skill validation**

  ```bash
  "$PYTHON_BIN" -m compileall -q researcher_recruiting scripts
  "$PYTHON_BIN" \
    /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
    .
  "$PYTHON_BIN" scripts/researcher_recruiting.py --help
  git diff --check
  ```

  Expected: compilation and validation succeed, help exits zero, and the diff
  has no whitespace errors.

- [ ] **Step 3: Run the opt-in public-network smoke test**

  ```bash
  RUN_NETWORK_TESTS=1 "$PYTHON_BIN" -m pytest \
    tests/test_network_e2e.py -m network -q
  ```

  Expected: the real arXiv run creates only `report.html` and retains every
  expected author.

- [ ] **Step 4: Generate the requested paper report**

  ```bash
  RESEARCHER_RECRUITING_CACHE=/private/tmp/researcher-recruiting-2601.21998-html.sqlite3 \
    "$PYTHON_BIN" scripts/researcher_recruiting.py \
    "https://arxiv.org/abs/2601.21998" \
    --output outputs/2601.21998-html \
    --refresh
  ```

  Expected: the printed timestamped run directory contains exactly
  `report.html`, and the page lists all 12 paper authors.

- [ ] **Step 5: Inspect the generated HTML**

  Verify:

  ```bash
  find outputs/2601.21998-html -mindepth 2 -maxdepth 2 -type f -print
  rg -n \
    "Lin Li|Qihang Zhang|Yiming Luo|Shuai Yang|Ruilin Wang|Fei Han|Mingrui Yu|Zelin Gao|Nan Xue|Xing Zhu|Yujun Shen|Yinghao Xu" \
    outputs/2601.21998-html/*/report.html
  ```

  Open the file in a browser and confirm responsive layout, search, filtering,
  link behavior, and readable no-JavaScript content.

- [ ] **Step 6: Commit final verification adjustments**

  If validation required tracked fixes, commit only those tracked files:

  ```bash
  git add researcher_recruiting tests SKILL.md README.md references
  git commit -m "test: verify HTML-only recruiting reports"
  ```

  Do not add generated `outputs/` unless explicitly requested.

- [ ] **Step 7: Push the completed branch**

  ```bash
  git push origin main
  ```

  Expected: the remote `main` SHA matches local `HEAD`.
