# Threshold Recalibration — BGE Cosine Cannot Separate Faithful Paraphrases From On-Topic Hard Negatives

date: 2026-06-01
status: completed (analysis); conclusion: L2-by-threshold is blocked by a model-class limitation, not a fixture bug
backend: bge (`BAAI/bge-small-zh-v1.5`)
fixture: `backend/data/evals/grounding_semantic_pairs_bge.json` (14 pairs)
script: `backend/scripts/sweep_threshold_recalibration.py`
decision: governed by ADR-0012; default RAG path stays offline `deterministic`

## Purpose

ADR-0012 §4 gates L2 (real provider as the default internal-preview path) on three
prerequisites. The first is a **threshold recalibration**: expand the labeled fixture with
real-LLM-style claims and re-run `run_grounding_semantic_separation` to pick a semantic
threshold (candidate range 0.55–0.72) that does not over-block faithful paraphrases.

The 2026-05-31 live smoke (`2026-05-31-opencode-go-bge-smoke.md`) showed the 0.78 threshold
blocking all three real `opencode_go` answers on `semantic_low_support`, including plausibly
faithful claims (0.700–0.727). That smoke only had faithful claims and *easy* negatives
(disjoint-vocabulary fabrications). To recalibrate **safely** the fixture must also contain
**hard negatives**: on-topic fabrications that reuse the cited chunk's vocabulary but invent
scope, numbers, cures, or causation. The recalibrated threshold then has to separate
faithful-paraphrase from hard-negative — a much tighter band than 0.78-vs-easy-negative.

## Fixture

`grounding_semantic_pairs_bge.json` holds 7 faithful claims **lifted verbatim from the live
smoke output** (the real answers 0.78 over-blocked) plus 7 authored hard-negative twins.
Each twin reuses its faithful claim's cited chunk text, so the gate is tested against
on-topic fabrication rather than a topic mismatch.

Example pair (microbiome chunk):

- **faithful**: 肠道菌群失衡与特应性皮炎发病相关，菌群干预可能有助于恢复免疫稳态。
- **hard negative**: 特应性皮炎患者的肠道菌群结构改变已被确立为唯一致病机制，定向菌群干预的临床治愈率高达百分之九十。

The hard negative keeps 肠道菌群结构改变 / 菌群干预 but fabricates a sole-cause mechanism and
a 90% cure rate the chunk never states (the chunk only claims 可能作用).

## Results (bge backend)

Faithful claims (must PASS):

| score | id |
|---:|---|
| 0.863 | sem-live-microbiome-faithful |
| 0.870 | sem-live-syndromebarrier-faithful |
| 0.874 | sem-live-network-faithful |
| 0.882 | sem-live-gbsaxis-faithful |
| 0.898 | sem-live-pruritus-faithful |
| 0.916 | sem-live-syndrome-faithful |
| 0.963 | sem-live-guideline-faithful |

**min faithful = 0.863**

Hard-negative claims (must BLOCK):

| score | id |
|---:|---|
| 0.736 | sem-live-gbsaxis-hallucinated |
| 0.781 | sem-live-syndromebarrier-hallucinated |
| 0.813 | sem-live-pruritus-hallucinated |
| 0.829 | sem-live-network-hallucinated |
| 0.835 | sem-live-syndrome-hallucinated |
| 0.853 | sem-live-guideline-hallucinated |
| 0.870 | sem-live-microbiome-hallucinated |

**max hard-negative = 0.870**

**Score gap (min_faithful − max_hard_negative) = −0.007 → distributions OVERLAP.**

Threshold sweep:

| threshold | faithful pass | hard-neg block | false reject | false accept |
|---:|:---:|:---:|:---:|:---:|
| 0.55 | 7/7 | 0/7 | 0 | 7 |
| 0.58 | 7/7 | 0/7 | 0 | 7 |
| 0.60 | 7/7 | 0/7 | 0 | 7 |
| 0.62 | 7/7 | 0/7 | 0 | 7 |
| 0.64 | 7/7 | 0/7 | 0 | 7 |
| 0.66 | 7/7 | 0/7 | 0 | 7 |
| 0.68 | 7/7 | 0/7 | 0 | 7 |
| 0.70 | 7/7 | 0/7 | 0 | 7 |
| 0.72 | 7/7 | 0/7 | 0 | 7 |
| 0.74 | 7/7 | 1/7 | 0 | 6 |
| 0.76 | 7/7 | 1/7 | 0 | 6 |
| 0.78 | 7/7 | 1/7 | 0 | 6 |

There is **no threshold** that admits the faithful paraphrases (≥0.863) and blocks the hard
negatives (up to 0.870). Anywhere in the ADR-0012 candidate band (0.55–0.72) the gate admits
**all 7** hard negatives — strictly weaker than the current 0.78.

In production the band is even wider: the live smoke scored these same faithful claims at
0.591–0.881 (the model cited weaker chunks than the ideal one), while hard negatives reach
0.870. Lowering the threshold to rescue faithful claims would wave through on-topic
fabrications.

## Root cause (model class, not a fixture bug)

BGE (`bge-small-zh-v1.5`) is a sentence-**similarity** model: cosine measures topical/lexical
relatedness, not factual **entailment**. A well-crafted hallucination that stays on-topic
("菌群干预治愈率90%") is topically near-identical to its source chunk, so it scores as high as a
faithful paraphrase. Cosine similarity structurally cannot distinguish "faithful restatement"
from "on-topic fabrication that adds unsupported scope/numbers/causation." This is the same
limitation already noted for the hashing backend, surfacing on the semantic backend too once
the negatives are on-topic.

## Conclusion and decision

- ADR-0012 §4a (a recalibrated cosine threshold that keeps faithful paraphrases while
  preserving the guardrail) is **not achievable with BGE-cosine alone**. We did not lower the
  threshold, because every value that rescues faithful claims also admits the hard negatives,
  which would weaken the anti-hallucination guardrail.
- **L1 stays as-is** (controlled smoke/demo, gate on at 0.78). The default RAG path remains
  offline `deterministic`. No default flip.
- L2-by-threshold is blocked. Closing the gap requires a different gate stage — a Chinese
  NLI/entailment or claim-verification model that scores entailment rather than similarity —
  which is a separate, larger architecture decision (out of scope here).

## Reproduce

```powershell
cd backend
$env:HF_HUB_OFFLINE = "1"   # use locally cached bge weights
& .\.uv-test-venv\Scripts\python.exe scripts\sweep_threshold_recalibration.py
```

The fixture structure is locked by
`tests/test_grounding_semantic.py::test_bge_recalibration_fixture_is_balanced_and_paired`.
