# AFK Trial Hardening Handoff — 2026-06-05

date: 2026-06-05
status: implemented; focused verification passed; full local gate pending in current session
profile: default offline preview remains `deterministic` + `keyword` + JSON runtime

---

## Goal

Implement the non-human-dependent hardening slice before small-scale internal trial: preserve the current working-tree context, wire frontend calls through the existing backend token gate, improve PDF preview-window selection without changing extraction dependencies, and add automated token-profile smoke coverage.

## Implemented

- Added `frontend/lib/api/client.ts`.
  - Reads optional `NEXT_PUBLIC_QIYAN_ACCESS_TOKEN`.
  - Adds `X-Access-Token` to backend fetches when configured.
  - Preserves JSON `Content-Type` headers and avoids setting multipart `Content-Type` for PDF upload.
- Updated all frontend backend API helpers to use the token-aware wrapper:
  - literature search/detail/upload/parse/sync
  - RAG answer/export
  - network analyze/result/report/entities
  - RAG eval report
- Added backend token-profile smoke coverage in `backend/tests/test_token_profile_smoke.py`.
  - Missing token returns 401.
  - Matching token allows literature search, RAG answer, RAG Markdown export, network analyze/result/report.
- Improved PDF preview selection in `backend/app/services/literature.py`.
  - Keeps `pypdf-text-preview` as the default text-layer extractor.
  - Selects body-like windows using abstract/body signals such as `摘要`, `目的`, `方法`, `结果`, `结论`, `特应性皮炎`, and `atopic dermatitis`.
  - Skips obvious page numbers, reference-list starts, NUL-heavy header lines, and low-density table/formula-like lines.
  - Keeps the existing quality-warning copy byte-identical.
- Updated README, current-state, and reviewer checklist to document token profile and PDF preview-window behavior.

## Verification

Focused checks passed during implementation:

```powershell
cd frontend
node --import tsx --test tests\api-client.test.ts tests\literature-api.test.ts tests\literature-detail-api.test.ts tests\rag-api.test.ts tests\network-api.test.ts tests\network-entities-api.test.ts tests\evals-api.test.ts
```

Observed: 50 passed.

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_token_profile_smoke.py -q
```

Observed: 1 passed.

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_upload_api.py tests\test_pdf_quality_helpers.py -q
```

Observed: 43 passed.

Full local gate still needs to be run after final doc edits:

```powershell
.\scripts\verify-local.ps1
```

Run E2E only for reviewer/branch closeout:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

## Boundaries

- This does not complete formal clinician or research reviewer sign-off.
- This does not enable real LLM / real embedding / PostgreSQL by default.
- `NEXT_PUBLIC_QIYAN_ACCESS_TOKEN` is browser-visible and only suitable for internal preview shared-token gating, not production authentication.
- PDF OCR, table reconstruction, and commercial/license-reviewed extractors remain separate future spikes.

## Recommended Next Step

Run the full local gate, then preserve the changes as an AFK hardening commit. Formal reviewer sign-off should still be performed by real clinician and research reviewers using `docs/evaluations/2026-06-05-reviewer-feedback.md`.
