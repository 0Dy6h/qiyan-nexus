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
- 11 题有预期 chunk 命中。
- 20 题覆盖免责声明。
- 禁用语违规 0。
- `tests/test_eval_service.py::test_run_rag_ad_eval_report_meets_baseline_pass_rate`
  作为回归门，硬 lock `passed_questions == 20`。

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

## 后续建议

- 当前样本 chunks 仅 6 条，仍不足以覆盖所有文献。补 chunk 是提升 chunk_hit_count
  （目前 11/20）的下一颗自然 slice。
- 接入真实 LLM 前，应保持该评估报告作为回归基线；新加 sample 数据时务必跑 eval 不退化。
- 后续可增加 empty-result 专用评估问题，单独验证无证据时的回答边界。
