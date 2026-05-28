# Internal Preview Smoke Checklist

date: 2026-05-27
audience: internal clinician/research reviewer

## Setup

Backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

Frontend:

```powershell
cd frontend
pnpm dev
```

Default expectation: no real LLM key is required; deterministic provider and keyword retrieval should work offline.

## API Smoke

| Step | Request | Expected result | Record issues |
|---|---|---|---|
| Health | `GET http://127.0.0.1:8000/health` | HTTP 200, app responds | |
| Literature search | `GET /api/literature/search?q=AD&source=pubmed&page=1&page_size=5` | HTTP 200, `items` array, PubMed source entries from seed/runtime | |
| RAG answer | `POST /api/rag/answer` with `{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}` | HTTP 200, `provider_name`, `retrieval.strategy`, `disclaimer`, citation card fields | |
| RAG eval | `GET /api/evals/rag-ad/report` | HTTP 200, `summary.total_questions == 50`, disclaimer coverage present | |
| Network analyze | `POST /api/network/analyze` with `{"query":"消风散","analysis_type":"formula"}` | HTTP 202/200 style accepted payload with `task_id` | |
| Network result | `GET /api/network/result/{task_id}` | First poll may be running, later poll returns completed mock chain | |

## UI Path 1: Literature Search

- Preparation: backend and frontend running; no external key required.
- Operation: open `/literature`; search `特应性皮炎` or `AD`; switch data-source view among `全部来源`、`PubMed 实时`、`CNKI sample`、`上传 PDF`.
- Expected: search results render with source metadata; data-source banner changes; clicking a result opens `/literature/[id]`.
- Record issues: empty state mismatch, source label ambiguity, broken detail link, stale runtime state.

## UI Path 2: PDF Upload And Parse

- Preparation: choose a text-layer PDF that the reviewer is allowed to use. Do not upload protected or patient-identifiable files.
- Operation: open `/literature/cn-ad-gbs-001`; upload PDF; trigger auto-parse if needed; open preview link.
- Expected success path: status becomes parsed; parse result shows `pypdf-text-preview`; preview text is legible enough for internal review; uploaded chunk can appear in RAG citation.
- Expected fallback path: scanned/no-text/encrypted PDFs show honest file-level fallback or parse failure; this is not a product bug unless the UI overclaims extraction.
- Record issues:乱码, paragraph order, header/footer noise, encrypted PDF dependency error, no-text scan, invalid PDF.

## UI Path 3: RAG Question

- Preparation: default deterministic provider.
- Operation: open `/rag`; ask `特应性皮炎和肠-脑-皮肤轴有什么关系？`; use `全部文献`, `top_k=2`; export Markdown.
- Expected: answer, citation cards, disclaimer, provider, retrieval strategy, token usage, and export button are visible.
- Expected metadata: provider `deterministic`; strategy `keyword`; token input/output `未返回`.
- Record issues: citation link broken, entity chip broken, token fields misleading, disclaimer missing.

## UI Path 4: RAG Eval

- Preparation: backend running.
- Operation: open `/evals/rag-ad`; click run evaluation.
- Expected: summary displays 50-question run; pass rate, citation hit, chunk hit, disclaimer coverage, must-not violations visible.
- Record issues: page still says 20 questions, report fails, slow run, unclear failed item details.

## UI Path 5: Network Pharmacology Mock

- Preparation: backend and frontend running.
- Operation: open `/network`; submit `消风散` with formula analysis; follow entity chips and related literature links.
- Expected: mock chain renders; entity focus prefill works from `/network?focus=...`; related literature and RAG/network links are navigable.
- Record issues: task stuck, focus prefill wrong, entity label missing, citation/entity back-link broken.

## Completion Record

| Date | Reviewer | Browser | Backend command | Frontend command | Pass/Fail | Notes |
|---|---|---|---|---|---|---|
| 2026-05-27 | Codex local smoke | Playwright Chromium 148 headless | `ruff format --check`; `ruff check`; `mypy`; `pytest -q` | `pnpm test`; `pnpm typecheck`; `pnpm build`; `pnpm e2e` | Pass | Backend 235 tests passed; frontend 109 tests passed; Playwright 2 specs passed. Browser smoke covered literature search/detail/RAG/Markdown affordance, PDF upload fallback parse, 50-question RAG eval surface, and `/network` mock chain. No real LLM key or reviewer-approved Chinese PDF was used. |
| 2026-05-28 | Codex automated closure | Playwright Chromium headless | `ruff format --check`; `ruff check`; `mypy`; `pytest -q` | `pnpm test`; `pnpm typecheck`; `pnpm build`; `pnpm e2e` | Pass | Backend 247 tests passed; frontend 113 tests passed; Playwright 2 specs passed. `pnpm typecheck` is now self-contained through `next typegen && tsc --noEmit`. PubMed parser smoke returned 5 records; default RAG API returned deterministic/keyword/skipped grounding with required disclaimer. Human reviewer walkthrough and reviewer-approved Chinese PDF smoke remain pending. |
