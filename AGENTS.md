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
| 入口 | `README.md` | 本地启动、测试、目录说明 |
| 领域语言 | `CONTEXT.md` | TCM 术语表、共享语言 |
| 长期模块路线图 | `docs/adr/0010-research-workbench-module-roadmap.md` | 证据工作台、网络药理学、分子对接/MD 的分阶段边界与概念预留 |
| 最近交接 | `docs/handoffs/` | 越新的 handoff 越接近当前事实，用于跨会话续接 |
| 开发计划 | `docs/plans/` | 已落地或待执行的纵向切片计划 |
| 质量 | `docs/quality-score.md` | 各领域质量评分 |
| 历史归档 | `docs/archive/pre-dev-planning/` | 早期需求、任务、设计、Word 文档与 HTML 原型，仅作追溯参考 |

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
