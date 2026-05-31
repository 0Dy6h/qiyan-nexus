# OpenCode Go + BGE Live Smoke Record

date: 2026-05-31
status: live smoke completed (real API calls); blocking config + grounding findings recorded
provider: opencode_go (`deepseek-v4-flash` via `https://opencode.ai/zen/go/v1`)
embedding backend: bge (`BAAI/bge-small-zh-v1.5`)
semantic threshold: 0.78

## Summary

This record captures the first real (key-backed) live smoke of the `opencode_go` provider
through the full RAG pipeline with BGE semantic grounding. It uses
`backend/scripts/smoke_opencode_go_bge.py` and three AD questions. Findings are reported
as observed; no result is claimed as production-ready.

Three concrete findings:

1. **Provider-native tool grounding is unavailable with this model.** Forcing
   `tool_choice` returns HTTP 400: `Thinking mode does not support this tool_choice`.
   The provider correctly falls back to the structured-claims (v3) JSON path, which the
   model supports and which returns well-formed `{"claims":[...]}` with valid
   `evidence_refs`.
2. **Default `QIYAN_OPENCODE_GO_MAX_TOKENS=1200` is too low for this reasoning model.**
   At 1200, reasoning consumed the entire completion budget (`finish_reason=length`,
   `reasoning_tokens≈1200`, `content` empty) → deterministic fallback for all three
   questions. At `max_tokens=4000` the model emitted populated `content`
   (`finish_reason=stop`) and the live `opencode_go` path engaged with no fallback.
3. **At threshold 0.78, BGE blocked all three live drafts on `semantic_low_support`.**
   The structured claims were well-formed and cited allowed evidence IDs, but at least one
   claim per answer scored below 0.78 against its cited chunk text, so the gate replaced the
   answer with the hard-block text. This is the gate working as designed (no hallucination
   shown), but it also shows 0.78 — calibrated on the 20-pair fixture — is strict against
   real free-form LLM claims that paraphrase or add scope beyond the single cited chunk.

## How it was run

```powershell
cd backend
$env:QIYAN_OPENCODE_GO_API_KEY = [Environment]::GetEnvironmentVariable("QIYAN_OPENCODE_GO_API_KEY","User")
$env:QIYAN_LLM_PROVIDER = "opencode_go"
$env:QIYAN_EMBEDDING_BACKEND = "bge"
$env:QIYAN_GROUNDING_SEMANTIC_THRESHOLD = "0.78"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS = "4000"   # 1200 default is too low for this reasoning model
$env:PYTHONIOENCODING = "utf-8"              # Windows GBK console cannot print ✅/❌ or CJK otherwise
$env:PYTHONUTF8 = "1"
& .\.uv-test-venv\Scripts\python.exe scripts\smoke_opencode_go_bge.py
```

The API key is read from the User-scope environment variable at run time and is never
written to any file, log, README, handoff, or test. Output above is paraphrased/recorded;
no key material appears in this document.

## Raw response-shape probe (throwaway, not committed)

A one-off diagnostic posted directly to `/chat/completions` to isolate the fallback cause:

| Request | HTTP | `finish_reason` | `content` | `tool_calls` | Notes |
|---|---|---|---|---|---|
| `include_tools=True`, forced `tool_choice` | 400 | — | — | — | `Thinking mode does not support this tool_choice` |
| `include_tools=False`, `max_tokens=1200` | 200 | length | empty (len 0) | none | `reasoning_tokens=1200`, budget exhausted |
| `include_tools=False`, `max_tokens=4000` | 200 | stop | valid claims JSON (len 238) | none | `reasoning_tokens≈917` |
| `tool_choice=auto`, `max_tokens=4000` | 200 | stop | valid claims JSON (len 371) | none | model ignores tools, emits JSON content |

Conclusion: with `deepseek-v4-flash`, the supported grounding route is structured-claims v3
(not provider-native tool use), and the budget must leave room for content after reasoning.

## Live smoke results (max_tokens=4000)

All three questions reached the live provider (`provider_name=opencode_go`, no fallback) and
were then blocked by the semantic gate.

| # | Question | Provider | Claims | Min semantic | Status | Blocked reason |
|---|---|---|---:|---:|---|---|
| 1 | 特应性皮炎和肠-脑-皮肤轴有什么关系？ | opencode_go | 3 | 0.716 | blocked | semantic_low_support |
| 2 | 黄芩在治疗特应性皮炎中的作用机制是什么？ | opencode_go | 2 | 0.700 | blocked | semantic_low_support |
| 3 | 中医药治疗特应性皮炎的临床证据有哪些？ | opencode_go | 2 | 0.591 | blocked | semantic_low_support |

Per-claim semantic scores (claim text vs cited chunk text):

Q1 (min 0.716, max 0.881, avg 0.793):
- 0.716 — 特应性皮炎与肠-脑-皮肤轴密切相关，该轴失调表现为肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱。
- 0.782 — 肠道菌群失衡，尤其是双歧杆菌、乳酸杆菌减少，与特应性皮炎发病相关，菌群干预可能有助于恢复免疫稳态。
- 0.881 — 脾虚湿蕴、血虚风燥等中医证候与肠-脑-皮肤轴环节失调存在可解释关联，为特应性皮炎治疗提供靶点。

Q2 (min 0.700, max 0.727, avg 0.714):
- 0.700 — 中医药干预特应性皮炎瘙痒的机制涉及调节IL-31、神经肽等介质，以及瘙痒-搔抓循环的恶性环路。
- 0.727 — 网络药理学分析提示特应性皮炎常用方剂的作用机制常涉及PI3K-Akt、NF-kB、JAK-STAT等关键信号通路。

Q3 (min 0.591, max 0.920, avg 0.756):
- 0.920 — 中西医结合诊疗共识将皮肤屏障维护、规律外用润肤剂、辨证施治与长期管理列为特应性皮炎的核心管理要点。
- 0.591 — 特应性皮炎中医证候研究强调脾虚湿蕴、血虚风燥等证候与皮肤屏障及神经免疫调节之间的联系。

Token usage observed: Q1 in=517 out=1087; Q2 in=503 out=1860; Q3 in=512 out=1619.

## Interpretation

- The grounding gate behaves correctly: well-formed, evidence-ID-valid claims are still
  blocked when their semantic support against the cited chunk falls under threshold. No
  unsupported answer was ever shown to the user; the disclaimer was present in every case.
- The 0.78 threshold (calibrated on the curated 20-pair fixture) is strict against real,
  longer, paraphrasing LLM claims. Several blocked claims (e.g. 0.716, 0.727) are plausibly
  faithful but score below 0.78 because they summarize or add scope beyond the single cited
  chunk. This is a precision/recall tradeoff to resolve with a larger labeled set, not a
  code bug.
- `deepseek-v4-flash` (thinking mode) cannot use forced tool calling; the supported path is
  structured-claims v3. The enablement decision (ADR-0012) must not assume provider-native
  tool grounding for this model.
- `QIYAN_OPENCODE_GO_MAX_TOKENS` must be raised (≥4000 observed-good) for this reasoning
  model; the documented 1200 silently degrades to deterministic fallback.

## Recommended follow-ups (tracked into later slices)

- ADR-0012 enablement: record that the live path is structured-claims v3 (not tool use) for
  `deepseek-v4-flash`, and that `max_tokens` must leave headroom after reasoning.
- Threshold calibration: before enabling a real provider in the default preview path, expand
  `backend/data/evals/grounding_semantic_pairs.json` with real-LLM-style claims and re-run
  `run_grounding_semantic_separation` to choose a threshold that does not over-block faithful
  paraphrases. Candidate range to evaluate: 0.55–0.72.
- Smoke ergonomics: the smoke script prints emoji/CJK and needs `PYTHONUTF8=1` on Windows;
  consider making the script set UTF-8 stdout itself so future runs don't crash on GBK.

## Status of pending items

| Item | Status |
|---|---|
| OpenCode Go live provider reachable with key | done |
| Live path engages without deterministic fallback (max_tokens≥4000) | done |
| Provider-native tool grounding with deepseek-v4-flash | not supported (HTTP 400, thinking mode) |
| Structured-claims v3 grounding path | done (well-formed claims, valid evidence_refs) |
| BGE semantic gate active at 0.78 | done (blocked all 3 on semantic_low_support) |
| Threshold calibrated for real-LLM claims | pending (needs expanded labeled fixture) |
