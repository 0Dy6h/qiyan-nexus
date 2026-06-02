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
5. Claim scope is constrained before generation: each claim should cite exactly
   one supplied evidence ID and be directly entailed by that evidence text. The
   system prompt forbids cross-citation synthesis and unsupported efficacy,
   target, quality-of-life, causality, or guideline-status claims.

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

## Capture claim-quality validation data

Use this when validating prompt/schema quality, not as a default-preview
configuration. It intentionally lowers the BGE cosine prefilter to `0.3` so the
NLI entailment gate can evaluate real cross-lingual/paraphrased claims.

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

Expected output: `backend/data/runtime/captured_real_claims_live_<timestamp>.json`.
Do not commit this runtime JSON. Convert it into an evaluation note under
`docs/evaluations/` with aggregate counts, blocked reasons, semantic/NLI score
ranges, and reviewer notes for any passed answers.

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

   **Update (2026-06-01): the NLI gate is implemented (opt-in, default off).** A
   `mDeBERTa-v3-mnli-xnli` entailment gate separates faithful claims (~0.99) from
   on-topic hard negatives (≤0.001) with 0 false accepts where cosine had 7/7.
   Enable with `QIYAN_NLI_BACKEND=transformers` + `QIYAN_NLI_THRESHOLD=0.5`
   (lazy-loads ~560 MB). It runs after the cosine pre-filter and blocks with
   `nli_low_entailment`. This resolves the §4a technical limitation but is **not**
   an automatic L2 flip — still validate on a larger labeled set + pick a
   production threshold, fold the NLI forward-pass latency/cost into the SLI
   baseline, and run the reviewer walkthrough first. See
   `docs/evaluations/2026-06-01-nli-grounding-spike.md`.
2. Configure real `QIYAN_OPENCODE_GO_PRICE_*` and record an SLI baseline.
3. Run a human reviewer walkthrough per
   `docs/checklists/internal-preview-smoke.md` and record feedback.
4. ~~Re-run live claim capture after prompt/schema v2 and record claim count,
   evidence-ref count, blocked reasons, semantic scores, and entailment scores.~~
   **Done 2026-06-02.** Result: 10 questions, 14 claims, 14/14 exactly one
   evidence ref, 4 answers passed, 6 blocked by `nli_low_entailment`, no raw draft
   leakage. This improves L1 but does not flip L2; see
   `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`.
5. Before any default change, get formal reviewer sign-off on passed claims and
   make a separate ADR-quality decision on whether `BGE=0.3 + NLI=0.5` is an
   acceptable default-preview profile.
