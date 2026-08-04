# Candidate batch collaboration

Use this mode only when the input object has `type: candidate_enrichment_batch`.
The calling `research-talent-scout` remains owner of filtering, graduation and
publication verification, final merging, and the single user-facing result.

## Input contract

```json
{
  "type": "candidate_enrichment_batch",
  "batch_id": "stable digest",
  "deadline_at": "ISO-8601 timestamp",
  "candidates": [{
    "candidate_id": "stable-id",
    "name": "Exact Name",
    "identity_state": "verified",
    "institution": "Known institution",
    "degree": "phd",
    "graduation_year": 2027,
    "graduation_state": "confirmed",
    "existing_evidence": [],
    "qualifying_publications": [{
      "source_id": "stable-publication-id",
      "title": "Exact paper title",
      "url": "https://..."
    }]
  }]
}
```

Reject a batch without `batch_id`, `deadline_at`, stable `candidate_id`, or at
least one qualifying publication per candidate. Enrich only listed candidates.
Never expand to coauthors or all authors of their papers.

## Search contract

For each candidate, use the exact name plus one qualifying paper title or
distinctive acronym. Use at most one follow-up query. Search candidates in the
largest parallel batch supported by the host and stop at `deadline_at`.

Preserve ambiguous same-name candidates as separate stable IDs. Every non-empty
homepage, public professional contact, GitHub, or OpenReview field requires a
directly opened public professional evidence URL. Search snippets, inferred
email patterns, and identity guesses never verify a field.

## Output contract

Return one object and no HTML report:

```json
{
  "type": "candidate_enrichment_result",
  "batch_id": "same stable digest",
  "completed_at": "ISO-8601 timestamp",
  "candidates": {
    "stable-id": {
      "enrichment_state": "已核验",
      "fields": {
        "homepage": null,
        "professional_contact": null,
        "github": null,
        "openreview": null
      },
      "evidence": [{
        "field": "homepage",
        "url": "https://...",
        "retrieved_at": "ISO-8601 timestamp"
      }],
      "warnings": []
    }
  }
}
```

Allowed enrichment states are `已核验`, `可能匹配`, `暂未找到`, and
`未执行网页检索`. Include every input candidate even when the deadline expires;
use explicit null values and warnings instead of omission.
