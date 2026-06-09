# Handoff — 2026-06-09 post-MVP-A 工程收口

> 日期：2026-06-09
> 范围：Phase 0 仓库卫生、Phase 2D 合并到 main、Phase 2A gpt-5.5 baseline 准备
> 状态：工程侧大部分收口；正式 reviewer sign-off 与有效 gpt-5.5 凭据仍是外部阻塞项

## 1. 目标

在正式医生/科研 reviewer sign-off 仍需真人推进的前提下，先完成工程侧可并行收口：推送长期 feature 分支、安全集成回 `main`、刷新事实源索引，并对 router.team `gpt-5.5` baseline 做首次前置尝试。

## 2. 当前状态

- PR #13（`feat: close post-MVP-A integration`）已在 GitHub 合并到 `main`。
- `origin/main` merge commit：`729fa068a8cf947d29065f6385314ca14b3a647a`。
- `docs/current-state.md` 已索引 2026-06-09 `gpt-5.5` baseline attempt 及其 HTTP 401 结果。
- `docs/evaluations/2026-06-09-gpt-5.5-baseline-attempt.md` 记录了为什么该尝试不能算有效 live baseline。
- runtime capture 输出仍留在 `backend/data/runtime/`，该目录 gitignored，不应提交。
- repo-local Git 代理已配置为 `http://127.0.0.1:7897`；`gh` 命令仍需在命令或会话环境里设置 `HTTP_PROXY` / `HTTPS_PROXY`。

## 3. 本轮已完成

- 将此前 feature 分支工作推送到 `origin/feat/multilingual-bge-m3-backend`。
- 从 `origin/main` 创建 `integration/post-mvp-a-closeout`。
- 将 feature 分支 squash-merge 到当前 `origin/main` 基线，解决冲突时保留较新的 BGE-M3 / corpus isolation 状态，并叠加后续 UI、network、internal-preview 等改动。
- 创建 PR #13，并将 GitHub Actions 中 frontend/e2e job 的 pnpm 版本从 8 升到 10，解决 lockfile v9 的 CI 安装失败。
- 确认 PR #13 checks 通过并完成 squash merge。
- 用 router.team + `gpt-5.5` 配置尝试 Phase 2A baseline，profile 为 BGE + NLI grounding。
- 将 baseline attempt 记录为 HTTP 401 授权阻塞，避免把 deterministic fallback 数据误报成 live `gpt-5.5` baseline。

## 4. 仍未完成 / 阻塞

- 正式 clinician 与 research reviewer sign-off 仍需真人填写 `docs/evaluations/2026-06-05-reviewer-feedback.md`。
- Phase 2A 需要更换为已授权 `gpt-5.5` 的 router.team `QIYAN_OPENCODE_GO_API_KEY`，否则无法产出有效 live baseline。
- `QIYAN_OPENCODE_GO_PRICE_*` 应继续保持未设置或 0，直到真实 router.team 合同价格被确认。
- 若本地 `main` 还保留旧的 pre-squash commit，可能与 `origin/main` diverged。对齐本地 `main` 前应先建备份分支；不要删除 `.codex/`、`.tmp/`、`论文产出/`、`项目实体/` 等用户工作目录。

## 5. 关键文件与产物

- PR #13：`https://github.com/0Dy6h/qiyan-nexus/pull/13`
- 当前事实源：`docs/current-state.md`
- baseline attempt：`docs/evaluations/2026-06-09-gpt-5.5-baseline-attempt.md`
- reviewer 反馈模板：`docs/evaluations/2026-06-05-reviewer-feedback.md`
- reviewer 走查清单：`docs/checklists/internal-preview-reviewer-walkthrough.md`
- 内部预览启动脚本：`scripts/run-internal-preview.ps1`
- 内部预览 smoke 脚本：`scripts/smoke-internal-preview.ps1`

## 6. 验证

- PR #13 合并前，`.\scripts\verify-local.ps1` 通过。
- PR #13 合并前，`.\scripts\verify-local.ps1 -IncludeE2E` 通过。
- pnpm 10 CI 修复后，PR #13 GitHub checks 通过。
- `gh pr view 13 --json state,mergedAt,mergeCommit,url` 确认 PR #13 为 `MERGED`。
- `docs/evaluations/2026-06-09-gpt-5.5-baseline-attempt.md` 记录了 10/10 题 HTTP 401 fallback 证据。

## 7. 推荐下一步

先刷新 router.team `gpt-5.5` key，跑单题 smoke 证明返回 `provider_name="opencode_go"`，再重跑 10 题 capture 并新增 evaluation note。并行继续真人 reviewer 流程；内部 smoke、AI review 或证据包都不能替代 clinician/research sign-off。

## 8. 推荐阅读顺序

1. `docs/current-state.md`
2. `docs/evaluations/2026-06-09-gpt-5.5-baseline-attempt.md`
3. `docs/evaluations/2026-06-05-reviewer-feedback.md`
4. `docs/checklists/internal-preview-reviewer-walkthrough.md`
5. `scripts/run-internal-preview.ps1`

## 9. 推荐技能 / 工具

- `github-pr-workflow`：后续 PR / 分支清理。
- `session-handoff`：继续保存跨会话上下文。
- `systematic-debugging`：若换 key 后单题 smoke 仍失败，再系统排查 provider / gateway / env。
