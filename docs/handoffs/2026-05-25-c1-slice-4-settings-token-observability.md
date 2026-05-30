# C1 slice 4/5 — MODEL/MAX_TOKENS 进 Settings + AnswerDraft 加 token 字段 + caplog 锁

date: 2026-05-25
slice: C1.4 of C1 (Anthropic 真接入)
branch: feat/c1-anthropic-provider
status: verified (Hermes gauntlet + Claude Code review passed)

## Scope

(A) Settings 注入 MODEL/MAX_TOKENS：运维可通过 `QIYAN_ANTHROPIC_MODEL` / `QIYAN_ANTHROPIC_MAX_TOKENS` 环境变量切 model + tune max_tokens，类常量删除退化为 Settings default。
(B) AnswerDraft 加可选 `input_tokens / output_tokens`：AnthropicProvider 成功路径从 `response.usage` 提取，DeterministicProvider / MockClaudeProvider 保持 None。本 slice 不冒泡到 RagAnswerResponse（C2 observability 的事）。
(C) Fallback warning log 加 caplog parametrized test 锁住 4 个 APIError 子类。

## Out of Scope

- 真 key live smoke (C1.5)
- token 字段冒泡到 API response / 前端 UI (C2)
- prompt caching / tool use / citation grounding 的高级特性 (C1.5+)

## Changes

### backend/app/core/config.py (+4/-0)

- `Settings` 加 `anthropic_model: str = "claude-haiku-4-5"` + `anthropic_max_tokens: int = 1024`
- `get_settings()` 读 `os.getenv("QIYAN_ANTHROPIC_MODEL", "claude-haiku-4-5")` + `int(os.getenv("QIYAN_ANTHROPIC_MAX_TOKENS", "1024"))`
- 非法数值 → ValueError（运维 fail-fast，不默默回退）

### backend/app/services/llm/provider.py (+2/-0)

- `AnswerDraft` 加 `input_tokens: int | None = None` + `output_tokens: int | None = None`
- DeterministicProvider / MockClaudeProvider 不设 → 默认 None
- rag.py 只用 `.text` / `.provider_name` → 零影响

### backend/app/services/llm/anthropic_provider.py (+11/-4)

- 删除类常量 `MODEL` / `MAX_TOKENS`
- 顶部 add `from app.core.config import get_settings`（module top，lru_cache 已是零成本 lazy）
- `generate_answer` 入口调 `settings = get_settings()`，用 `settings.anthropic_model` / `settings.anthropic_max_tokens`
- 成功路径防御性提取 token：
  ```python
  usage = getattr(response, "usage", None)
  input_tokens = getattr(usage, "input_tokens", None)
  output_tokens = getattr(usage, "output_tokens", None)
  ```
  写入 AnswerDraft
- empty citations 短路 + fallback 路径不填 token（默认 None）
- 评审后：`getattr(x, attr, None) if x else None` → 简化为 `getattr(x, attr, None)`（getattr 本身对 None 也返回 default）

### backend/tests/test_anthropic_provider.py (+130/-2)

新增 6 个 test function（parametrized×4 = pytest 收集 9 个 test case）：
- `test_settings_override_model_and_max_tokens` — monkeypatch.setenv，cache_clear，断言 kwargs 对
- `test_default_settings_model_and_max_tokens` — 不设 env，断言默认值
- `test_token_usage_extracted_from_response` — mock usage.input_tokens=123, output_tokens=456
- `test_token_usage_none_when_usage_missing` — response.usage=None
- `test_fallback_draft_has_none_tokens` — APIError 子类 fallback 路径 token=None
- `test_fallback_logs_warning_with_error_type_and_message` — parametrize 4 错误，caplog 锁前缀 + error_type
- 评审后：删 dead `from __future__ import annotations`

`test_llm_provider.py` 未改动 — AnswerDraft 默认 None 向后兼容。

### Anthropic SDK Usage 类型

```python
from anthropic.types import Usage
# input_tokens: int (硬字段)
# output_tokens: int (硬字段)
# cache_creation_input_tokens: Optional[int]
# cache_read_input_tokens: Optional[int]
# ...
```

## Verification

### Hermes 独立 gauntlet

```
cd /home/dyh2026/Projects/Tcm_tech/backend
.venv/bin/python -m ruff format --check app tests   # 73 files already formatted
.venv/bin/python -m ruff check app tests             # All checks passed!
.venv/bin/python -m mypy app                         # Success: no issues found in 43 source files
.venv/bin/python -m pytest -q                        # 221 passed in 3.17s (212 baseline + 9 new)
```

### Claude Code 独立评审 (freemodel + claude-opus-4-7)

```json
{
  "passed": true,
  "security_concerns": [],
  "logic_errors": [],
  "suggestions": [
    "from __future__ import annotations 在本 diff 中无使用 → 已采纳，删掉",
    "getattr(usage, 'x', None) if usage else None 冗余 → 已采纳，简化",
    "int(os.getenv('MAX_TOKENS')) 非法值抛 ValueError 是 fail-fast → 同设计",
    "lru_cache test 用 try/finally cache_clear 正确；pytest-xdist 无 race 问题",
    "caplog parametrized 同时锁 prefix + error_type → 建议结构化 log 时提成常量"
  ],
  "summary": "C1 slice 4/5 干净落地：env override + token 透传 + 4 子类 caplog 锁定都到位，无安全或逻辑红线。"
}
```

采纳 #1 + #2，re-verify 仍 221 passed。

## 三端联动执行日志

1. **Hermes 准备**：读 config.py (dataclass + lru_cache)、Usage 类型 (硬字段 input_tokens/output_tokens)、rag.py 调用点 (只用 .text/.provider_name)
2. **派活 OpenCode** (`opencode-go/deepseek-v4-pro`)：~4 min 完成，自迭代 ruff format + check
3. **Hermes 独立验收**：scope clean (4 files)，ruff/mypy/pytest 全绿
4. **Claude Code 评审**：passed=true，0 security/logic，2 条采用 + re-verify
5. **commit + handoff**：本文件 + commit 入分支

## Hermes terminal 新坑 (secret redaction 坍 ~/.bashrc 提取)

在 C1.3 复用 `/tmp/run-claude-review.sh` 时，Hermes secret redaction 把 `write_file` / `terminal` 内容里的 `FREEMODEL_CLAUDE_API_KEY=*** 的 `=` 也 redact 为 `=***`，导致：
- awk 的 `/^export FREEMODEL_CLAUDE_API_KEY=*** .../` → unterminated regexp
- sed 的 `s/^export FREEMODEL_CLAUDE_API_KEY=*** .../` → unterminated `s' command

**workaround**：改用 `PS1='dummy' + source ~/.bashrc 2>/dev/null` 让 bashrc 的 `case $- in *i*) return` 短路不触发，直接拿 `$FREMODEL_CLAUDE_API_KEY` 变量。

→ 待沉淀到 wiki/concepts/hermes-known-boundaries.md (本 session 结束后做)

## Next session recipe

C1.5 (live smoke with 真 Anthropic API key)：
1. 用户提供 `ANTHROPIC_API_KEY` + 预算确认
2. 构造 `AnthropicProvider(client=Anthropic())`，调 `generate_answer("测试特应性皮炎", citations=[])` — empty citations 短路直接返回，不打 API
3. 调 `generate_answer("什么是AD", [...real_citations])` → 真实 messages.create → 验证 prompt shape + system prompt 长度 + response content text 不为空
4. 特试 `ANTHROPIC_API_KEY` 错误的 AuthenticationError → fallback → caplog
5. PR review + 收口合 main

C2 (UI observability: token 用量看板 + provider 切换 UI) 等 C1 收口后再启动。
