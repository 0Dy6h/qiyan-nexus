# Internal Preview Readiness Handoff

date: 2026-05-27
status: implemented, local verification passed

## Current State

Qiyan Nexus is best described as:

> MVP-A evidence workbench mostly ready for internal walkthrough; MVP-B network pharmacology mock path is live; C-stage provider/retrieval infrastructure is partially in place, but real model trust, real data governance, and productionization are not complete.

Default path remains local/offline:

- RAG provider: `deterministic`
- Retrieval provider: `keyword`
- External LLM providers: `mock_claude`, `anthropic`, `opencode_go` are opt-in only
- Vector/hybrid retrieval: opt-in only via `QIYAN_RETRIEVAL_PROVIDER`

## Changes In This Sprint

- `RagAnswerResponse` now carries `input_tokens` and `output_tokens`.
- `/rag` frontend types and UI now expose provider, retrieval strategy, and token usage.
- Markdown export includes provider, retrieval strategy, and token usage.
- `README.md` and `docs/current-state.md` now reflect `/network`, 50-question eval, provider list, retrieval strategy list, and opt-in external service policy.
- Added:
  - `docs/plans/2026-05-27-internal-preview-sprint.md`
  - `docs/checklists/internal-preview-smoke.md`
  - `docs/checklists/llm-provider-smoke.md`
  - `docs/evaluations/2026-05-27-real-data-smoke.md`
- Playwright e2e is now Windows-compatible:
  - Backend webServer starts via `frontend/e2e/start-backend.mjs`.
  - Frontend webServer starts via `frontend/e2e/start-frontend.mjs`.
  - E2E runtime state is isolated for literature, chunks, network tasks, vector cache, and uploads.
  - `frontend/next.config.mjs` allows `127.0.0.1` as a dev origin.
- Added `frontend/e2e/internal-preview.spec.ts` to cover PDF upload fallback, RAG eval, and network mock browser paths.

## Smoke Evidence

PubMed:

- Live NCBI parser/client smoke passed with 10 PMIDs for `atopic dermatitis traditional Chinese medicine`.
- This did not write runtime state; it only verifies network + parser path.

RAG default API:

- TestClient smoke returned HTTP 200.
- `provider_name=deterministic`
- `retrieval.strategy=keyword`
- `input_tokens/output_tokens=null`
- disclaimer byte-identical: `非诊断结论、需结合临床。`

Automated gates:

- Backend: `ruff format --check`, `ruff check`, `mypy`, and `pytest -q` passed; 235 tests.
- Frontend: `pnpm test`, `pnpm typecheck`, and `pnpm build` passed; 109 unit tests.
- Browser: `pnpm e2e` passed; 2 Playwright Chromium specs.

PDF:

- Existing local uploaded PDFs show mixed outcomes: garbled Chinese text with NUL noise, no text layer, encrypted/AES dependency issue, and invalid/truncated file.
- This supports keeping fallback copy honest and deferring OCR/encrypted-PDF handling.
- Automated PDF browser smoke used a generated minimal PDF fixture and validated upload + fallback parse UI only. It does not prove curated Chinese PDF extraction quality.

LLM:

- Live smoke is pending local keys.
- Missing-key/default behavior should remain deterministic and non-failing.

## Remaining Risks

- Documentation drift can recur because code is moving faster than fact-source docs.
- Chinese PDF extraction quality is not yet demo-stable without curated text-layer samples.
- Real LLM provider connectivity does not equal trustworthy medical generation; citation grounding and hallucination rejection are still missing.
- Runtime JSON is approaching its ceiling for concurrent writes, stale state, rollback, and data versioning.
- Network pharmacology is still seed/mock, not TCMSP/STRING/KEGG/GO grade analysis.
- Productionization remains early: no proper auth, database, object storage, audit log, deployment pipeline, monitoring, backup, or data retention workflow.

## Recommended Next Slice

Choose one primary path based on reviewer needs:

1. **Human reviewer walkthrough**: use `docs/checklists/internal-preview-smoke.md` with an internal clinician/research reviewer and record feedback.
2. **LLM trust**: implement citation grounding and out-of-citation rejection before making live providers user-visible by default.
3. **PDF/data quality**: collect approved Chinese PDFs and decide whether to keep `pypdf`, change extractor, or defer OCR.
4. **Network preview**: add a Markdown report export for `/network` tasks with seed chain, parameters, citations, and disclaimer.

## Verification Commands

Backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```
