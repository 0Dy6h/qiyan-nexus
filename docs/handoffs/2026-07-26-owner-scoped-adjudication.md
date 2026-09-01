# 交接：owner-scoped 逐行人工 adjudication 与「我的研究」任务列表

date: 2026-07-26
status: 本地实现、独立复审与统一门禁已完成；未 stage、commit 或 push
branch: `feat/pillar2-real-evidence-ranking`

## 1. 本次目标

接续 2026-07-15 handoff 指定的「唯一下一切片」：为 disease、compound 与派生 intersection lineage rows 实现 owner-scoped 人工 adjudication，并补上任务容器入口（`/tasks`「我的研究」）。硬约束：人工判定是**附加审计数据**，不得改写冻结 lineage、provenance hash 或 `formal_network_ready`。

进入本次会话时，该切片已有大量未提交实现，但**未验证、且带有真实缺陷**。本次工作是完成它、修掉缺陷并独立验收。

## 2. 环境阻塞（先于任何代码工作）

项目目录曾从 `D:\Projects\Tcm_tech` 移动到当前路径，pnpm 的**绝对路径 symlink 全部悬空**，`frontend/node_modules` 仅剩 9 个失效链接。表现为 `pnpm test` / `pnpm typecheck` 报 `MODULE_NOT_FOUND: next/dist/bin/next`，与任何代码改动无关。

处置：`rm -rf node_modules && pnpm install --frozen-lockfile`。**目录迁移后必须重装前端依赖**，否则所有前端门禁结果都不可信。

## 3. 本次完成

### 契约

- `POST /api/network/result/{task_id}/adjudications`：append-only 追加一条判定。fail closed —— 未知/外人/legacy ownerless task 一律 `404`；非 `completed` 或无冻结 result 为 `409`；`lineage_row_id` 不在冻结 lineage 中为 `422`；`reviewer_id` 等派生字段作为额外 body 字段提交为 `422`。
- `GET /api/network/tasks`：owner-scoped 任务摘要列表，`created_at DESC, task_id DESC` 确定性排序，legacy ownerless 记录在 repository 层排除，永不输出 `owner_id`。
- `adjudication` projection 挂在**结果响应信封**上（`NetworkResultResponse`），不在冻结的 `NetworkAnalysisResult` 快照内。同一 row 多次判定时 latest wins；`reviewer_id` 持久化供审计但从不回投。
- 报告新增只读「人工判定」段落，声明该数据不改变 lineage、provenance 与 readiness。

### 修掉的真实缺陷

1. **判定计数恒为 0（前端读错位置）**：后端把 `adjudication` 放在响应信封，前端类型与读取写成 `result.adjudication`。reviewer 会提交成功却看不到任何变化——**静默错误，不报错**。已把类型移到 `NetworkResultResponse` 并改为独立 state。
2. **两处 typecheck 失败**：`TargetLineageTable` 要求 `adjudication` prop，两个调用点都没传。派生交集表则**完全没有判定控件**，尽管后端把这些 row 计入 pending。已补齐三类 row set。
3. **成功写入被报成失败**：POST 与随后的刷新 GET 共用一个 `catch`，刷新失败时告诉 reviewer「提交失败，请重试」，而判定其实已落库。重试会在 append-only 审计流里留下本不应存在的事件。已拆成两段，刷新失败给出「已记录，但刷新失败」的独立文案。
4. **页面级提交锁**：任一行在途会禁用全部三张表所有行的按钮，把逐行批量复核串行化。已改为 per-row 锁，并补 `role="status"` live region 说明在途行数。
5. **被取代任务的迟到响应覆盖当前任务**：组件在 URL 变化时不重挂载，`mountedRef` 不足以拦截。已加 `activeTaskIdRef` 世代守卫，每个 `await` 之后校验。
6. **审计 ID 可碰撞**：`adjudication_id` 的 `sequence` 取自写前快照，重试的同 payload 请求可能算出同一 ID。已加 nonce。
7. **SQLite append 丢更新**：`append_adjudication` 是无保护的 read-modify-write，而相邻的 `advance()` 早已因同样原因使用 `poll_count` CAS。`_PATH_LOCKS` 只在进程内生效，第二个 worker 进程可静默吞掉一条已记录判定。已套用同样的 CAS + 重试。

### 附带

- 双侧 operator 高级配置收进 `<details>`，readiness 文案改为「是（达到正式科研标准）／否（未达正式科研标准）」，避免裸 `true/false` 被误读。
- 导航新增「我的研究」，移除失效的「证据评估」入口（`/evals/rag-ad` 路由本身保留）。
- `scripts/smoke-internal-preview.ps1` 新增两个新端点的 smoke 断言，含「判定后 readiness 未翻转」「列表不泄漏 owner」「报告含人工判定段」。

## 4. 验证

- backend 全量：`851 passed, 1 skipped`；`ruff format --check`、`ruff check`、`mypy app` 全通过。
- frontend：`278 passed`（新增 37 个测试）；`pnpm typecheck`、`pnpm build` 通过。
- `./scripts/verify-local.ps1`：通过。
- **活体回归**（dev backend，非仅单测）：reviewer 身份不回投、`formal_network_ready` 保持 false、冻结 lineage row 保持 `pending/unreviewed`、latest-wins、未知 row `422`、伪造 `reviewer_id` `422`、外部 task `404`、报告含判定段、列表不泄漏 owner。
- **并发回归**：8 个并发同 payload 提交得到 8 个不同审计 ID，无丢失 append，projection 仍为单条 latest。
- **变异测试**：移除 SQLite CAS 守卫后新回归测试确实失败（外部写入者的判定被丢弃），证明该测试有效。
- `git diff --check`：无 whitespace error；index 为空。

## 5. 已知红线（本次未修，非本切片引入）

**`-IncludeE2E` 当前为红**：`e2e/main-path.spec.ts` 与 `e2e/literature-data-source.spec.ts` 两个 spec 因 `waitForLoadState("networkidle")` 超时失败（页面渲染正常，load 事件在 dev 模式反复触发导致 networkidle 永不达成）。已用 `git stash` 清空本次改动后复现同样两条失败，确认为**既有红线**。2026-07-15 handoff 记录当时 Playwright `4 passed`，说明这是此后引入的回归，需单独定位。

## 6. 仍存边界

- 人工判定**不能**单独产生网络结论或翻转 `formal_network_ready`；`_build_research_readiness` 中该字段仍硬编码 `False`。
- 冻结 lineage row 上的 `adjudication_status` / `decision` 字段仍恒为 `pending` / `unreviewed`；本切片的判定是并行的审计流，**不回写 lineage row**。两套语义并存是刻意的，但对读者不直观，未来若统一需单独 ADR。
- JSON backend 的 `append_adjudication` 与其 `advance()` / `upsert()` 一样没有跨进程守卫；这是该 backend 的既有整体属性，本次刻意保持一致而未只加固单个方法。
- Postgres 的 `list_records_for_owner` 与 `append_adjudication` 仅由代码审阅确认，跨 backend 参数化测试仍只覆盖 json/sqlite（需要活库）。
- adjudications 数组无长度上限，重试循环可无界增长；每次 append 重写整条记录。
- 仍缺真实领域 reviewer；仍缺独立定义并验证的 source-bound network-assembly gate。

## 7. 关键文件

- `backend/app/api/network.py`、`backend/app/services/network.py`、`backend/app/schemas/network.py`
- `backend/app/repositories/sqlite_network_tasks.py`（CAS 守卫）
- `backend/tests/test_network_adjudication_api.py`、`test_network_task_list_api.py`
- `frontend/components/NetworkAnalysisClient.tsx`、`NetworkTaskListClient.tsx`
- `frontend/lib/network-adjudication.ts`、`network-tasks.ts`、`lib/api/network.ts`
- `frontend/tests/network-adjudication-ui.test.ts`、`network-tasks.test.ts`

## 8. 未提交与工作区

未 stage、commit、push；保留工作树既有改动。工作树另有 `.mcp.json`、`components.json`、根 `package.json` 三个**非本切片**的工具配置文件（shadcn MCP / registry 配置，前端未使用 Tailwind），提交前需单独确认去留。

## 9. 唯一推荐下一步

先修 E2E 既有红线（两条 literature spec 的 `networkidle` 超时），恢复 `-IncludeE2E` 绿色基线；这是分支级收口的前置条件。之后才进入 source-bound network-assembly gate 的**定义与独立验证**——该 gate 不能由人工判定或 artifact 一致性代替。不要在 E2E 红线未清前追加 provider、enrichment 或基础设施。
