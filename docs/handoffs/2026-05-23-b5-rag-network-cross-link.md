# B5 — RAG citation ↔ network entity 双向跳转（2026-05-23）

> 阶段 B 第五颗 slice。把 B4 落地的 entity seed graph 真正接到 UI 上：让 `/rag` citation 卡片可点跳 `/network?focus=<id>`，反向也支持从 `/literature/[id]` 进入；`/network` 页接 `?focus=<id>` 参数 → 解析 entity → prefill 表单 → 自动 submit。
> 前置 slice：B4（`docs/handoffs/2026-05-22-b4-network-entity-sample-dataset.md`）。
> 分支：`feat/b5-rag-network-cross-link`（5 commit，stack 在 B4 上）。

## 落地点

5 个 vertical slice，每颗一个 commit、TDD red → green：

### Slice 1 — `CitationCard.related_entity_ids`（commit `072d13e`）

- `backend/app/schemas/rag.py`：`CitationCard` 加 `related_entity_ids: list[str] = Field(default_factory=list)`
- `backend/app/services/rag.py:177` 组装 citation 时 `related_entity_ids=list(item.related_entity_ids)`
- `backend/tests/test_rag_service.py` 加 2 条断言：query `"消风散与当归饮子治疗特应性皮炎的复方研究"` → `citation.related_entity_ids` 含 `formula-xiaofengsan`；query `cn-ad-gbs-001` → `related_entity_ids == []`

### Slice 2 — `GET /api/network/entities`（commit `f9cc005`）

- `backend/app/schemas/network_entities.py`：新增 `NetworkEntitiesResponse`（按 `EntityKind` 分组的 5 个 list 字段）
- `backend/app/services/network.py`：新增 `list_all_entities(entity_repo: NetworkEntityRepository | None = None) -> NetworkEntitiesResponse`
- `backend/app/api/network.py`：追加 `@router.get("/entities", response_model=NetworkEntitiesResponse)`
- `backend/tests/test_network_api.py` 加 2 条：shape `{herbs, formulas, compounds, targets, pathways}` + 总数 5+2+5+5+4=21；每个元素有 `id` + 显示名字段

### Slice 3 — 前端 entity lookup + `EntityChips` 组件（commit `64a4fc9`）

- `frontend/lib/api/network-entities.ts`（**新建**）：导出 `EntityKind`、`NetworkEntity`、`NetworkEntitiesLookup`、`buildNetworkEntitiesUrl()`、`fetchNetworkEntities()`（module-level memoize via `cachedLookupPromise`）、`resetNetworkEntitiesCache()`、`lookupEntity()`、`buildNetworkFocusHref()`、`getEntityKindLabel()`。靶点 chip 显示 `symbol` 不显示蛋白全名。
- `frontend/lib/api/rag.ts`：`CitationCard` 类型加可选 `related_entity_ids?: string[]`
- `frontend/components/EntityChips.tsx`（**新建**，`"use client"`）：props `{ ids: string[]; emptyHint?: string }`，mount 时拉 lookup → 渲染 inline-style chip（`#0d9488` border `#14b8a6` background `#f0fdfa` borderRadius 999）；未知 id 走虚线 fallback chip。`aria-label="相关网药实体"`
- `frontend/tests/network-entities-api.test.ts`（**新建**，5 条）：URL builder、lookup flatten + kind、memoize、`lookupEntity()`、`buildNetworkFocusHref` URL 编码

### Slice 4 — `/rag` + `/literature/[id]` 挂 chip（commit `fcaf1c0`）

- `frontend/components/RagAnswerClient.tsx`：`import EntityChips` + `<EntityChips ids={citation.related_entity_ids ?? []} />` 插在 `CardBodyText` 后
- `frontend/app/literature/[id]/page.tsx`：`import EntityChips`（Server Component 嵌 Client Component 标准模式）+ `<EntityChips ids={item.related_entity_ids ?? []} emptyHint="..." />` 插在 `CardMetaRow` 后
- `frontend/tests/entity-chips-source.test.ts`（**新建**，4 条）：源码字符串断言 chip 挂载 + 5 类 entity kind label

### Slice 5 — `/network` 接 `?focus=<id>` prefill（commit `f65d62a`）

- `frontend/components/NetworkAnalysisClient.tsx`：
  - 加 `import { useSearchParams } from "next/navigation"` + `import { fetchNetworkEntities, type NetworkEntity } from "../lib/api/network-entities"`
  - `const searchParams = useSearchParams(); const focusEntityId = searchParams.get("focus");`
  - `appliedFocusRef = useRef<string | null>(null)` 做一次性 guard（避免 re-render 重复 submit）
  - 把原 `onSubmit` 中的 submit 流程抽成 `runAnalysis(submitQuery, submitType)`，prefill effect 也复用同一个函数（避免 setState 异步导致 stale state）
  - `useEffect(() => { ... }, [focusEntityId])`：解析 entity → `setQuery(entity?.name ?? focusEntityId)` + `setAnalysisType(entity?.kind === "herb" ? "herb" : "formula")` + `void runAnalysis(nextQuery, nextType)`
- `frontend/app/network/page.tsx`：`<Suspense fallback={<StatusPanel message="加载网药分析面板..." />}>` 包 `<NetworkAnalysisClient />`，让 `useSearchParams` 在 next 16 下仍可 SSG
- `frontend/tests/network-focus-prefill.test.ts`（**新建**，3 条）：源码字符串断言 `useSearchParams` import、prefill 逻辑、Suspense 包裹

## 行为契约（B5 后）

| 维度 | 行为 |
|---|---|
| `POST /api/rag/answer` | citation 上多出 `related_entity_ids: list[str]`，与 literature 上的同名字段同步 |
| `GET /api/network/entities` | 返回 `{herbs, formulas, compounds, targets, pathways}` 各分组 list；总 21 条 entity |
| `/rag` citation 卡片 | 卡片下方出现 entity chip，点击跳 `/network?focus=<id>`；无 entity 的 citation 没有 chip 区域 |
| `/literature/[id]` | metadata 区下方出现 entity chip；3 条 seed 上挂的 `related_entity_ids` 有 chip 渲染，其他显示 emptyHint |
| `/network?focus=<entity-id>` | mount 时一次性 prefill query + analysis_type，自动 submit；URL 不变化 |
| analysis_type 兜底 | `herb` 直填，其他 4 类（formula / compound / target / pathway）暂归 `formula` 走 B4 fallback chain |
| disclaimer | 仍 `非诊断结论、需结合临床。` byte-identical |
| `/network` 路由形态 | 仍 `○ Static`（thanks to Suspense） |

## 调试痕迹

1. **runtime state stale**：Slice 1 写完测试断言 `formula-xiaofengsan ∈ citation.related_entity_ids` 时 FAIL，因为 `data/runtime/literature_state.json` 是 B3 时期 bootstrap 的，缺 B4 加的 `related_entity_ids` 字段（bootstrap 是「文件不存在才拷 seed」单次行为）。修法：`rm data/runtime/literature_state.json` 让它重 bootstrap。已写入 memory `runtime-state-bootstrap-stale-on-seed-change`。
2. **chip kind label 测试断言路径错位**：第一版把 `EntityChips.tsx` 里写过 kind label，但 `getEntityKindLabel` 实际在 `lib/api/network-entities.ts`；测试断言改成读 lib 源码字符串。
3. **prefill 用 setState 后立刻 submit 拿到 stale state**：第一版 prefill 跑 `setQuery(name); setAnalysisType(kind); void runAnalysis(query, analysisType)` —— 后两个参数仍是初始 state，没生效。改成 `runAnalysis(nextQuery, nextType)` 直接传 resolved 值，不依赖 state。
4. **`useSearchParams` 在 next 16 下要求 Suspense**：直接渲染 `<NetworkAnalysisClient />` 会让 `/network` route 从 `○ Static` 降级到 `ƒ Dynamic`；包 `<Suspense>` 后恢复 prerender。

## 不在 B5 范围

- 不开 `GET /api/network/entities/{id}` 单查路由（前端 lookup memoize 已够用）
- 不做 `/network` 页焦点 chain 高亮（focus 只用于 prefill，不变色）
- 不做 entity 节点上的「相关文献反向列表」
- 不动数据来源切换面板（已在 B6 落地）
- 不引入 entity 详情面板 / 弹层 / sidebar
- 不接 KEGG / STRING / TCMSP 真实数据库
- 不为 compound / target / pathway 提供 entity-kind-aware query（暂走 formula fallback chain）

## 验证

```bash
cd backend
.venv/bin/python -m ruff format --check app tests \
  && .venv/bin/python -m ruff check app tests \
  && .venv/bin/python -m mypy app \
  && .venv/bin/python -m pytest -q \
  && echo "BACKEND GAUNTLET GREEN"
# 163 passed (+5 from B4)

cd frontend
pnpm test       # 99 passed (+12 from B4)
pnpm typecheck  # silent OK
pnpm build      # 8 routes，/network 仍 ○ Static
```

**人工 smoke 路径**：

1. `fastapi dev` + `pnpm dev` 同启
2. `/rag` 问 `"消风散治疗 AD 的网络药理学机制"` → citation 卡片下出现 chip（含「消风散」「荆芥」等），鼠标 hover 显示 link
3. 点 `消风散` chip → 跳 `/network?focus=formula-xiaofengsan` → 表单自动填 `query="消风散"`、`analysis_type="formula"` → 自动 submit → chain 表
4. `/literature/cn-ad-network-007` → metadata 区下方 6 个 chip（3 条 pathway + 3 条 target）→ 点 `STAT3` chip → `/network?focus=target-stat3` → 自动 fallback prefill（target 暂归 formula 类）
5. `curl -sS http://127.0.0.1:8000/api/rag/answer -X POST -H 'Content-Type: application/json' -d '{"question":"消风散"}' | jq '.citations[].related_entity_ids'` → 非空数组
6. `curl -sS http://127.0.0.1:8000/api/network/entities | jq '[.herbs, .formulas, .compounds, .targets, .pathways] | map(length)'` → `[5,2,5,5,4]`

## 下一颗候选 / 后续

- **B6 数据来源切换面板（0.5d）** —— 已在 `feat/b6-literature-data-source-switcher` 落地
- **C1 真实 Anthropic Claude API** —— B1 的 provider 抽象已铺好接入位
- 修补项（不阻塞 B5 验收）：
  - `/network` 上为 compound / target / pathway 提供 entity-kind-aware query（不走 formula fallback）
  - chain 表对 focus 命中行做高亮变色
  - entity chip 加 kind tooltip / 前缀
