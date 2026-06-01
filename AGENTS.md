# AGENTS.md — Qiyan Nexus

> 本文件是项目地图层。当前事实源优先读 `docs/current-state.md`、`README.md`、`CONTEXT.md`、`docs/adr/` 与最新 handoff；历史规划已归档到 `docs/archive/pre-dev-planning/`。

## 仓库性质

项目已从纯规划阶段切换到开发骨架启动阶段。

当前代码目录：
- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口

历史规划产物：
- `docs/archive/pre-dev-planning/` — 早期 Cursor / Trae / Word / HTML 原型归档，仅作历史参考，不作为当前实现事实源。

## 快速导航

| 层级 | 文件 | 读它来做什么 |
|------|------|-------------|
| 当前事实源 | `docs/current-state.md` | 当前能力边界、事实源优先级、标准验证命令 |
| 入口 | `README.md` | 每个已实现 endpoint 的 curl 示例 |
| 命令与架构细节 | `CLAUDE.md` | 后端分层、RAG 管线、PDF 流、前端测试机制（注意其命令用 Linux 路径，本机需换成下方 PowerShell 写法） |
| 领域语言 | `CONTEXT.md` | TCM 术语表、共享语言 |
| 长期模块路线图 | `docs/adr/0010-research-workbench-module-roadmap.md` | 证据工作台、网络药理学、分子对接/MD 的分阶段边界与概念预留 |
| 最近交接 | `docs/handoffs/` | 越新的 handoff 越接近当前事实，用于跨会话续接 |
| 开发计划 | `docs/plans/` | 已落地或待执行的纵向切片计划 |
| 质量 | `docs/quality-score.md` | 各领域质量评分 |
| 历史归档 | `docs/archive/pre-dev-planning/` | 早期需求、任务、设计、Word 文档与 HTML 原型，仅作追溯参考 |

## 命令（本机是 Windows + pwsh，照抄）

后端 venv 是 `backend/.uv-test-venv`（不是 `.venv`），必须走 `Scripts\python.exe`。CLAUDE.md 里的 `.venv/bin/...` 是 Linux 写法，本机会失败。

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

- `pnpm e2e`（Playwright）不在每次提交门禁内，需先 `pnpm exec playwright install chromium` 及系统库，按 `frontend/e2e/README.md`。
- 没有 CI、没有 `opencode.json`、没有 `.cursor` 规则；门禁靠本地手跑上述命令。

## 改代码前必看的硬约束（测试会卡）

- 后端严格分层：`api/` → `services/` → `repositories/` → `schemas/`，不许跨层（router 不直接读 JSON，service 不 import FastAPI）。router 在 `app/main.py` 接线。
- CORS 限定 `localhost:3000`/`127.0.0.1:3000`，仅 `GET, POST`；加 `PUT`/`DELETE` 路由要改 `app/main.py` 中间件。
- 免责声明字符串 `非诊断结论、需结合临床。` 是 load-bearing，被后端测试、eval、前端断言引用，必须逐字节一致，不要改写 `services/rag.py` 的 `DISCLAIMER`。
- RAG 契约：`/api/rag/answer` 返回的每个 `citations[*].literature_id` 必须能被 `/api/literature/{id}` 解析（`test_rag_literature_contract.py`）。
- runtime 状态写在 `backend/data/runtime/`（gitignored），是本地开发态，不要回写 seed fixture，也不要把 runtime state / 上传的 PDF 当 fixture 提交。
- PDF 流分两步：`POST /api/uploads/pdf` 只落盘并置 `pending`，要单独调 `POST /api/uploads/pdf/auto-parse` 才推进到 `parsed`/`failed`；upload endpoint 不做重解析。
- 前端 4 个测试（`pdf-upload-status`、`literature-detail-meta`、`client-section-consistency`、`page-shell-consistency`）用 `readFileSync` 对 `.tsx` 源码做正则断言；改页面壳、导航或可见 meta 文案时最容易挂这几个。
- 后端 mypy `strict=true` 仅作用于 `app/`（tests 排除）；`B008` 全局忽略，因为 FastAPI 用 `Body()`/`Form()`/`File()`/`Query()` 当默认值。
- eval 数据集是 50 题（`backend/data/evals/rag_ad_eval_questions.json`），CLAUDE.md 里写的 "20-question" 已过时。

## 已冻结的技术决策

项目当前采用小步可验证的 MVP-A 边界：前端是 Next.js / React / Ant Design，后端是 FastAPI / Pydantic；本阶段使用本地 JSON seed、runtime state 与 deterministic retrieval，不提前接入 PostgreSQL、pgvector、Neo4j、Celery、Redis、MinIO、真实 LLM 或 embedding。上述重依赖保留为后续阶段的架构方向，而不是当前实现要求。

## 产品边界

- 病种仅特应性皮炎；用户仅医生/科研人员端；不替代诊断；不自训大模型
- 所有 AI 输出必须带 "非诊断结论、需结合临床" 免责声明
- 视觉：青黛绿主色 `#0d9488`~`#14b8a6`，浅色产品端，Noto Sans SC

## 语言约定

文档/需求用简体中文。代码变量/函数/API 端点用英文，注释可中英混合。

## 当前开发原则

- 小步提交：先健康检查、配置、页面壳，再接真实业务能力
- TDD：行为代码先写测试，确认失败，再实现
- 不提前接入真实 AI API、Embedding 模型、Neo4j、支付等重依赖
- Secret 不进仓库，只写 `.env.example`
- 长期科研模块按阶段推进：当前只做证据工作台 MVP-A；网络药理学为 MVP-B；分子对接/分子动力学模拟为 MVP-C；当前只做 herb、formula、compound、target、pathway、disease、protein、ligand、simulation_task 等概念预留，不接真实重计算
