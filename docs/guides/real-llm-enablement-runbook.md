# Real LLM Enablement Runbook

date: 2026-05-31 (updated 2026-06-08 for router.team / gpt-5.5 switch)
scope: how to safely turn the real `opencode_go` provider on/off for Qiyan Nexus RAG
decision: governed by ADR-0012; data flow by ADR-0011

This runbook is operational. For the *why* and the hard invariants, read
`docs/adr/0012-real-llm-enablement.md`. The older
`docs/guides/opencode-go-bge-smoke-test.md` is historical evidence only and
must not be executed as a current setup guide.

## 2026-06-08 Provider switch — router.team gateway + gpt-5.5

The default `opencode_go` configuration was switched from
`opencode.ai/zen/go/v1` + `deepseek-v4-flash` to `ai.router.team/v1` +
`gpt-5.5`. The provider class, `.name`, env var prefix, and grounding policy
are unchanged — only the gateway
URL, model name, and `max_tokens` default (1200 → 4096). All sections below
referencing `deepseek-v4-flash` describe **historical** findings from prior
smoke runs; they remain accurate as historical evidence but the live model is
now gpt-5.5. New baselines (price SLI, NLI pass rate, latency) should be
captured with gpt-5.5 before relying on them for governance decisions.

Key model-level differences vs the previous deepseek-v4-flash:

- gpt-5.5 via router.team does not use thinking-mode reasoning tokens, so
  `max_tokens=4096` is adequate (previously 4000 was the minimum to survive
  reasoning).
- Forced `tool_choice` is expected to work (this was the OpenAI-spec default
  the provider already implements; deepseek-v4-flash rejected it with HTTP 400
  and the provider's no-tools structured retry path covered that).
- Pricing is unknown until a router.team contract baseline is recorded; keep
  `QIYAN_OPENCODE_GO_PRICE_*` at `0.0` until then so `estimated_cost_usd` stays
  `null` instead of surfacing a guessed price.

---

## Hard invariants (must hold whenever a real provider is on)

These are enforced by code + tests; do not disable them to "make it work":

1. Disclaimer `非诊断结论、需结合临床。` is byte-identical in every answer.
2. The grounding gate is always on for external providers (structured claims +
   evidence-ID whitelist + BGE semantic threshold). Failed grounding → hard-block
   text, `grounding.status="blocked"`; an unverified draft is never shown.
3. Missing key / HTTP error / gateway failure / empty content → fall back to
   deterministic. `/api/rag/answer` never hard-fails for the user.
4. The API key lives only in the environment. Never commit it or log it.
5. Claim scope is constrained before generation: each claim should cite exactly
   one supplied evidence ID and be directly entailed by that evidence text. The
   system prompt forbids cross-citation synthesis and unsupported efficacy,
   target, quality-of-life, causality, or guideline-status claims.

## Maturity levels (ADR-0012 §4)

- **L1 — controlled smoke / demo (enabled now).** Real provider in a local or
  controlled environment with the gate on. `semantic_low_support` blocks are
  expected and are the hallucination guardrail working.
- **L2 — default preview path (NOT enabled).** The reviewer-verdict delta and
  price SLI baseline are now complete. Remaining blocker: a governance decision
  on whether the lower-BGE-prefilter + NLI profile should enter L2/default-preview
  discussion. Do not flip the default to a real provider unless ADR-0012 is
  explicitly updated with that decision.

## Enable (L1 controlled smoke / demo)

PowerShell (Windows). The key is read from your User-scope env var; it is never
written to a file.

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"
$env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.78"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4096"   # gpt-5.5 default; deepseek-v4-flash needed >=4000
# Optional cost SLI: set real prices (USD per million tokens).
# Keep these unset or 0.0 until the router.team/gpt-5.5 contract price is known.
# The 2026-06-02 deepseek-v4-flash baseline is historical evidence, not a
# router.team/gpt-5.5 budget.
Remove-Item Env:\QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK -ErrorAction SilentlyContinue
Remove-Item Env:\QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK -ErrorAction SilentlyContinue
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

Current model note (2026-06-08):

- The current opt-in smoke default is router.team `gpt-5.5` with
  `QIYAN_OPENCODE_GO_MAX_TOKENS=4096`.
- Price SLI, NLI pass rate, latency, and L2 governance baselines for gpt-5.5 are
  not yet recorded. Keep cost env vars unset/0.0 until the contract price is
  known.

Historical model-specific constraints (from the 2026-05-31 deepseek-v4-flash
live smoke):

- `deepseek-v4-flash` runs in thinking mode and **rejects forced tool_choice**
  (HTTP 400). The supported grounding route is structured claims v3, not
  provider-native tool use. Do not expect `tool_call_count > 0` with this model.
- `max_tokens` must be ≥4000 so content survives after reasoning. At 1200 the
  response is `finish_reason=length` with empty content → deterministic fallback.

Claim-quality constraints (2026-06-01 prompt/schema v2):

- The provider is instructed to output 1-3 short claims.
- Each claim may cite only one evidence ID.
- In the prompt payload, `证据文本（claim 只能基于此字段）` is the only field the
  model should use as factual support; title/source/reason/confidence are
  metadata for traceability, not facts to expand.
- 2026-06-02 live validation recorded 14/14 claims with exactly one evidence ref,
  0 unsupported refs, 0 schema parse failures, and 4/10 answers passed under the
  evaluation profile `BGE=0.3 + NLI=0.5`. See
  `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`.
- 2026-06-02 price SLI baseline uses `deepseek-v4-flash` input `$0.14` / 1M
  tokens and output `$0.28` / 1M tokens. The 10-question live capture estimates
  `$0.005042` total cost. See
  `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`.

## Verify it is actually live

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"; $env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.78"; $env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4096"
$env:PYTHONUTF8 = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\smoke_opencode_go_bge.py
```

Expected: `Provider: opencode_go` (not `deterministic`). If you see
`deterministic`, the provider fell back — check the warning line:
- `missing API key` → key not in this process env.
- `ValueError status=None` with empty content → raise `max_tokens`.
- HTTP 400 with tools → that is the forced-tool_choice rejection; the provider
  already retries the no-tools structured path, so this alone should not block.

## Capture claim-quality validation data

Use this when validating prompt/schema quality, not as a default-preview
configuration. It intentionally lowers the BGE cosine prefilter to `0.3` so the
NLI entailment gate can evaluate real cross-lingual/paraphrased claims.

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4096"
$env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.3"
$env:QIYAN_NLI_BACKEND = "transformers"
$env:QIYAN_NLI_THRESHOLD = "0.5"
$env:PYTHONUTF8 = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\capture_real_answer_claims.py
```

Expected output: `backend/data/runtime/captured_real_claims_live_<timestamp>.json`.
Do not commit this runtime JSON. Convert it into an evaluation note under
`docs/evaluations/` with aggregate counts, blocked reasons, semantic/NLI score
ranges, and reviewer notes for any passed answers.

For the 2026-06-02 capture, use the existing delta-only reviewer packet instead
of repeating the 2026-06-01 §4c walkthrough:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\build_reviewer_packet.py `
  --input data\runtime\captured_real_claims_live_20260602_0846.json `
  --output ..\docs\evaluations\2026-06-02-l2-passed-claims-reviewer-packet.md `
  --question-ids rag-eval-005,rag-eval-007,rag-eval-008,rag-eval-010
```

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
   `backend/scripts/sweep_threshold_recalibration.py`) shows faithful paraphrases
   (0.863–0.963) and on-topic hard negatives (0.736–0.870) overlap on bge cosine
   (gap −0.007). No threshold separates them; the candidate band would admit every
   hard negative. Root cause: BGE measures similarity, not entailment. The
   threshold was **not** lowered. L2-by-threshold is closed; unlocking L2 needs a
   different gate (Chinese NLI/entailment or claim verification). See
   `docs/evaluations/2026-06-01-threshold-recalibration.md` and ADR-0012's
   2026-06-01 update.

   **Update (2026-06-01): the NLI gate is implemented (opt-in, default off).** A
   `mDeBERTa-v3-mnli-xnli` entailment gate separates faithful claims (~0.99) from
   on-topic hard negatives (≤0.001) with 0 false accepts where cosine had 7/7.
   Enable with `QIYAN_NLI_BACKEND=transformers` + `QIYAN_NLI_THRESHOLD=0.5`
   (lazy-loads ~560 MB). It runs after the cosine pre-filter and blocks with
   `nli_low_entailment`. This resolves the §4a technical limitation but is **not**
   an automatic L2 flip — still validate on a larger labeled set + pick a
   production threshold, fold the NLI forward-pass latency/cost into the SLI
   baseline, and keep reviewer verdicts separate from the already-completed
   §4c gate walkthrough. See
   `docs/evaluations/2026-06-01-nli-grounding-spike.md`.
2. Configure real `QIYAN_OPENCODE_GO_PRICE_*` and record an SLI baseline.
   **Done 2026-06-02 for the captured `deepseek-v4-flash` profile.** Baseline:
   6,040 input tokens + 14,984 output tokens → `$0.005042` estimated total cost
   at `$0.14` / 1M input and `$0.28` / 1M output. Re-check prices before
   production budgeting.
3. ~~Run a human reviewer walkthrough per
   `docs/checklists/internal-preview-smoke.md` and record feedback.~~ **Done
   2026-06-01 for gate/fallback/rollback/UI metadata.** Do not repeat this as
   the next L2 step.
4. ~~Re-run live claim capture after prompt/schema v2 and record claim count,
   evidence-ref count, blocked reasons, semantic scores, and entailment scores.~~
   **Done 2026-06-02.** Result: 10 questions, 14 claims, 14/14 exactly one
   evidence ref, 4 answers passed, 6 blocked by `nli_low_entailment`, no raw draft
   leakage. This improves L1 but does not flip L2; see
   `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`.
5. ~~Before any default change, have a formal clinician/research reviewer confirm
   or revise the Codex technical verdicts in
   `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`.~~ **Done
   2026-06-02 by user confirmation: 6 supported / 0 unsupported / 0 unclear.**
   Next, make a separate ADR-quality decision on whether `BGE=0.3 + NLI=0.5` is
   an acceptable default-preview profile.
