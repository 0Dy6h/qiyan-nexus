# 001: PDF Extractor Comparison

## Question

Given the four A5 Chinese AD PDF samples, when we compare the current `pypdf` text-layer extraction against `pdfplumber`, then can a lightweight extractor swap or layout-aware variant reduce `quality_warning` without adding OCR or changing the upload API contract?

## Scope

- Compare current production-shaped `pypdf` extraction with `pdfplumber` default/layout extraction.
- Use only local gitignored reviewer samples from `local-review-pdfs/` or `backend/uploads/`.
- Record metrics, not full article text.
- Do not add a production dependency or change `/api/uploads/pdf/auto-parse`.
- Do not evaluate OCR, table reconstruction models, or scanned PDF support.

## How To Run

```powershell
uv run --with pypdf==6.12.2 --with pdfplumber python .\spikes\001-pdf-extractor-comparison\compare_extractors.py
```

Outputs are written to:

- `spikes/001-pdf-extractor-comparison/results/pdf_extractor_comparison.json`
- `spikes/001-pdf-extractor-comparison/results/pdf_extractor_comparison.md`

## Verdict

## Verdict: PARTIAL

### What Worked

- The comparison script ran against all four A5 Chinese AD reviewer PDFs.
- `pdfplumber` extracted text from all four samples without new extraction failures.
- The three already-clean samples stayed clean under `pdfplumber_default` and `pdfplumber_layout`: 0 NUL bytes and no current `quality_warning`.
- `pdfplumber_default` produced more compact readable starts for some samples than the current middle-line `pypdf` preview window.

### What Didn't

- `pdfplumber` did not remove the embedded-font NUL problem in `cn-ad-formula-002`.
- On the known problem sample, NUL ratios were:
  - `pypdf_full`: 12.88%
  - `pypdf_current_middle_lines`: 14.59%
  - `pdfplumber_default`: 18.17%
  - `pdfplumber_layout`: 8.17%
- All extractor variants still exceed the current 5% warning threshold for `cn-ad-formula-002`, so `quality_warning` remains correct.
- `pdfplumber_layout` greatly expands extracted text and can dilute CJK density; for example `cn-ad-barrier-006` fell to 12.48% CJK and was flagged as `low_cjk_ratio` by this spike's heuristic.

### Surprises

- The layout-aware `pdfplumber` mode lowered the NUL ratio on the known problem sample by increasing text volume, not by decoding the missing characters. The raw NUL count stayed 805.
- The current `pypdf` middle-line filtering can move the preview into less useful regions for some samples; this is a preview-window selection issue, not a decoding-quality fix.

### Recommendation For The Real Build

- Do not add `pdfplumber` to the default backend dependency set for this spike.
- Keep the current `pypdf` text-layer path plus `quality_warning`.
- Treat embedded-font NUL garbling as a user-facing warning condition unless a future OCR or commercial/license-reviewed extractor spike proves a real improvement.
- If the next PDF slice is small, focus on preview-window selection rather than decoder replacement: prefer abstract/title/body-like lines before references and method-materials fragments.
