# Qiyan Nexus

面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。

当前状态：已从纯规划仓库切换到开发骨架启动阶段。当前已有多条已验证的纵向切片：文献检索使用本地 JSON 样本文献库 + repository 层 + FastAPI 搜索接口；文献详情接口可按 ID 返回单条样本文献；RAG endpoint 已升级为基于 literature + chunk 样本的 deterministic retrieval，并返回带引用卡片与 retrieval metadata 的合规问答响应；PDF upload endpoint 已支持本地文件存储、稳定 upload id 下载/预览，并返回 storage metadata。另已为文献记录补上 PDF metadata 契约字段（`pdf_upload_id`、`pdf_file_name`、`pdf_parse_status`），fake parser 成功后会写入 `uploaded_pdf` chunk，使上传 PDF mock 解析结果可进入 RAG 检索与 citation cards。RAG 评估 endpoint 可运行 20 个 AD 问题集，统计引用命中、chunk 命中、必含词缺口、禁用语风险与免责声明覆盖。当前仍不接真实 PDF parser、LLM、embedding、pgvector 或外部服务。

正式命名建议见 `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`。短期仓库目录仍保留为 `/home/dyh2026/projects/Tcm_tech`，避免破坏已有路径和脚本。

## 目录

- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口
- `docs/` — 规划、ADR、设计与开发计划
- `Traedos/`、`Cursordos/` — 历史 AI 工具链规划产物

## 后端

首次安装：

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .
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

- 样本文献 JSON：`backend/data/literature/sample_ad_literature.json`
- repository 层：`backend/app/repositories/literature.py`
- service 层：`backend/app/services/literature.py`
- 当前已预留 PDF metadata 字段：`pdf_upload_id`、`pdf_file_name`、`pdf_parse_status`、`pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count`
- 当前已支持本地 PDF 上传存储：`POST /api/uploads/pdf`（multipart `file`），默认写入 `backend/uploads/`，可通过 `UPLOAD_STORAGE_DIR` 覆盖
- 当前已支持本地 PDF 下载/预览：`GET /api/uploads/pdf/{pdf_upload_id}`，按稳定 upload id 读取 `UPLOAD_STORAGE_DIR` 下的 PDF 文件

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

说明：upload endpoint 只负责落盘与写入 `pending`；真正的 mock 解析推进由独立 fake parser API 完成，并补充 `pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count`。
fake parser 成功时还会向 `backend/data/literature/sample_ad_chunks.json` upsert 一个 `source_type=uploaded_pdf` 的 chunk；失败时只更新解析状态，不生成 chunk。RAG deterministic retrieval 会按 chunk 粒度检索，因此上传 PDF 的 mock 解析片段可被引用卡片回指。

Fake parser API（独立 mock 解析步骤）：

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

RAG mock API：

```bash
curl -X POST "http://127.0.0.1:8000/api/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":2}'
```

当前 RAG endpoint 当前采用 deterministic retrieval：基于 literature + chunk 样本，对 title/snippet/abstract/keywords/evidence_tags/chunk text 做关键词命中计分，并返回 answer + citation cards + “非诊断结论、需结合临床”免责声明。当前仍不接真实 LLM、embedding、pgvector 或外部服务。后端契约测试已保证每个 `citations[*].literature_id` 都能通过 `/api/literature/{item_id}` 解析到文献详情。RAG 请求支持 `source`（`all` / `cn_literature` / `pubmed`）和 `top_k`（>= 1）控制 citation card，并返回 `retrieval` 元数据（`applied_source`、`applied_top_k`、`available_citation_count`）供前端展示当前检索条件。

RAG eval API：

```bash
curl "http://127.0.0.1:8000/api/evals/rag-ad/report"
```

当前评估报告基于 `backend/data/evals/rag_ad_eval_questions.json` 的 20 个特应性皮炎问题，调用 deterministic RAG 后返回 summary + item results。当前本地结果：20 题中 15 题通过，20 题有预期文献命中，9 题有预期 chunk 命中，20 题覆盖免责声明，禁用语违规 0。

当前验证结果：

- 后端：`cd backend && .\.venv\Scripts\python.exe -m pytest -q --basetemp .\.pytest-tmp` → 69 passed
- 前端：`cd frontend && pnpm test` → 45 passed
- 前端：`cd frontend && pnpm typecheck` → 通过
- 前端：`cd frontend && pnpm build` → 通过

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
```

页面：

- 首页：`/`
- 文献检索页：`/literature`
- RAG 问答页：`/rag`
- 文献详情页：`/literature/[id]`
- RAG 评估页：`/evals/rag-ad`

当前前端能力：

- `/literature`：支持 query 输入、来源筛选、加载/错误/空结果状态、结果卡片跳转详情页
- `/rag`：支持 question、source、top_k 输入，展示 answer、retrieval metadata、citation cards 与免责声明
- `/literature/[id]`：服务端读取文献详情，展示统一 meta/body 样式，并提供 PDF 上传入口、PDF 预览链接、parse status 展示、parse message/时间戳/触发来源/尝试次数展示，以及 pending→parsed/failed 的手动 mock 推进按钮
- `/evals/rag-ad`：客户端触发 `/api/evals/rag-ad/report`，展示 20 题 RAG 评估的通过率、引用命中、chunk 命中、免责声明覆盖和禁用语检查
- `/rag` 与 `/literature` 的状态文案、状态面板、meta 行和正文密度已做最小统一
- 当 RAG 成功返回 0 citations 时，会展示明确空状态提示，而不是空白引用区

## 合规底线

所有 AI 输出必须带：

非诊断结论、需结合临床。

本平台不替代医生诊断，不面向普通患者 C 端。
