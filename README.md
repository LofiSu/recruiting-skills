# 招聘 Skills · Recruiting Skills

[![CI](https://github.com/LofiSu/recruiting-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/LofiSu/recruiting-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/LofiSu/recruiting-skills)](https://github.com/LofiSu/recruiting-skills/stargazers)

中文 | [English](#english)

给 Codex、Claude、Cursor 以及其他 Agent Skills 宿主用的研究者招聘技能包。两个 Skill 可以单独安装，也可以按稳定候选人 ID 协作。仓库自带索引引擎和合成 fixture，不附带真实候选人数据库。

| Skill | 适用场景 | 主要输出 |
| --- | --- | --- |
| `researcher-recruiting-skill` | 已知一篇 arXiv 论文，调查全部作者 | 作者、机构、主页、公开职业联系方式、GitHub/OpenReview、证据和 HTML 报告 |
| `research-talent-scout` | 按毕业年份、学位、会议和论文数量批量筛人 | 已确认候选人、待核验候选人、论文统计、毕业证据和覆盖范围 |

论文请求走第一个 Skill。形如"寻找 2027/2028 届、满足论文门槛的人"走第二个 Skill。筛选完成后，`research-talent-scout` 可以把入围候选人一次性交给 `researcher-recruiting-skill` 补全公开职业资料。

## 安装

```bash
git clone https://github.com/LofiSu/recruiting-skills.git
cd recruiting-skills
```

链接名必须与 `SKILL.md` 的 `name` 一致。把下面的 `dest` 换成你使用的宿主目录；只安装需要的宿主即可。Cursor 也会读取 Codex 与 Claude 的技能目录。

| 宿主 | 安装目录 |
| --- | --- |
| Codex | `${CODEX_HOME:-$HOME/.codex}/skills` |
| Claude Code | `$HOME/.claude/skills`，或项目内 `.claude/skills` |
| Cursor | `$HOME/.cursor/skills`、`$HOME/.agents/skills`，或项目内 `.cursor/skills`、`.agents/skills` |

```bash
dest="${CODEX_HOME:-$HOME/.codex}/skills"
# dest="$HOME/.claude/skills"
# dest="$HOME/.cursor/skills"
# dest="$HOME/.agents/skills"
# dest="/path/to/another-project/.cursor/skills"

mkdir -p "$dest"
ln -s "$PWD" "$dest/researcher-recruiting-skill"
ln -s "$PWD/research-talent-scout" "$dest/research-talent-scout"
```

注意事项：
- 克隆目录是 `recruiting-skills`；根 Skill 的安装名是 `researcher-recruiting-skill`，两者不同，这样已有触发方式不会断。
- 只做单篇论文作者调查时，创建第一个链接即可。
- 批量筛选和自动资料补全需要两个 Skill 都能被宿主发现。
- 安装后请开启新一轮 Agent 会话以刷新 Skill 列表。
- 不要把本仓库链接进它自己的 `.cursor/skills/`，那会把目录嵌套进自身。

## 演示

静态演示报告：[`examples/demo-report/index.html`](examples/demo-report/index.html)。用浏览器打开即可看版式（GitHub 网页会把它显示成源码）。按模板重新生成并检查一致性：

```bash
python3 scripts/render_demo_report.py
python3 scripts/render_demo_report.py --check
```

索引演示用合成记录，见[本地索引快速开始](docs/local-index-quickstart.md)。

## 数据与合规边界

- 只收集公开职业信息；
- 不根据姓名或机构规则猜测邮箱；
- 不登录、不绕过访问控制、不解 CAPTCHA、不批量抓取受限平台；
- 搜索摘要只能用于发现页面，不能单独作为已核验证据；
- 同名身份存在歧义时保持 `可能匹配` 或独立记录；
- 输出用于人工复核，不进行候选人排名、自动雇佣决策或自动外联。

## 更多文档

- [功能说明](docs/capabilities.md)
- [使用示例](docs/usage-examples.md)
- [协作契约与工作流](docs/collaboration-contract.md)
- [本地索引快速开始](docs/local-index-quickstart.md)
- [从 OpenAlex / Semantic Scholar 导入](docs/importing-openalex-semantic-scholar.md)
- [验证](docs/verification.md)
- [GitHub Pages 发布](docs/github-pages.md)
- [仓库约定](docs/repo-conventions.md)
- [仓库简介与 GitHub topics](REPO_META.md)
- [2026-10-29 发现信号对照](docs/trending-notes-2026-10-29.md)
- [贡献方式](CONTRIBUTING.md) · [行为准则](CODE_OF_CONDUCT.md) · [安全漏洞报告](SECURITY.md) · [MIT 许可证](LICENSE)

---

## English

Agent Skills for Codex, Claude, Cursor, and any other host that discovers `SKILL.md`: enrich every author of an arXiv paper with public professional evidence, or screen an indexed graduate cohort and enrich only the qualifiers. The two Skills install independently and collaborate through stable candidate IDs. The repository ships the index engine and synthetic fixtures; it does not ship a live candidate database.

| Skill | Use it for | Main output |
| --- | --- | --- |
| `researcher-recruiting-skill` | Investigating every author of a known arXiv paper | Authors, affiliations, public professional contacts, profiles, evidence, and an HTML report |
| `research-talent-scout` | Filtering a cohort by graduation year, degree, venue, and publication thresholds | Confirmed and pending candidates, categorized paper counts, graduation evidence, and index coverage |

Use the first Skill for a paper-centric request. Use the second for a cohort request such as "find 2027/2028 graduates above these publication thresholds." After filtering, the scout hands exactly one qualifying-candidate batch to the recruiting Skill for bounded public-profile enrichment.

## Installation

```bash
git clone https://github.com/LofiSu/recruiting-skills.git
cd recruiting-skills
```

The symlink name must match the `name` in each `SKILL.md`. Point `dest` at the host you use. Cursor also loads Codex and Claude skill directories.

| Host | Install directory |
| --- | --- |
| Codex | `${CODEX_HOME:-$HOME/.codex}/skills` |
| Claude Code | `$HOME/.claude/skills`, or `.claude/skills` inside a project |
| Cursor | `$HOME/.cursor/skills`, `$HOME/.agents/skills`, or `.cursor/skills` / `.agents/skills` inside a project |

```bash
dest="${CODEX_HOME:-$HOME/.codex}/skills"
# dest="$HOME/.claude/skills"
# dest="$HOME/.cursor/skills"
# dest="$HOME/.agents/skills"
# dest="/path/to/another-project/.cursor/skills"

mkdir -p "$dest"
ln -s "$PWD" "$dest/researcher-recruiting-skill"
ln -s "$PWD/research-talent-scout" "$dest/research-talent-scout"
```

Important notes:
- The clone directory is `recruiting-skills`; the root Skill install name is `researcher-recruiting-skill` — these differ intentionally so existing triggers keep working.
- Install only the first link for paper author investigation without cohort filtering.
- Both Skills must be discoverable for cohort filtering and automatic enrichment.
- Start a new agent session after installation so Skill discovery refreshes.
- Do not link this repository into its own `.cursor/skills/` directory.

## Demo

Static demo report: [`examples/demo-report/index.html`](examples/demo-report/index.html). Open it in a browser to see the layout (GitHub renders the file as source). Regenerate from the template and check consistency:

```bash
python3 scripts/render_demo_report.py
python3 scripts/render_demo_report.py --check
```

For the index demo with synthetic records, see [Local index quickstart](docs/local-index-quickstart.md).

## Data boundaries

- Public professional information only.
- No guessing email addresses from name or affiliation rules.
- No logging in, bypassing access controls, solving CAPTCHAs, or bulk-scraping restricted platforms.
- Search snippets are for discovery, not standalone verified evidence.
- Ambiguous same-name identities stay as possible-match or separate records.
- Outputs are research leads for human review — no candidate ranking, no automated employment decisions, no automated outreach.

## More documentation

- [Capabilities](docs/capabilities.md)
- [Usage examples](docs/usage-examples.md)
- [Collaboration contract and workflow](docs/collaboration-contract.md)
- [Local index quickstart](docs/local-index-quickstart.md)
- [Importing from OpenAlex / Semantic Scholar](docs/importing-openalex-semantic-scholar.md)
- [Verification](docs/verification.md)
- [GitHub Pages publishing](docs/github-pages.md)
- [Repository conventions](docs/repo-conventions.md)
- [Repository About and GitHub topics](REPO_META.md)
- [Trending-notes snapshot 2026-10-29](docs/trending-notes-2026-10-29.md)
- [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md) · [MIT License](LICENSE)
