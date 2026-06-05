# 2026-06-05 工作总结（最终收工版）

date: 2026-06-05
status: completed; branch pushed; worktree clean
branch: `feat/multilingual-bge-m3-backend`
latest commit: `b26e294 feat(review): add internal trial ops smoke`

---

## 今日最终状态

- MVP-A 证据工作台内部预览基线已收口。
- MVP-B 网络药理学 mock 链路可跑，含网络图、键盘交互、GO/KEGG mock 富集与 Markdown 报告导出。
- PostgreSQL/pgvector spike 已完成真实 Docker runtime benchmark，结论是不翻默认：默认仍 JSON，SQLite 仍是当前可选本地持久化推荐，PostgreSQL 保留 explicit opt-in spike/backend。
- PDF 抽取质量 spike 已完成，结论是不引入 `pdfplumber` 默认依赖、不切换 pypdf；保留 pypdf 启发式增强与 quality warning 路径。
- 内部 reviewer 彩排、正式 reviewer 技术 preflight、token profile automated smoke 与 AFK internal-trial ops 均已完成。
- 正式 clinician/research reviewer sign-off 仍未完成，必须真人填写 `docs/evaluations/2026-06-05-reviewer-feedback.md`，不能由自动化或内部代走替代。

## 今日完成

### Reviewer readiness / preflight

- `016aa1c feat(observability): add request logging middleware for internal preview`
  - 补 request logging middleware、`X-Request-ID`、RAG SLI request id 关联。
  - 新增 `docs/checklists/internal-preview-reviewer-walkthrough.md`。
  - 更新 `docs/quality-score.md`。
- `c3c177d feat(review): close internal reviewer rehearsal loop`
  - 完成内部 reviewer rehearsal。
  - 修复 network enrichment seed path 与 PDF 上传控件 accessible name。
  - 记录 `docs/handoffs/2026-06-05-internal-reviewer-rehearsal.md` 与 formal feedback packet。
- `8c8e16f feat(review): harden internal trial profile`
  - 前端 backend fetch 统一走 token-aware client。
  - 补 backend token-profile smoke。
  - 改进 PDF preview-window 选择。
  - 更新 README/current-state/formal review packet。

### PostgreSQL / PDF spikes

- `680bb38 feat(spike): add PostgreSQL + pgvector backend implementation (partial)`
- `236ba8f feat(spike): close PostgreSQL runtime backend partial`
- `8d83b78 chore(infra): configure PostgreSQL spike compose`
- `d0c4466 docs(spike): record PostgreSQL benchmark verdict`
  - Docker Desktop + `pgvector/pgvector:pg15` runtime smoke 与 JSON/SQLite/PostgreSQL benchmark 已完成。
  - 最终结论记录于 `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`。
- `24eac7e` PDF text extraction quality implementation（later verified by `9dfeab6` / `f1e38dc`）
- `9dfeab6 test(pdf): add unit tests and validation script for PDF quality improvements`
- `f1e38dc docs(spike): record PDF extractor comparison verdict`
  - A5 四份中文 PDF 样本验证与 `pdfplumber` 对照已完成。
  - 最终结论记录于 `docs/evaluations/2026-06-05-pdf-quality-spike.md` 与 `docs/evaluations/2026-06-05-pdf-extractor-comparison.md`。

### AFK internal-trial ops

- `b26e294 feat(review): add internal trial ops smoke`
  - 新增 `scripts/run-internal-preview.ps1`：open/token profile 的 isolated runtime 启停。
  - 新增 `scripts/smoke-internal-preview.ps1`：health、文献四来源、PDF upload+auto-parse、RAG answer/export、network analyze/result/report API smoke。
  - Playwright token profile 支持 `QIYAN_E2E_ACCESS_TOKEN`，token mode 禁止复用 open-mode server。
  - `scripts/verify-local.ps1` 新增 `-E2ETokenProfile`。
  - 新增 `docs/handoffs/2026-06-06-afk-internal-trial-ops.md`。

## 验证

今日最终已跑通：

```powershell
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
.\scripts\smoke-internal-preview.ps1
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop

.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -AccessToken "trial-token"
.\scripts\smoke-internal-preview.ps1 -AccessToken "trial-token"
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -Stop
```

Observed:

- open profile API smoke passed。
- token profile API smoke passed。
- stop command 后 backend/frontend ports 均不可访问。

```powershell
.\scripts\verify-local.ps1
.\scripts\verify-local.ps1 -IncludeE2E
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

Observed:

- backend gates passed: `ruff format --check`、`ruff check`、`mypy app`、`pytest -q` (`504 passed, 1 skipped`)。
- frontend gates passed: `pnpm test` (`166 passed`)、`pnpm typecheck`、`pnpm build`。
- open-mode Playwright E2E passed: `4 passed`。
- token-mode Playwright E2E passed: `4 passed`。

## 当前工作区

- Branch: `feat/multilingual-bge-m3-backend`
- Remote: pushed to `origin/feat/multilingual-bge-m3-backend`
- Working tree: clean at收工时
- Local services: backend/frontend stopped at收工时

## 仍开放 / 不做

- 正式 clinician + research reviewer sign-off 仍需真人 reviewer 走查并填写 `docs/evaluations/2026-06-05-reviewer-feedback.md`。
- L2 default preview 仍不翻转；BGE=0.3 + NLI=0.5 profile 是治理决策，不是默认工程动作。
- 不默认启用真实 LLM、真实 embedding、PostgreSQL、pgvector retrieval、OCR、商业 PDF 抽取器或生产认证。
- PostgreSQL 生产化 ADR 仅在出现多人并发、真实 pgvector ANN 检索、备份恢复/权限/审计等明确生产需求时重开。
- PDF 后续若继续，应单独做 OCR、表格重建或 license-reviewed 抽取器 spike，不能扩进默认内部预览路径。

## 明日推荐下一步

唯一推荐主线：安排真实医生 + 科研 reviewer 按 `docs/checklists/internal-preview-reviewer-walkthrough.md` 走查，并把结果填入 `docs/evaluations/2026-06-05-reviewer-feedback.md`。

若 reviewer 仍不可用，不要继续横向开新基础设施；优先保持当前分支可合并/可演示状态，等待人工反馈里的 P0/P1。

## 推荐阅读顺序

1. `docs/current-state.md`
2. `docs/handoffs/2026-06-05-daily-work-summary.md`
3. `docs/handoffs/2026-06-06-afk-internal-trial-ops.md`
4. `docs/checklists/internal-preview-reviewer-walkthrough.md`
5. `docs/evaluations/2026-06-05-reviewer-feedback.md`

## 推荐技能 / 工具

- `session-handoff`：正式 reviewer 反馈回来后记录 closeout。
- `test-driven-development`：如 reviewer 报 P0/P1，用最小 failing test 先锁问题。
- `systematic-debugging`：如出现环境/端口/Playwright 不稳定，再按反馈环排查。
