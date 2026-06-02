# Session Handoff — 2026-06-02（跨语言术语桥扩展，条件①收尾）

branch: main（改动未提交，按惯例待用户决定是否 commit）
default RAG path: offline `deterministic`，未变
stopped at: 纯数据术语桥扩展完成，rag-eval-011 闭合，035/047/020 结构性上限已记录，全量绿

## Goal

按 ADR-0012 更新（四）条件①「可继续扩展术语映射覆盖剩余 4/17 弱召回题」，以**纯数据**方式
（只改 `cross_lingual_terms.json`）闭合可桥接的跨语弱召回题，不动默认检索排序，并诚实记录数据
手段无法闭合的结构性上限。

## Current state

- `run_cross_lingual_retrieval_eval()`（keyword, top_k=10, 17 双语题）`avg_cross_lingual_recall`
  从 **0.7647 → 0.7941**，mono 保持 1.0。
- **rag-eval-011**（中英文献 AD 微生态研究对比）`cross_recall` `0.0 → 0.5`：40100002 进 top-10（rank 6）。
- 诊断确认其余 3 题受 raw-rank 评分结构 / 弱标注所限，**不属纯数据范围**：
  - rag-eval-035 / 047：中文单字 token 淹没英文文献，40100002 仅差 1 名落在 rank 11。
  - rag-eval-020：合规题，期望「草药系统综述」与问题无主题重叠（弱标注）。
- L2/default preview 仍不翻转；默认 provider 仍 `deterministic`。

## Completed in this session

- 只读诊断（未提交）定位 4 题实际排名与根因，验证「`微生态`→`gut` canonical → `+9` tag-bonus」杠杆。
- 改 `backend/data/retrieval/cross_lingual_terms.json`：`gut` 条目 zh 增加 `"微生态"`（一词）。
- 加两条回归测试到 `backend/tests/test_cross_lingual_eval.py`：
  - `test_rag_eval_011_cross_lingual_recall_above_zero`（011 cross>0 且 40100002 在 top-10）。
  - `test_cross_lingual_term_bridge_no_aggregate_regression`（avg_cross ≥ 0.7647 且 mono == 1.0）。
- 新增评估笔记 `docs/evaluations/2026-06-02-cross-lingual-term-bridge-extension.md`。
- 更新 `docs/current-state.md`（跨语检索段 + 候选⑦条件①）与 `docs/adr/0012-real-llm-enablement.md`
  （新增更新（十一））。

## Still open / blocked

- **纯术语桥天花板已到**：035/047/020 不是缺词，而是评分结构（中文单字淹没 + `+7` tag-bonus 仅限
  8 个 `_KEYWORD_ALIASES` 键）与弱标注。继续提升需独立、更大的决策（见下）。
- rag-eval-011 的 40100009 仍在 top-10 外（缺 `gut_skin_axis` 标签），纯数据无法拉进，属已知上限。

## Key files and artifacts

- `backend/data/retrieval/cross_lingual_terms.json`（`gut` 条目 +「微生态」）
- `backend/tests/test_cross_lingual_eval.py`（+2 回归锁）
- `docs/evaluations/2026-06-02-cross-lingual-term-bridge-extension.md`
- `docs/current-state.md`、`docs/adr/0012-real-llm-enablement.md`
- 评估 harness：`backend/app/services/retrieval_eval.py`；注入逻辑：`backend/app/services/retrieval/provider.py`

## Verification

- `& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_cross_lingual_eval.py -q` — 22 passed。
- `& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` — clean。
- `& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` — clean。
- `& .\.uv-test-venv\Scripts\python.exe -m mypy app` — clean。
- `& .\.uv-test-venv\Scripts\python.exe -m pytest -q` — **361 passed**。
- 前端未触及，无需跑前端 gauntlet。

## Recommended next step

跨语线纯术语桥已收口。若要继续提升跨语召回，需在以下独立方向择一并单独决策（均超出纯数据范围）：

1. **受控打分修复**：让 `microbiome` 参与 `+7` tag-bonus，或抑制中文单字 token 淹没——改默认检索
   排序，**必须全量重验 50 题 RAG eval**。可救回 035/047（两者均仅差 1 名）。
2. **expected-label 复核**：rag-eval-020（合规题配草药综述）、011 的 40100009 是否为合理跨语期望。
3. **多语 embedding**（bge-m3 / multilingual-e5-large）替代/补充 keyword 桥。

或转其它主线（见 `docs/current-state.md` §下一步候选：网络图交互增强、后端网络报告导出、runtime
JSON → SQLite spike）。

## Recommended reading order

1. `docs/current-state.md`
2. `docs/evaluations/2026-06-02-cross-lingual-term-bridge-extension.md`
3. `docs/adr/0012-real-llm-enablement.md`（更新（十一））
4. `backend/app/services/retrieval/provider.py`（`tokenize_query` / `score_item` / `alias_tag_bonus`）
