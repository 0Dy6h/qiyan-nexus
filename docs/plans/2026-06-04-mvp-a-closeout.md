# MVP-A 收尾对账 — 2026-06-04

> roadmap 阶段 A 计划收尾日（`docs/plans/2026-05-21-roadmap.md` §3.1，2026-05-21 → 2026-06-04，2 周）
> 本文档对齐 A1-A6 六个 slice 的真实完成态，分类先前 handoff 留下的 loose ends，给阶段 B 起手提示。
> 不替代 roadmap；roadmap 仍是路线唯一入口。

## A 阶段六个 slice 收尾对照

| Slice | 主题 | 收尾 commit / 引用 | 验收依据 | 状态 |
|---|---|---|---|---|
| A1 | 真实 PubMed 抓取 | PR #10 (`5556df0`) 内 + `docs/handoffs/2026-05-21-a1-pubmed-sync.md` | `backend/app/services/pubmed.py` 真 NCBI E-utils；`literature.py:297 sync_pubmed`；`POST /api/literature/sync`；真网络 ≥10 命中；`test_literature_sync_api.py` 全绿 | ✅ |
| A1.5 | PubMed 同步前端入口 | PR #10 (`5556df0`) 内 + `docs/handoffs/2026-05-21-a1-5-pubmed-sync-ui.md` | `/literature` 页顶部"同步 PubMed"表单组件 | ✅ |
| A2 | 最小访问控制 | 早期 PR + CLAUDE.md 已固化 | `app/core/access_control.py` X-Access-Token 中间件；`QIYAN_ACCESS_TOKENS` env 白名单；CORS 不变；401/200 测试覆盖 | ✅ |
| A3 | RAG 答案 Markdown 导出 | `c7fe91f`（本批次） | `POST /api/rag/answer/export` (PlainTextResponse) + `app/services/rag.py:build_answer_markdown`；前端 fetch；14 个新 backend tests；对齐 Slice 9 网络报告设计 | ✅ |
| A4 | Playwright E2E 起步 | PR #11 (`7ebc11b`) | `frontend/e2e/network-graph-keyboard.spec.ts` + 早期主路径 spec；`pnpm e2e` 全绿（非 per-commit gauntlet） | ✅ |
| A5 | 中文 PDF 人工验收 | `6671c47`（本批次） | `docs/handoffs/2026-06-04-a5-chinese-pdf-verification.md`：4 份真实中文 AD PDF 走 upload + auto-parse + detail 三接口；3/4 干净中文（CJK 130-200），1/4 触发 quality_warning fallback（按设计） | ✅ |
| A6 | 合规页扩展 | `docs/handoffs/2026-05-11-compliance-polish.md` | `frontend/lib/compliance-page.ts:44-58`（数据来源说明 + PDF 版权声明）；`frontend/tests/compliance-page.test.ts:31-69` | ✅ |

**结论**：roadmap §3.1 全部 6 slice + 1 增补（A1.5）已闭环。MVP-A 证据工作台 100% 收尾完成。

## Loose ends 已分类（不计入 A 收尾）

来自 `docs/handoffs/2026-06-03-session-wrap.md` §Loose ends：

| Loose end | 归属 | 处理 |
|---|---|---|
| `DEP0190` 警告（Node 22+ `shell:true` + args 数组 deprecated） | 工程纪律 | 留 as-is。本地 node 路径含中文目录（`D:\辅助应用\node.js\node.exe`）拼字符串风险大于警告价值；无注入面。`docs/handoffs/2026-06-03-session-wrap.md:48` 已书面记录 |
| rag-eval-011 / pmid-40100009 跨语召回 loose end | 已处理（eval 数据审计） | 2026-06-04 已完成 eval corpus isolation + q011 审计：`pmid-40100009` 保留为合法英文视角，`chunk-pmid-40100009-staph` 纳入 expected chunks，microbiome bridge 补齐「微生态 / 皮肤微生态 / skin microbiome」；seed keyword bilingual cohort 当前 cross=1.0000 |
| `pnpm e2e` 非 per-commit gauntlet（CI 接入未做） | 工程纪律（CI 接入独立工作） | 不阻 MVP-A 出口；A4 验收只要求 `pnpm e2e` 本地可跑全绿 |
| 真实 provider 合同价格（price SLI baseline 用公开价格） | 非工程（业务/采购） | `docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md` 已书面记录"生产预算前需复核真实合同价格" |

## 阶段 B 入口准备

按 `docs/plans/2026-05-21-roadmap.md` §3.2 原规划：阶段 B（2026-06-05 → 2026-07-02，4 周）。

**B 阶段实际状态对账**：

| 原 slice | 当前状态 | 备注 |
|---|---|---|
| B1 LLM provider 接口抽象 | **大部分已落地** | `backend/app/services/llm/` 已含 `deterministic` / `mock_claude` / `opencode_go` 三 provider，`QIYAN_LLM_PROVIDER` env 切换可用；剩余仅 ADR 收尾 |
| B2 RAG eval 扩展到 50 题 | **已落地** | `backend/data/evals/rag_ad_eval_questions.json` 已扩展至 50 题 |
| B3 网络药理学任务壳（前后端） | **已落地** | `/api/network/analyze` + `/api/network/result/{task_id}` + `/network` 页面全栈 |
| B4 herb/compound/target/pathway sample 数据集 | **已落地** | `backend/data/network/sample_*.json` + `app/schemas/network_entities.py` |
| B5 RAG citation ↔ network entity 双向跳转 | **已落地** | citation 含 `related_entity_ids` + `/network` 节点指回 |
| B6 数据来源切换面板（合规） | **已落地并补 e2e** | `/literature` 已支持“全部来源 / PubMed 记录 / CNKI sample / 上传 PDF”四来源视图，`LiteratureDataSourceBanner` 随选择切换合规口径；PubMed 记录视图明示包含演示 seed，卡片/详情显示 `记录来源`；上传 PDF 视图走 `has_pdf_upload=true`；`frontend/e2e/literature-data-source.spec.ts` 锁定浏览器 → API 参数合同 |

**结论**：阶段 B 原 slice 大部分已在 cross-lingual / network 推进期间附带落地。

**下次 session 起手建议**（不强约束）：

1. **L2 governance**：BGE=0.3 + NLI=0.5 profile 是否可接受仍是治理决策；默认路径继续 deterministic。
2. **PostgreSQL/pgvector spike**：runtime SQLite 已落地，生产数据库路径可独立评估。
3. **PDF 抽取质量 spike**：OCR、表格重建或质量启发式可作为独立 spike，不扩进默认内部预览路径。
4. **内部 reviewer sign-off**：当前工程/e2e 基线可支撑内部预览，但正式医生/科研 reviewer 走查仍需单独记录，不能由自动化替代。

**已完成补记**：多语 embedding spike 三个 sub-slice 已于 2026-06-04 闭合，结论为 BGE-M3 不翻默认，仅保留 `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` env opt-in；随后 eval corpus isolation + q011 数据审计已把 seed keyword bilingual cohort 对账到 cross=1.0000。详见 `docs/evaluations/2026-06-04-multilingual-bge-m3-eval.md` 与 `docs/evaluations/2026-06-04-eval-corpus-isolation-and-rag-eval-011-audit.md`。

## 引用

- `docs/plans/2026-05-21-roadmap.md` — 原路线图（仍是路线唯一入口）
- `docs/handoffs/2026-06-03-session-wrap.md` — 阶段 A 最后一次 cross-lingual / e2e 工作 wrap
- `docs/handoffs/2026-06-04-a5-chinese-pdf-verification.md` — A5 closure
- `docs/handoffs/2026-06-04-internal-preview-baseline.md` — B6 数据来源 e2e + 内部预览基线收口
- `docs/adr/0010-module-roadmap.md` — MVP-A/B/C 模块边界
- `docs/adr/0012-real-llm-enablement.md` — L2 治理决策

---

**生效**：2026-06-04
