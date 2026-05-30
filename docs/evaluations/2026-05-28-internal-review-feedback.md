# Internal Review Feedback Record

date: 2026-05-28
status: automated baseline completed; human reviewer walkthrough pending

## Summary

This record implements the internal-preview closure slice for the current session. It separates verified automated evidence from human review items that still require a clinician/research reviewer and approved sample files.

## Automated Baseline

| Area | Command / flow | Result | Notes |
|---|---|---|---|
| Backend format | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` | Pass | 78 files already formatted |
| Backend lint | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` | Pass | All checks passed |
| Backend typing | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m mypy app` | Pass | 46 source files checked |
| Backend tests | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest -q` | Pass | 249 passed |
| Frontend unit tests | `cd frontend; pnpm test` | Pass | 120 passed |
| Frontend typecheck | `cd frontend; pnpm typecheck` | Pass after script fix | `typecheck` now runs `next typegen && tsc --noEmit` so it does not depend on a previous build |
| Frontend build | `cd frontend; pnpm build` | Pass | Next.js production build completed |
| Frontend e2e | `cd frontend; pnpm e2e` | Pass | 2 Playwright Chromium specs passed |

## API Smoke Evidence

### PubMed Parser

Command shape:

```powershell
cd backend
@'
from app.services.pubmed import PubmedClient
client = PubmedClient()
query = "atopic dermatitis traditional Chinese medicine"
pmids = client.esearch(query, max_results=5)
records = client.efetch(pmids)
print(pmids)
for record in records:
    print(record.pmid, record.year, record.title)
'@ | & .\.uv-test-venv\Scripts\python.exe -
```

Observed:

| Field | Value |
|---|---|
| Query | `atopic dermatitis traditional Chinese medicine` |
| Returned PMIDs | `42186710,42186432,42182585,42175694,42152434` |
| Parsed records | 5 |
| Runtime write | Not performed; parser/client smoke only |

Interpretation: the NCBI client/parser path is reachable and can parse current records. This does not prove curated search relevance or reviewer approval of every returned paper.

### Default RAG API

Command shape:

```powershell
cd backend
@'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
response = client.post("/api/rag/answer", json={"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1})
payload = response.json()
print(response.status_code)
print(payload["provider_name"])
print(payload["retrieval"]["strategy"])
print(payload["grounding"]["status"], payload["grounding"]["policy"])
print(payload["input_tokens"], payload["output_tokens"])
print(len(payload["citations"]))
print(payload["disclaimer"])
'@ | & .\.uv-test-venv\Scripts\python.exe -
```

Observed:

| Field | Value |
|---|---|
| HTTP status | 200 |
| `provider_name` | `deterministic` |
| `retrieval.strategy` | `keyword` |
| `grounding.status` | `skipped` |
| `grounding.policy` | `hard_block_v2_sentence_refs` |
| `input_tokens` / `output_tokens` | `null` / `null` |
| Citation count | 1 |
| Disclaimer | `非诊断结论、需结合临床。` |

Interpretation: the default internal-preview path remains offline and does not require external LLM credentials.

## Human Review Queue

| Priority | Area | Status | Required input | Notes |
|---|---|---|---|---|
| P0 | Full clinician/research walkthrough | Pending | 1 internal reviewer session | Use `docs/checklists/internal-preview-smoke.md`; do not mark complete from automated Playwright only |
| P1 | Reviewer-provided Chinese PDF sample probe | Completed for local API probe; formal reviewer approval pending | 2-3 approved text-layer Chinese PDFs | 2026-05-30 isolated upload + auto-parse probe covered four local reviewer PDFs without committing file bodies |
| P1 | PDF quality judgment | Completed for local API probe; formal reviewer approval pending | Same PDF sample set | Three samples are candidate acceptable for internal demo by local probe; one sample is acceptable only with explicit quality warning and original-PDF verification |
| P2 | Live OpenCode Go provider smoke | Optional | Local `QIYAN_OPENCODE_GO_API_KEY` | Keep opt-in; success does not mean default-live LLM is allowed |
| P2 | Live Anthropic provider smoke | Optional | Local `ANTHROPIC_API_KEY` | Keep opt-in; no key is not a blocker |

## Human Walkthrough Notes In Progress

| ID | Priority | Area | Finding | Status | Notes |
|---|---|---|---|---|---|
| IR-001 | P1 | `/network` mock path | During manual `/network` testing, entity chips were not found, and related literature / RAG / network links were not visible. | Fixed | Network chain responses now carry `related_entity_ids`; `/network` result cards render `EntityChips` and visible links to literature search, RAG question, and focused network analysis. `/literature?q=...` and `/rag?question=...` now consume those params. |
| IR-002 | P1 | PDF parsing quality | One of four reviewer-provided Chinese PDF samples showed numeric/table garbling in extracted preview text. | Fixed with warning | Local `pypdf` inspection identified `中医辨证治疗异位性皮炎临床观察_周海啸.pdf` as the clearest affected sample. Parse results now include `quality_warning` when extracted text contains likely NUL placeholder garbling, and the frontend shows an `抽取质量提示` asking reviewers to verify key numbers against the original PDF. |

### Reviewer PDF Samples In Progress

These PDF files were provided from a local review folder for manual/internal smoke. File bodies are not committed.

| File | Local observation | Initial quality judgment |
|---|---|---|
| `除湿糊剂治疗特应性皮炎的实验与临床观察_王琼 - 副本.pdf` | `pypdf` extracted text from first two pages with no NUL placeholders; Chinese text and numeric values were present. | Candidate acceptable, pending reviewer UI check |
| `健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf` | `pypdf` extracted text with no NUL placeholders, but included special/control characters and symbolized numeric punctuation such as `83−33%`. | Minor extraction-quality risk, pending reviewer judgment |
| `中药健脾止痒颗粒合铍宝消炎癣湿药膏治疗特应性皮炎疗效分析_杨瑛 - 副本.pdf` | `pypdf` extracted text from first two pages with no NUL placeholders; text is readable but has spacing/order noise. | Candidate acceptable, pending reviewer UI check |
| `中医辨证治疗异位性皮炎临床观察_周海啸.pdf` | `pypdf` extracted text had heavy numeric/table garbling; years and table values appeared as NUL placeholders. | Not acceptable as a clean internal demo PDF unless framed as fallback/known parser limitation |

## P1 Fix Follow-up

Implemented after the in-progress human walkthrough notes:

- `/network` result chains now include backend `related_entity_ids` so the frontend can render concrete entity chips instead of only plain text chain labels.
- `/network` result cards now expose visible actions: search related literature by target, open a prefilled RAG question, and focus the first related network entity.
- PDF parse results now expose an optional `quality_warning`; NUL-placeholder-heavy extracted text is flagged as possible numeric/table garbling instead of being presented as clean extraction.
- The PDF detail UI shows `抽取质量提示 ...` above the preview text while preserving the extracted preview for reviewer comparison.

## Feedback Triage Rules

| Label | Meaning | Example |
|---|---|---|
| P0 blocker | Prevents internal preview or creates medical/compliance misrepresentation | Missing disclaimer, API 500, broken RAG answer path |
| P1 demo issue | Does not block the demo but harms reviewer trust or understanding | Misleading PDF parse copy, stale provider metadata label |
| P2 follow-up | Useful next work but not needed for this internal preview closure | Network report export, PDF extractor replacement spike |
| Out of scope | Intentionally deferred for this phase | OCR, production auth, PostgreSQL, Neo4j, real embedding model |

## 2026-05-28 Implementation Follow-up

This follow-up reran the implementation-ready baseline after the internal-preview closure plan was accepted for execution.

| Area | Command / flow | Result | Notes |
|---|---|---|---|
| Git worktree | `git status --short` | Pass | Clean before documentation updates |
| Local reviewer PDF probe | `pypdf` read-only probe across `local-review-pdfs/` | Pass | Four local PDF samples were inspected without committing file bodies; `中医辨证治疗异位性皮炎临床观察_周海啸.pdf` triggers the new garbling warning condition |
| Backend format | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` | Pass | 79 files already formatted |
| Backend lint | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` | Pass | All checks passed |
| Backend typing | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m mypy app` | Pass | 46 source files checked |
| Backend tests | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest -q` | Pass | 249 passed |
| Frontend unit tests | `cd frontend; pnpm test` | Pass | 120 passed |
| Frontend typecheck | `cd frontend; pnpm typecheck` | Pass | `next typegen && tsc --noEmit` completed |
| Frontend build | `cd frontend; pnpm build` | Pass | Next.js production build completed |
| Frontend e2e | `cd frontend; pnpm e2e` | Pass | 2 Playwright Chromium specs passed; existing PDF fallback path emitted parser warnings but completed successfully |

No P0 blocker was found by the automated gates in this follow-up. The two manual P1 findings recorded as IR-001 and IR-002 were addressed; formal clinician/research reviewer sign-off can still be run separately if required.

## Current Outcome

- No P0 blocker was found in automated verification.
- One verification-process issue was found and fixed: `pnpm typecheck` depended on generated `.next/types` when run before `pnpm build`; the script now runs `next typegen` first.
- The 2026-05-28 implementation follow-up reconfirmed the full backend/frontend automated baseline.
- Manual P1 feedback on `/network` links and PDF garbling has been addressed; do not treat automated Playwright results alone as formal clinical/research reviewer sign-off.

## 2026-05-30 Internal Preview Closure Pass

This pass implemented the accepted internal-preview closure plan as far as possible from the local workspace. It reconfirmed the automated baseline and exercised the reviewer PDF samples through the real upload + auto-parse API path using isolated temp runtime/upload directories. PDF file bodies remain local-only and are not committed.

| Area | Command / flow | Result | Notes |
|---|---|---|---|
| Git worktree | `git status --short` | Pass with known untracked temp dir | Only `backend/.pytest-tmp/` was present before documentation edits |
| Backend format | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` | Pass | 79 files already formatted |
| Backend lint | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` | Pass | All checks passed |
| Backend typing | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m mypy app` | Pass | 46 source files checked |
| Backend tests | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest -q` | Pass | 251 passed |
| Frontend unit tests | `cd frontend; pnpm test` | Pass | 120 passed |
| Frontend typecheck | `cd frontend; pnpm typecheck` | Pass | `next typegen && tsc --noEmit` completed |
| Frontend build | `cd frontend; pnpm build` | Pass | Next.js production build completed |
| Frontend e2e | `cd frontend; pnpm e2e` | Pass | 2 Playwright Chromium specs passed |
| Reviewer PDF API probe | Isolated `TestClient` upload + `/api/uploads/pdf/auto-parse` for four local PDFs | Pass | No tracked runtime state or upload files were written |

### 2026-05-30 Reviewer PDF API Probe

The probe used isolated `UPLOAD_STORAGE_DIR`, `LITERATURE_RUNTIME_STATE_PATH`, `CHUNK_RUNTIME_STATE_PATH`, and `NETWORK_TASKS_RUNTIME_STATE_PATH` values. Each sample returned HTTP 201 from upload, HTTP 200 from auto-parse, and `pdf_parse_status="parsed"`.

| File | Extraction method | Quality warning | Probe judgment |
|---|---|---|---|
| `除湿糊剂治疗特应性皮炎的实验与临床观察_王琼 - 副本.pdf` | `pypdf-text-preview` | None | Candidate acceptable for internal demo |
| `健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf` | `pypdf-text-preview` | None | Candidate acceptable for internal demo |
| `中药健脾止痒颗粒合铍宝消炎癣湿药膏治疗特应性皮炎疗效分析_杨瑛 - 副本.pdf` | `pypdf-text-preview` | None | Candidate acceptable for internal demo |
| `中医辨证治疗异位性皮炎临床观察_周海啸.pdf` | `pypdf-text-preview` | `检测到抽取文本可能存在数字或表格乱码，请对照原始 PDF 核对关键数值。` | Acceptable only with explicit warning and original-PDF verification |

### 2026-05-30 Triage

| ID | Priority | Area | Finding | Status | Notes |
|---|---|---|---|---|---|
| IR-003 | P1 | Reviewer PDF samples | Local sample PDFs now complete the real upload + auto-parse API path in isolated state. | Closed | Three samples are candidate acceptable; one sample correctly surfaces the existing quality warning. No code change required. |
| IR-004 | P0 | Automated internal-preview baseline | Full backend/frontend gates stayed green after the previous P1 fixes. | Closed | No P0 blocker found by automated verification. |
| IR-005 | P0/P1 | Formal clinician/research reviewer sign-off | A live clinician/research reviewer session was not captured in this agent run. | Pending | Do not represent the automated closure as formal clinical/research sign-off. Use `docs/checklists/internal-preview-smoke.md` if a separate human session is required. |

### 2026-05-30 Outcome

- Automated internal-preview closure remains green.
- The local reviewer PDF sample set has been validated through the real backend upload/parse API path.
- No new P0/P1 code defect was found, so this pass only updates evidence and handoff documentation.
- Formal clinician/research sign-off remains pending unless a separate live reviewer session is performed and recorded.
