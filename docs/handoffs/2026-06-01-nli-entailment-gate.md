# Handoff: NLI Entailment Grounding Gate — Spike Validated + Opt-In Implementation

date: 2026-06-01
branch: feat/l2-real-llm-promotion
status: complete (spike GO + opt-in gate shipped, default off); L2 default flip still gated
focus: build the entailment gate that closes the cosine-vs-entailment gap from the prior slice

---

## TL;DR

The prior slice proved BGE **cosine** cannot separate faithful paraphrases from on-topic hard
negatives (gap −0.007). This slice validated and built the documented fix: an **NLI entailment
gate**. On the same 14-pair fixture, NLI scores faithful claims at **0.997–0.999** and on-topic
fabrications at **≤0.001**, with **0 false accepts at every threshold** (cosine had 7/7). It is
implemented as an **opt-in, default-off** second stage after the cosine pre-filter. Default RAG
behavior is byte-identical; CI never downloads the model.

## Spike result (GO)

| | cosine (BGE) | NLI (mDeBERTa-v3-mnli-xnli) |
|---|---|---|
| Faithful | 0.863–0.963 | 0.997–0.999 (6/7) |
| Hard negatives | 0.736–0.870 | ≤0.001 (7/7) |
| False accepts | 7/7 every threshold | **0/7 every threshold 0.10–0.90** |

The one faithful "reject" (`sem-live-syndrome`, 0.0073) is arguably NLI being correct — that
claim adds "提供潜在靶点", a scope addition the cited chunk never states. Evidence + sweep:
`docs/evaluations/2026-06-01-nli-grounding-spike.md`; reproducible via
`backend/scripts/spike_nli_grounding.py`.

## What shipped (opt-in, default OFF)

- `backend/app/services/nli.py` — `NliBackend` Protocol + lazy `TransformersNliBackend`
  (imports transformers/torch and loads the model only on first `entailment` call) +
  `select_nli_backend` (returns `None` when disabled/unknown). Mirrors `embedding.py`.
- `backend/app/services/grounding.py` — after the cosine gate, if an NLI backend + threshold
  are supplied, scores `entailment(chunk, claim)` per claim, surfaces `entailment_score` /
  `min_entailment_score`, blocks with `blocked_reason="nli_low_entailment"` below threshold.
- `backend/app/schemas/rag.py` — `GroundedClaim.entailment_score`,
  `GroundingMetadata.nli_threshold`, `GroundingMetadata.min_entailment_score` (optional, `None`
  when off).
- `backend/app/core/config.py` + `.env.example` — `QIYAN_NLI_BACKEND` (default `""` = off),
  `QIYAN_NLI_MODEL` (default `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`), `QIYAN_NLI_THRESHOLD`
  (default `0.0` = off). `services/rag.py` wires them.
- `backend/pyproject.toml` — `transformers>=4.40.0` added to `dev` extras (nli.py imports it
  directly; was only transitive via sentence-transformers).
- Tests: `backend/tests/test_grounding_nli.py` (6 tests, deterministic fake backend — no model
  download); `test_rag_api.py` grounding snapshot updated with the two new `None` fields.

## Default-behavior invariants (verified)

- `QIYAN_NLI_BACKEND` empty → `select_nli_backend` returns `None` → gate is a no-op.
- Disclaimer byte-identical; block replaces the draft; safe fallback unchanged.
- CI/offline path never imports transformers or downloads the ~560 MB model.

## Enable (controlled smoke)

```powershell
cd backend
$env:QIYAN_LLM_PROVIDER = "opencode_go"   # gate only runs for external providers
$env:QIYAN_NLI_BACKEND = "transformers"
$env:QIYAN_NLI_THRESHOLD = "0.5"
$env:HF_HUB_OFFLINE = "1"                 # after the model is cached
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

First-time model fetch needed the Windows proxy in this env:
`$env:HTTPS_PROXY="http://172.26.0.1:7897"` then
`snapshot_download('MoritzLaurer/mDeBERTa-v3-base-mnli-xnli')`.

## Verification

Backend gauntlet green: ruff format/check clean, mypy clean (49 files), **pytest 315 passed**
(309 → +6 NLI tests). Frontend **141 tests** + typecheck clean (NLI fields are backend-only).
Real-model integration check confirmed end-to-end: faithful claim passes (0.9971), on-topic
fabrication blocked (0.0011) through `evaluate_answer_grounding`.

## This is NOT an automatic L2 promotion

The gate resolves the §4a technical blocker, but the default is still `deterministic`. Before
flipping the default to a real provider (ADR-0012 §4):

1. **Larger labeled set + production threshold.** 14 pairs is a spike; one faithful claim
   already exposed a labeling nuance. Expand `grounding_semantic_pairs_bge.json` (or a new
   NLI-specific fixture), validate, and pick the production `QIYAN_NLI_THRESHOLD`.
2. **SLI baseline must include NLI cost.** One NLI forward pass per claim adds CPU latency
   (the model is ~560 MB on CPU torch). Measure p50/p95 with the gate on and fold into §4b.
3. **Human reviewer walkthrough (§4c).**

## Recommended next action

Pick one:
- **Expand the NLI fixture + measure NLI latency** (directly advances §4a-final + §4b).
- **Surface entailment in the `/rag` UI + Markdown export** (the fields exist in the response
  but the frontend doesn't show them yet) — small, improves transparency for reviewers.
- **GPU/quantized NLI or a smaller model** if CPU latency proves too high for L2 ergonomics.

## Files

New: `backend/app/services/nli.py`, `backend/tests/test_grounding_nli.py`,
`backend/scripts/spike_nli_grounding.py`, `docs/evaluations/2026-06-01-nli-grounding-spike.md`,
this handoff.

Modified: `backend/app/services/grounding.py`, `backend/app/services/rag.py`,
`backend/app/schemas/rag.py`, `backend/app/core/config.py`, `backend/.env.example`,
`backend/pyproject.toml`, `backend/tests/test_rag_api.py`, `docs/adr/0012-real-llm-enablement.md`,
`docs/current-state.md`, `docs/guides/real-llm-enablement-runbook.md`.
