# 02: 任务创建时间按 UTC 原串展示，比本地时间慢 8 小时

状态: Agent可接
优先级: P1
发现轮次: 第 1 轮（UI 走查）

## 现象

`/tasks` 列表把 2026-09-04 07:34（本地）创建的任务显示为 `2026-09-03 23:34`。API 返回 `created_at: "...+00:00"`（正确带偏移），展示层未转换。

## 根因

`frontend/lib/network-tasks.ts:14` `formatNetworkTaskCreatedAt` 对 ISO 串做 `replace("T"," ").slice(0,16)` 字符串切片，无时区转换。

## 整改方案

`formatNetworkTaskCreatedAt` 先 `new Date(trimmed)` 解析，成功则按本地时间格式化为 `YYYY-MM-DD HH:mm`（复用 format-date.ts 的 `formatLocalDateTimeMinutes`）；解析失败回退现有切片行为（兼容非 ISO 历史串）。

## 验证

- `frontend/tests/network-tasks.test.ts` 既有 UTC 切片断言改为「由同一输入 Date 的本地 getter 计算期望」的时区无关断言；补充解析失败回退用例
- UI 复查 /tasks 时间与本地钟一致

## 评论

- 已整改并随第 1 轮提交验证：前端门禁 288 tests + typecheck + build 全绿，UI 复查通过（见 docs/reports/2026-09-04-ux-review-cycles.md 第 1 轮）。
