# UX 循环 2026-09-04：三轮「试用体验 → 问题清单 → 整改方案 → 优化整改」

## 背景

延续 `docs/reports/2026-09-03-ux-review-cycles.md`（工具链 / 全流程 / 负路径三轮已收口）。
本轮三轮走查向下探一层，避开已覆盖面与遗留决策项（`/network` omics UI 入口、CORS 多端口、IL6/STAT3/TNF 真实数据）。

## 环境

- isolated preview：backend 8010 / frontend 3000（`run-internal-preview.ps1 -RuntimeRoot .tmp/ux-loop-0904`）
- 走查层：
  - 第 1 轮：前端 UI 全页面（浏览器实际操作：首页 / network 建任务与结果 / 判定 / tasks / literature 搜索与详情 / rag 深链与问答 / compliance）
  - 第 2 轮：待定（走查后填）
  - 第 3 轮：待定（走查后填）

## 本轮不做（记录在案）

- RAG 回答模板句在问题实体（如 IL6）无命中时仍称「检索到相关证据片段」——属检索质量域，牵动 eval 基线（AGENTS.md 检索排序约束），不在 UX 循环内改，转人工评估。
- 报告导出文件名中的 UTC 时间戳是机器标识，非墙钟展示，不改。
- 真人 reviewer / omics UI / CORS——产品决策项，维持上轮结论。
