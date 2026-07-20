# Article-to-HTML Recruiting Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every generated `report.html` a Chinese recruiting-intelligence dossier using the `article-to-html` paper design while preserving complete authors, audit evidence, security, and single-file offline output.

**Architecture:** Keep the research pipeline and normalized records unchanged. Add deterministic summary and presentation helpers inside the existing exporter, then replace only the report markup, embedded CSS, and progressive-enhancement script. Existing sanitization, redaction, author scoping, and atomic publishing remain the rendering boundary.

**Tech Stack:** Python 3.11+, standard-library `collections.Counter`, existing HTML escaping and URL validation helpers, embedded semantic HTML/CSS/vanilla JavaScript, BeautifulSoup test assertions, pytest, Playwright browser verification.

## Global Constraints

- A successful or partial run directory contains exactly one file: `report.html`.
- `--paper`, author identity, source, and contact collection behavior do not change.
- Interface labels are Chinese; paper titles, author names, affiliations, evidence, source names, URLs, and other collected values remain unchanged.
- Preserve `--paper: #f7f7f5` and `--ink: #1a1a1a`.
- Use serif body text, monospace metadata, numbered section prefixes, and no emoji.
- All CSS and JavaScript are inline; load no remote fonts, images, stylesheets, scripts, analytics, or CDNs.
- Every paper author appears once in paper order even when identity or contact discovery is incomplete.
- Full contact provenance, evidence, and source attempts are closed native `<details>` elements by default.
- The document remains complete and navigable without JavaScript.
- Reuse `_text`, `_link`, `_email_link`, `_safe_href`, `_redact`, and `_jsonable`; do not add parallel sanitization.
- Generated example output under `outputs/` is not committed.

## File map

- Modify `researcher_recruiting/exporters.py`: deterministic summary, best-contact selection, author index/dossier helpers, `article-to-html` CSS, Chinese document structure, and progressive-enhancement script.
- Modify `tests/test_exporters.py`: structural, summary, localization, navigation, disclosure, interaction, mobile, and best-contact regression tests.
- Modify `docs/superpowers/plans/2026-07-20-article-to-html-recruiting-report.md`: mark execution checkboxes only while performing this plan.
- Create a timestamped directory under `outputs/2601.21998-article-html/` during final verification; do not stage it.

---

### Task 1: Deterministic recruiting summary

**Files:**
- Modify: `researcher_recruiting/exporters.py`
- Test: `tests/test_exporters.py`

**Interfaces:**
- Consumes: redacted candidate dictionaries from `_candidate_records(run)` and redacted author attempt dictionaries from `_source_attempt_records(run)`.
- Produces: `_report_summary(candidates: list[dict[str, Any]], source_attempts: list[dict[str, object]]) -> dict[str, int]`.

- [ ] **Step 1: Write the failing summary test**

Add `_report_summary` to the imports in `tests/test_exporters.py`, then add:

```python
def test_report_summary_counts_recruiting_outcomes():
    candidates = [
        {
            "identity_state": "confirmed",
            "contact_status": "found",
        },
        {
            "identity_state": "ambiguous",
            "contact_status": "not_found",
        },
    ]
    attempts = [
        {
            "source_attempts": [
                {"status": "ok"},
                {"status": "source_unavailable"},
            ]
        },
        {
            "source_attempts": [
                {"status": "blocked_by_robots"},
            ]
        },
    ]

    assert _report_summary(candidates, attempts) == {
        "authors": 2,
        "contacts_found": 1,
        "confirmed": 1,
        "probable": 0,
        "ambiguous": 1,
        "not_found": 0,
        "unavailable_attempts": 2,
    }
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python -m pytest tests/test_exporters.py::test_report_summary_counts_recruiting_outcomes -q
```

Expected: collection fails because `_report_summary` cannot be imported.

- [ ] **Step 3: Implement the deterministic summary**

Add `Counter` to the imports and place this helper before `_report_html`:

```python
def _report_summary(
    candidates: list[dict[str, Any]],
    source_attempts: list[dict[str, object]],
) -> dict[str, int]:
    identity_counts = Counter(
        str(candidate["identity_state"]) for candidate in candidates
    )
    unavailable_statuses = {
        "source_unavailable",
        "blocked_by_robots",
    }
    unavailable_attempts = sum(
        1
        for author in source_attempts
        for attempt in author["source_attempts"]
        if attempt["status"] in unavailable_statuses
    )
    return {
        "authors": len(candidates),
        "contacts_found": sum(
            candidate["contact_status"] == "found"
            for candidate in candidates
        ),
        "confirmed": identity_counts["confirmed"],
        "probable": identity_counts["probable"],
        "ambiguous": identity_counts["ambiguous"],
        "not_found": identity_counts["not_found"],
        "unavailable_attempts": unavailable_attempts,
    }
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
python -m pytest tests/test_exporters.py::test_report_summary_counts_recruiting_outcomes -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit the summary boundary**

```bash
git add researcher_recruiting/exporters.py tests/test_exporters.py
git commit -m "feat: summarize recruiting report outcomes"
```

---

### Task 2: Article-style Chinese document shell and author index

**Files:**
- Modify: `researcher_recruiting/exporters.py`
- Test: `tests/test_exporters.py`

**Interfaces:**
- Consumes: `_report_summary(...)`, redacted paper data, candidate records, stable `author-N` dossier anchors, and existing contact/evidence rendering helpers.
- Produces: `_render_author_index(candidates: Iterable[dict[str, Any]]) -> str` and an updated `_report_html(...) -> str` with `.doc`, `.doc-header`, `.tldr`, `.recruiting-workspace`, `.author-index`, and `.candidate-card`.

- [ ] **Step 1: Write failing article-shell tests**

Add:

```python
def test_html_uses_chinese_article_design_and_original_content(
    tmp_path, run_result
):
    report = _report(run_result, tmp_path)
    soup = BeautifulSoup(report, "html.parser")

    assert soup.html["lang"] == "zh-CN"
    assert soup.select_one("article.doc")
    assert soup.select_one(".doc-header .doc-title").get_text(
        " ", strip=True
    ) == "Attention Is All You Need"
    assert "研究者招聘情报报告" in report
    assert "Fixture abstract" in report
    assert "--paper: #f7f7f5" in report
    assert "--ink: #1a1a1a" in report
    assert "ui-serif" in report
    assert "ui-monospace" in report


def test_html_renders_deterministic_tldr_and_numbered_sections(
    tmp_path, run_result
):
    soup = BeautifulSoup(_report(run_result, tmp_path), "html.parser")
    tldr = soup.select_one(".tldr")

    assert tldr is not None
    assert "共 1 位作者" in tldr.get_text(" ", strip=True)
    assert "1 位找到公开职业联系方式" in tldr.get_text(
        " ", strip=True
    )
    assert [
        item.get_text(strip=True)
        for item in soup.select("h2 > .num")
    ] == ["01", "02", "03"]


def test_html_indexes_every_author_to_a_stable_dossier(
    tmp_path, duplicate_name_run
):
    soup = BeautifulSoup(
        _report(duplicate_name_run, tmp_path),
        "html.parser",
    )

    links = soup.select(".author-index a.author-index-link")
    dossiers = soup.select(".candidate-card")
    assert [link["href"] for link in links] == [
        "#author-1",
        "#author-2",
    ]
    assert [item["id"] for item in dossiers] == [
        "author-1",
        "author-2",
    ]
    assert all(link.get_text(strip=True) for link in links)
```

- [ ] **Step 2: Run the shell tests and verify RED**

Run:

```bash
python -m pytest \
  tests/test_exporters.py::test_html_uses_chinese_article_design_and_original_content \
  tests/test_exporters.py::test_html_renders_deterministic_tldr_and_numbered_sections \
  tests/test_exporters.py::test_html_indexes_every_author_to_a_stable_dossier \
  -q
```

Expected: all three tests fail against the current generic card document.

- [ ] **Step 3: Add the author-index renderer**

Place before `_report_html`:

```python
def _render_author_index(
    candidates: Iterable[dict[str, Any]],
) -> str:
    items = []
    for index, candidate in enumerate(candidates, start=1):
        order = candidate["author_order"] or index
        items.append(
            '<li class="author-index-item" '
            f'data-contact-status="{_text(candidate["contact_status"])}">'
            f'<a class="author-index-link" href="#author-{_text(order)}">'
            f'<span class="author-index-order">{_text(order).zfill(2)}</span>'
            f'<span class="author-index-name">'
            f'{_text(candidate["author_name"])}</span>'
            f'<span class="author-index-status">'
            f'{_text(candidate["contact_status"])}</span>'
            f'<span class="author-index-confidence">'
            f'{_text(candidate["confidence"])}/100</span>'
            "</a></li>"
        )
    return '<ol class="author-index-list">' + "".join(items) + "</ol>"
```

- [ ] **Step 4: Replace the document shell and CSS**

Update `_report_html` so it computes:

```python
summary = _report_summary(candidates, source_attempts)
author_index = _render_author_index(candidates)
tldr = (
    f"共 {_text(summary['authors'])} 位作者；"
    f"{_text(summary['contacts_found'])} 位找到公开职业联系方式；"
    f"身份确认 {_text(summary['confirmed'])} 位，"
    f"大概率匹配 {_text(summary['probable'])} 位，"
    f"存在歧义 {_text(summary['ambiguous'])} 位，"
    f"未找到 {_text(summary['not_found'])} 位；"
    f"{_text(summary['unavailable_attempts'])} 次来源访问不可用或受限。"
)
```

Replace the outer markup with this semantic structure while retaining the
existing redacted `cards`, paper metadata, and embedded script. The strings
below are Python f-string expressions inside `_report_html`:

```python
return f"""\
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>研究者招聘情报报告：{paper title}</title>
  <style>
    :root {
      --paper: #f7f7f5;
      --paper-edge: #efefea;
      --ink: #1a1a1a;
      --ink-soft: #4a4a4a;
      --ink-faint: #7a7a7a;
      --rule: #d8d8d2;
      --rule-soft: #e8e8e2;
      --accent: #a5523d;
      --accent-soft: #ead9d3;
      --accent-faint: #f4ece9;
      --warn: #9a7136;
      --warn-soft: #f5ecdc;
    }
    body {
      margin: 0;
      padding: 48px 24px 96px;
      background: var(--paper);
      color: var(--ink);
      font-family: ui-serif, Charter, Georgia, "Songti SC",
        "Source Han Serif SC", serif;
      line-height: 1.6;
    }
    .doc { max-width: 1180px; margin: 0 auto; }
    .doc-eyebrow, .doc-meta, .tldr-label, .num,
    .author-index, dt, summary, button, input, select {
      font-family: ui-monospace, "SF Mono", Menlo,
        "PingFang SC", monospace;
    }
    .doc-header {
      border-bottom: 1px solid var(--rule);
      padding-bottom: 28px;
      margin-bottom: 32px;
    }
    .doc-title { font-size: clamp(28px, 5vw, 46px); line-height: 1.12; }
    .doc-meta { display: flex; flex-wrap: wrap; gap: 12px 24px; }
    .tldr {
      background: var(--accent-faint);
      border-left: 2px solid var(--accent);
      padding: 20px 24px;
      margin-bottom: 40px;
    }
    h2 { border-bottom: 1px solid var(--rule); padding-bottom: 10px; }
    h2 .num { color: var(--ink-faint); margin-right: 14px; }
    .recruiting-workspace {
      display: grid;
      grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
      gap: 48px;
      align-items: start;
    }
    .author-index { position: sticky; top: 20px; }
    .author-index-list { list-style: none; margin: 0; padding: 0; }
    .author-index-link {
      display: grid;
      grid-template-columns: 2.5em 1fr auto;
      gap: 6px 10px;
      padding: 10px 0;
      border-bottom: 1px solid var(--rule-soft);
      color: var(--ink);
      text-decoration: none;
    }
    .author-index-status { grid-column: 2; color: var(--ink-faint); }
    .author-index-confidence { grid-column: 3; color: var(--ink-faint); }
    .candidate-card {
      scroll-margin-top: 24px;
      border-top: 1px solid var(--rule);
      padding: 30px 0 42px;
    }
    @media (max-width: 760px) {
      body { padding: 28px 16px 64px; }
      .recruiting-workspace { grid-template-columns: 1fr; gap: 28px; }
      .author-index {
        position: static;
        overflow-x: auto;
        padding-bottom: 8px;
      }
      .author-index-list { display: flex; min-width: max-content; }
      .author-index-item { width: 220px; margin-right: 18px; }
    }
  </style>
</head>
<body>
  <article class="doc">
    <header class="doc-header">
      <div class="doc-eyebrow">
        <span class="mascot"></span>研究者招聘情报报告
      </div>
      <h1 class="doc-title">{_text(paper["title"])}</h1>
      <p class="doc-subtitle">
        按论文作者顺序整理的公开职业身份、联系路径与来源证据
      </p>
      <div class="doc-meta">
        <span>ARXIV · {_text(paper["arxiv_id"])}</span>
        <span>分类 · {_text(", ".join(paper["categories"]))}</span>
        <span>生成时间 · {_text(generated_at.isoformat())}</span>
        <span>{paper_link}</span>
      </div>
    </header>
    <div class="tldr">
      <div class="tldr-label">TL;DR</div>
      <p>{tldr}</p>
    </div>
    <section class="paper-context">
      <h2><span class="num">01</span>论文概览</h2>
      <p>{_text(paper["abstract"])}</p>
    </section>
    <section class="author-section">
      <h2><span class="num">02</span>作者招聘档案</h2>
      <div class="report-controls" aria-label="作者筛选"></div>
      <div class="recruiting-workspace">
        <nav class="author-index" aria-label="作者索引">
          {author_index}
        </nav>
        <div class="author-dossiers">{''.join(cards)}</div>
      </div>
    </section>
    <section class="compliance">
      <h2><span class="num">03</span>合规与采集边界</h2>
      <p>
        仅收录公开职业联系方式和公开身份依据。Google Scholar、
        ResearchGate、Academia.edu、LinkedIn、脉脉及未授权商业数据库
        仅提供定位链接；未绕过登录、CAPTCHA、付费墙、robots 限制或
        其他访问控制。
      </p>
    </section>
  </article>
</body>
</html>
"""
```

- [ ] **Step 5: Run shell tests and the existing exporter suite**

Run:

```bash
python -m pytest tests/test_exporters.py -q
```

Expected: all exporter tests pass.

- [ ] **Step 6: Commit the article shell**

```bash
git add researcher_recruiting/exporters.py tests/test_exporters.py
git commit -m "feat: render article-style author dossiers"
```

---

### Task 3: Best contact route, collapsed audits, and progressive enhancement

**Files:**
- Modify: `researcher_recruiting/exporters.py`
- Test: `tests/test_exporters.py`

**Interfaces:**
- Consumes: existing candidate contact fields, `_email_link`, `_link`, existing provenance/evidence/source renderers, `.candidate-card`, and `.author-index-item`.
- Produces: `_render_best_contact(candidate: dict[str, Any]) -> str`, closed audit disclosures, `#candidate-search`, `#contact-filter`, `#audit-toggle`, `#back-to-top`, and a defensive inline script.

- [ ] **Step 1: Write failing contact and disclosure tests**

Add:

```python
def test_html_prioritizes_verified_email_as_best_contact(
    tmp_path, run_result
):
    soup = BeautifulSoup(_report(run_result, tmp_path), "html.parser")
    best = soup.select_one("#author-1 .best-contact")

    assert best is not None
    assert "最佳公开联系路径" in best.get_text(" ", strip=True)
    assert best.select_one(
        'a[href="mailto:ada@university.example"]'
    )


def test_html_keeps_audit_details_closed_by_default(
    tmp_path, run_result
):
    soup = BeautifulSoup(_report(run_result, tmp_path), "html.parser")
    audits = soup.select("#author-1 details.audit-disclosure")

    assert len(audits) == 3
    assert all(not item.has_attr("open") for item in audits)
    assert {item["data-audit-kind"] for item in audits} == {
        "contact-provenance",
        "evidence",
        "source-attempts",
    }


def test_html_includes_recruiting_filters_and_enhancement_controls(
    tmp_path, run_result
):
    report = _report(run_result, tmp_path)
    soup = BeautifulSoup(report, "html.parser")

    assert soup.select_one("#candidate-search")
    assert soup.select_one("#contact-filter")
    assert soup.select_one("#audit-toggle")
    assert soup.select_one("#back-to-top")
    assert "IntersectionObserver" in report
    assert "audit-disclosure" in report
    assert "@media (max-width: 760px)" in report
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest \
  tests/test_exporters.py::test_html_prioritizes_verified_email_as_best_contact \
  tests/test_exporters.py::test_html_keeps_audit_details_closed_by_default \
  tests/test_exporters.py::test_html_includes_recruiting_filters_and_enhancement_controls \
  -q
```

Expected: all three fail because the new dossier components do not exist.

- [ ] **Step 3: Implement deterministic best-contact selection**

Add:

```python
def _render_best_contact(candidate: dict[str, Any]) -> str:
    routes = (
        ("职业邮箱", _email_link(str(candidate["email"]))),
        (
            "联系表单",
            _link("打开联系表单", str(candidate["contact_form"])),
        ),
        ("个人主页", _link("打开个人主页", str(candidate["homepage"]))),
        ("GitHub", _link("打开 GitHub", str(candidate["github"]))),
        (
            "OpenReview",
            _link("打开 OpenReview", str(candidate["openreview"])),
        ),
    )
    selected = next(
        ((label, rendered) for label, rendered in routes if rendered),
        None,
    )
    if selected is None:
        return (
            '<div class="best-contact best-contact-empty">'
            '<div class="callout-label">最佳公开联系路径</div>'
            "<p>未找到经过核验的公开职业联系方式。</p>"
            "</div>"
        )
    label, rendered = selected
    return (
        '<div class="best-contact">'
        '<div class="callout-label">最佳公开联系路径</div>'
        f"<p><strong>{_text(label)}</strong> · {rendered}</p>"
        "</div>"
    )
```

- [ ] **Step 4: Mark all audit sections and add controls**

Make `_render_contact_provenance` return a closed disclosure with:

```html
<details class="contact-provenance audit-disclosure"
         data-audit-kind="contact-provenance">
  <summary>联系方式溯源</summary>
  {existing provenance content}
</details>
```

Render the candidate evidence and source attempts inside two additional
closed disclosures:

```html
<details class="audit-disclosure" data-audit-kind="evidence">
  <summary>完整身份与联系证据</summary>
  {existing evidence content}
</details>
<details class="audit-disclosure" data-audit-kind="source-attempts">
  <summary>各数据源尝试记录</summary>
  {existing source-attempt content}
</details>
```

Place these controls above the recruiting workspace:

```html
<div class="report-controls" aria-label="作者筛选">
  <label for="candidate-search">搜索作者</label>
  <input id="candidate-search" type="search"
         placeholder="姓名、机构、联系方式或证据">
  <label for="contact-filter">联系方式状态</label>
  <select id="contact-filter">
    <option value="">全部状态</option>
    <option value="found">已找到</option>
    <option value="not_found">未找到</option>
    <option value="ambiguous">存在歧义</option>
    <option value="sources_unavailable">来源不可用</option>
  </select>
  <button class="btn" id="audit-toggle" type="button">展开全部审计</button>
</div>
<button class="back-to-top" id="back-to-top" type="button">返回顶部</button>
```

- [ ] **Step 5: Replace the enhancement script**

Use one guarded IIFE:

```html
<script>
(() => {
  const search = document.querySelector("#candidate-search");
  const status = document.querySelector("#contact-filter");
  const auditToggle = document.querySelector("#audit-toggle");
  const backToTop = document.querySelector("#back-to-top");
  const cards = [...document.querySelectorAll(".candidate-card")];
  const indexItems = [...document.querySelectorAll(".author-index-item")];
  const indexLinks = [...document.querySelectorAll(".author-index-link")];

  const filter = () => {
    const query = search ? search.value.toLocaleLowerCase() : "";
    const selected = status ? status.value : "";
    cards.forEach((card, index) => {
      const matchesText = card.textContent
        .toLocaleLowerCase()
        .includes(query);
      const matchesStatus = !selected ||
        card.dataset.contactStatus === selected;
      const hidden = !(matchesText && matchesStatus);
      card.hidden = hidden;
      if (indexItems[index]) indexItems[index].hidden = hidden;
    });
  };

  if (search) search.addEventListener("input", filter);
  if (status) status.addEventListener("change", filter);

  if (auditToggle) {
    auditToggle.addEventListener("click", () => {
      const audits = [...document.querySelectorAll(
        "details.audit-disclosure"
      )];
      const shouldOpen = audits.some(item => !item.open);
      audits.forEach(item => { item.open = shouldOpen; });
      auditToggle.textContent = shouldOpen
        ? "折叠全部审计"
        : "展开全部审计";
    });
  }

  if (backToTop) {
    backToTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const href = `#${entry.target.id}`;
        indexLinks.forEach(link => {
          const active = link.getAttribute("href") === href;
          link.classList.toggle("active", active);
          if (active) link.setAttribute("aria-current", "true");
          else link.removeAttribute("aria-current");
        });
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    cards.forEach(card => observer.observe(card));
  }
})();
</script>
```

- [ ] **Step 6: Run targeted and full exporter tests**

Run:

```bash
python -m pytest tests/test_exporters.py -q
```

Expected: all exporter tests pass without warnings.

- [ ] **Step 7: Commit the recruiting interactions**

```bash
git add researcher_recruiting/exporters.py tests/test_exporters.py
git commit -m "feat: prioritize contacts and audit controls"
```

---

### Task 4: Full regression and real-paper browser verification

**Files:**
- Modify only if a verified defect is found: `researcher_recruiting/exporters.py`, `tests/test_exporters.py`
- Create but do not commit: `outputs/2601.21998-article-html/<timestamp>/report.html`

**Interfaces:**
- Consumes: the installed CLI, existing source routing and cache configuration, final `_report_html`, and Playwright.
- Produces: a verified real report for `arXiv:2601.21998`, desktop/mobile screenshots or inspection evidence, and a clean source commit.

- [ ] **Step 1: Run formatting and complete network-free verification**

Run:

```bash
git diff --check
python -m compileall -q researcher_recruiting tests
python -m pytest -m "not network" -q
```

Expected: no whitespace errors, compilation succeeds, and all non-network
tests pass.

- [ ] **Step 2: Regenerate the real report**

Run:

```bash
RESEARCHER_RECRUITING_CACHE=/private/tmp/researcher-recruiting-2601.21998-article.sqlite3 \
python scripts/researcher_recruiting.py \
  https://arxiv.org/abs/2601.21998 \
  --output outputs/2601.21998-article-html
```

Expected: the CLI prints one new timestamped run directory containing only
`report.html`. Optional upstream failures are visible inside the report and
do not remove authors.

- [ ] **Step 3: Validate the artifact contract and content**

Run:

```bash
find outputs/2601.21998-article-html -mindepth 2 -maxdepth 2 -type f -print
```

Expected: exactly one `report.html` in the newest timestamped directory.
Open the newest report and confirm:

- the original paper title is unchanged;
- all paper authors appear in order in the index and dossiers;
- Chinese interface labels and deterministic TL;DR are present;
- best contact routes, locator links, evidence, and source attempts render;
- audit sections start closed.

- [ ] **Step 4: Verify desktop and mobile behavior in Playwright**

Open the newest local `report.html` and inspect at:

- desktop: `1440 × 1000`;
- tablet: `768 × 1024`;
- mobile: `375 × 812`.

At each width confirm:

- no horizontal page overflow;
- index navigation reaches the correct dossier;
- search and contact-status filters hide matching dossier/index pairs only;
- “展开全部审计” opens every audit disclosure and toggles back;
- external links retain `target="_blank"` and `rel="noopener noreferrer"`;
- the browser console contains no errors.

- [ ] **Step 5: Add a failing regression test for every discovered defect**

For each defect, first add the smallest BeautifulSoup assertion or browser
behavior test that reproduces it, run that test to verify RED, implement the
smallest exporter correction, and rerun it to GREEN. Do not patch generated
HTML directly.

- [ ] **Step 6: Run final verification**

Run:

```bash
git diff --check
python -m compileall -q researcher_recruiting tests
python -m pytest -m "not network" -q
git status --short
```

Expected: all checks pass; only intentional source/test/plan changes and the
untracked `outputs/` directory are present.

- [ ] **Step 7: Commit any browser-driven fixes**

If Step 5 changed source or tests:

```bash
git add researcher_recruiting/exporters.py tests/test_exporters.py
git commit -m "fix: polish article recruiting report"
```

If no defect was found, do not create an empty commit.
