# Session Handoff — 2026-06-02 (L2 Passed-Claim Reviewer Packet)

branch: main
default RAG path: offline `deterministic`, unchanged
stopped at: delta-only reviewer packet generated, Codex technical verdicts filled and user-confirmed, and price SLI baseline recorded

## Goal

Avoid repeating the 2026-06-01 §4c reviewer walkthrough while closing the next
L2 delta: prepare and technically review the 2026-06-02 claim-quality v2 passed
answers for claim-vs-chunk support.

## Current state

- The 2026-06-01 §4c reviewer walkthrough is already recorded and should not be repeated.
- The 2026-06-02 live capture produced 4 passed answers and 6 blocked answers.
- A reviewer packet now exists at `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`.
- The packet covers `rag-eval-005`, `rag-eval-007`, `rag-eval-008`, and `rag-eval-010`.
- Codex technical evidence-support review marked 6/6 claims `supported`.
- Price SLI baseline exists at `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`.
- User confirmed the six technical verdicts on 2026-06-02.
- L2/default preview remains not flipped; default provider remains `deterministic`.

## Completed in this session

- Added `backend/scripts/build_reviewer_packet.py`.
- Added `backend/tests/test_build_reviewer_packet.py`.
- Generated the delta-only reviewer packet from
  `backend/data/runtime/captured_real_claims_live_20260602_0846.json`.
- Updated `docs/current-state.md`, ADR-0012, the 2026-06-02 validation note, and
  the real-LLM runbook to point to the packet instead of asking for a duplicate §4c run.
- Filled the packet with Codex technical verdicts: 6 supported / 0 unsupported / 0 unclear.
- Recorded price SLI baseline for the 2026-06-02 capture: 6,040 input tokens,
  14,984 output tokens, estimated total cost `$0.005042`, provider latency avg
  13.148s at the current `deepseek-v4-flash` baseline prices.
- Updated `.env.example`, runbook, current-state, live validation note, and ADR-0012.

## Still open / blocked

- Formal verdict confirmation is complete by user confirmation.
- The recorded capture still has `estimated_cost_usd=null` as raw fact because
  price env vars were not set during that run; the retroactive baseline is in a
  separate evaluation note.
- Production budgeting still needs contract/pricing re-check before relying on
  the baseline.
- Any L2/default-provider change still requires a separate ADR-quality decision.

## Key files and artifacts

- `backend/scripts/build_reviewer_packet.py`
- `backend/tests/test_build_reviewer_packet.py`
- `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`
- `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`
- `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`
- `docs/adr/0012-real-llm-enablement.md`
- `docs/guides/real-llm-enablement-runbook.md`
- `docs/current-state.md`

## Verification

- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_build_reviewer_packet.py tests\test_capture_real_answer_claims.py -q` — 6 passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests scripts\build_reviewer_packet.py` — passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff check app tests scripts\build_reviewer_packet.py` — passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m mypy app` — passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest -q` — 359 passed.
- `cd frontend; pnpm test` — 160 passed.
- `cd frontend; pnpm typecheck` — passed when run after build/typegen settled.
- `cd frontend; pnpm build` — passed.
- Price baseline computed from
  `backend/data/runtime/captured_real_claims_live_20260602_0846.json` with
  input `$0.14` / 1M and output `$0.28` / 1M.

Note: `ruff check app tests scripts` still reports pre-existing lint issues in
older scripts such as `eval_bge_separation.py`, `eval_hashing_baseline.py`, and
`smoke_opencode_go_bge.py`; this session validated the standard `app tests`
scope plus the new script directly.

## Recommended next step

Decide whether `BGE=0.3 + NLI=0.5` remains only an L1 demo/evaluation profile or
deserves a separate L2 governance discussion. Do not repeat the full §4c
walkthrough unless the provider/profile changes.

## Recommended reading order

1. `docs/current-state.md`
2. `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`
3. `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`
4. `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`
5. `docs/adr/0012-real-llm-enablement.md`
6. `backend/scripts/build_reviewer_packet.py`

## Recommended skill / toolset

- `test-driven-development` for any change to packet generation.
- `session-handoff` after reviewer verdicts are recorded.
- Plain doc review for the next step; no provider smoke is needed unless config changes.
