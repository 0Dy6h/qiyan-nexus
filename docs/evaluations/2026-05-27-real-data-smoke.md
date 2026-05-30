# Real Data Smoke Record

date: 2026-05-27
status: partial smoke completed

## Summary

This record captures what was actually checked in the local environment for the internal preview sprint. It does not claim production data readiness.

- PubMed E-utilities parser smoke: passed for 10 records.
- RAG default API shape smoke: passed for deterministic provider + keyword retrieval.
- Internal-preview browser smoke: passed with Playwright Chromium for literature, RAG, PDF upload fallback, RAG eval, and network mock paths.
- Local uploaded PDF artifact probe: completed; results show extraction quality risk and fallback cases.
- Curated reviewer-selected Chinese PDF smoke: pending, because no reviewer-approved PDF set was provided.
- Real LLM live smoke: pending local API keys; missing-key/default fallback remains the supported default path.

## PubMed Live Parser Smoke

Command shape:

```powershell
cd backend
@'
from app.services.pubmed import PubmedClient
client = PubmedClient()
query = "atopic dermatitis traditional Chinese medicine"
pmids = client.esearch(query, max_results=10)
records = client.efetch(pmids)
print(pmids)
for record in records:
    print(record.pmid, record.year, record.title)
'@ | & .\.uv-test-venv\Scripts\python.exe -
```

Observed result:

| Field | Value |
|---|---|
| Query | `atopic dermatitis traditional Chinese medicine` |
| Returned PMIDs | `42186710,42186432,42182585,42175694,42152434,42148088,42113767,42098749,42095287,42085844` |
| Parsed records | 10 |
| Network/API result | passed |
| Runtime write | not performed in this smoke; parser/client only |

Sample parsed titles:

| PMID | Year | Title |
|---|---:|---|
| 42186710 | 2026 | Comment on 'Effects of Acupuncture as a Therapeutic Intervention Targeting Both Skin and Gastrointestinal Symptoms in Patients With Atopic D... |
| 42186432 | 2026 | Characteristics and Risk Factors of Dupilumab-Associated Head and Neck Dermatitis in Patients With Atopic Dermatitis. |
| 42182585 | 2026 | Advances in Yupingfeng San Research: Multi-Target Mechanisms and Clinical Evidence. |
| 42175694 | 2026 | Identification of Lipid Metabolism-Related Gene GM2A as a Potential Biomarker in Atopic Dermatitis by Combining Weighted Gene Co-Expression... |
| 42098749 | 2026 | Research progress on the mechanisms of Panax ginseng and its active components in maintaining skin homeostasis and disease intervention. |

Interpretation:

- The current PubMed client/parser can reach NCBI and parse current records in this environment.
- The query is broad and returns non-TCM AD-adjacent results as well as TCM/herbal results, so product demos should still present PubMed results as live literature candidates requiring human review.
- This smoke did not mutate seed data and did not validate deduplication/user-facing search after runtime sync.

## RAG Default API Shape Smoke

Command shape:

```powershell
cd backend
@'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
response = client.post("/api/rag/answer", json={"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1})
print(response.status_code)
print(response.json())
'@ | & .\.uv-test-venv\Scripts\python.exe -
```

Observed result:

| Field | Value |
|---|---|
| HTTP status | 200 |
| `provider_name` | `deterministic` |
| `retrieval.strategy` | `keyword` |
| `input_tokens` / `output_tokens` | `null` / `null` |
| disclaimer | `非诊断结论、需结合临床。` |

Interpretation:

- The internal preview default path does not need external LLM credentials.
- Token fields correctly remain absent/null for deterministic provider.

## Internal Preview Browser Smoke

Command shape:

```powershell
cd frontend
pnpm e2e
```

Observed result:

| Field | Value |
|---|---|
| Browser | Playwright Chromium 148 headless |
| Specs | `main-path.spec.ts`, `internal-preview.spec.ts` |
| Result | 2 passed |
| Covered paths | `/literature`, `/literature/cn-ad-gbs-001`, `/rag`, `/evals/rag-ad`, `/network` |
| Runtime isolation | e2e backend uses temp literature, chunk, network task, vector cache, and upload paths |

Interpretation:

- The internal preview UI can run the main literature → detail → RAG → citation/disclaimer path in-browser.
- The PDF path was tested with a generated minimal PDF fixture, not a curated Chinese article. It exercised upload, auto-parse, preview link, and honest `file-metadata-placeholder` fallback behavior.
- The RAG eval page rendered the 50-question summary surface.
- The network mock task completed and rendered the seed 「成分-靶点-通路-疾病」 chain with disclaimer.

## Local PDF Artifact Probe

This probe only inspected existing files under `backend/uploads/`. Their provenance is not treated as curated real-data evidence.

Command shape:

```powershell
cd backend
@'
from pathlib import Path
from pypdf import PdfReader
for path in sorted(Path("uploads").glob("*.pdf")):
    try:
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        print(path.name, path.stat().st_size, len(reader.pages), len(text), repr(text[:80]))
    except Exception as exc:
        print(path.name, path.stat().st_size, type(exc).__name__, exc)
'@ | & .\.uv-test-venv\Scripts\python.exe -
```

Observed result:

| File | Bytes | Pages | Extracted text length | Result |
|---|---:|---:|---:|---|
| `pdf-cn-ad-gbs-001-43-pdf.pdf` | 321952 | 2 | 6411 | Text layer exists, but preview contains NUL/garbling noise |
| `pdf-cn-ad-gbs-001-cc-1-pdf.pdf` | 125901 | 2 | 0 | No extractable text layer |
| `pdf-cn-ad-gbs-001-cc-pdf.pdf` | 4438025 | n/a | n/a | Encrypted/AES path requires `cryptography>=3.1` |
| `pdf-cn-ad-gbs-001-pdf.pdf` | 282876 | 2 | 5730 | Text layer exists, but preview contains heavy NUL/garbling noise |
| `pdf-cn-ad-gbs-001-review-pdf.pdf` | 24 | n/a | n/a | Invalid/truncated PDF |

Interpretation:

- The current `pypdf` preview path is useful but not sufficient for high-quality Chinese PDF review.
- The fallback behavior is necessary and should remain honest.
- Do not add OCR or encrypted-PDF handling inside this internal-preview sprint.
- A reviewer-selected text-layer Chinese PDF set is still needed before claiming demo-quality PDF extraction.

## Pending Manual Smoke

| Item | Status | Needed input |
|---|---|---|
| Curated Chinese PDF upload | pending | 2-3 reviewer-approved text-layer Chinese PDFs |
| OpenCode Go live provider | pending | local `QIYAN_OPENCODE_GO_API_KEY` |
| Anthropic live provider | pending | local `ANTHROPIC_API_KEY` |
| Full browser demo checklist | passed by automated local smoke; pending human reviewer walkthrough | reviewer session using `docs/checklists/internal-preview-smoke.md` |

## 2026-05-28 Follow-up

- PubMed parser/client smoke reran with `max_results=5` for `atopic dermatitis traditional Chinese medicine`; 5 records parsed and no runtime write was performed.
- Default RAG API smoke returned HTTP 200, `provider_name="deterministic"`, `retrieval.strategy="keyword"`, `grounding.status="skipped"`, one citation, token fields `null`, and disclaimer `非诊断结论、需结合临床。`
- Full automated backend/frontend baseline passed; details are recorded in `docs/evaluations/2026-05-28-internal-review-feedback.md`.
- Human reviewer walkthrough and reviewer-approved Chinese PDF smoke remain pending.

## Next Recommendation

For the next iteration, pick one of:

- PDF quality path: collect 2-3 approved Chinese PDFs and decide whether `pypdf` is acceptable or needs a replacement extractor.
- LLM trust path: implement citation grounding and out-of-citation rejection before any default live-provider demo.
- Data path: run `/api/literature/sync` into runtime with a narrow query and verify user-facing `/literature` search behavior.
