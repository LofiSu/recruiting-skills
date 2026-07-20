# Public researcher-data boundaries

## Allowed

- Read official arXiv pages and public professional webpages.
- Use the host Agent's ordinary web search and browsing capabilities.
- Record public professional email addresses, contact forms, homepages,
  institutional profiles, GitHub, and OpenReview when a public page directly
  supports the value.
- Generate search or locator URLs for restricted platforms.
- State ambiguity, conflicts, missing evidence, time-budget exhaustion, and
  missing web capabilities.

## Forbidden

- Guessing an email address from a name or institutional convention.
- Collecting private, personal, or non-professional contact information.
- Logging in to or directly scraping Google Scholar, LinkedIn, Maimai,
  ResearchGate, Academia.edu, or licensed commercial products.
- Requesting cookies, session tokens, shared credentials, or CAPTCHA solving.
- Bypassing robots rules, paywalls, or other access controls.
- Treating a same-name profile or search snippet as confirmed identity.
- Ranking candidates, making employment decisions, or sending outreach.

## Decision rules

Retain every paper author even when nothing is found. A restricted-platform
locator is not a verified profile or direct contact.

Mark a value `已核验` only when a directly relevant public page supports both
the person's identity and the field. Use `可能匹配` for unresolved identity
ambiguity and `暂未找到` when the bounded search returns no usable evidence.

These outputs are research leads for human review. Preserve uncertainty and
link the evidence used for every non-empty professional field.
