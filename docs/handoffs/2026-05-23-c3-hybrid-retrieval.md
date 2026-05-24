# C3 — Embedding + Faiss 混合检索（2026-05-23）

> 阶段 C 第一颗 slice（4d 估）：把 RAG 检索从「keyword + alias 表」单线扩展到可切换的 `keyword | vector | hybrid` 三轴；hybrid 走 RRF(k=60) 融合，default 仍是 keyword、所有既有测试与字节级断言零回归。一并铺好 C1（真实 Anthropic Claude）与 C2（citation grounding tool use）的接口位。

## 落地点

### Slice 1 — `RetrievalProvider` Protocol + `KeywordRetrievalProvider`
- 新增 `backend/app/services/retrieval/__init__.py`、`backend/app/services/retrieval/provider.py`：
  - `ScoredCandidate` dataclass、`RetrievalProvider` Protocol、`KeywordRetrievalProvider`
  - `select_retrieval_provider()` env 选择器（`QIYAN_RETRIEVAL_PROVIDER`，default `keyword`，未知值 warn 回退）
  - `_resolve_provider_class(candidate)` 做 vector/hybrid 的 lazy import，避免 keyword 路径触发 faiss/st 加载
- 改造 `backend/app/services/rag.py`：`answer_question` 调用 `select_retrieval_provider().rank(...)`；`tokenize_query` / `score_item` / `_alias_tag_bonus` / `_CONFIDENCE_BY_SOURCE_TYPE` 留作 KeywordProvider 内部依赖
- 新增 `backend/tests/test_retrieval_provider.py`（镜像 `test_llm_provider.py` 的 5 用例）

### Slice 2 — `EmbeddingBackend` Protocol + Hashing/BGE 双实现
- 新增 `backend/app/services/retrieval/embedding.py`：
  - `EmbeddingBackend` Protocol（属性 `name` / `dim`，方法 `embed_texts`）
  - `HashingEmbeddingBackend`（dim=128，md5 → ±1 → L2 归一化，零下载 / deterministic）
  - `SentenceTransformerEmbeddingBackend`（dim=512，`BAAI/bge-small-zh-v1.5`，lazy import + lazy load）
  - `select_embedding_backend()`（env `QIYAN_EMBEDDING_BACKEND`，default `hashing`，未知值 fallback）
  - 公开 `EmbeddingMatrix = npt.NDArray[np.float32]`，`Any` 不外泄
- 新增 `backend/tests/test_embedding_backend.py`（8 用例：单位向量、deterministic、不同输入不同向量、Protocol 满足、env default / unknown fallback / 显式覆盖、bge 实例化不触发模型加载）
- `backend/pyproject.toml` runtime 加 `numpy>=1.26,<3`，dev extra 加 `sentence-transformers>=3.0.0`

### Slice 3 — `ChunkVectorIndex` (faiss) + `VectorRetrievalProvider`
- 新增 `backend/app/services/retrieval/vector_index.py`：
  - `ChunkVectorIndex(backend, cache_path)`，方法 `build` / `search` / `compute_fingerprint` / `load_or_build` / `_save_to_cache` / `_load_from_cache`
  - faiss `IndexFlatIP`；持久化为 `vector_index_state.npy` + `.meta.json`（含 `backend_name`/`dim`/`chunk_ids`/`fingerprint`）
  - `_INDEX_SINGLETONS: dict[str, ChunkVectorIndex]` 按 `backend.name` 做 module-level 单例缓存
  - `get_chunk_vector_index(...)`、`reset_chunk_vector_index_cache()`
- 新增 `backend/app/services/retrieval/vector_provider.py`：`VectorRetrievalProvider(backend, cache_path, index)`，name=`"vector"`；flatten chunks → load_or_build → search → 映射回 `ScoredCandidate(score=pool_size-rank)`；chunkless item 给 zero-score fallback
- 改造 `backend/app/repositories/runtime_storage.py`：加 `resolve_vector_index_cache_path()`（env `VECTOR_INDEX_RUNTIME_CACHE_PATH`，default `backend/data/runtime/vector_index_state.npy`，mkdir parent 但不做 seed bootstrap——派生 artifact 首次 build 才写）
- 新增 `backend/tests/test_vector_index.py`（4 用例）、`backend/tests/test_vector_retrieval_provider.py`（4 用例）；test 内用 `SubstringEmbeddingBackend`（dim=8，把 query 子串位置编码进向量）做语义召回断言，绕开 hashing 碰撞
- `backend/pyproject.toml` runtime 加 `faiss-cpu>=1.8.0`

### Slice 4 — `HybridRetrievalProvider` (RRF) + `RetrievalMetadata.strategy`
- 新增 `backend/app/services/retrieval/hybrid_provider.py`：
  - 常量 `RRF_K = 60`、`SUB_PROVIDER_TOP_K = 50`（Cormack 原始 k=60）
  - `_FusionEntry(rrf, language_bonus, candidate)` 内部 dataclass
  - `HybridRetrievalProvider(keyword_provider, vector_provider)` 默认装载 `KeywordRetrievalProvider()` + `VectorRetrievalProvider()`
  - `rank()`：双侧先 filter `score > 0`（空则回退原列表）→ `composite_key = (item.id, chunk.chunk_id or "_")` → 累加 `1/(RRF_K + rank + 1)` → 排序后给 integer score = `pool_size - final_rank`，保 downstream parity（`score > 0` 阈值不变）
- 改造 `backend/app/schemas/rag.py`：`RetrievalMetadata.strategy: str = "keyword"`（additive，wire 兼容）
- 改造 `backend/app/services/rag.py`：填 `strategy=retrieval_provider.name`
- 新增 `backend/tests/test_hybrid_retrieval_provider.py`（4 用例，`_StubProvider` 锚定 RRF 算式：Protocol、3 候选 RRF 数学、vector 空时回退 keyword、双侧独有候选都进 top_k）
- 同步既有 `backend/tests/test_rag_service.py`、`test_rag_api.py` 的 JSON 断言

### Slice 5 — Eval ablation API + CLI 对比表 + ADR-0014
- 改造 `backend/app/services/eval.py`：`run_rag_ad_eval_report(strategy: str | None = None)`；内部 `_override_retrieval_strategy(strategy)` contextmanager 临时设/恢复 `os.environ[RETRIEVAL_PROVIDER_ENV_VAR]`；`applied_strategy` 从 response.retrieval.strategy 取
- 改造 `backend/app/schemas/eval.py`：`RagEvalSummary.retrieval_strategy: str = "keyword"`
- 改造 `backend/app/api/eval.py`：`?strategy=` Query 参数，`pattern="^(keyword|vector|hybrid)$"`（未知 → 422）
- 新增 `backend/scripts/compare_retrieval_strategies.py`：纯 stdlib + `fastapi.testclient`；CLI 打印 markdown 对比表
- 新增 `docs/adr/0014-retrieval-provider-and-hybrid-search.md`：10 条决策记录
- 扩展 `backend/tests/test_eval_service.py`（3 用例）、`backend/tests/test_eval_api.py`（2 用例 + 既有 broken_report fixture 兼容 `**_kwargs`）

## 行为契约

| 维度 | 行为 |
|---|---|
| 默认 retrieval | `keyword` —— 所有既有 ≥168 测试零修改通过、`response.retrieval.strategy == "keyword"` |
| `QIYAN_RETRIEVAL_PROVIDER=vector` | 走 faiss flat IP；keyword 路径完全不触达，answer 体含 disclaimer byte-identical |
| `QIYAN_RETRIEVAL_PROVIDER=hybrid` | RRF(k=60) 融合 keyword + vector top-50；候选取并集，单侧独有候选保留 |
| 大小写 / 未知值 | env 大小写不敏感；未知值 `logging.warning` 后回退 keyword，**不抛错** |
| `QIYAN_EMBEDDING_BACKEND` | default `hashing`（CI / 测试）；`bge` 显式 opt-in（lazy 加载 `BAAI/bge-small-zh-v1.5`）；未知值 fallback hashing |
| Index 生命周期 | 模块级 singleton 按 `backend.name` 缓存；每次 `load_or_build` 用 `sha256((chunk_id, text[:64], backend.name, backend.dim))` 重算 fingerprint 比对，不匹配重建——绕开 `[[runtime-state-bootstrap-stale-on-seed-change]]` 坑 |
| `/api/evals/rag-ad/report?strategy=` | 接受 `keyword \| vector \| hybrid`；其他值 422；返回 summary 内 `retrieval_strategy` 字段 |
| `RetrievalMetadata.strategy` | additive 字段，default `"keyword"`，wire 兼容老客户端 |
| disclaimer 与 `deterministic retrieval` 字符串 | 全程不变；不论 retrieval 路径如何切换，answer 体均含 byte-identical 标记 |

## 不在范围

- 不接真实 Anthropic API（C1 才做；C3 给 C1 的 prompt 准备更准的 chunk）
- 不接 tool use / citation grounding（C2 才做；hybrid 路径作为 C2 fast-path 保留）
- 不在 `/api/rag/answer` body 加 per-request `strategy` 参数 + 前端 `/rag` 页切换器（后续 UI slice）
- 不做 `InMemoryChunkRepository.upsert_uploaded_pdf_chunk` 的增量 re-embed hook（当前首次 hybrid 查询整 index rebuild，PDF 上传场景下可接受；chunk 量过千再优化）
- 不引入 pgvector / Redis / Celery / MinIO（与 ADR-0005/0007/0008 边界一致）

## 验证

```bash
# Backend gauntlet（标准 4 步，绿色出口）
cd /home/dyh2026/Projects/Tcm_tech/backend
.venv/bin/python -m ruff format --check app tests \
  && .venv/bin/python -m ruff check app tests \
  && .venv/bin/python -m mypy app \
  && .venv/bin/python -m pytest -q \
  && echo "BACKEND GAUNTLET GREEN"
# 199 passed
```

```bash
# Strategy ablation（hashing backend，离线）
cd /home/dyh2026/Projects/Tcm_tech/backend && .venv/bin/python scripts/compare_retrieval_strategies.py
# | strategy | pass_rate | citation_hit | chunk_hit |
# | keyword  | 1.000     | 50/50        | 50/50     |
# | hybrid   | 0.900     | 47/50        | 45/50     |
```

```bash
# Strategy ablation（bge backend，需先 pip install -e .[dev] 与首次下载 ~95MB）
cd /home/dyh2026/Projects/Tcm_tech/backend
QIYAN_EMBEDDING_BACKEND=bge .venv/bin/python scripts/compare_retrieval_strategies.py
# 期望 hybrid 追平或略超 keyword
```

```bash
# Live API（端到端 sanity）
cd backend && .venv/bin/fastapi dev app/main.py &
# 1) keyword default
curl -s 'http://localhost:8000/api/rag/answer' -H 'content-type: application/json' \
  -d '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？"}' | jq '.retrieval.strategy'
# "keyword"

# 2) hybrid via env
QIYAN_RETRIEVAL_PROVIDER=hybrid curl -s 'http://localhost:8000/api/rag/answer' \
  -H 'content-type: application/json' \
  -d '{"question":"消风散治疗 AD 的网络药理学机制"}' | jq '.retrieval.strategy'
# "hybrid"

# 3) eval report
curl -s 'http://localhost:8000/api/evals/rag-ad/report?strategy=hybrid' \
  | jq '.summary | {retrieval_strategy, pass_rate}'
```

前端无改动：`pnpm test` / `pnpm typecheck` 不受影响（schema 是 additive）。

## 依赖变化

| 库 | 位置 | 用途 |
|---|---|---|
| `numpy>=1.26,<3` | runtime | embedding 向量、faiss buffer、fingerprint 计算 |
| `faiss-cpu>=1.8.0` | runtime | `IndexFlatIP` 检索；ABI3 wheel 覆盖 cp310–cp313 |
| `sentence-transformers>=3.0.0` | dev extra | `BAAI/bge-small-zh-v1.5` 加载；CI 不装、显式 `pip install -e .[dev]` 才解锁 |

mypy strict 隔离面只在两处：
- `backend/app/services/retrieval/vector_index.py` 顶部 `import faiss  # type: ignore[import-untyped, import-not-found, unused-ignore]`
- `backend/app/services/retrieval/embedding.py::_load_sentence_transformer` 内部局部 import，同 ignore 三元组

public surface 均返回 `numpy.typing.NDArray[np.float32]` 或 typed dataclass，`Any` 不外泄全仓。

## bge 模型本地化注记

- 首次调用 `SentenceTransformerEmbeddingBackend.embed_texts(...)`（或 `huggingface-cli download BAAI/bge-small-zh-v1.5`）会下载 ~95MB 到 `~/.cache/huggingface/`
- GFW 下不稳：`HF_ENDPOINT=https://hf-mirror.com` 或预先在境外网络下载后 rsync 到 `~/.cache/huggingface/hub/`
- 模型一旦缓存，离线机器同样可用；CI 永远走 `hashing` backend、绝不下载

## 下一颗候选

- **C1（真实 Anthropic Claude API）**：直接添加 `AnthropicProvider` 实现 `LLMProvider`，触发 `claude-api` skill；C3 的 hybrid 让 C1 第一轮 prompt 更准、token 成本下降
- **C2（citation grounding tool use）**：把 `VectorRetrievalProvider.rank` 暴露为 Claude tool；hybrid 作为非 tool-use 时的 fast-path 保留
- **UI 透传**：`/api/rag/answer` body 加 `strategy` + 前端 `/rag` 页切换器（roadmap 未列、收益清晰）

按"先把真实模型接进来再加 citation tool"的优先级，推荐 **C1**。
