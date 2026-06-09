# Small-scale Trial Feedback — 2026-06-06

date: 2026-06-06
status: template-ready
target users: 3-5 small-scale internal trial users
profile: default offline preview (`deterministic` provider + `keyword` retrieval + JSON runtime)

---

## Purpose

本文件用于记录真实用户小范围试用反馈。它承接技术预审与正式 reviewer packet，但不替代 `docs/evaluations/2026-06-05-reviewer-feedback.md` 中的 clinician / research reviewer sign-off。

本轮目标是验证真实用户是否能理解产品边界、完成核心流程，并指出临床语境、科研工作流和 mock 数据认知上的问题。

## Trial Boundary

默认包含：

- 文献检索与四数据源切换。
- 文献详情与 PDF 上传、自动解析、预览。
- RAG 问答、citation cards 与 Markdown 导出。
- 网络药理学 mock 分析、网络图、富集分析表格与 Markdown 导出。
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
| Runtime root |  |
| Access profile | open / shared-token |
| Evidence package |  |
| Verification before trial |  |

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

- [ ] 文献检索与四数据源切换
- [ ] 文献详情
- [ ] PDF 上传、自动解析与预览
- [ ] RAG 问答与 citation cards
- [ ] RAG Markdown 导出
- [ ] 网络药理学 mock 分析
- [ ] 网络图交互
- [ ] 富集分析表格
- [ ] 网络报告 Markdown 导出
- [ ] 合规说明页

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

- [ ] 文献检索与四数据源切换
- [ ] 文献详情
- [ ] PDF 上传、自动解析与预览
- [ ] RAG 问答与 citation cards
- [ ] RAG Markdown 导出
- [ ] 网络药理学 mock 分析
- [ ] 网络图交互
- [ ] 富集分析表格
- [ ] 网络报告 Markdown 导出
- [ ] 合规说明页

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

