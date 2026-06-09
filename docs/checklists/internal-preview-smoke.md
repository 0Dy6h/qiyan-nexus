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
- Operation: open `/literature`; search `特应性皮炎` or `AD`; switch data-source view among `全部来源`、`PubMed 记录`、`CNKI sample`、`上传 PDF`.
- Expected: search results render with source metadata and `记录来源`; the PubMed view banner reads `PubMed 记录（含演示 seed）` and states seed entries are not externally searchable real literature; clicking a result opens `/literature/[id]`.
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
| 2026-05-28 | Codex implementation follow-up | Playwright Chromium headless | `ruff format --check`; `ruff check`; `mypy`; `pytest -q` | `pnpm test`; `pnpm typecheck`; `pnpm build`; `pnpm e2e` | Pass | Backend 249 tests passed; frontend 120 tests passed; Playwright 2 specs passed. Manual P1 findings for `/network` entity chips/links and PDF garbling warning were addressed; local reviewer PDF bodies remain uncommitted. |
| 2026-05-30 | Codex internal-preview closure | Playwright Chromium headless + isolated API PDF probe | `ruff format --check`; `ruff check`; `mypy`; `pytest -q` | `pnpm test`; `pnpm typecheck`; `pnpm build`; `pnpm e2e` | Pass | Backend 251 tests passed; frontend 120 tests passed; Playwright 2 specs passed. Four local reviewer PDFs were uploaded and auto-parsed through isolated temp runtime/upload paths; three are candidate acceptable and one correctly shows the numeric/table garbling warning. Formal clinician/research reviewer sign-off remains pending unless a separate live session is recorded. |

## §4c — Real LLM Provider Walkthrough (L2 promotion gate)

**Prerequisite**: ADR-0012 L2 prerequisites §4a (threshold calibrated) and NLI
gate (opt-in, default-off). NLI gate is validated on real-answer distribution
(0 false accepts, 0 false rejects at threshold 0.5). This walkthrough exercises
the full pipeline with the real `opencode_go` provider and NLI entailment gate.

### Enable (PowerShell, from backend/)

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"
$env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.78"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4000"
$env:QIYAN_NLI_BACKEND = "transformers"
$env:QIYAN_NLI_THRESHOLD = "0.5"
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

Key constraints from live smoke (2026-05-31):
- `max_tokens` must be ≥4000 (1200 silently degrades to deterministic)
- `deepseek-v4-flash` rejects forced `tool_choice` (HTTP 400); grounding uses
  structured-claims v3 path
- NLI gate adds ~2s per answer (batch entailment, after model warm-up)
- Claim-quality prompt/schema v2 asks for 1-3 claims, one evidence ID per claim,
  and direct entailment from `证据文本（claim 只能基于此字段）`; do not treat this as
  L2 evidence until a live capture is recorded.

### Walkthrough Steps

| Step | Operation | Expected result | Record issues |
|---|---|---|---|
| R1 | `POST /api/rag/answer` with `{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":2}` | `provider_name="opencode_go"`, `grounding.status` is `"passed"` or `"blocked"`, NOT `"skipped"` | |
| R2 | Same request, verify grounding metadata | `grounding.checked=true`, `semantic_threshold=0.78`, `nli_threshold=0.5` present; claims have `semantic_score` and `entailment_score` | |
| R3 | Same request, verify disclaimer | `disclaimer = "非诊断结论、需结合临床。"` (byte-identical) | |
| R4 | Use deterministic fallback: remove `QIYAN_OPENCODE_GO_API_KEY`, restart, re-query | `provider_name="deterministic"`, default path unchanged, no error | |
| R5 | Verify rollback: `QIYAN_LLM_PROVIDER=deterministic` | Instant fallback, no code change needed | |
| R6 | Check `/rag` UI: real provider answer shows provider name "opencode_go", SLI (latency/cost), export includes provider metadata | All metadata fields visible and accurate | |
| R7 | If grounding blocks answer with `nli_low_entailment`: verify the hard-block text is shown (NOT the raw draft), citations still appear | Safe fallback behavior, no unverified draft leaked | |
| R8 | Export Markdown from `/rag` and inspect grounding metadata | Export includes NLI threshold, minimum entailment score, and per-claim `semantic_score` / `entailment_score` when present | |

### Expected findings

- **NLI gate behavior**: With the 0.5 threshold, the NLI gate should pass
  faithful claims (entailment ~0.99) and block unsupported claims. Some claims
  may be blocked by the BGE cosine pre-filter at 0.78 before reaching NLI.
- **Latency**: Real provider ~10-15s + NLI gate ~2s per answer (batch entailment,
  after model warm-up). Total ~12-17s per question.
- **Cost**: Check `sli.estimated_cost_usd` (null unless real prices configured).
- **Claim quality**: For prompt/schema v2, record whether the model returns 1-3
  claims, whether each claim has exactly one evidence ref, and whether blocked
  answers are due to BGE, NLI, malformed JSON, or unsupported evidence IDs.

### Completion Record (§4c)

| Date | Reviewer | Browser | Real provider enabled? | Groundings passed? | Pass/Fail | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |
| 2026-06-01 | 真人 reviewer | pwsh API + browser | opencode_go + BGE=0.3 + NLI=0.5 | 4 条查询全 blocked（nli_low_entailment），1 条 claim entailment=0.86 通过 NLI 但同回答另一条 0.004 拉低 min 分 | Pass（gate 正确运行） | R1-R7 全通过。R4（缺 key fallback）和 R5（回滚 deterministic）均验证。R6 前端 UI 正确展示 provider/grounding。结论：NLI gate 在生产管线正确运行，0 误放行。L2 不翻转——BGE=0.78 下无回答穿透，opencode_go 自由改写 + keyword retriever 跨语匹配弱是阻塞因素。详见 ADR-0012 2026-06-01 更新（三）和 `docs/handoffs/2026-06-01-slices-1-5.md`。 |
| 2026-06-02 | Codex technical live validation | pwsh API capture | opencode_go + BGE=0.3 + NLI=0.5 | 4/10 回答 passed，6/10 blocked（均为 `nli_low_entailment`）；14/14 claims 均为单 evidence ref | Pass（技术验证，不是正式 reviewer sign-off） | Claim-quality prompt/schema v2 live capture 完成：无 fallback、无 schema parse failure、无 unsupported refs、无 raw draft 泄漏。4 个 passed 回答经快速 claim-level review 与 cited chunks 对齐。L2 仍不翻转；详见 `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md` 与 ADR-0012 更新（六）。 |
