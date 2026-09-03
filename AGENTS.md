# AGENTS.md — Qiyan Nexus

> 本文件是项目地图层。当前事实源优先读 `docs/current-state.md`、`README.md`、`CONTEXT.md`、`docs/adr/` 与最新 handoff；历史规划已归档到 `docs/archive/pre-dev-planning/`。

## 仓库性质

项目已从纯规划阶段切换到可运行开发阶段。2026-07-11 起，唯一产品主轴是窄领域网络药理学自动化科研辅助；MVP-A 文献/PDF/RAG 能力作为证据服务层保留。网络药理学已具备 mock/live 任务壳、最小研究协议门禁、双侧离线 raw-artifact engineering provenance、owner-scoped 逐行人工 adjudication（2026-07-26 上线）与 source-bound 候选装配计划门禁（2026-08-02 上线），真实科研数据闭环仍未完成；真实 LLM / embedding / 生产数据库仍保持显式 opt-in 或后续 spike，不进入默认路径。2026-08 ADR-0018（Accepted，Gate 1-3 已确认）：在 ADR-0017 当前契约之上，把底层逻辑升级为组学策略，网络药理学为系统层核心，真实组学数据只作显式 opt-in 验证层；Gate 3 已选定转录组 GSE32924 并定义 `omics_validated` 证据等级，三个 Gate 均未写代码；Gate 3 实现计划已起草（`docs/plans/2026-09-03-gate3-omics-implementation-plan.md`，Draft 待研究者拍板 D-G3-A/D-G3-B 两个决策点，生效前不写 Gate 3 代码）。检索质量基线：Track A 首版 150 标签（precision@5=0.113、MRR@5=0.163）；2026-08-17 种子扩展 batch1-5 完成（总表 83 条查询，runtime 语料 344→693 pubmed_live），工程侧 v2 盲评迭代至 p@5=0.400、MRR@5=0.744（补记见 `docs/reports/2026-08-17-pubmed-seed-expansion-batch2-5-changelog.md`）；标签仍是工程侧，真人 domain reviewer 数字出现前不声称检索有效。至今没有任何真人 domain reviewer 判定记录，「能记录判定/装配」不等于「已有人判定」，`formal_network_ready` 恒 false。

当前代码目录：
- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口
- `spikes/` — 一次性技术 spike 归档（如 PDF 抽取器对比），不是产品代码

历史规划产物：
- `docs/archive/pre-dev-planning/` — 早期 Cursor / Trae / Word / HTML 原型归档，仅作历史参考，不作为当前实现事实源。

## 快速导航

| 层级 | 文件 | 读它来做什么 |
|------|------|-------------|
| 当前事实源 | `docs/current-state.md` | 当前能力边界、事实源优先级、标准验证命令 |
| 入口 | `README.md` | 每个已实现 endpoint 的 curl 示例 |
| 命令与架构细节 | `CLAUDE.md` | 后端分层、RAG 管线、PDF 流、前端测试机制、codegraph 决策树；若命令冲突，以本文件的 Windows PowerShell 写法为准 |
| 领域语言 | `CONTEXT.md` | TCM 术语表、共享语言 |
| 长期模块路线图 | `docs/adr/0010-research-workbench-module-roadmap.md`、`0017-network-pharmacology-first-product-contract.md`、`0018-omics-strategy-platform-contract.md` | 证据工作台、网络药理学、分子对接/MD 的分阶段边界与概念预留；0017 是当前产品主轴契约基线，0018 是组学策略方向演进 |
| 最近交接 | `docs/handoffs/` | 越新的 handoff 越接近当前事实，用于跨会话续接 |
| 开发计划 | `docs/plans/` | 已落地或待执行的纵向切片计划 |
| 质量 | `docs/quality-score.md` | 各领域质量评分 |
| 历史归档 | `docs/archive/pre-dev-planning/` | 早期需求、任务、设计、Word 文档与 HTML 原型，仅作追溯参考 |
| Agent 约定 | `docs/agents/` | 领域文档消费规则、本地 Markdown issue tracker（`.scratch/<feature-slug>/`）、triage 中文标签映射 |

## 代码结构查询

仓库已索引 `.codegraph/`（会话挂 codegraph MCP）：结构类问题（符号在哪、谁调用、改动影响面）先走 codegraph 工具而不是 grep 循环；CLAUDE.md 顶部有完整决策树与禁用场景（字面文本、日志、中文文案仍用 grep/Read）。

## 命令（本机是 Windows + pwsh，照抄）

后端 venv 是 `backend/.uv-test-venv`（不是 `.venv`），必须走 `Scripts\python.exe`。

```powershell
# 推荐：统一本地门禁（默认跑 backend 4 项 + frontend test/typecheck/build）
.\scripts\verify-local.ps1

# reviewer 走查或分支收口前追加 Playwright E2E
.\scripts\verify-local.ps1 -IncludeE2E

# 单侧门禁
.\scripts\verify-local.ps1 -BackendOnly
.\scripts\verify-local.ps1 -FrontendOnly
```

```powershell
# 后端验证门禁（提交前 4 项全绿）— 顺序：format -> lint -> type -> test
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q

# 单测 / 单用例
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_rag_service.py -q
& .\.uv-test-venv\Scripts\python.exe -m pytest "tests\test_rag_service.py::test_name" -q

# dev server (http://127.0.0.1:8000)
& .\.uv-test-venv\Scripts\fastapi.exe dev app/main.py
```

```powershell
# 前端（pnpm，期望后端在 127.0.0.1:8000）
cd frontend
pnpm test        # node --import tsx --test tests/*.test.ts，无 build 步
pnpm typecheck   # next typegen && tsc --noEmit（含 tests/）
pnpm build       # next build --webpack
node --import tsx --test tests\literature-api.test.ts   # 单测文件
```

```powershell
# 仓库根便捷脚本（package.json 代理到 frontend/ 或 scripts/）
pnpm dev           # frontend dev
pnpm dev:backend   # 直接用 uvicorn 起后端 127.0.0.1:8000（不是 fastapi dev）
pnpm preview       # = scripts\run-internal-preview.ps1（isolated runtime 起前后端）
pnpm preview:stop

# 内部预览 isolated runtime + API smoke（用法详见 docs/current-state.md）
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open
.\scripts\smoke-internal-preview.ps1
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-open -Stop
.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\trial-token -AccessToken "trial-token"
.\scripts\smoke-internal-preview.ps1 -AccessToken "trial-token"
```

- `pnpm e2e`（Playwright）不在每次提交门禁内，需先 `pnpm exec playwright install chromium` 及系统库，按 `frontend/e2e/README.md`。
- GitHub Actions CI 位于 `.github/workflows/ci.yml`，规则说明见 `.github/workflows/README.md`；没有 `.cursor` 规则。提交前仍必须本地手跑上述 PowerShell / pnpm 门禁，不能把远端 CI 当作首次验证。

## 改代码前必看的硬约束（测试会卡）

- 后端严格分层：`api/` → `services/` → `repositories/` → `schemas/`，不许跨层（router 不直接读 JSON，service 不 import FastAPI）。router 在 `app/main.py` 接线。
- CORS 限定 `localhost:3000`/`127.0.0.1:3000`，仅 `GET, POST`；加 `PUT`/`DELETE` 路由要改 `app/main.py` 中间件。
- 免责声明字符串 `非诊断结论、需结合临床。` 是 load-bearing，被后端测试、eval、前端断言引用，必须逐字节一致，不要改写 `services/rag.py` 的 `DISCLAIMER`。
- RAG 契约：`/api/rag/answer` 返回的每个 `citations[*].literature_id` 必须能被 `/api/literature/{id}` 解析（`test_rag_literature_contract.py`）。
- runtime 状态写在 `backend/data/runtime/`（gitignored），是本地开发态，不要回写 seed fixture，也不要把 runtime state / 上传的 PDF 当 fixture 提交。
- reviewer identity 只能来自 access token 验证后的 request state；受保护部署由可信 nginx 覆盖写入 `X-Qiyan-Reviewer`。禁止信任浏览器或任意客户端直传的 reviewer header，后端 8000 必须保持 loopback。
- network task 必须按 `task_id + owner_id` 查询和推进；foreign 或 legacy ownerless task 都要 fail closed。report GET 是只读观察接口，不得借读取推进状态或写 runtime。
- 派生 network task 的 parent link 也是授权边界：必须通过同 owner 的查询解析，`source_task_id` 要跨 JSON/SQLite/PostgreSQL、result、report 持久化且不可变，禁止 self-link 与 child-of-child。缺少 link 的 legacy child 在 result/report/export 读取时只返回非持久化失败投影，不得由读取修复或推进。
- 靶点集合必须失败关闭：`disease_targets`、`compound_targets`、`intersection_targets` 分开建模；没有独立疾病靶点来源时 disease/intersection 必须为空，禁止从 compound set 自造交集。同一 canonical symbol 的不同 source record 保留多行，unique target count 与 lineage row count 分开；自动抽取不得冒充人工 adjudication。`disease_target_import` 在 task 创建时封存且不可后改：旧 `/api/network/analyze` 客户端导入固定为 `unverified_client_import`；`server_verified_raw_artifact` 只能由受支持的离线 raw artifact（当前为 Open Targets GraphQL 疾病数据或 `chembl_known_activity_v1` ChEMBL 成分数据）经服务端 SHA-256、operator-controlled trusted manifest 与服务端 parser 派生。客户端不得提交 records/hash/provenance/readiness/判定字段，multipart 外层也必须 strict allowlist；该中间态不得命名为 `verified`，且不得翻转 `formal_network_ready`。intersection 必须是一条/unique symbol 的服务端派生 row，并完整引用两侧匹配 lineage row IDs。
- 双侧 raw artifact 只建立冻结 snapshot，不自动授权下游网络结论。compound child 必须跳过 provider、机制链、PPI、通路与 enrichment，保持 `chains=[]`、`enrichment=null` 和明确的 network-assembly blocker；独立 validator、report 与 UI 必须共同执行该 snapshot-only 边界。
- 人工判定是与冻结快照平行的 append-only 审计流，不属于快照：projection 挂在结果响应信封而非 `NetworkAnalysisResult`，同一 lineage row 多次判定按 latest-wins 投影，`reviewer_id` 持久化但从不回投，且结构上不得翻转 `formal_network_ready`。冻结 lineage row 的 `adjudication_status` / `decision` 不由该审计流回写。「能记录判定」不等于「已有人判定」，更不等于科学有效。
- source-bound 装配门禁只证明「装配输入已封存」，不生成网络结论、不授权任何 writer、不翻转 `formal_network_ready`：`POST /api/network/result/{task_id}/assembly-plans` 产出不可变候选装配计划（确定性 plan_id + 协议/父子任务/双侧 artifact/冻结 lineage/判定快照全量绑定 hash），计划封存与判定流在 repository 锁内原子绑定（评估期间追加判定返回 `conflict`）；旧计划 append-only 默认不可执行，writer 消费契约尚未定义。独立 validator `backend/scripts/validate_network_assembly_plan.py` 与 producer 零共享代码，改 plan 结构时必须让它对每一种篡改继续拒绝。
- SQLite network-task repository 的锁按 canonical DB path 在单进程内共享；literature/chunk 仍是实例级锁。两者都不提供多 worker exactly-once；若引入多进程，必须先设计数据库 claim/lease 或等价原子协议。共享行上任何新增 read-modify-write 必须复用邻近方法已有的 CAS + 重试（`advance()`、`append_adjudication()` 即例），同文件已有的守卫就是需求；并发测试必须能观测到它声称覆盖的竞态——同进程两个 repository 实例共享 path lock，去掉守卫后仍会通过，必须显式制造交错并做变异验证。
- 写操作与其后用于刷新界面的读取必须分开捕获错误。共用一个 `catch` 会把已落库的写报成失败，在 append-only 审计域里会诱导重试并污染历史。
- 跨端字段的位置必须两侧各有断言。后端放在响应信封、前端从嵌套快照读取时不会有任何报错，只会静默显示 0。
- 门禁全红时先排除工具链再改代码：pnpm 写绝对 symlink，仓库目录一旦移动，前端依赖全部悬空、前端门禁全红且与 diff 无关，需 `rm -rf frontend/node_modules && pnpm install --frozen-lockfile`；`.next` 缓存同样含迁移前绝对路径，目录移动后 dev/E2E 会出现与 diff 无关的间歇性失败（如 Playwright `networkidle` 超时），需一并 `rm -rf frontend/.next`。判断某条失败是否既有，用 `git stash` 清空改动后复跑确认，且复跑必须处于干净工具链（已重装依赖、已清缓存），不要凭印象归因。
- 启动外部进程时传结构化 argv，禁止拼接 `PowerShell -Command` 或 curl config/header 字符串；端口和凭证参数必须先校验。
- PDF 流分两步：`POST /api/uploads/pdf` 只落盘并置 `pending`，要单独调 `POST /api/uploads/pdf/auto-parse` 才推进到 `parsed`/`failed`；upload endpoint 不做重解析。
- 前端测试套件（`frontend/tests/`，40+ 个测试文件）里有 4 个源码断言测试（`pdf-upload-status`、`literature-detail-meta`、`client-section-consistency`、`page-shell-consistency`）用 `readFileSync` 对 `.tsx` 源码做正则断言；改页面壳、导航或可见 meta 文案时最容易挂这几个。
- 后端 mypy `strict=true` 仅作用于 `app/`（tests 排除）；`B008` 全局忽略，因为 FastAPI 用 `Body()`/`Form()`/`File()`/`Query()` 当默认值。
- eval 数据集是 50 题（`backend/data/evals/rag_ad_eval_questions.json`），不要按历史文档里的 20 题口径规划。
- 检索排序预期是调参产物，不是随手可修的失败：改 `services/retrieval/provider.py` 评分（字段加权 title=3/keywords=2/abstract=1、IDF 加权、多字术语词典）、`backend/data/retrieval/cjk_medical_terms.json` 或 `cross_lingual_terms.json` 会改变 citation 排序；`test_rag_service.py`、`test_rag_api.py`、`test_cross_lingual_eval.py` 的预期顺序对应 Track A/A+ 实测基线（MRR@5 0.268）——该基线对应 seed fixture 上的确定性检索，扩展语料只存在于 gitignored runtime state，不进测试语料，测试预期不受 v6 数字影响——调整时必须说明对基线的影响，不得为过测试而抹平排序。

## 已冻结的技术决策

项目当前采用小步可验证的内部预览边界：前端是 Next.js / React / Ant Design，后端是 FastAPI / Pydantic；默认使用本地 JSON seed、runtime state、可选 SQLite runtime backend 与 deterministic retrieval，不提前接入 PostgreSQL、pgvector、Neo4j、Celery、Redis、MinIO、真实 LLM 或真实 embedding。上述重依赖保留为后续阶段的架构方向或显式 spike，而不是当前默认实现要求。

## 产品边界

- 病种仅特应性皮炎；用户仅医生/科研人员端；不替代诊断；不自训大模型
- 产品主轴是网络药理学科研项目；文献检索、PDF、RAG 与引用导出必须服务于研究项目、靶点、通路、网络边或科研 claim
- network task 必须携带明确表型、`Homo sapiens`、证据策略与查询日期；缺少来源版本、阈值或逐边人工判定时 `formal_network_ready=false`
- 所有 AI 输出必须带 "非诊断结论、需结合临床" 免责声明
- 视觉：青黛绿主色 `#0d9488`~`#14b8a6`，浅色产品端，Noto Sans SC

## 语言约定

文档/需求用简体中文。代码变量/函数/API 端点用英文，注释可中英混合。

## 当前开发原则

- 小步提交：先健康检查、配置、页面壳，再接真实业务能力
- TDD：行为代码先写测试，确认失败，再实现
- 不提前接入真实 AI API、Embedding 模型、Neo4j、支付等重依赖
- Secret 不进仓库，只写 `.env.example`
- 长期科研模块按阶段推进：先完成网络药理学协议、lineage、独立复算与小规模真实闭环；证据服务层按网络研究对象绑定；MVP-C 分子对接/分子动力学模拟目前只做 schema 概念预留
