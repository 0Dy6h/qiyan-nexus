# UX 循环 2026-09-05 PRD

## 目标

延续 2026-09-03 / 2026-09-04 两轮 UX 循环，第三天换层探测：本轮主攻**输入与校验边界**（表单空值/过短/超长/特殊字符/未来日期），并延续到导航与状态连续性、加载与异步反馈两层。每轮「走查 → 问题清单 → 整改 → verify-local 全绿 → commit」闭环。

## 范围

- 隔离预览：`run-internal-preview.ps1 -RuntimeRoot .tmp/ux-loop-0905`（backend 8010 / frontend 3000，open dev mode）
- 浏览器实际操作走查 + API 负路径核对
- 避开已收口面：工具链、全流程 happy path、深链 404/focus 预填、同步/导出/文案、时区/空态（2026-09-03、09-04 已修）
- 避开转人工项：RAG 实体命中透明化（09-04 issue 05）、/network omics UI 入口、CORS 多端口、AL vs ANL snapshot

## 三轮分层

1. 第 1 轮：输入与校验边界（/network 协议表单、/literature 搜索、/rag 提问）
2. 第 2 轮：任务生命周期与导航连续性（列表/详情/刷新/后退/多任务）
3. 第 3 轮：加载态与异步反馈（提交中/轮询中/重复点击/错误恢复）

## 状态标签

用 docs/agents/triage-labels.md 中文标签；走查发现即 `Agent可接`，需拍板的标 `需人工`。
