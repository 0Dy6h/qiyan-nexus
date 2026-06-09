# Formal Review Preflight Refresh Handoff — 2026-06-06

date: 2026-06-06  
status: technical preflight refreshed; formal human sign-off still pending  
profile: default offline preview (`deterministic` provider + `keyword` retrieval + JSON runtime)

---

## Goal

Execute Phase 0 of `.hermes/plans/2026-06-06_132821-formal-reviewer-signoff-and-trial-readiness.md`: refresh the technical gate and evidence package immediately before formal clinician/research reviewer walkthroughs.

## Current State

- Branch: `feat/multilingual-bge-m3-backend`
- Base commit used for technical refresh: `a723472`
- Latest verification rerun used the engineering pre-review closeout worktree, including record-origin labels, Windows smoke compatibility hardening, stale PubMed-view documentation updates, and the legacy `record_origin` repository regression test.
- Formal reviewer packet remains ready at `docs/evaluations/2026-06-05-reviewer-feedback.md`.
- Clinician reviewer and research reviewer sections are still blank and must be filled by real reviewers.

## Verification Completed

Passed:

```powershell
.\scripts\verify-local.ps1
```

Observed:

- backend `ruff format --check`: pass
- backend `ruff check`: pass
- backend `mypy app`: pass
- backend `pytest -q`: `505 passed, 1 skipped`
- frontend `pnpm test`: `168 passed`
- frontend `pnpm typecheck`: pass
- frontend `pnpm build`: pass

Passed:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

Observed:

- same backend/frontend gates passed
- Playwright open-mode E2E: `4 passed`

Passed:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

Observed:

- same backend/frontend gates passed
- Playwright shared-token E2E: `4 passed`

Passed:

```powershell
.\scripts\collect-internal-preview-evidence.ps1
```

Generated local evidence package:

```text
.tmp/internal-preview-evidence/20260606-152844/
```

Evidence files:

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

Evidence summary:

- open profile: passed, 12 flows, 12 request IDs.
- shared-token profile: passed, 12 flows, 12 request IDs.
- covered flows: health, literature all/PubMed/CNKI/uploaded-PDF filter, PDF upload + auto-parse, RAG answer/export, network analyze/result/report.
- access token value was intentionally omitted.

## Windows PowerShell Compatibility Follow-up

After a user attempted to run:

```powershell
.\scripts\smoke-internal-preview.ps1
```

from Windows PowerShell, the script failed before execution with parser errors around the Chinese default PDF path and Markdown table lines. Root cause: Windows PowerShell 5.1 can misread UTF-8-without-BOM `.ps1` files as ANSI; the UTF-8 Chinese bytes can be interpreted as quote-like characters, which breaks string parsing. After that was fixed, two more Windows PowerShell 5.1 compatibility issues appeared: `Invoke-RestMethod` did not support `-ResponseHeadersVariable` / `-StatusCodeVariable`, and response content needed explicit UTF-8 decoding for Chinese disclaimer comparisons.

Implemented:

- `scripts/smoke-internal-preview.ps1` no longer embeds Chinese strings in source for its default path/query/assertion values.
- Default `-PdfPath` is now empty; the script auto-selects a PDF under `local-review-pdfs/`, while still supporting explicit `-PdfPath`.
- Chinese query/disclaimer/test strings are constructed from Unicode code points at runtime.
- HTTP requests use `Invoke-WebRequest -UseBasicParsing` with explicit UTF-8 request/response handling so the script works on both Windows PowerShell 5.1 and PowerShell 7.
- Markdown evidence line building now uses `[void]$lines.Add(...)`, avoiding noisy pipeline parsing differences.
- `frontend/tests/internal-preview-ops-source.test.ts` was updated to lock the compatibility behavior.

Verification:

- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-internal-preview.ps1 -BackendUrl http://127.0.0.1:8010` passed against an isolated preview on backend port `8010`.
- `cd frontend; node --import tsx --test tests\internal-preview-ops-source.test.ts` passed.
- `.\scripts\collect-internal-preview-evidence.ps1` passed after the hardening and generated `.tmp/internal-preview-evidence/20260606-152844/`.

## Literature Source Credibility Follow-up

During pre-review, the user noticed that literature titles shown on `http://127.0.0.1:3000/literature` could not be found on external websites. Investigation confirmed that the tracked seed corpus intentionally contains synthetic/curated demonstration records, including `example.org` citation URLs and PubMed-looking sample IDs. The product risk was that the UI could make these records look like externally verifiable real CNKI/PubMed articles.

Classified as P1 pre-review credibility issue and fixed before formal reviewer walkthrough:

- Added `record_origin` to `LiteratureItem` API responses.
- Repository readers infer legacy/runtime records as:
  - `seed_sample` for tracked synthetic seed records.
  - `pubmed_live` when source is `PubMed live sync`.
- PubMed sync writes `record_origin="pubmed_live"` for new/updated live records.
- `/literature` result cards now show `记录来源 演示样本` or `记录来源 PubMed 实时同步`.
- `/literature/[id]` detail metadata shows the same `记录来源`.
- PubMed sync result cards show the record origin.
- The PubMed filter label changed from `PubMed 实时` to `PubMed 记录`.
- The PubMed banner now says `PubMed 记录（含演示 seed）` and explicitly states that seed entries must not be treated as externally searchable real literature.

Verification:

- Backend focused tests: `27 passed, 1 skipped`.
- Frontend focused tests: `23 passed`.
- `.\scripts\verify-local.ps1`: passed (`505 passed, 1 skipped`; frontend `168 passed`; typecheck/build passed).
- `cd frontend; pnpm e2e`: passed (`4 passed`).

## Documentation Updated

Updated:

- `docs/evaluations/2026-06-05-reviewer-feedback.md`
  - Added current technical refresh commit `a723472`.
  - Updated frontend URL to `http://127.0.0.1:3000`.
  - Added state backend `json`.
  - Recorded open and shared-token profile verification.
  - Recorded evidence package path and smoke summary.
  - Preserved the warning that automated tests/internal rehearsal/evidence packs do not replace formal reviewer sign-off.

Added:

- `.hermes/plans/2026-06-06_132821-formal-reviewer-signoff-and-trial-readiness.md`
  - Formal reviewer execution plan.

## Still Open

- Formal clinician reviewer walkthrough is pending.
- Formal research reviewer walkthrough is pending.
- Reviewer A / Reviewer B fields in `docs/evaluations/2026-06-05-reviewer-feedback.md` remain blank.
- Consolidated triage remains empty until reviewer feedback exists.
- Closeout decision remains empty.

## Recommended Next Step

Run the real reviewer sessions using:

- `docs/checklists/internal-preview-reviewer-walkthrough.md`
- `docs/evaluations/2026-06-05-reviewer-feedback.md`
- `.tmp/internal-preview-evidence/20260606-152844/evidence-summary.md` as the latest technical artifact

If either reviewer records any P0/P1 issue, fix only that blocker, rerun the affected focused tests, then rerun:

```powershell
.\scripts\verify-local.ps1
```

Before marking sign-off complete, rerun:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

If access-token wiring is touched, also rerun:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

## Boundaries

- This does not complete formal clinician/research sign-off.
- This does not enable real LLM, real embedding, PostgreSQL, pgvector retrieval, OCR, or production authentication by default.
- `.tmp/internal-preview-evidence/20260606-152844/` is a local technical artifact and should not be committed.
- Shared-token profile remains an internal preview gate only, not production auth/RBAC.
