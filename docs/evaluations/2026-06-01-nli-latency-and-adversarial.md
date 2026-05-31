# NLI Gate — Latency Baseline + Adversarial Generalization (32 pairs)

date: 2026-06-01
status: completed; NLI gate generalizes on adversarial cases + latency measured for §4b
model: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (CPU torch)
fixtures: `grounding_semantic_pairs_bge.json` (14) + `grounding_nli_adversarial.json` (18) = 32 pairs
scripts: `backend/scripts/bench_nli_latency.py`, `backend/scripts/spike_nli_grounding.py`
decision: governed by ADR-0012; default RAG path unchanged (gate still opt-in, default off)

## Why this follow-up

The NLI spike (`2026-06-01-nli-grounding-spike.md`) showed clean separation on 14 pairs, but
those were self-confirming: faithful claims came from the smoke output and the hard negatives
were authored alongside the gate. Two L2 unknowns remained:

1. **Generalization** — does NLI hold on failure modes the first set never tested?
2. **Cost (§4b)** — what latency does an NLI forward pass per claim add?

This doc records both. Default behavior is unchanged; the gate stays opt-in and off.

## 1. Latency baseline (§4b)

`scripts/bench_nli_latency.py`, CPU torch, `mDeBERTa-v3-base-mnli-xnli`:

| metric | value |
|---|---|
| Cold first call (incl. model load) | ~6,710 ms (once per process) |
| Warm per-claim — mean | 840 ms |
| Warm per-claim — p50 | 854 ms |
| Warm per-claim — p95 | 922 ms |
| Per 3-claim answer (sequential) | ~2,561 ms p50 / ~2,765 ms p95 |

Context: the 2026-05-31 live smoke measured `opencode_go` provider latency ≈11,768 ms, so the
gate adds roughly +20% to a real-provider answer. Acceptable for an internal preview; not free.

**Known optimization (not done):** claims are scored sequentially. Batching all claims of an
answer into a single forward pass would cut the per-answer cost toward the single-claim figure.
Deferred — the sequential number is the honest current baseline.

## 2. Adversarial generalization

`grounding_nli_adversarial.json` adds 18 pairs targeting modes the 14-pair set lacked. Labels
were reviewed and approved before scoring. premise = cited chunk, hypothesis = claim,
score = entailment probability.

### Per-mode result (all correct)

| Failure mode | Example (non-supported) | Entailment | Verdict |
|---|---|---:|---|
| Number tampering | "约78%的特应性皮炎患者存在肠道菌群结构改变" | 0.0003 | blocked ✓ |
| Number tampering | "规律外用润肤剂可使复发率降低62%" | 0.0002 | blocked ✓ |
| Hedge removal (可能→确定性) | "菌群干预能够确定性地恢复免疫稳态" | 0.0030 | blocked ✓ |
| Hedge removal | "已被证实能完全修复角质层屏障" | 0.0007 | blocked ✓ |
| Partial support + leap | true prefix + "益生菌应作为一线治疗" | 0.0003 | blocked ✓ |
| Partial support + leap | true pathways + "应优先用JAK抑制剂治疗所有患者" | 0.0002 | blocked ✓ |
| Negation (deny relation) | "不存在任何关联" | 0.0001 | blocked ✓ |
| Overgeneralization | "所有儿童…都属于湿热证型，无需辨证" | 0.0002 | blocked ✓ |
| Entity splicing | filaggrin+神经酰胺→JAK-STAT 假因果 | 0.0003 | blocked ✓ |
| Cross-chunk synthesis | network chunk + pediatric chunk fused | 0.0002 | blocked ✓ (see limitation) |

Faithful robustness cases (reordered entities, synonym compression, double-negative
restatement, hedge preserved) all PASS at ≥0.9854. The number-tampering result is the headline:
"约78%…" is near-identical text to its chunk — cosine's exact blind spot — and NLI scored it
**0.0003**.

### Combined 32-pair confusion matrix

| | count | range |
|---|---|---|
| Faithful (want pass) | 15 | 14 at ≥0.996, 1 at 0.0073 |
| Non-supported (want block) | 17 | all ≤0.0030 |

**min faithful = 0.0073, max non-supported = 0.0030, gap = +0.0044.**

| threshold | faithful pass | non-sup block | false reject | false accept |
|---:|:---:|:---:|:---:|:---:|
| 0.10–0.90 | 14/15 | **17/17** | 1 | **0** |

**0 false accepts at every threshold.** The matrix is flat across 0.10–0.90, so **0.5 is the
recommended production threshold** (faithful ≈0.99, non-supported ≈0.003 — a ~0.99 margin).
This is wired as `QIYAN_NLI_THRESHOLD`; default stays `0.0` (off).

### The single false reject is arguably correct

`sem-live-syndrome-faithful` (0.0073) adds "为特应性皮炎治疗提供潜在靶点", a therapeutic-target
claim the cited chunk never states. NLI flagged a real scope addition that the faithful label
was too generous about. So 14/15 understates the gate.

## Caveats (kept honest)

1. **Still synthetic.** 32 pairs is broader and adversarial, but I authored the negatives; this
   is not a real-traffic distribution. A real-answer sample remains the next validation step.
2. **NLI is strict about scope.** It blocks claims that add reasonable-sounding framing beyond
   the cited chunk (the 0.0073 case). Real LLM answers often add such framing — for L2 this is a
   precision/recall tradeoff to tune, possibly with a slightly lower threshold or per-claim
   review, not a free pass.
3. **Cross-chunk limitation is real.** `nli-multichunk-008-crosschunk` documents it: a claim
   genuinely supported by *two* chunks is rejected because the gate scores each claim against
   its own refs (max over refs), not the concatenation. Multi-chunk summaries would need premise
   concatenation to pass. Out of scope here; flagged for the gate's future work.

## Status vs L2 (ADR-0012 §4)

- §4a (separation): resolved technically — NLI separates faithful from on-topic / adversarial
  fabrication with 0 false accepts on 32 pairs.
- §4b (SLI cost): latency measured (above); fold ~+2.5 s/answer into the SLI baseline when the
  gate is enabled.
- §4c (reviewer walkthrough) and a real-answer (non-synthetic) validation set are still open
  before any default flip. The gate remains opt-in, default off.

## Reproduce

```powershell
cd backend
$env:HF_HUB_OFFLINE = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\bench_nli_latency.py
& .\.uv-test-venv\Scripts\python.exe scripts\spike_nli_grounding.py
```

Fixture structure is locked by
`tests/test_grounding_nli.py::test_adversarial_nli_fixture_is_balanced_and_well_formed`.
