# Multilingual Embedding Spike + B6 Handoff — 2026-06-10

## Goal

执行阶段 B 起手计划：先把多语 embedding spike 的代码底座落地并验证默认路径不变；随后复核 B6 数据来源切换面板是否仍是待办。

## Current State

- `QIYAN_EMBEDDING_BACKEND` 仍默认 `hashing`，不触发任何模型下载。
- 新增 opt-in backend：`bge-m3`（`BAAI/bge-m3`）与 `multilingual-e5-large`（`intfloat/multilingual-e5-large`），并支持别名 `multilingual-e5` / `e5-large`。
- 所有 sentence-transformers backend 仍懒加载，仅首次真实 `encode` 才加载模型。
- `multilingual-e5-large` 已按 document/query role 分别加 `passage: ` / `query: ` 前缀。
- Vector index 建索引走 document role，搜索走 query role；grounding 中 claim 走 query role，evidence text 走 document role。
- B6 数据来源切换面板经复核已在 `fcf9ac4` 落地，不再是待办；`docs/plans/2026-06-04-mvp-a-closeout.md` 与 `docs/current-state.md` 已修正。
- 默认 RAG / retrieval 路径保持离线 deterministic + keyword，不翻转 L2。

## Completed In This Session

- 重构 `backend/app/services/retrieval/embedding.py`：
  - 增加 role-aware encode 支持。
  - 增加 `encode_with_role()` 兼容旧测试 fake backend。
  - 增加 `BgeM3EmbeddingBackend` 与 `MultilingualE5LargeEmbeddingBackend`。
- 更新 `backend/app/services/retrieval/vector_index.py`：
  - chunk vectors 使用 document role。
  - query vector 使用 query role。
- 更新 `backend/app/services/grounding.py`：
  - claim/evidence 分别按 query/document role 编码。
- 补测试：
  - `backend/tests/test_embedding_backend.py`
  - `backend/tests/test_vector_index.py`
  - `backend/tests/test_grounding_semantic.py`
- 更新文档：
  - `README.md`
  - `docs/current-state.md`
  - `docs/plans/2026-06-04-mvp-a-closeout.md`

## Still Open / Blocked

- 未跑真实 `bge-m3` / `multilingual-e5-large` cross-lingual eval。本机未发现对应 Hugging Face cache，本 session 未主动下载大模型，避免把默认验证变成长下载任务。
- 下一步真实模型评估应在明确允许模型下载或预先缓存后进行。
- 本地 `backend/data/runtime/` 有上传 PDF 与 runtime 状态，直接跑 eval 会受本地状态影响；可比对基线时必须显式指向 seed JSON。
- L2/default preview 仍不翻转；本次只补 embedding 底座，不改变真实 LLM 默认启用策略。

## Key Files And Artifacts

- `backend/app/services/retrieval/embedding.py`
- `backend/app/services/retrieval/vector_index.py`
- `backend/app/services/grounding.py`
- `backend/tests/test_embedding_backend.py`
- `backend/tests/test_vector_index.py`
- `backend/tests/test_grounding_semantic.py`
- `frontend/tests/literature-data-source-switcher.test.ts`
- `README.md`
- `docs/current-state.md`
- `docs/plans/2026-06-04-mvp-a-closeout.md`
- `docs/evaluations/2026-06-02-expected-label-audit.md`
- Model cards for later real eval:
  - `https://huggingface.co/BAAI/bge-m3`
  - `https://huggingface.co/intfloat/multilingual-e5-large`

## Verification

- Focused backend tests:
  - `pytest tests\test_embedding_backend.py tests\test_vector_index.py tests\test_grounding_semantic.py tests\test_retrieval_provider.py tests\test_vector_retrieval_provider.py tests\test_hybrid_retrieval_provider.py tests\test_cross_lingual_eval.py -q`
  - Result: `75 passed`
- Backend gate:
  - `ruff format --check app tests`
  - `ruff check app tests`
  - `mypy app`
  - `pytest -q`
  - Result: `470 passed, 1 skipped`
- Seed-state retrieval smoke with `QIYAN_EMBEDDING_BACKEND=hashing`:
  - keyword: `n=16`, mono `1.0`, cross `0.9688`, diversity `0.3753`, P@10 `0.225`, MRR `0.9167`
  - vector: `n=16`, mono `0.7812`, cross `0.3750`, diversity `0.4159`, P@10 `0.1313`, MRR `0.5152`
  - hybrid: `n=16`, mono `1.0`, cross `0.8438`, diversity `0.3452`, P@10 `0.2063`, MRR `0.7937`
- Frontend verification:
  - `pnpm test` — `154 passed`
  - `pnpm typecheck` — passed
  - `pnpm build` — passed

## Recommended Next Step

Run the real multilingual embedding eval as a separate explicit slice, starting with `bge-m3` before `multilingual-e5-large` because BGE-M3 does not require query/passage prefixes and is the lower-integration-risk candidate. Use seed-state env overrides so results compare against the locked `0.9688` keyword baseline rather than local runtime uploads.

## Recommended Reading Order

1. `docs/current-state.md`
2. `docs/handoffs/2026-06-10-multilingual-embedding-spike-b6.md`
3. `backend/app/services/retrieval/embedding.py`
4. `backend/app/services/retrieval/vector_index.py`
5. `docs/evaluations/2026-06-02-expected-label-audit.md`

## Recommended Skill / Toolset

- `test-driven-development` for the next real-model eval slice.
- `systematic-debugging` if model download, cache, or vector-index rebuild behaves oddly.
- `frontend-design` only if B6 UI is reopened; it is currently verified as already landed.
