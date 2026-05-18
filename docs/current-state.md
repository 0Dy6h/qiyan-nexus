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

- 当前阶段：MVP-A 证据工作台。
- 数据：本地 JSON seed + `backend/data/runtime/` 运行态副本。
- 文献：本地样本文献、chunk 与 eval 数据集。
- RAG：deterministic retrieval，返回 answer、citation cards、retrieval metadata 与免责声明。
- PDF：本地上传存储；文本型 PDF 通过 `pypdf` 提供预览；扫描件/OCR 暂不支持，失败时回退到文件级占位说明。
- 前端：Next.js App Router + React + Ant Design，页面包括 `/`、`/literature`、`/literature/[id]`、`/rag`、`/evals/rag-ad`、`/compliance`。
- 暂不接入真实 LLM、embedding、pgvector、Neo4j、Celery、Redis、MinIO、NextAuth 或外部生产服务。

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

## 当前下一步候选

最新项目级状态见 `docs/handoffs/` 与 Hermes wiki 项目页。近期候选方向包括：

1. 用真实 PubMed 数据替换部分合成样本文献。
2. 评估更高质量的中文 PDF 文本抽取，但不把 OCR 扩进当前小切片。
3. 改善 PDF 上传后解析状态刷新体验。
4. 继续收敛 `/rag`、`/literature`、`/compliance` 的演示数据提示与合规展示。
