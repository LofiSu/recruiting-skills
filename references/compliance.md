# Collection and recruiting boundaries

## Allowed

- Query documented public APIs with their published authentication methods.
- Fetch public arXiv, institutional, laboratory, personal, and code-profile
  pages when robots policy permits.
- Record public professional email addresses, contact forms, homepages, and
  professional profiles explicitly published by the person or institution.
- Generate search/locator URLs for restricted or licensed platforms.
- Cache sanitized public response bodies and retain field-level source URLs and
  collection times.
- Report ambiguous candidates, conflicts, missing credentials, rate limits,
  and robots denials.

## Forbidden

- Logging in to LinkedIn, Maimai, Google Scholar, ResearchGate, Academia.edu,
  or commercial scholarly products to scrape profiles.
- Requesting or reusing browser cookies, session tokens, shared accounts, or
  another person's credentials.
- Solving or outsourcing CAPTCHAs; rotating fingerprints or proxies to evade
  anti-bot controls; bypassing robots.txt, paywalls, or access controls.
- Guessing private email addresses or collecting non-public contact data.
- Treating identical names, Wikidata alone, ROR, or citation links as confirmed
  identity.
- Automatically contacting, ranking out, or making employment decisions about
  people.

## Decision rule

When an official public API or permitted public page is unavailable, record
`source_unavailable` or `blocked_by_robots` and continue. Never replace that
lane with a prohibited scraper. Restricted platforms remain locator-only even
when the user has an account or asks for “deeper crawling.”

Retain every paper author. Report one explicit contact status per author:
`found`, `not_found`, `ambiguous`, or `sources_unavailable`. A locator-only
link is not a verified direct contact, and an unavailable source is not proof
that no public contact exists.

Outputs are research leads requiring human review. Preserve provenance and
state uncertainty plainly.
