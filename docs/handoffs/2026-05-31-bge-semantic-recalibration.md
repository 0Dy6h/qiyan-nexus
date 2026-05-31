# BGE Semantic Grounding Recalibration Handoff

date: 2026-05-31
status: hashing baseline evaluated; BGE evaluation blocked by network; recommendations provided

## Goal

Validate the semantic grounding gate's performance on the BGE (BAAI/bge-small-zh-v1.5) backend and recalibrate the threshold if needed. The current default threshold (0.40) was tuned against the hashing lexical-overlap proxy, not true semantic embeddings.

## Context

The semantic grounding gate (implemented in `backend/app/services/grounding.py`) scores each claim against its cited chunk text using cosine similarity. If any claim's score falls below the threshold, the answer is blocked with `grounding.status="blocked"` and `blocked_reason="semantic_low_support"`.

**Current limitation**: The default `HashingEmbeddingBackend` is a deterministic lexical-overlap proxy (128-dim, md5-based), not true semantics. This allows high-lexical-overlap fabrications to slip through (test suite tolerates ≤3 false accepts out of 10 hallucinations).

**BGE upgrade path**: Setting `QIYAN_EMBEDDING_BACKEND=bge` upgrades to true semantic embeddings (512-dim, BAAI/bge-small-zh-v1.5) in place, with no code changes required.

## What Was Completed

### Hashing Baseline Evaluation

Ran `run_grounding_semantic_separation(threshold=0.40, backend_name="hashing")` against the 20-pair labeled fixture (`backend/data/evals/grounding_semantic_pairs.json`):

**Results**:
- **Faithful claims**: 10/10 accepted (0 false rejects) ✓
- **Hallucinated claims**: 7/10 rejected (3 false accepts) ⚠
- **Paired separation**: 10/10 (100%) — every faithful claim outscores its hallucinated twin ✓
- **Score distribution**:
  - Min faithful score: 0.503
  - Max hallucinated score: 0.762
  - Gap: -0.259 (OVERLAP — some hallucinations score higher than some faithful claims)

**Interpretation**:
- The hashing backend is **conservative** (zero false rejects) but **permissive** (3 false accepts).
- The 3 false accepts are high-lexical-overlap fabrications (e.g., "该复方已被国家药监局批准" cites a chunk mentioning "中药复方" but fabricates regulatory approval).
- Paired separation is perfect (100%), meaning within each (faithful, hallucinated) twin pair, the faithful claim always scores higher.
- Score distributions overlap globally, but paired comparisons separate cleanly.

### BGE Evaluation Attempt

Attempted to run `run_grounding_semantic_separation(threshold=0.40, backend_name="bge")` but encountered network timeout when downloading the BGE model from Hugging Face:

```
'[WinError 10060] 由于连接方在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败。'
thrown while requesting HEAD https://huggingface.co/BAAI/bge-small-zh-v1.5/resolve/main/./modules.json
```

**Root cause**: Local network requires proxy (`http://172.26.0.1:7897`) for Hugging Face access, but the `sentence-transformers` library's model download does not respect `HTTPS_PROXY` environment variable consistently.

**Workaround attempted**: Set `HF_ENDPOINT=https://hf-mirror.com` (China mirror), but connection still timed out.

### Evaluation Scripts Created

1. **`backend/scripts/eval_bge_separation.py`** — Full hashing vs BGE comparison script (requires network)
2. **`backend/scripts/eval_hashing_baseline.py`** — Hashing-only evaluation with BGE expectations analysis (works offline)

Both scripts output:
- Confusion matrix (TP/FP/TN/FN)
- Score distribution (min faithful, max hallucinated, gap)
- Paired separation percentage
- Threshold recommendations

## Key Findings

### Hashing Backend (Current Default)

| Metric | Value | Assessment |
|--------|-------|------------|
| False rejects (faithful blocked) | 0/10 | ✓ Conservative, safe |
| False accepts (hallucinated passed) | 3/10 | ⚠ Lexical overlap limitation |
| Paired separation | 10/10 (100%) | ✓ Perfect within pairs |
| Score gap | -0.259 | ⚠ Distributions overlap globally |
| Threshold 0.40 | Appropriate | Conservative for hashing |

### BGE Backend (Expected Performance)

Based on test suite comments (`backend/tests/test_grounding_semantic.py`) and prior handoff documentation:

| Metric | Expected | Rationale |
|--------|----------|-----------|
| False rejects | 0/10 | Threshold 0.40 is conservative; BGE should maintain this |
| False accepts | <3/10 | True semantics should separate fabrications more cleanly |
| Paired separation | 10/10 (100%) | Should maintain or improve |
| Score gap | Positive | BGE should create clean separation (no overlap) |
| Recommended threshold | 0.50-0.60 | Likely can tighten without false rejects |

## Threshold Recommendation

### For Hashing Backend (Current)
**Keep threshold at 0.40** — it's conservative (zero false rejects) and acceptable for a lexical proxy. The 3 false accepts are a known limitation documented in the test suite.

### For BGE Backend (When Available)
**Run full BGE evaluation first**, then:

1. If BGE achieves **zero false rejects and <3 false accepts**:
   - Tighten threshold to `(min_faithful_score + max_hallucinated_score) / 2`
   - Expected range: 0.50-0.60
   - Update `backend/app/core/config.py` default if BGE becomes the production backend

2. If BGE achieves **zero false rejects and zero false accepts**:
   - Perfect separation! Set threshold to `min_faithful_score`
   - Document this as production-ready

3. If BGE still has **false accepts**:
   - Keep threshold at 0.40 (conservative)
   - Consider expanding the labeled fixture or using a stronger model (bge-large)

## Still Open / Blocked

1. **BGE evaluation blocked by network** — requires either:
   - Working proxy configuration for `sentence-transformers` downloads
   - Manual model download to `~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/`
   - Running evaluation on a machine with direct Hugging Face access

2. **Threshold recalibration deferred** — cannot recommend a BGE-specific threshold without actual BGE scores

3. **Production enablement deferred** — semantic grounding gate remains opt-in (`QIYAN_GROUNDING_SEMANTIC_THRESHOLD` must be set explicitly) until BGE evaluation confirms production readiness

## Next Steps

### Immediate (When Network Available)
1. Run BGE evaluation:
   ```bash
   cd backend
   HTTPS_PROXY=http://172.26.0.1:7897 .venv/Scripts/python.exe scripts/eval_bge_separation.py
   ```
2. Record BGE confusion matrix, score distribution, and paired separation
3. Compare BGE vs hashing false accept rates
4. Update this handoff with BGE results

### If BGE Evaluation Succeeds
1. If BGE separation is clean (≤1 false accept):
   - Recommend new threshold (likely 0.50-0.60)
   - Update `backend/.env.example` with BGE-specific threshold guidance
   - Update `docs/current-state.md` to mark BGE as validated
2. If BGE separation is not significantly better than hashing:
   - Document findings and keep hashing as default
   - Consider alternative models (bge-large, bge-m3) or threshold tuning

### Downstream Work (After BGE Validation)
1. **C1 OpenCode Go live smoke** — test real LLM with semantic grounding enabled
2. **C2 Citation grounding** — tool-use enforcement (requires C1 complete)
3. **Production enablement** — default-enable semantic grounding if BGE validates

## Key Files

- `backend/app/services/grounding.py` — `score_claim_support()`, semantic gate logic
- `backend/app/services/eval.py` — `run_grounding_semantic_separation()`
- `backend/app/services/retrieval/embedding.py` — `HashingEmbeddingBackend`, `SentenceTransformerEmbeddingBackend`
- `backend/data/evals/grounding_semantic_pairs.json` — 20-pair labeled fixture
- `backend/tests/test_grounding_semantic.py` — Separation eval tests (hashing baseline)
- `backend/scripts/eval_bge_separation.py` — Full comparison script (requires network)
- `backend/scripts/eval_hashing_baseline.py` — Offline hashing evaluation

## Verification

Hashing baseline evaluation passed:
```bash
cd backend
.venv/Scripts/python.exe scripts/eval_hashing_baseline.py
# Output: 0 false rejects, 3 false accepts, 100% paired separation
```

BGE evaluation not yet run (network blocked).

## Recommended Reading Order

1. This handoff
2. `backend/app/services/grounding.py` — semantic scoring implementation
3. `backend/tests/test_grounding_semantic.py` — test expectations
4. `backend/data/evals/grounding_semantic_pairs.json` — labeled corpus
5. `backend/scripts/eval_hashing_baseline.py` — evaluation script output

## Recommended Skill / Toolset

- Network troubleshooting for Hugging Face model downloads
- Manual model download and cache placement if proxy fails
- Python evaluation scripting for threshold tuning
- Statistical analysis of score distributions (if expanding the labeled fixture)
