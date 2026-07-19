# Cross-Agent Author Contact Discovery Design

## Goal

Turn a specific arXiv paper, arXiv identifier, or exact title into a
complete list of its authors and evidence-backed public professional contact
routes. Package the workflow so any Agent Skills-compatible agent can use it,
while retaining a standalone CLI for systems that do not load skills.

Success means:

- Every paper author appears exactly once and in paper order.
- Every author has a contact status, even when no contact is found.
- Every reported contact has field-level provenance and an identity confidence.
- Restricted platforms remain locator-only.
- The core workflow has no dependency on Codex, Claude Code, MCP, or a hosted
  service.

## Privacy and Compliance Boundary

Collect only contact information that the author or their organization has
made publicly available for professional use:

- Email addresses explicitly presented for professional use on a public
  author, institutional, employer, or laboratory page
- Public laboratory, university, company, or personal research homepages
- Public contact forms
- Public GitHub and OpenReview profiles
- Locator links for Google Scholar, LinkedIn, and Maimai

Do not collect or derive:

- Private phone numbers, home addresses, or personal records
- Data from breaches, people-search brokers, or credentialed accounts
- Guessed email addresses based on a name and domain
- Email-validity probes that send mail or otherwise contact the person
- Data obtained by bypassing login, CAPTCHA, paywall, robots rules, or access
  controls

Google Scholar, LinkedIn, Maimai, ResearchGate, Academia.edu, and unlicensed
commercial indexes remain locator-only. The program may construct search URLs
but must not fetch or parse their search results or profiles.

## Chosen Architecture

Use an open Skill plus a deterministic local CLI and optional thin
platform-specific metadata.

### Skill Layer

The repository root is an Agent Skills-compatible skill:

- `SKILL.md` contains a platform-neutral workflow.
- `references/` contains source, compliance, identity, and installation
  details.
- Optional metadata such as `agents/openai.yaml` enhances a particular agent
  platform but is not required by the workflow.

The Skill must not name proprietary agent tools, assume a browser or MCP
server, use a platform-specific virtual-environment path, or require an agent
to grant permissions through a particular user interface. It tells the agent
to execute the bundled CLI and interpret its standard artifacts.

An Agent Skills-compatible agent that can run local commands can use the
project directly. An agent that can only read skills presents the exact CLI
command to the user instead of improvising a manual search.

### CLI Layer

`scripts/researcher_recruiting.py` and the installed
`researcher-recruiting` command are the stable interfaces. They accept a paper
identifier or title, output directory, refresh flag, and optional source
overrides.

The CLI:

1. Resolves the paper and author list.
2. Creates one candidate seed per author in paper order.
3. Enriches identities and public professional contact routes.
4. Computes identity and contact statuses.
5. Writes the standard artifacts atomically.

The CLI returns failure only when it cannot resolve the paper or obtain a
trustworthy author list. Individual source or author failures produce partial
artifacts and explicit statuses.

### Core Library

`researcher_recruiting/` remains independent of agent runtimes. It owns source
adapters, crawling policy, caching, identity resolution, contact aggregation,
and exporters. API keys, proxies, and higher-quota services are optional.

No commercial API may be a required dependency. Source adapters must preserve
partial results when another source is unavailable.

## Contact Data Model

Add a structured contact model rather than relying on a single email field.

### ContactPoint

Each contact point contains:

- `kind`: `professional_email`, `contact_form`, `homepage`, `github`,
  `openreview`, `google_scholar_locator`, `linkedin_locator`, or
  `maimai_locator`
- `value`: email address or URL
- `source`: adapter or locator that produced it
- `source_url`: page or API record supporting the value
- `collected_at`: UTC collection timestamp
- `confidence`: integer from 0 to 100
- `direct`: whether a recruiter can use the value as a direct contact route
- `metadata`: optional public context such as affiliation or account handle

Contact points are deduplicated by normalized kind and value while preserving
all supporting evidence.

### ContactStatus

Every author receives one of:

- `found`: at least one public professional contact belongs to a confirmed or
  probable identity
- `not_found`: all applicable sources completed without finding a contact
- `ambiguous`: possible contacts exist, but identity evidence is insufficient
- `sources_unavailable`: no contact was found and one or more required contact
  sources could not be checked

Locator links alone do not change `not_found` into `found`, because they are
research routes rather than verified profiles or direct contacts.

Applicable direct-contact sources are paper metadata, discovered public
homepages, public GitHub profiles, and public OpenReview or ORCID profiles. Use
`sources_unavailable` only when no direct contact was found and at least one
applicable source could not complete; use `not_found` when all applicable
sources completed without a contact.

Direct contact points enter the primary candidate fields only for `confirmed`
or `probable` identities. Possible contacts for an ambiguous identity remain
in evidence with the ambiguous status.

## Discovery and Verification Flow

Apply this order for every author:

1. Extract any explicit public professional contact from paper metadata.
2. Discover and inspect robots-permitted institutional, employer, laboratory,
   and public research homepages.
3. Read public GitHub profile fields, including public email, profile URL, and
   homepage.
4. Read public OpenReview and ORCID fields that help confirm identity or expose
   professional links.
5. Use scholarly sources such as OpenAlex, Semantic Scholar, DBLP, Crossref,
   PubMed, Europe PMC, and INSPIRE to corroborate identity, affiliation,
   coauthors, and research topic.
6. Generate high-precision Google Scholar, LinkedIn, and Maimai locator links
   using the author name, affiliation, and paper context.

Identity resolution considers name variants, affiliation, coauthors, research
topics, verified identifiers, and cross-linked profiles. A name-only match is
never enough to promote an identity or contact.

## Output Contract

Every successful or partial run writes exactly:

- `report.md`
- `candidates.csv`
- `candidates.json`
- `evidence.json`
- `run-log.json`

### candidates.csv

Keep one row per author, in paper order. Include contact status, primary
professional email, contact form, homepage, GitHub, OpenReview, Google Scholar
locator, LinkedIn locator, Maimai locator, identity state, confidence, and
short matching reasons.

### candidates.json

Include the complete structured `contact_points` collection, all existing
candidate fields, contact status, and evidence references.

### evidence.json

Preserve field-level source name, value, URL, collection time, candidate
association, and metadata. Redact credentials and API secrets.

### report.md

Lead with author coverage and public contactability. For every author, show:

- Identity state and confidence
- Contact status
- Direct public professional contact routes
- Public profile links
- Locator-only research links
- Supporting evidence or an explicit explanation of why contact was not found

### run-log.json

Record which sources were attempted for each author and distinguish `ok`,
`not_found`, `source_unavailable`, and `blocked_by_robots`. A blank contact
field is never sufficient to infer that no contact exists.

## Error Handling

- Retain all authors when an enrichment source fails.
- Bound rate-limit waits and network retries.
- Cache sanitized responses, falling back to a temporary writable location
  when the default cache is unavailable.
- Treat malformed, unavailable, and access-restricted sources as explicit
  source outcomes.
- Avoid substituting a prohibited scraper when a public source fails.
- Write artifacts atomically so interrupted runs do not look complete.

## Cross-Agent Packaging

The README documents four entry paths:

1. Generic Agent Skills installation
2. Claude Code-compatible skill installation
3. Codex-compatible skill installation
4. Standalone Python CLI installation

The generic path is normative. Platform-specific sections may specify where
to place or link the skill directory, but they must invoke the same script and
must not fork the workflow.

The Skill uses relative paths from its own directory and a generic Python
3.11-or-newer setup. It may recommend an out-of-repository virtual environment
without hard-coding a platform-specific location.

## Testing Strategy

### Unit tests

Cover contact-point normalization, deduplication, primary-contact selection,
professional-email acceptance, locator classification, identity gating, and
contact-status calculation.

### Source contract tests

Use fixed responses for public GitHub, OpenReview, ORCID, public homepages, and
scholarly sources. Verify that source adapters emit structured evidence and do
not infer private data.

### Pipeline and exporter tests

Verify that:

- Every input author appears once and remains in paper order.
- Partial source failures retain all authors.
- Every author receives a contact status.
- Ambiguous contacts do not enter primary contact fields.
- CSV, JSON, Markdown, evidence, and run-log artifacts agree.

### Network smoke test

Keep an opt-in real-paper test that confirms all five artifacts are generated
and all parsed authors appear, without requiring every upstream source to be
available.

### Skill behavior tests

Run a baseline scenario without the revised Skill and a forward scenario with
it. The forward scenario passes only when a generic agent:

- Uses the bundled CLI rather than an ad hoc search
- Preserves every paper author
- Inspects `run-log.json`
- Reports contact status and evidence
- Keeps Google Scholar, LinkedIn, and Maimai locator-only
- Does not rely on Codex- or Claude-specific commands

## Non-Goals

- Sending recruiting messages
- Ranking candidates for hiring decisions
- Inferring protected or sensitive personal attributes
- Circumventing access controls
- Hosting a mandatory central service
- Guaranteeing that every author has a public contact route

The guarantee is complete author coverage and explicit contact status, not a
fabricated contact for every author.
