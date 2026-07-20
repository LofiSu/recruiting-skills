# researcher-recruiting-skill

中文 | [English](#english)

一个面向 Agent Skills 标准的论文作者招聘线索 Skill。给它一篇 arXiv
论文，它会快速找出完整作者名单、机构、公开职业联系方式、主页、GitHub /
OpenReview 资料和证据链接，并生成单文件 HTML 报告。

默认模式使用宿主 Agent 自带的网页搜索与浏览能力，不安装 Python、Node.js、
爬虫框架、字体、CDN 或外部服务。

## 能做什么

输入 arXiv URL、arXiv ID 或精确论文标题后，Skill 会返回：

- arXiv 官方顺序的完整作者列表；
- best-effort 的机构、个人主页、公开职业邮箱、GitHub、OpenReview；
- 每个非空字段对应的可点击证据链接；
- `已核验`、`可能匹配`、`暂未找到`、`未执行网页检索` 状态；
- 对话里的快速作者表；
- 单文件报告：`outputs/<arxiv-id>/report.html`；
- 如果 GitHub 写入权限已授权，自动发布到 GitHub Pages：
  `https://<owner>.github.io/<repository>/<arxiv-id>/`。

默认 enrichment 预算约 20 秒。它会优先返回可用结果，而不是等待所有来源完整审计。

## 安装

把仓库 clone 或 symlink 到支持 Agent Skills 的目录，然后开启新一轮 Agent 会话。

| 范围 | 路径 |
| --- | --- |
| 通用 Agent | `~/.agents/skills/researcher-recruiting-skill/` |
| Claude Code 个人 | `~/.claude/skills/researcher-recruiting-skill/` |
| Claude Code 项目 | `.claude/skills/researcher-recruiting-skill/` |
| OpenCode 个人 | `~/.config/opencode/skills/researcher-recruiting-skill/` |
| OpenCode 项目 | `.opencode/skills/researcher-recruiting-skill/` |
| Codex 个人 | `${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill/` |

Codex 当前 checkout 可以直接这样接入：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill"
```

只需要安装这个 Skill。`article-to-html` 风格的 HTML/CSS 已经内嵌在本仓库里，
不需要再单独安装 `article-to-html`。

## 使用

可以直接把论文链接发给 Agent：

```text
https://arxiv.org/abs/2606.19980
帮我找这篇论文所有作者的机构、主页、公开职业邮箱和证据链接。
```

如果宿主 Agent 支持 Skill 显式调用，也可以写：

```text
Use $researcher-recruiting-skill on
https://arxiv.org/abs/2606.19980 and find every author's institution,
homepage, public professional email, and evidence.
```

Skill 会打开 arXiv，按作者并行搜索，返回聊天表格，并写入：

```text
outputs/<arxiv-id>/report.html
```

HTML 是静态单文件，包含中文界面、论文概览、作者表、证据链接和使用边界。

## GitHub Pages 发布

生成报告不会提交到 `main`。当仓库有可写 GitHub remote 时，Skill 会把报告复制到：

```text
gh-pages:<arxiv-id>/index.html
```

稳定访问地址：

```text
https://<owner>.github.io/<repository>/<arxiv-id>/
```

GitHub Pages 需要一次性设置为从 `gh-pages` 分支根目录部署。首次部署可能慢于
20 秒搜索结果；如果 GitHub 写入或 Pages 设置不可用，Skill 只返回本地
`report.html`，不会虚构线上链接。

## 没有网页搜索能力时

如果宿主 Agent 不能搜索网页，Skill 仍会在可访问 arXiv 的前提下保留官方作者名单，
生成 Google Scholar、LinkedIn、脉脉定位链接，并把作者状态标记为
`未执行网页检索`。

它不会要求用户安装本地爬虫，也不会静默切换到 Python/Node 采集。

## 数据边界

只收集公开职业信息。邮箱不会根据姓名或机构规则猜测。

Google Scholar、LinkedIn、脉脉、ResearchGate、Academia.edu 等平台可以通过普通公开搜索结果定位；
如果页面无需登录即可访问，并且能支持身份匹配，可以作为证据。Skill 不登录、不绕过访问控制、
不解 CAPTCHA、不批量抓取这些平台。搜索片段只能作为发现线索，不能单独作为已核验证据。

输出是人工复核用的研究线索，不是候选人排名、雇佣决策或自动外联系统。

---

## English

An Agent Skills-standard workflow for finding researcher recruiting leads from
an arXiv paper. Given an arXiv paper, it quickly returns the full ordered author
list, institutions, public professional contact routes, homepages, GitHub /
OpenReview profiles, and evidence links, then generates a single-file HTML
report.

The default mode uses the host Agent's native web search and browsing tools. It
does not require Python, Node.js, crawler frameworks, API keys, fonts, CDNs, or
hosted services.

## What it returns

For an arXiv URL, arXiv identifier, or exact paper title, the Skill returns:

- the complete author list in official arXiv order;
- best-effort institutions, professional homepages, public work email, GitHub,
  and OpenReview profiles;
- a clickable evidence link for every non-empty professional field;
- explicit `已核验`, `可能匹配`, `暂未找到`, or `未执行网页检索` states;
- an immediate chat summary table;
- one static report at `outputs/<arxiv-id>/report.html`;
- when GitHub writes are authorized, an automatically published report at
  `https://<owner>.github.io/<repository>/<arxiv-id>/`.

The native enrichment phase targets approximately 20 seconds. It returns partial
results at the time budget instead of waiting for exhaustive source auditing.

## Installation

Clone or symlink this repository into a supported Agent Skills discovery
directory, then start a fresh Agent turn so Skill discovery refreshes.

| Scope | Location |
| --- | --- |
| Generic shared | `~/.agents/skills/researcher-recruiting-skill/` |
| Claude Code personal | `~/.claude/skills/researcher-recruiting-skill/` |
| Claude Code project | `.claude/skills/researcher-recruiting-skill/` |
| OpenCode personal | `~/.config/opencode/skills/researcher-recruiting-skill/` |
| OpenCode project | `.opencode/skills/researcher-recruiting-skill/` |
| Codex personal | `${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill/` |

To connect the current checkout to Codex without copying files:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill"
```

Install only this Skill. The `article-to-html`-style HTML/CSS presentation layer
is embedded in this repository, so `article-to-html` is not a separate runtime
dependency.

## Usage

Send the paper directly:

```text
https://arxiv.org/abs/2606.19980
Find every author's institution, homepage, public professional email, and
evidence links.
```

If the host Agent supports explicit Skill invocation:

```text
Use $researcher-recruiting-skill on
https://arxiv.org/abs/2606.19980 and find every author's institution,
homepage, public professional email, and evidence.
```

The Skill opens arXiv, batches author searches with the Agent's own web tools,
returns the chat table, and creates:

```text
outputs/<arxiv-id>/report.html
```

The report is a static single-file HTML page with a Chinese interface, paper
overview, author table, evidence links, and data-boundary notes.

## GitHub Pages

Generated reports stay out of `main`. When the repository has an authorized
GitHub remote, the Skill copies the finished report to:

```text
gh-pages:<arxiv-id>/index.html
```

Stable URL:

```text
https://<owner>.github.io/<repository>/<arxiv-id>/
```

GitHub Pages must be configured once to deploy from the root of the `gh-pages`
branch. First-time deployment can take longer than the 20-second search result.
If GitHub writes or Pages settings are unavailable, the Skill returns the local
`report.html` and does not invent an online URL.

## Host without web search

When an Agent cannot search the web, the Skill still preserves the official
arXiv author list when page access exists, generates Google Scholar, LinkedIn,
and Maimai locator URLs, marks rows `未执行网页检索`, and creates the chat and
HTML outputs.

It does not ask users to install a local crawler and does not silently switch to
Python or Node.js collection.

## Data boundaries

Only public professional information is collected. Email addresses are never
guessed from names or institutional conventions.

Google Scholar, LinkedIn, Maimai, ResearchGate, and Academia.edu may be opened
through ordinary public search results. If a page is accessible without login
and supports identity matching, it may be used as evidence. The Skill does not
log in, bypass access controls, solve CAPTCHAs, or run batch scrapers against
those platforms. Search snippets are discovery aids, not verified evidence by
themselves.

The output is a research lead for human review, not a candidate ranking,
employment decision, or automated outreach system.
