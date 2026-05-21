# Qiyan Nexus PDF 到 RAG 证据链切片

日期：2026-05-10

## 目标

把当前 PDF 上传与 fake parser 状态推进，补齐到 RAG citation 证据链：

上传 PDF → 写入 pending metadata → fake parser 标记 parsed → 生成 uploaded_pdf chunk → RAG 可检索并引用该 chunk。
同时补齐本地对象存储 mock 的读取入口，使上传后的 PDF 能通过稳定 upload id 预览或下载。

## 当前边界

- 只做 deterministic mock parser。
- 不接真实 PyMuPDF / unstructured。
- 不接真实 LLM、embedding、pgvector、Neo4j、Celery 或外部服务。
- chunk 仍写入本地 JSON，作为后续 ingestion 契约验证。
- PDF 文件读取仍基于本地 `UPLOAD_STORAGE_DIR`，不接真实 MinIO / R2。

## 已实现方向

- `LiteratureChunk` 增加 `source_type` 与 `pdf_upload_id`。
- `InMemoryChunkRepository` 增加 `upsert_uploaded_pdf_chunk`，按 `chunk_id` 幂等更新。
- fake parser 成功时生成 `source_type=uploaded_pdf` 的 chunk。
- fake parser 失败时不生成 chunk。
- RAG 从“每篇文献取第一个 chunk”调整为“每个 chunk 都参与打分”。
- 文献搜索卡片可显示 PDF 解析状态。
- `GET /api/uploads/pdf/{pdf_upload_id}` 可按稳定 upload id 返回本地 PDF，响应 `application/pdf` 且 inline 展示。
- 文献详情页在已有 upload id 时展示 PDF 预览链接。

## 验收标准

- 上传 PDF 返回 `pending`。
- fake parser 成功返回 `parsed`，并生成 uploaded chunk。
- fake parser 失败返回 `failed`，不生成 uploaded chunk。
- RAG 能命中 uploaded chunk，并返回对应 `chunk_id`、`quote`、`reason`。
- `citations[*].literature_id` 仍可解析到文献详情。
- 前端搜索卡片显示 `PDF 待解析`、`PDF 已解析` 或 `PDF 解析失败`。
- 上传 PDF 可通过 `GET /api/uploads/pdf/{pdf_upload_id}` 取回；缺失 upload id 返回 404。
- 文献详情页能从 PDF 状态区打开预览链接。

## 本地验证说明

当前 PowerShell 环境存在两个验证阻塞：

- `backend/.venv` 是 Linux/WSL 结构，`bin/python` 在 Windows 下为 0 字节占位，不能直接运行 pytest。
- `frontend/node_modules/typescript` 是 0 字节文件，`pnpm typecheck` 无法找到 `typescript/bin/tsc`。

建议先修复环境后执行：

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && pnpm install
cd frontend && pnpm test
cd frontend && pnpm typecheck
cd frontend && pnpm build
```

如继续使用 Windows PowerShell，建议重建 Windows venv；如继续使用 Linux venv，需在已安装发行版的 WSL 中运行。
