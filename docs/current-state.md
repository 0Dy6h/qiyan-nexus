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

- 当前阶段：MVP-A 证据工作台基本可内部走查；MVP-B 网络药理学 mock 起步链路已落地；C 阶段 provider / retrieval / grounding 底座部分提前完成；2026-05-30 自动化内部预览收口复核通过，4 份本地 reviewer PDF 样本已通过隔离状态的真实上传 + auto-parse API 探测；人工反馈中的 `/network` 链接缺口与 PDF 数字/表格乱码提示已处理。正式医生/科研 reviewer sign-off 仍需单独真人走查记录，不能由自动化结果替代。
- 数据：本地 JSON seed + `backend/data/runtime/` 运行态副本；runtime state 是本地开发/演示状态，不是生产数据库，也不应回写 seed fixture。
- 文献：本地样本文献、PubMed 实时同步入口、上传 PDF 解析片段、chunk 与 50 题 AD RAG eval 数据集。
- RAG：默认 `deterministic` provider + `keyword` retrieval，返回 answer、citation cards、retrieval metadata、provider name、token usage、grounding metadata 字段与免责声明。
- LLM provider：`deterministic` 默认；`mock_claude` 用于离线 wiring 测试；`opencode_go` 是当前优先 live-provider smoke 路径，仅在显式配置 `QIYAN_OPENCODE_GO_API_KEY` 后调用外部服务。**2026-05-31 已完成真实 live smoke**（`docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`）：实测 `deepseek-v4-flash`（thinking mode）拒绝强制 `tool_choice`（HTTP 400），真实路径走 structured claims v3 而非 provider-native tool use；默认 `max_tokens=1200` 会被 reasoning 吃光导致空 content 回退 deterministic，需 ≥4000 才能让真实路径生效。优先尝试 OpenAI-compatible `record_grounded_claims` function tool grounding；若网关或模型拒绝 tools，则重试 structured claims JSON 并继续经过 structured claim grounding v3 校验。`anthropic` 路径保留为后置可选 smoke，仅在未来有 `ANTHROPIC_API_KEY` 时使用。上述结构/工具/证据 ID grounding 之后，外部 provider 还会经过语义级 grounding gate：每条 claim 与其引用 chunk 文本计算 cosine，低于阈值（`QIYAN_GROUNDING_SEMANTIC_THRESHOLD`，hashing backend 默认 `0.40`，bge backend 推荐 `0.78`）则 `blocked_reason="semantic_low_support"`。**默认 `hashing` backend 下该分数是词汇重叠代理（lexical proxy），不是真正语义判定；`QIYAN_EMBEDDING_BACKEND="bge"` 原地升级为真实语义（已验证，推荐阈值 0.78）。** 标注语料 `backend/data/evals/grounding_semantic_pairs.json` + `run_grounding_semantic_separation` 度量分离度。BGE 评估结果（2026-05-31）：阈值 0.78 下实现完美分离（0 false rejects, 0 false accepts, 100% paired separation, clean score gap +0.029）。详见 `docs/evaluations/2026-05-31-bge-semantic-evaluation.md`。该 gate 仅作用于 `anthropic` / `opencode_go`，不改变真实 provider 默认关闭的事实。**真实 provider 已具备可治理启用路径（L1 受控 smoke/演示可启用，L2 默认预览仍被阈值重校准 + 真人走查阻塞）：启用决策与不变量见 ADR-0012，外发数据流向与 PIPL 见 ADR-0011，开/关步骤见 `docs/guides/real-llm-enablement-runbook.md`；默认路径仍为离线 deterministic。**
- RAG SLI：`/api/rag/answer` 顶层返回 `sli`（`provider_latency_ms`、`estimated_cost_usd`），deterministic / fallback 路径 latency 为 int、cost 为 `null`；成本由 token 用量 × `QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK` / `QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK` 计算，单价默认 `0.0` 即不估算（不臆造价格）。后端额外打印不含 secret 的 `rag_sli` 结构化日志；`/rag` 页面与 Markdown 导出展示延迟与成本。
- Retrieval provider：`keyword` 默认；`vector` / `hybrid` 可通过 `QIYAN_RETRIEVAL_PROVIDER` 显式 opt-in；默认不启用真实 embedding 模型。
- PDF：本地上传存储；文本型 PDF 通过 `pypdf` 提供预览；扫描件/OCR 暂不支持，失败时回退到文件级占位说明。
- 网络药理学：`/api/network/analyze`、`/api/network/result/{task_id}`、`/api/network/entities` 与 `/network` 页面已可跑通 mock 分析任务、seed entity、citation/entity 双向跳转，并支持基于当前结果的前端 Markdown 报告导出。**新增 GO/KEGG 富集分析**：从 chains 提取 target symbols，使用本地 JSON 字典（`backend/data/network/sample_go_terms.json`、`sample_kegg_pathways.json`）模拟 GO/KEGG 数据库，通过 scipy 超几何分布计算 p-value（Bonferroni 校正），返回 top 20 显著富集的通路/功能（p < 0.05，至少 2 个重叠基因）。前端在结果页面展示富集分析表格（Term ID、通路/功能、类别、重叠基因、P-value、基因列表），限制显示前 10 条。当前为 mock 实现，不代表科研级 KEGG REST API 或真实 FDR 校正。
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

最新项目级状态见 `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`（✅ 真实 LLM live smoke 已完成）、`docs/evaluations/2026-05-31-bge-semantic-evaluation.md`（✅ BGE 语义评估，推荐阈值 0.78）、`docs/handoffs/2026-05-31-real-llm-enablement.md`、`docs/handoffs/2026-05-31-bge-semantic-recalibration.md` 与更早的 `docs/handoffs/2026-05-30-*`，真实 LLM 启用决策见 ADR-0012、外发数据流向见 ADR-0011、开/关步骤见 `docs/guides/real-llm-enablement-runbook.md`。近期候选方向包括：

1. **✅ 语义 grounding BGE 评估（已完成）**：BGE (BAAI/bge-small-zh-v1.5) 评估已完成。结果：在阈值 0.78 下实现完美分离（0 false rejects, 0 false accepts, 100% paired separation）。BGE 优于 hashing baseline（clean score gap +0.029 vs -0.259）。详见 `docs/evaluations/2026-05-31-bge-semantic-evaluation.md`。
2. **✅ 真实 LLM live smoke + 启用底座（已完成）**：OpenCode Go live smoke 已跑通（`provider=opencode_go`，非 fallback）；记录了 `deepseek-v4-flash` 拒绝强制 tool_choice、需 `max_tokens>=4000`、0.78 阈值对真实改写型 claim 偏严等事实。成本/延迟 SLI、外发 PIPL 措辞、ADR-0011/0012 与启用 runbook 已落地。真实 provider 现可在 **L1 受控 smoke/演示** 启用；默认仍 deterministic。
3. **下一轮真实 LLM 主线候选（L2 默认预览）**：~~扩充 `grounding_semantic_pairs.json` 至真实 LLM 风格 claim 并用 `run_grounding_semantic_separation` 重校准阈值（候选 0.55–0.72）~~ **（2026-06-01 已分析，结论：被阻塞）**。已用 `grounding_semantic_pairs_bge.json`（7 条逐字取自 live smoke 的忠实 claim + 7 条同主题硬负例）在 bge 上扫 0.55–0.78：忠实 claim 0.863–0.963 与硬负例 0.736–0.870 **分布重叠（gap −0.007）**，不存在能同时放行忠实改写、拦截硬负例的阈值。根因是 BGE cosine 度量相似度而非事实蕴含，结构上无法区分「忠实复述」与「同主题臆造」。**未下调阈值（会削弱护栏），保持 L1，默认仍 deterministic。** 详见 `docs/evaluations/2026-06-01-threshold-recalibration.md` 与 ADR-0012 的 2026-06-01 更新。**NLI 蕴含 gate（已落地，opt-in 默认关）**：spike 用 `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`（premise=chunk，hypothesis=claim）在同一 fixture 上把忠实 claim（entailment 0.997–0.999）与硬负例（≤0.001）干净分开，全阈值区间 **0 false accept**（cosine 是 7/7）。已实现为 cosine 之后的二级 gate（`QIYAN_NLI_BACKEND` 默认空=关，`blocked_reason="nli_low_entailment"`），默认行为逐字节不变、CI 不下载模型。详见 `docs/evaluations/2026-06-01-nli-grounding-spike.md`。**L2 仍需**：更大标注集复核 + 定生产阈值、NLI 延迟/成本计入 SLI 基线（§4b）、真人走查（§4c），完成后才翻转默认。
4. 已完成 4 份本地中文 PDF 样本的最小验收探测；后续 PDF 工作应聚焦更好的抽取质量启发式、OCR 或表格重建 spike，不能扩进默认内部预览路径。
5. 其它可选主线：network report export 后续增强（后端报告接口、PDF/Word）、runtime JSON → SQLite/PostgreSQL spike、网络图可视化；Anthropic 仅在有订阅/key 后再排期。
