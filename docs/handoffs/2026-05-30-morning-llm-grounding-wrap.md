# Morning LLM Grounding Wrap Handoff

date: 2026-05-30
status: morning work paused; implementation verified; changes not committed

## Goal

Implement the next AI safety/provider slice, then adjust the operating priority after the user clarified there is no Anthropic subscription. Final direction: keep Anthropic as a later optional path, but prioritize OpenCode Go for live-provider smoke and follow-up work.

## Current state

- Default RAG path remains `deterministic + keyword`; no external provider is called unless env explicitly opts in.
- OpenCode Go is now the preferred live-provider path:
  - first attempts OpenAI-compatible `record_grounded_claims` function tool calling;
  - if the gateway/model rejects tools with HTTP 400/422, retries the older structured claims JSON prompt;
  - either path is checked by the backend grounding gate before display.
- Anthropic native strict tool-use grounding remains implemented but is now documented as later optional, not the current operating path.
- Frontend `/rag` and Markdown export expose provider-native grounding, policy, tool name, and tool call count.
- The user-provided OpenCode Go smoke result has been recorded in `docs/checklists/llm-provider-smoke.md`.
- Worktree is intentionally dirty; no commit was made in this session.

## Completed in this session

- Added native grounding metadata:
  - `structured_claim_refs_v3`
  - `anthropic_tool_use_v1`
  - `opencode_go_tool_use_v1`
  - `provider_native_grounding`, `tool_name`, `tool_call_count`
- Implemented Anthropic strict tool use first, then reprioritized after user direction.
- Implemented OpenCode Go tool-call-first behavior and structured-claims compatibility retry.
- Added backend tests for:
  - Anthropic native tool claims and blocked tool mismatch cases.
  - OpenCode Go tool calls.
  - OpenCode Go retry when tools are rejected.
  - RAG service propagation for native provider claims.
- Updated frontend API types, `/rag` metadata rows, and Markdown export/tests.
- Updated docs:
  - `README.md`
  - `docs/current-state.md`
  - `docs/checklists/llm-provider-smoke.md`
  - `docs/plans/2026-05-21-roadmap.md`
  - `.env.example`
  - handoffs for Anthropic native grounding and OpenCode Go priority.

## Smoke result from user

OpenCode Go live smoke reached the external provider:

- `provider_name=opencode_go`
- `grounding.status=passed`
- `grounding.policy=structured_claim_refs_v3`
- `provider_native_grounding=False`
- `tool_call_count=0`
- `claim_count=3`
- `cited_claim_count=3`
- `input_tokens=355`
- `output_tokens=837`

Interpretation:

- OpenCode Go is usable through the compatibility structured-claims grounding path.
- Native function/tool calling did not surface in that live response.
- The pasted Chinese output showed mojibake, likely from PowerShell output encoding; re-run with UTF-8 capture before judging backend/model Chinese text quality.
- No API key or Authorization header was recorded.

## Still open / blocked

- Live OpenCode Go native `tool_calls` is not yet proven; current live evidence passed only through `structured_claim_refs_v3`.
- Need a UTF-8-safe smoke rerun to determine whether the returned Chinese is actually valid or only displayed incorrectly by PowerShell.
- Need a direct OpenCode Go gateway compatibility spike if `opencode_go_tool_use_v1` is important:
  - capture sanitized HTTP status/body shape for the tools request;
  - compare models;
  - decide whether tool calling is supported by the gateway/model pair.
- Anthropic live smoke is intentionally deferred until the team has an Anthropic subscription/key.
- No commit has been made; next session should review and commit if satisfied.

## Key files and artifacts

- `backend/app/services/llm/opencode_go_provider.py`
- `backend/app/services/llm/anthropic_provider.py`
- `backend/app/services/grounding.py`
- `backend/app/schemas/rag.py`
- `backend/app/services/rag.py`
- `frontend/lib/api/rag.ts`
- `frontend/components/RagAnswerClient.tsx`
- `frontend/lib/rag-export.ts`
- `docs/checklists/llm-provider-smoke.md`
- `docs/handoffs/2026-05-30-opencode-go-priority.md`
- `docs/handoffs/2026-05-30-anthropic-native-grounding.md`

## Verification

Passed:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed: formatting/lint/typecheck passed; full backend suite 260 passed.

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed: full frontend unit suite 127 passed; typecheck passed; build passed; Playwright 2 specs passed.

## Recommended next step

Run one UTF-8-safe OpenCode Go smoke and inspect the saved JSON file. If `grounding.policy` remains `structured_claim_refs_v3`, treat OpenCode Go tool calling as a separate compatibility spike rather than blocking the product path.

Suggested command shape:

```powershell
chcp 65001
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$response = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/rag/answer" `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}'

$response | ConvertTo-Json -Depth 10 | Out-File -Encoding utf8 .\opencode-go-smoke.json
```

## Recommended reading order

1. `docs/handoffs/2026-05-30-morning-llm-grounding-wrap.md`
2. `docs/handoffs/2026-05-30-opencode-go-priority.md`
3. `docs/checklists/llm-provider-smoke.md`
4. `backend/app/services/llm/opencode_go_provider.py`
5. `backend/tests/test_opencode_go_provider.py`

## Recommended skill / toolset

- `test-driven-development` for any provider behavior changes.
- `systematic-debugging` if investigating OpenCode Go tool-call compatibility.
- PowerShell + backend `TestClient` or direct FastAPI smoke for local provider verification.
