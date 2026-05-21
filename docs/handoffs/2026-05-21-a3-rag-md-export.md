# A3 RAG 答案 Markdown 导出

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A3
分支：`feat/rag-citation-pdf-provenance-batch`（沿用上一颗 slice 的分支）

## Goal

按 2026-05-21 路线图阶段 A 第三颗 slice：`/rag` 页面增加「导出答案」按钮，下载 .md 文件，含 question + answer + citations + disclaimer + timestamp。

## Completed

### Backend：在 `/api/rag/answer` 响应里加 `answered_at`

- `app/schemas/rag.py`：`RagAnswerResponse` 增加必填字段 `answered_at: str`。
- `app/services/rag.py`：`answer_question` 返回时填入 `datetime.now(UTC).isoformat()`；与 `app/services/literature.py` 已经在用的 `datetime.now(UTC).isoformat()` 写法一致。
- `tests/test_rag_service.py`：新增 `test_answer_question_returns_iso_utc_answered_at_timestamp`，正则 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00$` 锁住格式（毫秒可选 + 必须以 `+00:00` 结尾）。
- `tests/test_rag_api.py`：在既有 `test_rag_answer_endpoint_returns_ranked_citations_for_gut_skin_axis_question` 内补 `answered_at` 是 str 且 `endswith("+00:00")`，避免在序列化层漏出。

### Frontend：纯函数 markdown 构造 + 文件名

- `lib/api/rag.ts`：`RagAnswerResponse` 新增必填 `answered_at: string`，与后端 schema 对齐。
- `lib/rag-export.ts`（新增）：
  - `buildAnswerMarkdown(result)` → 返回带标题、元数据、问题、回答、引用、disclaimer 的 markdown 字符串。引用块用 `### 引用 N — 标题`，元数据行包含 `来源 · literature_id · 置信度 · chunk_id?/source_type?/pdf_upload_id?`，并按需追加「证据片段引文」与「命中证据标签」段。
  - `buildAnswerMarkdownFileName(answeredAt)` → 从 ISO 时间戳取 `YYYYMMDD-HHmm`，组装 `qiyan-rag-answer-YYYYMMDD-HHmm.md`；时间戳格式异常时回退到 `qiyan-rag-answer.md`。

### Frontend：`/rag` 导出按钮

- `components/RagAnswerClient.tsx`：
  - 引入 `buildAnswerMarkdown` / `buildAnswerMarkdownFileName`。
  - 新增 `onExportAnswer` 处理器：构造 `Blob` + `URL.createObjectURL` + 临时 `<a download>` + click + `URL.revokeObjectURL`。
  - 在「回答结果」section 的 disclaimer 下方放一颗 `button[aria-label="导出答案为 Markdown"]`，文案「导出答案为 Markdown ↓」，沿用既有的 #0d9488 主色与 44px 最小高度。
  - 把 disclaimer `<p>` 的 `marginBottom` 从 0 改为 12，让按钮与免责声明拉出节奏。

### Frontend：测试

- `tests/rag-export.test.ts`（新增）：4 条单元测试，覆盖正常 markdown、空引用占位、文件名生成、文件名 fallback。
- `tests/rag-answer-export.test.ts`（新增）：源码字符串断言锁住按钮存在、`onExportAnswer` 函数、`Blob`/`URL.createObjectURL` 用法、`anchor.download = fileName` 写法。

## Verification

完整 gauntlet 全绿（在两侧各跑一次）：

Backend:
- `cd backend && .venv/bin/python -m ruff format --check app tests` → 47 files already formatted
- `cd backend && .venv/bin/python -m ruff check app tests` → All checks passed!
- `cd backend && .venv/bin/python -m mypy app` → no issues in 29 source files
- `cd backend && .venv/bin/python -m pytest -q` → **99 passed**（98 + 1 新增）

Frontend:
- `cd frontend && pnpm test` → **72 passed**（66 + 6 新增：4 export 单元 + 2 source-string）
- `cd frontend && pnpm typecheck` → pass
- `cd frontend && pnpm build` → 7 routes，build OK

完整一行命令：
```bash
cd backend && .venv/bin/python -m ruff format --check app tests && .venv/bin/python -m ruff check app tests && .venv/bin/python -m mypy app && .venv/bin/python -m pytest -q && echo "BACKEND GAUNTLET GREEN"
cd frontend && pnpm test && pnpm typecheck && pnpm build && echo "FRONTEND GAUNTLET GREEN"
```

## Changed files

- `backend/app/schemas/rag.py`
- `backend/app/services/rag.py`
- `backend/tests/test_rag_service.py`
- `backend/tests/test_rag_api.py`
- `frontend/lib/api/rag.ts`
- `frontend/lib/rag-export.ts`（新增）
- `frontend/components/RagAnswerClient.tsx`
- `frontend/tests/rag-export.test.ts`（新增）
- `frontend/tests/rag-answer-export.test.ts`（新增）
- `docs/handoffs/2026-05-21-a3-rag-md-export.md`（本文档）

## Current caveats

- `answered_at` 当前是非可选必填。如果以后接 LLM 异步生成会复杂化，但目前所有调用方都同步返回，没问题。
- 导出按钮依赖浏览器端 `URL.createObjectURL` + `document.createElement("a")`；SSR 不会触发（按钮在 `RagAnswerClient` 客户端组件里）。
- 文件名只精确到分钟，多次连续导出会同名覆盖；用户场景下可以接受，需要更细就改成秒。
- 没动 deterministic retrieval / disclaimer / RAG eval 行为；eval baseline 不受影响。

## Recommended next step

阶段 A 还剩 4 颗：
- **A6 合规页扩展**（0.5d）：`/compliance` 加「数据来源说明」「PDF 版权声明」段，page-shell test 同步。最小、自包含，可立即推进。
- **A1 真实 PubMed 抓取**（2d）：阻塞 MVP-A 出口最关键的一颗；需要 httpx + NCBI E-utils + 速率限制，可能需要走 Windows 代理。
- **A2 最小访问控制**（1.5d）：X-Access-Token 中间件 + 白名单 env；上线后跑 `security-review` skill。
- **A4 Playwright E2E**（1d）：装 Playwright，写一条 `/literature → 详情 → /rag → 问答 → citation` 串联。
- **A5 真实中文 PDF 人工验收**（0.5d）：依赖用户上传 2-3 个真实 PDF，无法独立推进。

下一颗推荐 **A6**（0.5d，纯文档/UI，无外部依赖），或者直接进 **A1**（开始真正啃 MVP-A 出口）。
