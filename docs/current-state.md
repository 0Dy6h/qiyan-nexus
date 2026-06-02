# Current State

本文件是 Tcm_tech / Qiyan Nexus 当前开发事实源索引。若历史规划、早期 prototype 或 archive 内容与本文件冲突，以本文件列出的入口为准。

## 当前事实源优先级

1. `backend/`、`frontend/` 代码与测试
2. `README.md`
3. `AGENTS.md`
4. `CLAUDE.md`
5. `CONTEXT.md`
6. `docs/adr/`
7. 最新 `docs/handoffs/`
8. `docs/archive/` 仅作历史参考

## 当前能力边界

- 当前阶段：MVP-A 证据工作台基本可内部走查；MVP-B 网络药理学 mock 起步链路已落地；C 阶段 provider / retrieval / grounding 底座部分提前完成。**2026-06-01 L2 推进工程闭环（Slices 1-5）+ §4c 真人走查完成，决策：L2 不翻转，保持 L1。** 4 份本地 reviewer PDF 样本已通过隔离状态的真实上传 + auto-parse API 探测；人工反馈中的 `/network` 链接缺口与 PDF 数字/表格乱码提示已处理。正式医生/科研 reviewer sign-off 仍需单独真人走查记录，不能由自动化结果替代。
- 数据：本地 JSON seed + `backend/data/runtime/` 运行态副本；runtime state 是本地开发/演示状态，不是生产数据库，也不应回写 seed fixture。
- 文献：本地样本文献、PubMed 实时同步入口、上传 PDF 解析片段、chunk 与 50 题 AD RAG eval 数据集。
- RAG：默认 `deterministic` provider + `keyword` retrieval，返回 answer、citation cards、retrieval metadata、provider name、token usage、grounding metadata 字段与免责声明。
- LLM provider：`deterministic` 默认；`mock_claude` 用于离线 wiring 测试；`opencode_go` 是当前优先 live-provider smoke 路径，仅在显式配置 `QIYAN_OPENCODE_GO_API_KEY` 后调用外部服务。**2026-05-31 已完成真实 live smoke**（`docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`）：实测 `deepseek-v4-flash`（thinking mode）拒绝强制 `tool_choice`（HTTP 400），真实路径走 structured claims v3 而非 provider-native tool use；默认 `max_tokens=1200` 会被 reasoning 吃光导致空 content 回退 deterministic，需 ≥4000 才能让真实路径生效。优先尝试 OpenAI-compatible `record_grounded_claims` function tool grounding；若网关或模型拒绝 tools，则重试 structured claims JSON 并继续经过 structured claim grounding v3 校验。**2026-06-01 已落地 claim 质控 prompt v2**：发给真实 provider 的 prompt 明确要求每条 claim 只能引用 1 个证据 ID，且只能由对应 `证据文本` 直接蕴含；禁止跨引用综合，禁止添加引用片段未明示的治疗疗效、靶点、生活质量、因果或指南地位；OpenCode Go function schema 同步收紧为最多 3 条 claim、每条 claim 最多 1 个 evidence ref。`anthropic` 路径保留为后置可选 smoke，仅在未来有 `ANTHROPIC_API_KEY` 时使用。上述结构/工具/证据 ID grounding 之后，外部 provider 还会经过语义级 grounding gate：每条 claim 与其引用 chunk 文本计算 cosine，低于阈值（`QIYAN_GROUNDING_SEMANTIC_THRESHOLD`，hashing backend 默认 `0.40`，bge backend 推荐 `0.78`）则 `blocked_reason="semantic_low_support"`。**默认 `hashing` backend 下该分数是词汇重叠代理（lexical proxy），不是真正语义判定；`QIYAN_EMBEDDING_BACKEND="bge"` 原地升级为真实语义（已验证，推荐阈值 0.78）。** 标注语料 `backend/data/evals/grounding_semantic_pairs.json` + `run_grounding_semantic_separation` 度量分离度。BGE 评估结果（2026-05-31）：阈值 0.78 下实现完美分离（0 false rejects, 0 false accepts, 100% paired separation, clean score gap +0.029）。详见 `docs/evaluations/2026-05-31-bge-semantic-evaluation.md`。该 gate 仅作用于 `anthropic` / `opencode_go`，不改变真实 provider 默认关闭的事实。**真实 provider 已具备可治理启用路径（L1 受控 smoke/演示可启用，L2 默认预览仍不翻转）：启用决策与不变量见 ADR-0012，外发数据流向与 PIPL 见 ADR-0011，开/关步骤见 `docs/guides/real-llm-enablement-runbook.md`；默认路径仍为离线 deterministic。**
- LLM claim-quality v2 live validation：**2026-06-02 已用真实 key 重新采样 10 个问题**（`docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`）。配置为 `opencode_go + keyword + bge + semantic_threshold=0.3 + transformers NLI=0.5`；14/14 条 claim 均为单 evidence ref，0 条无 ref，0 条多 ref，0 条 unsupported ref/schema parse failure；4/10 个回答 passed，6/10 个回答 blocked，拦截原因均为 `nli_low_entailment`。快速 claim-level review 显示 4 个 passed 回答的 claim 与其 cited chunk 直接对齐。**2026-06-02 已生成并填写 delta-only reviewer packet 的 Codex technical verdict，且用户已确认正式 verdict**（`docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`）：6/6 passed claims 为 supported，0 unsupported，0 unclear；该 packet 只覆盖这 4 个 passed answers 的 claim-vs-chunk 核对，不重复 2026-06-01 已完成的 §4c gate/fallback/rollback/UI 走查。结论：v2 明显改善结构化 claim 质量，L1 受控 smoke/demo 路径更可用；**L2/default preview 仍不翻转**，默认仍为 deterministic。
- RAG SLI：`/api/rag/answer` 顶层返回 `sli`（`provider_latency_ms`、`estimated_cost_usd`），deterministic / fallback 路径 latency 为 int、cost 为 `null`；成本由 token 用量 × `QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK` / `QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK` 计算，单价默认 `0.0` 即不估算（不臆造价格）。后端额外打印不含 secret 的 `rag_sli` 结构化日志；`/rag` 页面与 Markdown 导出展示延迟与成本。
- Price SLI baseline：**2026-06-02 已用当前 `deepseek-v4-flash` 公开 token 价格补齐成本基线**（`docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`）：按 `$0.14` / 1M input、`$0.28` / 1M output 计算，10 题 live capture（6,040 input / 14,984 output）估算总成本 `$0.005042`；provider latency min 5.252s / avg 13.148s / max 28.540s。原 capture 中 `estimated_cost_usd=null` 仍是正确原始事实，因为当时未配置价格 env。生产预算仍需复核 OpenCode Go / DeepSeek 实际合同价格。
- Retrieval provider：`keyword` 默认；`vector` / `hybrid` 可通过 `QIYAN_RETRIEVAL_PROVIDER` 显式 opt-in；默认不启用真实 embedding 模型。
- 跨语言检索：新增确定性 CN↔EN 术语桥（`backend/data/retrieval/cross_lingual_terms.json`，17 组 AD 领域双语术语映射），keyword retriever 现可将中文查询注入英文等价 token，从而命中英文 PubMed 文献（cross_lingual_recall@10 从 0.0 提升至 0.76）。新增 `run_cross_lingual_retrieval_eval()` 评估 harness，支持 keyword/vector/hybrid 三种策略的跨语言 recall、MRR、language_diversity 对比。vector(bge) 在中英跨语场景表现差（0.18），确认 keyword+bridge 为当前唯一有效的跨语策略。详见 `docs/evaluations/2026-06-01-cross-lingual-retrieval-comparison.md`。**2026-06-02 纯数据术语桥扩展**：给 `gut` 条目 zh 补「微生态」一词，闭合 rag-eval-011（cross_recall `0.0 → 0.5`，40100002 进 top-10；40100009 缺 `gut_skin_axis` 标签属已知上限），`avg_cross_lingual_recall` `0.7647 → 0.7941`，mono 1.0 未退化，零默认路径改动。诊断同时确认剩余 3 题（035/047 中文单字 token 淹没、020 弱跨语标注）受 raw-rank 评分结构所限，**纯术语桥天花板已到**，进一步提升需独立决策。详见 `docs/evaluations/2026-06-02-cross-lingual-term-bridge-extension.md`。
- PDF：本地上传存储；文本型 PDF 通过 `pypdf` 提供预览；扫描件/OCR 暂不支持，失败时回退到文件级占位说明。
- 网络药理学：`/api/network/analyze`、`/api/network/result/{task_id}`、`/api/network/entities` 与 `/network` 页面已可跑通 mock 分析任务、seed entity、citation/entity 双向跳转，并支持基于当前结果的前端 Markdown 报告导出。**新增 GO/KEGG 富集分析**：从 chains 提取 target symbols，使用本地 JSON 字典（`backend/data/network/sample_go_terms.json`、`sample_kegg_pathways.json`）模拟 GO/KEGG 数据库，通过 scipy 超几何分布计算 p-value（Bonferroni 校正），返回 top 20 显著富集的通路/功能（p < 0.05，至少 2 个重叠基因）。前端在结果页面展示富集分析表格（Term ID、通路/功能、类别、重叠基因、P-value、基因列表），限制显示前 10 条。当前为 mock 实现，不代表科研级 KEGG REST API 或真实 FDR 校正。**新增结果图可视化（2026-06-01）**：`/network` 结果区在链卡片之上叠加确定性 node-link 图，按 `中药/复方 → 化合物 → 靶点 → 通路 → 疾病` 五层固定布局渲染内联 SVG（纯前端，零 d3/canvas/图表库依赖）。布局由纯函数 `frontend/lib/network-graph.ts` 的 `buildNetworkGraphModel` 计算（同层去重、相邻层连边、坐标确定性可复现，10 条真值单测兜底）；展示组件 `frontend/components/NetworkGraph.tsx` 将边 `score` 映射为线宽/透明度，带 `role="img"`、`aria-label`、每节点 `<title>` tooltip、图例与空态（「暂无网络数据」）。详见 `docs/handoffs/2026-06-01-network-graph-viz.md`。
- 前端：Next.js App Router + React + Ant Design，页面包括 `/`、`/literature`、`/literature/[id]`、`/rag`、`/evals/rag-ad`、`/compliance`、`/network`。
- 默认运行不接入真实 LLM、真实 embedding 模型、pgvector、Neo4j、Celery、Redis、MinIO、NextAuth 或外部生产服务；外部服务只作为本地显式 smoke，不进入默认用户路径。

## 当前目录分层

- `backend/` — FastAPI 后端应用。
- `frontend/` — Next.js 前端应用。
- `infra/` — 本地基础设施说明，目前不提供未验证的 compose 配置。
- `docs/adr/` — 架构决策与长期边界。
- `docs/plans/` — 可执行切片计划。
- `docs/handoffs/` — 跨会话续接记录，越新的越接近当前事实。
- `docs/archive/pre-dev-planning/` — 早期规划、Word 文档、HTML 原型和 Trae/Cursor 产物，仅作历史参考。

## 标准验证命令

Backend:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Frontend:

```bash
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

## 当前下一步候选

最新项目级状态见 `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`（✅ claim-quality v2 真实采样：10 题、14 条单 evidence-ref claims、4 passed / 6 NLI blocked）、`docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`（✅ 4 个 passed answers 的 delta-only reviewer packet 已生成并由 Codex technical review 填写，且用户已确认：6 supported / 0 unsupported / 0 unclear）、`docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`（✅ price SLI baseline：10 题估算 `$0.005042`，latency avg 13.148s）、`docs/evaluations/2026-06-01-nli-real-distribution.md`（✅ NLI 真实分布评估：0 FP, 0 FN, gap +0.9549）、`docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`（✅ 真实 LLM live smoke）、`docs/adr/0012-real-llm-enablement.md`、`docs/guides/real-llm-enablement-runbook.md`。**L2 推进** 工程前置、claim-quality v2 真实技术验证、passed-claim verdict 确认与 price SLI baseline 已完成；阻塞项转为 BGE=0.3 评估 profile 是否可接受的治理决策，以及生产预算前复核真实合同价格。近期候选方向包括：

1. **✅ 语义 grounding BGE 评估（已完成）**：BGE (BAAI/bge-small-zh-v1.5) 评估已完成。详见 `docs/evaluations/2026-05-31-bge-semantic-evaluation.md`。
2. **✅ 真实 LLM live smoke + 启用底座（已完成）**：OpenCode Go live smoke 已跑通。真实 provider 现可在 **L1 受控 smoke/演示** 启用；默认仍 deterministic。
3. **L2 默认预览推进（工程部分✅，走查完成，决策不翻转）**：
   - ✅ **threshold recalibration**（§4a）：BGE-cosine 不可达 → 落地 NLI entailment gate（opt-in，默认关）。
   - ✅ **NLI gate 实现**：`mDeBERTa-v3-base-mnli-xnli`，二级 gate（cosine 预筛后）。
   - ✅ **Slice 1-5 工程闭环**：采集 → 标注（20 对）→ 真实分布评估（0 FP, 0 FN, gap +0.95）→ 批处理（batch entailment, ~1.1x）→ §4c 走查准备。
   - ✅ **§4c 真人走查**（2026-06-01）：7 步核验全部通过，NLI gate 在生产管线正确运行，R4/R5 回退验证通过。
   - ❌ **L2 不翻轉**：走查全程无回答穿透 BGE=0.78 + NLI=0.5（4 条全 blocked）。根因是 keyword retriever 中英跨语匹配弱 + openCode Go 自由改写触发多 claim NLI 拦截。保持 L1 受控启用；存 key 者设 3 个 env var 即可启用真实 provider。详见 ADR-0012 2026-06-01 更新（三）。
   - ✅ **claim-quality v2 live validation**（2026-06-02）：BGE 预筛降至 0.3 后，NLI gate 放行 4/10 个回答；所有 14 条 claim 均单证据引用，未见 raw draft 泄漏。delta-only reviewer packet 已由 Codex technical review 填写 6/6 supported，并已由用户确认；决策仍不翻转 L2。
4. 已完成 4 份本地中文 PDF 样本的最小验收探测；后续 PDF 工作应聚焦更好的抽取质量启发式、OCR 或表格重建 spike，不能扩进默认内部预览路径。
5. **✅ 跨语言检索改进（已完成）**：keyword + cross-lingual bridge 策略，cross_lingual_recall@10 从 0.0 提升至 0.76。详见 `docs/evaluations/2026-06-01-cross-lingual-retrieval-comparison.md`。
6. 其它可选主线：network report export 后续增强（后端报告接口、PDF/Word）、runtime JSON → SQLite/PostgreSQL spike；**网络图可视化已落地（2026-06-01）**，后续增强候选为 hover 高亮连通边、节点点击聚焦实体；Anthropic 仅在有订阅/key 后再排期。
7. 下一步候选：
   - ① ~~retrieval 中英跨语匹配~~ → **已完成**（keyword+bridge, 0.7647 → 0.7941 cross_lingual_recall；2026-06-02 术语桥扩展闭合 rag-eval-011，035/047/020 为评分结构/弱标注上限，纯术语桥到顶）
   - ② ~~BGE 阈值 + NLI gate 的真实 LLM 重验证~~ → **技术采样已完成**（BGE=0.3 + NLI=0.5 下 4/10 passed）；reviewer packet 已生成并填入 Codex technical verdict，用户已确认 verdict；仍需治理判断是否接受 lower-BGE-prefilter profile。
   - ③ ~~LLM claim 质量控制（结构化 claim 校验、grounding gate 增强）~~ → **prompt/schema 质控 v2 已落地并 live 验证结构改善**；后续重点是是否接受 lower-BGE-prefilter profile。
