# B2 prep notes — RAG eval 扩展到 50 题（2026-05-22 起草）

> PR #1 merge 后从 main 切 `feat/b2-rag-eval-50q`，照本文执行。

## 事实盘点（B1 完成时刻的 baseline）

- 文献池：20 篇（10 CN + 10 PubMed），不需新增
- chunk 池：12 条；可能需补 4–8 条让新题精准命中
- 现有 eval：20 题，pass_rate = 20/20 = 100%
- 测试硬锁：
  - `test_load_rag_eval_dataset_returns_20_questions` → `len == 20`
  - `test_run_rag_ad_eval_report_*` → `total_questions == 20`、`chunk_hit_count == 20`、`passed_questions == 20`、`citation_hit_count == 20`、`disclaimer_coverage_count == 20`、`must_not_violation_count == 0`
  - q019 lit-hit 三元组 `[cn-ad-network-007, pmid-40100008, pmid-40100005]`

## 30 道新题主题分布

| 主题簇 | 题数 | 命中文献候选 |
|---|---|---|
| Formula 机制（复方研究） | 6 | cn-ad-formula-002, cn-ad-network-007, pmid-40100004 |
| Target / Pathway（JAK-STAT, Th2, IL-31, NF-κB, filaggrin） | 8 | pmid-40100005, pmid-40100001, pmid-40100006, cn-ad-network-007 |
| Microbiome 深入（菌群-皮肤-免疫） | 4 | pmid-40100002, pmid-40100007, pmid-40100009, cn-ad-microbiome-003 |
| 儿童分层 / 表型 | 3 | cn-ad-child-009, pmid-40100010 |
| 屏障修复 / 外治 | 4 | cn-ad-barrier-006, cn-ad-external-008, pmid-40100006 |
| 证据图谱 / 综述方法 | 3 | cn-ad-review-010, pmid-40100004 |
| Network pharmacology 工作流（herb→compound→target→pathway） | 2 | cn-ad-network-007, pmid-40100008 |

## 测试改动表

| 测试 | 现状 | B2 目标 |
|---|---|---|
| `test_load_rag_eval_dataset_returns_20_questions` | `== 20` | 改名 `_returns_50_questions` + `== 50` |
| `test_get_rag_eval_questions_returns_serializable_payload` | `== 20` | `== 50`；末题断言换成 q050 或保留 q017 抽样 |
| `test_run_rag_ad_eval_report_*` summary counts | hardcode 20 | 全部改为 50 |
| `test_run_rag_ad_eval_report_meets_baseline_pass_rate` | `passed_questions == 20`（100%） | 改为 `passed_questions >= 48`（≥95%），保留 citation/disclaimer/violation 硬锁 |
| `chunk_hit_count == 20` | 严格 | 若补 chunk 后能维持高命中率则改 `>= 45`；否则改判定逻辑接受 `expected_chunk_ids == []` 的新题 |
| q019 lit-hit lock | 保留 | 不动 |

## 关键风险 + 对冲

1. **95% pass rate 难度**：deterministic retrieval 在 20 篇文献内复用容易"hit 同一篇"，但 `must_include` 词如果不在文献 snippet / abstract / chunk text 里就会 miss。**对冲**：每题 must_include 词都从文献原文反查；先跑 `run_rag_ad_eval_report` 看哪题 fail 再迭代。
2. **chunk_hit 退化**：新题如果设 `expected_chunk_ids` 但未补 chunk → fail。**对冲**：要么不设 expected_chunks（被 `eval.py` 第 51 行 `not question.expected_chunk_ids or bool(expected_chunk_hits)` 接受），要么先补 chunk 再造题。
3. **q019 lock 别破**：新题别覆盖 q019 的 expected_literature_ids 排序逻辑（network / targeted_therapy rerank 路径）。
4. **must_include 中文断言需要在文献里有原文**：英文文献的 snippet 是英文，问中文问题去 `source_preference="pubmed"` 时 must_include 选英文 token（barrier、microbiome 等），别选中文。

## 执行步骤（TDD 节奏）

1. 改 4–6 个 fail-counter 测试为 `== 50` / `>= 48`（先看到红）
2. 起草 30 题草稿（JSON），先用机器生成命中性高的题再人工抛光
3. 跑 `pytest tests/test_eval_service.py -q` → 看哪题 fail → 调 `must_include` / `source_preference` / `expected_literature_ids`
4. 视情况补 4–8 条 chunk 入 `sample_ad_chunks.json`（注意保留现有 q019 chunk）
5. 全 gauntlet 绿 → commit → handoff doc → PR

## 工作量

- 题目设计 + 调试：1.0d
- chunk 补齐：0.3d
- 测试更新 + gauntlet：0.2d
- handoff + PR：0.2d
- **合计 ≈ 1.7d**（roadmap §3.2 B2 估 2d 之内）

## 不在 B2 范围

- 不引入真实 embedding / 向量检索（C3 才做）
- 不改 `DISCLAIMER` 字符串
- 不调 `_KEYWORD_ALIASES` 别名表（动它会污染现有 20 题的 pass）
- 不接 LLM provider 对比 eval（B1 已抽象，但 B2 eval 仍只跑 deterministic provider）

## 触发条件

- PR #1（feat/b1-llm-provider-abstraction）merge 后立即开 `feat/b2-rag-eval-50q`
- 若 PR #1 review 中改动 `app/services/eval.py` / `app/services/rag.py` / eval JSON，B2 起点重新对齐本文档
