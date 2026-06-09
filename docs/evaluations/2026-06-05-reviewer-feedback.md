# Reviewer Feedback Packet — 2026-06-05

date: 2026-06-05  
status: ready-for-formal-review  
target reviewers: clinician + research reviewer  
environment profile: default offline preview (`deterministic` provider + `keyword` retrieval + open access)

---

## Technical Preflight

Preflight status: completed by engineering; formal clinician/research reviewer sign-off still pending.

| Field | Value |
|---|---|
| Branch | `feat/multilingual-bge-m3-backend` |
| Baseline commit | `c3c177d` |
| Current technical refresh base commit | `8bd38a6` |
| Verified worktree | Slice 0 repository hygiene and fact-source refresh for router.team/gpt-5.5 opt-in provider, network live opt-in status, frontend UI handoff, and TCMBench contact tracking |
| Backend URL | `http://127.0.0.1:8000` |
| Frontend URL | `http://127.0.0.1:3000` |
| Runtime profile | default offline preview |
| LLM provider | `deterministic` |
| Retrieval provider | `keyword` |
| State backend | `json` |
| Access control | open dev mode verified; shared-token profile also verified as internal preview gate |
| External data egress | none; no real LLM / embedding / PostgreSQL enabled |
| Runtime isolation | `.tmp/internal-preview-evidence/20260608-224628/runtime-open` and `.tmp/internal-preview-evidence/20260608-224628/runtime-token` |
| Evidence package | `.tmp/internal-preview-evidence/20260608-224628/evidence-summary.md` |

Preflight verification:

- 2026-06-08 Slice 0 technical refresh passed:
  - `.\scripts\verify-local.ps1` passed: backend `ruff format --check`, `ruff check`, `mypy app`, `pytest -q` (`562 passed, 1 skipped`); frontend `pnpm test` (`201 passed`), `pnpm typecheck`, `pnpm build`.
  - `.\scripts\verify-local.ps1 -IncludeE2E` passed: same backend/frontend gates plus Playwright open-mode E2E (`4 passed`).
  - `.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile` passed: same backend/frontend gates plus shared-token Playwright E2E (`4 passed`).
  - `.\scripts\collect-internal-preview-evidence.ps1` passed and created `.tmp/internal-preview-evidence/20260608-224628/`.
  - Note: Playwright Chromium headless shell was installed locally before the E2E rerun because the browser executable was missing from the machine cache; the rerun passed after installation.
- Evidence smoke summary:
  - open profile: passed, 12 flows, 12 request IDs.
  - shared-token profile: passed, 12 flows, 12 request IDs; access token value intentionally omitted.
  - Covered flows: health, literature all/PubMed/CNKI/uploaded-PDF filter, PDF upload + auto-parse, RAG answer/export, network analyze/result/report.
- Internal rehearsal already passed on the same default offline profile; see `docs/handoffs/2026-06-05-internal-reviewer-rehearsal.md`.
- Internal preview ops and evidence collector handoffs are current as of 2026-06-06; see `docs/handoffs/2026-06-06-afk-internal-trial-ops.md` and `docs/handoffs/2026-06-06-internal-preview-evidence-pack.md`.
- This packet must still be filled by a real clinician and a real research reviewer. Automated tests and internal rehearsal are not a substitute for domain sign-off.

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

## Engineering-discovered pre-review issue

#### Issue E-1

- `reviewer_role`: engineering pre-review
- `flow`: 文献检索与数据来源切换
- `severity`: P1
- `description`: `/literature` 默认结果包含 seed 演示文献，其中部分中文/英文标题、作者、PMID/DOI 与 `example.org` citation URL 不是外部数据库可检索的真实记录；原 UI 虽有 sample banner，但卡片层没有逐条标明记录来源，`PubMed 实时` 文案也容易让 reviewer 误以为 PubMed seed 样本都是实时真实记录。
- `steps_to_reproduce`: 访问 `/literature`，搜索 `特应性皮炎` 或切换 PubMed 视图，尝试用外部网站检索页面展示的 seed 标题。
- `expected`: 页面和 API 必须诚实区分演示 seed、PubMed 实时同步记录与本地上传 PDF 状态；演示 seed 不应被误读为可外部检索的真实文献。
- `actual`: 修复前卡片主要展示 `来源` / `期刊`，缺少逐条 `记录来源` 标识。
- `request_id`: n/a（工程侧静态数据/文案问题）
- `screenshot_note`: 修复后文献卡片与详情页 meta 行显示 `记录来源 演示样本` 或 `记录来源 PubMed 实时同步`；PubMed 视图 banner 改为 `PubMed 记录（含演示 seed）` 并明示 seed 不可当作外部可检索真实文献。
- `disposition`: fixed-before-formal-review
- `blocks_trial`: no after fix

## Reviewer A — Clinician

本节必须由真实临床 reviewer 填写。AI 技术预审、自动化测试、内部代走和彩排证据都不能替代本节。

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

本节必须由真实科研 reviewer 填写。AI 技术预审、自动化测试、内部代走和彩排证据都不能替代本节。

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

## AI Technical Pre-review Summary

本节记录 2026-06-06 AI 技术预审结论，用于正式 reviewer 走查前的工程参考；它不是正式医生/科研 reviewer sign-off。

报告位置：

- `docs/handoffs/2026-06-06-comprehensive-product-review.md`

预审结论：

- AI 技术预审未发现 P0/P1 问题。
- AI 技术预审建议可进入小范围试用准备，但仍需真实临床与科研 reviewer 现场走查后才能 close out。
- 预审发现的 P2 `网络药理学 mock 边界标注可增强` 已在本轮补强：`/network` 页面新增演示数据边界 note，后端 network Markdown 报告头部新增数据说明。
- 预审发现的 P3 `英文样本作者姓名可优化` 仍作为 backlog，不阻塞小范围试用准备。

## Consolidated Triage

| ID | Reviewer | Flow | Priority | Blocks Trial | Disposition |
|---|---|---|---|---|---|
| E-1 | engineering pre-review | 文献检索与数据来源切换 | P1 | no after fix | fixed-before-formal-review |
| E-2 | AI technical pre-review | 网络药理学 mock 边界标注 | P2 | no after fix | fixed-before-human-review |
| A-1 | clinician |  |  |  | pending-human-review |
| B-1 | research |  |  |  | pending-human-review |

## Closeout Decision

- [ ] No P0/P1 issues; proceed to small-scale internal trial.
- [ ] P0/P1 issues found; fix and repeat affected flow.
- [ ] Feedback requires scope change; write a new implementation plan before coding.

Decision notes:

待真实 clinician reviewer 与 research reviewer 完成本文件对应章节后填写。AI 技术预审、自动化测试、内部代走与证据包均不能替代此 closeout decision。
