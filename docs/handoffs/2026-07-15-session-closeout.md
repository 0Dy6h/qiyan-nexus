# 2026-07-15 收工交接：ChEMBL Provenance 收口

## 1. Goal

完成并独立验收 ChEMBL compound-target raw-artifact provenance 纵向切片，在不扩大默认依赖和科学声明的前提下，守住 owner、parent link、snapshot-only 输出与 readiness 失败关闭边界。本切片已完成，当前会话主动停止。

## 2. Current state

- Gate 1 与 Gate 2 双侧 artifact/lineage 工程闭环已完成。
- compound child 仅输出冻结 lineage 与派生交集，不构建网络。
- `formal_network_ready=false`，没有未完成的本切片代码缺口。
- 工作树保持未 stage、未 commit、未 push，并保留所有既有用户改动。

## 3. Completed in this session

- 独立追踪 create -> store -> result -> report -> validator -> UI 全生命周期。
- 补受保护模式 HTTP owner 回归，证明 foreign parent 返回 `404` 且无 task/artifact 副作用。
- 同步 current-state、专项 handoff、整改 STATUS/WORKLOG、项目规则与硬化 skill。
- 两轮独立复审均未发现 P0-P3 问题。

## 4. Still open / blocked

- 当前切片没有 blocker。
- 仍缺 owner-scoped 人工 adjudication、真实领域 reviewer 与独立 source-bound network-assembly gate。
- `pnpm audit --prod` 因 npm audit endpoint HTTP 410 未形成漏洞结论；这不是零漏洞证明。

## 5. Key files and artifacts

- `docs/current-state.md`
- `docs/handoffs/2026-07-15-compound-target-provenance.md`
- `docs/audits/2026-07-11-network-pharmacology-realignment/STATUS.md`
- `docs/audits/2026-07-11-network-pharmacology-realignment/WORKLOG.md`
- `docs/guides/network-compound-target-import.md`
- `backend/tests/test_network_compound_api.py`
- `backend/scripts/validate_network_target_lineage.py`

## 6. Verification

- network-focused backend：`219 passed`
- backend 全量：`794 passed, 1 skipped`
- frontend：`240 passed`，typecheck/build 通过
- `./scripts/verify-local.ps1`：通过
- `./scripts/verify-local.ps1 -IncludeE2E`：通过，Playwright `4 passed`
- `git diff --check`：无 whitespace error；index 为空

## 7. Recommended next step

先为 disease、compound 与 intersection rows 写 owner-scoped human adjudication 的纵向切片计划。计划必须先冻结身份、状态机、不可变 snapshot、只读 report 和“不翻转 readiness”验收条件，再进入 RED 测试。

## 8. Recommended reading order

1. `AGENTS.md`
2. `docs/current-state.md`
3. `docs/handoffs/2026-07-15-compound-target-provenance.md`
4. `docs/audits/2026-07-11-network-pharmacology-realignment/STATUS.md`
5. `docs/guides/network-compound-target-import.md`
6. `backend/tests/test_network_compound_api.py`

## 9. Recommended skill / toolset

- `qiyan-adversarial-hardening`
- `project-grill`，先明确 adjudication 状态与权限语义
- `vertical-slice-planning` + `test-driven-development`
- `requesting-code-review`，最终独立验收
