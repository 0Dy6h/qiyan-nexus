# Eval Corpus Isolation and rag-eval-011 Audit — 2026-06-04

## 结论

- RAG eval 与 cross-lingual retrieval eval 的默认语料已改为 immutable seed corpus。
- Runtime/local uploaded PDF state 仍可评估，但必须显式选择：API/query/service 参数 `corpus="runtime"`，BGE-M3 对比脚本参数 `--corpus runtime`。
- Eval summary 新增 `corpus` 字段，前端 `/evals/rag-ad` 报告页显示 `语料范围`。
- `rag-eval-011` 的 expected-label/data bridge 已闭合：`pmid-40100009` 继续作为合法英文 skin microbiome / S. aureus 视角保留，且对应 chunk `chunk-pmid-40100009-staph` 已纳入 expected chunks。
- Seed keyword cross-lingual cohort 当前结果：`N=16`，`avg_monolingual_recall=1.0000`，`avg_cross_lingual_recall=1.0000`。

## 背景

2026-06-04 BGE-M3 eval spike 发现本地 runtime 中存在 uploaded PDF chunks，会改变默认 eval 结果：

- seed cross-lingual baseline 曾为 `0.9688`
- local runtime default 曾为 `0.9375`
- RAG eval report 在 runtime 污染下可降到 `41/50`，而 seed benchmark 预期应保持 `>=46/50`

因此，本次修复把 benchmark eval 从运行态中隔离出来。Runtime 仍保留为本地开发/演示状态，但不再悄悄影响默认质量门禁。

## 变更

### Backend contract

- `backend/app/schemas/eval.py`
  - 新增 `EvalCorpus = Literal["seed", "runtime"]`
  - `RagEvalSummary` / `CrossLingualRetrievalSummary` 新增 `corpus`

- `backend/app/services/retrieval_eval.py`
  - `run_cross_lingual_retrieval_eval(..., corpus="seed")`
  - 默认读取 `backend/data/literature/sample_ad_literature.json` 与 `sample_ad_chunks.json`
  - `corpus="runtime"` 时读取 runtime state paths

- `backend/app/services/eval.py`
  - `run_rag_ad_eval_report(..., corpus="seed")`
  - 默认通过 seed repositories 调用 RAG service
  - `corpus="runtime"` 时沿用当前 runtime RAG path

- `backend/app/services/rag.py`
  - `answer_question()` 增加可选 repository injection
  - 默认 `/api/rag/answer` 行为不变

- `backend/app/api/eval.py`
  - `/api/evals/rag-ad/report?corpus=seed|runtime`
  - unknown corpus 由 FastAPI/Pydantic 返回 `422`

### Data audit

- `backend/data/retrieval/cross_lingual_terms.json`
  - microbiome zh aliases 新增「微生态」「皮肤微生态」
  - microbiome en aliases 新增 `skin microbiome`

- `backend/data/evals/rag_ad_eval_questions.json`
  - `rag-eval-011.expected_chunk_ids` 新增 `chunk-pmid-40100009-staph`

这不是 ranking rule change，也没有翻转 vector/hybrid/BGE-M3/default LLM。它只是把原本合理的 q011 skin microbiome 期望用数据桥表达完整。

## 验证

Focused backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_cross_lingual_eval.py -q
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_eval_service.py tests\test_eval_api.py -q
```

CLI smoke:

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
```

Observed in the focused run path: `156` tests passed.

## Notes

- `backend/data/runtime/` remains local, gitignored runtime state.
- Existing BGE-M3 evaluation JSON artifacts are historical runtime-scoped outputs; do not rewrite them in this slice.
- BGE-M3 remains opt-in via `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3`; default retrieval remains `keyword`.
