# Evidence policy

## Graduation states

- `confirmed`: a public professional source explicitly binds the person, degree, and expected graduation time.
- `likely_needs_verification`: inferred from program start, academic year, or job-market context.
- `unknown`: no usable evidence.
- `stale`: formerly usable evidence exceeds the query freshness limit.
- `conflict`: credible public sources materially disagree.

Prefer evidence in this order: current personal CV, personal homepage, official institution or laboratory page, adviser page, other public professional profile. Prefer newer and more direct evidence. Never present inferred, stale, or conflicting dates as confirmed.

## Identity

Do not merge people solely by name. Require a stable source identifier or corroboration from publications, institution, coauthors, ORCID, homepage, or equivalent professional evidence. Set identity state to `ambiguous` when unresolved.

## Authorship

- `main_first`: first in the official ordered author list for a main-conference paper.
- `co_first`: direct official or paper evidence states equal contribution.
- `findings`, `workshop`, `short`, and `demo`: preserve separately.
- `unclassified`: do not count by default.
