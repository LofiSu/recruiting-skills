---
name: research-talent-scout
description: Use when finding cohorts of graduate researcher candidates by graduation year, degree, institution, venue, or authorship thresholds, especially when results require indexed filtering before selective public-profile enrichment.
---

# Research Talent Scout

Use a local evidence-backed index for fast candidate discovery. Treat results as research leads for human review, not hiring decisions.

## Required workflow

1. Read `references/compliance.md`, `references/evidence-policy.md`, `references/schema.md`, `references/venue-policy.yaml`, and `references/handoff.md`.
2. Parse the user's years, degrees, thresholds, venues, publication categories, institutions, and acceptable graduation states.
3. Interpret “more than N” with `--strictly-greater`; do not silently convert it to “at least N.”
4. Query the local SQLite index before considering live discovery.
5. Return `confirmed` and `likely_needs_verification` candidates separately.
6. Preserve qualifying publication links, graduation evidence, verification timestamps, coverage, and warnings.
7. When public-profile enrichment is requested and `researcher-recruiting-skill`
   is available, create exactly one `candidate_enrichment_batch` containing
   only qualifying candidates and merge its result by stable candidate ID.
8. If coverage is incomplete or stale, report the gap. Do not block the indexed result on broad live-web discovery.
9. Never convert inferred dates, ambiguous identities, or snippets into confirmed facts.

## Commands

Initialize an index:

```bash
python3 scripts/init_index.py --db <path>
```

Import normalized JSONL records:

```bash
python3 scripts/import_records.py --db <path> --input <records.jsonl>
```

Query the index:

```bash
python3 scripts/query_candidates.py \
  --db <path> \
  --graduation-years 2027,2028 \
  --degree-threshold phd=5,masters=3 \
  --strictly-greater \
  --venues ACL,ICML,ICLR,NeurIPS,EMNLP,CVPR,AAAI,ICCV,MLSys,OSDI,EuroSys,ASPLOS,ISCA,SC,PPoPP \
  --categories main_first,co_first,findings,workshop,short,demo \
  --graduation-states confirmed,likely_needs_verification
```

Render query JSON as Chinese Markdown:

```bash
python3 scripts/export_results.py --input <results.json>
```

## Output rules

- Do not rank candidates or claim that a candidate should be hired.
- State the index scope and freshness with every result.
- Link every qualifying paper and confirmed graduation field to public professional evidence.
- Keep ambiguous same-name people separate and surface identity warnings.
- Use `unknown` explicitly instead of guessing.
