# Internal Preview Closure Handoff

date: 2026-05-30
status: automated closure and local PDF sample probe complete; formal human reviewer sign-off still pending

## Goal

Implement the accepted internal-preview closure plan: reconfirm the automated MVP-A / MVP-B mock baseline, exercise local reviewer PDF samples through the real upload/parse path, record evidence durably, and only fix P0/P1 issues if found.

## Current state

- Full backend and frontend automated gates passed on 2026-05-30.
- Four local reviewer PDFs under `local-review-pdfs/` were exercised through `POST /api/uploads/pdf` and `POST /api/uploads/pdf/auto-parse` with isolated temp runtime/upload paths.
- Three PDF samples are candidate acceptable for internal demo.
- `中医辨证治疗异位性皮炎临床观察_周海啸.pdf` still shows numeric/table garbling risk and correctly triggers `quality_warning`.
- No new P0/P1 code defect was found in this closure pass.
- Formal clinician/research reviewer sign-off was not captured by this agent run and should not be implied from Playwright or API probes.

## Completed in this session

- Rechecked the worktree before docs edits; only `backend/.pytest-tmp/` was present as an untracked temp directory.
- Re-ran backend gates: ruff format check, ruff check, mypy, pytest.
- Re-ran frontend gates: unit tests, typecheck, production build, Playwright e2e.
- Ran isolated PDF acceptance probe across the four local reviewer PDFs without committing PDF bodies, runtime state, or uploads.
- Updated `docs/evaluations/2026-05-28-internal-review-feedback.md` with the 2026-05-30 closure evidence and PDF sample table.
- Updated `docs/current-state.md` and `docs/checklists/internal-preview-smoke.md` to point to this closure pass; the `docs/current-state.md` update has since been committed with the network report export feature.

## Still open / blocked

- Formal clinician/research reviewer walkthrough remains pending unless the team runs a live reviewer session and records it.
- OCR, scanned-PDF handling, table reconstruction, and better extraction heuristics remain out of scope.
- Live OpenCode Go / Anthropic provider smoke remains optional and local-secret-gated.
- The network Markdown report export baseline has since landed; remaining product mainline choices are provider-native grounding, network report export follow-up (backend report endpoint, PDF/Word, or richer report content), and runtime JSON to SQLite/PostgreSQL spike.

## Key files and artifacts

- `docs/evaluations/2026-05-28-internal-review-feedback.md`
- `docs/checklists/internal-preview-smoke.md`
- `docs/current-state.md`
- `docs/handoffs/2026-05-30-internal-preview-closure.md`
- `local-review-pdfs/` local-only PDF bodies, not committed

## Verification

Passed:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed backend result: 251 tests passed.

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed frontend result: 120 unit tests passed, typecheck passed, build passed, 2 Playwright Chromium specs passed.

PDF probe:

- Four local PDFs uploaded and auto-parsed through FastAPI `TestClient`.
- Each upload returned HTTP 201.
- Each auto-parse returned HTTP 200 and `pdf_parse_status="parsed"`.
- No tracked runtime/upload files were produced by the probe.

Not verified:

- Live clinician/research reviewer browser session.
- Live OpenCode Go or Anthropic smoke with local secrets.

## Recommended next step

If the team wants formal internal-preview sign-off, run `docs/checklists/internal-preview-smoke.md` with a live clinician/research reviewer and append the result to `docs/evaluations/2026-05-28-internal-review-feedback.md`. If formal sign-off is not required, choose one next mainline: provider-native grounding is the highest-safety AI slice; network report export follow-up can deepen the already-landed Markdown baseline; runtime storage migration is an infrastructure spike.

## Recommended reading order

1. `docs/current-state.md`
2. `docs/evaluations/2026-05-28-internal-review-feedback.md`
3. `docs/checklists/internal-preview-smoke.md`
4. `docs/handoffs/2026-05-30-internal-preview-closure.md`

## Recommended skill / toolset

- `writing-plans` for the next chosen mainline.
- `test-driven-development` for any P0/P1 fixes found in a live reviewer session.
- Browser/Playwright for reviewer-flow regressions.
