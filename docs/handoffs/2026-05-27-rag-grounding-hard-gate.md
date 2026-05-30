# RAG Grounding Hard Gate Handoff

date: 2026-05-27
status: implemented, upgraded to structured claim grounding v3

## Scope

Implemented a lightweight hard-block grounding gate for external RAG providers, then upgraded it from v2 sentence refs to v3 structured claim refs. The default path is still `deterministic + keyword`; real providers remain opt-in smoke paths only.

## Behavior

- `RagAnswerResponse` now includes `grounding`.
- `deterministic` and fallback deterministic paths return `grounding.status="skipped"`.
- `anthropic` and `opencode_go` successful drafts are checked after provider generation.
- External drafts must be structured claims JSON: `{"claims":[{"text":"...","evidence_refs":["chunk-..."]}]}`.
- The backend rebuilds the displayed answer from accepted structured claims instead of exposing raw provider prose.
- If the draft is not parseable claims JSON, has empty claims, has a claim without evidence refs, or references an ID outside the current citation set, the backend replaces `answer` with the hard-block copy and returns `grounding.status="blocked"`.
- Citations, `provider_name`, and token usage remain in the response when blocked so reviewers can audit what happened.
- External-provider success uses `grounding.policy="structured_claim_refs_v3"` and exposes `structured_claims`, `claim_count`, and `cited_claim_count` for UI and Markdown export.

## Changed Surfaces

- Backend:
  - `backend/app/services/grounding.py`
  - `backend/app/schemas/rag.py`
  - `backend/app/services/rag.py`
  - `backend/app/services/llm/anthropic_provider.py`
  - `backend/app/services/llm/opencode_go_provider.py`
  - `backend/app/schemas/eval.py`
  - `backend/app/services/eval.py`
- Frontend:
  - `/rag` shows grounding status, sentence coverage, structured claim count, and a warning block when the answer is hard-blocked.
  - Markdown answer export includes grounding status, policy, sentence coverage, structured claims, blocked reason, matched refs, and unsupported refs.
  - `/evals/rag-ad` shows grounding blocked count and item grounding status.
- Docs:
  - `README.md`
  - `docs/current-state.md`
  - `docs/checklists/llm-provider-smoke.md`
  - `docs/plans/2026-05-27-internal-preview-sprint.md`

## Verification

Focused backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests/test_rag_grounding.py tests/test_rag_service.py tests/test_rag_api.py tests/test_anthropic_provider.py tests/test_opencode_go_provider.py tests/test_eval_service.py tests/test_eval_api.py -q
# 84 passed
```

Focused frontend:

```powershell
cd frontend
pnpm test -- --test-name-pattern "RagAnswerResponse|buildAnswerMarkdown|warning|grounding|fetches report payload"
# 113 passed under filtered run
pnpm test
# 113 passed
pnpm typecheck
# passed
```

Full gauntlet should still be run before final commit:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q

cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

## Remaining Risks

- Hard-block v2 checks sentence-level evidence ID coverage, not semantic factual grounding.
- A live provider can still produce a semantically wrong statement with an allowed evidence ID; full tool-use grounding and out-of-citation rejection remain the next trust slice.
- Live provider smoke still requires local user-owned keys and was not run in this implementation.

## 2026-05-28 Structured Claim v3 Follow-up

- `GroundingMetadata.policy` now supports `structured_claim_refs_v3`.
- `GroundingMetadata.structured_claims` records accepted or blocked structured claims for reviewer audit.
- Provider prompts now require JSON-only `claims` output and explicitly forbid prose outside JSON.
- Natural-language answers with bracketed chunk IDs are now blocked for external providers with `blocked_reason="structured_claims_parse_error"`.
- This is still not semantic fact verification and still not provider-native tool-use grounding.

## 2026-05-27 Live OpenCode Go Follow-up

- `/models` returned 16 model IDs, including `deepseek-v4-flash`, `deepseek-v4-pro`, `minimax-m2.7`, `minimax-m2.5`, `kimi-k2.6`, `glm-5.1`, `glm-5`, `qwen3.7-max`, `qwen3.6-plus`, and `qwen3.5-plus`.
- With `deepseek-v4-flash` and `QIYAN_OPENCODE_GO_MAX_TOKENS=1200`, direct smoke returned final `content`, matched both allowed `chunk-...` refs, and passed grounding.
- With very low token ceilings, reasoning models can spend the completion budget on `reasoning_content` and return empty final `content`; provider now treats empty content as invalid and falls back to deterministic instead of raising.
- `kimi-k2.6` produced fullwidth evidence brackets during one smoke; grounding now accepts both ASCII and fullwidth square brackets.
