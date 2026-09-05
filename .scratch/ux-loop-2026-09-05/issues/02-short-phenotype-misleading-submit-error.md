# 02: 表型过短前端不拦，后端 422 被折叠成「请确认后端服务已启动」误导文案

状态: Agent可接
优先级: P1
发现轮次: 第 1 轮（输入与校验边界）

## 现象

研究表型填 `AD`（2 字符，后端 `min_length=4`）提交：

- 前端不拦截（空值有拦截、过短没有）
- 后端正确 422（未建任务），任务数不变
- 但 UI 显示 **「提交分析任务失败，请确认后端服务已启动。」** —— 后端明明在运行，用户被引导去排查错误的方向（重启后端），且不知道是哪个字段不合法

## 根因

两层叠加：

1. `frontend/lib/api/network.ts:469` `submitNetworkAnalysis` 对 `!response.ok` 抛普通 `Error("Network analyze request failed")`，不带状态码——2026-09-04 的 `ApiStatusError` 修复只覆盖了 GET result/report/tasks（524/534/544 行），POST 提交路径漏了。
2. `frontend/components/NetworkAnalysisClient.tsx:698` `runAnalysis` 的裸 `catch {}` 把一切失败折叠成「请确认后端服务已启动」。

与 2026-09-04 issue 06（坏 task_id 深链误报「轮询失败」）同一模式：非 2xx 被折叠成无状态码错误。

## 整改方案

- `submitNetworkAnalysis`：`!response.ok` 时抛 `new ApiStatusError(response.status, ...)`（与 GET 路径同口径）。
- `runAnalysis` catch 分层：
  - `ApiStatusError && status===422` → 「提交被服务端校验拒绝：请检查研究表型（4-200 字）与分析对象长度后重试。」
  - 其他非 2xx → 显示状态码的诚实文案
  - 真网络故障（非 ApiStatusError）→ 保留「请确认后端服务已启动」原文案
- 前端 `beginRun` 补过短/超长校验：表型 trim 后 <4 或 >200 直接拦截提示，不必等 422。

## 验证

- UI：表型 `AD` 提交 → 前端拦截提示，不出「后端已启动」误导；网络断开场景才出现原文案
- 测试：ApiStatusError 分层断言 + 前端校验测试

## 评论

- 已整改并随第 1 轮提交验证。
