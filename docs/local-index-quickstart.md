# 本地索引快速开始 · Local Index Quickstart

中文 | [English](#english)

演示数据是合成记录 [`research-talent-scout/tests/fixtures/records.jsonl`](../research-talent-scout/tests/fixtures/records.jsonl)（Alice Example、Bob Example 等），只用于演示和测试，不是真实候选人库。

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

---

## English

The demo data is synthetic — [`research-talent-scout/tests/fixtures/records.jsonl`](../research-talent-scout/tests/fixtures/records.jsonl) (Alice Example, Bob Example, etc.) — used for demonstration and testing only, not a real candidate database.

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

`data/*.sqlite` is gitignored and never enters version control.
