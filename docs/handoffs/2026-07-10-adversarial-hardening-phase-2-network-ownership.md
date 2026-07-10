# 2026-07-10 对抗性加固第二阶段：Network Task Ownership

## Goal

建立可信 reviewer identity，并用一个完整纵向切片证明对象级授权不是由浏览器参数决定：network task 创建、轮询和报告导出必须绑定同一 reviewer。

## Completed

- nginx Basic Auth 的 `$remote_user` 通过被覆盖的 `X-Qiyan-Reviewer` 进入 `/api/`，客户端同名 header 不能决定 owner。
- FastAPI access-control middleware 只有在内部 `X-Access-Token` 验证通过后才规范化 reviewer id 并写入 request state；open mode 固定为 `local-preview`，忽略来路身份头。
- protected reviewer id 必须已经是 canonical 小写 slug；后端拒绝大写/非规范 principal，不再通过 lowercasing 合并两个 Basic Auth 账号。
- `NetworkTaskRecord` 增加内部 `owner_id`，API response 不暴露该字段。
- create 持久化 owner；result/report 按 `task_id + owner_id` 查询。foreign reviewer 统一得到 404，且不会推进任务状态。
- JSON、SQLite、PostgreSQL repository 的原子 `advance()` 契约全部加入 owner 条件；SQLite/PostgreSQL schema 已提供增量列迁移和 owner index。
- 已存在 task 的 owner 在 upsert 时不可转移；JSON、SQLite、PostgreSQL 均保留首次持久化 owner，legacy `None` 也不会被后续写入自动认领。
- network repository factory 的首次初始化由进程内 `RLock` 串行化，两个冷启动并发请求不会创建两个独立 JSON/SQLite repository 实例。
- SQLite `advance()` 使用 `task_id + owner_id + poll_count` compare-and-swap；即使两个 repository connection 指向同一 DB，也会在冲突后读取新版本重试，不再把两次推进都写成同一个 poll count。
- 同一 Python 进程内，指向同一 canonical SQLite 路径的 repository 实例共享 path-level `RLock`；transition 不会在 CAS loser 上对同一旧版本重复执行，最后一个实例关闭后释放锁注册项。
- report endpoint 与推进式 result polling 已拆分：queued/running report 返回 202 但不推进、不写盘；completed report 只读导出；failed report 返回 409 并保留实际 error。`completed` / `failed` 的重复 result GET 同样不增加 `poll_count`、不重跑 provider、不覆盖已持久化结果。
- legacy runtime task 缺少 owner 时解析为 `None`，不会被 `local-preview` 或首个访问者自动认领。
- token-profile smoke 直连请求增加固定 `X-Qiyan-Reviewer: preview-smoke`。
- internal preview 启动器改用固定 `start-configured-process.ps1` helper；executable、参数 JSON、日志路径和 token 均通过 environment block 传递，不再构造含 operator 参数的 PowerShell `-Command`。端口为 `int` 且限制在 1-65535；优先使用 `pwsh`，实际启动日志保持原始 stderr 文本。
- multipart curl 通过 stdin `--config -` 读取临时 header 配置，不把 token 放进 argv；smoke reviewer id 使用 canonical slug 校验，token 限定为不会突破 curl config 的安全字符集。
- protected smoke 对 RAG signed response 保留后端原始 JSON 文本并原样回传 export endpoint，避免 PowerShell 反序列化/再序列化改变 canonical payload 后触发 409。
- 云端验收增加可判定的双账号 owner smoke：启用 `set -euo pipefail`，严格断言匿名 401、创建 202、owner 200、foreign result/report 404、task id 非空。
- nginx 的 80 redirect 与 443 server 都显式使用 `qiyan_trial` access log；该格式不记录 query string，权限 0640、按日轮转并保留 14 份。runbook 同时明确 nginx error log 在异常场景仍可能含 query context。
- 云端 token 生成、env 更新与 bundle 反查不再把真实 token 展开进 `sed` / `grep` argv；轮换覆盖 backend env、frontend env、nginx map，拆除流程清理 env、site、unit、fail2ban、logrotate、trial log，并在删除 token 配置后最终 reload nginx。

## TDD Evidence

1. Protected create 缺 reviewer identity：修复前 202，修复后 401。
2. Reviewer B 读取 Reviewer A 的 task：修复前 200，修复后 404；A 仍可正常轮询。
3. Repository owner 原子匹配：修复前 SQLite 不接受 owner 参数，修复后 JSON/SQLite contract 全绿。
4. Open mode 伪造 reviewer header：修复前可改变 owner，修复后统一归属 `local-preview`。
5. Legacy SQLite seed 缺 `data_mode`：修复前触发 NOT NULL，修复后补 `mock` 且 owner 仍保持未归属。
6. Completed task 重复 GET：修复前 `poll_count` 从 2 增到 3，修复后 runtime JSON 字节级不变；completed report 与 failed task 也锁定为只读。
7. 两个 SQLite repository 实例并发 transition：修复前观察版本 `[0, 0, 1]`，修复后严格为 `[0, 1]`。
8. HTTP 80 redirect access log：修复前未显式选择安全格式，修复后使用 `qiyan_trial`。
9. 本地 process helper：修复前 operator 路径/端口进入 `-Command`，修复后只执行固定 `-File`，实际 protected smoke 全链通过且 command line 不含 token。
10. Queued/running report：修复前 GET report 会推进并持久化状态，修复后 runtime 文件完全不变；failed report 从误报 202 “still running” 改为 409 + 原始 error。

## Verification

- Backend full suite：`629 passed, 1 skipped`。
- Ruff format/check：通过。
- mypy：通过，`69` 个 source files。
- Frontend Node tests：`229 passed`；typecheck、production build 通过。
- Playwright E2E：`4 passed`；`pnpm audit --prod`：`0` known vulnerabilities。
- PowerShell parser、子进程 command-line 检查与实际 protected token-profile 全链 smoke：通过；health、四类文献、PDF upload/parse、RAG answer/export、network analyze/result/report 全绿，子进程命令行未出现 token。

## Trust Boundary

该 owner 模型依赖以下条件同时成立：公网只进入 nginx；FastAPI/Next 仅监听 loopback；内部 access token 不发给 reviewer；nginx 覆盖 `X-Qiyan-Reviewer`。本机持有内部 token 的 operator 脚本仍可指定 reviewer，因此该 token 必须继续视为高权限内部凭据。`qiyan_trial` access log 只记录 method + URI path，不保存 query string，权限 0640，按日轮转并保留 14 份；这不保证 nginx error log 永远不含 query context。

## Remaining Highest Risk

PDF 仍不是独立私有对象：文件、共享 literature row 中的 metadata/parse result、uploaded chunk 和 RAG citation 横跨四条存储路径。下一切片不能只保护 download；应引入独立 `PdfUploadRecord`（`upload_id`、`owner_id`、`literature_id`、文件 metadata、checksum、parse state/result），并同时关闭 download、parse/status、detail/search projection 与 RAG chunk retrieval 的跨 reviewer 泄漏。

SQLite path-level lock 只保证同一 Python 进程内 transition 不重复；多 worker / 跨进程 exactly-once 仍需要 claim/lease 或正式事务队列。PostgreSQL ownership 目前仅做静态实现与 schema 契约，作为显式 opt-in spike 尚未获得真实数据库集成证据。

## Working Tree

- 未提交 commit。
- `.mcp.json` 与 `components.json` 仍是本阶段之外的本地 untracked 文件，不应纳入提交。
