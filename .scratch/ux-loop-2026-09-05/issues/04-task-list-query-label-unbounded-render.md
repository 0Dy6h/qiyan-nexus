# 04: 任务列表与结果页对超长对象名无截断，legacy 任务可刷屏整页

状态: Agent可接
优先级: P2
发现轮次: 第 2 轮（任务生命周期与导航连续性）

## 现象

R1 修复前创建的 3500 字符对象任务（runtime 内既有数据）：

- /tasks 列表「分析对象」单元格整串渲染 3500 字符，列表页变成文字墙，无法扫读
- 结果页摘要句「分析对象 …」整串渲染（无横向溢出，但一个句子占满整屏）
- 「查看」链接的 aria-label 同样整串（屏幕阅读器灾难）

输入上限（R1 issue 01）只管新任务；列表/结果页面对 legacy 任务、导入数据没有任何防御。

## 根因

- `frontend/components/NetworkTaskListClient.tsx:148` `<span>{row.query}</span>` 无截断；`:197` aria-label 用全量 `row.query`。
- `frontend/components/NetworkAnalysisClient.tsx:1221-1222` 摘要句模板嵌入全量 `result.query`。

## 整改方案

- 新增 `frontend/lib/format-text.ts` `truncateLabel(value, maxLength=40)`：超长截断加省略号。
- 列表单元格：`<span title={row.query}>{truncateLabel(row.query)}</span>`（悬停可见全名）；aria-label 同步用截断值。
- 结果页摘要句：句内用 `truncateLabel(result.query)`，`<p title={result.query}>` 保留全名可及性。

## 验证

- UI：怪物任务在列表/结果页均为单行截断显示，title 悬停见全名
- 测试：truncateLabel 单测 + 源码断言（列表与摘要句必须走 truncateLabel，aria-label 不得用全量 query）

## 评论

- 已整改并随第 2 轮提交验证。
