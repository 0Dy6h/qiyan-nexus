# AFK Internal Trial Ops Handoff — 2026-06-06

date: 2026-06-06
status: implemented; open/token API smoke passed; local gate and open/token E2E passed
profile: default offline preview remains `deterministic` + `keyword` + JSON runtime

---

## Goal

Make internal-trial operations repeatable without waiting for clinician/research reviewer availability: start/stop an isolated preview profile, smoke core APIs in open and shared-token modes, and run Playwright against token-gated frontend/backend wiring.

## Implemented

- Added `scripts/run-internal-preview.ps1`.
  - Starts backend via `backend\.uv-test-venv\Scripts\python.exe -m uvicorn app.main:app`.
  - Starts frontend via `pnpm dev`.
  - Writes runtime state, chunk state, network task state, vector cache, uploads, logs, and `processes.json` under caller-supplied `.tmp\...`.
  - Supports open dev profile by default and token profile with `-AccessToken`.
  - `-Stop` kills the recorded Windows process trees via `taskkill /T /F /PID`.
- Added `scripts/smoke-internal-preview.ps1`.
  - Checks `GET /health`, literature all/PubMed/CNKI/uploaded-PDF filter, PDF upload + auto-parse, RAG answer/export, network analyze/result/report.
  - Uses `curl.exe` for multipart upload and `Invoke-RestMethod` elsewhere.
  - Adds `X-Access-Token` when `-AccessToken` is provided.
  - Prints request IDs and core assertions in a compact table.
- Added E2E token profile wiring.
  - `QIYAN_E2E_ACCESS_TOKEN` maps to backend `QIYAN_ACCESS_TOKENS`.
  - `QIYAN_E2E_ACCESS_TOKEN` maps to frontend `NEXT_PUBLIC_QIYAN_ACCESS_TOKEN`.
  - Playwright disables server reuse in token mode to avoid accidentally testing an existing open-mode server.
  - `.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile` sets `QIYAN_E2E_ACCESS_TOKEN="qiyan-e2e-token"` only around the E2E step and restores the previous environment.
- Updated README, E2E README, and current-state with the new operations commands and boundaries.

## Focused Verification

Passed:

```powershell
cd frontend
node --import tsx --test tests\internal-preview-ops-source.test.ts
```

Observed: `3 passed`.

Passed:

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
.\scripts\smoke-internal-preview.ps1
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop
```

Observed: health, literature four-source checks, PDF upload/auto-parse, RAG answer/export, network analyze/result/report all passed; stop command left backend/frontend ports unavailable.

Passed:

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -AccessToken "trial-token"
.\scripts\smoke-internal-preview.ps1 -AccessToken "trial-token"
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -Stop
```

Observed: same API smoke passed with `X-Access-Token`.

## Branch-Closeout Verification

```powershell
.\scripts\verify-local.ps1
.\scripts\verify-local.ps1 -IncludeE2E
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

Observed:

- `.\scripts\verify-local.ps1`: backend 4 gates passed (`504 passed, 1 skipped`) + frontend `pnpm test` (`166 passed`) + `pnpm typecheck` + `pnpm build`.
- `cd frontend; pnpm e2e`: `4 passed` in open mode.
- `.\scripts\verify-local.ps1 -FrontendOnly -IncludeE2E -E2ETokenProfile`: frontend test/typecheck/build plus token-mode E2E passed (`4 passed`).

## Boundaries

- This does not complete formal clinician or research reviewer sign-off.
- This does not enable real LLM, real embedding, PostgreSQL, pgvector retrieval, OCR, or production authentication by default.
- `NEXT_PUBLIC_QIYAN_ACCESS_TOKEN` / `QIYAN_E2E_ACCESS_TOKEN` remain internal preview shared-token gates only.
- Runtime files under `.tmp/*` are local smoke artifacts and should not be committed.
