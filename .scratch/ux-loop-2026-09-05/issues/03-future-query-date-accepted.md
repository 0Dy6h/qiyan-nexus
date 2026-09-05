# 03: 未来查询日期前后端都不拦，与疾病导入路径的校验口径不一致

状态: Agent可接
优先级: P2
发现轮次: 第 1 轮（输入与校验边界）

## 现象

查询日期手动改为 `2027-01-01` 提交：

- 前端 date input 无 `max` 属性，不拦截
- 后端接受，任务创建成功，协议行展示「查询日期：2027-01-01」无任何警示
- 同文件疾病导入路径有明确校验 `query_date cannot be in the future`（`network.py:107/161/241`）——研究协议作为「运行前冻结」的门禁字段反而没有同等约束

查询日期语义是「外部数据库检索发生日」，未来日期在科研协议上不成立，且与导入路径口径矛盾。

## 根因

- `backend/app/schemas/network.py:49` `NetworkResearchProtocol.query_date: date` 无 validator；导入请求模型各自有 future 校验，协议模型漏了。
- `frontend/components/NetworkAnalysisClient.tsx` 查询日期 input 未设 `max`。

## 整改方案

- 后端：`NetworkResearchProtocol` 加 `@model_validator(mode="after")`：`query_date > today` 时 raise（文案与导入路径同口径「query_date cannot be in the future」）。
- 前端：date input 加 `max={formatLocalDate(new Date())}`（复用 `lib/format-date.ts`），从控件层杜绝未来日期。

## 验证

- UI：日期控件未来日期不可选/不可提交；手输未来日期提交 → 拦截
- 后端：直 POST 未来 query_date 返回 422
- 测试：schema validator 测试；确认既有 seed fixture/测试无未来日期

## 评论

- 已整改并随第 1 轮提交验证。
