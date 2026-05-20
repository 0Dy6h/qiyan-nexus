# Qiyan Nexus RAG citation 透传 PDF 出处 + 解析方式分支文案

日期：2026-05-21

## Goal

接住 2026-05-17 handoff 推荐的下一颗切片，并把它扩成一颗完整 vertical slice：

1. 把 chunk 上已有的 `source_type` / `pdf_upload_id` 透传到 RAG `/api/rag/answer` 返回的 `CitationCard`，让前端能识别 citation 是否来自上传的 PDF。
2. `/rag` 页面对 `source_type === "uploaded_pdf"` 的 citation 显示「来自上传 PDF」标签，并提供「预览原文 PDF」直链（复用既有的 `buildPdfDownloadUrl`）。
3. 文献详情页 PDF 上传面板的解析结果描述按 `extraction_method` 分支：`pypdf-text-preview` 时如实告知已抽取文本层；fallback 时保留原诚实占位说明。

## Completed

### Backend：citation 透传 chunk 出处

- `app/schemas/rag.py`：`CitationCard` 新增可选字段 `source_type: str | None` 和 `pdf_upload_id: str | None`，默认 `None` 以保持对旧响应的向后兼容。
- `app/services/rag.py`：在 `answer_question` 内组装 `CitationCard` 时，从 selected chunk 上转写 `source_type` / `pdf_upload_id`；无 chunk 时（仅文献级 citation）保持 `None`。

### Backend：测试

- `tests/test_rag_service.py`：
  - 新增 `test_answer_question_can_cite_uploaded_pdf_chunk` 已有 fixture 现在断言 `source_type == "uploaded_pdf"` 与 `pdf_upload_id == "pdf-cn-ad-gbs-001-ad-evidence-pdf"`。
  - 新增 `test_answer_question_leaves_sample_chunk_citation_without_upload_metadata`，保证 sample chunk citation 的 `source_type == "sample"`、`pdf_upload_id is None`，防止把所有 citation 都打上 uploaded 标签。

### Frontend：CitationCard 类型 + RagAnswerClient

- `lib/api/rag.ts`：`CitationCard` 类型补齐 `source_type?` / `pdf_upload_id?` / 同时把先前 schema 上已有但 TS 漏的 `chunk_id` / `quote` / `reason` 也补上。
- `components/RagAnswerClient.tsx`：
  - 引入 `buildPdfDownloadUrl` 计算 PDF 预览 URL。
  - `isUploadedPdf = citation.source_type === "uploaded_pdf"`。
  - meta row 增加「证据片段 来自上传 PDF」标签（仅 uploaded_pdf 显示）。
  - 文献详情链接旁边追加「预览原文 PDF ↗」，链接到 `/api/uploads/pdf/{pdf_upload_id}` 预览端点，新标签页打开。

### Frontend：解析方式分支文案

- `components/LiteraturePdfUploadClient.tsx`：解析结果描述根据 `currentParseResult.extraction_method` 切换：
  - `pypdf-text-preview`：「已抽取文本层预览，可对照原文做证据核对；扫描件与 OCR 能力将在后续接入。」
  - 其他（含 `file-metadata-placeholder`）：「未能抽取文本层，已回退到文件级占位说明；正文抽取与 OCR 能力将在后续接入。」

### Frontend：测试

- 新增 `tests/rag-uploaded-pdf-citation.test.ts`：
  - 通过具体值构造一个完整 `CitationCard`，借 `tsc --noEmit` 锁住新字段在类型上不可丢。
  - 读 `components/RagAnswerClient.tsx` 源码，正则断言已分支于 `citation.source_type === "uploaded_pdf"`、出现「来自上传 PDF」徽章、通过 `buildPdfDownloadUrl(citation.pdf_upload_id)` 构造链接、有「预览原文 PDF」文案。
- `tests/pdf-upload-status.test.ts`：补 `parse result description branches on extraction_method` 测试，要求 `已抽取文本层预览` / `回退到文件级占位说明` / `OCR 能力将在后续接入` 同时出现，且不再出现旧的“当前仅展示文件级信息与预览提示，正文抽取与 OCR 能力将在后续接入。”这条无条件文案，并且必须使用 `extraction_method === "pypdf-text-preview"` 判别。
- `tests/literature-detail-meta.test.ts`：调整旧的「文件级解析结果预览」描述断言，改为对 fallback 分支文案的断言，避免和上面分支测试冲突。

## Verification

完整 gauntlet 全绿（在 backend / frontend 两侧各跑了一遍）：

Backend:
- `cd backend && .venv/bin/python -m ruff format --check app tests` → 47 files already formatted
- `cd backend && .venv/bin/python -m ruff check app tests` → All checks passed!
- `cd backend && .venv/bin/python -m mypy app` → no issues in 29 source files
- `cd backend && .venv/bin/python -m pytest -q` → **98 passed**（较 2026-05-17 的 93 + 5 个新增）

Frontend:
- `cd frontend && pnpm test` → **66 passed**（较上一轮 58 + 多个新增/分裂）
- `cd frontend && pnpm typecheck` → pass
- `cd frontend && pnpm build` → 7 routes，build OK

## Changed files

- `backend/app/schemas/rag.py`
- `backend/app/services/rag.py`
- `backend/tests/test_rag_service.py`
- `frontend/components/LiteraturePdfUploadClient.tsx`
- `frontend/components/RagAnswerClient.tsx`
- `frontend/lib/api/rag.ts`
- `frontend/tests/literature-detail-meta.test.ts`
- `frontend/tests/pdf-upload-status.test.ts`
- `frontend/tests/rag-uploaded-pdf-citation.test.ts` (新增)
- `docs/handoffs/2026-05-21-rag-citation-pdf-provenance-and-parse-method-copy.md` (本文档)

## Current caveats

- 当前 branch 是 `chore/repo-cleanup-docs`，但本切片是 `feat` 而非 `chore` —— 视下一步是直接提交于现有分支还是新开 `feat/rag-citation-pdf-provenance` 分支，由用户决定。
- citation 的 `source_type` 现在以 chunk 上的字段为单一来源。对于纯文献级 citation（无 chunk 时），返回 `null`，前端不会显示徽章，行为安全。
- “预览原文 PDF” 链接打开的是 `/api/uploads/pdf/{pdf_upload_id}` 预览端点（既有路由），不是直接下载 + 不依赖 LLM。
- 没有改 RAG 排序或检索逻辑；q019 等 eval baseline 不受影响（pytest 仍 20/20 隐含通过）。

## Recommended next step

1. **人工走查 `/rag`**：选一条已经上传过 PDF 的文献，输入跟 PDF 内容相关的问题，确认 citation 卡片上：
   - 显示「证据片段 来自上传 PDF」徽章。
   - 同时有「查看文献详情 →」与「预览原文 PDF ↗」两个链接。
   - 点「预览原文 PDF」新标签页打开 PDF。
2. **commit** 本切片（branch 决策见上）：
   ```bash
   git add backend/app/schemas/rag.py backend/app/services/rag.py backend/tests/test_rag_service.py \
           frontend/components/LiteraturePdfUploadClient.tsx frontend/components/RagAnswerClient.tsx \
           frontend/lib/api/rag.ts frontend/tests/literature-detail-meta.test.ts \
           frontend/tests/pdf-upload-status.test.ts frontend/tests/rag-uploaded-pdf-citation.test.ts \
           docs/handoffs/2026-05-21-rag-citation-pdf-provenance-and-parse-method-copy.md
   git commit -m "feat(rag,frontend): surface uploaded pdf provenance on citations and branch parse copy"
   ```
3. **下一颗自然 slice 候选**：
   - 把 `extraction_method` 同样在 `/literature/[id]` 详情页的 PDF 元数据展示区显式展示中文标签（例如「解析方式：pypdf 文本预览」），让没进解析结果面板的入口也能识别。
   - 或者：在 `/rag` 页面对 `source_type === "uploaded_pdf"` 的 citation 额外暴露 chunk 内的 `source_quote` 浮层（已有 quote 字段，但目前 UI 没渲染）。
