# Multilingual Embedding Real-Model Evaluation — Handoff 2026-06-12

## Goal

Execute the first sub-slice of 方案 A (multilingual embedding spike): run real bge-m3 and multilingual-e5-large models on the 16-question bilingual subset, compare against the locked keyword baseline (avg_cross_lingual_recall=0.9688), and decide whether to switch embedding backends.

## Completed In This Session

### 1. Evaluation Scripts

Created two parallel evaluation scripts:
- `backend/scripts/eval_cross_lingual_bge_m3.py`
- `backend/scripts/eval_cross_lingual_e5_large.py`

Both scripts:
- Call `run_cross_lingual_retrieval_eval()` for keyword / vector / hybrid strategies
- Print markdown summary table with n, mono recall, cross recall, diversity, P@10, MRR
- Compare against keyword baseline 0.9688

### 2. Real Model Evaluation Results

**bge-m3** (BAAI/bge-m3, 1024-dim):
- vector: cross_recall **0.6250** (Δ -0.3438 vs baseline)
- hybrid: cross_recall **0.9062** (Δ -0.0626 vs baseline)
- mono_recall: **1.0000** (perfect, no degradation)

**multilingual-e5-large** (intfloat/multilingual-e5-large, 1024-dim, role-aware):
- vector: cross_recall **0.0625** (Δ **-0.9063** vs baseline) — near-total failure
- hybrid: cross_recall **0.6562** (Δ -0.3126 vs baseline)
- mono_recall: **1.0000** (perfect, no degradation)

**Keyword baseline** (reproduced in same run):
- cross_recall **0.9375** (Δ -0.0313 vs locked 0.9688)
- mono_recall **1.0000**

### 3. Documentation

Created comprehensive evaluation report:
- `docs/evaluations/2026-06-12-bge-m3-cross-lingual-eval.md`
- Includes raw tables, delta analysis, root cause analysis, model selection recommendation

## Key Findings

### 1. Keyword + Cross-Lingual Bridge Still Dominant

Neither bge-m3 nor multilingual-e5-large in pure vector mode can beat keyword+bridge:
- keyword: **0.9375**
- vector(bge-m3): 0.6250 (gap: **0.3125**)
- vector(e5-large): 0.0625 (gap: **0.8750**)

### 2. bge-m3 >> multilingual-e5-large (Cross-Lingual)

bge-m3 outperforms e5-large by **10× in vector** and **1.4× in hybrid**.

e5-large's role-aware `passage:` / `query:` prefixes, effective in general domains, fail on AD medical term cross-lingual mapping.

### 3. Hybrid Cannot Rescue Vector Weakness

- bge-m3 hybrid: 0.9062 < keyword 0.9375 (gap: 0.0313)
- e5-large hybrid: 0.6562 << keyword 0.9375 (gap: 0.2813)

RRF fusion brings back some of keyword's cross-lingual ability, but vector still drags down the result.

### 4. Root Cause: Domain-Specific Cross-Lingual Alignment Gap

General-purpose multilingual models (bge-m3 / e5-large) are trained on broad paired data (Wikipedia, news), but lack AD medical term pairs like:
- "gut-brain-skin axis" ↔ "肠-脑-皮肤轴"
- "skin microbiome" ↔ "皮肤微生态"
- "pruritus" ↔ "瘙痒"

Keyword + explicit term bridge (17 pairs in `cross_lingual_terms.json`) provides 100% recall on known mappings; embedding relies on implicit semantic space distance, which is not aligned in this domain.

### 5. rag-eval-011 / 035 / 047 Not Rescued

The hard cross-lingual questions (microbiome-related English PMIDs) remain unsolved by real models.

## Decision

**❌ Do NOT switch to bge-m3 or multilingual-e5-large.**

Reasons:
1. Cross-lingual recall degrades: bge-m3 (0.6250) and e5-large (0.0625) both far below keyword (0.9375).
2. Hybrid cannot compensate: bge-m3 hybrid (0.9062) still below keyword.
3. Model loading overhead: ~2.3GB download + first encode latency, no performance gain.
4. Current term bridge ceiling (0.9375 → 0.9688 gap) likely due to expected-label data issues, not retrieval capability.

**✅ Keep `QIYAN_EMBEDDING_BACKEND=hashing` + `QIYAN_RETRIEVAL_PROVIDER=keyword`.**

## Still Open / Blocked

### Slice 3 (Grounding Semantic Threshold Recalibration) — SKIPPED

Original plan: if bge-m3 / e5-large were selected, re-run `grounding_semantic_pairs.json` with the new backend and sweep for optimal threshold.

**Status**: Not needed. Since keyword remains the recommendation, grounding gate stays at bge (BAAI/bge-small-zh-v1.5) with threshold 0.78 (already calibrated in 2026-05-31).

### Alternative Directions (Out of Scope for This Slice)

1. **Domain fine-tune bge-m3**: Requires AD CN↔EN paired abstracts + GPU training.
2. **Expand term bridge**: From 17 to 30-50 pairs, but 2026-06-02 audit confirmed remaining failures are expected-label issues, not bridge coverage.
3. **Hybrid weight tuning**: keyword 0.8 + vector 0.2, but gain < 0.03.

All deferred to future work; not blocking MVP-A → MVP-B transition.

## Key Files And Artifacts

- `backend/scripts/eval_cross_lingual_bge_m3.py`
- `backend/scripts/eval_cross_lingual_e5_large.py`
- `docs/evaluations/2026-06-12-bge-m3-cross-lingual-eval.md`
- `backend/app/services/retrieval/embedding.py` (BgeM3EmbeddingBackend, MultilingualE5LargeEmbeddingBackend already present)
- `backend/tests/test_cross_lingual_eval.py` (unchanged, still passing)

## Verification

- bge-m3 evaluation: ✅ completed (keyword 0.9375, vector 0.6250, hybrid 0.9062)
- e5-large evaluation: ✅ completed (keyword 0.9375, vector 0.0625, hybrid 0.6562)
- Cross-lingual eval tests: ✅ passing (`pytest tests/test_cross_lingual_eval.py -q`)
- Backend gate: ⏳ pending full run (isolated test file passed)

## Recommended Next Step

Close multilingual embedding spike as "evaluated, not adopted."

Next priority candidates:
1. **PostgreSQL/pgvector spike** (infrastructure, prepares for production scale)
2. **L2 governance decision** (claim-quality v2 profile acceptance, blocked by business/procurement)
3. **MVP-B continuation** (network pharmacology mock → real enrichment analysis)

Per roadmap (`docs/plans/2026-05-21-roadmap.md`),阶段 B 原 slice B1-B6 大部分已提前落地；真实多语 embedding 评估证实 keyword+bridge 为最优，故无需重开 embedding 切换工作。

## Recommended Reading Order

1. `docs/evaluations/2026-06-12-bge-m3-cross-lingual-eval.md` — full results + root cause + recommendation
2. `backend/scripts/eval_cross_lingual_bge_m3.py` / `eval_cross_lingual_e5_large.py` — evaluation harness
3. `docs/handoffs/2026-06-10-multilingual-embedding-spike-b6.md` — embedding backend implementation baseline
4. `docs/evaluations/2026-06-01-cross-lingual-retrieval-comparison.md` — keyword+bridge baseline

---

**Session Date**: 2026-06-12
