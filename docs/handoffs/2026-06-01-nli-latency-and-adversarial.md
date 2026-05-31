# Handoff: NLI Gate — Latency Baseline + Adversarial Generalization

date: 2026-06-01
branch: feat/l2-real-llm-promotion
status: complete; NLI gate validated on adversarial cases + latency measured; default unchanged
focus: path A from the prior session — kill the §4b cost unknown, then stress-test §4a generalization

---

## TL;DR

Advanced the two real L2 unknowns left after the NLI gate shipped:
1. **Cost (§4b):** measured. NLI adds ~840 ms/claim (p50), ~2.5 s per 3-claim answer, ~+20% on a
   real-provider answer; 6.7 s one-time cold load.
2. **Generalization (§4a):** stress-tested. Added 18 adversarial pairs (number tampering, hedge
   removal, partial support, negation, overgeneralization, entity splicing, cross-chunk). Combined
   **32 pairs → 0 false accepts at every threshold**, recommended production threshold **0.5**.

Default RAG behavior unchanged: gate stays opt-in (`QIYAN_NLI_BACKEND` empty = off), CI never
loads the model.

## Latency (§4b)

`scripts/bench_nli_latency.py`, CPU torch, `mDeBERTa-v3-base-mnli-xnli`:

| metric | value |
|---|---|
| Cold first call (incl. load) | ~6,710 ms (once per process) |
| Warm per-claim p50 / p95 | 854 / 922 ms |
| Per 3-claim answer | ~2,561 ms p50 / ~2,765 ms p95 |

vs. live provider latency ≈11,768 ms → ~+20%. Known un-done optimization: batch all claims of an
answer into one forward pass (current code scores sequentially).

## Adversarial result (§4a generalization)

`grounding_nli_adversarial.json` (18 pairs, labels reviewed + approved before scoring). Every
targeted failure mode handled correctly:

- Number tampering "约78%…" (near-identical to chunk, cosine's blind spot) → 0.0003, blocked.
- Hedge removal 可能→确定性 → ≤0.003, blocked. Partial-support true-prefix+false-leap → ≤0.0003.
- Negation, overgeneralization, entity splicing, cross-chunk synthesis → all blocked ≤0.0003.
- Faithful robustness (reorder / synonym / double-negative / hedge-preserved) → all pass ≥0.9854.

Combined 32 pairs: 15 faithful (14 ≥0.996, 1 at 0.0073), 17 non-supported (all ≤0.0030).
**gap +0.0044; 14/15 faithful pass, 17/17 non-supported block, 0 false accepts, 0.10–0.90.**
Recommended `QIYAN_NLI_THRESHOLD=0.5`.

The single false reject (`sem-live-syndrome-faithful`, 0.0073) adds "提供潜在靶点" the chunk never
states — arguably NLI being right about a scope addition I over-labeled.

## Honest caveats (in the eval doc)

1. **Still synthetic** — I authored the negatives; 32 pairs is broader/adversarial but not a
   real-traffic distribution. A real-answer validation set is the next step.
2. **NLI is strict about scope additions** — real LLM answers that add reasonable framing may get
   blocked (the 0.0073 case). For L2, a precision/recall tradeoff to tune.
3. **Cross-chunk limitation is real** — multi-chunk-supported claims get rejected because the gate
   scores each claim against its own refs (max over refs), not concatenated premises. Documented by
   `nli-multichunk-008-crosschunk`; future gate work.

## Files

New:
- `backend/scripts/bench_nli_latency.py`
- `backend/data/evals/grounding_nli_adversarial.json`
- `docs/evaluations/2026-06-01-nli-latency-and-adversarial.md`
- this handoff

Modified:
- `backend/tests/test_grounding_nli.py` (adversarial fixture structural test)
- `docs/current-state.md`

## Verification

Backend gauntlet green: ruff format/check clean, mypy clean (49 files), **pytest 316 passed**
(315 → +1 structural test). No app code changed this slice — gate logic was shipped in the prior
commit (6b46fbc); this is eval + measurement + one test.

## Status vs L2 (ADR-0012 §4)

- §4a: separation resolved + now adversarially generalized (0 false accepts on 32 pairs).
- §4b: NLI latency measured; fold ~+2.5 s/answer into the SLI baseline when enabled.
- §4c (reviewer walkthrough) + a real-answer (non-synthetic) validation set: still open. Gate
  remains opt-in, default off; no default flip.

## Recommended next action

1. **Real-answer validation set** — collect actual `opencode_go` answers (the live smoke produced
   some), label claim-level support, score with the gate at 0.5. This replaces the synthetic
   caveat and is the last technical gate before §4c.
2. Optional perf: batch per-answer claims into one NLI forward pass to cut the ~2.5 s.
3. Then §4c reviewer walkthrough → only then consider flipping the default.
