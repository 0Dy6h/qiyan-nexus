# Internal preview baseline — 2026-06-04

## Goal

Close the internal preview baseline after MVP-A closeout by locking the already-implemented B6 literature data-source switcher in browser e2e, keeping the Windows Playwright backend teardown fix, and refreshing stale project facts that still pointed at older A/B-stage status.

## Current state

- MVP-A evidence workbench remains complete for internal preview.
- MVP-B network pharmacology mock path remains implemented; this slice did not add network behavior.
- No commit was created for this slice per user instruction. The working tree intentionally contains the changed docs/e2e files listed below.
- `/literature` now has explicit browser regression coverage for:
  - 全部来源
  - PubMed 实时 → backend `source=pubmed`
  - CNKI sample → backend `source=cn_literature`
  - 上传 PDF → backend `has_pdf_upload=true`
  - view-aware `数据来源说明` compliance banner
- Playwright now runs 4 specs instead of 3.
- `frontend/e2e/start-backend.mjs` keeps Windows process-tree teardown with `taskkill /T /F /PID` so uvicorn worker processes do not remain orphaned on port 8000 after e2e shutdown.

## Working tree at stop

Tracked modifications:

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `docs/current-state.md`
- `docs/plans/2026-06-04-mvp-a-closeout.md`
- `frontend/e2e/README.md`
- `frontend/e2e/start-backend.mjs`

Untracked new files:

- `docs/handoffs/2026-06-04-internal-preview-baseline.md`
- `frontend/e2e/literature-data-source.spec.ts`

Light cleanup done:

- Removed Playwright `frontend/test-results/.last-run.json`.
- `.tmp/frontend-3001.err.log` and `.tmp/frontend-3001.out.log` were left in place because an existing Next process on port 3001 still held the handles. Do not remove them unless that dev server is stopped.

## Completed in this slice

- Added `frontend/e2e/literature-data-source.spec.ts`.
- Normalized indentation in `frontend/e2e/start-backend.mjs` while preserving the Windows process-tree cleanup.
- Updated `README.md`:
  - current status now says MVP-A is closed for internal preview
  - `GET /api/literature/search` documents `has_pdf_upload`
  - `/literature` capability describes four data-source views and the compliance banner
- Updated `docs/current-state.md`:
  - internal preview baseline recorded
  - B6 data-source switcher and e2e coverage recorded
  - next-step candidates no longer point to duplicate frontend UI/B6 work
- Updated `docs/plans/2026-06-04-mvp-a-closeout.md`:
  - B6 status now reflects the implemented data-source switcher plus e2e coverage
  - next step moved to reviewer sign-off / L2 governance / PDF quality spike / PG spike
- Updated `AGENTS.md`, `CLAUDE.md`, and `frontend/e2e/README.md` to align command, eval-size, tool-config, and stage wording with current repo facts.

## Verification

Focused e2e:

```powershell
cd frontend
pnpm exec playwright test e2e/literature-data-source.spec.ts
```

Observed:

- `1 passed`

Backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed:

- `ruff format --check`: `104 files already formatted`
- `ruff check`: `All checks passed!`
- `mypy`: `Success: no issues found in 54 source files`
- `pytest -q`: `474 passed, 1 skipped`

Frontend:

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed:

- `pnpm test`: `158 passed`
- `pnpm typecheck`: passed
- `pnpm build`: passed, 8 app routes generated
- `pnpm e2e`: `4 passed`

Note: `pnpm e2e` still prints pypdf warnings (`incorrect startxref pointer`, `parsing for Object Streams`) from the intentionally minimal test PDF used by `internal-preview.spec.ts`; this is expected and non-blocking.

## Still open / deferred

- Review and commit the current working tree when ready; no commit has been made.
- Formal doctor/researcher reviewer sign-off is still a human workflow and cannot be replaced by this automated baseline.
- PDF quality work remains a separate spike: OCR, table reconstruction, and better garbling heuristics are not part of this slice.
- PostgreSQL/pgvector remains a separate production database spike; default runtime remains JSON with optional SQLite.
- L2/default real-provider preview remains not flipped; governance remains separate from this internal preview baseline.

## Key files

- `frontend/e2e/literature-data-source.spec.ts`
- `frontend/e2e/start-backend.mjs`
- `docs/current-state.md`
- `docs/plans/2026-06-04-mvp-a-closeout.md`
- `README.md`

## Recommended next step

Review the working-tree diff, then commit the internal preview baseline as one or two commits after human approval. Do not start PDF OCR, PostgreSQL/pgvector, or L2 governance work in the same commit.

## Recommended reading order

1. `docs/handoffs/2026-06-04-internal-preview-baseline.md`
2. `docs/current-state.md`
3. `frontend/e2e/literature-data-source.spec.ts`
4. `docs/plans/2026-06-04-mvp-a-closeout.md`

## Recommended skill / toolset

- `test-driven-development` for any future behavior change.
- `neat-freak` after the next milestone or before creating a PR.
- `project-grill` or `writing-plans` before PDF quality, PostgreSQL/pgvector, or L2 governance work.
