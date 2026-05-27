# OpenCode Go provider 接入

date: 2026-05-27
status: implemented, backend and frontend gates passed

## Scope

新增后端 LLM provider `opencode_go`，用于通过 OpenCode Go 的 OpenAI-compatible Chat Completions API 调用 `deepseek-v4-flash`。默认 provider 仍是 `deterministic`；只有显式设置 `QIYAN_LLM_PROVIDER=opencode_go` 且提供 `QIYAN_OPENCODE_GO_API_KEY` 时才会调用外部 API。

## Changes

- `backend/app/core/config.py`
  - 新增 `opencode_go_api_key`、`opencode_go_base_url`、`opencode_go_model`、`opencode_go_max_tokens`、`opencode_go_temperature`。
  - 默认 base URL：`https://opencode.ai/zen/go/v1`。
  - 默认模型：`deepseek-v4-flash`。
- `backend/app/services/llm/provider.py`
  - `select_provider()` lazy 注册 `opencode_go`。
- `backend/app/services/llm/opencode_go_provider.py`
  - 使用 `httpx` 调用 `{base_url}/chat/completions`。
  - 请求体为 OpenAI-style `model`、`max_tokens`、`temperature`、`messages`。
  - 成功时解析 `choices[0].message.content`，并将 `usage.prompt_tokens/completion_tokens` 映射到 `AnswerDraft.input_tokens/output_tokens`。
  - 空 citations、缺 key、HTTP/网络/响应结构异常均不让 `/api/rag/answer` 失败；会回退 `DeterministicProvider`，warning 不记录 secret。
- `backend/.env.example`
  - 仅增加 OpenCode Go 变量占位，不包含真实 key。
- `README.md`、`docs/current-state.md`
  - 更新默认 deterministic + 可选 OpenCode Go provider 说明。

## Verification

Focused provider tests:

```bash
cd backend
UV_PROJECT_ENVIRONMENT='D:\Projects\Tcm_tech\backend\.uv-test-venv' uv run python -m pytest \
  tests/test_config.py \
  tests/test_llm_provider.py \
  tests/test_anthropic_provider.py \
  tests/test_opencode_go_provider.py \
  tests/test_rag_service.py \
  -q
# 68 passed
```

Full backend gauntlet:

```bash
cd backend
UV_PROJECT_ENVIRONMENT='D:\Projects\Tcm_tech\backend\.uv-test-venv' uv run python -m ruff format --check app tests
UV_PROJECT_ENVIRONMENT='D:\Projects\Tcm_tech\backend\.uv-test-venv' uv run python -m ruff check app tests
UV_PROJECT_ENVIRONMENT='D:\Projects\Tcm_tech\backend\.uv-test-venv' uv run python -m mypy app
UV_PROJECT_ENVIRONMENT='D:\Projects\Tcm_tech\backend\.uv-test-venv' uv run python -m pytest -q
# ruff format/check clean, mypy clean, 235 passed
```

Frontend gate:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm test
pnpm typecheck
pnpm build
# 107 frontend tests passed, typecheck passed, build passed
```

Notes:

- Windows checkout 的 `backend/.venv` 不是有效 Python 环境，`uv run` 默认会被它挡住；本轮使用 `UV_PROJECT_ENVIRONMENT=D:\Projects\Tcm_tech\backend\.uv-test-venv` 跑测试。
- 初次运行 frontend gate 前本地缺少 `node_modules`，已用 lockfile 安装依赖；未改 `pnpm-lock.yaml`。
- 本轮未在仓库中写入任何真实 API key。
- 未自动运行 live smoke；需要用户在本地 shell 设置 `QIYAN_OPENCODE_GO_API_KEY` 后手工调用 `/api/rag/answer`。

## Manual smoke recipe

PowerShell:

```powershell
cd backend
$env:QIYAN_LLM_PROVIDER="opencode_go"
$env:QIYAN_OPENCODE_GO_API_KEY="<local-secret>"
$env:QIYAN_OPENCODE_GO_MODEL="deepseek-v4-flash"
$env:QIYAN_OPENCODE_GO_MAX_TOKENS="160"
fastapi dev app/main.py
```

Then:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/rag/answer" `
  -ContentType "application/json" `
  -Body '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？","source":"all","top_k":1}'
```

Expected:

- HTTP 200
- `provider_name` is `opencode_go`
- `disclaimer` is `非诊断结论、需结合临床。`
- `citations` is non-empty

Fallback check:

- Set `QIYAN_OPENCODE_GO_API_KEY` to a known bad value and call the same endpoint.
- Expected HTTP 200 with `provider_name="deterministic"` and no secret in logs.
