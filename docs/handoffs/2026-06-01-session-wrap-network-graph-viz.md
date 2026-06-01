# Session Wrap + Handoff — 2026-06-01 (Network Graph Visualization)

branch: main（feat/network-graph-viz 已合并，分支已删除）
default RAG path: offline `deterministic`，本会话未触碰
stopped at: 前端 158 passed / typecheck / build 全绿；后端 351 passed、mypy/ruff clean
working tree: clean | main in sync with origin/main | zero stale local branches

---

## 本会话弧线

本场只做了一件事：**为 MVP-B 网络药理学补齐结果图可视化**。五颗 slice 全程 TDD，无旁路。

| Slice | 内容 | 验证 |
|---|---|---|
| 0 | 基线确认 fn pnpm test/typecheck/build | 141 起点全绿 |
| 1 | 纯布局模型 `buildNetworkGraphModel` + 10 条真值单测 | 151 passed |
| 2 | SVG 展示组件 `NetworkGraph.tsx` + 接入 `NetworkAnalysisClient` + 7 条源码断言 | 158 passed |
| 3 | a11y / 响应式 / 空态收尾 + Playwright DOM 真机走查 | 11 节点 / 23 边 / 5 层标题 / tooltip / 图例 核验通过 |
| 4 | handoff + current-state 刷新 + 审查 + 提交 + PR #9 合并 | merged into main |

## 交付清单

新增 4 个源文件：
- `frontend/lib/network-graph.ts` — `buildNetworkGraphModel(chains)`：5 层确定性布局、按层去重、相邻层按链连边、坐标纯函数可复现
- `frontend/components/NetworkGraph.tsx` — 零依赖内联 SVG（无 d3/canvas/图表库）；边 score → 线宽/透明度三档；`role="img"` + `aria-label` + 每节点 `<title>`；图例；空态
- `frontend/tests/network-graph.test.ts` — 10 条真值断言覆盖空链、单链、去重、坐标确定性、formula 覆盖 herb、边 score 正确性、节点 y 单调增
- `frontend/tests/network-graph-ui.test.ts` — 7 条源码断言覆盖 import、SVG role/aria/layer-headers/legend/tooltip/empty-state

改动 2 个文件（纯增量）：
- `frontend/components/NetworkAnalysisClient.tsx` — +2 行：import + `<NetworkGraph chains={result.chains} />` 插入在链卡片之前；所有既有卡片、富集表、EntityChips、跳转链接、导出按钮、disclaimer 完整保留
- `docs/current-state.md` — 网络药理学能力边界 + 下一步候选刷新

## 仍开放的 L2 阻塞状态

L2 promotion 仍保持 L1（默认离线 deterministic）。上次会话遗留的三个条件中：
- ① retrieval 中英跨语：keyword+bridge 已达 0.76 cross recall，4/17 题仍有覆盖盲区（rag-eval-011/020/035/047）
- ② BGE 阈值重校准：NLI entailment gate 已实现（opt-in 默认关），但需真实 key + reviewer 做真人验证
- ③ LLM claim 质量控制：openCode Go 自由改写触发 multi-claim NLI 拦截，需 prompt 约束优化

## 下一步候选（从最新手到次选的天然顺序）

1. **网络图 hover/交互增强（本切片延伸）** — hover 节点高亮连通边（零依赖 state/CSS）、节点点击复用「聚焦首个实体」跳转、重复边显式聚合。纯前端，低风险。
2. **跨语言术语桥补全 4 题** — 扩展 `cross_lingual_terms.json` 覆盖 rag-eval-011/020/035/047，最快可测的确定性 win（≈0.5d）。
3. **Real-answer NLI 验证集** — 采集真实 opencode_go 答案的 structured claims，标注 support 后过 0.5 阈值评估。关掉 grounding guardrail 最后一个技术 caveat（需真实 key）。
4. **SQLite 持久化 spike** — runtime JSON → SQLite，架构性改动。

## 仓库卫生

- 4 个已合并的残留本地分支全部清理：`chore/gitignore-agents-update`、`feat/c1-anthropic-provider`、`feat/cross-lingual-retrieval`、`feat/l2-real-llm-promotion`
- 当前仅剩 `main` 分支，与 `origin/main` 同步，working tree clean
- 每删除前均核验内容已完全并入 main（diff stat 零内容差异、main..branch 零独有提交）

## 复现

```powershell
# 前端全门禁
cd D:\Projects\Tcm_tech\frontend
pnpm test              # 158 passed
pnpm typecheck
pnpm build

# 网络图单测
node --import tsx --test tests\network-graph.test.ts      # 10 条真值
node --import tsx --test tests\network-graph-ui.test.ts    # 7 条源码断言

# 真机走查（需后端在 8000，Windows 下避开 fastapi-cli 的 emoji GBK 坑）：
# 终端 1
$env:PYTHONUTF8="1"
cd D:\Projects\Tcm_tech\backend
& .\.uv-test-venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 终端 2
cd D:\Projects\Tcm_tech\frontend
pnpm dev --port 3000
# 浏览器 → localhost:3000/network → 提交「消风散」→ 链卡片上方出现 node-link 图
```
