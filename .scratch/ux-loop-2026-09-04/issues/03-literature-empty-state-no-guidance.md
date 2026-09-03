# 03: 链路「查相关文献」深链必然 0 结果，空态无任何引导

状态: Agent可接
优先级: P2
发现轮次: 第 1 轮（UI 走查）

## 现象

mock 链卡片的「查相关文献」链接指向 `/literature?q=IL6|TNF|STAT3`；演示语料实测这些词命中 0（只有 消风散=6、atopic dermatitis / 特应性皮炎=20）。研究者从主流程点过去只会看到「未检索到匹配文献，请调整关键词、来源或排序后重试」，没有说明是语料覆盖问题，也没有可一键尝试的替代词。

## 根因

`frontend/components/LiteratureSearchClient.tsx:330` 空态只有一句通用文案；跨模块深链与语料现实不匹配。

## 整改方案

检索 0 结果（`hasSearched` 且无 error）时，在 StatusPanel 下追加引导块：说明当前为小型演示语料、覆盖主题有限，并提供「消风散」「atopic dermatitis」「特应性皮炎」三个示例检索按钮（点击即以该词重查）。文案保持诚实：不承诺命中、不暗示真实库覆盖。

## 验证

- UI：IL6 深链 → 0 结果 + 引导块 → 点「消风散」→ 6 条
- 既有 literature 系列测试不受影响（文案无测试固化断言，跑全量确认）

## 评论

- 已整改并随第 1 轮提交验证：前端门禁 288 tests + typecheck + build 全绿，UI 复查通过（见 docs/reports/2026-09-04-ux-review-cycles.md 第 1 轮）。
