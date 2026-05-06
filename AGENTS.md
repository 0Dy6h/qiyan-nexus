# AGENTS.md — Qiyan Nexus

> 本文件是项目地图层。详细知识存放在 `docs/`、`CONTEXT.md` 和历史规划目录中。

## 仓库性质

项目已从纯规划阶段切换到开发骨架启动阶段。

当前代码目录：
- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口

历史规划产物：
- `Cursordos/` — Cursor 驱动的规划（前端设计、排期脚本、HTML 原型）
- `Traedos/` — Trae 驱动的规划（`.trae/specs/` 内含 spec、tasks、checklist）

## 快速导航

| 层级 | 文件 | 读它来做什么 |
|------|------|-------------|
| 入口 | `README.md` | 本地启动、测试、目录说明 |
| 领域语言 | `CONTEXT.md` | TCM 术语表、共享语言 |
| 需求 | `Traedos/.trae/specs/tcm-platform-mvp/spec.md` | 产品需求、验收标准 |
| 任务 | `Traedos/.trae/specs/tcm-platform-mvp/tasks.md` | 8 大实现任务 + 依赖 + 测试要求 |
| 验证 | `Traedos/.trae/specs/tcm-platform-mvp/checklist.md` | 验证清单 |
| 设计 | `Cursordos/docs/tcm-platform-frontend-design.md` | 信息架构、色彩/字体、合规交互 |
| 质量 | `docs/quality-score.md` | 各领域质量评分 |
| 开发计划 | `docs/plans/2026-05-06-first-week-dev-start.md` | 第一周开发启动计划 |

## 已冻结的技术决策

- **前端**: Next.js + React + Ant Design + AntV G6
- **后端**: FastAPI + Pydantic（Python 3.11+）
- **数据**: PostgreSQL + pgvector（向量），Neo4j Aura（图谱）
- **异步**: Celery + Redis + Flower；对象存储 MinIO（本地 Docker Compose，S3 兼容）
- **认证**: NextAuth.js + 魔法链接 + 邀请白名单
- **AI**: DeepSeek（日常问答）+ Claude Sonnet（医学推理与报告），按 endpoint 硬编码路由
- **Embedding**: text2vec-base-chinese + PubMedBERT（中英分流）

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
