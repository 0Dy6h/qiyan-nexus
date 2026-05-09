# Qiyan Nexus

面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。

当前状态：已从纯规划仓库切换到开发骨架启动阶段。当前已有四条已验证的后端纵向切片：文献检索使用本地 JSON 样本文献库 + repository 层 + FastAPI 搜索接口；文献详情接口可按 ID 返回单条样本文献；RAG endpoint 已升级为基于 literature + chunk 样本的 deterministic retrieval，并返回带引用卡片与 retrieval metadata 的合规问答响应；PDF upload endpoint 已支持本地文件存储并返回 storage metadata。另已为文献记录补上 PDF metadata 契约字段（`pdf_upload_id`、`pdf_file_name`、`pdf_parse_status`），为后续真实 ingestion / parser slice 预留稳定接口。

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

文献检索 mock API：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=特应性皮炎"
```

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

说明：upload endpoint 只负责落盘与写入 `pending`；真正的 mock 解析推进由独立 fake parser API 完成，并补充 `pdf_parse_message`、`pdf_parse_started_at`、`pdf_parse_finished_at`、`last_parse_trigger`、`parse_attempt_count`。

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

当前验证结果：

- 后端：`cd backend && .venv/bin/python -m pytest -q` → 62 passed
- 前端：`cd frontend && pnpm test` → 37 passed
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

当前前端能力：

- `/literature`：支持 query 输入、来源筛选、加载/错误/空结果状态、结果卡片跳转详情页
- `/rag`：支持 question、source、top_k 输入，展示 answer、retrieval metadata、citation cards 与免责声明
- `/literature/[id]`：服务端读取文献详情，展示统一 meta/body 样式，并提供 PDF 上传入口、parse status 展示、parse message/时间戳/触发来源/尝试次数展示，以及 pending→parsed/failed 的手动 mock 推进按钮
- `/rag` 与 `/literature` 的状态文案、状态面板、meta 行和正文密度已做最小统一
- 当 RAG 成功返回 0 citations 时，会展示明确空状态提示，而不是空白引用区

## 合规底线

所有 AI 输出必须带：

非诊断结论、需结合临床。

本平台不替代医生诊断，不面向普通患者 C 端。
