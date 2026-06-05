# Reviewer Feedback Packet — 2026-06-05

date: 2026-06-05  
status: ready-for-formal-review  
target reviewers: clinician + research reviewer  
environment profile: default offline preview (`deterministic` provider + `keyword` retrieval + open access)

---

## 使用说明

本文件用于正式医生/科研 reviewer 走查记录。请按 `docs/checklists/internal-preview-reviewer-walkthrough.md` 完成流程，并把每个问题按 P0/P1/P2/P3 分级。

本轮默认不启用真实 LLM，不向外部 provider 发送问题或证据片段。所有 AI/RAG 输出仍必须出现：

非诊断结论、需结合临床。

主 PDF 样本：

`local-review-pdfs/健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf`

可选质量警告样本：

`local-review-pdfs/中医辨证治疗异位性皮炎临床观察_周海啸.pdf`

## 问题分级

| Priority | Definition | Action |
|---|---|---|
| P0 | 合规、医学安全或核心流程不可用，阻塞 sign-off | 立即修复，复测同一流程 |
| P1 | 核心 reviewer 流程明显受损，正式试用前必须修 | 本轮修复，复测相关流程 |
| P2 | 影响体验或可信度，但不阻塞试用判断 | 进入下一 sprint |
| P3 | 优化建议或新功能愿望 | 进入 backlog |

## Reviewer A — Clinician

- 姓名：
- 职称/角色：
- 专业领域：
- 浏览器/环境：
- 评审日期：
- 评审耗时：

### 必走流程

- [ ] 文献检索与详情页
- [ ] RAG 问答与引用核对
- [ ] PDF 上传、自动解析与预览
- [ ] 合规说明页

### 评分

| 维度 | 1-5 分 | Notes |
|---|---:|---|
| 产品定位清晰度 |  |  |
| 核心功能完整度 |  |  |
| 用户体验流畅度 |  |  |
| 医学专业性 |  |  |
| 合规意识 |  |  |

### 是否推荐进入小范围试用

- [ ] 推荐进入小范围试用
- [ ] 建议修复关键问题后再试用
- [ ] 不推荐

### 问题记录

#### Issue A-1

- `reviewer_role`: clinician
- `flow`:
- `severity`: P0 / P1 / P2 / P3
- `description`:
- `steps_to_reproduce`:
- `expected`:
- `actual`:
- `request_id`:
- `screenshot_note`:
- `disposition`:
- `blocks_trial`: yes / no

## Reviewer B — Research

- 姓名：
- 职称/角色：
- 专业领域：
- 浏览器/环境：
- 评审日期：
- 评审耗时：

### 必走流程

- [ ] 文献检索与数据来源切换
- [ ] RAG citation cards 与 Markdown 导出
- [ ] 网络药理学链路、网络图与富集分析
- [ ] 网络分析 Markdown 报告导出

### 评分

| 维度 | 1-5 分 | Notes |
|---|---:|---|
| 产品定位清晰度 |  |  |
| 核心功能完整度 |  |  |
| 用户体验流畅度 |  |  |
| 科研工作流可用性 |  |  |
| 数据/证据可追溯性 |  |  |

### 是否推荐进入小范围试用

- [ ] 推荐进入小范围试用
- [ ] 建议修复关键问题后再试用
- [ ] 不推荐

### 问题记录

#### Issue B-1

- `reviewer_role`: research
- `flow`:
- `severity`: P0 / P1 / P2 / P3
- `description`:
- `steps_to_reproduce`:
- `expected`:
- `actual`:
- `request_id`:
- `screenshot_note`:
- `disposition`:
- `blocks_trial`: yes / no

## Consolidated Triage

| ID | Reviewer | Flow | Priority | Blocks Trial | Disposition |
|---|---|---|---|---|---|
| A-1 | clinician |  |  |  |  |
| B-1 | research |  |  |  |  |

## Closeout Decision

- [ ] No P0/P1 issues; proceed to small-scale internal trial.
- [ ] P0/P1 issues found; fix and repeat affected flow.
- [ ] Feedback requires scope change; write a new implementation plan before coding.

Decision notes:

