# Formal Reviewer Sign-off Handoff — 2026-06-05

date: 2026-06-05
status: technical-preflight-complete; formal human sign-off pending
profile: default offline preview (`deterministic` provider + `keyword` retrieval + open access)

---

## Goal

Execute the formal reviewer closeout plan up to the point that can be completed by engineering: classify the current worktree, preserve an isolated run profile, verify the pre-review baseline, and prepare a durable handoff for the real clinician and research reviewer. Human sign-off is still pending and must not be inferred from automated tests or internal rehearsal.

## Current state

- MVP-A evidence workbench is closed for internal preview.
- MVP-B network pharmacology mock path is runnable, including mock GO/KEGG enrichment, network graph keyboard navigation, citation/entity links, and Markdown report export.
- Internal reviewer rehearsal passed on 2026-06-05 in the default offline profile.
- Formal reviewer packet is ready at `docs/evaluations/2026-06-05-reviewer-feedback.md`.
- Formal clinician and research reviewer fields are still blank; no final sign-off decision has been made.

## Completed in this session

- Confirmed worktree classification:
  - `.gitignore` and `CLAUDE.md` contain CodeGraph / Claude runtime guidance changes.
  - `frontend/next-env.d.ts` was modified by Next type generation (`.next/types` to `.next/dev/types` import).
  - `.codex/` is local Codex hook/tooling state and should not be mixed into the reviewer business closeout.
- Added technical preflight metadata to `docs/evaluations/2026-06-05-reviewer-feedback.md`.
- Preserved the formal review operating assumptions: offline deterministic provider, keyword retrieval, open dev mode, isolated runtime/upload paths, and no external LLM egress.
- Started the backend against `.tmp/formal-review/runtime/*` and `.tmp/formal-review/uploads/`, then ran API smoke checks for health, literature search, RAG answer/export, and network analyze/result/report.

## Still open / blocked

- Formal clinician reviewer walkthrough is pending.
- Formal research reviewer walkthrough is pending.
- P0/P1/P2/P3 triage remains empty until human reviewer feedback is recorded.
- If any P0/P1 issue appears, fix only that blocker and retest the affected flow before expanding scope.

## Key files and artifacts

- `docs/checklists/internal-preview-reviewer-walkthrough.md` — step-by-step reviewer checklist.
- `docs/evaluations/2026-06-05-reviewer-feedback.md` — formal feedback packet to fill.
- `docs/handoffs/2026-06-05-internal-reviewer-rehearsal.md` — engineering rehearsal evidence.
- `docs/current-state.md` — project state source of truth.
- `local-review-pdfs/健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf` — primary PDF sample.
- `local-review-pdfs/中医辨证治疗异位性皮炎临床观察_周海啸.pdf` — optional quality-warning sample.

## Verification

Previously verified in this planning/execution handoff sequence:

- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` — passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` — passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m mypy app` — passed.
- `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest -q` — passed with `499 passed, 1 skipped`.
- `cd frontend; pnpm test` — passed with `159 passed`.
- `cd frontend; pnpm typecheck` — passed.
- `cd frontend; pnpm build` — passed.
- `cd frontend; pnpm e2e` — passed with `4 passed`.

Formal-review isolated API smoke:

| Flow | Status | Request ID | Notes |
|---|---:|---|---|
| `GET /health` | 200 | captured in access log | returned `status=ok` |
| `GET /api/literature/search?source=all` | 200 | captured in access log | returned literature results |
| `GET /api/literature/search?source=pubmed` | 200 | captured in access log | returned PubMed-scoped results |
| `GET /api/literature/search?source=cn_literature` | 200 | captured in access log | returned CNKI sample-scoped results |
| `GET /api/literature/search?has_pdf_upload=true` | 200 | captured in access log | uploaded-PDF filter path reachable |
| `POST /api/rag/answer` | 200 | `a6dd27ce-24e0-4032-9464-f409f53b62c2` | provider `deterministic`, 2 citations, required disclaimer present |
| `POST /api/rag/answer/export` | 200 | `49d4f598-0d37-4ff6-b119-68b6704ab406` | exported Markdown from full `RagAnswerResponse` payload |
| `POST /api/network/analyze` | 202 | `fb6502fd-3112-4483-9389-f99e43d8e297` | accepted `消风散` formula task |
| `GET /api/network/result/{task_id}` | 200 | `1a60bc43-8c6c-40a6-ad42-f9ed9fdac86b` | completed; nested result contained 5 chains and 14 enrichment terms |
| `GET /api/network/result/{task_id}/report` | 200 | `8c18521f-61be-4386-8d6d-96e2d4a85218` | exported Markdown report |

Rerun the standard gate after any P0/P1 code fix.

## Recommended next step

Schedule and run the real clinician + research reviewer walkthrough using `docs/checklists/internal-preview-reviewer-walkthrough.md`, then fill `docs/evaluations/2026-06-05-reviewer-feedback.md`. If both reviewers report no P0/P1 issues, update `docs/current-state.md` to say formal reviewer sign-off is complete and small-scale internal trial may proceed.

## Recommended reading order

1. `docs/evaluations/2026-06-05-reviewer-feedback.md`
2. `docs/checklists/internal-preview-reviewer-walkthrough.md`
3. `docs/handoffs/2026-06-05-internal-reviewer-rehearsal.md`
4. `docs/current-state.md`

## Recommended skill / toolset

- `session-handoff` for recording the final human sign-off result.
- `test-driven-development` if a P0/P1 blocker needs code changes.
- Browser/manual walkthrough plus terminal logs for request ID capture.
