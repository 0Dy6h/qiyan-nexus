# Reviewer 快速入门（5 分钟）

本页是正式医生 / 科研 reviewer 走查 Qiyan Nexus 的**单页入口**。先读这一页，再按需深入下方链接，不必从多份文档里自己拼流程。

## 你在审查什么

Qiyan Nexus 是面向**特应性皮炎（AD）医生与科研人员**的中医药证据整理工作台。你要判断的是：**这条「查证据 → 问证据 → 核对引用 → 导出材料」的核心工作流，是否可信、可追溯、边界清晰**。它不替代诊断，不面向 C 端患者。

## 启动（默认离线、不外发数据）

Windows PowerShell：

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
# 后端 http://127.0.0.1:8000，前端 http://127.0.0.1:3000
# 走查结束：.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop
```

默认配置：`deterministic` provider + `keyword` retrieval + open access + 隔离 runtime。**不启用真实 LLM、不连生产数据库、不向外部发送问题或证据。**

## 必走流程（建议 15–20 分钟）

1. **查证据** `/literature`：搜索「特应性皮炎」，切换四类来源（全部 / PubMed 记录 / CNKI 样本 / 上传 PDF），确认每条都标注了「记录来源」，演示样本是否被诚实标注。
2. **问证据** `/rag`：提一个 AD 问题（如「消风散对特应性皮炎皮肤屏障功能有什么影响？」），核对：答案是否基于检索到的**原文证据片段**、引用卡片能否点开溯源、免责声明是否在场。再提一个**无关问题**（如「高血压一线降压药」），确认系统**如实回答「未检索到匹配证据」而不是强行作答**。
3. **核对引用**：从引用卡片点进 `/literature/[id]` 或预览原文 PDF，确认 citation 可追溯。
4. **导出材料**：在 `/rag` 导出 Markdown 证据简报，确认它适合进入你的评审/记录。
5. **看机制线索** `/network`：提交「消风散」，确认页面明确标注这是 **mock 演示数据 / 非正式网络药理学结论**。

## 如何判定 + 在哪记录

按 P0/P1/P2/P3 分级记录问题，填写到正式反馈包：

- 反馈表（评分 + 问题记录）：[`docs/evaluations/2026-06-05-reviewer-feedback.md`](evaluations/2026-06-05-reviewer-feedback.md)
- 精简任务单（S1–S4）：[`docs/checklists/reviewer-walkthrough-task-card.md`](checklists/reviewer-walkthrough-task-card.md)
- 需要展开步骤时：[`docs/checklists/internal-preview-reviewer-walkthrough.md`](checklists/internal-preview-reviewer-walkthrough.md)

重点判断（反馈表已列）：产品定位清晰度、核心功能完整度、可信度/可追溯性、是否有任何 seed/mock/AI 边界让你误解、是否推荐进入小范围试用。

## 当前能力边界（评审前请知悉）

- **RAG 是本地确定性检索**，答案是检索到的原文证据片段，**不是模型综合生成的结论**；真实 LLM 为显式 opt-in，默认关闭。
- **文献库为小型构造演示样本集（约数十篇）**，不可当作外部可检索的真实文献；真实 PubMed 同步（`POST /api/literature/sync`）为 opt-in，写入 runtime，不污染样本。需要更大的真实语料时，运维可运行 `backend/scripts/seed_pubmed_corpus.py` 一键填充 runtime 语料。
- **网络药理学默认 mock**；live 模式需提前准备 TCMSP 缓存 / 靶点预测文件，**内部预览期间建议直接用 mock 模式**，不要为走查去开 live。
- **多人试用的 PDF 仍共享**：network task 已按 reviewer 隔离，但 PDF、解析结果、uploaded chunk 与 RAG citation 尚未对象级隔离；只能上传所有参与者均有权查看的材料。
- 分子对接 / 分子动力学（MVP-C）**仅 schema 预留，无功能**。

## 关键设计决策摘要（如被问起）

| 决策 | 一句话理由（面向 reviewer） | 详细 |
|---|---|---|
| 默认不接真实 LLM，走确定性检索 | 隐私/PIPL 合规 + 不给医生虚假信心，证据可追溯优先 | [ADR-0012](adr/0012-real-llm-enablement.md)、[ADR-0011](adr/0011-external-llm-data-flow-and-pipl.md) |
| 中英文证据来源透明 | AD 证据中英文并重，当前以 seed/runtime、PubMed 入口和来源标签便于核对 | [current-state](current-state.md) |
| 默认本地 JSON/SQLite，不上生产数据库 | 内部预览阶段够用，PostgreSQL/pgvector 为 opt-in spike | [ADR-0014](adr/0014-retrieval-provider-and-hybrid-search.md) |
| 网络药理学先 mock 后 live | 先验证产品路径，真实外部数据库链路按需 opt-in | [ADR-0010](adr/0010-research-workbench-module-roadmap.md) |
| 仅桌面端，不做移动适配 | 医生/科研工作台以桌面为主场景 | [ADR-0002](adr/0002-MVP仅桌面端不做移动端适配.md) |

> 自动化测试、内部代走与证据包都**不能替代**本页的真人 reviewer sign-off。事实源以代码与 [`docs/current-state.md`](current-state.md) 为准。
