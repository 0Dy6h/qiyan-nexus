# Qiyan Nexus

面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台。

当前状态：已从纯规划仓库切换到开发骨架启动阶段。当前已有两个后端纵向切片：文献检索使用本地 JSON 样本文献库 + repository 层 + FastAPI 搜索接口；RAG mock endpoint 返回带引用卡片的合规问答响应。前端 `/literature` 页面已通过浏览器端 API client 调用文献检索后端，RAG 前端后续再做。

正式命名建议见 `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`。短期仓库目录仍保留为 `/home/dyh2026/projects/Tcm_tech`，避免破坏已有路径和脚本。

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

文献检索 API 数据来源：

- 样本文献 JSON：`backend/data/literature/sample_ad_literature.json`
- repository 层：`backend/app/repositories/literature.py`
- service 层：`backend/app/services/literature.py`

文献检索 mock API：

```bash
curl "http://127.0.0.1:8000/api/literature/search?q=特应性皮炎"
```

RAG mock API：

```bash
curl -X POST "http://127.0.0.1:8000/api/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{"question":"特应性皮炎和肠-脑-皮肤轴有什么关系？"}'
```

当前 RAG endpoint 只返回 mock answer + citation cards + “非诊断结论、需结合临床”免责声明，不接真实 LLM、embedding、pgvector 或外部服务。

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
