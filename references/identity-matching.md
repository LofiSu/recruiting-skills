# Identity matching rules

The resolver is deterministic and evidence-first. A matching name contributes
only five points and can never produce a probable or confirmed identity by
itself.

## Evidence weights

| Signal | Weight | Strong |
| --- | ---: | :---: |
| ORCID present on the candidate | 60 | yes |
| Institutional profile cross-link | 50 | yes |
| Exact public email | 45 | yes |
| Paper or DOI overlap | 25 | no |
| Affiliation overlap | 20 | no |
| Coauthor overlap | 15 | no |
| Public email-domain overlap | 15 | no |
| Research-topic overlap | 10 | no |
| Name or declared name variant | 5 | no |

Scores are capped at 100. `confirmed` requires at least 80 points plus either
one strong signal or three independent non-name signal categories. `probable`
requires at least 50 points and at least one non-name signal.

DOIs, ORCIDs, PMIDs, OpenAlex identifiers, and DBLP person keys are
canonicalized before use. The same DOI copied through OpenAlex, Crossref, and
Semantic Scholar therefore counts once.

## Conflicts and unavailable sources

- Two distinct ORCIDs in the candidate set force `ambiguous`.
- Equally scored plausible candidates force `ambiguous`.
- An empty result is `not_found` only if every attempted source completed.
- If any identity source was unavailable, an empty result remains
  `ambiguous` and the unavailable sources are named in the reasons.
- ROR organization matches, Wikidata support facts, OpenCitations records,
  locator links, and name equality cannot independently confirm a person.

Chinese names and Western comma order are compared through normalized tokens.
Transliteration is accepted only when arXiv or another trusted input supplies
the spelling as an explicit `name_variants` value; the resolver does not invent
transliterations.
