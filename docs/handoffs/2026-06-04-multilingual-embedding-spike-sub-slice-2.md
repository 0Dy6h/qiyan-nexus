# Session Handoff — 2026-06-04（多语 embedding spike sub-slice ②，backend 接入）

branch: `feat/multilingual-bge-m3-backend`（已提交 2 个 commit：sub-slice ① 文档 + sub-slice ② 后端）
default RAG path: offline `deterministic`，未变
default embedding backend: `hashing`，未变
stopped at: 后端 `MultilingualBgeM3EmbeddingBackend` 已注册、TDD 测试 GREEN、四件套全绿；下一步 sub-slice ③ 需本地预下载 `BAAI/bge-m3` 权重再跑 `run_cross_lingual_retrieval_eval()`

## Goal

闭合 `docs/plans/2026-06-04-mvp-a-closeout.md` §阶段 B 入口准备 推荐的「多语 embedding spike」sub-slice ②：在 `EmbeddingBackend` 注册表追加 BGE-M3 backend，env `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` 显式 opt-in，default 仍 `hashing`，CI 永远不下载权重。为 sub-slice ③（eval 复跑突破 0.97 cross-lingual recall ceiling）准备最小可跑底座。

## Current state

- branch `feat/multilingual-bge-m3-backend` HEAD = sub-slice ② commit；与 main 差 2 个 commit（①、②）
- `backend/app/services/retrieval/embedding.py`：新增 `MultilingualBgeM3EmbeddingBackend` 类（`name="multilingual_bge_m3"`, `dim=1024`, `model_name="BAAI/bge-m3"`），lazy 加载形态与现有 `SentenceTransformerEmbeddingBackend` 完全镜像；注册进 `_BACKENDS`
- `backend/tests/test_embedding_backend.py`：+3 测试（lazy construction、env-driven selection、Protocol satisfaction）
- 完整后端 gauntlet：ruff format 104/104、ruff check 全绿、mypy strict 54 文件 0 issue、pytest **467 passed, 1 skipped**（前 baseline 447 passed，期间其它工作 +17，本 sub-slice +3）
- 默认运行路径不变：未配置 `QIYAN_EMBEDDING_BACKEND` 或配置为非法值时仍走 `HashingEmbeddingBackend`，CI / 本地 default 测试零模型下载

## Completed in this session

### Sub-slice ①（commit `af3f86f`）
- 新增 `docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md`：BGE-M3 / multilingual-e5-large / LaBSE 三候选静态对比 + 推荐 BGE-M3 主选 + e5-multi-large 备选 + 与 ADR-0005 / ADR-0014 / ADR-0012 关系说明
- `docs/current-state.md` 跨语行末尾追加 sub-slice ① closure 一句
- 0 代码改动

### Sub-slice ②（本次 commit）
- `app/services/retrieval/embedding.py`：追加 `MultilingualBgeM3EmbeddingBackend` 类 + 注册表登记
- `tests/test_embedding_backend.py`：追加 3 测试
  - `test_multilingual_bge_m3_backend_does_not_load_model_on_construction`（lazy 不下载契约）
  - `test_select_embedding_backend_resolves_multilingual_bge_m3`（env 解析）
  - `test_multilingual_bge_m3_backend_satisfies_protocol`（Protocol 满足）
- `docs/current-state.md` 跨语行末尾追加 sub-slice ② closure 一句
- 本 handoff

## Still open / blocked

### Sub-slice ③（未启动，依赖本地权重 + 用户授权一次性下载）

- 需要 `BAAI/bge-m3` 权重首次下载到 `~/.cache/huggingface/`（~1.4GB，2-5 分钟 / 视网络）
- 需要环境变量：`QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` + `QIYAN_RETRIEVAL_PROVIDER=vector` 或 `hybrid`
- 跑 `run_cross_lingual_retrieval_eval()`（17 题 cross-lingual cohort）；对比当前 `avg_cross_lingual_recall=0.9118 / 0.9688`（去/留 rag-eval-020 两种基线，见 Slice 8 expected-label 审计），目标突破到接近 1.0
- 关键观察点：
  - **rag-eval-011 / pmid-40100009**（皮肤微生态 + S. aureus，CN 查询「肠道菌群」语义偏移）是否被 BGE-M3 在共享语义空间救回
  - **mono-zh / mono-en recall** 是否退化（当前 1.0；若退化则 BGE-M3 在领域文献上不如 `bge-small-zh-v1.5`，需考虑是否回到双轨架构）
  - **首次 encode latency**（CPU 单条 ~50-150ms 预期）是否在 dev 体验可接受范围
- 决策门：
  - 若 sub-slice ③ 显示 cross-lingual recall 显著突破且 mono 不退化 → 写 ADR-0015 草案，决议 BGE-M3 是否成为「跨语 retrieval 默认路径」（仍非全局 default，仅 env-opt-in 的推荐配置）
  - 若 cross-lingual 仅小幅提升或 mono 退化 → spike 写 evaluation 收尾报告，BGE-M3 backend 作为可选项保留但不推默认

### 与本 spike 无关但未处理

- `CLAUDE.md` 工作树有先前 session 的 frontend skill 路由约定改动（+10 行 §Frontend skill routing），本 spike 未触碰、未提交，留待用户单独决定 commit 时机
- 本地 main 比 origin/main 多 3 个 commit（MVP-A closeout / A5 handoff / A3 export 后端化），与本 spike 无关，由用户决定何时 push

## Key files and artifacts

新增 / 修改：
- `docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md`（sub-slice ① 选型评估，195 行）
- `backend/app/services/retrieval/embedding.py`（+`MultilingualBgeM3EmbeddingBackend` 类 + 注册表条目）
- `backend/tests/test_embedding_backend.py`（+3 测试 + import 行扩展）
- `docs/current-state.md`（跨语行 +2 句 closure 增量）
- `docs/handoffs/2026-06-04-multilingual-embedding-spike-sub-slice-2.md`（本文档）

未改：
- `app/services/retrieval/vector_index.py`、`provider.py` 等 retrieval 模块；BGE-M3 作为新 backend 无需任何 vector index / RetrievalProvider 接口变更（ADR-0014 §7 fingerprint rebuild 自然处理 dim 漂移）
- 任何 router / schema / repository / RAG service
- `pyproject.toml` 依赖；`sentence-transformers>=3.0.0` 已在 `[dev]` extras（ADR-0014 §影响 落地），BGE-M3 走同依赖，无需新增 pip 包

## Verification

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_embedding_backend.py -q    # 11 passed
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests                 # 104 files
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests                          # clean
& .\.uv-test-venv\Scripts\python.exe -m mypy app                                      # 54 files, 0 issue
& .\.uv-test-venv\Scripts\python.exe -m pytest -q                                     # 467 passed, 1 skipped
```

CI 等价路径（Linux）：用 `backend/.venv/bin/python` 或 `python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install -e ".[dev]"`，环境构造完成后命令与上同。CI 仍走 default `hashing` backend，永远不触发模型下载。

## Recommended next step

**Sub-slice ③（eval 复跑）**，建议下一会话直接进。前置：
1. 用户确认愿意一次性下载 BGE-M3 权重（~1.4GB）
2. 跑 `BAAI/bge-m3` 首次 encode 烟测（验证 sentence-transformers 能加载 / 与现有 `_load_sentence_transformer` 兼容）；典型命令：
   ```python
   from app.services.retrieval.embedding import MultilingualBgeM3EmbeddingBackend
   b = MultilingualBgeM3EmbeddingBackend()
   v = b.encode(["特应性皮炎与肠道菌群", "atopic dermatitis gut microbiome"])
   print(v.shape)  # (2, 1024)
   ```
3. 跑跨语 eval（`backend/tests/test_cross_lingual_eval.py` 已是 monolingual + cross-lingual baseline 锁定测，需要新写一条 BGE-M3-backed 的对照评估或一次性 ablation 脚本，参考 `scripts/compare_retrieval_strategies.py` 形态）
4. 产出 `docs/evaluations/2026-06-05-multilingual-bge-m3-eval.md` 收尾报告，决定是否进 ADR-0015

如果用户不愿下载权重 / spike 整体收尾：把本 backend 保留为「可选 backend，未在本地验证」，并把 sub-slice ② handoff 升级为 spike 最终收尾文档（明确标注「未跑实测，仅工程接入完成」）。

## Recommended reading order

1. `docs/current-state.md`（跨语行 sub-slice ①/② closure 两句）
2. `docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md`（sub-slice ① 选型评估）
3. 本 handoff
4. `backend/app/services/retrieval/embedding.py`（`MultilingualBgeM3EmbeddingBackend` 类）
5. `backend/tests/test_embedding_backend.py`（lazy 契约 + env 解析测试模式）
6. `docs/adr/0014-retrieval-provider-and-hybrid-search.md` §7（fingerprint rebuild 如何处理 dim 漂移）

---

**生效**：2026-06-04 | sub-slice ① + ② 闭合 | sub-slice ③ 待用户授权下载权重后进
