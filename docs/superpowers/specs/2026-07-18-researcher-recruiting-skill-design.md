# Researcher Recruiting Skill Design

## 1. Objective

Build a reusable Codex skill and standalone Python CLI that accepts an arXiv paper, enumerates its authors, discovers public academic and professional identity signals, resolves likely identities with source-backed confidence, and exports a recruiting-oriented report.

The first version must:

- parse an arXiv URL, arXiv identifier, or paper title;
- retrieve public data from arXiv, OpenReview, Semantic Scholar, ORCID, GitHub, personal sites, and lab sites;
- generate candidate search links for Google Scholar, LinkedIn, and Maimai without scraping restricted profiles;
- retain field-level source URLs and collection timestamps;
- distinguish confirmed, probable, ambiguous, and not-found identities;
- produce Markdown, CSV, JSON, evidence, and run-log artifacts;
- run locally as both a Codex skill and a normal command-line program.

## 2. Scope and Boundaries

### In scope

- Public APIs and public web pages.
- Public HTML crawling that respects robots.txt, rate limits, timeouts, and access controls.
- Identity disambiguation based on explicit, reviewable evidence.
- Partial results when one or more sources are unavailable.
- Proxy and API-token configuration through environment variables.
- Local response caching.

### Out of scope

- Circumventing authentication, CAPTCHA, paywalls, access controls, or anti-bot systems.
- Copying authenticated browser cookies or account credentials.
- Scraping LinkedIn or Maimai profile content.
- Automated outreach, connection requests, or recruiting messages.
- Treating a matching name as sufficient proof of identity.
- A hosted multi-user service, database, or MCP server in the first version.

Google Scholar, LinkedIn, and Maimai are locator-only sources in the first version. The tool generates search URLs and marks them for human confirmation.

## 3. Chosen Approach

Use a Codex skill with bundled Python crawler and enrichment code.

The skill is responsible for:

- detecting relevant requests;
- validating the requested paper input;
- invoking the bundled CLI;
- explaining partial failures and confidence labels;
- presenting the generated artifacts to the user;
- enforcing the restricted-source boundary.

The Python package is responsible for deterministic network access, parsing, caching, identity scoring, evidence retention, and exports. The same package must be independently runnable without Codex.

This approach is preferred over a prompt-only skill because it provides stable parsing, reproducible outputs, explicit retries, and testable identity rules. It is preferred over an MCP service for the first version because it avoids hosting and operational overhead.

## 4. Repository and Skill Structure

```text
researcher-recruiting-skill/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   └── researcher_recruiting.py
├── researcher_recruiting/
│   ├── cli.py
│   ├── models.py
│   ├── pipeline.py
│   ├── cache.py
│   ├── crawling.py
│   ├── identity.py
│   ├── search_links.py
│   ├── exporters.py
│   └── sources/
│       ├── arxiv.py
│       ├── openreview.py
│       ├── semantic_scholar.py
│       ├── orcid.py
│       ├── github.py
│       └── public_web.py
├── references/
│   ├── sources.md
│   ├── identity-matching.md
│   └── compliance.md
├── tests/
│   ├── fixtures/
│   ├── test_arxiv.py
│   ├── test_identity.py
│   ├── test_crawling.py
│   ├── test_exporters.py
│   └── test_pipeline.py
├── pyproject.toml
└── README.md
```

`scripts/researcher_recruiting.py` is a thin, stable entry point for Codex. Reusable behavior lives in the Python package rather than in one large script.

## 5. Data Flow

1. Accept an arXiv URL, arXiv identifier, or paper title.
2. Resolve the input to an arXiv record.
3. Extract title, abstract, categories, submission date, ordered authors, affiliations, and public contact information.
4. Build an identity seed for each author:
   - normalized name;
   - name variants;
   - original affiliation;
   - public email domain;
   - coauthors;
   - paper title;
   - research keywords.
5. Query API-backed sources and eligible public web sources concurrently within per-domain limits.
6. Follow identity links only from sufficiently credible public sources, such as an institutional homepage linking to ORCID or GitHub.
7. Normalize source results into evidence records.
8. Group candidate records that may represent the same person.
9. Score each candidate identity using explicit evidence and conflicts.
10. Generate locator-only search links for Google Scholar, LinkedIn, and Maimai.
11. Export the report, candidate table, machine-readable records, evidence, and run log.

The pipeline must continue when an optional source fails. It must stop only when the paper cannot be resolved or no author list can be established.

## 6. Source Strategy

### API-backed sources

- arXiv: authoritative paper metadata and author order.
- OpenReview: public profiles, submissions, and public review activity where available.
- Semantic Scholar: paper-author graph, publications, citations, and author candidates.
- ORCID: public researcher identifiers and public record fields within API terms.
- GitHub: public accounts and repositories through the official API when possible.

### Public-web sources

- Institutional personal pages.
- Lab and research-group pages.
- Public CV or biography pages explicitly linked from credible sources.

Public crawling must:

- evaluate robots.txt before crawling;
- use a descriptive User-Agent;
- enforce per-domain concurrency and delay;
- follow bounded redirects;
- set connect and response timeouts;
- limit response size and accepted content types;
- avoid form submission and authenticated areas;
- cache successful public responses;
- record the final URL and collection time.

HTTP fetching is the default. JavaScript browser automation is not required for the first version and must not be used to bypass a site's intended access model.

### Locator-only sources

- Google Scholar.
- LinkedIn.
- Maimai.

For these sources, generate encoded search URLs using the researcher's name plus institution or topic. Do not request or parse the resulting profile pages.

## 7. Identity Resolution

Name equality alone is weak evidence. The resolver must combine multiple independent signals.

### Strong evidence

- Matching ORCID.
- An institutional page explicitly linking to the candidate account.
- Reciprocal links between credible profiles.
- A unique public email address matching the paper or institutional page.

### Supporting evidence

- Matching current or historical institution.
- Exact paper overlap.
- Coauthor overlap.
- Matching email domain.
- Consistent research topics.
- Consistent geographic or employment timeline.

### Conflicts

- Different ORCID identifiers.
- Incompatible simultaneous institutions or timelines.
- Unrelated research history with no overlapping papers or coauthors.
- A credible page indicating that the account belongs to another person.

The implementation will use deterministic weighted rules defined in one module and documented in `references/identity-matching.md`. The exact numeric weights and thresholds will be test-driven against representative fixtures before they are finalized.

Identity states:

- `confirmed`: a strong identifier or multiple independent, non-conflicting signals.
- `probable`: substantial supporting evidence without a decisive strong identifier.
- `ambiguous`: two or more plausible candidates or material unresolved conflicts.
- `not_found`: successful searches produced no credible candidate.

If required sources were unavailable, use `source_unavailable` at the source level and do not convert the overall outcome to `not_found` solely because of that failure.

Every identity decision must include human-readable reasons and references to the evidence records used.

## 8. Output Contract

Each run creates:

```text
results/<arxiv-id>-<timestamp>/
├── report.md
├── candidates.csv
├── candidates.json
├── evidence.json
└── run-log.json
```

Each candidate record includes:

- paper identifier and title;
- author name and author order;
- original affiliation;
- current public affiliation, role, and location when found;
- public email and email domain when found;
- personal and lab homepages;
- OpenReview, Semantic Scholar, ORCID, and GitHub URLs;
- Google Scholar, LinkedIn, and Maimai locator URLs;
- identity state and numeric confidence;
- human-readable match reasons;
- field-level source references;
- collection timestamps;
- a blank recruiting-notes field for human use.

`evidence.json` contains normalized source facts and provenance. `run-log.json` contains source status, timings, retry counts, cache status, warnings, and sanitized errors.

## 9. Configuration and Secrets

Support standard proxy variables:

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `NO_PROXY`

Support optional source credentials through environment variables:

- `GITHUB_TOKEN`
- `SEMANTIC_SCHOLAR_API_KEY`
- ORCID public-client credentials if the selected endpoints require them.

Do not store secrets, browser cookies, or authenticated session data in source files, output artifacts, logs, fixtures, or caches. Redact authorization headers and secret-looking query parameters from errors.

The CLI must still produce useful partial output when optional credentials are absent.

## 10. Failure Handling

- Retry rate limits and transient server errors with bounded exponential backoff and jitter.
- Honor `Retry-After` when provided.
- Do not retry permanent client errors except where a token refresh or alternate public endpoint is explicitly supported.
- Isolate failures by source and author.
- Treat malformed responses as source errors and retain diagnostic metadata without raw secrets.
- Mark a source as `source_unavailable` when network policy, DNS, timeout, authentication, or rate limiting prevents a conclusive lookup.
- Distinguish `not_found` from `source_unavailable` in all exports.
- Return a nonzero process status only for invalid input, unresolved paper identity, unrecoverable output failure, or an internal invariant violation.

## 11. Testing and Validation

### Code tests

- Parser fixtures for arXiv XML/HTML and each supported source format.
- Identity fixtures covering:
  - common names;
  - Chinese and Western name-order variants;
  - transliteration variants;
  - institution changes;
  - conflicting ORCID identifiers;
  - overlapping and non-overlapping coauthors;
  - exact and partial paper overlap.
- Crawler tests for robots denial, redirect limits, unsupported content, oversized responses, timeouts, 429 handling, malformed HTML, and cache refresh.
- Export tests that assert stable schemas and provenance.
- Pipeline tests proving that a single-source failure still produces structurally complete artifacts.

Network-dependent checks are separate from deterministic fixture tests. One real arXiv paper will be used for an opt-in end-to-end check.

### Skill tests

Before writing the skill, run a baseline request without it and record whether Codex:

- selects appropriate public sources;
- preserves evidence;
- avoids restricted profile scraping;
- distinguishes unavailable sources from absent identities;
- produces the required artifacts.

After writing the skill, repeat the same request with the skill and verify compliance. Forward testing must use a clean context and a realistic user prompt.

### Acceptance criteria

- No author is marked `confirmed` from name equality alone.
- Every populated identity field has provenance.
- Restricted sources remain locator-only.
- A partial network failure still produces all five artifact files.
- Secrets are absent from artifacts and logs.
- The CLI works independently, and Codex invokes the same CLI through the skill.
- Unit and fixture-based tests pass without network access.
- The opt-in end-to-end run either succeeds or reports source availability accurately without fabricating data.

## 12. Distribution

The canonical repository is:

```text
git@github.com:LofiSu/researcher-recruiting-skill.git
```

The repository is both a normal Python project and the skill folder. After cloning, a user can place or link it under the personal Codex skills directory so Codex can discover `SKILL.md`.

The initial repository uses the `main` branch. Design, implementation, validation, and installation guidance are committed as normal project history.

## 13. Deferred Work

The following items are intentionally deferred:

- MCP server packaging;
- hosted multi-user operation;
- database-backed historical candidate tracking;
- scheduled paper monitoring;
- recruiter collaboration and permissions;
- automated outreach;
- authenticated access to professional networks;
- JavaScript-browser crawling for sites that do not expose public HTML.
