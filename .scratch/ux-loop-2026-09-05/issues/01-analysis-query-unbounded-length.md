# 01: 分析对象无长度上限：3500 字符可建成任务并整串多处渲染

状态: Agent可接
优先级: P2
发现轮次: 第 1 轮（输入与校验边界）

## 现象

在 /network 分析对象输入 3500 字符（`"超长复方名测试".repeat(500)`）：

- 前端 input 无 `maxLength`（实测 `maxLength: -1`），无长度校验提示
- 后端接受并创建任务，mock 分析照常完成（`GET /api/network/tasks` 可见该任务）
- 结果页把 3500 字符对象名整串渲染在多处（分析对象、表型行、报告等），页面文本被同一串垃圾输入刷屏

## 根因

- `backend/app/schemas/network.py:419`：`NetworkAnalyzeRequest.query: str = Field(min_length=1)` 无 `max_length`；同文件其他用户输入字段均有上限（canonical_symbol 40、phenotype 200、raw_identifier 100 等），唯独 query 缺失。
- `frontend/components/NetworkAnalysisClient.tsx`：分析对象 input 未设 `maxLength`，`beginRun` 校验只 trim 非空。

## 整改方案

- 后端：`query` 加 `max_length=100`（复方/单味药名实际长度远小于此，100 足够宽容），422 报文自然带出。
- 前端：input 加 `maxLength={100}`；`beginRun` 增加同口径校验提示（与后端一致），避免依赖 422 才暴露。

## 验证

- UI：超长输入无法超过 100 字符；粘贴超长串被截断且可正常提交
- 后端：直 POST 超长 query 返回 422（schema 校验）
- 测试：schema 边界测试 + 前端校验测试

## 评论

- 已整改并随第 1 轮提交验证。
