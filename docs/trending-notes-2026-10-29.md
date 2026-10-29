# Agent Skills 仓库为什么容易被找到（2026-10-29）

这份笔记记录 2026-10-29 当天，招聘向 Agent Skills 仓库在 GitHub 上被发现时，审阅者实际会点开的几样东西，以及 `LofiSu/recruiting-skills` 分别落到了哪一个文件。它不是流量预测，也不改 `SKILL.md` 的触发契约。

公开仓库 API 当天返回：About 描述仍是 `researcher-recruiting-skill`，`topics` 为 `[]`，许可证为 `MIT`，默认分支为 `main`。Topics 和 About 描述写进 git 不会生效，必须在 GitHub → About 里手工套用 [`REPO_META.md`](../REPO_META.md)。

## 被点开的六件事

1. **可安装的 `SKILL.md`。** Codex、Claude、Cursor 只把「目录里有 `SKILL.md`，且链接名等于 frontmatter `name`」的包放进技能列表。README 里的一段说明不够。本仓库把安装写成两条 symlink：仓库根目录 → `researcher-recruiting-skill`，`research-talent-scout/` → `research-talent-scout`。宿主目录见 README 的安装表。根技能的 `name` 故意不等于克隆目录名，这样已有的 `$researcher-recruiting-skill` 触发不会断。
2. **不用密钥就能打开的演示。** [`examples/demo-report/index.html`](../examples/demo-report/index.html) 用现有报告模板填入公开论文 arXiv:1706.03762 的官方作者顺序和论文 HTML 上的机构。联系路径全部是「暂未找到」，没有邮箱，也没有 `mailto`。批量筛选的演示数据是合成记录 [`research-talent-scout/tests/fixtures/records.jsonl`](../research-talent-scout/tests/fixtures/records.jsonl)。审阅者不用 `OPENALEX_API_KEY` 就能看版式、跑查询。
3. **双语 README。** [`README.md`](../README.md) 先写中文，再用 `## English` 写同一套安装、协作边界和合规说明。GitHub 代码搜索会索引两边。只维护一种语言时，另一种搜索词（「招聘 skill」「talent scout arXiv」）会落到过期段落。
4. **GitHub topics。** Topic 页和 Agent Skills / recruiting 这一类列表按 About topics 过滤。文件里的清单不会出现在那些页面上。应当套用的发现用 topics 写在 [`REPO_META.md`](../REPO_META.md)，下面单独列出。
5. **MIT。** [`LICENSE`](../LICENSE) 是 MIT，GitHub 已识别为 `MIT`。宿主用户要把技能目录链接进 `~/.codex/skills`、`~/.claude/skills` 或 `~/.cursor/skills`，专有许可证会在这一步被拒。
6. **对 PR 运行的 CI。** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) 在指向 `main` 的 pull request 上执行 `bash tests/verify-all.sh`（Python 3.12，`contents: read`）。同一条命令覆盖两个 Skill 的 frontmatter、演示报告、Pages 首页生成器，以及 scout 的索引、导入、查询和离线连接器 fixture。徽章在 README 顶部。

## 本仓库对照

| 发现信号 | 本仓库里的位置 | 2026-10-29 状态 |
| --- | --- | --- |
| 可安装技能 | 根 [`SKILL.md`](../SKILL.md)（`name: researcher-recruiting-skill`）；[`research-talent-scout/SKILL.md`](../research-talent-scout/SKILL.md)（`name: research-talent-scout`） | 已在仓库中。安装命令在 README。 |
| 宿主展示名 | [`agents/openai.yaml`](../agents/openai.yaml)，[`research-talent-scout/agents/openai.yaml`](../research-talent-scout/agents/openai.yaml) | 已在仓库中。展示名不能代替 `SKILL.md` 的 `name`。 |
| 静态演示 | [`examples/demo-report/`](../examples/demo-report/) | 已提交在 `main`。CI 不把它发布到 `gh-pages`。 |
| 合成索引 | `research-talent-scout/tests/fixtures/records.jsonl` | 已在仓库中。`data/*.sqlite` 被 gitignore。 |
| 双语说明 | `README.md`、`CONTRIBUTING.md` | 已在仓库中。 |
| Topics | [`REPO_META.md`](../REPO_META.md) | **尚未套用。** 公开 API 的 `topics` 为 `[]`。 |
| About 描述 | 同文件里的建议描述 | **尚未套用。** 当前描述是 `researcher-recruiting-skill`。建议改为：`Agent Skills for researcher recruiting: arXiv author enrichment + cohort talent scout with evidence-backed reports.` |
| 许可证 | `LICENSE` | MIT，GitHub 已识别。 |
| CI | `.github/workflows/ci.yml` | 已在 `main` 的 push 和 PR 上运行 `tests/verify-all.sh`。 |
| 合规边界 | [`references/compliance.md`](../references/compliance.md) | 已在仓库中。只处理公开职业信息。 |

## 应在 GitHub About 套用的 topics

完整清单和说明在 [`REPO_META.md`](../REPO_META.md#suggested-topics)。发现用的六个 topic 是：

- [`agent-skills`](https://github.com/topics/agent-skills)
- [`recruiting`](https://github.com/topics/recruiting)
- [`arxiv`](https://github.com/topics/arxiv)
- [`talent-scout`](https://github.com/topics/talent-scout)
- [`research`](https://github.com/topics/research)
- [`python`](https://github.com/topics/python)

`REPO_META.md` 还建议 `codex` 和 `claude`，因为这两个是安装宿主。上面六个对应招聘技能这条发现路径：技能格式、用途、论文来源、队列筛选、研究领域、实现语言。套用时六个和宿主 topic 一起贴进 About，不要只提交这个文件。

## 不靠改契约去追词

`SKILL.md` 的 `name` 和 `description` 是宿主发现契约。`CONTRIBUTING.md` 已写明：除非是明确缺陷，不要为了通过检查或凑关键词改写触发条件。本仓库要补的是 About topics 和描述，不是把「trending」写进技能正文。

也不要为了看起来「有数据」而提交真实候选人库。仓库约定是索引引擎加合成 fixture；连接器只在本地把公开元数据写成 JSONL，毕业年份不会被标成 `confirmed`。

## 访客可以自己核对

```bash
git clone https://github.com/LofiSu/recruiting-skills.git
cd recruiting-skills
bash tests/verify-all.sh
python3 scripts/render_demo_report.py --check
```

演示报告用浏览器打开 `examples/demo-report/index.html`。GitHub 网页会把它显示成源码。

---

# Why Agent Skills repositories get found (2026-10-29)

Snapshot of the surfaces a reviewer actually opens when an Agent Skills repo is filed under a recruiting track, and where `LofiSu/recruiting-skills` stands on each one. This is not a traffic forecast. It does not change the `SKILL.md` trigger contract.

On this date the public repository API returned About description `researcher-recruiting-skill`, `topics: []`, license `MIT`, default branch `main`. Committing a topic list does not publish it. Apply [`REPO_META.md`](../REPO_META.md) in GitHub → About.

## The six things people open

1. **An installable `SKILL.md`.** Codex, Claude, and Cursor load a skill only when a directory contains `SKILL.md` and the symlink name equals the frontmatter `name`. This repo documents two links: the clone root as `researcher-recruiting-skill`, and `research-talent-scout/` as `research-talent-scout`. The root install name intentionally differs from the clone directory so existing `$researcher-recruiting-skill` triggers keep working.
2. **A demo that needs no API key.** [`examples/demo-report/index.html`](../examples/demo-report/index.html) fills the report template with the public author order of arXiv:1706.03762 and the affiliations printed on the paper HTML. Every contact path is “暂未找到”. There is no email address and no `mailto` link. Cohort queries use the synthetic file [`research-talent-scout/tests/fixtures/records.jsonl`](../research-talent-scout/tests/fixtures/records.jsonl).
3. **A bilingual README.** [`README.md`](../README.md) leads with Chinese and repeats the install, collaboration boundary, and compliance rules under `## English`. GitHub code search indexes both. Letting one language go stale hides the repo from the other query.
4. **GitHub topics.** Topic pages filter on About topics. A list inside the repo is invisible until someone applies it. The discovery topics live in [`REPO_META.md`](../REPO_META.md) and are repeated below.
5. **MIT.** [`LICENSE`](../LICENSE) is MIT and GitHub already reports `MIT`. People symlink the skill into `~/.codex/skills`, `~/.claude/skills`, or `~/.cursor/skills`; a proprietary license stops that.
6. **CI on pull requests.** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs `bash tests/verify-all.sh` on pull requests to `main` (Python 3.12, `contents: read`). That command checks both skills' frontmatter, the demo report, the Pages index generator, and the scout index, import, query, and offline connector fixtures. The badge is at the top of the README.

## How this repository maps

| Signal | Where it lives | Status on 2026-10-29 |
| --- | --- | --- |
| Installable skills | Root [`SKILL.md`](../SKILL.md) (`name: researcher-recruiting-skill`); [`research-talent-scout/SKILL.md`](../research-talent-scout/SKILL.md) (`name: research-talent-scout`) | In the repo. Install commands are in the README. |
| Host display names | [`agents/openai.yaml`](../agents/openai.yaml), [`research-talent-scout/agents/openai.yaml`](../research-talent-scout/agents/openai.yaml) | In the repo. Display names do not replace `SKILL.md` `name`. |
| Static demo | [`examples/demo-report/`](../examples/demo-report/) | Committed on `main`. CI does not publish it to `gh-pages`. |
| Synthetic index | `research-talent-scout/tests/fixtures/records.jsonl` | In the repo. `data/*.sqlite` is gitignored. |
| Bilingual docs | `README.md`, `CONTRIBUTING.md` | In the repo. |
| Topics | [`REPO_META.md`](../REPO_META.md) | **Not applied.** Public API `topics` is `[]`. |
| About description | Suggested text in the same file | **Not applied.** Current description is `researcher-recruiting-skill`. Suggested text: `Agent Skills for researcher recruiting: arXiv author enrichment + cohort talent scout with evidence-backed reports.` |
| License | `LICENSE` | MIT, already recognized by GitHub. |
| CI | `.github/workflows/ci.yml` | Runs `tests/verify-all.sh` on pushes and pull requests to `main`. |
| Compliance boundary | [`references/compliance.md`](../references/compliance.md) | In the repo. Public professional information only. |

## Topics to apply in GitHub About

The full list is [`REPO_META.md`](../REPO_META.md#suggested-topics). The six discovery topics for this track are:

- [`agent-skills`](https://github.com/topics/agent-skills)
- [`recruiting`](https://github.com/topics/recruiting)
- [`arxiv`](https://github.com/topics/arxiv)
- [`talent-scout`](https://github.com/topics/talent-scout)
- [`research`](https://github.com/topics/research)
- [`python`](https://github.com/topics/python)

`REPO_META.md` also suggests `codex` and `claude` because those are install hosts. The six above are the recruiting-track set: skill format, job to be done, paper source, cohort filter, field, and implementation language. Apply the six together with the host topics. Committing this note does not set them.

## Do not chase the word by editing the contract

`name` and `description` in `SKILL.md` are the host discovery contract. `CONTRIBUTING.md` already says not to rewrite trigger text unless it is a real defect. The missing piece is the About description and topics, not a keyword stuffed into the skill body.

Do not commit a real candidate database to look more complete. The repository ships an index engine and synthetic fixtures. Connectors write public metadata to local JSONL and do not mark graduation years `confirmed`.

## What a visitor can check

```bash
git clone https://github.com/LofiSu/recruiting-skills.git
cd recruiting-skills
bash tests/verify-all.sh
python3 scripts/render_demo_report.py --check
```

Open `examples/demo-report/index.html` in a browser. GitHub's file view shows the HTML source.
