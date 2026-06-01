# Session Wrap + Handoff — 2026-06-01 (Network Graph Visualization)

branch: 待定（建议 `feat/network-graph-viz`）
default RAG path: offline `deterministic`，本切片未触碰
gauntlet at stop: 前端 158 passed / typecheck / build 全绿；后端 351 passed、mypy/ruff clean（无回归）

---

## 交付清单

| Slice | 内容 | 状态 |
|---|---|---|
| 0 | 基线确认（前端 141 → 起点全绿） | ✅ |
| 1 | 纯布局模型 `buildNetworkGraphModel` + 10 条真值单测 | ✅ |
| 2 | SVG 展示组件 `NetworkGraph.tsx` + 接入 `NetworkAnalysisClient` + 7 条源码断言 | ✅ |
| 3 | a11y / 响应式 / 空态 + 真机 `/network` 走查（Playwright DOM 核验） | ✅ |
| 4 | 文档收口（本 handoff + current-state） | ✅ |

## 做了什么

把 `/network` 结果区从「纯链卡片 + 富集表格」升级为**确定性 node-link 图**：成分链按
`中药/复方 → 化合物 → 靶点 → 通路 → 疾病` 五层固定布局渲染为内联 SVG，叠加在原有链卡片**之上**
（纯增量，未删除任何既有卡片、富集表、EntityChips、跳转链接、导出按钮、disclaimer）。

- **布局是纯函数**：`buildNetworkGraphModel(chains)` 同层去重节点、相邻层连边、坐标确定性可复现；
  逻辑由 10 条真值单测（非源码字符串）兜底。
- **展示是无依赖 SVG**：零 d3 / 零 canvas / 零图表库；inline-style + 主色 `#0d9488~#14b8a6~#99f6e4`。
  边的 `score` 映射为线宽/透明度（≥0.9 粗、≥0.7 中、<0.7 细）用于解读而非装饰。
- **a11y**：`<svg role="img" aria-label="网络药理学成分-靶点-通路-疾病链图">`，每节点 `<title>`（如「靶点: IL6」）。
- **响应式**：SVG 包在 `overflowX:auto` 容器，`viewBox` 动态计算。
- **空态**：链为空时渲染层标题 + 居中「暂无网络数据」。

## 真机走查结果（Playwright DOM 核验，2026-06-01）

后端 uvicorn:8000 + 前端 next dev:3000，提交「消风散」（复方）：

- SVG `aria-label` 正确，`viewBox="0 0 1120 340"`
- **11 节点**（1 复方 + 3 化合物 + 3 靶点 + 3 通路 + 1 疾病）、**23 条边**
- 5 层标题全部存在；图例「连线粗细表示置信度（越粗越高）」存在
- `<title>` tooltip 正确（如「中药/复方: 消风散」「靶点: IL6」）
- 节点标签为真实 mock 数据（槲皮素 / 木犀草素 / 山奈酚 / IL6 / TNF / STAT3 / JAK-STAT signaling pathway / Atopic dermatitis 等）
- 唯一 console error 是既有 `favicon.ico` 404，与本切片无关

## 新增文件

- `frontend/lib/network-graph.ts` — 纯布局模型 `buildNetworkGraphModel` + 类型 `GraphModel/GraphNode/GraphEdge`
- `frontend/components/NetworkGraph.tsx` — 内联 SVG 展示组件（default export，`"use client"`）
- `frontend/tests/network-graph.test.ts` — 10 条真值单测（去重 / 边数 / 坐标确定性 / formula 覆盖 herb / 空态等）
- `frontend/tests/network-graph-ui.test.ts` — 7 条源码断言（SVG role、层标题、图例、tooltip、接入）

## 修改文件

- `frontend/components/NetworkAnalysisClient.tsx` — 仅两处增量：
  1. `import NetworkGraph from "./NetworkGraph";`（在 `EntityChips` import 之后）
  2. 在 `phase==="completed"` 分支链卡片 grid **之前**插入 `<NetworkGraph chains={result.chains} />`

## 技术决策

1. **确定性分层布局，不引入 force/d3**：临床工作台基调要求低噪、可预测、可复现；纯函数布局还能单测。
2. **增量叠加而非替换链卡片**：不隐藏证据。图作概览，卡片仍承载 EntityChips、查文献/去 RAG/聚焦实体跳转、置信度、导出。
3. **边 score → 线宽/透明度**：用于解读优先级，不是装饰性渐变。
4. **纯前端切片，未动后端/schema**：`NetworkChain` 形状（herb/formula?/compound/target/pathway/disease/score）不变。
5. **未新增 ADR**：纯前端可视化、无架构边界变更，仅 handoff + current-state 记录即可。

## 未做 / 边界

- 未引入 d3 / Tailwind / 图表库；未改后端、schema、报告导出；未改 `disclaimer` 字符串；未碰 runtime/seed JSON。
- 默认 RAG 仍离线 `deterministic` / L1，本切片未触碰。
- hover 高亮连通边（可选 stretch）**未实现**——核心切片保持静态，可作为下一步增强。

## Loose ends（给下一会话）

1. **未提交、未建分支。** 工作区有 4 个新文件 + 1 个改动文件待提交，建议单分支 `feat/network-graph-viz`，
   按 slice 拆 commit 或单 commit + 本 handoff 同 commit。
2. **可选增强候选**：
   - hover 节点高亮其连通边（零依赖 state/CSS）
   - 节点点击 → 复用现有「聚焦首个实体」跳转语义
   - 同层节点过多时的折叠/分页（当前 mock 规模 11 节点无压力）

## 复现（前端，离线）

```powershell
cd D:\Projects\Tcm_tech\frontend
pnpm test                                          # 158 passed（含 17 新增）
pnpm typecheck
pnpm build
node --import tsx --test tests\network-graph.test.ts        # 10 布局真值单测
node --import tsx --test tests\network-graph-ui.test.ts      # 7 源码断言
```

真机走查（需后端在 127.0.0.1:8000；Windows 下 fastapi-cli emoji 会触发 GBK 编码报错，
改用 uvicorn 直跑并设 `PYTHONUTF8=1`）：

```powershell
# 后端（工作目录必须是 backend，否则 ModuleNotFoundError: app）
$env:PYTHONUTF8="1"
cd D:\Projects\Tcm_tech\backend
& .\.uv-test-venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 前端
cd D:\Projects\Tcm_tech\frontend
pnpm dev --port 3000
# 浏览器开 http://localhost:3000/network → 提交「消风散」→ 链卡片上方出现 node-link 图
```
