# Internal Preview Feedback Handoff

date: 2026-05-28
status: automated closure implemented; human reviewer walkthrough pending

## Goal

Close the next development slice around internal preview readiness: verify the current baseline, make the frontend typecheck command stable, record real smoke evidence, and leave a clear path for a human clinician/research reviewer walkthrough.

## Current State

- MVP-A evidence workbench remains internally walkable with default `deterministic` RAG provider and `keyword` retrieval.
- MVP-B `/network` mock path remains available for seed formula/herb analysis and citation/entity navigation.
- External providers `anthropic` and `opencode_go` remain opt-in smoke paths only.
- Structured claim grounding v3 is in place for external provider success paths, but it is not semantic fact verification.
- `pnpm typecheck` is now self-contained through `next typegen && tsc --noEmit`.
- No reviewer-approved Chinese PDF sample set has been provided yet.

## Completed In This Session

- Ran backend gates:
  - `ruff format --check app tests` passed.
  - `ruff check app tests` passed.
  - `mypy app` passed.
  - `pytest -q` passed with 247 tests.
- Ran frontend gates:
  - `pnpm test` passed with 113 tests.
  - `pnpm build` passed.
  - `pnpm e2e` passed with 2 Playwright Chromium specs.
  - `pnpm typecheck` initially failed when `.next/types` was absent; after fixing the script, it passed independently.
- Ran a PubMed parser smoke for `atopic dermatitis traditional Chinese medicine`, max 5 records; 5 records parsed.
- Ran default RAG API smoke; returned HTTP 200, `provider_name="deterministic"`, `retrieval.strategy="keyword"`, `grounding.status="skipped"`, one citation, and the required disclaimer.
- Added `docs/evaluations/2026-05-28-internal-review-feedback.md` as the internal-preview closure record.

## Still Open / Blocked

- Human reviewer walkthrough is still pending. Use `docs/checklists/internal-preview-smoke.md`.
- Reviewer-approved Chinese PDF quality smoke is still pending. Do not use protected or patient-identifiable files.
- Live LLM smoke is optional and requires local secrets; absence of keys is not a blocker.
- Full provider-native tool-use citation grounding, semantic hallucination rejection, network report export, and runtime JSON to database migration are intentionally deferred.

## Key Files And Artifacts

- `docs/current-state.md`
- `docs/checklists/internal-preview-smoke.md`
- `docs/checklists/llm-provider-smoke.md`
- `docs/evaluations/2026-05-27-real-data-smoke.md`
- `docs/evaluations/2026-05-28-internal-review-feedback.md`
- `docs/plans/2026-05-27-internal-preview-sprint.md`
- `frontend/package.json`

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

Run one real internal reviewer walkthrough using `docs/checklists/internal-preview-smoke.md`, record findings in `docs/evaluations/2026-05-28-internal-review-feedback.md`, and only fix P0/P1 issues before choosing the next development mainline.

## Recommended Reading Order

1. `docs/current-state.md`
2. `docs/evaluations/2026-05-28-internal-review-feedback.md`
3. `docs/checklists/internal-preview-smoke.md`
4. `docs/handoffs/2026-05-27-rag-grounding-hard-gate.md`
5. `docs/plans/2026-05-27-internal-preview-sprint.md`

## Recommended Skill / Toolset

- `test-driven-development` for P0/P1 fixes.
- `systematic-debugging` if any reviewer walkthrough path fails.
- `writing-plans` only after choosing the next mainline from feedback.
