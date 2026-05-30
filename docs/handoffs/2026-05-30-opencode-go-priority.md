# OpenCode Go Priority Handoff

date: 2026-05-30
status: implemented; live OpenCode Go smoke still local-secret-gated

## Goal

Move the live LLM priority away from Anthropic and toward `opencode_go`, because the current team does not have an Anthropic subscription. Keep Anthropic as an optional later path, but make OpenCode Go the first provider to smoke and improve.

## Completed

- Updated `OpenCodeGoProvider` to send OpenAI-compatible function tools first:
  - tool name: `record_grounded_claims`
  - policy on tool success: `opencode_go_tool_use_v1`
  - response answer is rebuilt only from accepted tool claims.
- Added a compatibility retry: if the gateway rejects tool/function calling with HTTP 400/422, the provider retries the existing no-tools structured claims prompt.
- Kept structured claim grounding v3 as the compatibility safety path for OpenCode Go models/gateways that ignore or reject tools.
- Added backend tests for OpenCode Go native tool calls, tool-rejection retry, and RAG service propagation.
- Updated frontend type/export tests to treat OpenCode Go as the native grounding sample provider.
- Updated README, current-state, provider smoke runbook, `.env.example`, and roadmap wording so Anthropic is clearly later optional.

## Safety boundary

- Default remains `QIYAN_LLM_PROVIDER=deterministic`.
- `opencode_go` still requires explicit `QIYAN_OPENCODE_GO_API_KEY`.
- If OpenCode Go returns unsupported evidence IDs, malformed tool args, empty claims, or invalid structured JSON, the grounding gate blocks the answer.
- Anthropic code remains available but should not be the next operating path unless the team obtains an Anthropic key.

## Verification

Passed:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_opencode_go_provider.py tests\test_rag_service.py::test_answer_question_uses_opencode_go_native_tool_claims -q
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed: formatting/lint/typecheck passed; focused OpenCode Go provider/service suite 9 passed; full backend suite 260 passed.

```powershell
cd frontend
pnpm test -- --test-name-pattern "OpenCode Go native|RagAnswerResponse type"
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed: focused frontend tests passed; full frontend unit suite 127 passed; typecheck passed; build passed; Playwright 2 specs passed.

## Next

- Run the preferred OpenCode Go live smoke from `docs/checklists/llm-provider-smoke.md` with a local `QIYAN_OPENCODE_GO_API_KEY`.
- Record whether the gateway returns `opencode_go_tool_use_v1` or falls back to `structured_claim_refs_v3`.
- Only revisit Anthropic after a subscription/key exists.
