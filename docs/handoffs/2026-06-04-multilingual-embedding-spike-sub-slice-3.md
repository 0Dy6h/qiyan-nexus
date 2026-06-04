# Session Handoff — 2026-06-04（多语 embedding spike sub-slice ③ + spike 收尾）

branch: `feat/multilingual-bge-m3-backend`（在 PR #12 之上追加 1 commit）
default RAG path: offline `deterministic`，未变
default embedding backend: `hashing`，未变
default retrieval provider: `keyword`，未变
stopped at: spike 三 sub-slice 全闭合 + 负面结论收尾；BGE-M3 backend 保留为 env-opt-in 可选项；不发 ADR-0015；下一可行路径转入 expected-label 数据补齐

## Goal

闭合多语 embedding spike 的第三个 sub-slice：在本地下载 `BAAI/bge-m3` 权重后跑 `run_cross_lingual_retrieval_eval()`，与 keyword baseline 对比，判断是否突破 cross-lingual recall 工程上限。

## Current state

- branch `feat/multilingual-bge-m3-backend` HEAD = sub-slice ③ commit，PR #12 现在含 3 个 commit（①、②、③）
- 三 sub-slice 全部闭合
- **spike 整体负面结论**：BGE-M3 没救回 closeout doc 点名的瓶颈题（rag-eval-011 / pmid-40100009），并在 rag-eval-019 上引入退化
- 默认路径全保留；BGE-M3 backend 保留作为 `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` 显式 opt-in

## Completed in this session (across spike)

### Sub-slice ①（commit `af3f86f`，已合）
- `docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md`：BGE-M3 主选 + multilingual-e5-large 备选 静态对比
- `docs/current-state.md` +1 句

### Sub-slice ②（commit `408da92`，已合）
- `backend/app/services/retrieval/embedding.py`：追加 `MultilingualBgeM3EmbeddingBackend`（`dim=1024`, lazy load `BAAI/bge-m3`）+ 注册
- `backend/tests/test_embedding_backend.py`：+3 单测（lazy / env / Protocol）
- `docs/current-state.md` +1 句
- `docs/handoffs/2026-06-04-multilingual-embedding-spike-sub-slice-2.md`
- 后端 gauntlet 全绿（ruff/mypy/pytest 467 passed, 1 skipped）

### Sub-slice ③（本 commit）
- `backend/scripts/eval_multilingual_bge_m3.py`：4 组对比配置（keyword / vector_hashing / vector_bge_m3 / hybrid_bge_m3）evaluation harness 调用脚本
- `backend/scripts/_diff_bge_m3.py`：一次性 per-item diff helper（脚本不进 suite）
- `docs/evaluations/bge_m3_eval_data.json`：vec_bge / hyb_bge per-item 原始数据
- `docs/evaluations/keyword_baseline_eval_data.json`：keyword / vec_hashing per-item 原始数据
- `docs/evaluations/2026-06-04-multilingual-bge-m3-eval.md`：完整 evaluation 报告（汇总 + 单题 + 退化分析 + 决策门对账）
- `docs/current-state.md` +1 句（spike 收尾）
- 本 handoff

## Key numbers (sub-slice ③)

| label | strategy | embedding | N | mono | cross | div | MRR | elapsed |
|---|---|---|---:|---:|---:|---:|---:|---:|
| keyword（baseline） | keyword | hashing | 16 | **1.0000** | **0.9375** | 0.3765 | 0.9115 | 0.03s |
| vector_hashing | vector | hashing | 16 | 0.8438 | 0.3438 | 0.3405 | 0.4734 | 0.31s |
| vector_bge_m3 | vector | multilingual_bge_m3 | 16 | 1.0000 | 0.6250 | 0.1977 | 0.8750 | 179.53s（首次） |
| hybrid_bge_m3 | hybrid | multilingual_bge_m3 | 16 | 1.0000 | **0.9062** | 0.2289 | 0.9271 | 12.08s |

- **hybrid_bge_m3 vs keyword 净 cross 差 = -0.0313**（绝对 -0.5/16 题）
- mono recall 100% 持平（无退化）
- 单题级 diff：
  - rag-eval-011：双方齐 0.5，**pmid-40100009 仍未进 top-10** —— spike 主线目标失败
  - rag-eval-019：keyword 0.5 → hybrid 0.0，**新增退化**（BGE-M3 把 `pmid-40100001` 提到 rank 2，挤掉 `pmid-40100008`）

## Decision

按 sub-slice ① 文档退路条款：**cross 净下降 0.03 + 有题退化 → 触发 spike 收尾分支**

- ❌ 不发 ADR-0015
- ❌ 不动 retrieval default（`keyword`）
- ❌ 不动 embedding default（`hashing`）
- ❌ 不动 RAG default（`deterministic`）
- ❌ 不动 50 题 RAG eval baseline
- ✅ 保留 BGE-M3 backend 工程接入（env-opt-in 可选）
- ✅ 下一可行路径明确：expected-label 数据补齐（rag-eval-011 pmid-40100009 / rag-eval-020 候选项）

## Still open

### 数据侧（下一会话候选起手）

- **rag-eval-011 / pmid-40100009 expected-label 审计**：closeout doc Loose ends 已列；现在 sub-slice ③ 实证证明这不是 retrieval 算法层能解的（keyword 0.5、BGE-M3 0.0 / 0.5、hybrid 0.5），必须走数据侧
- **rag-eval-020 残余**（Slice 8 已开半步，从 expected_literature 移除 pmid-40100004，bilingual cohort 17→16）：是否进一步审计该题的其他期望

### 工程侧（非阻塞）

- `CLAUDE.md` 工作树 +10 行 frontend skill 路由约定（先前 session 的工作，与本 spike 无关），仍未 commit；用户单独决定
- 本地 main 比 origin/main 多 3 个 commit（MVP-A closeout / A5 / A3 export），与本 spike 无关；用户决定何时 push main

### PR #12

- PR #12 现在含本 sub-slice 的新 commit（总 3 commit），待用户 squash / merge
- PR body 写在 sub-slice ②，sub-slice ③ 结论可由 reviewer 翻 commit log 看；如需要可加 follow-up comment 引用本 handoff

## Key files

新增 / 修改 in sub-slice ③:
- `backend/scripts/eval_multilingual_bge_m3.py`（177 行）
- `backend/scripts/_diff_bge_m3.py`（31 行，一次性 helper）
- `docs/evaluations/bge_m3_eval_data.json`（17835 字节，vec_bge / hyb_bge）
- `docs/evaluations/keyword_baseline_eval_data.json`（keyword / vec_hashing baseline）
- `docs/evaluations/2026-06-04-multilingual-bge-m3-eval.md`（完整报告）
- `docs/current-state.md`（跨语行 +1 句）
- `docs/handoffs/2026-06-04-multilingual-embedding-spike-sub-slice-3.md`（本文档）

未触碰：
- `backend/app/services/retrieval/` 任何代码（embedding.py 内的 backend 实现保留）
- `backend/app/services/retrieval_eval.py`（已存在 `run_cross_lingual_retrieval_eval()`，本次只调用不改）
- `backend/pyproject.toml`
- 任何 router / schema / repository / RAG service

## Verification

```powershell
# 工程门禁（仍同 sub-slice ② baseline）
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q

# 重跑本 sub-slice 评估（vector_bge_m3 / hybrid_bge_m3 首次需下载 ~1.4GB BGE-M3 权重）
& .\.uv-test-venv\Scripts\python.exe scripts\eval_multilingual_bge_m3.py keyword vector_hashing --json ..\docs\evaluations\keyword_baseline_eval_data.json
& .\.uv-test-venv\Scripts\python.exe scripts\eval_multilingual_bge_m3.py vector_bge_m3 hybrid_bge_m3 --json ..\docs\evaluations\bge_m3_eval_data.json
& .\.uv-test-venv\Scripts\python.exe scripts\_diff_bge_m3.py
```

CI 不跑 eval 脚本路径，default `hashing` backend 永不下载权重。

## Recommended next action

按 spike 实证导向：

1. **rag-eval-011 expected-label 审计**（最高优先）：判定 pmid-40100009「皮肤微生态」是否仍合法保留为该题期望；如保留则该题接受 0.5 上限作为 documented limit
2. **PR #12 squash + merge**（轻量收尾，把 spike 全 3 commit 合入 main，让 evaluation 报告作为 archive 可查）
3. **MVP-A closeout doc 修订**（小改）：把"多语 embedding spike"从「推荐下次起手」改为「已落地，负面结论」，并把 §阶段 B 入口准备 优先级 1 替换为 expected-label 审计
4. 可选独立议题：PostgreSQL/pgvector spike（与本 spike 无关，但仍是 closeout doc 列的候选）

## Recommended reading order

1. `docs/evaluations/2026-06-04-multilingual-bge-m3-eval.md`（本 spike 核心结论 + 数字）
2. 本 handoff
3. `docs/handoffs/2026-06-04-multilingual-embedding-spike-sub-slice-2.md`（sub-slice ② 接入交接）
4. `docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md`（sub-slice ① 选型推荐）
5. `backend/scripts/eval_multilingual_bge_m3.py`（评估脚本骨架，未来重跑可直接复用）

---

**生效**：2026-06-04 | spike 三 sub-slice 全闭合 + 负面结论收尾 | 下一会话建议起手 expected-label 审计
