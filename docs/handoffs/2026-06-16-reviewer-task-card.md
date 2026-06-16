# Reviewer Task Card Handoff

## Goal

为 Qiyan Nexus 正式医生 + 科研 reviewer sign-off 产出一份统一、锚定、精简的走查任务单，降低真人 reviewer 启动成本。已完成任务单、新旧文档场景命名对齐、自动化覆盖审计和 isolated runtime smoke 对账。

## Current state

- 新增 `docs/checklists/reviewer-walkthrough-task-card.md`，作为 30-45 分钟执行卡；详细步骤继续引用 `docs/checklists/internal-preview-reviewer-walkthrough.md`。
- 四场景统一命名为：
  - S1 文献四来源检索
  - S2 PDF 上传 → 解析 → RAG 引用
  - S3 RAG 答案 + 免责声明
  - S4 网络药理学 mock 边界
- `docs/checklists/internal-preview-reviewer-walkthrough.md` 只改四个核心标题与问题模板字段；未复制或重构 335 行手册。
- `docs/evaluations/2026-06-05-reviewer-feedback.md` 的使用说明、必走流程、triage flow 已指向 S1-S4 和新任务单。
- `docs/evaluations/2026-06-06-small-scale-trial-feedback.md` 的默认包含项与 participant completed flows 已收拢到 S1-S4。
- 本任务未改 `backend/app`、`backend/tests`、`frontend/app`、`frontend/components`、`frontend/lib`，未改 smoke 脚本或测试行为。

## Completed in this session

### Gap 1: 三份文档命名/粒度不一致

- 统一了 walkthrough、formal reviewer packet、small-scale trial template 与新任务单中的四场景名称。
- 保留旧文档主体结构，只在标题、checklist 标签、triage flow 和使用说明层面轻量对齐。

### Gap 2: 客观锚与主观点未分离

在任务单中新增“自动化覆盖对照表”，按场景区分：

| 场景 | 自动化客观锚 | 人工主观点 |
|---|---|---|
| S1 文献四来源检索 | smoke `literature_all` / `literature_pubmed` / `literature_cnki` / `literature_uploaded_filter`；pytest `test_literature_search.py`；Playwright `literature-data-source.spec.ts`。 | seed / sample / uploaded PDF 边界是否真的被理解；检索结果是否有用；TCM / AD 术语是否准确。 |
| S2 PDF 上传 → 解析 → RAG 引用 | smoke `pdf_upload` / `pdf_auto_parse`；pytest `test_upload_api.py`、`test_rag_service.py`；frontend `rag-uploaded-pdf-citation.test.ts`；Playwright `internal-preview.spec.ts`。 | 抽取文本、数字表格乱码、上传 PDF citation 来源标记、失败/placeholder 回退是否影响信任。 |
| S3 RAG 答案 + 免责声明 | smoke `rag_answer` / `rag_export`；pytest `test_rag_api.py`、`test_rag_literature_contract.py`；Playwright `main-path.spec.ts`。 | 答案医学准确性、疗效承诺边界、免责声明显著性、引用是否真实支撑论断。 |
| S4 网络药理学 mock 边界 | smoke `network_analyze` / `network_result` / `network_report`；pytest `test_network_api.py`、`test_network_enrichment_integration.py`、`test_network_report_service.py`；Playwright `internal-preview.spec.ts`、`network-graph-keyboard.spec.ts`。 | mock 是否被理解为非真实科研结果；p-value 是否会被误读；作用链证据与边界说明是否可信。 |

### Gap 3: 缺一份 30-45 分钟任务单

- 新任务单顶部固定运行 profile、免责声明字节串、主 PDF 样本、smoke 命令、request_id 获取方式。
- 每个 S1-S4 场景使用统一模板：目标、操作路径、已自动验证、只看专业判断、在哪记录。
- 明确声明自动化锚、内部代走、AI 技术预审和证据包都不能替代人工 sign-off。

## Audit notes

- smoke 里的 `literature_uploaded_filter` 当前在上传前执行，本次结果 `total=0`。因此它只能证明 `has_pdf_upload=true` filter endpoint 返回 200 和 `items` 字段，不证明本轮上传后列表非空。
- smoke 当前没有断言“本次上传 PDF 必定进入后续 RAG citation”。已有 pytest 覆盖 uploaded PDF citation metadata，前端测试覆盖 badge / preview link，但正式 reviewer 仍需人工看 S2 中 citation 来源是否清楚；未来可补 smoke 断言。
- S4 的 `data_mode=mock`、`chains > 0`、`enrichment.terms > 0` 和 report disclaimer 均由 smoke 实跑验证；但 p-value 是否会被误读为真实统计只能由科研 reviewer 判断。
- 所有 AI/RAG/network 输出仍以 `非诊断结论、需结合临床。` 为 load-bearing 字节串；本任务未改该字符串。

## Smoke dry-run evidence

Commands run with PowerShell 7 (`pwsh`):

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\reviewer-card-open
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-internal-preview.ps1 -OutputJson .tmp\reviewer-card-open\smoke.json -OutputMarkdown .tmp\reviewer-card-open\smoke.md
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\reviewer-card-open -Stop
```

Result: passed, open profile, deterministic + keyword + isolated runtime.

| Flow | Status | Request ID | Notes |
|---|---:|---|---|
| health | 200 | `0f395905-db3a-49bb-afe2-478f6913ba08` | status=ok |
| literature_all | 200 | `39e909fb-01a3-4fb7-9801-b2fa633faceb` | total=20 |
| literature_pubmed | 200 | `35e5c02c-60fc-484c-b905-bb2b2cdbfe4e` | total=10 |
| literature_cnki | 200 | `c5ebc9c8-33e4-42eb-a31d-824ae740a3d6` | total=10 |
| literature_uploaded_filter | 200 | `77c747be-6871-4a44-93f4-2a64cca36bd7` | total=0 |
| pdf_upload | 201 | `7ce6a2c8-66cc-4b27-8059-fb55702d6aa6` | upload_id=pdf-cn-ad-barrier-006-pdf-2c576156 |
| pdf_auto_parse | 200 | `55a73179-882f-4d50-baad-65a3ea41b0d1` | method=pypdf-text-preview |
| rag_answer | 200 | `433650bd-8da9-4ed6-bd45-e7749d14f2dd` | citations=2 |
| rag_export | 200 | `e789661d-7def-46a7-b411-67139a6e163d` | markdown=ok |
| network_analyze | 202 | `ce05812e-fd2f-4644-8616-1b3ba2602b2a` | task=network-35cebf01d163 |
| network_result | 200 | `e5fdcc65-d8ad-40a4-a3e3-5477ca51a4f1` | mode=mock; chains=5; enrichment=14 |
| network_report | 200 | `fc2e556a-8db5-4efc-b8b2-36a8f68b0a1b` | markdown=ok |

Smoke artifact files were generated under `.tmp\reviewer-card-open\smoke.json` and `.tmp\reviewer-card-open\smoke.md`; they are local evidence artifacts and are not intended to be committed.

## Still open / blocked

- Formal sign-off itself remains open. This session only reduced reviewer startup cost; it did not perform clinician / research reviewer judgment.
- Suggested future hardening: extend `scripts/smoke-internal-preview.ps1` to assert uploaded PDF citation appears in a post-upload RAG answer, if the team wants that objective anchor. This was intentionally not changed in this task.
- Suggested future hardening: add a smoke or e2e assertion around the exact S4 mock boundary copy if reviewer confusion persists. Current tests already cover mock boundary page/report copy at unit/source level.

## Key files and artifacts

- `docs/checklists/reviewer-walkthrough-task-card.md`
- `docs/checklists/internal-preview-reviewer-walkthrough.md`
- `docs/evaluations/2026-06-05-reviewer-feedback.md`
- `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`
- `docs/handoffs/2026-06-16-reviewer-task-card.md`
- `.tmp\reviewer-card-open\smoke.md` and `.tmp\reviewer-card-open\smoke.json` local smoke evidence, not committed.

## Verification

- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\reviewer-card-open` — passed.
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-internal-preview.ps1 -OutputJson .tmp\reviewer-card-open\smoke.json -OutputMarkdown .tmp\reviewer-card-open\smoke.md` — passed, 12 flows with request IDs.
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\reviewer-card-open -Stop` — passed.
- Full `verify-local.ps1` was not rerun because this was docs-only, smoke-script-only-read validation and no app/test behavior changed.

## Recommended next step

Give `docs/checklists/reviewer-walkthrough-task-card.md` plus `docs/evaluations/2026-06-05-reviewer-feedback.md` to the real clinician and research reviewer, then triage any P0/P1 before small-scale trial expansion.

## Recommended reading order

1. `docs/checklists/reviewer-walkthrough-task-card.md`
2. `docs/evaluations/2026-06-05-reviewer-feedback.md`
3. `docs/checklists/internal-preview-reviewer-walkthrough.md` only when a reviewer needs detailed steps
4. This handoff for automation evidence and known gaps

## Recommended skill / toolset

- `session-handoff` for continuation notes.
- Terminal + Git for rerunning smoke and preparing PR updates.
