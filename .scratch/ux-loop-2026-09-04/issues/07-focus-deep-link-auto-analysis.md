# 07: focus 深链被动触发分析写入：实体 chip 点击即建任务、非方药实体被标「复方」、离开页面任务卡 running

状态: Agent可接
优先级: P1
发现轮次: 第 2 轮（图谱/focus 走查）

## 现象

访问 `/network?focus=target-il6`（链路卡实体 chip 与「聚焦首个实体」的落点）后，`/api/network/tasks` 多出一个 `query=IL6, analysis_type=formula` 的任务且停留在 running。实测一次页面访问即创建任务。

三层问题：

1. **被动导航触发写操作**：focus effect 直接 `runAnalysis`，点 chip = 建任务。与产品「研究协议运行前冻结、任务由研究者显式启动」的门禁精神相悖；5 张链 × 4 类实体 chip 走一遍会静默制造一批任务。
2. **kind 映射语义错误**：非 herb 实体（target/pathway/compound）一律按 `formula` 预填，「IL6」以复方身份进入任务列表。
3. **mock 任务靠读推进**：auto-run 后立刻离开页面，任务停在 running，直到有人 GET result 才完成，/tasks 列表长期显示「运行中」。

## 根因

`NetworkAnalysisClient.tsx:806-840` focus effect 调用 `runAnalysis(nextQuery, nextType)`；`nextType = entity?.kind === "herb" ? "herb" : "formula"`。

## 整改方案

focus 深链降级为**纯预填**，不自动运行：

- `herb` / `formula`：预填分析对象与类型，显示信息级提示「已按实体预填分析对象「X」，请核对研究协议后点击开始分析。」
- `compound` / `target` / `pathway`：不预填（它们不是合法分析对象），提示「「X」是成分/靶点/通路，不作为分析对象；可用链路卡的「查相关文献」「去 RAG 提问」继续。」

新增 `infoMessage` 状态（StatusPanel 默认 tone），`beginRun` 时清除。mock 任务惰性推进为既有设计，记录不改。

## 验证

- UI：focus=herb/formula 深链 → 预填 + 提示，任务数不变；focus=target-... → 不预填 + 提示，任务数不变
- 更新既有 focus prefill 测试（network-focus-prefill.test.ts）锁定新行为

## 评论

- 已整改并随第 2 轮提交验证：前端 typecheck + 290 tests + build 全绿，UI 复查通过（任务数 walk-through 前后保持 3，无静默写入）。
