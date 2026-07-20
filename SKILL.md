---
name: researcher-recruiting-skill
description: Use when finding the authors, institutions, public professional contact routes, homepages, GitHub or OpenReview profiles, and evidence for an arXiv paper or exact research-paper title.
---

# Researcher Recruiting

Return useful author leads quickly. Use the host Agent's native web search and
browsing tools; never install or invoke a local runtime.

## Required workflow

1. Read [references/compliance.md](references/compliance.md) and
   [references/search.md](references/search.md).
2. Open the official arXiv page. Preserve its exact paper title and complete
   ordered author list.
3. Start a roughly 20-second enrichment budget after resolving the paper.
4. Search all authors in the largest parallel batches the host supports.
5. Accept a professional field only when a clickable public page supports it.
6. Stop at the budget. Retain every author and mark unknown values explicitly.
7. Copy [assets/report-template.html](assets/report-template.html) to
   `outputs/<arxiv-id>/report.html`, replace the example tokens and row comment
   with escaped results, and keep the file self-contained.
8. Return an ordered chat table and a link to the HTML report.

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

## Output contract

Write only `outputs/<arxiv-id>/report.html` for the requested paper. Chat and
HTML must contain the same ordered authors and core values.

Escape every collected value before inserting it into HTML. Permit links only
for `https`, `http`, and `mailto`. Keep names and paper titles exactly as the
source presents them.

The report must remain static: no scripts, search controls, status filters,
audit toggles, sticky indexes, source-attempt dumps, candidate ratings, or
automated recruiting recommendations.
