# 内部预览证据包自动归档执行计划

date: 2026-06-06
status: proposed
scope: next local-development slice; no human reviewer dependency
profile: default offline preview (`deterministic` + `keyword` + isolated JSON runtime)

---

## Goal

在正式医生 / 科研 reviewer 暂不可用时，不继续横向扩张新基础设施，而是把已经完成的内部预览启动、smoke、token profile、E2E 能力固化为一个可重复生成的「内部预览证据包」。

目标产物是：一条 PowerShell 命令能在 isolated runtime 下生成本轮预览证据目录，包含 open/token 两种 profile 的 smoke 结果、request id、关键运行配置、日志路径、通过/失败汇总和一份 Markdown summary。它不替代真人 sign-off，只降低后续 reviewer 走查和小范围 trial 前的技术核对成本。

## Current Context

当前事实来自 `docs/current-state.md`、`README.md`、最近 handoff、当前脚本与测试源码，而不是历史 archive。

已完成并可信的进度：

- MVP-A 证据工作台已完成内部预览收尾。
- MVP-B 网络药理学 mock 链路已落地，包含 network analyze/result/report、网络图、键盘交互、mock GO/KEGG 富集和 Markdown 报告导出。
- 默认运行仍为本地离线 preview：`deterministic` provider、`keyword` retrieval、JSON runtime，不默认启用真实 LLM、真实 embedding、PostgreSQL、pgvector retrieval、OCR、商业 PDF 抽取器或生产认证。
- SQLite runtime backend 已作为 opt-in 可用；PostgreSQL/pgvector spike 已闭环，结论是不切默认。
- PDF 抽取质量 spike 已闭环，结论是不引入 `pdfplumber` 默认依赖、不切换 pypdf；OCR/表格重建仍是独立后续 spike。
- 正式 clinician/research reviewer sign-off 仍未完成，必须由真实 reviewer 填写 `docs/evaluations/2026-06-05-reviewer-feedback.md`，自动化或内部代走不能替代。
- 2026-06-06 已补齐 AFK internal-trial ops：
  - `scripts/run-internal-preview.ps1` 支持 isolated runtime 启停 open/token profile。
  - `scripts/smoke-internal-preview.ps1` 覆盖 health、文献四来源、PDF upload + auto-parse、RAG answer/export、network analyze/result/report，并输出 request id。
  - `scripts/verify-local.ps1 -IncludeE2E -E2ETokenProfile` 支持 token-gated Playwright E2E。
  - `frontend/tests/internal-preview-ops-source.test.ts` 已用源码断言锁定关键脚本约束。
- 当前 `git status --short --branch` 显示分支 `feat/multilingual-bge-m3-backend` 相对远端 ahead 1，无未提交工作树文件；最近本地提交为 `0d96cac docs(handoff): close 2026-06-05 session`。

最新开放项的分类：

- 需要人工：正式医生 + 科研 reviewer sign-off、P0/P1/P2/P3 人工反馈、是否进入小范围试用。
- 需要治理决策：L2 default preview 是否翻转、BGE=0.3 + NLI=0.5 profile 是否可作为默认预览配置、真实合同价格复核。
- 已闭环不应重复：PostgreSQL/pgvector spike、PDF extractor comparison、内部 reviewer rehearsal、token profile smoke。
- 当前可本地推进：把 internal preview 运行证据自动化归档，提升可追溯性和走查交接质量。

## Why This Slice

这个切片适合作为下一步，因为它满足四个约束：

- 不需要医生、科研 reviewer、API key、订阅、外部服务或生产数据库。
- 不改变默认产品边界，不把 mock/spike 推成生产路径。
- 直接强化目前最接近试用的路径：内部预览环境启动、smoke、token profile、request id 追踪。
- 产物对后续真人 sign-off 有帮助：reviewer 反馈回来后，可以快速定位每个 flow 对应的 request id、profile、日志和基线提交。

不推荐此时继续做的新方向：

- 不做 L2 默认翻转：这是治理决策，不是工程默认动作。
- 不做真实 LLM 追加采样：需要 key、预算和治理判断。
- 不做 PostgreSQL 生产化：spike 已判定当前不翻默认。
- 不做 OCR/表格重建：属于独立 PDF spike，且会扩大依赖面。
- 不做正式 reviewer 反馈填充：必须由真实 reviewer 完成。

## Proposed Approach

新增一个薄的 orchestration/reporting 层，而不是改业务 API：

1. 扩展或包裹 `scripts/smoke-internal-preview.ps1`，让 smoke 除了控制台表格，还能可选输出机器可读 JSON 和 Markdown。
2. 新增 `scripts/collect-internal-preview-evidence.ps1`，负责启动 isolated preview、分别运行 open/token smoke、收集结果、停止服务，并生成证据目录。
3. 增加源码级单测，锁定 evidence 脚本必须覆盖 open/token、request id、runtime/log paths、disclaimer、PDF/RAG/network 核心流程。
4. 更新 README/current-state/handoff 或 docs guide，只记录命令与边界，不宣称完成 formal sign-off。

建议的证据目录结构：

```text
.tmp/internal-preview-evidence/YYYYMMDD-HHmmss/
  evidence-summary.md
  metadata.json
  open-smoke.json
  open-smoke.md
  token-smoke.json
  token-smoke.md
  run.log
  backend-open.log
  frontend-open.log
  backend-token.log
  frontend-token.log
```

其中 `.tmp/` 已被 `.gitignore` 忽略，证据包默认作为本地 trial artifact，不提交仓库；提交仓库的只应是脚本、测试和文档。

## Step-by-Step Plan

### Step 0: Baseline Sanity Check

目的：确认开工前没有服务残留和意外工作树改动。

Commands:

```powershell
git status --short --branch
Get-Process | Where-Object { $_.ProcessName -match 'node|python|uvicorn' }
```

如发现已有 backend/frontend 预览进程，优先用已记录的 runtime root 停掉：

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -Stop
```

验收：

- 工作树只包含本切片计划内文件改动。
- 无占用 `8000` / `3000` 的旧预览服务，或已明确换端口运行。

### Step 1: Make Smoke Output Structured

目标：让 `scripts/smoke-internal-preview.ps1` 保持当前控制台输出，同时支持写出 JSON/Markdown artifact。

Likely file:

- `scripts/smoke-internal-preview.ps1`

Suggested parameters:

```powershell
[string]$OutputJson = ""
[string]$OutputMarkdown = ""
[string]$ProfileName = ""
```

Implementation notes:

- 保留现有默认行为：无参数时继续只打印表格和 `Internal preview smoke passed.`。
- 当前 `$results` 已经是结构化 list，可直接复用。
- JSON 输出建议包含：
  - `profile`
  - `backend_url`
  - `pdf_path`
  - `started_at`
  - `finished_at`
  - `passed`
  - `flows`
  - `request_ids`
  - `disclaimer`
  - `failure`（失败时写入 message）
- Markdown 输出建议包含：
  - profile
  - backend URL
  - runtime note
  - flow table
  - request id table
  - disclaimer assertion
  - failure details（如有）
- 如果某一步失败，优先在 `catch` 中写出失败 artifact，再 rethrow，让调用方仍能看到失败原因。
- 不改变 smoke 的业务断言，避免把报告化切片变成业务逻辑改造。

Edge cases:

- PowerShell `ConvertTo-Json` 对深层对象需要 `-Depth 10` 或更高。
- Markdown 输出要避免把 token 写进去；只记录 token profile enabled，不记录 token 原文。
- PDF 路径可以记录相对路径或文件名，避免把用户机器上的绝对隐私路径写入长期文档。

Acceptance:

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\evidence-open
.\scripts\smoke-internal-preview.ps1 `
  -ProfileName "open" `
  -OutputJson ".tmp\evidence-open\smoke.json" `
  -OutputMarkdown ".tmp\evidence-open\smoke.md"
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\evidence-open -Stop
```

Expected:

- smoke 仍通过。
- `.tmp\evidence-open\smoke.json` 存在，含 `passed=true` 和每个 flow 的 status/request id。
- `.tmp\evidence-open\smoke.md` 存在，含 flow table、免责声明断言和 request id。

### Step 2: Add Evidence Collector Script

目标：新增一个一键收集脚本，自动跑 open + token 两种 profile，并归档结果。

Likely file:

- `scripts/collect-internal-preview-evidence.ps1`

Suggested parameters:

```powershell
param(
    [string]$OutputRoot = ".tmp/internal-preview-evidence",
    [string]$AccessToken = "trial-token",
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "3000",
    [string]$PdfPath = "local-review-pdfs\健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf",
    [switch]$SkipTokenProfile,
    [switch]$KeepServicesOnFailure
)
```

Behavior:

1. Create timestamped output directory under `$OutputRoot`.
2. Write `metadata.json` with:
   - branch name
   - HEAD commit
   - dirty/clean status
   - current timestamp
   - backend/frontend URLs
   - provider/retrieval/state profile
   - whether token profile was run
3. Start open profile:
   - runtime root: `<evidence-dir>\runtime-open`
   - call `run-internal-preview.ps1`
   - wait until backend `/health` is reachable, with timeout.
4. Run open smoke:
   - call `smoke-internal-preview.ps1 -ProfileName open -OutputJson ... -OutputMarkdown ...`
5. Stop open profile.
6. Start token profile:
   - runtime root: `<evidence-dir>\runtime-token`
   - call `run-internal-preview.ps1 -AccessToken $AccessToken`
7. Run token smoke:
   - call `smoke-internal-preview.ps1 -AccessToken $AccessToken -ProfileName token -OutputJson ... -OutputMarkdown ...`
8. Stop token profile.
9. Copy or reference logs:
   - Either copy `backend.log` / `frontend.log` into stable names, or record their runtime paths in summary.
10. Generate `evidence-summary.md`:
   - overall result
   - commit/profile
   - open smoke status
   - token smoke status
   - request id list
   - artifact paths
   - explicit caveat: this is not formal reviewer sign-off.

Important implementation constraints:

- Always attempt cleanup in `finally`, unless `-KeepServicesOnFailure` is set.
- Do not print or write the token value to summary/logs.
- Keep all generated runtime artifacts under `.tmp/`.
- Do not invoke Playwright E2E from this collector by default; E2E remains heavier gate via `verify-local.ps1 -IncludeE2E`.
- Do not call external LLM/embedding services.

Acceptance:

```powershell
.\scripts\collect-internal-preview-evidence.ps1
```

Expected:

- Creates `.tmp/internal-preview-evidence/<timestamp>/`.
- Runs open smoke and token smoke successfully.
- Stops backend/frontend after completion.
- Produces `evidence-summary.md`, `metadata.json`, `open-smoke.json`, `token-smoke.json`.
- Summary includes request ids from RAG/network/report flows and states that formal sign-off remains pending.

### Step 3: Source-Level Tests For Evidence Ops

目标：按项目当前前端测试习惯，用 source tests 锁定 PowerShell 脚本关键契约，避免后续改坏。

Likely file:

- `frontend/tests/internal-preview-ops-source.test.ts`

Add tests or extend existing tests to assert:

- `collect-internal-preview-evidence.ps1` exists.
- It calls `run-internal-preview.ps1`.
- It calls `smoke-internal-preview.ps1`.
- It runs an open profile.
- It runs a token profile unless skipped.
- It writes `metadata.json`.
- It writes `evidence-summary.md`.
- It uses `.tmp/internal-preview-evidence`.
- It references request ids / `X-Request-ID`.
- It contains cleanup via `finally` or equivalent.
- It avoids writing `AccessToken` value directly into summary output.

Also extend the existing smoke-script test to assert:

- `OutputJson`
- `OutputMarkdown`
- `ProfileName`
- `ConvertTo-Json`
- Markdown flow table or summary writer

Focused validation:

```powershell
cd frontend
node --import tsx --test tests\internal-preview-ops-source.test.ts
```

Expected:

- All internal-preview ops source tests pass.

### Step 4: Documentation Update

目标：让后续 agent / 人类知道新证据包命令怎么用，以及它不能替代什么。

Likely files:

- `README.md`
- `docs/current-state.md`
- Optional: `docs/handoffs/2026-06-06-internal-preview-evidence-pack.md`
- Optional: `docs/checklists/internal-preview-reviewer-walkthrough.md`

Recommended doc changes:

In `README.md`, add a short command block near internal preview smoke:

```powershell
.\scripts\collect-internal-preview-evidence.ps1
```

Explain:

- default output root is `.tmp/internal-preview-evidence/<timestamp>/`
- it runs open + token profile smoke
- it produces `evidence-summary.md`
- it does not replace formal clinician/research reviewer sign-off

In `docs/current-state.md`, update Reviewer walkthrough bullet:

- AFK ops now can optionally generate a local evidence package.
- Formal reviewer sign-off still pending.

In handoff:

- Record what was implemented and exactly which commands passed.
- Keep boundaries explicit:
  - no real LLM
  - no production auth
  - no formal reviewer sign-off
  - no default backend/retrieval/provider changes

### Step 5: Verification

Run focused tests first:

```powershell
cd frontend
node --import tsx --test tests\internal-preview-ops-source.test.ts
```

Run functional evidence collection:

```powershell
cd ..
.\scripts\collect-internal-preview-evidence.ps1
```

Inspect generated summary:

```powershell
Get-ChildItem .tmp\internal-preview-evidence | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content .tmp\internal-preview-evidence\<timestamp>\evidence-summary.md
```

Run standard gate:

```powershell
.\scripts\verify-local.ps1
```

If this branch is being prepared for reviewer/trial closeout, additionally run:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

Expected:

- Focused source test passes.
- Evidence collector creates complete artifacts.
- Backend/frontend services are stopped after the collector exits.
- Standard gate passes.
- E2E open/token passes if included.

### Step 6: Commit Hygiene

Suggested commit split:

1. Script + tests:

```powershell
git add scripts\smoke-internal-preview.ps1 scripts\collect-internal-preview-evidence.ps1 frontend\tests\internal-preview-ops-source.test.ts
git commit -m "feat(review): collect internal preview evidence package"
```

2. Docs/handoff:

```powershell
git add README.md docs\current-state.md docs\handoffs\2026-06-06-internal-preview-evidence-pack.md
git commit -m "docs(review): document internal preview evidence package"
```

Before committing:

```powershell
git diff --check
git status --short
```

Do not commit:

- `.tmp/**`
- generated evidence artifacts
- runtime JSON state
- uploaded PDFs
- logs
- access token values

## Files Likely To Change

Primary:

- `scripts/smoke-internal-preview.ps1`
- `scripts/collect-internal-preview-evidence.ps1`
- `frontend/tests/internal-preview-ops-source.test.ts`
- `README.md`
- `docs/current-state.md`

Optional:

- `docs/handoffs/2026-06-06-internal-preview-evidence-pack.md`
- `docs/checklists/internal-preview-reviewer-walkthrough.md`

Files that should not change in this slice:

- `backend/app/services/rag.py` unless smoke reveals a real regression.
- `backend/app/main.py` unless request id middleware is broken.
- `backend/app/repositories/*` unless runtime smoke uncovers a blocker.
- `frontend/app/**` unless source tests reveal a mismatch with documented behavior.
- `docs/evaluations/2026-06-05-reviewer-feedback.md` because formal reviewer fields must remain human-filled.

## Validation Matrix

| Layer | Command | Required |
|---|---|---:|
| Source contract | `cd frontend; node --import tsx --test tests\internal-preview-ops-source.test.ts` | yes |
| Evidence functional smoke | `.\scripts\collect-internal-preview-evidence.ps1` | yes |
| Standard local gate | `.\scripts\verify-local.ps1` | yes |
| Open E2E | `.\scripts\verify-local.ps1 -IncludeE2E` | branch closeout |
| Token E2E | `.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile` | branch closeout / token profile changes |

## Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Collector leaves services running after failure | Port conflicts, confusing later tests | Use `try/finally`; default cleanup; only keep services with explicit `-KeepServicesOnFailure` |
| Token leaks into generated summary | Security/compliance issue | Never render token value; only write `token_profile=true` |
| Evidence artifact becomes mistaken for formal sign-off | Product governance confusion | Put explicit caveat in summary, README, current-state and handoff |
| Smoke reporting changes break existing behavior | Loss of stable AFK ops | Preserve default no-output behavior; add source tests |
| Full E2E inside collector makes it slow/flaky | Lower usability | Keep E2E as separate gate; collector covers API smoke only |
| Request ids missing from some responses | Traceability gap | Existing middleware should return `X-Request-ID`; smoke should record empty string as failure for key flows if traceability is required |

## Stop Conditions

Stop and record partial status if:

- `run-internal-preview.ps1` cannot reliably stop process trees.
- `smoke-internal-preview.ps1` fails in the existing open/token profile before reporting changes.
- Output JSON/Markdown requires exposing access tokens or local secrets.
- Functional smoke reveals a P0/P1 product regression unrelated to evidence collection.

Do not broaden scope into:

- production authentication
- user/role management
- external LLM calls
- PostgreSQL default switching
- pgvector retrieval productionization
- OCR or commercial PDF extraction
- formal reviewer verdict filling

## Open Questions

These can be deferred; no need to block the first implementation:

- Should evidence summaries be copied into `docs/evaluations/` after a human selects a specific run, or remain local `.tmp` only?
- Should the collector support custom backend/frontend ports in addition to default `8000` / `3000`?
- Should failed smoke artifacts include a trimmed tail of backend/frontend logs, or only log paths?
- Should request id presence be mandatory for every flow, or only RAG/network/export flows?

## Recommended Next Action

Implement Step 1 through Step 3 as one vertical slice:

1. Add structured smoke outputs.
2. Add collector script.
3. Add source tests.
4. Run focused test and one full collector smoke.

Only after that update README/current-state/handoff and run the full local gate.

