# 岐研枢（Qiyan Nexus）

面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。

当前状态：已从纯规划仓库切换到开发骨架启动阶段。当前已有第一个文献检索端到端切片：后端 mock API + 前端浏览器端 API 调用页面。

正式命名建议见 `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`。短期仓库目录仍保留为 `Tcm_tech`，避免破坏已有路径和脚本。

## 目录

- `frontend/` — Next.js 前端应用
- `backend/` — FastAPI 后端应用
- `infra/` — 本地基础设施说明与后续 Docker Compose 入口
- `docs/` — 规划、ADR、设计与开发计划
- `Traedos/`、`Cursordos/` — 历史 AI 工具链规划产物

## 后端

首次安装：

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .
```

运行测试：

```bash
cd backend
.venv/bin/python -m pytest -q
```

启动开发服务：

```bash
cd backend
.venv/bin/fastapi dev app/main.py
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

文献检索 mock API：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=特应性皮炎"
```

## 前端

首次安装：

```bash
cd frontend
pnpm install
```

构建验证：

```bash
cd frontend
pnpm build
```

启动开发服务：

```bash
cd frontend
pnpm dev
```

前端 API 地址默认是 `http://127.0.0.1:8000`。如需覆盖：

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev
```

前端测试：

```bash
cd frontend
pnpm test
```

页面：

- 首页：`/`
- 文献检索页：`/literature`

## 合规底线

所有 AI 输出必须带：

非诊断结论、需结合临床。

本平台不替代医生诊断，不面向普通患者 C 端。
