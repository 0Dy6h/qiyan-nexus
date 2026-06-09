# Internal Preview Evidence Pack Handoff — 2026-06-06

date: 2026-06-06
status: implemented; open/token evidence collector smoke passed
profile: default offline preview remains `deterministic` + `keyword` + JSON runtime

---

## Goal

Make AFK internal-trial evidence repeatable while formal clinician/research reviewer sign-off is still pending. The new evidence pack captures technical smoke results, request IDs, runtime metadata, and logs for open and shared-token preview profiles without changing product defaults.

## Implemented

- Extended `scripts/smoke-internal-preview.ps1`.
  - Preserves existing console-only behavior by default.
  - Adds optional `-ProfileName`, `-OutputJson`, and `-OutputMarkdown`.
  - Writes flow results, request IDs, disclaimer assertion, profile metadata, and pass/fail status when output paths are provided.
  - Does not write the access token value.
- Added `scripts/collect-internal-preview-evidence.ps1`.
  - Starts isolated open profile under `.tmp/internal-preview-evidence/<timestamp>/runtime-open`.
  - Runs structured smoke and writes `open-smoke.json` / `open-smoke.md`.
  - Starts isolated shared-token profile under `.tmp/internal-preview-evidence/<timestamp>/runtime-token`.
  - Runs structured smoke and writes `token-smoke.json` / `token-smoke.md`.
  - Copies backend/frontend logs to stable `backend-open.log`, `frontend-open.log`, `backend-token.log`, and `frontend-token.log`.
  - Writes `metadata.json` and `evidence-summary.md`.
  - Attempts process cleanup in `finally`.
- Extended `frontend/tests/internal-preview-ops-source.test.ts`.
  - Locks structured smoke output parameters and artifact writer.
  - Locks collector existence, output root, open/token runtime roots, JSON/Markdown artifacts, metadata, request ID summary, cleanup, and token omission note.
- Updated `README.md` and `docs/current-state.md` with the new command and boundaries.

## Verification

Focused source test passed:

```powershell
cd frontend
node --import tsx --test tests\internal-preview-ops-source.test.ts
```

Observed: 4 tests passed.

PowerShell parser checks passed for:

```powershell
scripts\smoke-internal-preview.ps1
scripts\collect-internal-preview-evidence.ps1
```

Functional collector smoke passed:

```powershell
.\scripts\collect-internal-preview-evidence.ps1
```

Observed output directory:

```text
.tmp\internal-preview-evidence\20260606-131845\
```

Generated files:

- `evidence-summary.md`
- `metadata.json`
- `open-smoke.json`
- `open-smoke.md`
- `token-smoke.json`
- `token-smoke.md`
- `backend-open.log`
- `frontend-open.log`
- `backend-token.log`
- `frontend-token.log`

Observed smoke summary:

- open profile: passed, 12 flows, 12 request IDs.
- token profile: passed, 12 flows, 12 request IDs.
- backend/frontend ports were unavailable after completion, confirming services were stopped.

## Boundaries

- This does not complete formal clinician or research reviewer sign-off.
- This does not fill `docs/evaluations/2026-06-05-reviewer-feedback.md`.
- This does not enable real LLM, real embedding, PostgreSQL, pgvector retrieval, OCR, commercial PDF extraction, or production authentication.
- The generated evidence directory lives under `.tmp/` and should not be committed.
- Shared-token profile remains an internal preview gate only; token values are intentionally omitted from summaries.

## Recommended Next Step

Run the standard local gate after this slice:

```powershell
.\scripts\verify-local.ps1
```

Before reviewer or branch closeout, also run:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

Formal clinician + research reviewer walkthrough remains the next product gate.

