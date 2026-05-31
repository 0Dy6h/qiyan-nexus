# Session Wrap + Handoff — 2026-06-01

branch: feat/l2-real-llm-promotion (9 commits ahead of origin/main; NOT pushed)
default RAG path: offline `deterministic`, unchanged all session
gauntlet at stop: backend 316 passed, frontend 141 passed, mypy/ruff clean

---

## The arc of this session

Goal was the repo-endorsed L2 promotion (make a real LLM the default internal-preview RAG path,
ADR-0012 §4). It turned into a chain of honest findings rather than a forced flip:

1. **Threshold recalibration failed honestly** (`f51ce28`). Built a harder fixture (faithful
   claims from the live smoke + authored on-topic hard negatives) and swept BGE cosine. Faithful
   (0.863–0.963) and hard negatives (0.736–0.870) **overlap** — no threshold separates them.
   Root cause: cosine measures similarity, not entailment. Did **not** lower the threshold
   (would weaken the guardrail). L2-by-threshold closed; stayed at L1.

2. **NLI entailment gate — spiked then built** (`6b46fbc`). Validated that an NLI model
   (`mDeBERTa-v3-base-mnli-xnli`) separates what cosine couldn't: faithful 0.997–0.999, on-topic
   fabrications ≤0.001, 0 false accepts. Implemented as an **opt-in, default-off** second stage
   after the cosine pre-filter (`app/services/nli.py`, `QIYAN_NLI_BACKEND/MODEL/THRESHOLD`,
   `blocked_reason="nli_low_entailment"`). Default behavior byte-identical; CI never loads the model.

3. **Latency + adversarial generalization** (`342ace3`). Measured NLI cost (~840 ms/claim p50,
   ~2.5 s per 3-claim answer, 6.7 s cold load — ~+20% over a real-provider answer). Added 18
   adversarial pairs (number tampering, hedge removal, partial-support leaps, negation,
   overgeneralization, entity splicing, cross-chunk). Combined **32 pairs → 0 false accepts at
   every threshold**; recommended production threshold **0.5**.

## Current state (facts)

- Default RAG: `deterministic`, offline, no key, no egress. **Never changed this session.**
- Real provider: still L1 (controlled smoke/demo) per ADR-0012. No default flip.
- NLI gate: implemented, **default OFF**. Enable with `QIYAN_NLI_BACKEND=transformers` +
  `QIYAN_NLI_THRESHOLD=0.5` (lazy-loads ~560 MB; only runs for external providers after cosine).
- Hard invariants intact: disclaimer byte-identical, gate-on-for-external, safe fallback,
  secret-only-env.

## Loose ends (for next session)

1. **Branch not pushed.** `feat/l2-real-llm-promotion` is 9 commits ahead of `origin/main`
   (6 pre-existing + 3 today). Nothing on remote. Push when ready.
2. **Two uncommitted edits, unrelated to this work, left intentionally untouched:**
   - `.gitignore` — adds `opencode.json` / `opencode.jsonc` / `.opencode/` (local OpenCode config).
   - `AGENTS.md` — adds a Windows pwsh command block + a `CLAUDE.md` nav row.
   These predate my session and are good changes; I did not bundle them onto the feature branch.
   Decide separately whether to commit them (suggest a small `docs/chore:` commit on main or a
   dedicated branch).

## Recommended next action

**Build the real-answer (non-synthetic) validation set.** This is the last technical caveat
before the §4c reviewer walkthrough. The 32-pair result is strong but I authored the negatives;
the live smoke already produced real `opencode_go` answers. Steps:
1. Collect real answers' structured claims + their cited chunks.
2. Label claim-level support (human-in-loop, like the fixtures here).
3. Score with the gate at 0.5; report false-accept/false-reject on real distribution.
Then: optional per-answer NLI batching (cut the ~2.5 s), then §4c reviewer walkthrough, then —
only if all clean — consider flipping the default.

## Key files this session

New: `backend/app/services/nli.py`, `backend/tests/test_grounding_nli.py`,
`backend/data/evals/grounding_semantic_pairs_bge.json`,
`backend/data/evals/grounding_nli_adversarial.json`,
`backend/scripts/{sweep_threshold_recalibration,spike_nli_grounding,bench_nli_latency}.py`,
`docs/evaluations/2026-06-01-{threshold-recalibration,nli-grounding-spike,nli-latency-and-adversarial}.md`,
prior handoffs `docs/handoffs/2026-06-01-*`.

Modified: `backend/app/services/{grounding,rag,eval}.py`, `backend/app/schemas/rag.py`,
`backend/app/core/config.py`, `backend/.env.example`, `backend/pyproject.toml`,
`backend/tests/{test_rag_api,test_grounding_semantic}.py`,
`docs/adr/0012-real-llm-enablement.md`, `docs/current-state.md`,
`docs/guides/real-llm-enablement-runbook.md`.

## Reproduce (offline, after model cached)

```powershell
cd backend
$env:HF_HUB_OFFLINE = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\sweep_threshold_recalibration.py   # cosine overlap
& .\.uv-test-venv\Scripts\python.exe scripts\spike_nli_grounding.py             # NLI separation
& .\.uv-test-venv\Scripts\python.exe scripts\bench_nli_latency.py               # NLI latency
```
