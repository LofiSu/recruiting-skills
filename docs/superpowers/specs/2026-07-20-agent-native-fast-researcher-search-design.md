# Agent-Native Fast Researcher Search Design

Date: 2026-07-20  
Status: approved in conversation; pending written-spec review

## Goal

Replace the Python-based recruiting research pipeline with a portable,
agent-native Skill that uses the host Agent's built-in web search and browsing
tools. A normal arXiv-author request should return a useful chat summary and a
single compact HTML report in approximately 10–20 seconds without installing
or running Python.

## Scope

The repository becomes a pure Agent Skill. Remove the Python package, CLI,
source adapters, packaging configuration, Python test suite, and the old
multi-source audit workflow.

Retain only the files needed to distribute and operate the Skill:

- `SKILL.md`
- `README.md`
- `agents/openai.yaml`
- concise compliance and search references
- a reusable, self-contained HTML report template
- Skill behavior and portability test scenarios

Generated user reports remain outside version control.

## Default User Experience

An arXiv URL, identifier, paper title, or request to find paper authors triggers
the Skill.

The Agent:

1. Opens the official arXiv page and records the exact paper title and complete
   ordered author list.
2. Uses its native web-search capability to search all authors in parallel or
   in the largest batches supported by the host.
3. Prioritizes personal homepages, institutional and laboratory pages, project
   pages, GitHub, and OpenReview.
4. Uses indexed Google Scholar, LinkedIn, and Maimai results only as locator
   links. It does not log in to or directly scrape restricted profile pages.
5. Stops enrichment at an approximately 20-second global budget and returns
   all results already found.
6. Immediately presents a compact chat table.
7. Writes one self-contained report to
   `outputs/<arxiv-id>/report.html`.

There are no quick, standard, or audit modes. There is no Python fallback.

## Search Strategy

Use one focused query per author:

```text
"<exact author name>" "<paper title or distinctive acronym>"
```

When evidence is sparse, use at most one follow-up query:

```text
"<exact author name>" (university OR lab OR GitHub OR homepage OR email)
```

Batch and parallelize queries where the Agent supports it. Do not repeatedly
rewrite searches or enumerate guessed URLs.

Evidence priority:

1. the person's public professional homepage;
2. an institutional, laboratory, or project page;
3. a public GitHub or OpenReview profile;
4. an exact scholarly profile match;
5. a search-result locator for restricted platforms.

Public email addresses require a directly supporting public page. Never infer
or construct an email address from a name or institutional convention.

## Identity and Evidence States

Each author receives one state:

- `已核验`: the exact person is supported by the paper context and a directly
  relevant public professional page;
- `可能匹配`: a plausible profile exists but the evidence does not safely
  disambiguate the person;
- `暂未找到`: the time-bounded search found no usable public professional
  profile;
- `未执行网页检索`: the host Agent has no web-search capability.

Every institution, homepage, email, GitHub, or OpenReview value must carry a
clickable evidence URL. Search snippets alone cannot upgrade a value to
`已核验`.

## Hosts Without Web Search

If the host Agent cannot search the web:

1. read the arXiv page if URL access is available;
2. preserve the complete ordered author list;
3. generate Google Scholar, LinkedIn, and Maimai locator links;
4. mark every author `未执行网页检索`;
5. still return the chat summary and HTML report.

The Skill must not request Python installation or silently substitute a local
scraper.

## HTML Report

The report is a single static HTML file with no JavaScript and no external
assets. It uses a compact editorial table inspired by the successful chat
search presentation.

The first screen contains:

- paper title and arXiv link;
- submission date and paper-level institution summary when evidenced;
- number of authors and number of verified public contact routes;
- an ordered author table.

The author table contains:

- author name;
- institution;
- public email;
- homepage and professional profiles;
- evidence links;
- identity/evidence state.

Remove all of the following:

- author search input;
- contact-status selector;
- expand/collapse-all button;
- sticky author index;
- scrollspy and back-to-top JavaScript;
- large source-attempt logs;
- nested audit disclosures;
- candidate ranking or star ratings.

The layout must remain readable at desktop and mobile widths and printable
without interactive controls.

## Chat Response

The Agent returns a concise table with the same author order and core values as
the HTML report, then links the generated `report.html`. It explicitly states:

- how many authors were found;
- how many contact routes were verified;
- which authors remain possible or unknown;
- whether the search stopped at the time budget or lacked web access.

## Safety and Collection Boundaries

- Collect only public professional identity and contact information.
- Do not guess private email addresses.
- Do not log in, solve CAPTCHAs, reuse cookies, bypass paywalls, or evade
  robots and anti-bot controls.
- Do not directly scrape Google Scholar, LinkedIn, Maimai, ResearchGate, or
  Academia.edu.
- Do not rank candidates or make employment decisions.
- Preserve uncertainty and conflicting evidence.

## Error Handling

- If one search fails, retain the author and continue with the other results.
- If the global budget expires, generate the report from partial results.
- If arXiv cannot be read, report the blocking error and do not invent an
  author list.
- If file writing is unavailable, return the full chat table and provide the
  single-file HTML as an artifact or code block supported by that host.
- HTML-escape all collected values and allow only safe `http`, `https`, and
  `mailto` links.

## Acceptance Criteria

1. A normal request never checks for, installs, or runs Python.
2. The old Python package, CLI, adapters, packaging metadata, and Python tests
   are absent.
3. ENPIRE (`arXiv:2606.19980`) returns all 17 authors in arXiv order.
4. The Agent targets approximately 10–20 seconds and never waits for the old
   exhaustive API matrix.
5. Chat and HTML contain the same ordered authors and evidence-backed fields.
6. The generated file is exactly `outputs/<arxiv-id>/report.html`.
7. The HTML contains no search controls, audit controls, source-attempt dumps,
   or JavaScript.
8. The Skill validates against the Agent Skills format.
9. Forward tests cover a web-enabled Agent and a host without web search.
10. Restricted platforms remain locator-only.

## Verification Strategy

The existing ENPIRE run is the baseline failure: it required Python, took
minutes, and produced less useful contact discovery than direct Agent search.

Implementation verification will include:

- a Skill pressure scenario demonstrating that the old instructions choose
  Python and miss the speed requirement;
- the same scenario against the revised Skill, confirming native search and no
  Python;
- an ENPIRE forward test checking 17 ordered authors, chat output, evidence,
  and generated HTML;
- a no-web capability test checking graceful locator-only output;
- static validation of the Skill metadata and HTML template;
- inspection at desktop and mobile widths when the browser environment permits.

## Non-Goals

- Rebuilding the removed crawler in another programming language.
- Hosting a centralized search API.
- Guaranteeing a verified contact route for every author.
- Exhaustive bibliographic or citation auditing.
- Crawling restricted social and academic platforms.
- Candidate scoring, ranking, or automated outreach.
