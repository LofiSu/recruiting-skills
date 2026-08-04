# Record contracts

Each JSONL line contains one candidate and related normalized records:

```json
{
  "candidate": {
    "id": "stable-id",
    "name": "Name",
    "degree": "phd",
    "institution": "University",
    "lab": "Lab",
    "graduation_year": 2027,
    "graduation_state": "confirmed",
    "identity_state": "verified",
    "homepage": "https://example.edu/name",
    "verified_at": "2026-08-04"
  },
  "publications": [{
    "source_id": "source:key",
    "title": "Paper",
    "year": 2026,
    "venue": "NeurIPS",
    "category": "main_first",
    "url": "https://example.org/paper"
  }],
  "evidence": [{
    "field": "graduation_year",
    "state": "confirmed",
    "source_type": "personal_cv",
    "url": "https://example.edu/cv.pdf",
    "excerpt": "Expected graduation: 2027",
    "retrieved_at": "2026-08-04"
  }]
}
```

Allowed degrees: `phd`, `masters`. Allowed identity states: `verified`, `ambiguous`. Allowed evidence and authorship states are defined in `evidence-policy.md`.

Query JSON contains `confirmed`, `likely_needs_verification`, `coverage`, `generated_at`, and `warnings`. Candidate rows contain categorized counts, qualifying publications, graduation evidence, and timestamps.
