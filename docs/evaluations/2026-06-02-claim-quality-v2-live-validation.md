# Claim-Quality v2 Live Validation

date: 2026-06-02
provider: `opencode_go`
default decision: keep `deterministic`; do not flip L2
runtime artifact: `backend/data/runtime/captured_real_claims_live_20260602_0846.json` (gitignored)
reviewer packet: `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`
price SLI baseline: `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`

## Goal

Validate whether the 2026-06-01 claim-quality prompt/schema v2 improved real
`opencode_go` answer structure: fewer claims, exactly one evidence ref per claim,
no unsupported evidence IDs, no raw draft leakage, and measurable BGE/NLI scores.

This was a technical live validation with a quick claim-level review of passed
answers. Follow-up reviewer confirmation was completed on 2026-06-02 by user
confirmation of the six passed-claim verdicts in
`docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`.

## Configuration

PowerShell environment:

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4000"
$env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.3"
$env:QIYAN_NLI_BACKEND = "transformers"
$env:QIYAN_NLI_THRESHOLD = "0.5"
$env:PYTHONUTF8 = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\capture_real_answer_claims.py
```

Why `BGE=0.3`: the previous §4c walkthrough showed that `BGE=0.78` blocks most
real cross-lingual/paraphrased claims before NLI can evaluate entailment. This
run intentionally lowered the cosine prefilter to let the NLI gate decide claim
faithfulness. This is an evaluation profile, not a default preview flip.

## Results

| Metric | Result |
|---|---:|
| Questions captured | 10 |
| Total claims | 14 |
| Provider rows | 10 `opencode_go`, 0 fallback |
| Grounding passed | 4 answers |
| Grounding blocked | 6 answers |
| Blocked reasons | 6 `nli_low_entailment` |
| Claims with zero refs | 0 |
| Claims with one ref | 14 |
| Claims with multi refs | 0 |
| Semantic score range | 0.3394-0.9553 |
| Entailment score range | 0.0004-0.9990 |
| Provider latency | min 5.25s, avg 13.15s, max 28.54s |
| Token usage | 6,040 input / 14,984 output total |
| Estimated cost | `null` / not recorded; no real price env configured |

Cost follow-up: `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`
retrofits the recorded token usage with the current `deepseek-v4-flash` price
baseline (`$0.14` / 1M input, `$0.28` / 1M output), estimating `$0.005042` total
cost for this 10-question capture. The original capture still correctly records
`estimated_cost_usd=null` because the price env vars were not configured during
that run.

Passed answers:

| Question | Claims | Min semantic | Min entailment | Review note |
|---|---:|---:|---:|---|
| `rag-eval-005` skin barrier damage | 2 | 0.3394 | 0.9985 | Passed claims are directly supported by English PubMed chunks on filaggrin loss-of-function and barrier/type-2 inflammation. |
| `rag-eval-007` JAK-STAT pathway | 1 | 0.5893 | 0.9990 | Claim is directly supported by the cited JAK-STAT review chunk. |
| `rag-eval-008` network pharmacology usage | 2 | 0.5783 | 0.9985 | Claims are directly supported by the cited network-pharmacology chunks. |
| `rag-eval-010` long-term management consensus | 1 | 0.9553 | 0.7446 | Claim is directly supported by the cited consensus-management chunk. |

## Codex Technical Evidence-Support Review

date: 2026-06-02
packet: `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`
reviewer: Codex technical review
status: technical evidence-support review complete; user-confirmed formal reviewer verdicts complete

Result:
- Claims reviewed: 6
- Supported: 6
- Unsupported: 0
- Unclear: 0
- Formal confirmation: confirmed by user on 2026-06-02; no verdict revisions.

Interpretation:
- All six passed claims were directly supported by their cited chunks in this technical review.
- This supports continued controlled L1 demo/evaluation use of the `BGE=0.3 + NLI=0.5` profile.
- This does not approve L2/default preview because a separate ADR-quality profile decision remains open.

Blocked answers:

All six blocked answers were blocked by `nli_low_entailment`; there were no
schema parse failures, unsupported evidence refs, missing refs, or multi-ref
claims. This means the v2 prompt/schema materially improved structure, but NLI
still rejects claims whose phrasing or scope is not directly entailed by the
single cited chunk.

The most informative case was `rag-eval-009`: one claim had high entailment
(`0.9990`) but the sibling claim in the same answer scored `0.0104`, so the
answer was blocked by the conservative min-score policy. This is the intended
behavior for a medical evidence workbench: a mixed-quality answer does not leak
raw provider text.

## Interpretation

- Claim structure improved: 14/14 claims used exactly one evidence ref, matching
  the v2 prompt/schema requirement.
- The grounding gate is still active and useful: 6/10 answers were blocked by
  NLI, not by formatting errors.
- The first credible passed real-provider answers appeared under the evaluation
  profile `BGE=0.3 + NLI=0.5`.
- `BGE=0.78` remains too strict for this real-provider validation path because
  several passed claims had low BGE scores (for example 0.3394) but high NLI
  entailment (0.9985), especially in cross-lingual English chunk cases.
- There was no raw draft leakage in the capture result: blocked answers used the
  hard-block answer text while retaining citation cards and grounding metadata.

## Decision

Keep L1 only. Do not flip L2/default preview.

Rationale:

- v2 improved claim structure enough to justify keeping the real-provider L1
  smoke/demo path.
- The evaluation profile required lowering the BGE prefilter to 0.3; this needs
  a separate ADR-quality decision before production/default use.
- Codex technical evidence-support review found 6/6 passed claims supported by
  their cited chunks, and the user confirmed those six verdicts on 2026-06-02.
- Price SLI baseline has been recorded separately from the original capture:
  `$0.005042` estimated total cost at current `deepseek-v4-flash` public token
  prices. Formal budgeting should still re-check provider contract pricing.

## Next Recommendation

If continuing the L2 line, do not repeat the 2026-06-01 §4c reviewer walkthrough
that already verified gate, fallback, rollback, and UI metadata behavior. The
narrow delta packet now has user-confirmed verdicts for all six passed claims.
The remaining decision is whether the lower BGE prefilter plus NLI gate is
acceptable beyond controlled L1 demo/evaluation use. Default provider must
remain `deterministic` unless a new ADR explicitly changes that decision.
