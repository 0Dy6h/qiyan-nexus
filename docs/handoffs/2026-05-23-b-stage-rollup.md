# 阶段 B Rollup（2026-05-23）

> 路线图：`docs/plans/2026-05-21-roadmap.md` §3.2 阶段 B（MVP-A 真实化 + MVP-B 起步）。
> 本文不重写每颗 slice 的 handoff（B1–B4 各自已有专文），主要做横向汇总：交付物索引、跨 slice 的不变量、未完事项与上下游影响。

## 0. 一句话状态

阶段 B 全部 6 颗 slice 已完成实现（TDD + gauntlet），其中只有 **B1** 已 push 到 origin 并 squash 进 main；**B2 – B6** 仍以本地分支形式排队，待 WSL → GitHub 代理可达后推送 / 评审 / 合并。

| Slice | 主题 | 状态 | 单独 handoff |
|---|---|---|---|
| B1 | LLM provider 接口抽象 | merged in main (`0085ceb`) | `docs/handoffs/2026-05-22-b1-llm-provider-abstraction.md` |
| B2 | RAG eval 50 题 + provider_name 标签 | local on `feat/b2-rag-eval-50q` (commit `a7a3bc0`) | `docs/handoffs/2026-05-22-b2-rag-eval-50q.md` |
| B3 | 网络药理学任务壳（持久化 + `/network` 页） | local on `feat/b3-network-task-shell` (commit `bf497c4`) | `docs/handoffs/2026-05-22-b3-network-task-shell.md` |
| B4 | herb / formula / compound / target / pathway seed | local on `feat/b4-network-entity-sample-dataset` (commit `2df8195`) | `docs/handoffs/2026-05-22-b4-network-entity-sample-dataset.md` |
| B5 | RAG citation ↔ network entity 双向跳转 | local on `feat/b5-rag-network-cross-link`（5 commits 起 `072d13e`，止 `f65d62a`） | 暂无独立文（本 rollup 覆盖） |
| B6 | 数据来源切换面板 | local on `feat/b6-literature-data-source-switcher`（3 commits 起 `fcfc621`，止 `8324957`） | 暂无独立文（本 rollup 覆盖） |

分支拓扑：B1 ⊂ main；B2 ⊂ B3 ⊂ B4 ⊂ B5（线性 stack）；B6 直接基于 main、与 B2-B5 独立。

## 1. 跨 slice 的不变量与共识

- **`非诊断结论、需结合临床。` disclaimer 字符串** 仍是 byte-identical 锁：RAG / eval / frontend 多处断言；阶段 B 内未触碰，C 阶段也不能改。
- **不接真实外部依赖**：LLM、embedding、pgvector、Neo4j、Celery、Redis、MinIO、对象存储、支付都没有引入；网络药理学走本地 JSON seed + deterministic chain，KEGG/STRING/TCMSP 留 C 阶段。
- **provider 抽象（B1）已铺好 C1 接入位**：`select_provider()` env 切换、`AnswerDraft.provider_name` 透传 → eval report；C1 接 Anthropic 时只新增 provider 实现，不动 `services/rag.py` 主线。
- **网络药理学 seed graph（B4）是后续 4 颗 slice 的基础**：B5 的 entity chip 链接、B6 之外（C4 富集分析）都将复用 `backend/data/network/sample_*.json` 与 `app/repositories/network_entities.py` 5 个 `list_*` 方法。
- **TDD 节奏**：每颗 slice 都遵循 RED → GREEN → commit，落地前 backend `ruff format/check + mypy strict + pytest` 与 frontend `pnpm test + typecheck + build` 双侧 gauntlet 必须全绿。

## 2. 测试基数进展

| 节点 | Backend pytest | Frontend pnpm test | Build routes |
|---|---|---|---|
| 阶段 A 收尾 (`3dec7fb`) | 133 | 81 | 7 |
| B1 落地 | 134 (+1) | 81 | 7 |
| B2 落地 | 143 (+9) | 82 (+1) | 7 |
| B3 落地 | 152 (+9) | 87 (+5) | 8 (`/network` 加入) |
| B4 落地 | 158 (+6) | 87 | 8 |
| B5 落地 | 163 (+5) | 99 (+12) | 8 |
| B6 落地（off main，独立线） | 145（main 142 baseline + 3） | 89（main 86 baseline + 3） | 5（main 上 `/network` 不存在；B6 与 B5 合并后会回到 8 routes 145+） |

注：B6 的 baseline 较低是因为它从 main 切出，没有 B2-B5 累计的测试。合并顺序确定后，最终主干会回到 ≥ 165 backend / ≥ 100 frontend。

## 3. 核心交付物（按层）

### 后端

- `app/services/llm/provider.py` — `AnswerDraft` + `LLMProvider` Protocol + `DeterministicProvider` / `MockClaudeProvider` + `select_provider()` env 选择器（B1）
- `app/services/rag.py` — provider 调用 + `available_citation_count` + `applied_source` / `applied_top_k` retrieval metadata（A 阶段已铺，B2 扩展）
- `app/repositories/network_entities.py` — 5 个 `list_*` seed 读取（B4）
- `app/repositories/network_tasks.py` — JSON-backed task repository，进程重启可恢复（B3）
- `app/repositories/runtime_storage.py` — 单次 bootstrap helper（既有），B 阶段没改但产生了 [[runtime-state-bootstrap-stale-on-seed-change]] 这条踩坑教训
- `app/schemas/network_entities.py` — 5 类 entity + `NetworkEntitiesResponse`（B4 + B5）
- `app/services/network.py` — chain 构造改走 seed graph，新增 `list_all_entities()`（B4 + B5）
- `app/api/network.py` — 加 `GET /api/network/entities`（B5）
- `app/api/literature.py` — `/search` 加 `has_pdf_upload` query 过滤（B6）
- `data/network/sample_{herbs,formulas,compounds,targets,pathways,chains}.json` — 5 + 2 + 5 + 5 + 4 + 6 条 seed（B4）
- `data/evals/rag_ad_eval_questions.json` — 30 → 50 题，覆盖 herb / formula / target / pathway（B2）
- `data/literature/sample_ad_literature.json` — 3 条 seed literature 上挂 `related_entity_ids`（B4）

### 前端

- `lib/api/network.ts` + `lib/api/network-entities.ts` — 任务提交 + entity lookup（B3 + B5）
- `lib/api/literature.ts` — `LiteratureDataSourceView` + helpers + `hasPdfUpload` 串接（B6）
- `lib/api/rag.ts` — `CitationCard.related_entity_ids?: string[]`（B5）
- `components/NetworkAnalysisClient.tsx` — submit + poll + 支持 `?focus=<entity-id>` 一次性 prefill（B3 + B5）
- `components/EntityChips.tsx` — citation / literature detail 上的 chip → `/network?focus=<id>`（B5）
- `components/LiteratureDataSourceBanner.tsx` — view-aware 提示卡（4 tone）（B6）
- `components/LiteratureSearchClient.tsx` — source dropdown 改 4 档 view 选择器（B6）
- `components/RagAnswerClient.tsx` — citation 卡片下挂 `<EntityChips />`（B5）
- `app/network/page.tsx` — 新页面，Suspense 包 client 以兼容 next 16 `useSearchParams`（B3 + B5）
- `app/literature/[id]/page.tsx` — metadata 下挂 `<EntityChips />`（B5）

## 4. 已知踩坑 / 复发风险

1. **runtime state stale-after-seed-change**：B5 slice 1 RAG 断言炸过一次，因为 `data/runtime/literature_state.json` 是「不存在才拷 seed」的单次 bootstrap，B4 给 schema 加 `related_entity_ids` 后 runtime 不会自动跟进。B6 slice 1 又因为 `chunk_state.json` 残留 20 条（seed 12 条）而炸 `test_rag_api`。修法同样：删 runtime 文件让它重 bootstrap。已写入 [[runtime-state-bootstrap-stale-on-seed-change]] memory。
2. **WSL → GitHub 代理依赖**：B2 – B6 push 阻塞在 `HTTPS_PROXY=http://172.26.0.1:7897` 不可达。回家把 Windows 侧代理打开后批量推。详见 [[github-remote-via-windows-proxy]]。
3. **Hermes Agent 并发提交**：本仓库有外部 agent 自治推 commit（B2/B3/B4 的 author 行就是 `Hermes Agent`）；任何 slice 开工前要 `git fetch && git rebase origin/main` 防冲突。详见 [[hermes-agent-concurrent-commits]]。
4. **`/network` 前端 `?focus=<id>` 只 prefill 名称 + 兜底类型**：target / compound / pathway 三类 entity 暂被归到 `formula` 触发 fallback chain；正确的 entity-kind-aware query 留给 C2 或之后。
5. **`/literature` 上传 PDF view 默认空**：seed 无 `pdf_upload_id`，要先走 `/api/uploads/pdf` 上传一份 PDF 才能在 view = `uploaded_pdf` 看到结果。展示用环境可以预先种 1-2 份样例 PDF（仍走标准流程，不要直接编辑 seed JSON）。

## 5. push / 合并顺序建议

代理恢复后建议按以下顺序推 + 合（保持线性历史；Hermes Agent 自治分支需要先 fetch）：

```bash
HTTPS_PROXY=http://172.26.0.1:7897 git fetch origin
# 1) B2 起头（B1 已在 main）
git checkout feat/b2-rag-eval-50q && git push -u origin feat/b2-rag-eval-50q
gh pr create --base main --title "feat(eval): expand RAG eval to 50 questions" --fill
# 2) B2 合并后，B3 → B4 → B5 依次 rebase + push（它们是 stacked branches）
git checkout feat/b3-network-task-shell && git rebase main && git push -u origin feat/b3-network-task-shell
# ...repeat for b4, b5
# 3) B6 独立线，可与 B2-B5 并行推
git checkout feat/b6-literature-data-source-switcher && git push -u origin feat/b6-literature-data-source-switcher
```

如果想缩短 review 时间，可以把 B2-B5 合成一个大 PR（同主题：MVP-B 起步）；B6 单 PR 保留以便走合规 / 文案 review。

## 6. 收尾验收（建议在 push 之前本地跑一遍）

- 后端 gauntlet（branch = feat/b5-rag-network-cross-link 上）：`cd backend && .venv/bin/python -m ruff format --check app tests && .venv/bin/python -m ruff check app tests && .venv/bin/python -m mypy app && .venv/bin/python -m pytest -q && echo "BACKEND GAUNTLET GREEN"` → 期望 163 passed。
- 前端 gauntlet（同上）：`cd frontend && pnpm test && pnpm typecheck && pnpm build && echo "FRONTEND GAUNTLET GREEN"` → 期望 99 passed，build 8 routes。
- 浏览器 smoke（B5 + B6 串测）：
  1. `/rag` 问 "消风散治疗 AD" → citation 卡片下出现 entity chip → 点 `消风散` → `/network?focus=formula-xiaofengsan` → 自动 submit → chain 表
  2. `/literature/cn-ad-network-007` → metadata 下出现 6 个 chip（3 pathway + 3 target）
  3. `/literature` → 切换 4 档 view → banner 颜色 + 文案随之变化；切 "上传 PDF" 时空列表（除非已上传过 PDF）

## 7. 与 C 阶段的衔接

- **C1**（Anthropic Claude API 接入）：直接补 `app/services/llm/anthropic_provider.py` 实现 `LLMProvider`，env `QIYAN_LLM_PROVIDER=anthropic` 切换；保留 deterministic 作为回退。touch claude-api skill。
- **C2**（citation grounding tool use）：依赖 B5 已落地的 `CitationCard.related_entity_ids` 与 `chunks` 结构；LLM 必须通过 `cite_chunk` tool 引用，超出 citation 集合 reject。
- **C3**（embedding + faiss）：与 keyword retrieval 并行；不上 pgvector，单文件 `.npy` + 内存 index 即可。
- **C4**（网络药理学富集分析）：复用 B4 seed graph + B3 任务壳；GO/KEGG 走本地字典模拟，不调 STRING。
- **C5**（分析报告 Markdown 导出）：复用 A3 的 `/api/rag/export/markdown` 模式 + B5 的 entity chip 数据。
- **C6**（MVP-C 概念对象 schema 预留）：仅 `schemas/molecular.py` 类型定义；不接路由。

## 8. 不在本 rollup 范围

- 不重述每颗 slice 的实现细节（看各自 handoff）
- 不动 ADR；阶段 B 没有产生新的架构决策，所有 slice 都在既有 ADR-0010 模块边界内
- 不写新的 plan 文档；slice 计划已在 `docs/plans/2026-05-21-roadmap.md` §3.2 与各 slice plan 文里
