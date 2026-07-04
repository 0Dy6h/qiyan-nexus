# Small-scale Trial Feedback — 2026-06-06

date: 2026-06-06
status: template-ready
target users: 3-5 small-scale internal trial users
profile: default offline preview (`deterministic` provider + `keyword` retrieval + JSON runtime)

---

## Purpose

本文件用于记录真实用户小范围试用反馈。它承接技术预审与正式 reviewer packet，但不替代 `docs/evaluations/2026-06-05-reviewer-feedback.md` 中的 clinician / research reviewer sign-off。

本轮目标是验证真实用户是否能理解产品边界、完成核心流程，并指出临床语境、科研工作流和 mock 数据认知上的问题。

本轮核心产品假设：

> 真实医生 / 科研用户愿意用 Qiyan Nexus 完成一次 AD 中医药证据整理任务，并认可其证据可追溯性。

配套执行计划见 `docs/plans/2026-06-18-core-evidence-workflow-validation.md`。正式展开 S1-S4 前，先跑 `docs/checklists/reviewer-walkthrough-task-card.md` 中的 10-15 分钟“核心证据整理任务”。

## Trial Boundary

默认包含：

- 10-15 分钟核心证据整理任务：文献或 PDF → RAG 提问 → citation 追溯 → Markdown 导出。
- S1 文献四来源检索。
- S2 PDF 上传 → 解析 → RAG 引用。
- S3 RAG 答案 + 免责声明。
- S4 网络药理学 mock 边界。
- 合规说明页与免责声明核对。

默认不包含：

- 真实 LLM。
- 真实 embedding 模型。
- PostgreSQL / pgvector 默认运行。
- 真实 TCMSP / STRING / KEGG API。
- OCR、表格重建或商业 PDF 抽取器。
- 生产认证、RBAC、审计或正式部署。

所有 AI/RAG/network 输出仍必须出现：

非诊断结论、需结合临床。

## Environment

| Field | Value |
|---|---|
| Frontend URL | `http://127.0.0.1:3000` |
| Backend URL | `http://127.0.0.1:8000` |
| Runtime root | `.tmp\core-evidence-trial` |
| Access profile | open |
| Evidence package | `.tmp\core-evidence-trial\smoke.md` and `.tmp\core-evidence-trial\smoke.json` |
| Verification before trial | 2026-06-18 smoke passed: 12 flows covered health, literature four-source checks, PDF upload + auto-parse, RAG answer/export, and network analyze/result/report |

Recommended pre-trial commands:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
.\scripts\collect-internal-preview-evidence.ps1
```

## Severity Rules

| Priority | Definition | Action |
|---|---|---|
| P0 | 合规、医学安全或核心流程不可用，阻塞继续试用 | 立即暂停相关流程，修复并复测 |
| P1 | 核心试用流程明显受损，扩大试用前必须修 | 本轮修复，复测相关流程 |
| P2 | 影响体验、可信度或理解成本，但不阻塞小范围试用 | 下一 sprint 处理 |
| P3 | 优化建议、新功能愿望或样本质量建议 | Backlog |

## Success Metrics

第一批 3-5 位真实用户的判定标准：

- 至少 80% 能在无工程介入下完成核心证据整理任务。
- 0 位用户把 seed / mock 数据误认为外部真实数据库结论。
- 0 个 P0，且无未解决 P1。
- 至少 2 位用户回答“愿意继续用它整理 AD 中医药证据”。
- 至少 2 位用户给“引用/证据可追溯性”打 4 分或 5 分。
- 每份 RAG Markdown 导出都包含完整免责声明字节串：`非诊断结论、需结合临床。`

## Participant Log

### Participant 1

- 姓名/代号：
- 角色：clinician / TCM researcher / methodology expert / other
- 专业背景：
- 浏览器/设备：
- 试用日期：
- 试用时长：
- 是否全程使用默认离线 profile：yes / no

#### Completed Flows

- [ ] 核心证据整理任务：文献或 PDF → RAG 提问 → citation 追溯 → Markdown 导出
- [ ] S1 文献四来源检索
- [ ] S2 PDF 上传 → 解析 → RAG 引用
- [ ] S3 RAG 答案 + 免责声明
- [ ] S4 网络药理学 mock 边界
- [ ] 合规说明页与免责声明核对

#### Ratings

| Dimension | 1-5 | Notes |
|---|---:|---|
| 产品定位清晰度 |  |  |
| 数据来源透明度 |  |  |
| 术语准确性 |  |  |
| 引用/证据可追溯性 |  |  |
| 操作流畅度 |  |  |
| mock 边界理解度 |  |  |
| 是否愿意继续试用 |  |  |

#### Key Feedback

- 是否愿意再次用它整理 AD 中医药证据：
- citation 是否足够可追溯，让你愿意把它当作科研/临床参考辅助：
- 最有价值的功能：
- 最困惑的地方：
- 是否误以为 seed/mock 数据是真实外部数据库结果：
- 是否认为免责声明和边界提示足够清楚：
- 临床语境或科研工作流不匹配之处：
- 其他建议：

#### Issues

##### Issue P1-1

- `reviewer_role`:
- `flow`:
- `severity`: P0 / P1 / P2 / P3
- `description`:
- `steps_to_reproduce`:
- `expected`:
- `actual`:
- `request_id`:
- `screenshot_note`:
- `disposition`:
- `blocks_next_trial`: yes / no

### Participant 2

- 姓名/代号：
- 角色：clinician / TCM researcher / methodology expert / other
- 专业背景：
- 浏览器/设备：
- 试用日期：
- 试用时长：
- 是否全程使用默认离线 profile：yes / no

#### Completed Flows

- [ ] 核心证据整理任务：文献或 PDF → RAG 提问 → citation 追溯 → Markdown 导出
- [ ] S1 文献四来源检索
- [ ] S2 PDF 上传 → 解析 → RAG 引用
- [ ] S3 RAG 答案 + 免责声明
- [ ] S4 网络药理学 mock 边界
- [ ] 合规说明页与免责声明核对

#### Ratings

| Dimension | 1-5 | Notes |
|---|---:|---|
| 产品定位清晰度 |  |  |
| 数据来源透明度 |  |  |
| 术语准确性 |  |  |
| 引用/证据可追溯性 |  |  |
| 操作流畅度 |  |  |
| mock 边界理解度 |  |  |
| 是否愿意继续试用 |  |  |

#### Key Feedback

- 是否愿意再次用它整理 AD 中医药证据：
- citation 是否足够可追溯，让你愿意把它当作科研/临床参考辅助：
- 最有价值的功能：
- 最困惑的地方：
- 是否误以为 seed/mock 数据是真实外部数据库结果：
- 是否认为免责声明和边界提示足够清楚：
- 临床语境或科研工作流不匹配之处：
- 其他建议：

#### Issues

##### Issue P2-1

- `reviewer_role`:
- `flow`:
- `severity`: P0 / P1 / P2 / P3
- `description`:
- `steps_to_reproduce`:
- `expected`:
- `actual`:
- `request_id`:
- `screenshot_note`:
- `disposition`:
- `blocks_next_trial`: yes / no

## Consolidated Trial Triage

| ID | Participant | Role | Flow | Priority | Blocks Next Trial | Disposition |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Trial Closeout

- [ ] No P0/P1 issues; proceed to broader internal trial.
- [ ] P0/P1 issues found; fix and repeat affected flows.
- [ ] Feedback requires scope change; write a new implementation plan before coding.

Decision notes:

-

