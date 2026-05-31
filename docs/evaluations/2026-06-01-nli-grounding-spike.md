# NLI Entailment Grounding Spike — Closing the Cosine Gap

date: 2026-06-01
status: spike validated (GO) + opt-in gate implemented; default RAG path unchanged
model: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (multilingual NLI via XNLI; supports Chinese)
fixture: `backend/data/evals/grounding_semantic_pairs_bge.json` (same 14 pairs as the cosine sweep)
spike script: `backend/scripts/spike_nli_grounding.py`
decision: governed by ADR-0012; default RAG stays offline `deterministic`

## Why

The 2026-06-01 threshold recalibration (`2026-06-01-threshold-recalibration.md`) proved that
BGE **cosine** cannot separate faithful paraphrases from on-topic hard negatives — both are
topically similar to the cited chunk, so they score in the same band (gap −0.007). Cosine
measures *similarity*, not *entailment*. ADR-0012's L2-by-threshold path was blocked, and the
documented unlock was "a different gate that scores entailment." This spike validates that
idea before building it.

## Hypothesis

Score each pair with NLI where **premise = cited chunk, hypothesis = claim**, and use the
entailment probability. A faithful claim should be entailed by its chunk (high entailment); an
on-topic fabrication adds unsupported scope/cause/numbers, so the chunk does **not** entail it
(low entailment, often high contradiction) — even though it stays on-topic.

## Result (GO)

| | cosine (BGE) | NLI entailment (mDeBERTa) |
|---|---|---|
| Faithful claims | 0.863 – 0.963 | **0.997 – 0.999** (6 of 7) |
| Hard negatives | 0.736 – 0.870 | **≤ 0.001** (7 of 7) |
| Separation | gap −0.007 (overlap) | **0 false accepts at every threshold 0.10–0.90** |

Entailment-threshold sweep on the 14-pair fixture:

| threshold | faithful pass | hard-neg block | false reject | false accept |
|---:|:---:|:---:|:---:|:---:|
| 0.10–0.90 | 6/7 | 7/7 | 1 | **0** |

NLI blocks **all** on-topic fabrications with **zero false accepts**, flat across the whole
threshold range — exactly the separation cosine could not produce.

### The one faithful "reject" is arguably correct

`sem-live-syndrome-faithful` scored 0.0073 entailment. Its claim adds
"...为特应性皮炎治疗提供潜在靶点" (provides therapeutic targets), which the cited chunk never
states — the chunk only asserts a 可解释关联. NLI flagged a genuine scope addition that the
faithful label was too generous about. So the model is, if anything, sharper than the headline
6/7 suggests. A real deployment threshold around 0.5 keeps a wide safety margin (faithful
≈0.99, hard negatives ≈0.001).

## What was implemented (opt-in, default-off)

The gate is a second stage **after** the cosine pre-filter, engaged only when configured:

- `app/services/nli.py` — `NliBackend` Protocol + `TransformersNliBackend` (lazy: imports
  `transformers`/`torch` and loads the model only on first `entailment` call) + `select_nli_backend`
  (returns `None` when disabled/unknown). Mirrors the `EmbeddingBackend` env-selection pattern.
- `app/services/grounding.py` — after the cosine gate, if an NLI backend + threshold are
  supplied, score `entailment(chunk, claim)` per claim, surface `entailment_score` /
  `min_entailment_score`, and block with `blocked_reason="nli_low_entailment"` when the min
  falls below threshold. Hard invariants unchanged (disclaimer byte-identical, block replaces
  the draft, safe fallback).
- `app/schemas/rag.py` — `GroundedClaim.entailment_score`, `GroundingMetadata.nli_threshold`,
  `GroundingMetadata.min_entailment_score` (all optional / `None` when the gate is off).
- `app/core/config.py` + `.env.example` — `QIYAN_NLI_BACKEND` (default `""` = off),
  `QIYAN_NLI_MODEL`, `QIYAN_NLI_THRESHOLD` (default `0.0` = off). `services/rag.py` wires them.

**Default behavior is byte-identical**: `QIYAN_NLI_BACKEND` empty → `select_nli_backend`
returns `None` → gate is a no-op. CI never imports transformers or downloads the ~560 MB model
(tests use a deterministic fake backend; `tests/test_grounding_nli.py`).

## Status vs L2 prerequisites (ADR-0012 §4)

- §4a was blocked because cosine can't separate faithful from on-topic fabrication. The NLI
  gate **resolves the underlying technical limitation**: on this fixture it separates cleanly
  with 0 false accepts.
- This is **not** an automatic L2 promotion. Before flipping the default to a real provider:
  1. validate NLI on a larger, more varied labeled set (this fixture is 14 pairs; one faithful
     claim already exposed a labeling nuance) and pick a production threshold;
  2. measure the added latency/cost of an NLI forward pass per claim and fold it into the SLI
     baseline (§4b);
  3. run the human reviewer walkthrough (§4c).
- The gate ships **off by default**, so it changes nothing for current users until those steps
  are done and the default is deliberately flipped.

## Reproduce

```powershell
cd backend
# first run only: fetch the model (proxy needed in this environment)
$env:HTTPS_PROXY = "http://172.26.0.1:7897"
& .\.uv-test-venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download as d; d('MoritzLaurer/mDeBERTa-v3-base-mnli-xnli')"
# then, offline:
$env:HF_HUB_OFFLINE = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\spike_nli_grounding.py
```
