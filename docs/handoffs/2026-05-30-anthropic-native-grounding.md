# Anthropic Native Grounding Handoff

date: 2026-05-30
status: implemented; priority superseded by `2026-05-30-opencode-go-priority.md`; live Anthropic smoke remains later optional

## Goal

Implement the Anthropic AI safety slice: make the `anthropic` provider use provider-native strict tool use for citation grounding while keeping the default RAG path offline and deterministic. As of the follow-up handoff `2026-05-30-opencode-go-priority.md`, this path is no longer the operational priority because the team does not currently have an Anthropic subscription.

## Completed

- Added `anthropic_tool_use_v1` as an additive grounding policy alongside `structured_claim_refs_v3`.
- Extended grounding metadata with `provider_native_grounding`, `tool_name`, and `tool_call_count`.
- Updated `AnthropicProvider` to force the strict `record_grounded_claims` tool and parse `tool_use` inputs into backend `GroundedClaim` records.
- Wired `AnswerDraft` native grounding metadata through `answer_question()` so the backend only displays answers rebuilt from accepted claims.
- Preserved deterministic fallback for missing Anthropic key, Anthropic API errors, rate limits, and timeouts.
- Kept `opencode_go` on structured claim grounding v3; native OpenAI-compatible tool calling is not claimed for that provider.
- Updated `/rag` frontend metadata, Markdown export, README/current-state docs, `.env.example`, and the LLM provider smoke runbook.

## Safety boundary

- Default remains `QIYAN_LLM_PROVIDER=deterministic`; no external model is called unless a local env override is set.
- Anthropic success requires the `record_grounded_claims` tool. Missing tool use, wrong tool name, malformed tool input, empty claims, missing evidence refs, or out-of-citation evidence IDs hard-block the answer.
- Raw provider text is not used as the user-facing answer in the Anthropic native path.
- This still is not semantic fact verification; it only enforces tool protocol and allowed evidence IDs.

## Verification

Passed:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_rag_grounding.py tests\test_anthropic_provider.py tests\test_rag_service.py tests\test_rag_api.py -q
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed: formatting/lint/typecheck passed; focused RAG/Anthropic suite 65 passed; full backend suite 257 passed.

```powershell
cd frontend
pnpm test -- --test-name-pattern "RagAnswerResponse type|Anthropic native|grounding metadata|buildAnswerMarkdown includes question"
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed: focused frontend tests passed; full frontend unit suite 127 passed; typecheck passed; build passed; Playwright 2 specs passed.

## Remaining work

- Prefer OpenCode Go live smoke first; see `docs/handoffs/2026-05-30-opencode-go-priority.md`.
- Run live Anthropic smoke only after the team has a user-owned local `ANTHROPIC_API_KEY`; record results in `docs/checklists/llm-provider-smoke.md` without secrets or raw Authorization headers.
- Treat semantic hallucination detection, privacy wording, latency/cost SLI, and default live-provider enablement as separate future slices.
