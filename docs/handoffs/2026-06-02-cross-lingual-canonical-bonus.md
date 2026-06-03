# Session Handoff — 2026-06-02（跨语言 canonical tag-bonus 扩展，Slice 7）

branch: `feat/cross-lingual-term-bridge`（已提交 1 个 feat commit + 1 个 docs follow-up commit）
default RAG path: offline `deterministic`，未变
stopped at: 受控打分修复完成，rag-eval-035/047 闭合，cross-lingual recall 0.7941 → 0.9118，全量绿

## Goal

执行 Slice 6 handoff（`2026-06-02-cross-lingual-term-bridge.md`）头号 follow-up：以**受控打分修复**闭合 rag-eval-035 / 047（两题目标文档 pmid-40100002 均卡 rank 11，纯术语桥救不回），不动 ranking 排序键、disclaimer、router 层。

## Current state

- `run_cross_lingual_retrieval_eval()`（keyword, top_k=10, 17 双语题）`avg_cross_lingual_recall`
  从 **0.7941 → 0.9118**，mono 保持 1.0。完美跨语题 13/17 → **15/17**。
- **rag-eval-035** `cross_recall` `0.0 → 1.0`：pmid-40100002 进 top-10。
- **rag-eval-047** `cross_recall` `0.0 → 1.0`：pmid-40100002 进 top-10。
- **rag-eval-011** `cross_recall` 保持 `0.5`：pmid-40100009 仍缺 `gut_skin_axis` 标签（已知数据侧上限）。
- L2/default preview 仍不翻转；默认 provider 仍 `deterministic`。

## Completed in this session

- 改 `backend/app/services/retrieval/provider.py`：新增 `_canonical_token_set()` helper，把 `alias_tag_bonus`
  的识别集从 `_KEYWORD_ALIASES.keys()` 扩展为「`_KEYWORD_ALIASES.keys()` ∪ `cross_lingual_terms.json`
  中所有 canonical」。权重 `+2` / `+7` 不变。3 行核心 + 1 helper。
- 加 3 条新测：
  - `test_alias_tag_bonus_honours_cross_lingual_canonicals`（单元）
  - `test_rag_eval_035_cross_lingual_recall_equals_one`（035 单题）
  - `test_rag_eval_047_cross_lingual_recall_equals_one`（047 单题）
- 把 `_CROSS_LINGUAL_RECALL_BASELINE` 收紧 `0.7647 → 0.9118`（实测值）。
- 更新 7 个固定 top-1 的旧测：cn-ad-gbs-001 与 cn-ad-microbiome-003 在「肠-脑-皮肤轴」中文查询下
  tie-break 互换（前者 +7、后者 +14），两文档仍同处 top-2，eval set 把两者都列为 rag-eval-001
  expected_literature——属合理 swap，非质量回退。3 个 provider-swap mock 加
  `QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0`（claim 文本原为 gbs-001 wording 定制，与该测试主题无关）。
- 新增 `docs/evaluations/2026-06-02-cross-lingual-canonical-bonus.md`。
- 更新 `docs/current-state.md`（跨语段补 Slice 7 闭合）。

## Still open / blocked

- **rag-eval-011 的 pmid-40100009**：缺 `gut_skin_axis` 标签，纯打分救不回，需要 expected-label
  审计 + 数据侧标签补齐。Slice 6 handoff 已列为独立候选。
- **rag-eval-020**：合规题与「草药系统综述」期望弱关联，同属 expected-label 审计候选。
- **L2 翻转阻塞点**：不在 retrieval 而在 grounding NLI 60% 拦截率
  （`2026-06-02-claim-quality-v2-live-validation.md`），与本 slice 无关。

## Key files and artifacts

- `backend/app/services/retrieval/provider.py`（`_canonical_token_set` + `alias_tag_bonus`）
- `backend/tests/test_retrieval_provider.py`（+1 单元测 + 1 顺序更新）
- `backend/tests/test_cross_lingual_eval.py`（+2 单题测 + 1 baseline 收紧）
- `backend/tests/test_rag_service.py`（4 个 fixture 顺序更新 + 3 个 mock 加 grounding 豁免）
- `backend/tests/test_rag_api.py`（1 个 fixture 顺序更新）
- `docs/evaluations/2026-06-02-cross-lingual-canonical-bonus.md`
- `docs/current-state.md`（跨语段补 Slice 7）

## Verification

- `.venv/Scripts/python.exe -m pytest tests/test_cross_lingual_eval.py -q` — 25 passed。
- `.venv/Scripts/python.exe -m ruff format --check app tests` — clean。
- `.venv/Scripts/python.exe -m ruff check app tests` — clean。
- `.venv/Scripts/python.exe -m mypy app` — clean。
- `.venv/Scripts/python.exe -m pytest -q` — **447 passed, 1 skipped**。
- 前端未触及，无需跑前端 gauntlet。

## Recommended next step

跨语检索召回已近上限。下一 slice 候选（按 Slice 6 / 7 handoff 沉淀的优先级）：

1. **rag-eval-011 pmid-40100009 + rag-eval-020 expected-label 审计**：纯数据修，无 ranking 风险。
2. **网络图前端交互**（hover edges, click focus）+ **网络报告导出按钮**（已就绪的 markdown API 接到前端）。
3. **L2 governance**：NLI 拦截率重新校准 / BGE prefilter 阈值复议（独立 ADR 决策包）。
4. **多语 embedding**（bge-m3 / multilingual-e5-large）：跨架构方向，工程量大。

## Recommended reading order

1. `docs/current-state.md`（跨语段）
2. `docs/evaluations/2026-06-02-cross-lingual-canonical-bonus.md`
3. `docs/handoffs/2026-06-02-cross-lingual-term-bridge.md`（Slice 6 上下文）
4. `backend/app/services/retrieval/provider.py`（`_canonical_token_set` / `alias_tag_bonus`）
