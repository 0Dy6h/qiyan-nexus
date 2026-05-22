# Qiyan Nexus 第一周开发启动计划

> For Hermes: use TDD for behavior code. This plan intentionally starts small: create runnable skeletons, health checks, and a local dev baseline before implementing domain features.

Goal: 将项目从纯规划仓库切换为可运行的前后端工程骨架，并完成第一周最小开发闭环。

Architecture: 采用 monorepo。前端放在 `frontend/`，后端放在 `backend/`，基础设施放在 `infra/`。第一周只建立可运行骨架、健康检查、配置样例和最小测试，不实现 RAG、Embedding、Neo4j、Celery 业务逻辑。

Tech Stack: Next.js 15 + React + Ant Design 5；FastAPI + Pydantic v2；pytest；Docker Compose later for PostgreSQL/Redis/MinIO.

---

## Assumptions

- 用户已批准删除旧的架构约束文件，并从规划阶段切换到开发阶段。
- 当前 WSL 环境有 Node 22、npm、pnpm、Python 3.13。项目文档写的是 Python 3.11+，3.13 满足“+”，但部分 ML/Embedding 包未来可能需要降到 3.11/3.12。
- 第一周目标不是做完整 MVP，而是建立“能跑、能测、可迭代”的工程地基。

## Success Criteria

- `docs/architecture-constraints.md` 已删除。
- 项目根目录出现 `frontend/`、`backend/`、`infra/`、`docs/plans/`。
- 后端健康检查可由测试验证。
- 前端最小页面可构建或至少可通过静态 lint/type baseline。
- 根目录 README 说明如何启动前后端。

---

## Task 1: 后端最小 FastAPI 骨架

Objective: 建立可测试的 FastAPI app，并提供 `/health`。

Files:
- Create: `backend/app/main.py`
- Create: `backend/app/__init__.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/pyproject.toml`

Steps:
1. 写测试 `backend/tests/test_health.py`：请求 `/health` 应返回 200 和 `{"status":"ok","service":"qiyan-nexus-api"}`。
2. 运行 `cd backend && python3 -m pytest tests/test_health.py -v`，预期失败，因为 app 不存在。
3. 创建 `backend/app/main.py`，实现最小 FastAPI app 和 health endpoint。
4. 运行 `cd backend && python3 -m pytest tests/test_health.py -v`，预期通过。

Verification:
- `cd backend && python3 -m pytest -q`

---

## Task 2: 后端配置样例

Objective: 明确后端环境变量入口，但不接真实外部服务。

Files:
- Create: `backend/.env.example`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/tests/test_config.py`

Steps:
1. 写测试：默认配置中 `app_name == "Qiyan Nexus API"`，`environment == "dev"`。
2. 运行单测，预期失败。
3. 用 Pydantic Settings 或简单 dataclass 实现最小配置。为避免额外依赖，第一版用 dataclass + os.getenv。
4. 写 `.env.example`，只列变量名，不写任何 secret。
5. 运行后端测试，预期通过。

Verification:
- `cd backend && python3 -m pytest -q`

---

## Task 3: 前端最小 Next.js 骨架

Objective: 建立最小 Next.js app shell，首页显示项目名与合规短句。

Files:
- Create under `frontend/` using pnpm/npm scaffold or hand-written minimal package.
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`

Steps:
1. 创建最小 Next.js 项目结构。
2. 首页显示：`Qiyan Nexus`。
3. 首页显示免责声明：`非诊断结论、需结合临床`。
4. 安装或声明依赖：Next.js 15、React、React DOM、Ant Design。
5. 运行 `cd frontend && pnpm next --version` 或 `pnpm build` 做基础验证。

Verification:
- `cd frontend && pnpm install`
- `cd frontend && pnpm build`

---

## Task 4: 根目录开发说明

Objective: 让下一位开发者能从 README 直接知道怎么跑。

Files:
- Create or Modify: `README.md`

Content must include:
- 项目定位
- 当前阶段：开发骨架启动
- 后端启动命令
- 前端启动命令
- 测试命令
- 合规免责声明要求

Verification:
- 人工阅读 README，确认路径和命令与实际文件一致。

---

## Task 5: 基础 infra 占位

Objective: 创建 infra 目录和后续 Docker Compose 入口，但第一步不强行接数据库。

Files:
- Create: `infra/README.md`
- Optionally Create: `infra/docker-compose.yml` only if immediately验证可运行。

Scope:
- 第一周先记录未来服务：PostgreSQL + pgvector、Redis、MinIO、Flower。
- 不在没有验证的情况下承诺 docker compose 已可用。

Verification:
- `infra/README.md` 说明当前状态是 placeholder。

---

## Task 6: 更新项目地图

Objective: 项目已从规划期切入开发期，更新 AGENTS.md 避免继续误导。

Files:
- Modify: `AGENTS.md`

Required changes:
- 移除“纯规划阶段，无任何应用代码”的绝对表述。
- 记录当前代码目录：`frontend/`、`backend/`、`infra/`。
- 保留产品边界与技术决策。
- 移除指向已删除 `docs/architecture-constraints.md` 的导航。

Verification:
- `grep -n "architecture-constraints\|纯规划阶段\|不应生成 src" AGENTS.md` 不应再出现旧约束。

---

## Not This Week

- 不接真实 DeepSeek / Claude API。
- 不下载 Embedding 模型。
- 不实现 RAG。
- 不接 Neo4j Aura。
- 不实现 NextAuth 魔法链接。
- 不做付费导出。

这些都依赖更稳定的工程地基和 secret 管理。
