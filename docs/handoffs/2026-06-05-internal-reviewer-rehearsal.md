# Internal Reviewer Rehearsal — 2026-06-05

date: 2026-06-05  
status: completed  
profile: default offline preview (`deterministic` provider + `keyword` retrieval + open access)

---

## 背景

本轮承接 reviewer walkthrough 闭环计划：在正式医生 + 科研 reviewer 走查前，先由内部代走完整跑一遍核心路径，验证环境、清单、request tracing、PDF 样本和导出链路是否能支撑正式 sign-off。

本轮不启用真实 LLM、不启用访问 token、不切换 PostgreSQL、不引入 `pdfplumber` 默认路径。后端使用隔离 runtime/upload 目录完成代走，避免污染本地默认 `backend/data/runtime/` 与 `backend/uploads/`。

## 环境

- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`
- Backend start command: `backend\.uv-test-venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Runtime isolation:
  - `.tmp/walkthrough/runtime/literature_state.json`
  - `.tmp/walkthrough/runtime/chunk_state.json`
  - `.tmp/walkthrough/runtime/network_tasks_state.json`
  - `.tmp/walkthrough/uploads/`
- PDF sample: `local-review-pdfs/健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf`

说明：原计划中的 FastAPI CLI 命令在 Windows 重定向日志时会因 Rich banner emoji 触发 GBK `UnicodeEncodeError`；代走改用 `uvicorn app.main:app` 启动同一 app，避免 CLI banner，不影响后端代码路径。

## 代走结果

| Flow | Result | Evidence |
|---|---|---|
| 文献检索 | PASS | 默认检索返回 20 条；四来源视图均触发预期 API 参数：all / PubMed / CNKI / uploaded PDF |
| PDF 上传→自动解析 | PASS | `cn-ad-barrier-006` 上传样本 PDF，`POST /api/uploads/pdf` 返回 201，auto-parse 返回 `parsed` + `pypdf-text-preview`，无 `quality_warning` |
| RAG 问答 | PASS | deterministic + keyword；返回 2 条 citation，其中包含 uploaded PDF citation；免责声明逐字显示；Markdown 导出成功 |
| RAG 空问题 | PASS | 空问题显示 `请输入问题。`，未进入后端生成路径 |
| 网络药理学 | PASS | `消风散` mock 分析完成，网络图可见，键盘烟测通过，富集分析表格展示 14 条 term，Markdown 报告导出成功 |

Request IDs captured:

| Label | Status | Request ID |
|---|---:|---|
| literature_search_all | 200 | `48ed30bf-5a98-4ef6-87ed-6e47e28a64fa` |
| literature_search_pubmed | 200 | `310878ac-f71c-4f28-9a3b-8064f35615f4` |
| literature_search_cnki | 200 | `dd2e0f0b-b87c-449e-b11c-5d43dd72e953` |
| literature_search_uploaded_pdf | 200 | `fa7b1d1e-ac78-41ed-b0cf-92c6122a1011` |
| pdf_upload | 201 | `627699aa-49a7-418e-9a62-4d5263b7db9c` |
| pdf_auto_parse | 200 | `54064882-d39b-413c-bb9c-246f543633cb` |
| rag_answer | 200 | `19a4e52b-32d3-4b0d-8270-325efb164b7d` |
| network_analyze | 202 | `a4aaab0f-9179-45e8-8b22-8dba31bcf716` |

Console/page findings: none in final pass.

## 修复项

### P1: Network enrichment table was empty in reviewer seed path

- Symptom: `/network` could submit `消风散` and render chains, but the checklist-required "富集分析结果" table did not appear.
- Root cause: `backend/app/services/network.py` loaded GO/KEGG sample dictionaries from `backend/app/data/network/...`; actual tracked data lives under `backend/data/network/...`.
- Fix: use `Path(__file__).resolve().parents[2] / "data" / "network" / ...` for both GO and KEGG loaders.
- Regression test: `backend/tests/test_network_enrichment_integration.py::test_xiaofengsan_mock_analysis_returns_visible_enrichment_terms`.

### P2: PDF file picker and upload submit button shared the same accessible name

- Symptom: The file input and submit button were both exposed as "上传 PDF", which is confusing for automation and screen-reader workflows.
- Fix: file input `aria-label` changed to `选择 PDF 文件`; submit button remains visually and accessibly `上传 PDF`.
- Regression test: `frontend/tests/pdf-upload-status.test.ts`.

## Reviewer Packet Readiness

`docs/checklists/internal-preview-reviewer-walkthrough.md` was lightly refreshed to match current UI and rehearsal findings:

- Records the default offline profile.
- Names the primary PDF sample and optional quality-warning sample.
- Updates PDF flow from manual parse trigger to automatic parse confirmation.
- Adds P0/P1/P2/P3 priority rules.
- Adds request ID and "是否阻塞试用" fields to issue reporting.

## Verification

Pre-rehearsal gates:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed:

- format: `110 files already formatted`
- ruff check: `All checks passed!`
- mypy: `Success: no issues found in 59 source files`
- pytest: `498 passed, 1 skipped`

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed:

- `pnpm test`: `158 passed`
- `pnpm typecheck`: passed
- `pnpm build`: passed
- `pnpm e2e`: `4 passed`

Focused post-fix checks:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_network_enrichment_integration.py tests\test_enrichment_service.py -q
```

Observed: `17 passed`.

```powershell
cd frontend
node --import tsx --test tests\pdf-upload-status.test.ts
```

Observed: `11 passed`.

## Open / Next

- Formal doctor + research reviewer sign-off is still pending. This internal rehearsal proves the workflow is ready to schedule; it is not a substitute for human domain judgment.
- Use `docs/evaluations/2026-06-05-reviewer-feedback.md` as the formal feedback packet.
- If formal feedback includes P0/P1 findings, fix only those blockers first and retest the affected flow before broadening scope.

## Key Files

- `docs/checklists/internal-preview-reviewer-walkthrough.md`
- `docs/evaluations/2026-06-05-reviewer-feedback.md`
- `backend/app/services/network.py`
- `backend/tests/test_network_enrichment_integration.py`
- `frontend/components/LiteraturePdfUploadClient.tsx`
- `frontend/tests/pdf-upload-status.test.ts`
