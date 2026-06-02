# Session Handoff — 2026-06-02 (LLM Claim Quality v2 Live Validation)

branch: main
default RAG path: offline `deterministic`, unchanged
working tree: dirty, not committed
stopped at: claim-quality v2 implemented, live validation completed, docs updated

---

## Goal

Close the next LLM claim-quality slice after L2 remained L1: tighten real-provider
claim generation, expose NLI metadata, then validate the result with a real
`opencode_go` capture. The slice reached a technical validation record but does
not flip the default provider.

## Current State

- Real provider is still opt-in only. `QIYAN_LLM_PROVIDER` default remains unset/`deterministic`.
- `GROUNDING_SYSTEM_PROMPT` asks for `1-3` short JSON claims, exactly one evidence ID per claim, directly entailed by `证据文本（claim 只能基于此字段）`.
- OpenCode Go function schema allows max 3 claims and max 1 `evidence_ref` per claim.
- Frontend RAG API types, `/rag` metadata, and Markdown export surface NLI threshold/min entailment score and per-claim entailment score.
- `backend/scripts/capture_real_answer_claims.py` now records per-question and aggregate claim-quality fields.
- Live validation record exists at `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`.

## Completed in This Session

- Backend prompt/schema:
  - Tightened `backend/app/services/llm/prompting.py`.
  - Tightened `backend/app/services/llm/opencode_go_provider.py`.
  - Updated Anthropic/OpenCode Go prompt-shape tests.
- Capture script:
  - Added `_build_question_capture_entry()` with claim ref counts, grounding scores, retrieval strategy, token usage, latency, and cost fields.
  - Added aggregate capture meta counts for grounding status, blocked reasons, provider distribution, and zero/one/multi-ref claims.
  - Added `backend/tests/test_capture_real_answer_claims.py`.
- Frontend transparency:
  - Updated `frontend/lib/api/rag.ts`.
  - Updated `frontend/components/RagAnswerClient.tsx`.
  - Updated `frontend/lib/rag-export.ts`.
  - Added tests for NLI metadata and claim-level scores.
- Live validation:
  - Ran real `opencode_go` capture with `BGE=0.3 + NLI=0.5`.
  - Runtime artifact: `backend/data/runtime/captured_real_claims_live_20260602_0846.json` (gitignored, do not commit).
  - Result: 10 questions, 14 claims, 14/14 single evidence ref, 4 answers passed, 6 blocked by `nli_low_entailment`, no fallback, no unsupported refs, no schema failures, no raw draft leakage.
- Docs:
  - Added `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`.
  - Added ADR-0012 update six.
  - Updated `docs/current-state.md`.
  - Updated `docs/guides/real-llm-enablement-runbook.md`.
  - Updated `docs/checklists/internal-preview-smoke.md`.

## Still Open / Blocked

- L2 default preview remains not flipped.
- The `BGE=0.3 + NLI=0.5` profile is validated as an evaluation/L1 smoke profile only; accepting it for default preview needs a separate ADR-quality decision.
- Formal clinician/research reviewer sign-off is still missing. The passed claims received only quick technical claim-level review.
- Real `QIYAN_OPENCODE_GO_PRICE_*` values were not configured, so cost SLI remains `null`.
- Changes are uncommitted.

## Key Files and Artifacts

- `backend/app/services/llm/prompting.py`
- `backend/app/services/llm/opencode_go_provider.py`
- `backend/scripts/capture_real_answer_claims.py`
- `backend/tests/test_capture_real_answer_claims.py`
- `backend/tests/test_llm_prompting.py`
- `backend/tests/test_opencode_go_provider.py`
- `backend/tests/test_anthropic_provider.py`
- `frontend/lib/api/rag.ts`
- `frontend/components/RagAnswerClient.tsx`
- `frontend/lib/rag-export.ts`
- `frontend/tests/rag-api.test.ts`
- `frontend/tests/rag-export.test.ts`
- `frontend/tests/client-section-consistency.test.ts`
- `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`
- `docs/adr/0012-real-llm-enablement.md`
- `docs/guides/real-llm-enablement-runbook.md`
- `docs/checklists/internal-preview-smoke.md`
- `docs/current-state.md`

## Verification

Focused checks already passed:

- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_llm_prompting.py tests\test_opencode_go_provider.py tests\test_anthropic_provider.py tests\test_rag_grounding.py tests\test_grounding_nli.py tests\test_rag_api.py -q` — 59 passed.
- `cd frontend; node --import tsx --test tests\rag-api.test.ts tests\rag-answer-export.test.ts tests\client-section-consistency.test.ts` — 14 passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_capture_real_answer_claims.py -q` — 2 passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe scripts\capture_real_answer_claims.py` — offline smoke passed.
- Live capture command with real key completed; output file named above.

Full gates should be run before committing:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests scripts
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests scripts
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q

cd ..\frontend
pnpm test
pnpm typecheck
pnpm build
```

## Recommended Next Step

Run the full gates, then commit the code/docs slice if green. If continuing the
L2 line after that, schedule a formal reviewer walkthrough focused only on the
four passed questions from `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`.

## Recommended Reading Order

1. `docs/current-state.md`
2. `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`
3. `docs/adr/0012-real-llm-enablement.md` update six
4. `docs/guides/real-llm-enablement-runbook.md`
5. `backend/scripts/capture_real_answer_claims.py`

## Recommended Skill / Toolset

- `test-driven-development` for any follow-up code slice.
- `session-handoff` before stopping after reviewer sign-off.
- `systematic-debugging` if live provider output regresses to fallback, malformed JSON, or unexpectedly high NLI false rejects.
