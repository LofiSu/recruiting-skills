# 功能说明 · Capabilities

中文 | [English](#english)

## 单篇论文作者调查

由 `researcher-recruiting-skill` 执行：

- 接受 arXiv URL、arXiv ID 或精确论文标题；
- 保留 arXiv 官方顺序的完整作者列表；
- best-effort 查找机构、个人主页、公开职业邮箱、GitHub 和 OpenReview；
- 每个非空字段都附可点击的公开证据；
- 使用 `已核验`、`可能匹配`、`暂未找到`、`未执行网页检索` 状态；
- 默认资料补全预算约 20 秒；
- 生成 `outputs/<arxiv-id>/report.html`，该目录已加入 `.gitignore`；
- 授权后可发布至 GitHub Pages 的 `gh-pages:<arxiv-id>/index.html`。

## 批量人才筛选

由 `research-talent-scout` 执行：

- 按博士/硕士、毕业年份、院校、实验室、会议和作者类别筛选；
- 支持 `main_first`、`co_first`、`findings`、`workshop`、`short`、`demo` 分类计数；
- 正确区分"多于 5 篇"和"至少 5 篇"；
- 将毕业年份分为 `confirmed`、`likely_needs_verification`、`unknown`、`stale` 和 `conflict`；
- 不会仅凭姓名合并同名研究者；
- 返回全部索引内匹配者，并显示索引覆盖和新鲜度限制；
- 使用 SQLite 进行快速查询。可以用 OpenAlex 或 Semantic Scholar 的公开元数据 API 写入 JSONL 再导入；仓库不附带真实候选人数据库。

导入细节见 [从 OpenAlex / Semantic Scholar 导入](importing-openalex-semantic-scholar.md)。

---

## English

## Paper author investigation

Owned by `researcher-recruiting-skill`:

- accepts an arXiv URL, identifier, or exact paper title;
- preserves the complete official author order;
- finds best-effort affiliations, homepages, public work email, GitHub, and OpenReview profiles;
- requires a clickable public source for every non-empty field;
- uses explicit verified, possible-match, not-found, and no-search states;
- targets approximately 20 seconds for native web enrichment;
- writes `outputs/<arxiv-id>/report.html` (gitignored) and can publish it to GitHub Pages when authorized.

## Cohort talent scouting

Owned by `research-talent-scout`:

- filters by degree, graduation year, institution, lab, venue, and authorship category;
- counts main first, evidenced co-first, Findings, workshop, short, and demo papers separately;
- distinguishes "more than N" from "at least N";
- preserves confirmed, likely_needs_verification, unknown, stale, and conflicting graduation evidence;
- keeps ambiguous same-name researchers separate;
- returns all matches inside declared index coverage and reports freshness limitations;
- uses a lightweight SQLite index for fast repeated queries;
- can fill that index from the OpenAlex and Semantic Scholar public metadata APIs.

The connectors write normalized JSONL. They do not ship a live candidate database, and they do not mark graduation years as confirmed. See [Importing from OpenAlex / Semantic Scholar](importing-openalex-semantic-scholar.md).
