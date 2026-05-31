# Real LLM Enablement Runbook

date: 2026-05-31
scope: how to safely turn the real `opencode_go` provider on/off for Qiyan Nexus RAG
decision: governed by ADR-0012; data flow by ADR-0011

This runbook is operational. For the *why* and the hard invariants, read
`docs/adr/0012-real-llm-enablement.md`. For smoke-test mechanics, read
`docs/guides/opencode-go-bge-smoke-test.md`.

## Hard invariants (must hold whenever a real provider is on)

These are enforced by code + tests; do not disable them to "make it work":

1. Disclaimer `非诊断结论、需结合临床。` is byte-identical in every answer.
2. The grounding gate is always on for external providers (structured claims +
   evidence-ID whitelist + BGE semantic threshold). Failed grounding → hard-block
   text, `grounding.status="blocked"`; an unverified draft is never shown.
3. Missing key / HTTP error / gateway failure / empty content → fall back to
   deterministic. `/api/rag/answer` never hard-fails for the user.
4. The API key lives only in the environment. Never commit it or log it.

## Maturity levels (ADR-0012 §4)

- **L1 — controlled smoke / demo (enabled now).** Real provider in a local or
  controlled environment with the gate on. `semantic_low_support` blocks are
  expected and are the hallucination guardrail working.
- **L2 — default preview path (NOT enabled).** Blocked on: threshold recalibration
  with real-LLM-style claims, real per-token price config + SLI baseline, and a
  human reviewer walkthrough. Do not flip the default to a real provider until
  these are done.

## Enable (L1 controlled smoke / demo)

PowerShell (Windows). The key is read from your User-scope env var; it is never
written to a file.

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"
$env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.78"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4000"   # REQUIRED: 1200 silently degrades to fallback
# Optional cost SLI: set real contract prices (USD per million tokens)
$env:QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK = "0.0"
$env:QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK = "0.0"
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

Model-specific constraints (from the 2026-05-31 live smoke):

- `deepseek-v4-flash` runs in thinking mode and **rejects forced tool_choice**
  (HTTP 400). The supported grounding route is structured claims v3, not
  provider-native tool use. Do not expect `tool_call_count > 0` with this model.
- `max_tokens` must be ≥4000 so content survives after reasoning. At 1200 the
  response is `finish_reason=length` with empty content → deterministic fallback.

## Verify it is actually live

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"; $env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.78"; $env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4000"
$env:PYTHONUTF8 = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\smoke_opencode_go_bge.py
```

Expected: `Provider: opencode_go` (not `deterministic`). If you see
`deterministic`, the provider fell back — check the warning line:
- `missing API key` → key not in this process env.
- `ValueError status=None` with empty content → raise `max_tokens`.
- HTTP 400 with tools → that is the forced-tool_choice rejection; the provider
  already retries the no-tools structured path, so this alone should not block.

## Observe (SLI)

Each `/api/rag/answer` emits a secret-free structured log line:

```
rag_sli provider=<name> grounding=<status> latency_ms=<int> input_tokens=<int> output_tokens=<int> cost_usd=<float|None> strategy=<name>
```

and the response carries `sli.provider_latency_ms` + `sli.estimated_cost_usd`
(cost is `null` unless both price env vars are set). The `/rag` UI and Markdown
export surface latency + cost. Watch for: rising `blocked` rate (threshold too
strict), latency spikes, cost drift.

## Roll back (instant, no code change)

```powershell
$env:QIYAN_LLM_PROVIDER = "deterministic"   # or Remove-Item Env:\QIYAN_LLM_PROVIDER
```

Restart the server. This is the only and sufficient rollback: the default path is
offline deterministic with no external egress.

## Before promoting to L2 (default preview)

1. ~~Expand `backend/data/evals/grounding_semantic_pairs.json` with real-LLM-style
   claims (paraphrases, multi-chunk summaries) and re-run
   `run_grounding_semantic_separation`; pick a threshold (candidate 0.55–0.72)
   that keeps faithful paraphrases from being over-blocked.~~ **Done 2026-06-01 —
   result: blocked.** The harder fixture (`grounding_semantic_pairs_bge.json`,
   `scripts/sweep_threshold_recalibration.py`) shows faithful paraphrases
   (0.863–0.963) and on-topic hard negatives (0.736–0.870) overlap on bge cosine
   (gap −0.007). No threshold separates them; the candidate band would admit every
   hard negative. Root cause: BGE measures similarity, not entailment. The
   threshold was **not** lowered. L2-by-threshold is closed; unlocking L2 needs a
   different gate (Chinese NLI/entailment or claim verification). See
   `docs/evaluations/2026-06-01-threshold-recalibration.md` and ADR-0012's
   2026-06-01 update.
2. Configure real `QIYAN_OPENCODE_GO_PRICE_*` and record an SLI baseline.
3. Run a human reviewer walkthrough per
   `docs/checklists/internal-preview-smoke.md` and record feedback.
4. Only then update the default and the fact-source docs.
