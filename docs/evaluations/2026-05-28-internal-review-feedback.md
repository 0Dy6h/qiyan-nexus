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
| Backend tests | `cd backend; & .\.uv-test-venv\Scripts\python.exe -m pytest -q` | Pass | 247 passed |
| Frontend unit tests | `cd frontend; pnpm test` | Pass | 113 passed |
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
| P1 | Reviewer-approved Chinese PDF samples | Pending | 2-3 approved text-layer Chinese PDFs | Do not commit file bodies unless licensing is explicitly cleared |
| P1 | PDF quality judgment | Pending | Same PDF sample set | Decide whether `pypdf` preview is acceptable for internal demo or should stay framed as fallback-only |
| P2 | Live OpenCode Go provider smoke | Optional | Local `QIYAN_OPENCODE_GO_API_KEY` | Keep opt-in; success does not mean default-live LLM is allowed |
| P2 | Live Anthropic provider smoke | Optional | Local `ANTHROPIC_API_KEY` | Keep opt-in; no key is not a blocker |

## Feedback Triage Rules

| Label | Meaning | Example |
|---|---|---|
| P0 blocker | Prevents internal preview or creates medical/compliance misrepresentation | Missing disclaimer, API 500, broken RAG answer path |
| P1 demo issue | Does not block the demo but harms reviewer trust or understanding | Misleading PDF parse copy, stale provider metadata label |
| P2 follow-up | Useful next work but not needed for this internal preview closure | Network report export, PDF extractor replacement spike |
| Out of scope | Intentionally deferred for this phase | OCR, production auth, PostgreSQL, Neo4j, real embedding model |

## Current Outcome

- No P0 blocker was found in automated verification.
- One verification-process issue was found and fixed: `pnpm typecheck` depended on generated `.next/types` when run before `pnpm build`; the script now runs `next typegen` first.
- Human reviewer feedback and reviewer-approved PDF quality evidence are still pending.
