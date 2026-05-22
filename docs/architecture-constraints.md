# 架构约束 — Harness Engineering 支柱二

> 本文件记录当前可运行骨架的开发约束。长期架构方向见 `docs/adr/`；当前事实源见 `docs/current-state.md`。

## 当前阶段边界

当前只做 MVP-A 证据工作台：文献检索、deterministic RAG、citation cards、PDF 上传与文本预览、RAG eval 和合规展示。

当前不提前接入：

- 真实 LLM / embedding
- PostgreSQL / pgvector
- Neo4j
- Celery / Redis / Flower
- MinIO / 外部对象存储
- NextAuth / 生产认证
- 网络药理学、分子对接或分子动力学真实计算

上述能力如需启动，应先写 ADR 或 slice plan，不应混入 UI polish、文档清理或小型 bugfix。

## 后端依赖方向

```text
api router → service → repository → data/runtime storage
                ↓
              schemas
```

规则：

- `backend/app/api/*.py` 只做路由、参数绑定和调用 service。
- `backend/app/services/*.py` 承载业务逻辑、ranking、parse result 与免责声明组合。
- `backend/app/repositories/*.py` 负责 seed/runtime 数据读取与写入。
- `backend/app/schemas/*.py` 定义 Pydantic 契约。
- API 层不直接读写 JSON 文件。
- Service 层不引入 FastAPI router 细节。
- seed 数据在 `backend/data/literature/`，运行态写入 `backend/data/runtime/`。

## 前端架构约束

当前前端是 Next.js App Router，目录在 `frontend/` 下：

```text
frontend/
├── app/          ← 路由层与页面组合
├── components/   ← 页面客户端组件与复用展示组件
├── lib/          ← API 客户端、UI helper、领域 helper
└── tests/        ← node:test + tsx 的轻量 source/contract tests
```

规则：

- 页面和组件保持现有 inline style / helper 风格，避免在小切片中引入新 styling layer。
- API 调用优先通过 `frontend/lib/api/` 客户端封装。
- 医学证据展示优先清晰、克制、可追溯，不做消费级健康 app 视觉风格。
- `/literature`、`/literature/[id]`、`/rag`、`/compliance` 的合规文案和 evidence hierarchy 不应被隐藏。

## 工具链约束

Backend:

```bash
cd backend
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest -q
```

Frontend:

```bash
cd frontend
pnpm test
pnpm typecheck
pnpm build
```

## 不可做规则

- ❌ 硬编码 API Key / Secret；只提交 `.env.example`。
- ❌ AI 输出缺少 `非诊断结论、需结合临床。` 免责声明。
- ❌ 将 `backend/uploads/` PDF 或 `backend/data/runtime/` 运行态 JSON 作为普通源码提交。
- ❌ 在未写计划/ADR 的情况下接入重基础设施或真实外部服务。
- ❌ 跳过类型检查和测试后提交行为代码。
- ❌ 把 `docs/archive/pre-dev-planning/` 中的早期规划当作当前实现边界。

## 环境

- 本地开发主事实源：WSL 路径 `/home/dyh2026/Projects/Tcm_tech`。
- Windows 副本或历史路径只在明确同步时使用。
- `backend/uploads/` 与 `backend/data/runtime/` 是本地运行态目录，可清空并重新生成。
