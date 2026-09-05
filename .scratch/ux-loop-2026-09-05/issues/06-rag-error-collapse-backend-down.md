# 06: RAG 生成失败把服务端 5xx/4xx 折叠成「请确认后端服务已启动」，误导排查方向

状态: Agent可接
优先级: P2
发现轮次: 第 3 轮（加载态与异步反馈）

## 现象

页内拦截 `/api/rag/answer` 注入 500 后提交问题：UI 显示「请求失败，请确认后端服务已启动。」——后端正在运行且已返回 500，用户被引导去排查「后端没启动」。重试路径本身正常（撤销拦截后重试成功出答案）。

这是「非 2xx 折叠成无状态码错误」家族的第三处：09-04 issue 06 修了 result 轮询 GET、09-05 issue 02 修了 network POST 提交，RAG 的 POST（answer）与导出、以及 network 轮询的非 404 分支仍折叠。

## 根因

- `frontend/lib/api/rag.ts:122/138/154`：answer / markdown 导出 / docx 导出三个 POST 对 `!response.ok` 抛普通 `Error`，不带状态码。
- `frontend/components/RagAnswerClient.tsx:204` 裸 `catch` → 固定「请求失败，请确认后端服务已启动。」
- `frontend/components/NetworkAnalysisClient.tsx:415-417` 轮询非 404 分支同样只认「后端已启动」一种解释。

## 整改方案

- rag.ts 三处改抛 `ApiStatusError(response.status, ...)`。
- RagAnswerClient catch 分层：`ApiStatusError` → 「生成回答失败（HTTP xxx），请稍后重试或调整检索范围。」；真网络故障 → 保留「请求失败，请确认后端服务已启动。」
- 轮询 catch 补非 404 分支：ApiStatusError → 显示状态码；transport 错误 → 保留原 backend 提示。
- 判定流复查为非问题：写/读错误已分离、双击有同步 ref 防护、文案多因不误导。

## 验证

- 页内注入 500 → 显示含状态码的诚实文案，不再出现「后端已启动」误导；撤拦截重试恢复
- 测试：ApiStatusError 分层断言（rag.ts 三处 + 两组件 catch）；network-focus-prefill 的轮询分支断言同步更新

## 评论

- 已整改并随第 3 轮提交验证。
