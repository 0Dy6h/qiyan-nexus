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

- 20 题中 15 题通过。
- 20 题有预期文献命中。
- 9 题有预期 chunk 命中。
- 20 题覆盖免责声明。
- 禁用语违规 0。

## 后续建议

- 优先改善未通过题目的必含词缺口，再考虑接真实 embedding。
- 接入真实 LLM 前，应保持该评估报告作为回归基线。
- 后续可增加 empty-result 专用评估问题，单独验证无证据时的回答边界。
