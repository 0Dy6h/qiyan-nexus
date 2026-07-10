# 对抗性加固收工交接（2026-07-11）

## Goal

从身份、对象归属、状态机、完整性、并发和运维命令边界出发，完成内部预览链路的第一性原则加固，并留下可复现的验证与下一步。

## Current state

本轮整改已完成并通过全量门禁。浏览器不再接触后端共享 token；network task 已按 reviewer 隔离；report GET 已变为只读观察；RAG export 使用服务端 HMAC 验证原始 answer payload；SQLite network-task 同进程共享路径锁与三类 repository rollback 已补齐；内部预览脚本和云端 runbook 已消除已知 argv/config/header 注入路径。

## Completed in this session

- 升级 Next.js 16.2.6，并将 PostCSS 固定为 8.5.10；生产依赖审计为 0。
- 建立 token 验证后的 reviewer request state，network JSON/SQLite/PostgreSQL repository 全部执行 owner-aware 查询与原子推进。
- foreign task 和 legacy ownerless task 返回 404；completed/failed polling 保持终态。
- report：queued/running 202 且不推进，completed 200 只读，failed 409 返回真实 error。
- unknown network query 返回空 chains；RAG Markdown/DOCX export 拒绝缺失或被篡改的 payload。
- 统一使用 `scripts/start-configured-process.ps1` 启动进程，校验端口及 smoke token/reviewer 参数。
- 更新 cloud runbook、reviewer walkthrough、当前事实源和项目级对抗性加固 skill。

## Still open / intentionally deferred

- PDF upload record、download、parse/status、literature projection、uploaded chunk、RAG retrieval/citation 尚未按 owner 隔离。
- SQLite path lock 仅覆盖单进程；多 worker exactly-once 需要数据库 claim/lease。
- PostgreSQL owner 路径只有 contract/backend 测试，未做真实 PostgreSQL 集成验证。
- reviewer identity 依赖可信代理覆盖 header、8000 loopback 且 reviewer 不知道内部 token。
- RAG export HMAC 使用进程内密钥，服务重启后旧 payload 会失效，这是当前设计边界。
- 当前事实源与高风险指南已同步；部分 2026-05/06 历史 plans、低优先架构快照和 dated handoff 仍有路径/状态漂移，后续应作为独立文档归档清理，不要与 PDF owner-isolation 代码切片混做。

## Key files

- `backend/app/core/access_control.py`、`backend/app/core/reviewer_identity.py`
- `backend/app/services/network.py`、`backend/app/services/rag_export_integrity.py`
- `backend/app/repositories/*network_tasks.py`、`backend/app/repositories/sqlite_*.py`
- `scripts/run-internal-preview.ps1`、`scripts/smoke-internal-preview.ps1`、`scripts/start-configured-process.ps1`
- `docs/guides/cloud-trial-deployment-runbook.md`

## Verification

- Backend：ruff format/check、mypy 全绿；pytest `629 passed, 1 skipped`。
- Frontend：Node tests `229 passed`；typecheck、build 全绿；Playwright `4 passed`。
- `pnpm audit --prod`：0 known vulnerabilities。
- 受保护 profile 真实 smoke：12 条流程通过；进程命令行未出现 token。
- PowerShell AST parse、`git diff --check`、独立 fail-closed review 均通过。

## Recommended next step

只推进一个纵向切片：`PdfUploadRecord` owner isolation。先写跨 reviewer 失败测试，再贯通 upload → parse/status → download → literature → chunk → RAG citation → SSR forwarding；legacy ownerless runtime 数据隔离或 fail closed。

## Recommended reading order

1. `docs/current-state.md`
2. 本 handoff
3. `docs/handoffs/2026-07-10-adversarial-hardening-phase-2-network-ownership.md`
4. `docs/guides/cloud-trial-deployment-runbook.md`
5. `AGENTS.md` 与 `.codex/skills/qiyan-adversarial-hardening/SKILL.md`

## Recommended skills/tools

使用项目级 `$qiyan-adversarial-hardening` 执行威胁建模、RED→GREEN 和提交前门禁；涉及跨会话续接时再使用 session handoff。只定向暂存预期文件，继续排除本机 `.mcp.json`、`components.json` 与 runtime state。
