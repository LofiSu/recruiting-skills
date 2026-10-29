# 招聘 Skills · Recruiting Skills

[![CI](https://github.com/LofiSu/recruiting-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/LofiSu/recruiting-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/LofiSu/recruiting-skills)](https://github.com/LofiSu/recruiting-skills/stargazers)

中文 | [English](#english)

给 Codex、Claude、Cursor 以及其他 Agent Skills 宿主用的研究者招聘技能包：从一篇 arXiv 论文补全全部作者的公开职业资料，或在本地索引里按毕业年份和论文门槛筛选人才队列，再只给入围者补证据。

这是招聘相关 Agent Skills 的长期集合。两个 Skill 可以单独安装，也可以按稳定候选人 ID 协作。仓库自带索引引擎和合成 fixture，不附带真实候选人数据库。

| Skill | 适用场景 | 主要输出 |
| --- | --- | --- |
| `researcher-recruiting-skill` | 已知一篇 arXiv 论文，调查全部作者 | 作者、机构、主页、公开职业联系方式、GitHub/OpenReview、证据和 HTML 报告 |
| `research-talent-scout` | 按毕业年份、学位、会议和论文数量批量筛人 | 已确认候选人、待核验候选人、论文统计、毕业证据和覆盖范围 |

论文请求走第一个 Skill。形如“寻找 2027/2028 届、满足论文门槛的人”走第二个 Skill。筛选完成后，`research-talent-scout` 可以把入围候选人一次性交给 `researcher-recruiting-skill` 补全公开职业资料。

## 两个 Skill 如何协作

```text
单篇论文
  └─ researcher-recruiting-skill
       ├─ 获取 arXiv 官方作者顺序
       ├─ 并行核验公开职业资料
       └─ 生成单文件 HTML 报告

批量人才条件
  └─ research-talent-scout
       ├─ 查询本地 SQLite 索引
       ├─ 按会议、一作类别、学位和毕业年份筛选
       ├─ 仅将入围候选人交给 researcher-recruiting-skill
       └─ 合并为一份证据化结果
```

`research-talent-scout` 负责索引内发现、确定性筛选、毕业与论文核验，以及最终合并结果。`researcher-recruiting-skill` 只对收到的稳定候选人 ID 做有界的公开资料补全。

交接使用唯一 `batch_id`、稳定 `candidate_id` 和明确的 `deadline_at`。资料补全不会扩展到论文的其他合作者，也不能改写原有论文统计、毕业年份状态或更强的既有证据。

## 仓库约定

- 克隆目录是 `recruiting-skills`。根目录 Skill 的安装名仍是 `researcher-recruiting-skill`，以兼容现有触发方式。
- 其他招聘 Skill 使用独立的 `<skill-name>/SKILL.md` 子目录。
- 每个 Skill 可以独立安装、触发和验证。
- 跨 Skill 协作必须定义稳定输入、输出、责任边界和失败降级。
- 通用合规原则保持一致：只处理公开职业信息，不执行招聘排名、自动雇佣决策或自动外联。

新增 Skill 后，需要在顶部目录表、安装说明和统一验证脚本中登记。发现用的仓库简介和 GitHub topics 写在 [`REPO_META.md`](REPO_META.md)；这些设置不能靠 git 文件自动生效。

## 功能

### 单篇论文作者调查

- 接受 arXiv URL、arXiv ID 或精确论文标题；
- 保留 arXiv 官方顺序的完整作者列表；
- best-effort 查找机构、个人主页、公开职业邮箱、GitHub 和 OpenReview；
- 每个非空字段都附可点击的公开证据；
- 使用 `已核验`、`可能匹配`、`暂未找到`、`未执行网页检索` 状态；
- 默认资料补全预算约 20 秒；
- 生成 `outputs/<arxiv-id>/report.html`，该目录已加入 `.gitignore`；
- 授权后可发布至 GitHub Pages 的 `gh-pages:<arxiv-id>/index.html`。

### 批量人才筛选

- 按博士/硕士、毕业年份、院校、实验室、会议和作者类别筛选；
- 支持 `main_first`、`co_first`、`findings`、`workshop`、`short`、`demo` 分类计数；
- 正确区分“多于 5 篇”和“至少 5 篇”；
- 将毕业年份分为 `confirmed`、`likely_needs_verification`、`unknown`、`stale` 和 `conflict`；
- 不会仅凭姓名合并同名研究者；
- 返回全部索引内匹配者，并显示索引覆盖和新鲜度限制；
- 使用 SQLite 进行快速查询。真实候选人数据需要通过规范化 JSONL 导入或后续数据连接器建立。

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

只做单篇论文作者调查时，创建第一个链接即可。批量筛选和自动资料补全需要两个 Skill 都能被宿主发现。安装后请开启新一轮 Agent 会话以刷新 Skill 列表。不要把本仓库链接进它自己的 `.cursor/skills/`，那会把目录嵌套进自身。

## 使用示例

### 调查一篇论文的全部作者

```text
https://arxiv.org/abs/2606.19980
帮我找这篇论文所有作者的机构、主页、公开职业邮箱和证据链接。
```

显式调用：

```text
Use $researcher-recruiting-skill on https://arxiv.org/abs/2606.19980.
Find every author's institution, homepage, public professional email,
GitHub/OpenReview profile, and evidence.
```

### 批量筛选研究人才

```text
Use $research-talent-scout to find indexed 2027 and 2028 graduates.
For PhD candidates require more than 5 qualifying papers; for master's
candidates require more than 3. Count ACL, ICML, ICLR, NeurIPS, EMNLP,
CVPR, AAAI, ICCV, MLSys, OSDI, EuroSys, ASPLOS, ISCA, SC, and PPoPP.
Separate confirmed graduation years from candidates needing verification,
then enrich only the qualifying candidates with public professional evidence.
```

“全部候选人”表示当前索引覆盖范围内的全部匹配者，不代表从实时互联网穷举全球所有研究者。

## 本地索引快速开始

演示数据是合成记录 [`research-talent-scout/tests/fixtures/records.jsonl`](research-talent-scout/tests/fixtures/records.jsonl)（Alice Example、Bob Example 等），只用于演示和测试。

```bash
cd research-talent-scout

python3 scripts/init_index.py --db data/candidates.sqlite
python3 scripts/import_records.py \
  --db data/candidates.sqlite \
  --input tests/fixtures/records.jsonl

python3 scripts/query_candidates.py \
  --db data/candidates.sqlite \
  --graduation-years 2027,2028 \
  --degree-threshold phd=5,masters=3 \
  --strictly-greater \
  --venues ACL,ICML,ICLR,NeurIPS,EMNLP,CVPR,AAAI,ICCV,MLSys,OSDI,EuroSys,ASPLOS,ISCA,SC,PPoPP \
  --categories main_first,co_first,findings,workshop,short,demo \
  --graduation-states confirmed,likely_needs_verification
```

`data/*.sqlite` 已被忽略，不会进入版本库。

## 验证

从仓库根目录运行：

```bash
bash tests/verify-all.sh
```

它会验证论文作者 Skill 的静态契约、两个 Skill 的 frontmatter、Pages 首页生成器，以及 `research-talent-scout` 的索引、导入、查询、证据状态和报告测试。GitHub Actions 在推送到 `main` 和指向 `main` 的 pull request 上运行同一命令。frontmatter 检查使用仓库内的标准库脚本，不依赖某台机器上的 skill-creator 路径。

## GitHub Pages

单篇论文模式生成的报告不会写入 `main`。授权后，报告会发布至：

```text
branch: gh-pages
file:   <arxiv-id>/index.html
URL:    https://<owner>.github.io/<repository>/<arxiv-id>/
home:   https://<owner>.github.io/<repository>/
```

本仓库对应 `https://lofisu.github.io/recruiting-skills/`。首页由 [`scripts/build_pages_index.py`](scripts/build_pages_index.py) 和 [`assets/pages-index-template.html`](assets/pages-index-template.html) 生成。如果 GitHub 写入、Pages 设置或部署验证不可用，Skill 只返回本地报告，不会虚构线上地址。

## 数据与合规边界

- 只收集公开职业信息；
- 不根据姓名或机构规则猜测邮箱；
- 不登录、不绕过访问控制、不解 CAPTCHA、不批量抓取受限平台；
- 搜索摘要只能用于发现页面，不能单独作为已核验证据；
- 同名身份存在歧义时保持 `可能匹配` 或独立记录；
- 输出用于人工复核，不进行候选人排名、自动雇佣决策或自动外联。

贡献方式见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。许可证为 [MIT](LICENSE)。

---

## English

Agent Skills for Codex, Claude, Cursor, and any other host that discovers `SKILL.md`: enrich every author of an arXiv paper with public professional evidence, or screen an indexed graduate cohort and enrich only the qualifiers.

This is the long-term home for recruiting skills. The two skills install independently and collaborate through stable candidate IDs. The repository ships the index engine and synthetic fixtures. It does not ship a live candidate database.

| Skill | Use it for | Main output |
| --- | --- | --- |
| `researcher-recruiting-skill` | Investigating every author of a known arXiv paper | Authors, affiliations, public professional contacts, profiles, evidence, and an HTML report |
| `research-talent-scout` | Filtering a cohort by graduation year, degree, venue, and publication thresholds | Confirmed and pending candidates, categorized paper counts, graduation evidence, and index coverage |

Use the first Skill for a paper-centric request. Use the second for a cohort request such as “find 2027/2028 graduates above these publication thresholds.” After filtering, the scout hands exactly one qualifying-candidate batch to the recruiting Skill for bounded public-profile enrichment.

## How they collaborate

`research-talent-scout` owns indexed discovery, deterministic filtering, graduation and publication verification, and the single final result. `researcher-recruiting-skill` owns only bounded public-profile enrichment for the stable candidate IDs it receives.

The handoff uses a unique `batch_id`, stable `candidate_id` values, and an absolute `deadline_at`. Enrichment never expands to coauthors, re-filters the cohort, or overwrites stronger graduation or publication evidence.

## Repository convention

- Clone the repository as `recruiting-skills`. The root Skill install name remains `researcher-recruiting-skill` so existing triggers keep working.
- Additional recruiting Skills live in independent `<skill-name>/SKILL.md` directories.
- Every Skill must remain independently installable, triggerable, and verifiable.
- Cross-Skill workflows must define stable inputs, outputs, ownership, and failure behavior.
- Shared compliance rules permit only public professional information and prohibit candidate ranking, automated employment decisions, and automated outreach.

Register every new Skill in the catalog table, installation instructions, and `tests/verify-all.sh`. Suggested GitHub topics and the About description live in [`REPO_META.md`](REPO_META.md); GitHub does not apply those settings from a file.

## Features

### Paper author investigation

- accepts an arXiv URL, identifier, or exact paper title;
- preserves the complete official author order;
- finds best-effort affiliations, homepages, public work email, GitHub, and OpenReview profiles;
- requires a clickable public source for every non-empty field;
- uses explicit verified, possible-match, not-found, and no-search states;
- targets approximately 20 seconds for native web enrichment;
- writes `outputs/<arxiv-id>/report.html` (gitignored) and can publish it to GitHub Pages when authorized.

### Cohort talent scouting

- filters by degree, graduation year, institution, lab, venue, and authorship category;
- counts main first, evidenced co-first, Findings, workshop, short, and demo papers separately;
- distinguishes “more than N” from “at least N”;
- preserves confirmed, inferred, unknown, stale, and conflicting graduation evidence;
- keeps ambiguous same-name researchers separate;
- returns all matches inside declared index coverage and reports freshness limitations;
- uses a lightweight SQLite index for fast repeated queries.

Normalized real-world records or data-source connectors populate the index. Until then, queries run against whatever SQLite file you import.

## Installation

```bash
git clone https://github.com/LofiSu/recruiting-skills.git
cd recruiting-skills
```

The symlink name must match the `name` in each `SKILL.md`. Point `dest` at the host you use. Cursor also loads Codex and Claude skill directories, so a Codex or Claude install is visible in Cursor as well.

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

Install only the first link for paper author investigation without cohort filtering. Restart the Agent session after installation so Skill discovery refreshes. Do not link this repository into its own `.cursor/skills/` directory.

## Usage

Paper mode:

```text
Use $researcher-recruiting-skill on https://arxiv.org/abs/2606.19980.
Find every author's institution, homepage, public professional email,
GitHub/OpenReview profile, and evidence.
```

Cohort mode:

```text
Use $research-talent-scout to find indexed 2027/2028 PhD and master's
candidates above configurable first-author venue thresholds. Keep confirmed
and pending graduation evidence separate, then enrich only the qualifiers with
public professional evidence.
```

“All candidates” means all matches within declared index coverage, not an exhaustive live-web census of every researcher.

## Demo index

The quick start imports synthetic people from [`research-talent-scout/tests/fixtures/records.jsonl`](research-talent-scout/tests/fixtures/records.jsonl). Names such as Alice Example are fixtures, not a candidate database.

```bash
cd research-talent-scout

python3 scripts/init_index.py --db data/candidates.sqlite
python3 scripts/import_records.py \
  --db data/candidates.sqlite \
  --input tests/fixtures/records.jsonl

python3 scripts/query_candidates.py \
  --db data/candidates.sqlite \
  --graduation-years 2027,2028 \
  --degree-threshold phd=5,masters=3 \
  --strictly-greater \
  --venues ACL,ICML,ICLR,NeurIPS,EMNLP,CVPR,AAAI,ICCV,MLSys,OSDI,EuroSys,ASPLOS,ISCA,SC,PPoPP \
  --categories main_first,co_first,findings,workshop,short,demo \
  --graduation-states confirmed,likely_needs_verification
```

## Verification

Run from the repository root:

```bash
bash tests/verify-all.sh
```

This validates both Skill structures, frontmatter, the original paper-mode contract, the Pages homepage generator, and the scout's deterministic index, import, query, evidence-state, and rendering tests. GitHub Actions runs the same command on pushes and pull requests to `main`. The frontmatter check is the in-repo standard-library script `scripts/validate_skill_frontmatter.py`.

## GitHub Pages

Paper-mode reports stay off `main`. When publication is authorized, the Skill publishes:

```text
branch: gh-pages
file:   <arxiv-id>/index.html
URL:    https://<owner>.github.io/<repository>/<arxiv-id>/
home:   https://<owner>.github.io/<repository>/
```

For this repository the collection home is `https://lofisu.github.io/recruiting-skills/`. [`scripts/build_pages_index.py`](scripts/build_pages_index.py) renders it from [`assets/pages-index-template.html`](assets/pages-index-template.html). If GitHub writes, Pages settings, or deployment checks are unavailable, the Skill returns the local report and does not invent a live URL.

## Data boundaries

Only public professional information is collected. The Skills never guess email addresses, log in to restricted platforms, bypass access controls, solve CAPTCHAs, or treat search snippets as verified evidence. Outputs are research leads for human review, not candidate rankings, employment decisions, or automated outreach.

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
