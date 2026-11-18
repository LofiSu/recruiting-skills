# 从 OpenAlex / Semantic Scholar 导入 · Importing from OpenAlex / Semantic Scholar

中文 | [English](#english)

连接器在 `research-talent-scout/scripts/connectors/`，入口是 `scripts/fetch_records.py`。它们只读公开学术元数据，写成 JSONL 再由 `import_records.py` 导入。不猜测邮箱，不下载全文，不把毕业年份标成 `confirmed`。`--degree` 是调用者给索引用的标签，不是 API 事实。`identity_state: verified` 只表示这一行对应一个来源作者 ID，不是雇佣核验。同名作者不会被合并。

## 默认速率限制

| 来源 | 默认间隔 | 说明 |
| --- | --- | --- |
| OpenAlex | 0.2 秒 | 低于无 key 的每秒 10 次，也低于免费 key 的每秒 30 次 |
| Semantic Scholar | 1.1 秒 | 按 introductory key 的每秒 1 次 |

收到 HTTP 429 或 503 时最多重试 3 次，并遵守 `Retry-After`。

## 环境变量

| 变量 | 作用 |
| --- | --- |
| `OPENALEX_API_KEY` | 真实拉取时需要。以 `Authorization: Bearer` 发送，不要放进命令行参数。不设 key 时只有很小的测试额度，并且不会用 cursor 翻页。列表请求大约 10 credits，免费 key 每日大约 100,000 credits。 |
| `S2_API_KEY` | 可选。以请求头 `x-api-key` 发送。有 key 时 introductory 限额是每秒 1 次。不设 key 时走公共池（文档写明共享每秒 1000 次，拥挤时会更慢）。 |

## 示例命令

```bash
cd research-talent-scout
export OPENALEX_API_KEY=...   # 不要提交到 git
export S2_API_KEY=...         # 可选

python3 scripts/fetch_records.py \
  --source openalex \
  --venue NeurIPS \
  --year 2024 \
  --degree phd \
  --output data/openalex.jsonl

python3 scripts/fetch_records.py \
  --source semanticscholar \
  --author-id 1234567 \
  --degree phd \
  --output data/s2.jsonl

python3 scripts/init_index.py --db data/candidates.sqlite
python3 scripts/import_records.py --db data/candidates.sqlite --input data/openalex.jsonl
```

也可以按作者姓名搜索（`--author`）。多个来源 ID 会各成一行。Semantic Scholar 的论文检索按相关度排序，不是某个会议的全量普查，默认最多 25 篇。一作且 venue 能对上支持列表时记为 `main_first`；venue 字符串写明 workshop、findings、short 或 demo 时分开记；其余作者记为 `unclassified`。不推断共同一作。

离线样例是合成作者 Ada Fixture 和 Ben Fixture，不是真人库：

```bash
python3 scripts/import_records.py \
  --db data/candidates.sqlite \
  --input examples/sample-records.jsonl
```

---

## English

The connectors live in `research-talent-scout/scripts/connectors/`. `scripts/fetch_records.py` writes JSONL for `import_records.py`. It reads public scholarly metadata only: no email guessing, no full-text download, and no confirmed graduation year. `--degree` is a caller-supplied index label, not an API fact. `identity_state: verified` means the row is one source author ID, not a hiring check. People who share a display name stay on separate rows.

## Default rate limits

| Source | Default pause | Notes |
| --- | --- | --- |
| OpenAlex | 0.2 s | Under the keyless cap of 10 req/s and the free-key cap of 30 req/s |
| Semantic Scholar | 1.1 s | Matches the introductory API-key limit of 1 req/s |

HTTP 429 and 503 responses are retried up to three times, honoring `Retry-After`.

## Environment variables

| Variable | Role |
| --- | --- |
| `OPENALEX_API_KEY` | Required for real OpenAlex use. Sent as `Authorization: Bearer`, never as an argv flag. Without a key the API allows only a small test budget and this client does not follow cursor pages. List calls cost about 10 credits; a free key is about 100,000 credits per day. |
| `S2_API_KEY` | Optional. Sent as the `x-api-key` header. With a key, the introductory limit is 1 request/second. Without a key, calls share the public pool (documented as 1000 requests/second shared, and slower when that pool is busy). |

## Example commands

```bash
cd research-talent-scout
export OPENALEX_API_KEY=...   # do not commit
export S2_API_KEY=...         # optional

python3 scripts/fetch_records.py \
  --source openalex \
  --venue NeurIPS \
  --year 2024 \
  --degree phd \
  --output data/openalex.jsonl

python3 scripts/fetch_records.py \
  --source semanticscholar \
  --author-id 1234567 \
  --degree phd \
  --output data/s2.jsonl

python3 scripts/init_index.py --db data/candidates.sqlite
python3 scripts/import_records.py --db data/candidates.sqlite --input data/openalex.jsonl
```

`--author` searches by name. Semantic Scholar paper search is relevance-ranked, not a complete census of a venue, and the default cap is 25 works. The first author of a supported main-conference venue is `main_first`. Workshop, findings, short, and demo are recorded only when the venue string says so. Every other author is `unclassified`. Equal contribution is not inferred.

The offline sample uses synthetic people (Ada Fixture and Ben Fixture), not a real candidate database:

```bash
python3 scripts/import_records.py \
  --db data/candidates.sqlite \
  --input examples/sample-records.jsonl
```
