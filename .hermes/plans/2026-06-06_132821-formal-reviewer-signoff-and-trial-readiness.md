# 正式 reviewer sign-off 与小范围内部试用准备执行计划

date: 2026-06-06 13:28  
status: proposed  
scope: formal reviewer walkthrough, P0/P1 feedback closeout, internal trial readiness  
profile: default offline preview (`deterministic` provider + `keyword` retrieval + JSON runtime)

---

## Goal

把当前已经技术收口的 Qiyan Nexus 内部预览版推进到下一道真实产品关口：

1. 让医生 reviewer 与科研 reviewer 完成正式人工走查。
2. 把 reviewer 反馈按 P0/P1/P2/P3 分级并沉淀到事实源文档。
3. 若出现 P0/P1，只修阻塞项并按受影响流程复测。
4. 若无 P0/P1，更新项目状态为“formal reviewer sign-off complete”，进入小范围内部试用准备。

本计划不改变默认技术路线：不默认启用真实 LLM、真实 embedding、PostgreSQL、pgvector、OCR、生产认证或外部服务。

## Current Context

基于本轮只读盘点，当前真实进度如下：

- 当前分支：`feat/multilingual-bge-m3-backend`
- 最新提交：`a723472 feat(review): collect internal preview evidence pack`
- `git status --short`：干净工作树
- MVP-A 证据工作台：已完成内部预览收尾
- MVP-B 网络药理学：mock 起步链路已落地，含 mock GO/KEGG enrichment、网络图、键盘交互与 Markdown 报告导出
- 内部预览技术证据：已完成 open profile 与 shared-token profile 的启动、smoke、E2E、证据包采集链路
- 最新技术验证记录：
  - `docs/handoffs/2026-06-06-afk-internal-trial-ops.md` 记录 `.\scripts\verify-local.ps1`、open E2E、token E2E 已通过
  - `docs/handoffs/2026-06-06-internal-preview-evidence-pack.md` 记录 evidence collector 已跑通，open/token smoke 均 passed
- 正式 reviewer packet：`docs/evaluations/2026-06-05-reviewer-feedback.md` 已 ready，但医生与科研 reviewer 信息、评分、问题与最终决策仍为空
- PostgreSQL/pgvector spike：已完成，结论是不翻默认；SQLite 继续作为可选本地持久化推荐，PostgreSQL 保持 explicit opt-in
- PDF 抽取质量 spike：已完成，结论是不引入 `pdfplumber` 默认依赖；保留 `pypdf` + `quality_warning` 路径，OCR/商业抽取器另开独立 spike

## Assumptions

- 正式评审以默认离线 profile 为准：`deterministic` provider、`keyword` retrieval、JSON runtime、无外部 LLM/embedding egress。
- shared-token profile 可以作为技术补充验证，但不等于生产认证，不应作为正式权限系统承诺。
- `docs/evaluations/2026-06-05-reviewer-feedback.md` 是本轮 reviewer 反馈唯一填写入口。
- 自动化测试、内部代走、证据包都不能替代医生/科研 reviewer 的人工 sign-off。
- 如果 reviewer 发现医学安全、合规或核心流程问题，优先级高于任何新功能。

## Proposed Approach

采用“正式人工评审优先，工程修复最小化”的策略。

先用现有脚本启动隔离 preview 环境并刷新一次技术证据，再让两类 reviewer 按同一清单完成核心流程。评审后只把 P0/P1 作为当前开发必修内容；P2/P3 进入后续 sprint/backlog。若无 P0/P1，则不再继续扩功能，直接做状态文档 closeout 和小范围内部试用准备。

## Execution Plan

### Phase 0: Pre-review Technical Refresh

Objective: 在正式 reviewer 打开浏览器前，确认本地内部预览环境仍可重复启动，并生成一份新的技术证据包。

Steps:

1. 运行标准门禁。

   ```powershell
   .\scripts\verify-local.ps1
   ```

2. 在 reviewer 走查前追加 open-mode E2E。

   ```powershell
   .\scripts\verify-local.ps1 -IncludeE2E
   ```

3. 如本轮想验证 shared-token profile，再追加 token-mode E2E。

   ```powershell
   .\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
   ```

4. 生成正式评审前证据包。

   ```powershell
   .\scripts\collect-internal-preview-evidence.ps1
   ```

5. 把证据包路径、运行时间、open/token smoke 结果摘要填入 `docs/evaluations/2026-06-05-reviewer-feedback.md` 的 Technical Preflight 区域。不要提交 `.tmp/internal-preview-evidence/*` 原始证据目录。

Expected outcome:

- reviewer 之前的环境状态可追溯。
- 如果门禁或 smoke 失败，先修环境/阻塞问题，不进入人工评审。

### Phase 1: Run Formal Clinician Walkthrough

Objective: 医生 reviewer 从医学安全、临床边界、引用可信度和合规表达角度完成走查。

Primary files:

- `docs/checklists/internal-preview-reviewer-walkthrough.md`
- `docs/evaluations/2026-06-05-reviewer-feedback.md`

Required flows:

1. 文献检索与详情页。
2. RAG 问答与 citation cards 核对。
3. PDF 上传、自动解析、预览与质量警告理解。
4. 合规说明页与免责声明检查。

Data/profile:

- 主 PDF 样本：`local-review-pdfs/健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf`
- 可选 warning 样本：`local-review-pdfs/中医辨证治疗异位性皮炎临床观察_周海啸.pdf`
- 必须确认所有 AI/RAG 输出包含：`非诊断结论、需结合临床。`

Capture:

- Reviewer A 基本信息、评分、是否推荐进入小范围试用。
- 每个问题记录 flow、severity、steps、expected、actual、request_id、screenshot note、是否 blocks trial。

### Phase 2: Run Formal Research Walkthrough

Objective: 科研 reviewer 从科研工作流、证据可追溯性、数据来源透明度和网络药理学 mock 表达边界角度完成走查。

Primary files:

- `docs/checklists/internal-preview-reviewer-walkthrough.md`
- `docs/evaluations/2026-06-05-reviewer-feedback.md`

Required flows:

1. 文献检索与数据来源切换。
2. RAG citation cards 与 Markdown 导出。
3. 网络药理学链路、网络图、键盘交互与富集分析。
4. 网络分析 Markdown 报告导出。

Boundaries to make explicit during review:

- 当前 network enrichment 是 mock/sample 数据链路，不是科研级 TCMSP/STRING/KEGG REST 或真实 FDR 校正。
- 当前 RAG 默认 deterministic，不代表真实 LLM 默认可用。
- 上传 PDF preview 是文本抽取预览，不是 OCR 或表格重建。

Capture:

- Reviewer B 基本信息、评分、是否推荐进入小范围试用。
- 每个问题记录 flow、severity、steps、expected、actual、request_id、screenshot note、是否 blocks trial。

### Phase 3: Consolidated Triage

Objective: 把医生和科研 reviewer 的反馈转成工程可执行队列。

Steps:

1. 在 `docs/evaluations/2026-06-05-reviewer-feedback.md` 的 `Consolidated Triage` 表格中汇总所有 issue。
2. 对每个 issue 使用现有分级：
   - P0：合规、医学安全或核心流程不可用，阻塞 sign-off
   - P1：核心 reviewer 流程明显受损，正式试用前必须修
   - P2：影响体验或可信度，但不阻塞试用判断
   - P3：优化建议或新功能愿望
3. 判断是否进入开发修复：
   - 有 P0/P1：进入 Phase 4，只修阻塞项
   - 无 P0/P1：跳过 Phase 4，进入 Phase 5 closeout
4. 对 P2/P3 只记录，不在当前 closeout 中顺手扩 scope。

Suggested issue disposition values:

- `fix-now`
- `document-boundary`
- `next-sprint`
- `backlog`
- `not-reproducible`
- `accepted-risk`

### Phase 4: P0/P1 Fix Loop

Objective: 对正式 sign-off 阻塞项做最小可验证修复。

Rules:

- 先写或更新失败测试，再实现修复。
- 一次只修一个 P0/P1 flow，避免把 reviewer closeout 扩成新功能 sprint。
- 修复后只先跑受影响的 focused tests，再跑标准门禁。
- 不改 `services/rag.py` 的免责声明字符串。
- 不把 runtime state、上传 PDF、`.tmp` 证据包或本地 secret 提交。

Likely files by affected area:

Literature/search/data-source issues:

- `backend/app/api/literature.py`
- `backend/app/services/literature.py`
- `backend/app/repositories/literature.py`
- `backend/app/schemas/literature.py`
- `backend/tests/test_literature_search.py`
- `backend/tests/test_literature_detail.py`
- `frontend/components/LiteratureSearchClient.tsx`
- `frontend/components/LiteratureDataSourceBanner.tsx`
- `frontend/lib/api/literature.ts`
- `frontend/tests/literature-api.test.ts`
- `frontend/tests/literature-data-source-switcher.test.ts`
- `frontend/e2e/literature-data-source.spec.ts`

PDF upload/parse issues:

- `backend/app/api/upload.py`
- `backend/app/services/upload.py`
- `backend/app/services/pdf_storage.py`
- `backend/app/services/literature.py`
- `backend/app/repositories/chunk.py`
- `backend/tests/test_upload_api.py`
- `backend/tests/test_pdf_parse_status_api.py`
- `backend/tests/test_pdf_quality_helpers.py`
- `frontend/components/LiteraturePdfUploadClient.tsx`
- `frontend/app/literature/[id]/page.tsx`
- `frontend/tests/pdf-upload-status.test.ts`
- `frontend/tests/literature-detail-meta.test.ts`

RAG/citation/export issues:

- `backend/app/api/rag.py`
- `backend/app/services/rag.py`
- `backend/app/schemas/rag.py`
- `backend/tests/test_rag_api.py`
- `backend/tests/test_rag_service.py`
- `backend/tests/test_rag_literature_contract.py`
- `backend/tests/test_rag_export_api.py`
- `backend/tests/test_rag_export_service.py`
- `frontend/components/RagAnswerClient.tsx`
- `frontend/lib/api/rag.ts`
- `frontend/tests/rag-api.test.ts`
- `frontend/tests/rag-answer-export.test.ts`
- `frontend/tests/rag-uploaded-pdf-citation.test.ts`

Network pharmacology issues:

- `backend/app/api/network.py`
- `backend/app/services/network.py`
- `backend/app/services/enrichment.py`
- `backend/app/repositories/network_tasks.py`
- `backend/app/repositories/network_entities.py`
- `backend/tests/test_network_api.py`
- `backend/tests/test_network_service.py`
- `backend/tests/test_network_report_service.py`
- `backend/tests/test_network_enrichment_integration.py`
- `frontend/components/NetworkAnalysisClient.tsx`
- `frontend/components/NetworkGraph.tsx`
- `frontend/lib/network-graph.ts`
- `frontend/lib/api/network.ts`
- `frontend/tests/network-api.test.ts`
- `frontend/tests/network-graph.test.ts`
- `frontend/tests/network-report-export.test.ts`
- `frontend/e2e/network-graph-keyboard.spec.ts`

Access-control/internal-preview ops issues:

- `backend/app/core/access_control.py`
- `backend/app/main.py`
- `frontend/lib/api/client.ts`
- `scripts/run-internal-preview.ps1`
- `scripts/smoke-internal-preview.ps1`
- `scripts/collect-internal-preview-evidence.ps1`
- `scripts/verify-local.ps1`
- `frontend/tests/internal-preview-ops-source.test.ts`
- `backend/tests/test_access_control.py`
- `backend/tests/test_cors.py`

Focused validation examples:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_rag_api.py tests\test_rag_literature_contract.py -q
```

```powershell
cd frontend
node --import tsx --test tests\rag-api.test.ts tests\rag-uploaded-pdf-citation.test.ts
```

After each P0/P1 fix:

```powershell
.\scripts\verify-local.ps1
```

Before final closeout:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

If the fix touches token-gated fetch or preview ops:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

### Phase 5: Sign-off Closeout

Objective: 把正式 reviewer 决策写回项目事实源。

If no P0/P1 issues remain:

1. Update `docs/evaluations/2026-06-05-reviewer-feedback.md`.
   - Fill `Closeout Decision`.
   - Record reviewer recommendation.
   - Record final P0/P1 count as `0` or `resolved`.
2. Create a new handoff under `docs/handoffs/`.
   - Suggested file: `docs/handoffs/2026-06-06-formal-reviewer-signoff.md`
   - Include reviewer roles, profile, flows completed, P0/P1/P2/P3 counts, verification commands, and decision.
3. Update `docs/current-state.md`.
   - Change “formal clinician + research reviewer sign-off pending” to complete only if both reviewers truly signed off.
   - Preserve default boundaries: deterministic + keyword + JSON runtime by default.
4. Update `README.md` only if commands, reviewer flow, or trial operation changed.
5. Optionally update `docs/quality-score.md` if reviewer results materially change a quality area.

If P0/P1 issues were found and fixed:

1. Add each fix and retest result to the feedback packet.
2. Ask the affected reviewer to re-run only the impacted flow.
3. Record re-review result before marking sign-off complete.

### Phase 6: Small-scale Internal Trial Preparation

Objective: After sign-off, prepare a tightly bounded internal trial without changing architecture defaults.

Tasks:

1. Choose run profile:
   - open profile for trusted local demo only, or
   - shared-token profile for minimal internal gate.
2. Create a local trial runtime root under `.tmp/`.

   ```powershell
   .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
   ```

   Or:

   ```powershell
   .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -AccessToken "trial-token"
   ```

3. Run smoke and keep request IDs.

   ```powershell
   .\scripts\smoke-internal-preview.ps1
   ```

   Or:

   ```powershell
   .\scripts\smoke-internal-preview.ps1 -AccessToken "trial-token"
   ```

4. For each trial session, preserve:
   - profile
   - runtime root
   - reviewer/trial user role
   - request IDs for key flows
   - known limitations shown to the participant
5. Stop services after the session.

   ```powershell
   .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop
   ```

## Files Likely To Change

Expected documentation changes:

- `docs/evaluations/2026-06-05-reviewer-feedback.md`
- `docs/handoffs/2026-06-06-formal-reviewer-signoff.md` or next timestamped handoff
- `docs/current-state.md`
- `README.md` if commands or operational boundaries change
- `docs/quality-score.md` if reviewer results change quality ratings

Conditional code/test changes only if P0/P1 feedback requires them:

- `backend/app/api/*`
- `backend/app/services/*`
- `backend/app/repositories/*`
- `backend/app/schemas/*`
- `backend/tests/*`
- `frontend/app/*`
- `frontend/components/*`
- `frontend/lib/api/*`
- `frontend/lib/ui/*`
- `frontend/tests/*`
- `frontend/e2e/*`
- `scripts/*.ps1`

Files/directories not to commit:

- `.tmp/`
- `backend/data/runtime/`
- `backend/uploads/` local files
- local PDF samples unless already intentionally tracked
- `.env` or any secret-bearing file
- generated evidence packs

## Tests And Validation

Standard local gate:

```powershell
.\scripts\verify-local.ps1
```

Branch closeout / reviewer closeout gate:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

Token profile validation when access-token wiring changes:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

Internal preview smoke:

```powershell
.\scripts\collect-internal-preview-evidence.ps1
```

Backend focused gate pattern:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Frontend focused gate pattern:

```powershell
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

Manual acceptance criteria:

- Both reviewer sections in `docs/evaluations/2026-06-05-reviewer-feedback.md` are filled.
- Each required clinician/research flow has been checked.
- Every recorded issue has severity, reproduction steps, actual/expected behavior, and request ID when applicable.
- `Consolidated Triage` has no unresolved P0/P1 before trial.
- `Closeout Decision` is filled.
- `docs/current-state.md` matches the actual sign-off state.

## Risks And Mitigations

Risk: reviewer reports a broad “make it production ready” request rather than a concrete P0/P1.

Mitigation: translate into specific flow-level issues. Keep production auth, PostgreSQL defaulting, OCR, real LLM defaulting, and large data integrations as separate plans/spikes.

Risk: PDF quality warning is interpreted as product failure.

Mitigation: explain current boundary clearly: text PDF preview works for many documents, embedded-font乱码 remains warning path, OCR/commercial extraction is out of current default scope.

Risk: network pharmacology mock is mistaken for final科研级 computation.

Mitigation: keep mock/sample wording visible; if reviewer requests real TCMSP/STRING/KEGG, classify as P2/P3 unless it blocks the explicitly scoped internal preview.

Risk: token profile is mistaken for production authentication.

Mitigation: record shared-token as internal preview gate only; do not rename it as auth or RBAC.

Risk: a P0/P1 fix touches load-bearing frontend source-regex tests.

Mitigation: run the focused frontend source tests after UI shell/meta/copy changes, especially `pdf-upload-status`, `literature-detail-meta`, `client-section-consistency`, and `page-shell-consistency`.

## Out Of Scope For This Plan

- L2 default preview flip to real LLM.
- New live LLM validation sampling.
- PostgreSQL/pgvector productionization.
- OCR, table reconstruction, or commercial PDF extractor integration.
- Real KEGG/STRING/TCMSP integration.
- Production authentication, NextAuth, invite whitelist, or RBAC.
- CI/CD setup.
- Mobile redesign.
- MVP-C molecular docking/MD implementation beyond existing schema placeholders.

## Stop Conditions

Stop and write a fresh implementation plan if:

- A reviewer records any P0 involving medical safety, compliance, or misleading clinical claims.
- A fix would require changing the RAG disclaimer text.
- A requested change would require enabling external LLM/embedding by default.
- A requested change requires production database/authentication architecture rather than local internal preview behavior.
- The same flow fails after two scoped fixes, suggesting a deeper design issue.

## Recommended Next Immediate Action

Schedule the clinician and research reviewer sessions, then run:

```powershell
.\scripts\collect-internal-preview-evidence.ps1
```

Use the generated evidence summary plus `docs/checklists/internal-preview-reviewer-walkthrough.md` during the walkthrough, and fill `docs/evaluations/2026-06-05-reviewer-feedback.md` as the single source of reviewer truth.
