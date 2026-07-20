# researcher-recruiting-skill

An Agent Skills-standard workflow for quickly finding every author of an arXiv
paper, their institution, public professional contact routes, and supporting
evidence.

The Skill uses the host Agent's native web search and browsing tools. It has no
local runtime, package installation, API-key, cache, or hosted-service
requirement.

The full `article-to-html` paper-style design is embedded in this repository.
Users install only this Skill; `article-to-html`, Python, Node.js, external
fonts, and CDN assets are not required.

## What it returns

For an arXiv URL, identifier, or exact paper title:

- the complete author list in official paper order;
- best-effort institutions, professional homepages, public work email,
  GitHub, and OpenReview profiles;
- a clickable evidence link for every non-empty professional field;
- explicit `已核验`, `可能匹配`, `暂未找到`, or `未执行网页检索` states;
- an immediate chat summary;
- one static report at `outputs/<arxiv-id>/report.html`;
- when GitHub writes are already authorized, an automatically published report
  at `https://<owner>.github.io/<repository>/<arxiv-id>/`.

The native enrichment phase targets approximately 20 seconds. It returns
partial results at the time budget instead of waiting for an exhaustive source
matrix.

## Install as an Agent Skill

Clone or symlink this repository into a supported Agent Skills discovery
directory, then refresh that Agent's Skill discovery.

| Scope | Location |
| --- | --- |
| Generic shared | `~/.agents/skills/researcher-recruiting-skill/` |
| Claude Code personal | `~/.claude/skills/researcher-recruiting-skill/` |
| Claude Code project | `.claude/skills/researcher-recruiting-skill/` |
| OpenCode personal | `~/.config/opencode/skills/researcher-recruiting-skill/` |
| OpenCode project | `.opencode/skills/researcher-recruiting-skill/` |
| Codex personal | `${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill/` |

There is nothing else to install. In particular, do not separately install
`article-to-html`; its reusable HTML and CSS presentation layer is part of this
Skill.

To connect the current checkout to Codex without copying files:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill"
```

Start a new Codex turn after linking so Skill discovery refreshes.

## Use

Send the paper directly:

```text
Use $researcher-recruiting-skill on
https://arxiv.org/abs/2606.19980 and find every author's institution,
homepage, public professional email, and evidence.
```

The Skill opens arXiv, batches author searches using the Agent's own web tools,
returns the chat table, and creates the single-file article-style HTML report.

## GitHub Pages

Generated reports stay out of `main`. When the repository has an authorized
GitHub remote, the Skill automatically copies the finished report to:

```text
gh-pages:<arxiv-id>/index.html
```

That produces a stable URL:

```text
https://<owner>.github.io/<repository>/<arxiv-id>/
```

GitHub Pages must be configured once to deploy the root of the `gh-pages`
branch. The Skill attempts this setup when the host exposes repository Pages
settings. GitHub deployment is asynchronous, so the search result can appear in
roughly 20 seconds while first-time Pages propagation takes longer.

If GitHub writes or Pages configuration are unavailable, the Skill still
returns the local `report.html`. It never invents an online URL.

## Host without web search

When an Agent cannot search the web, the Skill still preserves the official
arXiv author list when page access exists, generates Google Scholar, LinkedIn,
and Maimai locator URLs, marks rows `未执行网页检索`, and creates the chat and
HTML outputs.

It does not substitute a local crawler.

## Data boundaries

Only public professional information is collected. Email addresses are never
guessed. Google Scholar, LinkedIn, Maimai, ResearchGate, and Academia.edu may be
opened through ordinary public search results when the host Agent can access
them, but the Skill does not log in, bypass access controls, solve CAPTCHAs, or
run batch scrapers against those platforms. Search snippets are discovery aids,
not verified evidence by themselves.

The output is a research lead for human review, not a candidate ranking,
employment decision, or outreach action.
