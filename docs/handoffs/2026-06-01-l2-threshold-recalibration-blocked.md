# Handoff: L2 Threshold Recalibration — Blocked by BGE Cosine-vs-Entailment Limitation

date: 2026-06-01
branch: feat/l2-real-llm-promotion
status: Slice 1 complete (analysis + documentation); L2-by-threshold closed; default unchanged
focus: ADR-0012 §4a threshold recalibration — the first L2 promotion prerequisite

---

## TL;DR

We attempted the repo-endorsed next step: recalibrate the BGE semantic-grounding
threshold so a real `opencode_go` provider could become the default internal-preview RAG
path (ADR-0012 L2). The honest result is **it cannot be done with a cosine threshold**.
Faithful real-LLM paraphrases (0.863–0.963) and on-topic hard negatives (0.736–0.870)
**overlap** on BGE, so no threshold both admits faithful claims and blocks fabrications.
We did **not** lower the threshold (that would weaken the anti-hallucination guardrail).
**L1 stays as-is, default RAG remains offline `deterministic`, no default flip.**

## What was done

1. **Built a harder labeled fixture** — `backend/data/evals/grounding_semantic_pairs_bge.json`
   (14 pairs). The 7 faithful claims are **lifted verbatim from the 2026-05-31 live smoke
   output** (the real answers that 0.78 over-blocked). Each is twinned with an authored
   **hard negative**: same cited chunk, same vocabulary, but fabricated cure rates / causation /
   numbers / guideline status. Structure locked by a new test.
2. **Extended the sweep tooling** — `run_grounding_semantic_separation(...)` now takes an
   optional `pairs_path`; added module constant `SEMANTIC_PAIRS_BGE_PATH`; new reusable
   script `backend/scripts/sweep_threshold_recalibration.py` prints the per-threshold
   confusion matrix + score distributions on bge.
3. **Ran the sweep** (bge, offline cached weights) — overlap, gap = −0.007, every candidate
   threshold 0.55–0.72 admits all 7 hard negatives.
4. **Documented + decided** — eval report `docs/evaluations/2026-06-01-threshold-recalibration.md`;
   ADR-0012 2026-06-01 addendum (§4a unachievable with BGE-cosine, L2-by-threshold blocked);
   refreshed `docs/current-state.md` next-step item 3 and the runbook "Before promoting to L2".

## Key numbers (bge backend)

| | range |
|---|---|
| Faithful claims (must PASS) | 0.863 – 0.963 |
| Hard negatives (must BLOCK) | 0.736 – 0.870 |
| Gap (min_faithful − max_hardneg) | **−0.007 (overlap)** |

In production it is worse: the same faithful claims scored 0.591–0.881 in the live smoke
(weaker cited chunks), while hard negatives reach 0.870.

## Root cause

BGE (`bge-small-zh-v1.5`) is a sentence-**similarity** model. Cosine measures topical/lexical
relatedness, not factual **entailment**. An on-topic hallucination ("菌群干预治愈率90%") is
topically near-identical to its source chunk, so it scores like a faithful paraphrase. Cosine
cannot, by construction, separate "faithful restatement" from "on-topic fabrication."

## What this means for L2

- **§4a (threshold recalibration): closed.** Not achievable with BGE-cosine alone.
- **§4b (real price + SLI baseline) and §4c (human reviewer walkthrough): still open**, but
  they are not *sufficient* to enable L2 while §4a is unmet.
- **Unlocking L2 requires a different gate stage**: a Chinese NLI / entailment / claim-
  verification model that scores entailment instead of similarity. That is a separate,
  larger architecture decision (new dependency + model + tests) — out of scope for this slice
  and deliberately not started here.

## Files

New:
- `backend/data/evals/grounding_semantic_pairs_bge.json`
- `backend/scripts/sweep_threshold_recalibration.py`
- `docs/evaluations/2026-06-01-threshold-recalibration.md`

Modified:
- `backend/app/services/eval.py` (`pairs_path` param + `SEMANTIC_PAIRS_BGE_PATH`)
- `backend/tests/test_grounding_semantic.py` (fixture-structure test)
- `docs/adr/0012-real-llm-enablement.md` (2026-06-01 addendum)
- `docs/current-state.md`, `docs/guides/real-llm-enablement-runbook.md`

## Verification

Backend gauntlet green: ruff format clean, ruff check clean, mypy clean (48 files),
**pytest 309 passed** (was 308; +1 fixture-structure test). No default behavior changed:
default provider `deterministic`, default `QIYAN_GROUNDING_SEMANTIC_THRESHOLD` still 0.40,
gate untouched. Reproduce the sweep:

```powershell
cd backend
$env:HF_HUB_OFFLINE = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\sweep_threshold_recalibration.py
```

## Recommended next action

Decide the gate architecture, not another threshold sweep. Options, roughly increasing cost:

1. **Accept L1 as the ceiling for now** — keep real provider for controlled smoke/demo only;
   revisit L2 when an entailment gate is justified. (Lowest effort; honest.)
2. **Spike a Chinese NLI/entailment gate** as a second stage after the cosine pre-filter
   (cosine narrows candidates, NLI decides support). New model + dependency + labeled eval.
3. **L2 with mandatory human-verification UI state** — ship real answers flagged
   "pending human verification" while the cosine gate stays a coarse filter. Product decision,
   not just engineering.

Slices 2 (real price + SLI baseline) and 3 (reviewer walkthrough + default flip) from the
original plan are **not** started: flipping the default is unjustified while §4a is unmet.
