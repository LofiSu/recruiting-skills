# HTML-Only Recruiting Report Design

## Goal

Change every successful or partial researcher-recruiting run to produce one
self-contained `report.html` file and no Markdown, CSV, or JSON sidecar
artifacts.

## Output contract

The CLI continues to create a timestamped run directory under `--output`.
That directory contains exactly one file:

```text
report.html
```

The CLI prints the run directory as it does today. The HTML file is the
complete human-readable and audit-ready result. There is no legacy-output
flag and no optional multi-file mode.

## Report contents

The report contains:

- paper title, arXiv identifier, source link, categories, and abstract;
- every paper author in paper order;
- affiliation, identity state, confidence, and contact status for each author;
- verified public professional email, contact form, homepage, GitHub, and
  OpenReview links when present;
- locator-only links for Google Scholar, LinkedIn, and Maimai;
- identity reasons and evidence with source URLs;
- per-author source attempts, source status, and redacted errors;
- collection-boundary and compliance notices.

The page includes client-side author search and contact-status filtering.
CSS and JavaScript are embedded, so the file works offline without external
assets. The report remains useful with JavaScript disabled because all
authors and evidence are rendered into the HTML before it is written.

## Data flow and architecture

The pipeline and source adapters remain unchanged. The exporter continues to
build normalized candidate records and author-scoped source-attempt records
in memory. A new HTML renderer consumes those records and produces the single
document.

`write_artifacts` keeps its existing callable interface for compatibility,
but its artifact constant and atomic write operation change to the one-file
contract. The existing serializers may remain as internal helpers where they
support rendering or tests, but they do not write sidecar files.

## Security and privacy

All paper, author, source, evidence, and error text is HTML-escaped. Link
rendering accepts only `https`, `http`, and `mailto` schemes appropriate to
the displayed field; unsafe or malformed links render as text rather than
clickable anchors.

The existing secret-redaction and opaque paper-email-provenance rules apply
before content reaches the report. The page does not load remote scripts,
fonts, images, stylesheets, or analytics, and it does not execute evidence
content as markup or JavaScript.

## Failure behavior

Partial runs still produce the report. Missing contacts, ambiguous
identities, unavailable sources, robots exclusions, and rate limits remain
explicit instead of removing an author. A filesystem write failure preserves
the current CLI exit-code behavior and does not leave a partially published
run directory.

## Documentation contract

`SKILL.md`, `README.md`, installation guidance, source guidance, portability
checks, and skill cases describe `report.html` as the only artifact. Agents
must inspect the source-attempt section inside the report before interpreting
a missing contact.

## Test strategy

Tests first establish that the current exporter violates the new contract.
The implementation then must prove:

- a run directory contains exactly `report.html`;
- all authors, contact statuses, locator links, evidence, and source attempts
  appear in the document;
- verified contacts and public profiles are rendered correctly;
- unavailable-source and no-contact explanations remain visible;
- duplicate author names stay scoped by author ID and paper order;
- secrets and paper-email provenance remain absent;
- HTML injection and unsafe URL schemes cannot create executable content;
- the CLI and real-network smoke test use the one-file contract;
- skill validation, Python compilation, and the non-network suite pass.

Finally, the real paper `arXiv:2601.21998` is rerun to create a user-facing
HTML example in `outputs/`.
