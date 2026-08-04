# Enrichment handoff

`research-talent-scout` owns cohort discovery, deterministic filtering, and the
single final result. Use `$researcher-recruiting-skill` only after the local
query has selected qualifying candidates.

## Request

Build one object with `type: candidate_enrichment_batch`, a stable `batch_id`,
an ISO-8601 `deadline_at`, and every qualifying candidate keyed by stable
`candidate_id`. Include existing verification state and qualifying publication
titles/URLs. Never pass non-qualifying candidates or ask the enrichment Skill to
expand to coauthors.

Reserve up to 10 seconds for local filtering and the remaining budget, capped
at approximately 20 seconds, for enrichment. If the other Skill is unavailable
or the deadline expires, return the complete indexed result with explicit
enrichment warnings.

## Merge

Accept only `type: candidate_enrichment_result` with the matching `batch_id`.
Merge by `(candidate_id, field)`. Never overwrite stronger existing evidence,
graduation state, authorship state, or verification timestamp. Preserve every
indexed qualifier even when its enrichment is missing.

Output one result with `confirmed` and `likely_needs_verification` sections,
qualifying publication links, enrichment evidence, coverage, freshness, and
warnings. “All candidates” means all matches inside the declared index coverage,
not exhaustive live-web discovery.
