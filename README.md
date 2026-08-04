# 招聘 Skills · Recruiting Skills

中文 | [English](#english)

这是一个招聘相关 Agent Skills 的长期集合。以后用于人才发现、研究者调查、
候选人资料补全、招聘流程辅助等场景的 Skill 都集中维护在这个仓库中。

当前包含两个可以独立安装、也可以协作运行的 Skills：

| Skill | 适用场景 | 主要输出 |
| --- | --- | --- |
| `researcher-recruiting-skill` | 已知一篇 arXiv 论文，调查全部作者 | 作者、机构、主页、公开职业联系方式、GitHub/OpenReview、证据和 HTML 报告 |
| `research-talent-scout` | 按毕业年份、学位、会议和论文数量批量筛人 | 已确认候选人、待核验候选人、论文统计、毕业证据和覆盖范围 |

如果输入是一篇论文，使用第一个 Skill；如果输入是“寻找 2027/2028 届、满足论文门槛的人”，使用第二个 Skill。批量筛选完成后，`research-talent-scout` 可以把入围候选人一次性交给 `researcher-recruiting-skill` 补全公开职业资料。

## 工作方式

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

两个 Skill 通过稳定候选人 ID、唯一 `batch_id` 和明确的 `deadline_at` 协作。资料补全不会扩展到论文的其他合作者，也不能改写原有论文统计、毕业年份状态或更强的既有证据。

## 仓库约定

- 根目录保留 `researcher-recruiting-skill`，兼容现有安装方式；
- 其他招聘 Skill 使用独立的 `<skill-name>/SKILL.md` 子目录；
- 每个 Skill 可以独立安装、触发和验证；
- 跨 Skill 协作必须定义稳定输入、输出、责任边界和失败降级；
- 通用合规原则保持一致：只处理公开职业信息，不执行招聘排名、自动雇佣决策或自动外联。

新增 Skill 后，需要在顶部目录表、安装说明和统一验证脚本中登记。

## 功能

### 单篇论文作者调查

- 接受 arXiv URL、arXiv ID 或精确论文标题；
- 保留 arXiv 官方顺序的完整作者列表；
- best-effort 查找机构、个人主页、公开职业邮箱、GitHub 和 OpenReview；
- 每个非空字段都附可点击的公开证据；
- 使用 `已核验`、`可能匹配`、`暂未找到`、`未执行网页检索` 状态；
- 默认资料补全预算约 20 秒；
- 生成 `outputs/<arxiv-id>/report.html`；
- 授权后可发布至 GitHub Pages 的 `gh-pages:<arxiv-id>/index.html`。

### 批量人才筛选

- 按博士/硕士、毕业年份、院校、实验室、会议和作者类别筛选；
- 支持 `main_first`、`co_first`、`findings`、`workshop`、`short`、`demo` 分类计数；
- 正确区分“多于 5 篇”和“至少 5 篇”；
- 将毕业年份分为 `confirmed`、`likely_needs_verification`、`unknown`、`stale` 和 `conflict`；
- 不会仅凭姓名合并同名研究者；
- 返回全部索引内匹配者，并显示索引覆盖和新鲜度限制；
- 使用 SQLite 进行快速查询；真实候选人数据需要通过规范化 JSONL 导入或后续数据连接器建立。

## 安装

Clone 仓库：

```bash
git clone https://github.com/LofiSu/researcher-recruiting-skill.git
cd researcher-recruiting-skill
```

### Codex：安装两个 Skill

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill"
ln -s "$PWD/research-talent-scout" "${CODEX_HOME:-$HOME/.codex}/skills/research-talent-scout"
```

只需要单篇论文作者调查时，可以仅创建第一个链接。批量筛选和自动资料补全需要两个 Skill 都可被宿主 Agent 发现。安装后请开启新一轮 Agent 会话以刷新 Skill 列表。

其他 Agent Skills 宿主同样需要把两个 Skill 分别放入其技能发现目录，例如 `~/.agents/skills/`、`~/.claude/skills/` 或 `.claude/skills/`。

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

这里的 fixture 只用于演示和测试，不是真实候选人数据库。

## 验证

从仓库根目录运行：

```bash
bash tests/verify-all.sh
```

它会验证原有论文作者 Skill 的静态契约、两个 Skill 的结构，以及 `research-talent-scout` 的索引、导入、查询、证据状态和报告测试。

## GitHub Pages

单篇论文模式生成的报告不会写入 `main`。授权后，报告会发布至：

```text
branch: gh-pages
file:   <arxiv-id>/index.html
URL:    https://<owner>.github.io/<repository>/<arxiv-id>/
```

如果 GitHub 写入、Pages 设置或部署验证不可用，Skill 只返回本地报告，不会虚构线上地址。

## 数据与合规边界

- 只收集公开职业信息；
- 不根据姓名或机构规则猜测邮箱；
- 不登录、不绕过访问控制、不解 CAPTCHA、不批量抓取受限平台；
- 搜索摘要只能用于发现页面，不能单独作为已核验证据；
- 同名身份存在歧义时保持 `可能匹配` 或独立记录；
- 输出用于人工复核，不进行候选人排名、自动雇佣决策或自动外联。

---

## English

This repository is the long-term home for recruiting-related Agent Skills,
including talent discovery, researcher investigation, candidate enrichment,
and recruiting workflow support.

It currently contains two independently installable Skills that can also work
together:

| Skill | Use it for | Main output |
| --- | --- | --- |
| `researcher-recruiting-skill` | Investigating every author of a known arXiv paper | Authors, affiliations, public professional contacts, profiles, evidence, and an HTML report |
| `research-talent-scout` | Filtering a cohort by graduation year, degree, venue, and publication thresholds | Confirmed and pending candidates, categorized paper counts, graduation evidence, and index coverage |

Use the first Skill for a paper-centric request. Use the second for a cohort
request such as “find 2027/2028 graduates above these publication thresholds.”
After filtering, the scout can hand exactly one qualifying-candidate batch to
the recruiting Skill for bounded public-profile enrichment.

## How they collaborate

`research-talent-scout` owns indexed discovery, deterministic filtering,
graduation/publication verification, and the single final result.
`researcher-recruiting-skill` owns only bounded public-profile enrichment for
the stable candidate IDs it receives.

The handoff uses a unique `batch_id`, stable `candidate_id` values, and an
absolute `deadline_at`. Enrichment never expands to coauthors, re-filters the
cohort, or overwrites stronger graduation or publication evidence.

## Repository convention

- the repository root remains `researcher-recruiting-skill` for installation compatibility;
- additional recruiting Skills live in independent `<skill-name>/SKILL.md` directories;
- every Skill must remain independently installable, triggerable, and verifiable;
- cross-Skill workflows must define stable inputs, outputs, ownership, and failure behavior;
- shared compliance rules permit only public professional information and prohibit candidate ranking, automated employment decisions, and automated outreach.

Register every new Skill in the catalog table, installation instructions, and
the repository-wide verification command.

## Features

### Paper author investigation

- accepts an arXiv URL, identifier, or exact paper title;
- preserves the complete official author order;
- finds best-effort affiliations, homepages, public work email, GitHub, and
  OpenReview profiles;
- requires a clickable public source for every non-empty field;
- uses explicit verified, possible-match, not-found, and no-search states;
- targets approximately 20 seconds for native web enrichment;
- writes `outputs/<arxiv-id>/report.html` and can publish it to GitHub Pages
  when authorized.

### Cohort talent scouting

- filters by degree, graduation year, institution, lab, venue, and authorship
  category;
- counts main first, evidenced co-first, Findings, workshop, short, and demo
  papers separately;
- distinguishes “more than N” from “at least N”;
- preserves confirmed, inferred, unknown, stale, and conflicting graduation
  evidence;
- keeps ambiguous same-name researchers separate;
- returns all matches inside declared index coverage and reports freshness
  limitations;
- uses a lightweight SQLite index for fast repeated queries.

The repository ships the indexing and query engine plus synthetic fixtures. It
does not ship a real candidate database; normalized real-world records or data
source connectors must populate the index.

## Installation

```bash
git clone https://github.com/LofiSu/researcher-recruiting-skill.git
cd researcher-recruiting-skill

mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill"
ln -s "$PWD/research-talent-scout" "${CODEX_HOME:-$HOME/.codex}/skills/research-talent-scout"
```

Install only the first link if you need paper author investigation without
cohort filtering. Restart the Agent session after installation so Skill
discovery refreshes.

Other Agent Skills hosts can link both directories into their corresponding
skill discovery directory, such as `~/.agents/skills/`, `~/.claude/skills/`, or
`.claude/skills/`.

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

“All candidates” means all matches within declared index coverage, not an
exhaustive live-web census of every researcher.

## Verification

Run from the repository root:

```bash
bash tests/verify-all.sh
```

This validates both Skill structures, the original paper-mode contract, and the
scout's deterministic index, import, query, evidence-state, and rendering tests.

## Data boundaries

Only public professional information is collected. The Skills never guess
email addresses, log in to restricted platforms, bypass access controls, solve
CAPTCHAs, or treat search snippets as verified evidence. Outputs are research
leads for human review, not candidate rankings, employment decisions, or
automated outreach.
