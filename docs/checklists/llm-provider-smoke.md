# LLM Provider Smoke Runbook

date: 2026-05-27
scope: local explicit smoke only

Real LLM providers are not default user paths. Run these checks only in a local shell with local secrets. Do not commit keys, copied Authorization headers, provider dashboards, or raw logs containing secrets.

## Baseline Deterministic Check

```powershell
cd backend
Remove-Item Env:\QIYAN_LLM_PROVIDER -ErrorAction SilentlyContinue
@'
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
payload = client.post("/api/rag/answer", json={"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}).json()
print(payload["provider_name"])
print(payload["retrieval"]["strategy"])
print(payload["grounding"]["status"])
print(payload["grounding"]["policy"])
print(payload["grounding"]["provider_native_grounding"])
print(payload["grounding"]["tool_name"], payload["grounding"]["tool_call_count"])
print(payload["grounding"]["cited_claim_count"], payload["grounding"]["claim_count"])
print(len(payload["grounding"]["structured_claims"]))
print(payload["input_tokens"], payload["output_tokens"])
print(payload["disclaimer"])
'@ | & .\.uv-test-venv\Scripts\python.exe -
```

Expected:

- `provider_name == "deterministic"`
- `retrieval.strategy == "keyword"`
- `grounding.status == "skipped"`
- `grounding.policy == "structured_claim_refs_v3"`
- `grounding.provider_native_grounding == False`
- `grounding.tool_name is None` and `grounding.tool_call_count == 0`
- `grounding.cited_claim_count == 0` and `grounding.claim_count == 0`
- `grounding.structured_claims == []`
- token fields are `None`
- disclaimer is `非诊断结论、需结合临床。`

## OpenCode Go Live Smoke (Preferred)

```powershell
cd backend
$env:QIYAN_LLM_PROVIDER="opencode_go"
$env:QIYAN_OPENCODE_GO_API_KEY="<local-secret>"
$env:QIYAN_OPENCODE_GO_MODEL="deepseek-v4-flash"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS="1200"
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

另开终端：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/rag/answer" `
  -ContentType "application/json" `
  -Body '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}'
```

Expected success:

- HTTP 200
- `provider_name == "opencode_go"`
- answer is non-empty
- citations are still local backend citations
- disclaimer is returned by backend
- `input_tokens` / `output_tokens` are numeric when gateway returns `usage`
- Preferred grounding: `grounding.policy == "opencode_go_tool_use_v1"`, `grounding.provider_native_grounding == true`, `grounding.tool_name == "record_grounded_claims"`, and `grounding.tool_call_count >= 1`.
- Compatibility grounding: if the gateway/model rejects tools but returns valid structured claims JSON on retry, `grounding.policy == "structured_claim_refs_v3"` and `grounding.provider_native_grounding == false`.
- `grounding.status == "passed"` only when accepted tool claims or structured JSON claims use supplied evidence IDs, for example `{"claims":[{"text":"...","evidence_refs":["chunk-..."]}]}`.
- If the provider returns prose, empty claims, malformed tool arguments, missing evidence refs, or evidence IDs outside the current citations, `grounding.status == "blocked"` and `answer` is the hard-block copy.
- For reasoning models, keep `QIYAN_OPENCODE_GO_MAX_TOKENS` high enough for final `content`; with very low values the gateway may return only `reasoning_content`, which the provider treats as an invalid empty answer and falls back to deterministic.

Fallback check:

- Unset or corrupt `QIYAN_OPENCODE_GO_API_KEY`.
- Expected HTTP 200 with `provider_name == "deterministic"` and token fields `null`.
- Warning logs must not contain the secret.

## Anthropic Live Smoke (Later Optional)

Run this only if the team later has an Anthropic subscription/key. It is not the current priority path.

```powershell
cd backend
$env:QIYAN_LLM_PROVIDER="anthropic"
$env:ANTHROPIC_API_KEY="<local-secret>"
$env:QIYAN_ANTHROPIC_MODEL="claude-haiku-4-5"
$env:QIYAN_ANTHROPIC_MAX_TOKENS="160"
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

另开终端：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/rag/answer" `
  -ContentType "application/json" `
  -Body '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}'
```

Expected success:

- HTTP 200
- `provider_name == "anthropic"`
- answer is non-empty and is rebuilt from accepted tool claims, not raw provider prose
- citations and disclaimer remain backend-controlled
- token fields reflect Anthropic usage when available
- `grounding.policy == "anthropic_tool_use_v1"`
- `grounding.provider_native_grounding == true`
- `grounding.tool_name == "record_grounded_claims"` and `grounding.tool_call_count >= 1`
- `grounding.status == "passed"` only when the provider called the strict `record_grounded_claims` tool with claims that use supplied evidence IDs.
- `grounding.structured_claims` records the accepted tool claims.
- If the provider returns only prose, calls the wrong tool, sends malformed tool input, sends empty claims, omits evidence refs, or uses evidence IDs outside the current citations, `grounding.status == "blocked"` and `answer` is the hard-block copy.

Fallback check:

- Unset `ANTHROPIC_API_KEY`.
- Expected HTTP 200 with deterministic fallback and no secret in logs.

## Smoke Record

| Date | Provider | Model | Env path | Result | Policy | Tool | Latency | Input tokens | Output tokens | Fallback? | Notes |
|---|---|---|---|---|---|---|---:|---:|---:|---|---|
| 2026-05-27 | deterministic | n/a | default | passed via TestClient | structured_claim_refs_v3 | n/a | n/a | null | null | n/a | provider/retrieval/grounding/token/disclaimer shape verified; grounding skipped by design |
| 2026-05-27 | opencode_go | deepseek-v4-flash | user-provided key, local env only | historical pass under v2 | pre-v3 | n/a | n/a | 396 | 639 | no | `max_tokens=1200`; this row predates structured claim grounding v3 |
| 2026-05-27 | opencode_go | deepseek-v4-flash | user-provided key, TestClient env only | historical pass under v2 | pre-v3 | n/a | n/a | 396 | 722 | no | this row predates structured claim grounding v3; rerun before treating live provider as passed |
| 2026-05-27 | anthropic | claude-haiku-4-5 | local key required | later optional / pending key | anthropic_tool_use_v1 | record_grounded_claims | n/a | n/a | n/a | not run |后置路径；当前无订阅时不用跑 |
| 2026-05-28 | opencode_go | deepseek-v4-flash | user-provided key, local env only | partial / fallback | structured_claim_refs_v3 | n/a | n/a | null | null | yes | `/api/rag/answer` reached provider path but fell back to deterministic after OpenCode Go HTTP 500 / ConnectError; direct gateway probe authenticated and returned JSON-like content, but one low-token response was truncated before the closing brace. No key or raw Authorization header recorded. |
| 2026-05-28 | opencode_go | qwen3.5-plus | user-provided key, direct gateway probe | failed | n/a | n/a | n/a | n/a | n/a | n/a | Gateway returned 429 insufficient quota from upstream provider. |
| 2026-05-28 | opencode_go | glm-5.1 | user-provided key, direct gateway probe | failed | n/a | n/a | n/a | n/a | n/a | n/a | Gateway returned HTTP 500 from upstream provider. |
| 2026-05-30 | opencode_go | deepseek-v4-flash | user-provided key, local env only | passed via compatibility grounding | structured_claim_refs_v3 | n/a | n/a | 355 | 837 | no provider fallback | Native tool/function calling did not surface in the response; provider retried/used structured claims compatibility path and grounding passed with 3/3 cited claims. PowerShell display showed mojibake for Chinese text; re-run with UTF-8 console/output capture before judging user-facing copy. No key or raw Authorization header recorded. |

## Boundary

Successful live smoke does not mean trustworthy medical generation is complete. OpenCode Go is the preferred current live path: native tool-use grounding verifies that the provider called the expected function tool and used allowed evidence IDs, while structured claim grounding v3 remains the compatibility path when tool calling is unavailable. Anthropic native grounding is retained for later optional smoke when a subscription/key exists. Neither path is semantic fact verification. Do not default-enable real LLM answers until semantic grounding evaluation, cost/latency logging, and privacy wording are implemented.
