# Session Handoff — 2026-06-04（Eval corpus isolation + rag-eval-011 数据审计）

## Goal

本 session 接在 BGE-M3 多语 embedding spike 负面收尾之后，目标是把 RAG / cross-lingual eval 从本地 runtime 污染中隔离出来，并完成 `rag-eval-011` 的数据侧审计。当前实现、测试和文档均已落地；本 handoff 是收工交接，不是待实现计划。

## Current state

- RAG eval 与 cross-lingual retrieval eval 默认读取 tracked seed corpus，不再悄悄消费 `backend/data/runtime/` 的 uploaded PDF chunks。
- Runtime eval 仍保留，但必须显式 opt-in：
  - API: `/api/evals/rag-ad/report?corpus=runtime`
  - service: `run_rag_ad_eval_report(corpus="runtime")`
  - retrieval eval: `run_cross_lingual_retrieval_eval(corpus="runtime")`
  - BGE-M3 eval script: `scripts/eval_multilingual_bge_m3.py --corpus runtime`
- Eval summary 新增 `corpus` 字段；前端 `/evals/rag-ad` 报告页显示 `语料范围`。
- `rag-eval-011` 数据桥已补齐：
  - `expected_chunk_ids` 增加 `chunk-pmid-40100009-staph`
  - microbiome bridge 增加「微生态」「皮肤微生态」和 `skin microbiome`
- Seed keyword cross-lingual cohort 当前为 `N=16`，`avg_monolingual_recall=1.0000`，`avg_cross_lingual_recall=1.0000`。
- 默认路径仍未翻转：RAG = `deterministic + keyword`，embedding default = `hashing`，BGE-M3 仍是 env opt-in。

## Completed in this session

### Backend eval contract

- `backend/app/schemas/eval.py`
  - 新增 `EvalCorpus = Literal["seed", "runtime"]`
  - `RagEvalSummary` / `CrossLingualRetrievalSummary` 增加 `corpus`
- `backend/app/services/retrieval_eval.py`
  - `run_cross_lingual_retrieval_eval(..., corpus="seed")`
  - 默认读 `backend/data/literature/sample_ad_literature.json` 与 `sample_ad_chunks.json`
  - `corpus="runtime"` 才读 runtime storage paths
- `backend/app/services/eval.py`
  - `run_rag_ad_eval_report(..., corpus="seed")`
  - 默认通过 seed repositories 调用 RAG
- `backend/app/services/rag.py`
  - `answer_question()` 增加可选 repository injection
  - 普通 `/api/rag/answer` 默认行为不变
- `backend/app/api/eval.py`
  - `/api/evals/rag-ad/report` 接受 `corpus=seed|runtime`
  - unknown corpus 返回 FastAPI/Pydantic `422`

### Data audit

- `backend/data/evals/rag_ad_eval_questions.json`
  - `rag-eval-011.expected_chunk_ids` 增加 `chunk-pmid-40100009-staph`
- `backend/data/retrieval/cross_lingual_terms.json`
  - microbiome zh aliases 增加「微生态」「皮肤微生态」
  - microbiome en aliases 增加 `skin microbiome`

### Frontend

- `frontend/lib/api/evals.ts`
  - `RagEvalSummary` 增加 `corpus`
  - 新增 `getRagEvalCorpusLabel()`
- `frontend/components/RagEvalReportClient.tsx`
  - summary cards 增加 `语料范围`
  - 长文本 metric 自动用较小字号，避免卡片拥挤
- `frontend/tests/evals-api.test.ts`
  - 覆盖 corpus 字段和 label helper
- `frontend/tests/client-section-consistency.test.ts`
  - 锁定 eval report 必须显示 corpus scope

### Script and docs

- `backend/scripts/eval_multilingual_bge_m3.py`
  - 新增 `--corpus seed|runtime`，默认 `seed`
  - summary table 输出 corpus
- `README.md`
  - 补 `/api/evals/rag-ad/report?corpus=runtime` 示例
  - 说明默认 seed、runtime 显式 opt-in
- `docs/current-state.md`
  - 补 eval corpus isolation 与 q011 审计当前事实
- `docs/evaluations/2026-06-04-eval-corpus-isolation-and-rag-eval-011-audit.md`
  - 本轮专项评估报告，下一 session 优先读它

## Still open / deferred

- 没有把 BGE-M3 设为默认；2026-06-04 BGE-M3 eval 仍是负面 spike 结论。
- 没有重写历史 artifact：`docs/evaluations/bge_m3_eval_data.json`、`keyword_baseline_eval_data.json` 保留为历史 runtime-scoped 输出。
- 没有把 RAG eval top_k=3 调整为 top_k=10。RAG generation eval 仍按“至少命中一个 expected literature/chunk”口径；cross-lingual retrieval eval 才验证 q011 top-10 同时召回 `pmid-40100002` 和 `pmid-40100009`。
- 未处理本 session 前已存在的无关 dirty files：
  - `CLAUDE.md`
  - `frontend/e2e/start-backend.mjs`
  - `frontend/next-env.d.ts`

## Verification

Backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Observed:

- `ruff format --check`: `104 files already formatted`
- `ruff check`: `All checks passed`
- `mypy`: `Success: no issues found in 54 source files`
- full pytest: `474 passed, 1 skipped`

Focused backend:

- `tests/test_cross_lingual_eval.py`: `27 passed`
- `tests/test_eval_service.py tests/test_eval_api.py`: `26 passed`

Script smoke:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\eval_multilingual_bge_m3.py keyword --corpus seed
```

Observed:

```text
corpus=seed N=16 top_k=10 mono=1.0000 cross=1.0000 div=0.3864 mrr=0.9167
```

Frontend:

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Observed:

- `pnpm test`: `156 passed`
- `pnpm typecheck`: passed
- `pnpm build`: passed
- `pnpm e2e`: `3 passed`

Note: `pnpm typecheck` was first run in parallel with `pnpm build` and hit a `.next/types` race (`TS6053` missing generated files). Re-running `pnpm typecheck` alone passed. Treat that first failure as a tooling race, not a TypeScript/code failure.

Smoke metrics captured after implementation:

```text
RAG summary: corpus=seed, passed_questions=46/50, pass_rate=0.92,
citation_hit_count=49, chunk_hit_count=47, disclaimer_coverage_count=50,
must_not_violation_count=0, grounding_blocked_count=0

Cross summary: corpus=seed, N=16, avg_monolingual_recall=1.0,
avg_cross_lingual_recall=1.0, avg_language_diversity=0.3864,
avg_precision_at_k=0.2313, avg_mrr=0.9167

Cross q011 retrieved_ids include:
cn-ad-microbiome-003, pmid-40100002, pmid-40100009
```

## Key files and artifacts

Read in this order:

1. `docs/evaluations/2026-06-04-eval-corpus-isolation-and-rag-eval-011-audit.md`
2. `docs/current-state.md`
3. `backend/app/services/eval.py`
4. `backend/app/services/retrieval_eval.py`
5. `backend/app/services/rag.py`
6. `backend/tests/test_cross_lingual_eval.py`
7. `backend/tests/test_eval_service.py`
8. `backend/tests/test_eval_api.py`
9. `frontend/components/RagEvalReportClient.tsx`
10. `frontend/lib/api/evals.ts`

## Recommended next step

Best next engineering move: prepare a clean commit or PR from this slice, excluding the three unrelated dirty files listed above. If continuing feature work instead, the next smallest useful slice is not another retrieval algorithm change; it is a project-quality cleanup around stale cross-lingual prose in `docs/current-state.md` and older handoffs that still describe q011 as a “keyword bridge ceiling.” Keep that as a docs cleanup commit, not bundled with behavior changes.

## Recommended skill / toolset

- `test-driven-development` for any further behavior change.
- `qiyan-ui-defaults` + `ui-ux-pro-max` for any `/evals/rag-ad` interface work.
- `neat-freak` at the next milestone, especially if stale cross-lingual docs are cleaned up.
