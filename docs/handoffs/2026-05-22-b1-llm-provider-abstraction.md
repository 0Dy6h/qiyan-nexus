# B1 — LLM provider 接口抽象（2026-05-22）

> 阶段 B 第一颗 slice：在不接真实模型的前提下，把 RAG 答案文本生成抽象到 provider 接口，铺好 C1 真实 Claude 接入位。

## 落地点

- 新增 `backend/app/services/llm/__init__.py`（marker）
- 新增 `backend/app/services/llm/provider.py`：`AnswerDraft` Pydantic 模型、`LLMProvider` Protocol、`DeterministicProvider`、`MockClaudeProvider`、`select_provider()` env 选择器
- 改造 `backend/app/services/rag.py`：移除内联 `_EVIDENCE_TAG_TOPIC_CN` 与 `_collect_topic_phrases`（迁入 `provider.py`），`answer_question` 改走 `select_provider().generate_answer(...)`；保留 `build_answer()` 作向后兼容薄壳（仍委托给 `DeterministicProvider`）
- 新增 `backend/tests/test_llm_provider.py`（11 用例）
- 扩展 `backend/tests/test_rag_service.py`（2 用例：env 切到 `mock_claude` / 默认仍是 deterministic）

## 行为契约

| 维度 | 行为 |
|---|---|
| 默认 provider | `DeterministicProvider`，文本含 `deterministic retrieval` 标记字符串，与既有断言 byte-identical |
| `QIYAN_LLM_PROVIDER=mock_claude` | 切换为 `MockClaudeProvider`，文本以 `【模拟 Claude 草稿】` 起头并引用问题原文 + 文献题名 |
| 大小写 | env 大小写不敏感（`Mock_Claude` 同样命中） |
| 空值 / 未知值 | 回落到 deterministic 并 `logging.warning`，**不抛错** |
| 显式 name 参数 | `select_provider("deterministic")` 覆盖 env |
| `AnswerDraft` | `text: str` + `provider_name: str`，方便后续日志/eval 追溯 |
| disclaimer | 仍由 `rag.py` 层注入，不放在 provider 内部 |

## 不在范围

- 不接真实 Anthropic/OpenAI API（C1 才做）
- 不实现 prompt caching / tool use（claude-api skill 在 C1 触发）
- 不在 `MockClaudeProvider` 引入随机性（保持确定性以便测试）
- 不引入 `Settings` 字段（暂用 `os.getenv` 即时读取，方便 `monkeypatch.setenv` 测试）

## 验证

```bash
cd backend
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest -q
# 134 passed
```

前端无改动：`pnpm test` 81 passed、`tsc --noEmit` 静默成功。

## 下一颗候选

- **B2**：RAG eval 扩展到 50 题（roadmap 估 2d），eval 时可对 `provider_name` 做基线对比。
- **B6**：数据来源切换面板（roadmap 估 0.5d），UI 侧落地小切片。
- 若想先做 UI 透传 provider 信息：可在 `/rag` 页面回显 `provider_name`（roadmap 未列，但收益清晰）。

按"先收紧 MVP-A 出口、再推 MVP-B"的优先级，推荐 **B2**。
