# 01: /network 默认查询日期用 UTC，东八区 8 点前默认成昨天

状态: Agent可接
优先级: P1
发现轮次: 第 1 轮（UI 走查）

## 现象

打开 `/network`，查询日期默认 `2026-09-03`；当天本地日期是 `2026-09-04`（本地时间上午 7 点档）。

## 根因

`frontend/components/NetworkAnalysisClient.tsx:307`

```ts
const [queryDate, setQueryDate] = useState(() => new Date().toISOString().slice(0, 10));
```

`toISOString()` 返回 UTC 日期；UTC+8 在本地 00:00–08:00 之间慢一天。查询日期是研究协议门禁字段，默认值错会直接冻结进任务。

## 整改方案

新增 `frontend/lib/format-date.ts` 提供本地日期工具 `toLocalDateInputValue(date)`（本地年月日 → `YYYY-MM-DD`），默认值改用它；`retrievedAt`/`chemblRetrievedAt` 保持 UTC（机器元数据，语义正确）。

## 验证

- 新增 `frontend/tests/format-date.test.ts`（用本地 getter 计算期望值，任何时区都成立）
- UI 复查默认日期 = 当天本地日期

## 评论

- 已整改并随第 1 轮提交验证：前端门禁 288 tests + typecheck + build 全绿，UI 复查通过（见 docs/reports/2026-09-04-ux-review-cycles.md 第 1 轮）。
