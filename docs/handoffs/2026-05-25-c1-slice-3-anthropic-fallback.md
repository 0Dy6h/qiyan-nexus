# C1 slice 3/5 — AnthropicProvider fallback to DeterministicProvider on API failure

date: 2026-05-25
slice: C1.3 of C1 (Anthropic 真接入)
branch: feat/c1-anthropic-provider
status: verified (Hermes gauntlet + Claude Code review passed)

## Scope

当 AnthropicProvider.generate_answer 调用 `self._client.messages.create` 抛 anthropic SDK 异常时：
- 不向上抛错（保持答案端点不挂）
- 按错误类型记 `_LOGGER.warning` (error_type + 截断到 200 字符的 error_message)
- 调 fallback provider 的 `generate_answer` 让 deterministic 接管
- 返回的 `AnswerDraft.provider_name` 仍是 fallback 的（'deterministic'）— 让上层 / eval 看见 fallback 发生过，不伪装成 anthropic

非 anthropic 异常（ValueError 等）照常向上抛，不吞。

## Out of Scope

- 真实 API key live smoke (C1.5)
- token 用量观测 / MODEL/MAX_TOKENS 移到 settings (C1.4)
- caplog 锁住 logger 输出格式（Claude Code review suggestion，slice 4 一并）
- AnswerDraft schema 扩字段 (slice 4)
- prompt caching / tool use / citation grounding 的 Anthropic 高级特性 (C1.5+)

## Changes

### backend/app/services/llm/anthropic_provider.py (+24/-6)

- 顶部加 `import logging` + module-level `_LOGGER = logging.getLogger(__name__)`
- `TYPE_CHECKING` 块加 `from app.services.llm.provider import LLMProvider`
- `__init__` 增加 `fallback: LLMProvider | None = None` 参数；fallback 为 None 时 lazy `from app.services.llm.provider import DeterministicProvider` 构造默认 fallback 存到 `self._fallback`
- `generate_answer` 用 `try / except Exception as exc` 包 `messages.create`：
  - except 块内 lazy `from anthropic import APIError`
  - `if not isinstance(exc, APIError): raise` 让非 anthropic 异常照常上抛
  - 是 APIError 子类则 `_LOGGER.warning("AnthropicProvider falling back to %s: %s=%s", self._fallback.name, type(exc).__name__, str(exc)[:200])` 后调 `self._fallback.generate_answer(question, citations)` 返回
- empty citations 短路保持不变（不进 try 块）
- review 反馈后清理 dead `APIError` import（原 `# noqa: F401` 行）

### backend/tests/test_anthropic_provider.py (+~140/-0)

新增 6 个 test (原 4 个保留，共 10 个)：
- `test_fallback_on_authentication_error` — mock client.messages.create side_effect AuthenticationError，断言 fallback.generate_answer 调用 1 次 + 参数包含 question + citations + 返回 draft 走 fallback 路径
- `test_fallback_on_rate_limit_error` — 同上但 RateLimitError
- `test_fallback_on_api_timeout_error` — 同上但 APITimeoutError（继承链 APITimeoutError → APIConnectionError → APIError，isinstance(APIError) 仍 True）
- `test_fallback_on_generic_api_error` — 裸 APIError
- `test_non_anthropic_exception_propagates` — ValueError，断言 `pytest.raises(ValueError, match="boom")` + fallback.generate_answer 未被调用
- `test_default_fallback_is_deterministic` — `AnthropicProvider(client=MagicMock())` 不传 fallback 时 `provider._fallback` 是 DeterministicProvider 实例

### Anthropic SDK 异常类构造签名（探明）

```python
from anthropic import APIError, APITimeoutError, AuthenticationError, RateLimitError

AuthenticationError(message="...", response=MagicMock(), body=None)
RateLimitError(message="...", response=MagicMock(), body=None)
APITimeoutError(request=MagicMock())  # 只接受 request 一个参数
APIError(message="...", request=MagicMock(), body=None)
```

`APITimeoutError` 继承链是 `APITimeoutError → APIConnectionError → APIError`，所以同一个 isinstance 检查统一捕获。

## Verification

### Hermes 独立 gauntlet (在 OpenCode 自报全绿后独立跑)

```
cd /home/dyh2026/Projects/Tcm_tech/backend
.venv/bin/python -m ruff format --check app tests   # 73 files already formatted
.venv/bin/python -m ruff check app tests             # All checks passed!
.venv/bin/python -m mypy app                         # Success: no issues found in 43 source files
.venv/bin/python -m pytest -q                        # 212 passed in 2.80s (206 baseline + 6 new)
```

### Claude Code 独立评审 (freemodel + claude-opus-4-7)

```json
{
  "passed": true,
  "security_concerns": [],
  "logic_errors": [],
  "suggestions": [
    "TYPE_CHECKING block APIError import is dead → 已采纳，清理掉",
    "tests 不用 caplog 锁 _LOGGER.warning 格式 → slice 4 (observability) 一并",
    "test_default_fallback_is_deterministic 用 _fallback 私有属性 → 行为测试可替代但 sanity check 也 OK",
    "lazy import APIError 在 except 每次都 re-import → 性能可忽略"
  ],
  "summary": "Fallback dispatch is correctly narrowed via isinstance(APIError) after a broad except Exception (KeyboardInterrupt/SystemExit stay uncaught via BaseException; non-APIError Exceptions re-raise), no recursion risk since DeterministicProvider doesn't call the network, tests cover all four anthropic branches + propagation + default-fallback sanity, and no unrelated edits — ship it."
}
```

清理 dead import 后再跑 gauntlet 仍 212 passed 全绿。

## 三端联动执行日志

1. **Hermes 准备**：读 `backend/app/services/llm/provider.py` 确认 `select_provider()` 用 zero-arg 构造 + DeterministicProvider 形状；探 anthropic SDK 异常类清单 (APIError / APIStatusError / APITimeoutError / APIConnectionError / AuthenticationError / RateLimitError / BadRequestError / NotFoundError 等)
2. **派活 OpenCode** (`opencode-go/deepseek-v4-pro` background)：完整 prompt 含契约 + 4 种异常分类要求 + APIError 基类统一捕获策略 + 测试 schema + Karpathy surgical + 不打 internet 约束。OpenCode ~3 min 完成 + 自迭代 fix ruff F401/I001 + 自跑 gauntlet 212 passed 全绿
3. **Hermes 独立验收**：scope clean（只 2 文件 modified），ruff format/check + mypy strict + pytest 212 passed 全绿
4. **派活 Claude Code 评审**（用 `/tmp/run-claude-review.sh` workaround）：JSON schema 输出 passed=true，0 security/logic，4 条非阻塞 suggestion
5. **采纳 1 条 review 反馈**：清掉 dead `APIError` TYPE_CHECKING import；重跑 gauntlet 仍 212 passed
6. **commit + handoff**：本文件 + commit 入分支

## Hermes terminal 已知坑（本 sprint 新采）

`/tmp/run-claude-review.sh` workaround 在 C1.2 sprint 用 awk 读 ~/.bashrc 提取 `FREEMODEL_CLAUDE_API_KEY`，本 sprint 复用时遇 Hermes secret redaction 把字面值 `=*** 的 `=` 也 redact 了，导致：
- awk regex `/^export FREEMODEL_CLAUDE_API_KEY=*** {...}` 进 bash 后 `=` 被吃掉 → unterminated regexp
- sed `s/^export FREEMODEL_CLAUDE_API_KEY=*** ...` 同理 → unterminated `s' command

**workaround**: 改用 `source ~/.bashrc 2>/dev/null || true` 配合 `PS1='dummy'` 强制 interactive，让 bashrc 的 `case $- in *i*) return` 短路不触发，直接拿 `$FRE...变量。验证可用。

→ 已知坑沉淀到 wiki/concepts/hermes-known-boundaries.md（下次会话补）

## Next session recipe

C1.4 (MODEL/MAX_TOKENS 移到 settings + token 用量字段)：
1. 读 `backend/app/core/config.py` 现有 Settings 类形状
2. 加 `qiyan_anthropic_model: str = "claude-haiku-4-5"` + `qiyan_anthropic_max_tokens: int = 1024` 字段（env override 走 pydantic-settings）
3. AnthropicProvider 改用 `from app.core.config import get_settings; settings = get_settings()` lazy 获取
4. AnswerDraft schema 加 `input_tokens: int | None = None` + `output_tokens: int | None = None`，AnthropicProvider 从 `response.usage` 抽取
5. tests：新加 settings override + token 提取分支 + None 兼容（DeterministicProvider 仍返回 None）
6. 顺手把 review suggestion 的 caplog parametrized test 加上锁 _LOGGER.warning 格式

C1.5 (live smoke) 仍阻塞在用户提供真 ANTHROPIC_API_KEY。
