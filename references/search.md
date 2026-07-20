# Native web search

## Time budget

Resolve the official arXiv page first, then spend approximately 20 seconds on
author enrichment. Batch independent authors in parallel. Stop at the budget
and render partial results; do not wait for one slow site.

## Query sequence

Use one primary query per author:

```text
"<author>" "<paper title or distinctive acronym>"
```

Use at most one follow-up when the first query is sparse:

```text
"<author>" (university OR lab OR GitHub OR homepage OR email)
```

Do not repeatedly rewrite queries, enumerate guessed URL variants, or wait for
every author serially when the host supports parallel search.

## Evidence priority

1. Personal professional homepage.
2. Institution, laboratory, project, or conference page.
3. Public GitHub or OpenReview profile.
4. Exact scholarly profile supported by paper context.
5. Search locator for a restricted platform.

Public email requires a directly supporting page. A search snippet or guessed
address is not evidence. Conflicting identities remain `可能匹配`.

## Batch behavior

Use the largest search batch supported by the host. Extract only the strongest
result for each author, verify it directly when time permits, and stop once one
authoritative public route is established. Preserve unresolved authors instead
of spending the whole budget on them.

## Restricted-platform search

Google Scholar, LinkedIn, Maimai, ResearchGate, and Academia.edu may appear in
ordinary search results, and the host Agent may open pages that are public
without login. Treat them as regular evidence only when the page itself is
accessible, relevant, and supports the author's identity. Do not log in, solve
CAPTCHAs, bypass access controls, or run batch scrapers.

When direct public evidence is unavailable, generate safe locator URLs instead
of opening or scraping the restricted destination:

- Google Scholar:
  `https://scholar.google.com/scholar?q=<url-encoded-author>`
- LinkedIn:
  `https://www.google.com/search?q=site%3Alinkedin.com%2Fin+<url-encoded-author>`
- Maimai:
  `https://www.baidu.com/s?wd=site%3Amaimai.cn+<url-encoded-author>`

Locator links are discovery aids, not verified profiles or direct contacts.
