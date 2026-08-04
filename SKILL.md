---
name: researcher-recruiting-skill
description: Use when finding authors and public professional evidence for an arXiv paper or exact paper title, or when enriching a filtered batch of researcher candidates handed off by research-talent-scout.
---

# Researcher Recruiting

Return useful author leads quickly. Use the host Agent's native web search and
browsing tools; never install or invoke a local language runtime.

Choose exactly one mode:

- **Paper mode:** resolve one paper, enrich its complete ordered author list,
  and generate the embedded HTML report.
- **Candidate batch mode:** accept a `candidate_enrichment_batch` from
  `research-talent-scout`, enrich only those stable candidate IDs, and return
  one machine-readable batch. Do not generate per-paper reports.

This Skill contains its complete report design. Do not install or invoke
`article-to-html`; its paper-style presentation layer is already embedded in
[assets/report-template.html](assets/report-template.html).

## Required workflow

1. Read [references/compliance.md](references/compliance.md),
   [references/search.md](references/search.md), and
   [references/collaboration.md](references/collaboration.md).
2. Select paper mode or candidate batch mode from the input shape.
3. For candidate batch mode, follow `references/collaboration.md` and return
   the batch result immediately; steps 4–11 below apply only to paper mode.
4. Open the official arXiv page. Preserve its exact paper title and complete
   ordered author list.
5. Start a roughly 20-second enrichment budget after resolving the paper.
6. Search all authors in the largest parallel batches the host supports.
7. Accept a professional field only when a clickable public page supports it.
8. Stop at the budget. Retain every author and mark unknown values explicitly.
9. Generate the single local report described in **Report composition**.
10. Automatically attempt the publication workflow in
   [references/publishing.md](references/publishing.md) when an authorized
   GitHub remote and write-capable host tool are available.
11. Return an ordered chat table, the local report link, the verified report
   URL, and the verified collection homepage URL when publication succeeds.

Do not delay the author result to perform exhaustive profile auditing.
GitHub Pages propagation can take longer than the enrichment budget; distinguish
search time from publication time.

## Search contract

For each author, issue one focused query:

```text
"<exact author name>" "<paper title or distinctive acronym>"
```

Use at most one follow-up query:

```text
"<exact author name>" (university OR lab OR GitHub OR homepage OR email)
```

Prefer personal, institutional, laboratory, project, GitHub, and OpenReview
pages. A search snippet may locate a page but cannot alone verify a field.
Do not repeatedly rewrite failed searches or enumerate guessed URLs.

## Evidence states

- `已核验`: the exact person and field are supported by relevant public
  professional evidence.
- `可能匹配`: a plausible result exists but identity ambiguity remains.
- `暂未找到`: no usable result was found inside the time budget.
- `未执行网页检索`: the host lacks native web search.

Every non-empty institution, email, homepage, GitHub, or OpenReview value must
have a clickable evidence URL. Never construct an email address from a name or
institutional convention.

## Host without web search

When native web search is unavailable:

1. Read the official arXiv page when URL access exists.
2. Preserve every author in paper order.
3. Generate Google Scholar, LinkedIn, and Maimai locator URLs.
4. Mark every author `未执行网页检索`.
5. Still return the chat table and HTML report.

If the arXiv page also cannot be read, report that the paper cannot be resolved
and do not invent an author list. Never request a local runtime or silently
substitute a scraper.

## Report composition

Copy [assets/report-template.html](assets/report-template.html) to
`outputs/<arxiv-id>/report.html` and replace every token with escaped report
content:

- `{{ARXIV_ID}}`
- `{{PAPER_TITLE}}`
- `{{ARXIV_URL}}`
- `{{GENERATED_AT}}`
- `{{PAPER_META}}`
- `{{TLDR_BODY}}`
- `{{OVERVIEW_BODY}}`
- `{{AUTHOR_ROWS}}`
- `{{LIMITATIONS_BODY}}`
- `{{REFERENCE_ITEMS}}`

Use the embedded structures exactly:

- `.doc`, `.doc-header`, `.doc-eyebrow`, `.doc-title`, and `.doc-meta`;
- the top `.tldr` result summary;
- numbered sections `01` 论文概览, `02` 作者与公开联系路径, and `03` 证据与边界;
- a detailed `01` 论文概览 that explains the paper problem, method shape,
  evaluation setting, and why these authors are relevant recruiting leads;
- one `.author-row` for every author, in exact arXiv order;
- direct source links in `.contact-list`, `.evidence-list`, and the References footer.

Keep the interface text Chinese. Preserve the paper title, author names,
quotations, and original evidence excerpts exactly as their sources present them.
Use no search controls, filters, collapsible audit panels, scoring, recruiting
recommendations, scripts, external stylesheets, external fonts, or CDN assets.

Escape `&`, `<`, `>`, `"`, and `'` before insertion. Permit link targets only
with `https`, `http`, and `mailto` schemes. Include `rel="noreferrer noopener"`
on external HTTP links.

## Output contract

Write only `outputs/<arxiv-id>/report.html` locally for the requested paper.
Chat and HTML must contain the same ordered authors and core values.

The report is a single-file, static, responsive evidence document. It includes
only the paper overview, ordered author entries, public contact paths,
verification states, evidence boundaries, and direct references.

Automatic publication copies the finished file to
`<arxiv-id>/index.html` on `gh-pages` and refreshes the branch's root
`index.html` report list; it must not add reports to `main`.
If publication cannot run or cannot be verified, return the local report
immediately and state the concrete limitation. Never fabricate or pre-announce
a live URL.
