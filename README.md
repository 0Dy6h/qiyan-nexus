# Qiyan Nexus

面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。

当前状态：已从纯规划仓库切换到可运行的 MVP-A 证据工作台骨架。文献检索使用本地 JSON seed + repository/service 层；运行时 PDF metadata 与 parse 状态写入 `backend/data/runtime/`，不再污染 seed fixture。RAG endpoint 当前采用 deterministic retrieval，返回 answer、citation cards、retrieval metadata 与“非诊断结论、需结合临床”免责声明。PDF upload 支持本地文件存储、稳定 upload id 下载/预览；文本型 PDF 可通过 `pypdf` 生成预览文本，扫描件或无法抽取文本时诚实回退到文件级占位说明。当前仍不接真实 LLM、embedding、pgvector、Neo4j、Celery、Redis、MinIO、NextAuth 或外部生产服务。

当前事实源索引见 `docs/current-state.md`。正式命名建议见 `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`。短期仓库目录仍保留为 `/home/dyh2026/Projects/Tcm_tech`，避免破坏已有路径和脚本。

## 目录

- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口
- `docs/` — 当前状态、ADR、计划、交接与历史归档
- `docs/archive/pre-dev-planning/` — 早期 AI 工具链规划、Word 文档与 HTML 原型，仅作历史参考

## 后端

首次安装：

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
```

运行测试：

```bash
cd backend
.venv/bin/python -m pytest -q
```

启动开发服务：

```bash
cd backend
.venv/bin/fastapi dev app/main.py
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

文献检索 API 数据来源：

- seed 文献 JSON：`backend/data/literature/sample_ad_literature.json`
- seed chunk JSON：`backend/data/literature/sample_ad_chunks.json`
- runtime 文献状态：`backend/data/runtime/literature_state.json`（gitignored，可从 seed bootstrap）
- repository 层：`backend/app/repositories/literature.py`
- service 层：`backend/app/services/literature.py`
- 当前 PDF metadata 字段：`pdf_upload_id`、`pdf_file_name`、`pdf_parse_status`、`pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count`、`pdf_parse_result`
- 当前支持本地 PDF 上传存储：`POST /api/uploads/pdf`（multipart `file`），默认写入 `backend/uploads/`，可通过 `UPLOAD_STORAGE_DIR` 覆盖
- 当前支持本地 PDF 下载/预览：`GET /api/uploads/pdf/{pdf_upload_id}`，按稳定 upload id 读取 `UPLOAD_STORAGE_DIR` 下的 PDF 文件
- 当前支持文本型 PDF 预览：parse result 可返回 `extraction_method="pypdf-text-preview"` 与 `preview_text`；无法抽取文本时返回 `file-metadata-placeholder`

文献检索 API：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=特应性皮炎"
```

支持参数：

- `q`：必填检索关键词，后端会 trim。
- `source`：`all` / `cn_literature` / `pubmed`，默认 `all`。
- `page`：页码，默认 `1`。
- `page_size`：每页数量，默认 `10`，最大 `50`。
- `sort`：`relevance` / `year_desc` / `year_asc`，默认 `relevance`。

示例：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=瘙痒&source=cn_literature&page=1&page_size=5&sort=relevance"
```

返回字段保留 `query`、`total`、`items`，并新增 `source`、`page`、`page_size`、`total_pages`、`sort`，用于前端分页和排序展示。

文献详情 API：

```bash
curl "http://127.0.0.1:8000/api/literature/cn-ad-gbs-001"
```

PDF upload API（本地文件存储 + 自动关联 literature metadata；默认返回 pending）：

```bash
curl -X POST "http://127.0.0.1:8000/api/uploads/pdf" \
  -F "literature_id=cn-ad-gbs-001" \
  -F "file=@/absolute/path/to/ad-evidence.pdf;type=application/pdf"
```

PDF download/preview API（本地对象存储 mock）：

```bash
curl -L "http://127.0.0.1:8000/api/uploads/pdf/pdf-cn-ad-gbs-001-ad-evidence-pdf" \
  -o ad-evidence.pdf
```

说明：upload endpoint 负责落盘与写入 `pending`；独立 auto-parse endpoint 负责推进 parse 状态，并补充 `pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count` 与 `pdf_parse_result`。解析成功后会向 runtime chunk 状态补充 `source_type=uploaded_pdf` 的 chunk，使上传 PDF 的解析片段可进入 RAG 检索与 citation cards。

Auto-parse API：

```bash
curl -X POST "http://127.0.0.1:8000/api/uploads/pdf/auto-parse" \
  -H "Content-Type: application/json" \
  -d '{"literature_id":"cn-ad-gbs-001","file_name":"ad-evidence.pdf"}'
```

PDF metadata attach API（backend-only）：

```bash
curl -X POST "http://127.0.0.1:8000/api/literature/pdf-metadata" \
  -H "Content-Type: application/json" \
  -d '{"literature_id":"cn-ad-gbs-001","file_name":"ad-evidence.pdf","source_type":"uploaded_pdf"}'
```

PDF parse status API（backend-only）：

```bash
curl -X POST "http://127.0.0.1:8000/api/literature/pdf-parse-status" \
  -H "Content-Type: application/json" \
  -d '{"literature_id":"cn-ad-gbs-001","pdf_parse_status":"parsed"}'
```

RAG API：

```bash
curl -X POST "http://127.0.0.1:8000/api/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":2}'
```

当前 RAG endpoint 采用 deterministic retrieval：基于 literature + chunk 样本，对 title/snippet/abstract/keywords/evidence_tags/chunk text 做关键词命中计分，并返回 answer + citation cards + “非诊断结论、需结合临床”免责声明。当前仍不接真实 LLM、embedding、pgvector 或外部服务。后端契约测试保证每个 `citations[*].literature_id` 都能通过 `/api/literature/{item_id}` 解析到文献详情。RAG 请求支持 `source`（`all` / `cn_literature` / `pubmed`）和 `top_k`（>= 1）控制 citation card，并返回 `retrieval` 元数据（`applied_source`、`applied_top_k`、`available_citation_count`）供前端展示当前检索条件。

RAG eval API：

```bash
curl "http://127.0.0.1:8000/api/evals/rag-ad/report"
```

当前评估报告基于 `backend/data/evals/rag_ad_eval_questions.json` 的 20 个特应性皮炎问题，调用 deterministic RAG 后返回 summary + item results。当前基线目标：20/20 passed，citation_hit 20/20，chunk_hit 20/20，disclaimer 20/20，must_not violations 0。以本地测试输出与最新 handoff 为准。

标准后端验证：

```bash
cd backend
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest -q
```

## 前端

首次安装：

```bash
cd frontend
pnpm install
```

构建验证：

```bash
cd frontend
pnpm build
```

启动开发服务：

```bash
cd frontend
pnpm dev
```

前端 API 地址默认是 `http://127.0.0.1:8000`。如需覆盖：

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev
```

前端测试：

```bash
cd frontend
pnpm test
pnpm typecheck
pnpm build
```

页面：

- 首页：`/`
- 文献检索页：`/literature`
- RAG 问答页：`/rag`
- 文献详情页：`/literature/[id]`
- RAG 评估页：`/evals/rag-ad`
- 合规说明页：`/compliance`

当前前端能力：

- `/literature`：支持 query 输入、来源筛选、加载/错误/空结果状态、结果卡片跳转详情页，并展示演示数据提示。
- `/rag`：支持 question、source、top_k 输入，展示 answer、retrieval metadata、citation cards 与免责声明。
- `/literature/[id]`：服务端读取文献详情，展示统一 meta/body 样式，并提供 PDF 上传入口、PDF 预览链接、parse status、parse message、时间戳、触发来源、尝试次数、解析方式与解析结果预览。
- `/evals/rag-ad`：客户端触发 `/api/evals/rag-ad/report`，展示 20 题 RAG 评估的通过率、引用命中、chunk 命中、免责声明覆盖和禁用语检查。
- `/rag` 与 `/literature` 的状态文案、状态面板、meta 行和正文密度已做最小统一。
- 当 RAG 成功返回 0 citations 时，会展示明确空状态提示，而不是空白引用区。

## 合规底线

所有 AI 输出必须带：

非诊断结论、需结合临床。

本平台不替代医生诊断，不面向普通患者 C 端。
