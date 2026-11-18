# 协作契约 · Collaboration Contract

中文 | [English](#english)

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

## 职责边界

`research-talent-scout` 负责索引内发现、确定性筛选、毕业与论文核验，以及最终合并结果。`researcher-recruiting-skill` 只对收到的稳定候选人 ID 做有界的公开资料补全。

## 交接协议

交接使用：
- 唯一 `batch_id`
- 稳定的 `candidate_id`
- 明确的 `deadline_at`

资料补全不会扩展到论文的其他合作者，不能重新筛选候选人队列，也不能改写原有论文统计、毕业年份状态或更强的既有证据。

---

## English

## How the two Skills collaborate

```text
Single paper
  └─ researcher-recruiting-skill
       ├─ fetches the official arXiv author order
       ├─ verifies public professional profiles in parallel
       └─ writes a single-file HTML report

Cohort criteria
  └─ research-talent-scout
       ├─ queries the local SQLite index
       ├─ filters by venue, authorship category, degree, and graduation year
       ├─ hands exactly the qualifying candidates to researcher-recruiting-skill
       └─ merges into one evidence-backed result
```

## Ownership

`research-talent-scout` owns indexed discovery, deterministic filtering, graduation and publication verification, and the single final result. `researcher-recruiting-skill` owns only bounded public-profile enrichment for the stable candidate IDs it receives.

## Handoff protocol

The handoff uses:
- a unique `batch_id`
- stable `candidate_id` values
- an absolute `deadline_at`

Enrichment never expands to coauthors, re-filters the cohort, or overwrites stronger graduation or publication evidence.
