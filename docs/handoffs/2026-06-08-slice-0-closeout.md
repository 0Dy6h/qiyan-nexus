# Handoff — 2026-06-08 Slice 0 Closeout

## Goal

Slice 0 的目标是把当前分支从“功能基本健康但工作区未收口”推进到“可交付 reviewer 走查”的状态：只做仓库卫生、事实源对账、provider 文档一致性、reviewer preflight 和验证证据包，不新增产品功能，不翻默认运行路径。当前 Slice 0 已完成并暂停，下一轮应先处理未提交改动的提交/走查，再进入正式 reviewer sign-off。

## Current state

- 当前分支：`feat/multilingual-bge-m3-backend`。
- 当前 HEAD：`8bd38a6 feat(network): add opt-in live data pipeline`。
- 远端 `origin/feat/multilingual-bge-m3-backend` 当前停在 `80a80f9 feat(frontend): optimize meteor animation and panel translucency`，本地分支 ahead 1。
- 工作区仍有 Slice 0 收口改动未提交：8 个 tracked 文件 modified，4 个 handoff/roadmap 文档 untracked；本文件是本次收工新增的第 5 个 untracked handoff。
- 默认运行路径未翻转：LLM provider 仍为 `deterministic`，retrieval 仍为 `keyword`，state backend 仍为 `json`，network data provider 默认仍为 mock。
- opt-in live provider 配置已切到 `https://ai.router.team/v1` + `gpt-5.5` + `4096` tokens；这只影响显式设置 `QIYAN_LLM_PROVIDER="opencode_go"` 且提供 key 的 smoke 路径。
- 正式 clinician/research reviewer sign-off 仍未完成，不能由 AI 预审、内部代走、自动化测试或 evidence package 替代。

## Completed in this session

- 读取并核对当前事实源：`docs/current-state.md`、`docs/evaluations/2026-06-05-reviewer-feedback.md`、`docs/handoffs/2026-06-08-post-frontend-ui-handoff.md`、`docs/plans/2026-06-08-post-mvp-a-roadmap.md`。
- 确认 Slice 0 已完成：provider 配置/文档已对齐，reviewer packet 已指向最新 evidence package，默认 deterministic 路径未被翻转。
- 确认当前工作区真实状态：只有计划内 Slice 0 改动和 handoff/roadmap 新文件；`.tmp/`、`frontend/test-results/`、`论文产出/`、`项目实体/` 不在 tracked/untracked 待提交清单里。
- 确认当前 3000/8000 无监听服务，收工时没有遗留本地 dev server。
- 新增本 handoff 作为下一轮接手入口。

## Still open / blocked

- Slice 0 改动尚未提交。下一轮应先 review diff，再决定是否提交。
- 正式 reviewer sign-off 仍是项目下一步阻塞项，需要真实医生和科研 reviewer 填写 `docs/evaluations/2026-06-05-reviewer-feedback.md`。
- router.team + `gpt-5.5` 的 price SLI、latency、NLI pass rate 和治理通过率 baseline 尚未重建；不能沿用 2026-06-02 `deepseek-v4-flash` 历史成本/延迟数据做当前 L2 决策。
- TCMBench 作者联系已记录，仍在等待回复；回复前不集成非公开数据、不训练、不再分发。
- Evidence package 存在于 `.tmp/internal-preview-evidence/20260608-224628/`，该目录按设计 gitignored；reviewer packet 写的是本地路径，不代表证据包会随提交进入仓库。

## Key files and artifacts

- `docs/current-state.md` — 当前事实源索引，已补 2026-06-08 状态刷新。
- `README.md` — provider smoke 文档已从历史 `deepseek-v4-flash` 默认说明更新到 router.team + `gpt-5.5`。
- `backend/app/core/config.py` — opt-in `opencode_go` 默认值已更新；`llm_provider` 默认仍是 `deterministic`。
- `backend/.env.example` — opt-in live provider env 示例已更新。
- `backend/tests/test_config.py` — 配置默认值断言已同步。
- `docs/guides/real-llm-enablement-runbook.md` — 已标明 `gpt-5.5` 当前 smoke 默认，以及价格/延迟/NLI baseline 需重建。
- `docs/evaluations/2026-06-05-reviewer-feedback.md` — reviewer preflight 已刷新，指向 `.tmp/internal-preview-evidence/20260608-224628/evidence-summary.md`。
- `docs/handoffs/2026-06-08-post-frontend-ui-handoff.md` — 当前有效前端/UI 后续交接。
- `docs/handoffs/2026-06-08-frosted-glass-meteor-handoff.md` — 已标注 superseded，仅作历史参考。
- `docs/handoffs/2026-06-08-tcmbench-contact.md` — TCMBench 联系状态。
- `docs/plans/2026-06-08-post-mvp-a-roadmap.md` — 后续 roadmap；下一步仍是正式 reviewer sign-off。
- `.tmp/internal-preview-evidence/20260608-224628/evidence-summary.md` — 最新内部预览 evidence summary，本地 gitignored。

## Verification

- 最近一次完整 Slice 0 验证已通过，并写入 `docs/evaluations/2026-06-05-reviewer-feedback.md`：
  - `.\scripts\verify-local.ps1` passed：backend `ruff format --check`、`ruff check`、`mypy app`、`pytest -q`；pytest 为 `562 passed, 1 skipped`；frontend `pnpm test` 为 `201 passed`，`pnpm typecheck` 与 `pnpm build` 通过。
  - `.\scripts\verify-local.ps1 -IncludeE2E` passed：Playwright open profile `4 passed`。
  - `.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile` passed：Playwright token profile `4 passed`。
  - `.\scripts\collect-internal-preview-evidence.ps1` passed，并生成 `.tmp/internal-preview-evidence/20260608-224628/`。
- 本次收工阶段实际复核：
  - `git status -sb`：显示当前分支 ahead 1，Slice 0 改动未提交。
  - `git diff --stat` / `git diff --name-only`：tracked diff 为 8 个计划内文件。
  - `Get-NetTCPConnection -LocalPort 3000,8000 -State Listen`：无监听输出，未遗留 dev server。
- 本次收工未重新跑 full gate；不要把 handoff 写入本身视为通过门禁的证据。若下一轮要提交，建议先至少跑 `git diff --check`，必要时再跑 `.\scripts\verify-local.ps1`。

## Recommended next step

下一轮不要直接开新功能。先 review 当前 Slice 0 diff，确认无意外文件和事实源冲突，然后提交一个仓库卫生/文档对账 commit。提交后再推进正式 reviewer sign-off：让真实医生和科研 reviewer 按 `docs/evaluations/2026-06-05-reviewer-feedback.md` 完成走查并填写结论。

## Recommended reading order

1. `AGENTS.md`
2. `docs/current-state.md`
3. `docs/handoffs/2026-06-08-slice-0-closeout.md`
4. `docs/evaluations/2026-06-05-reviewer-feedback.md`
5. `docs/plans/2026-06-08-post-mvp-a-roadmap.md`
6. `docs/guides/real-llm-enablement-runbook.md`
7. `git status -sb` and `git diff --stat`

## Recommended skill / toolset

- `session-handoff` — 如果下一轮仍停在未提交状态或 reviewer sign-off 后需要继续交接。
- `requesting-code-review` — 提交前做 diff-oriented review，重点看默认路径是否被误翻转、runtime/evidence 是否误纳入。
- `test-driven-development` — 只有在 reviewer 发现 P0/P1 后，再按最小纵向切片修复。
- PowerShell / `git` / local gates — 本仓库验证命令以 Windows PowerShell 为准。
