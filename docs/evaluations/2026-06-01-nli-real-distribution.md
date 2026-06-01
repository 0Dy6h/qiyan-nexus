# NLI Real-Distribution Evaluation — 2026-06-01

date: 2026-06-01
status: completed
gate: NLI entailment (mDeBERTa-v3-base-mnli-xnli)
threshold: 0.5
fixture: grounding_real_answer_pairs.json (20 pairs, Slice 2)

## Summary

The NLI entailment gate achieves **perfect separation** on the real-answer
validation set: **0 false accepts, 0 false rejects** at the recommended
production threshold 0.5.

This closes the last pure-engineering caveat from ADR-0012 §4: the NLI gate's
performance has now been validated not just on synthetic/adversarial fixtures,
but on claims **lifted verbatim from a real `opencode_go` live smoke session**
and paired with their actual cited chunks.

## Results

| Metric | Value |
|---|---|
| Total pairs | 20 |
| Supported | 5 |
| Partial | 4 |
| Unsupported | 11 |
| Threshold | 0.5 |
| False accepts (FP) | **0** |
| False rejects (FN) | **0** |
| Accuracy | **100.0%** |

### Score distributions

| Label | Min | Max | Mean |
|---|---|---|---|
| supported | 0.9966 | 0.9990 | 0.9981 |
| partial | 0.0004 | 0.0473 | 0.0127 |
| unsupported | 0.0001 | 0.0417 | 0.0042 |

**Gap**: supported min (0.9966) − unsupported max (0.0417) = **+0.9549**

Any threshold in (0.0417, 0.9966) achieves perfect separation. The 0.5
recommendation has a **massive margin of safety** in both directions:
- Closest false accept: unsupported at 0.0417 (gap of 0.458 below threshold)
- Closest false reject: supported at 0.9966 (gap of 0.497 above threshold)

### Partial claims

The 4 partial claims — which are topically related to their chunk but add
unsupported scope (e.g., "为特应性皮炎治疗提供靶点" when the chunk only states
correlations, or "改善患者生活质量" as an inference) — all score **very low**
(0.0004–0.0473). The NLI model correctly identifies that the premise does not
*entail* the overscoped claim, even though the claim shares vocabulary with
the source.

This is the key advantage over BGE cosine: cosine scored the same partial
claims at 0.881 and 0.782 (similar to faithful claims), while NLI correctly
rates them near zero.

### Hard negatives

All 11 authored hard negatives (fabricated efficacy claims, cross-topic
mismatches, negation patterns, toxicity claims) score ≤0.0417 — every one is
correctly blocked. This includes:

- Cross-topic mismatch: a faithful claim paired with the wrong chunk → rejected
- Fabricated quantitative claims ("治愈率90%") → rejected
- Negation patterns (claim contradicts the chunk) → rejected
- Toxicity claims ("激素类药物作为一线治疗") → rejected
- Entity splicing (黄芩/黄连/黄柏 not in any chunk) → rejected

## Comparison with prior evaluations

| Fixture | Pairs | BGE-cosine false accepts | NLI false accepts |
|---|---|---|---|
| Synthetic easy | 20 | 0 | 0 |
| BGE recalibration | 14 | 7/7 | 0/7 |
| NLI adversarial | 32 | — | 0/32 |
| **Real-answer (this)** | **20** | — | **0/11** |

The NLI gate consistently achieves **0 false accepts** across all four
independent fixtures, whereas BGE-cosine collapsed (7/7 false accepts) on the
harder real-LLM-style fixture.

## Implications for L2 promotion (ADR-0012 §4)

The NLI gate is now validated on the real-answer distribution. The remaining
blockers for L2 (default preview) are:

1. ✅ **§4a — Threshold calibrated**: Done. 0.5 is validated on real distribution
   with 0 false accepts + 0 false rejects.
2. ✅ **NLI gate implemented**: Done (opt-in, default-off). Tested on 4 fixtures.
3. ⬜ **§4b — NLI latency in SLI baseline**: Not done. Per-answer NLI batching
   (Slice 4) will fold NLI cost into `rag_sli`.
4. ⬜ **§4c — Human reviewer walkthrough**: Not done. Requires human-in-the-loop
   verification per `docs/checklists/internal-preview-smoke.md`.

## Caveats

- The 5 supported claims all come from the same live smoke session (3 questions,
  7 claims total, 5 labeled supported). A larger, more diverse set of real
  answers would strengthen confidence.
- All supported claims scored very high (≥0.9966). This may partially reflect
  that the real opencode_go claims were *faithful paraphrases* of the chunks
  (the model was well-grounded). Claims from a model that produces more
  aggressive inferences might score lower.
- The NLI model adds ~560 MB memory and ~840 ms/claim latency (per
  `bench_nli_latency.py`). Per-answer batching (Slice 4) will reduce this.

## Recommendation

**Keep threshold at 0.5.** The gap is enormous (0.9549) and the threshold is
already conservative — any value in [0.05, 0.99] works. No recalibration needed.

**Proceed to Slice 4 (NLI batching) and Slice 5 (reviewer walkthrough).**
The NLI gate is technically ready for L2 default promotion, pending the human
reviewer sign-off in §4c.

## Reproduce

```powershell
cd backend
$env:QIYAN_NLI_BACKEND = "transformers"
$env:QIYAN_NLI_THRESHOLD = "0.5"
$env:HF_HUB_OFFLINE = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\eval_nli_real_distribution.py
```

Full JSON report: `backend/data/runtime/eval_nli_real_distribution_20260601_0901.json`

## Key files

- `backend/data/evals/grounding_real_answer_pairs.json` — Slice 2 fixture (20 pairs)
- `backend/scripts/eval_nli_real_distribution.py` — evaluation runner
- `backend/app/services/eval.py` — `run_nli_real_distribution_eval()`
- `backend/app/schemas/eval.py` — `RealAnswerPair` model
