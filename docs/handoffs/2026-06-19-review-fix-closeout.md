# 2026-06-19 Review Fix Closeout Handoff

## Goal

处理待提交审查报告中的问题并收口当前内部预览准备分支：修复 RAG 公式/药材实体查询误拒、DOCX 导出换行和 XML 控制字符问题、单字「肠」误命中风险，同时完成工作记录、交接和本地门禁验证。

## Current state

- RAG 默认路径仍为 `deterministic` provider + `keyword` retrieval，不启用真实 LLM / embedding / 生产数据库。
- RAG 可以处理不含 AD 字样但命中 seed/entity 关系的领域内查询：
  - `消风散的组成有哪些` -> `cn-ad-formula-002`
  - `黄芪的功效` -> 通过 `herb-huangqi` / `formula-danggui-yinzi` 关系返回 `cn-ad-formula-002`
- 离题查询守卫更稳：
  - `肠梗阻怎么治疗` -> 0 citations
  - `高血压一线降压药` -> 0 citations
- RAG 导出支持 Markdown 和 Word `.docx`：
  - Markdown: `POST /api/rag/answer/export`
  - DOCX: `POST /api/rag/answer/export/docx`
- `.docx` 由 `backend/app/services/rag_docx.py` 用标准库生成最小 OOXML 包，保留多行换行，并剥离 XML 1.0 非法控制字符。
- Reviewer 入门单页已存在：`docs/REVIEWER-GUIDE.md`。

## Completed in this session

- RAG retrieval / guard:
  - 从 gut alias 中移除单字 `肠`，保留 `肠道` / `肠-脑` / `微生态` 等有效 gut-axis 词。
  - 从 network seed 注入复方/药材实体 token，使 `消风散`、`黄芪` 等实体名能桥接到 literature/chunk `related_entity_ids`。
  - RAG citation selection 对 entity-only 查询优先限制在真实 entity-linked candidate pool，避免用单字噪声补满 `top_k`。
  - `cn-ad-formula-002` seed 文献补充 `herb-huangqi` 关系，与 network seed 的当归饮子/黄芪关系对齐。
- DOCX export:
  - 新增后端 `build_answer_docx()` 与 `/api/rag/answer/export/docx`。
  - DOCX 文本节点先清理 XML 非法控制字符，再 XML escape。
  - 回答中的 `\n` / `\r\n` / `\r` 渲染为 `<w:br/>`。
- Frontend/product readiness already in this commit scope:
  - `/rag` 增加 Word `.docx` 导出按钮。
  - 首页和左侧 shell 文案更聚焦核心工作流与内部预览边界。
  - Network mock 结果不再显示像真实置信度一样的分数文案。
  - Literature source label 从 `CNKI sample` 调整为 `CNKI 样本`。
  - README 增加产品定位、能力边界和 live network 风险提示。
  - `backend/scripts/seed_pubmed_corpus.py` 作为 operator 工具，用于将真实 PubMed 记录写入 runtime state，不污染 seed。

## Still open / blocked

- 未运行 Playwright E2E；统一脚本提示 reviewer walkthrough 或 branch closeout 前再跑 `.\scripts\verify-local.ps1 -IncludeE2E`。
- 正式 clinician / research reviewer sign-off 仍未完成，自动化和内部代走不能替代真人反馈。
- RAG 对 `黄芪` 的回答仍只限当前 AD seed/entity-linked 文献，不代表完整中药药性/功效知识库；这是刻意保守边界。
- Network live mode 仍不建议用于内部预览走查；默认 mock 不变。

## Key files and artifacts

- `backend/app/services/rag.py`
- `backend/app/services/retrieval/provider.py`
- `backend/app/services/rag_docx.py`
- `backend/app/api/rag.py`
- `backend/data/retrieval/cross_lingual_terms.json`
- `backend/data/literature/sample_ad_literature.json`
- `backend/tests/test_rag_service.py`
- `backend/tests/test_retrieval_provider.py`
- `backend/tests/test_rag_docx_export.py`
- `frontend/components/RagAnswerClient.tsx`
- `frontend/lib/api/rag.ts`
- `frontend/lib/rag-export.ts`
- `backend/scripts/seed_pubmed_corpus.py`
- `docs/REVIEWER-GUIDE.md`
- `README.md`
- `CLAUDE.md`
- `docs/current-state.md`

## Verification

- Focused backend:
  - `pytest tests\test_rag_service.py::test_answer_question_allows_formula_name_query_without_ad_term ... -q` — passed after fix
  - `pytest tests\test_rag_docx_export.py -q` — passed
  - `pytest tests\test_retrieval_provider.py -q` — passed
  - `pytest tests\test_rag_service.py tests\test_rag_api.py tests\test_rag_docx_export.py -q` — passed
- Full backend:
  - `ruff format --check app tests` — passed
  - `ruff check app tests` — passed
  - `mypy app` — passed
  - `pytest -q` — `579 passed, 1 skipped`
- Unified local verification:
  - `.\scripts\verify-local.ps1` — passed
  - Backend: `579 passed, 1 skipped`
  - Frontend: `215 passed`, typecheck passed, build passed
- E2E:
  - Not run in this session.

## Recommended next step

Run reviewer-prep E2E only if this commit is being used for branch-level closeout or formal walkthrough:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

Then proceed to真人 reviewer sign-off using `docs/REVIEWER-GUIDE.md` and `docs/evaluations/2026-06-05-reviewer-feedback.md`.

## Recommended reading order

1. `docs/current-state.md`
2. `README.md`
3. `docs/REVIEWER-GUIDE.md`
4. `backend/app/services/rag.py`
5. `backend/app/services/retrieval/provider.py`
6. `backend/app/services/rag_docx.py`
7. `backend/tests/test_rag_service.py`
8. `backend/tests/test_rag_docx_export.py`

## Recommended skill / toolset

- `test-driven-development` for any further RAG/export behavior changes.
- `dogfood` before reviewer walkthrough.
- `github-code-review` or local review stance before PR/merge.
- `session-handoff` after the next meaningful product/reviewer slice.
