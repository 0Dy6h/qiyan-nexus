# Internal Review Implementation Handoff

date: 2026-05-28
status: manual P1 findings fixed; automated implementation baseline reconfirmed

## Goal

Execute the accepted internal-preview closure plan as far as possible in the local workspace without fabricating human review evidence.

## Completed

- Reconfirmed the worktree was clean before implementation/documentation updates.
- Probed the four local reviewer PDF samples under `local-review-pdfs/` without committing file bodies.
- Addressed two P1 findings from the later manual walkthrough:
  - `/network` result cards now expose entity chips plus literature / RAG / network focus links, and `/literature?q=...` / `/rag?question=...` now consume those params.
  - PDF parse previews now surface an explicit quality warning when text extraction appears to contain numeric/table garbling.
- Re-ran backend gates:
  - `ruff format --check app tests` passed.
  - `ruff check app tests` passed.
  - `mypy app` passed.
  - `pytest -q` passed with 249 tests.
- Re-ran frontend gates:
  - `pnpm test` passed with 120 tests.
  - `pnpm typecheck` passed.
  - `pnpm build` passed.
  - `pnpm e2e` passed with 2 Playwright Chromium specs.
- Updated `docs/evaluations/2026-05-28-internal-review-feedback.md` with the implementation follow-up evidence.

## Still Open

- Formal clinician/research reviewer sign-off remains optional/pending if the team wants a separate reviewer session. Use `docs/checklists/internal-preview-smoke.md`.
- Broader Chinese PDF quality smoke remains a follow-up. Use 2-3 authorized text-layer Chinese PDFs; do not commit the file bodies unless licensing is explicitly cleared.
- The current PDF warning only flags obvious NUL-placeholder garbling; OCR, scanned-PDF support, table reconstruction, and better extraction heuristics remain out of scope.
- Optional live LLM smoke remains opt-in only and requires local secrets; it is not a blocker for the default internal-preview path.

## Verification

Passed:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Not run:

- Human reviewer browser session.
- Reviewer-approved Chinese PDF upload/parse quality check.
- Live OpenCode Go or Anthropic smoke with local secrets.

## Recommended Next Step

Run the human reviewer walkthrough with the approved PDF sample set, record findings in `docs/evaluations/2026-05-28-internal-review-feedback.md`, and fix only P0/P1 issues before selecting the next development mainline.

## Reading Order

1. `docs/current-state.md`
2. `docs/evaluations/2026-05-28-internal-review-feedback.md`
3. `docs/checklists/internal-preview-smoke.md`
4. `docs/handoffs/2026-05-28-internal-review-implementation.md`
