# Semantic Grounding Gate Handoff

date: 2026-05-30
status: slice implemented and verified end-to-end (backend + frontend); changes NOT committed (intentional dirty worktree, matching prior session pattern)

## Goal

Finish the in-progress **semantic grounding gate** slice — the layer that runs *after* the existing structural / tool / evidence-ID grounding and rejects external-provider claims whose text is not semantically supported by the chunk they cite. Make the slice coherent end-to-end: backend was already written but uncommitted and had one broken contract test + zero frontend surfacing.

## What the slice does

After structural grounding passes for an external provider (`anthropic` / `opencode_go`), each claim is scored by **cosine similarity** against its cited chunk text (`quote`, falling back to `snippet`). If any claim's score is below the threshold, the answer is blocked:

- `grounding.status="blocked"`, `grounding.blocked_reason="semantic_low_support"`
- `grounding.semantic_threshold`, `grounding.min_semantic_score`, and per-claim `structured_claims[].semantic_score` are all returned for inspection.

Threshold: `QIYAN_GROUNDING_SEMANTIC_THRESHOLD` (default `0.40`; `<=0` disables → `semantic_threshold=None`, no scoring).

Gate applies **only** to `anthropic` / `opencode_go`. `deterministic` and external→deterministic fallback paths still `status="skipped"`, unchanged.

**Important caveat:** the default `hashing` embedding backend makes the score a **lexical-overlap proxy**, NOT true semantics. `QIYAN_EMBEDDING_BACKEND="bge"` (BAAI/bge-small-zh-v1.5) upgrades it in place. The default threshold `0.40` was tuned against the hashing proxy, not bge.

## What I found on arrival

The backend implementation was already written but uncommitted (from a prior unfinished session). Two gaps:

1. **Broken contract test:** `backend/tests/test_rag_api.py` asserts the *full* `grounding` dict and failed because the slice added two fields it didn't account for.
2. **Frontend completely untouched:** the slice was backend-only. New schema fields were not in `frontend/lib/api/rag.ts`, not in Markdown export, not surfaced on `/rag`.

## Completed in this session

Backend fix:
- `backend/tests/test_rag_api.py` — added `semantic_threshold: None` + `min_semantic_score: None` to the expected deterministic-skip grounding dict.

Frontend surfacing (to make the slice coherent end-to-end):
- `frontend/lib/api/rag.ts` — added `semantic_score?` to `GroundedClaim`; `semantic_threshold?` + `min_semantic_score?` to `GroundingMetadata`.
- `frontend/lib/rag-export.ts` — two new Markdown lines: `语义阈值`（threshold or 未启用）and `最小语义支持度`（min score as % or 未计算）. Added `formatSemanticThreshold` / `formatSemanticScore` helpers.
- `frontend/components/RagAnswerClient.tsx` — two new metadata rows (语义阈值 / 最小语义支持度) + `semantic_low_support` → "存在与引用证据语义支持度过低的 claim" blocked-reason copy.
- `frontend/tests/rag-export.test.ts` — 2 new tests (blocked semantic gate details; disabled-when-null).

Reverted generated `frontend/next-env.d.ts` churn (build flips dev↔build route-types import) to keep diff surgical.

## Pre-existing uncommitted work (NOT written this session, but part of the slice)

These were already on disk when the session started and remain uncommitted:
- `backend/data/evals/grounding_semantic_pairs.json` (untracked) — 20 labeled (claim, chunk, supported) pairs, 10 faithful + 10 hallucinated twins.
- `backend/tests/test_grounding_semantic.py` (untracked) — unit + separation-eval tests.
- `backend/app/services/grounding.py` — `score_claim_support`, `_reference_text_by_ref`, semantic gate in `evaluate_answer_grounding`.
- `backend/app/services/eval.py` — `run_grounding_semantic_separation` (confusion matrix + paired separation).
- `backend/app/schemas/eval.py` — `GroundingSemanticPair` + loader.
- `backend/app/schemas/rag.py` — new grounding/claim fields.
- `backend/app/core/config.py`, `backend/.env.example` — threshold setting.
- `backend/app/services/rag.py` — wires backend + threshold into the answer path.
- `backend/tests/test_rag_service.py` — semantic gate block/disable tests; updated existing opencode/anthropic native-claim tests to use realistic Chinese claim text (so they pass the new semantic gate).
- `README.md`, `docs/current-state.md` — documented the gate + lexical-proxy caveat.

## Verification

Backend (`backend/.venv/Scripts/python.exe`):
```
ruff format --check app tests   → 81 files already formatted
ruff check app tests            → All checks passed!
mypy app                        → no issues in 46 source files
pytest -q                       → 272 passed
```

Frontend:
```
pnpm test       → 129 passed (added 2)
pnpm typecheck  → clean
pnpm build      → success, all routes built
```

## Still open / next steps

1. **Commit** — nothing is committed yet. Suggested split: (a) backend semantic-grounding slice, (b) frontend surfacing. Or one bundled commit. The two untracked files must be `git add`-ed.
2. **`bge` re-calibration (recommended main thread)** — the `0.40` threshold is tuned against the hashing lexical proxy. Run `run_grounding_semantic_separation(threshold, backend_name="bge")` to re-measure separation with real embeddings and re-tune the default. `bge` separates faithful/hallucinated far more cleanly; hashing lets a few high-overlap fabrications slip through (see the `>= 7 rejected` / `<= 3 false-accepted` tolerances in `test_grounding_semantic.py`).
3. Other candidate next threads (from `docs/current-state.md`): network report export backend API (PDF/Word), runtime JSON → SQLite/Postgres spike, PDF extraction-quality/OCR spike.
4. **Anthropic stays deferred** — team has no Anthropic key; do not schedule Anthropic live smoke. `opencode_go` is the prioritized live provider.

## Key files

- `backend/app/services/grounding.py` — `score_claim_support`, semantic gate
- `backend/app/services/eval.py` — `run_grounding_semantic_separation`
- `backend/data/evals/grounding_semantic_pairs.json` — labeled fixture
- `backend/tests/test_grounding_semantic.py` — gate + separation tests
- `frontend/lib/api/rag.ts`, `frontend/lib/rag-export.ts`, `frontend/components/RagAnswerClient.tsx`

## Recommended reading order

1. This handoff
2. `docs/current-state.md` (updated "next steps" section)
3. `backend/app/services/grounding.py` (gate logic)
4. `backend/tests/test_grounding_semantic.py` (what "separation" means on hashing vs bge)
5. `backend/data/evals/grounding_semantic_pairs.json` (the labeled corpus)
