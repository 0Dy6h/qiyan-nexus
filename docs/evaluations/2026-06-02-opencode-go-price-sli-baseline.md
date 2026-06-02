# OpenCode Go Price SLI Baseline

date: 2026-06-02
runtime artifact: `backend/data/runtime/captured_real_claims_live_20260602_0846.json` (gitignored)
provider path: `opencode_go`
model: `deepseek-v4-flash`
default decision: keep `deterministic`; do not flip L2

## Goal

Close the price-SLI part of the L2 review line without changing the default RAG
path. The original 2026-06-02 live capture did not configure
`QIYAN_OPENCODE_GO_PRICE_*`, so `estimated_cost_usd` was `null`. This note
computes the baseline cost from the recorded token usage and current published
`deepseek-v4-flash` prices.

## Price Source

- OpenCode Go is the current access path used by Qiyan Nexus. Its public Go page
  describes subscription pricing and request limits rather than per-token model
  prices: <https://opencode.ai/go>.
- For token-level SLI estimation, this baseline uses DeepSeek's official API
  pricing page for `deepseek-v4-flash`: `$0.14` / 1M cache-miss input tokens and
  `$0.28` / 1M output tokens: <https://api-docs.deepseek.com/quick_start/pricing>.
- Cache-hit pricing is not used here because the capture artifact records only
  `prompt_tokens` and `completion_tokens`; it does not distinguish cache-hit vs
  cache-miss input tokens. This is a conservative cache-miss estimate.

PowerShell configuration for future live runs:

```powershell
$env:QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK = "0.14"
$env:QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK = "0.28"
```

## Baseline Summary

| Metric | Value |
|---|---:|
| Questions captured | 10 |
| Provider rows | 10 `opencode_go`, 0 fallback |
| Grounding passed | 4 answers |
| Grounding blocked | 6 answers |
| Input tokens | 6,040 |
| Output tokens | 14,984 |
| Estimated total cost | `$0.005042` |
| Estimated passed-answer cost | `$0.002301` |
| Estimated blocked-answer cost | `$0.002741` |
| Provider latency | min 5.252s / avg 13.148s / max 28.540s |

## Per-Question Baseline

| Question | Grounding | Blocked reason | Input tokens | Output tokens | Latency ms | Estimated cost |
|---|---|---|---:|---:|---:|---:|
| `rag-eval-001` | blocked | `nli_low_entailment` | 623 | 2,880 | 23,629 | `$0.000894` |
| `rag-eval-002` | blocked | `nli_low_entailment` | 632 | 908 | 8,015 | `$0.000343` |
| `rag-eval-003` | blocked | `nli_low_entailment` | 616 | 843 | 7,881 | `$0.000322` |
| `rag-eval-004` | blocked | `nli_low_entailment` | 592 | 908 | 9,755 | `$0.000337` |
| `rag-eval-005` | passed |  | 586 | 1,513 | 12,647 | `$0.000506` |
| `rag-eval-006` | blocked | `nli_low_entailment` | 623 | 1,512 | 13,299 | `$0.000511` |
| `rag-eval-007` | passed |  | 578 | 434 | 5,252 | `$0.000202` |
| `rag-eval-008` | passed |  | 606 | 3,439 | 28,540 | `$0.001048` |
| `rag-eval-009` | blocked | `nli_low_entailment` | 591 | 898 | 7,668 | `$0.000334` |
| `rag-eval-010` | passed |  | 593 | 1,649 | 14,797 | `$0.000545` |

Formula:

```text
estimated_cost_usd =
  input_tokens / 1,000,000 * 0.14
  + output_tokens / 1,000,000 * 0.28
```

## Interpretation

- Cost is low for this 10-question capture (`$0.005042`), but latency remains a
  larger UX concern: average provider latency was 13.148s and the slowest answer
  took 28.540s before local grounding/NLI overhead is considered.
- Blocked answers still consume provider tokens. In this capture, 6 blocked
  answers accounted for `$0.002741`, slightly more than the 4 passed answers
  (`$0.002301`).
- This closes the current price-SLI baseline for the captured `deepseek-v4-flash`
  profile, but it is not an L2/default-preview approval. Prices can change, and
  OpenCode Go subscription/request-limit billing may differ from direct DeepSeek
  token billing; production budgeting should re-check the provider contract.

## Decision

Keep L1 only. Do not flip L2/default preview.

Rationale:

- Price SLI is now estimable for the captured profile.
- Formal clinician/research reviewer sign-off is still pending.
- The `BGE=0.3 + NLI=0.5` profile still needs a separate governance decision
  before any default-provider change.
