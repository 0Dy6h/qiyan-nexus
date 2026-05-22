# A1 真实 PubMed 抓取（最小可用）

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A1
分支：`feat/rag-citation-pdf-provenance-batch`（沿用同一颗 feat 分支批量推进 A 阶段）

## Goal

按路线图阶段 A 第一颗 slice，把 `/api/literature/sync?source=pubmed&q=...` 从设想变成可用接口：
1. 真实命中 NCBI E-utilities（esearch + efetch）。
2. 解析 XML，归一化成 `LiteratureItem` shape。
3. upsert 到 runtime literature 状态文件，不覆盖 seed，不破坏用户上传的 PDF 元数据。
4. 命中数 ≥10 时人工冒烟通过。
5. 前端入口不在本 slice，留给 A1.5。

## Completed

### Backend：PubMed 客户端 + 纯 stdlib 解析器

- `app/services/pubmed.py`（新增）：
  - `PubmedRecord` 数据类（pmid / title / abstract / authors / year / journal / keywords / doi）。
  - `parse_esearch_xml` / `parse_efetch_xml` 纯 stdlib `xml.etree.ElementTree`，不引第三方 XML 库。
  - 年份回退顺序：`ArticleDate/Year` → `Journal/JournalIssue/PubDate/Year` → `MedlineDate`。
  - 作者抽取兼容 `CollectiveName`、`LastName+ForeName` 与单字段。
  - `Abstract/AbstractText` 多段时按 `Label: text` 拼接。
  - `PubmedClient` 用 `httpx.Client`（同步），支持 `NCBI_API_KEY` env、自定义 User-Agent、10s 超时；esearch retmax 上限硬约束到 50。
  - `PubmedFetcher` Protocol：测试用，便于 monkeypatch 注入 fake。

### Backend：repository 增加 upsert

- `app/repositories/literature.py`：`bulk_upsert_pubmed_items(items) -> (created, updated)`。PubMed-owned 字段（title/abstract/authors/year/keywords/source/snippet/citation_url/doi/pubmed_id/language/source_type）会覆盖；PDF 元数据 + parse 状态字段（`pdf_upload_id`, `pdf_file_name`, `pdf_parse_*`, `last_parse_trigger`, `parse_attempt_count`）保留不动。

### Backend：sync 服务 + 路由

- `app/services/literature.py`：
  - 新增 `_default_pubmed_fetcher()` 工厂（测试可 monkeypatch）。
  - `_pubmed_record_to_item_dict(record)` 把 `PubmedRecord` 转换成 `LiteratureItem` 兼容 dict（id = `pmid-<PMID>`，source 固定 `"PubMed live sync"`，language 固定 `"en"`，citation_url 用 `https://pubmed.ncbi.nlm.nih.gov/<pmid>/`）。
  - `sync_pubmed(query, max_results, fetcher=None)` → 调 esearch → 没命中直接返回零计数 → 否则 efetch → bulk upsert → 返回 `LiteratureSyncResponse`（含本次涉及到的所有 items，方便前端展示）。
- `app/schemas/literature.py`：`LiteratureSyncRequest`（`source: Literal["pubmed"]`，`q: str min_length=1`，`max_results: int ge=1 le=50`）+ `LiteratureSyncResponse`。
- `app/api/literature.py`：`POST /api/literature/sync` 路由。CORS 已经允许 POST，无需改。

### Backend：测试（全部离线）

- `tests/fixtures/pubmed/esearch_two_ids.xml`、`tests/fixtures/pubmed/efetch_two_articles.xml`（手工构造，含 2 篇典型 PubMed 结构覆盖：带 `ArticleDate`、`KeywordList`、`CollectiveName`、`AbstractText[Label]` 的第 1 篇 + 只有 `JournalIssue/PubDate` 的第 2 篇）。
- `tests/test_pubmed_parser.py`（新增 5 条）：
  - esearch 解析顺序保留。
  - efetch 完整字段抽取（作者顺序、复合名、abstract 分段、keywords、doi）。
  - 年份回退到 `Journal/JournalIssue/PubDate`。
  - 空 IdList / 空 ArticleSet。
- `tests/test_literature_repository.py`（+2 条）：
  - upsert 同时 insert 新条目并 refresh 旧条目，未匹配的 seed 条目不被动到。
  - upsert 保留 PDF 元数据 + parse_attempt_count。
- `tests/test_literature_sync_api.py`（新增 5 条，用 `_FakePubmedFetcher` + `LITERATURE_RUNTIME_STATE_PATH` env 隔离）：
  - 正常流程：fetched=2 / created=1 / updated=1；runtime state 落盘验证 PDF 字段保留。
  - source ≠ "pubmed" → 422。
  - q="" → 422。
  - max_results=999 → 422。
  - esearch 命中 0 → 计数全 0、items=[]、原 seed 条目仍在。
  - fixture 在 teardown 时清掉 env 并 reload 模块，避免污染其它测试。

### Real-world smoke

走 `HTTPS_PROXY=http://172.26.0.1:7897` 跑了两次真网络验证（在 WSL 端，端到端 ≈ 1.5s）：

1. `PubmedClient.esearch("atopic dermatitis", max_results=10)` → 返回 10 个真 PMID（42159891 / 42159017 / ...），全部 2026 年。
2. `sync_pubmed("atopic dermatitis", max_results=10)` 端到端 → `fetched=10, created=10, updated=0`，runtime state 从 20 条增长到 30 条。命中示例：
   - `pmid-42159891 | 2026 | Understanding Infantile Atopic Dermatitis: A Review of Environmental, Familial, ...`
   - `pmid-42159017 | 2026 | Keratinocyte Priming by Staphylococcus aureus Reduces HSV-1 Susceptibility...`
   - `pmid-42158620 | 2026 | Thermosensitive Hydrogel Enables Noninvasive Extracellular Vesicle Therapy for AD...`

验收标准 「命中数 >=10」 通过。

## Verification

Backend gauntlet 全绿：
- `ruff format --check app tests` → 50 files already formatted
- `ruff check app tests` → All checks passed!
- `mypy app` → no issues in 30 source files (29 + pubmed)
- `pytest -q` → **111 passed**（99 + 12 新：5 parser + 5 sync API + 2 repo）

完整一行：
```bash
cd backend && .venv/bin/python -m ruff format --check app tests && .venv/bin/python -m ruff check app tests && .venv/bin/python -m mypy app && .venv/bin/python -m pytest -q && echo "BACKEND GAUNTLET GREEN"
```

前端未改动，gauntlet 无需重跑。

## Changed files

- `backend/app/api/literature.py`
- `backend/app/repositories/literature.py`
- `backend/app/schemas/literature.py`
- `backend/app/services/literature.py`
- `backend/app/services/pubmed.py`（新增）
- `backend/tests/test_literature_repository.py`
- `backend/tests/test_literature_sync_api.py`（新增）
- `backend/tests/test_pubmed_parser.py`（新增）
- `backend/tests/fixtures/pubmed/esearch_two_ids.xml`（新增）
- `backend/tests/fixtures/pubmed/efetch_two_articles.xml`（新增）
- `docs/handoffs/2026-05-21-a1-pubmed-sync.md`（本文档）

## Current caveats

- **无速率限制守门**。NCBI 限速 3 req/s（无 key）/ 10 req/s（有 key）。当前一次 `sync_pubmed` 只跑 2 次 HTTP（esearch + efetch），即使 max_results=50 也是单次 fetch，不会触发。如果未来加并发或定时同步，必须加 token bucket。
- **没有重试 / 退避**。NCBI 抖动会直接抛 `httpx.HTTPStatusError` 到 FastAPI（默认 500）。下一颗 slice（或 A2 之后）应当包一层重试 + 用户可读错误。
- **runtime state 写入是“覆盖式 JSON 重写”**。并发两个 sync 请求会丢写。当前 MVP 单用户场景可接受；上访问控制（A2）后如果有并发就要加文件锁或迁移 SQLite。
- **没有去重 evidence_tags**。新插入的 PubMed 条目 `evidence_tags=[]`，跟 seed 的精挑细选 tags 不同。RAG 检索目前依赖 evidence_tag alias bonus，新条目相关性会偏低；这是阶段 A 期内可接受的（RAG eval baseline 仍跑 seed 数据）。
- **API key 不强制**。`NCBI_API_KEY` env 在 `PubmedClient` 里是 optional；生产环境强烈建议设。
- **前端入口完全没有**。`/literature` 页面看不到「同步 PubMed」按钮；只能 POST `http://127.0.0.1:8000/api/literature/sync`，body `{"source": "pubmed", "q": "...", "max_results": <1-50>}`。

## Recommended next step

按路线图剩余阶段 A 4 颗：
- **A1.5（建议）**：补前端入口 —— `/literature` 页面顶部加「同步 PubMed」表单（query + max_results），打这个新接口，把 fetched/created/updated 计数显示出来。0.5d 量级，跟 A1 自然衔接。
- A6 合规页扩展（0.5d）：可与 A1.5 并行。
- A2 最小访问控制（1.5d）：上线 sync 接口之后接入 X-Access-Token 是合理的下一步，避免 sync 接口被外部滥用。
- A4 Playwright E2E（1d）：装 Playwright，写一条主路径串联。

我会建议：**A1.5 →（同 commit 内或独立 commit）A6 → A2**。把前端入口补完，再统一上访问控制。
