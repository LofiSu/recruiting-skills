# Source behavior

All HTTP sources share the sanitized SQLite cache, robots policy, bounded
response size, per-domain serialization, and retry handling for 429 and
transient 5xx responses. Secrets are sent only in headers or official API
parameters and are redacted from cache keys and output.

## Always-on public sources

| Source | Official base/API | Credential | Evidence |
| --- | --- | --- | --- |
| arXiv | `https://export.arxiv.org/api/query` | none | paper, ordered authors, categories |
| OpenAlex | `https://api.openalex.org/authors`, `/works` | `OPENALEX_API_KEY` optional | author/work IDs, ORCID, institution, DOI, topics |
| Crossref | `https://api.crossref.org/works` | `CROSSREF_MAILTO` recommended | DOI, contributor, ORCID, affiliation |
| Semantic Scholar | `https://api.semanticscholar.org/graph/v1` | `SEMANTIC_SCHOLAR_API_KEY` optional | author, papers, homepage |
| ORCID | `https://pub.orcid.org/v3.0` | `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET` | public record, employment, works, URLs |
| DataCite | `https://api.datacite.org/dois` | none | research-output DOI, creator ORCID, related IDs |
| ROR | `https://api.ror.org/v2/organizations` | none | organization normalization only |
| Wikidata | `https://query.wikidata.org/sparql` | none | supporting-only public identity facts |
| GitHub | `https://api.github.com` | `GITHUB_TOKEN` optional | public user profile, code-profile URL |
| OpenReview | `https://api2.openreview.net/profiles/search` | none | public profile and linked identifiers |

ORCID is reported `source_unavailable` when its public API client credentials
are absent. Optional keys improve quota but do not change identity rules.

## Category-routed sources

| arXiv categories | Source | Official API | Credential |
| --- | --- | --- | --- |
| `cs.*`, `stat.ML`, `eess.*` | DBLP | `https://dblp.org/search/author/api` | none |
| `q-bio.*` | PubMed | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | `NCBI_API_KEY` optional |
| `q-bio.*` | Europe PMC | `https://www.ebi.ac.uk/europepmc/webservices/rest` | none |
| `hep-*`, `nucl-*` | INSPIRE | `https://inspirehep.net/api` | none |

The registry preserves declared order, deduplicates names, and rejects unknown
explicit `--sources` values.

## DOI enrichment

| Source | API | Credential | Rule |
| --- | --- | --- | --- |
| OpenCitations COCI | `https://opencitations.net/index/coci/api/v1` | none | run only for already discovered DOIs; context-only |
| Unpaywall | `https://api.unpaywall.org/v2` | `UNPAYWALL_EMAIL` required when DOIs exist | lawful open-access location only |

Public homepage crawling runs only on homepage URLs emitted by credible public
sources. It may fetch one same-site lab/CV page and never recursively follows
arbitrary outbound links.

## Licensed and locator-only sources

Scopus (`SCOPUS_API_KEY`), Web of Science
(`WEB_OF_SCIENCE_API_KEY`), Dimensions (`DIMENSIONS_API_KEY`), Lens
(`LENS_API_TOKEN`), NASA ADS (`NASA_ADS_TOKEN`), IEEE Xplore
(`IEEE_XPLORE_API_KEY`), and Springer Nature
(`SPRINGER_NATURE_API_KEY`) are descriptor-only unless a source-specific
official adapter is registered and authorized. Otherwise they remain
locator-only.

Google Scholar, ResearchGate, Academia.edu, LinkedIn, and Maimai are always
locator-only. The CLI generates search URLs but never requests those pages.

## Status semantics

| Status | Meaning |
| --- | --- |
| `ok` | Source completed and returned usable public evidence. |
| `not_found` | Source completed successfully but returned no usable candidate. |
| `source_unavailable` | Credential, quota, transport, parser, or upstream failure prevented a result. |
| `blocked_by_robots` | The shared crawler refused the requested public page. |

An unavailable source never becomes `not_found`. Partial failures still
produce the complete HTML report.
