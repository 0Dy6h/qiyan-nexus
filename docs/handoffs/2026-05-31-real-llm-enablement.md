# Real LLM Enablement Final Mile Handoff

date: 2026-05-31
status: completed (L1 controlled-smoke enablement); L2 default-preview gated
focus: complete the C-phase "MVP-A LLM 化" tail — live smoke, SLI, PIPL, enablement decision

---

## What this session delivered

The 2026-05-21 roadmap A/B/C slices were already implemented; this session closed the
last stated gap ("real LLM in a governed path") in six slices. Default RAG remains
offline deterministic. Real `opencode_go` is now enablable at L1 (controlled smoke/demo)
with documented invariants and instant rollback.

### Slice 0 — smoke script fixed (commit 31848d1)
`scripts/smoke_opencode_go_bge.py` referenced non-existent response fields
(`grounding.blocked_claims`, `.semantic_backend`, `.semantic_scores`,
`retrieval.source`/`.top_k`) that would crash on the success path. Re-aligned to the
real schema (`structured_claims`, `semantic_threshold`, `min_semantic_score`,
`applied_source`/`applied_top_k`) and verified every field resolves.

### Slice 1 — live smoke + evidence (commit 9ffd716)
Ran the real key-backed smoke. `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`
records three real findings:
1. `deepseek-v4-flash` (thinking mode) **rejects forced tool_choice (HTTP 400)** —
   real grounding goes through structured claims v3, not provider-native tool use.
2. Default `max_tokens=1200` exhausts the budget on reasoning → empty content →
   deterministic fallback. **≥4000 is required** for the live path to engage.
3. At threshold 0.78, BGE **blocked all 3 live drafts on `semantic_low_support`** — the
   gate works (no hallucination shown), but 0.78 is strict against real paraphrasing
   claims. Threshold recalibration is the L2 blocker.
Also hardened the script to force UTF-8 stdout (Windows GBK console crashed on emoji/CJK).

### Slice 2 — cost/latency SLI (commit 7c31ae8)
- New `ProviderSli` nested model on `RagAnswerResponse`: `provider_latency_ms`,
  `estimated_cost_usd`.
- `services/rag.py` times only `generate_answer`; cost = tokens × env per-Mtok prices
  (`QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK` / `_OUTPUT_PER_MTOK`, default 0.0 → null,
  never a guessed price). Deterministic: latency=int, cost=null.
- Secret-free `rag_sli` structured log line (provider, grounding, latency, tokens, cost,
  strategy — no question/chunk text, no key).
- Surfaced in `/rag` retrieval metadata + Markdown export.
- Verified end-to-end against the live provider: latency≈11768ms, cost computed from
  real tokens with sample prices, grounding still blocked correctly.
- Tests: backend 304→308; frontend 137→140.

### Slice 3 — PIPL data flow (commit 9965d84, ADR-0011)
`/compliance` privacy section now states: default deterministic is offline; enabling
`opencode_go` sends question + cited chunks to an external gateway; PIPL
minimal-necessary + no patient identity; explicit not-sent list. ADR-0011 records the
data-flow boundary.

### Slice 4 — enablement decision (commit b75164b, ADR-0012 + runbook)
- ADR-0012: deterministic-default invariant, always-on grounding gate, safe fallback,
  secret-only-env. Two maturity levels: **L1 controlled smoke/demo = enabled now**;
  **L2 default preview = gated** on threshold recalibration + real price/SLI baseline +
  human reviewer walkthrough.
- `docs/guides/real-llm-enablement-runbook.md`: enable/verify/observe/rollback steps,
  model constraints, instant rollback via `QIYAN_LLM_PROVIDER=deterministic`.
- Refreshed `docs/current-state.md` + `README.md` (live smoke done, SLI, max_tokens≥4000).

### Slice 5 — review + gauntlet + handoff (this commit)
- Security review: session diff has no secrets; SLI log is secret-free; `.env`,
  `uploads/`, `runtime/`, `model_cache/` all gitignored.
- Full gauntlet green: backend ruff/mypy clean, **308 passed**; frontend **141 passed**,
  typecheck + build clean.

---

## Current enablement state

- **Default**: `deterministic`, offline, no egress, no key. Unchanged.
- **L1 enabled**: real `opencode_go` for controlled smoke/demo with gate on. Use the
  runbook. Expect `semantic_low_support` blocks (guardrail working).
- **L2 NOT enabled**: do not flip the default to a real provider until the three L2
  prerequisites are met.

## Production-ish config for L1 smoke

```
QIYAN_LLM_PROVIDER=opencode_go
QIYAN_OPENCODE_GO_API_KEY=<env-only>
QIYAN_EMBEDDING_BACKEND=bge
QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.78
QIYAN_OPENCODE_GO_MAX_TOKENS=4000        # 1200 silently falls back
QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK=<real>   # for cost SLI
QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK=<real>
```

## Recommended next action (L2 promotion main line)

1. Expand `backend/data/evals/grounding_semantic_pairs.json` with real-LLM-style claims
   (paraphrases, multi-chunk summaries) from the smoke output; re-run
   `run_grounding_semantic_separation` and pick a threshold in 0.55–0.72 that does not
   over-block faithful paraphrases.
2. Configure real per-token prices and capture an SLI baseline (latency p50/p95, cost).
3. Run the human reviewer walkthrough (`docs/checklists/internal-preview-smoke.md`),
   record feedback.
4. Only then switch the default and update fact-source docs.

## Key files

New:
- `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`
- `docs/adr/0011-external-llm-data-flow-and-pipl.md`
- `docs/adr/0012-real-llm-enablement.md`
- `docs/guides/real-llm-enablement-runbook.md`

Modified:
- `backend/app/core/config.py`, `backend/app/schemas/rag.py`, `backend/app/services/rag.py`
- `backend/scripts/smoke_opencode_go_bge.py`, `backend/.env.example`
- `backend/tests/test_config.py`, `backend/tests/test_rag_service.py`
- `frontend/lib/api/rag.ts`, `frontend/lib/rag-export.ts`,
  `frontend/components/RagAnswerClient.tsx`, `frontend/lib/compliance-page.ts`
- frontend tests: `rag-export`, `client-section-consistency`, `compliance-page`
- `docs/current-state.md`, `README.md`

## Git history (this session)

```
b75164b docs(llm): real LLM enablement decision (ADR-0012) + runbook; refresh fact sources
9965d84 docs(compliance): disclose external LLM data flow + PIPL handling (ADR-0011)
7c31ae8 feat(rag): add provider latency + cost SLI to API, /rag UI, and export
9ffd716 feat(smoke): record live opencode_go + BGE smoke findings and harden smoke script
31848d1 fix(smoke): align opencode_go BGE smoke script with real RAG schema fields
```
