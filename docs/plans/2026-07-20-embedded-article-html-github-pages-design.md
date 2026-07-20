# Embedded article-to-html and GitHub Pages design

Date: 2026-07-20

## Goal

Make `researcher-recruiting-skill` independently generate attractive, single-file
researcher reports and publish them at stable GitHub Pages URLs.

Users install only `researcher-recruiting-skill`. They do not install
`article-to-html`, Python, Node.js, browser drivers, fonts, or CDN assets.

## Decisions

### Embed the design system

Copy and adapt the complete reusable presentation layer from the installed
`article-to-html` skill into this repository:

- paper and ink color tokens
- serif reading typography and monospace metadata
- document header and metadata row
- TL;DR callout
- numbered sections
- cards, tables, callouts, evidence links, and footer
- responsive mobile rules

The resulting template remains one self-contained HTML file with inline CSS.
There are no runtime imports from `article-to-html`.

The interface is Chinese. Paper titles, author names, quotations, and original
evidence text remain unchanged.

### Report information architecture

Each report contains:

1. Paper header: title, arXiv identifier, publication metadata, and source link.
2. TL;DR: author count, verified public contact count, and a concise result summary.
3. Paper overview: abstract or short paper context and institutional signals.
4. Author directory: one readable entry per author with institution, public
   professional contact routes, profile links, and source-backed evidence.
5. Evidence and limitations: identity confidence, unresolved ambiguity, and the
   boundary between public professional information and restricted scraping.
6. References: authoritative source links used by the report.

The page has no search form, filter controls, expandable audit controls, or
decorative interaction. It opens as a finished report.

### Publication

The source branch remains clean:

- `main` stores the portable Skill and its embedded HTML template.
- generated reports are published to the dedicated `gh-pages` branch.
- each report is stored as `<arxiv-id>/index.html` on that branch.
- the stable URL is
  `https://lofisu.github.io/researcher-recruiting-skill/<arxiv-id>/`.

When the Agent has GitHub credentials and the user has selected automatic
publication, it generates the report and updates `gh-pages`. If publishing is
unavailable, it still returns the local `report.html` and clearly states that no
online URL was created.

Publishing changes external state, so implementations must not claim a URL until
the push and GitHub Pages response are verified.

## Portability

The Skill itself performs Agent-native web search and HTML composition. It does
not invoke a local generator program. Agents without web-search capability return
the arXiv author list and safe search links, using the same embedded report
presentation when they can write files.

## Verification

- Validate required Skill instructions and output contract with static checks.
- Verify the template contains the complete article document tokens and structural
  components.
- Render a representative multi-author report and inspect desktop and mobile
  screenshots.
- Confirm there are no external asset requests.
- Verify the `gh-pages` branch and live report URL before reporting deployment
  success.
