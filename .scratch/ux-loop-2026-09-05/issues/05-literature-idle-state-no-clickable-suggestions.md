# 05: /literature 无查询初始态只有纯文本提示，示例词不可点，与 0 结果空态不一致

状态: Agent可接
优先级: P3
发现轮次: 第 2 轮（任务生命周期与导航连续性）

## 现象

侧栏直接进入 /literature（无 q 参数、未检索）：页面只有表单 + StatusPanel 纯文本提示（「输入中医药或疾病相关关键词…例如：特应性皮炎、消风散、肠道菌群。」），示例词只是文字，要点手动输入。

而检索后 0 结果的空态（2026-09-04 issue 03 修复）提供可点击的「试试「消风散」」示例词按钮。同一页面两种空态，初始态反而更弱。

## 根因

`frontend/components/LiteratureSearchClient.tsx:334` 示例词按钮块整体包在 `{state.hasSearched ? … : null}` 里，idle 分支只有 StatusPanel 文案。

## 整改方案

示例词块移出 `hasSearched` 条件，idle 与 0 结果共用；语料边界说明段（「当前为小型演示语料…」）保持 0 结果专属；idle 分支补一句「还没有检索记录：点下面的示例词直接开始，或输入关键词后检索。」

## 验证

- UI：无查询进入 /literature → 见可点示例词，点击即检索出结果
- 测试：扩展 literature-empty-state-guidance 测试——旧结构（示例词包在 hasSearched 内）不得回归

## 评论

- 已整改并随第 2 轮提交验证。
