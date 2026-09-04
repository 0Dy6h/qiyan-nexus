# 06: 坏 task_id 深链误报「后端未启动」，且无恢复入口

状态: Agent可接
优先级: P1
发现轮次: 第 2 轮（报告/边界走查）

## 现象

打开 `/network?task_id=network-nonexistent`，页面显示「轮询任务结果失败，请确认后端服务已启动。」——后端实际在运行，404 被笼统 catch 成「服务不可用」，研究者从分享链接 / 历史记录进来会误判故障，且没有回到任务列表的入口。

## 根因

`fetchNetworkResult`（`frontend/lib/api/network.ts:520`）把所有非 2xx 折叠成无状态码的 generic Error；`pollUntilCompleted` 的 catch（`NetworkAnalysisClient.tsx:397-404`）只能展示统一文案。

## 整改方案

1. `lib/api/client.ts` 新增 `ApiStatusError`（携带 HTTP status）。
2. `fetchNetworkResult` / `fetchNetworkReportMarkdown` / `fetchNetworkTasks` 抛 `ApiStatusError`（消息不变，既有 `assert.rejects` 正则仍匹配）。
3. 客户端 404 分支：「未找到该任务：任务可能不存在、已被删除，或不属于当前环境。」并在错误面板下方渲染「← 回到我的研究」链接（新增 `errorHint` 状态）。

## 验证

- UI：坏 task_id 深链 → 404 专属文案 + 恢复链接可点回 /tasks
- 既有 network 测试不回归；新增测试锁定 404 分支文案与 hint

## 评论

- 已整改并随第 2 轮提交验证：前端 typecheck + 290 tests + build 全绿，UI 复查通过（任务数 walk-through 前后保持 3，无静默写入）。
