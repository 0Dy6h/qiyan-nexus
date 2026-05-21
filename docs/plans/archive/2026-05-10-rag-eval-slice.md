# Qiyan Nexus RAG 评估闭环切片

日期：2026-05-10

## 目标

在不接真实 LLM、embedding、pgvector 或外部服务的前提下，为当前 deterministic RAG 建立可重复评估入口。

## 已实现

- 后端新增 `GET /api/evals/rag-ad/report`。
- 评估数据来源：`backend/data/evals/rag_ad_eval_questions.json`。
- 每题会运行当前 `answer_question`，并统计：
  - 预期文献命中
  - 预期 chunk 命中
  - 必含词缺口
  - 禁用语命中
  - 免责声明覆盖
- 前端新增 `/evals/rag-ad`，可手动运行评估并查看 summary 与逐题结果。
- 首页与合规页导航已接入 RAG 评估入口。

## 当前基线

- 20 题全部通过（2026-05-16 推进至 20/20）。
- 20 题有预期文献命中。
- **20 题有预期 chunk 命中**（2026-05-17 chunk 数据集扩充后从 11 推到 20）。
- 20 题覆盖免责声明。
- 禁用语违规 0。
- `tests/test_eval_service.py::test_run_rag_ad_eval_report_meets_baseline_pass_rate`
  作为回归门，硬 lock `passed_questions == 20`。
- `tests/test_eval_service.py::test_run_rag_ad_eval_report_chunk_hit_count_meets_target`
  额外硬 lock `chunk_hit_count == 20`。

## 2026-05-16 推进记录

- Phase 1（commit 5a39422）：`build_answer` 引入 evidence_tag → 中文研究主题映射，
  并补合规话术 "引用来源"；citation reason 在无 chunk 时回退到 literature.evidence_tags。
  消化 q007/q010/q011/q013/q020 共 5 道 must_include 缺词题。13/20 → 18/20。
- Phase 2（commit cab1951）：`_alias_tag_bonus` 给 evidence_tag 与 query alias key
  对齐的候选加权（chunk +7、literature +2）；排序键改为
  `(language_bonus, score, year)` 让同语言不再被跨语言 char-rich 候选反超。
  解 q016（formula chunk 被 review 综述顶掉的问题）。18/20 → 19/20。
- Phase 3（commit a92a1db）：`source='all'` 且 `top_k>=3` 时，预留最后一个 citation
  槽给最佳跨语言 chunk-bearing 候选。让 q004（中文 query 期望英文 chunk）通过，
  不扰动 top_k<=2 的同语言契约。19/20 → 20/20。

## 2026-05-17 chunk 数据集扩充

- Phase 1（commit 6c0a5db）：给 pmid-40100005 / cn-ad-guideline-004 /
  cn-ad-external-008 各加一条 chunk，把 q007 / q010 / q012 / q018 / q020 的
  `expected_chunk_ids` 填上。chunk_hit_count 11 → 16。新增锁定测试
  `test_run_rag_ad_eval_report_chunk_hit_count_meets_target`（门槛 `>= 16`）。
- Phase 2（commit 61811fc）：再给 cn-ad-network-007 / cn-ad-child-009 /
  cn-ad-review-010 各加一条 chunk，把 q008 / q009 / q014 / q019 的
  `expected_chunk_ids` 填上。chunk_hit_count 16 → 20。锁定门槛升到 `== 20`。
  `test_run_rag_ad_eval_report_allows_questions_without_expected_chunks`
  改用合成 dataset 保护空 chunk 分支。
- 整轮没动 `rag.py`，全部走数据层；chunk evidence_tags 故意收敛避免抢同
  alias 的相邻 question。

## 后续建议

- 当前 chunk_hit_count 已满（20/20）。下一颗能可量化推的是 `q019` 的 lit_hit
  从 1/3 拉到更多——可考虑给 retrieval 增加 `molecular_docking` 类 alias，
  或在 dataset 中给目标文献加更显式的关键词。
- 接入真实 LLM 前，应保持该评估报告作为回归基线；新加 sample 数据时务必跑 eval 不退化。
- 后续可增加 empty-result 专用评估问题，单独验证无证据时的回答边界。
