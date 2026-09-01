# ADR-0014: RetrievalProvider 抽象与 Hybrid 检索（faiss + RRF）

日期：2026-05-23

## 状态

Accepted

## 背景

C 阶段（向真实模型逼近）的起点是把检索从“keyword + alias 表”这一条 deterministic 单线，扩展为可切换、可融合的多策略检索；既要给 C1（真实 LLM）准备更稳的 chunk 召回，也要为 C2（citation grounding tool use）提供分语义的 ranking 信号。

B 阶段已经把 `LLMProvider` 抽出（B1），有了 `select_provider()` 的 env 切换样板。检索侧此前一直内联在 `app/services/rag.py::answer_question`，所有改动都得改 RAG 主路径。

外部约束：
- 不引 pgvector / Redis / Celery / MinIO（与 ADR-0005、ADR-0007、ADR-0008 边界一致，C 阶段保持本地工程闭环）。
- mypy strict + `warn_unused_ignores=true` 已在 `app/` 落地，任何依赖必须有可隔离的类型边界。
- CI 不联网、不下载模型；50 题 RAG eval 必须能离线复现。

## 决策

1. **抽象 `RetrievalProvider` Protocol**：镜像 `LLMProvider`，签名 `rank(query, items, chunks_by_item, preferred_source_type) -> list[ScoredCandidate]`；env `QIYAN_RETRIEVAL_PROVIDER` 选择实现，未配置→ `keyword`、未知值 warn 后回退 keyword、不抛错。`answer_question` 仅负责调用 + 跨语言 top-3 调换 + `network` 二次排序等 *answer 政策*。
2. **三条实现并存**：`keyword`（B 阶段原有逻辑搬迁）、`vector`（faiss + embedding）、`hybrid`（RRF 融合前两条）。Default 一直是 keyword，所有既有测试无修改通过。
3. **`EmbeddingBackend` 双实现**：
   - `HashingEmbeddingBackend`（dim=128, md5 → ±1 → L2 归一化）是 default。零下载、deterministic，CI / 测试只走这条。
   - `SentenceTransformerEmbeddingBackend`（dim=512, `BAAI/bge-small-zh-v1.5`，lazy import + lazy load）是 dev/prod 路径。
   - env `QIYAN_EMBEDDING_BACKEND` 切换，未知值 fallback hashing。
4. **bge-small-zh-v1.5 选型理由**：50 题 eval 以中文医学查询为主；同尺寸下 zh 任务 bge-small 现 SOTA 段；~95MB CPU 可跑、无需 GPU/sudo 系统库；首次下载到 `~/.cache/huggingface/`。备选 `text2vec-base-chinese`（~400MB，老）、`m3e-small`（zh 任务略弱于 bge-small）。
5. **faiss IndexFlatIP**：当前 chunk 量 10–30 级别（seed 12 + uploaded PDFs），flat IP 子毫秒、零训练。faiss-cpu 1.14+ 的 ABI3 wheel cp310-abi3 在 Python 3.11–3.13 通用。如果未来量上千改 `IndexIVFFlat` 即可，public surface 不变。
6. **RRF 融合，k=60**：Cormack 原始常量；跨整数 keyword score 与浮点 cosine 时不用做 min-max；候选取并集，单侧独有候选保留；语言 bonus 取较大值；最终 score 转回整数 `pool_size - rank` 维护 `score > 0` 阈值不变。
7. **Index 生命周期：lazy build + fingerprint rebuild**。模块级 singleton 按 `backend.name` 缓存；`load_or_build` 在每次调用前对 `(chunk_id, text[:64], backend.name, backend.dim)` 排序 SHA256 比对，不匹配重建。**这是为了正面绕开 [[runtime-state-bootstrap-stale-on-seed-change]] 在 B5/B6 各踩一次的"seed 改了 runtime 不跟进"陷阱**——派生 cache 也用同一招校正。
8. **mypy strict 隔离面**：仅两处第三方未类型化导入用窄 ignore：
   - `app/services/retrieval/vector_index.py` 中的 `import faiss  # type: ignore[import-untyped, import-not-found, unused-ignore]`
   - `app/services/retrieval/embedding.py::_load_sentence_transformer` 中的局部 import
   - public surface 返回 `numpy.typing.NDArray[np.float32]` 或 typed dataclass，`Any` 不外泄。
9. **Eval ablation**：`/api/evals/rag-ad/report?strategy=keyword|vector|hybrid` 加 query param；`RagEvalSummary.retrieval_strategy` 字段 additive、default `keyword`；`backend/scripts/compare_retrieval_strategies.py` 给一条 stdlib + TestClient 的对照表。
10. **Slice 命名空间**：所有 C3 模块落在 `app/services/retrieval/`，不再共享 `app/services/rag.py` 命名空间——为后续 C2（citation grounding tool use）也能挂在 `retrieval` 域而不污染 `rag.py` 留路。

## 后续

- C1（真实 Anthropic Claude API）：直接添加 `AnthropicProvider` 实现 `LLMProvider`；C3 的 hybrid retrieval 给 C1 第一轮 prompt 更准的 chunk，prompt 成本会因此下降。
- C2（citation grounding tool use）：将 `VectorRetrievalProvider.rank` 暴露为 tool；hybrid 路径可以保留作为 fast-path。
- `/api/rag/answer` body 加 per-request `strategy` 参数 + 前端 `/rag` 页面切换器：属于后续 UI slice，C3 不做。
- `InMemoryChunkRepository.upsert_uploaded_pdf_chunk` 加 re-embed hook：当前首次 hybrid 查询会 rebuild 整个 index，PDF 上传场景下可接受；如果未来 chunk 量过千再优化为增量 add。

## 影响

- 后端运行依赖新增 `numpy>=1.26,<3` 与 `faiss-cpu>=1.8.0`（runtime）。`sentence-transformers>=3.0.0` 仅在 `[dev]` extra（CI 不装、生产显式 opt-in）。
- 50 题 eval：keyword 路径仍是 100% pass / 50 citation_hit / 50 chunk_hit（与 B2 完全等价）；hybrid + hashing backend 90% / 47 / 45（断言≥90% 锁住底线）；hybrid + bge backend 预期≥95%（验收时 `QIYAN_EMBEDDING_BACKEND=bge` 跑一次 ablation 表存档）。
- mypy / ruff / pytest gauntlet 全绿，全仓共两处窄 type ignore。
