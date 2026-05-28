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

- 当前阶段：MVP-A 证据工作台基本可内部走查；MVP-B 网络药理学 mock 起步链路已落地；C 阶段 provider / retrieval / grounding 底座部分提前完成；2026-05-28 自动化内部预览基线已通过，人工 reviewer 走查仍待执行。
- 数据：本地 JSON seed + `backend/data/runtime/` 运行态副本；runtime state 是本地开发/演示状态，不是生产数据库，也不应回写 seed fixture。
- 文献：本地样本文献、PubMed 实时同步入口、上传 PDF 解析片段、chunk 与 50 题 AD RAG eval 数据集。
- RAG：默认 `deterministic` provider + `keyword` retrieval，返回 answer、citation cards、retrieval metadata、provider name、token usage、grounding metadata 字段与免责声明。
- LLM provider：`deterministic` 默认；`mock_claude` 用于离线 wiring 测试；`anthropic` 与 `opencode_go` 仅在显式本地 env 配置 key 后用于 smoke，失败时回退 deterministic；真实外部 provider 成功草稿会经过 structured claim grounding v3 校验，未按 claims JSON 输出、缺少允许证据 ID 或引用本次 citations 之外证据 ID 时会拦截展示。v3 是结构化引用声明与越界证据 ID 拦截，不是语义事实核验。
- Retrieval provider：`keyword` 默认；`vector` / `hybrid` 可通过 `QIYAN_RETRIEVAL_PROVIDER` 显式 opt-in；默认不启用真实 embedding 模型。
- PDF：本地上传存储；文本型 PDF 通过 `pypdf` 提供预览；扫描件/OCR 暂不支持，失败时回退到文件级占位说明。
- 网络药理学：`/api/network/analyze`、`/api/network/result/{task_id}`、`/api/network/entities` 与 `/network` 页面已可跑通 mock 分析任务、seed entity、citation/entity 双向跳转。
- 前端：Next.js App Router + React + Ant Design，页面包括 `/`、`/literature`、`/literature/[id]`、`/rag`、`/evals/rag-ad`、`/compliance`、`/network`。
- 默认运行不接入真实 LLM、真实 embedding 模型、pgvector、Neo4j、Celery、Redis、MinIO、NextAuth 或外部生产服务；外部服务只作为本地显式 smoke，不进入默认用户路径。

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

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Frontend:

```bash
cd frontend
pnpm test
pnpm typecheck
pnpm build
pnpm e2e
```

## 当前下一步候选

最新项目级状态见 `docs/handoffs/2026-05-28-internal-preview-feedback.md`，当前内部预览收口计划见 `docs/plans/2026-05-27-internal-preview-sprint.md`，自动化闭环记录见 `docs/evaluations/2026-05-28-internal-review-feedback.md`。近期候选方向包括：

1. 按 `docs/checklists/internal-preview-smoke.md` 完成真实内部 reviewer demo 走查，并把反馈记录到 `docs/evaluations/2026-05-28-internal-review-feedback.md`。
2. 用真实 PubMed 数据与真实中文 PDF 样本补充最小验收记录，但不把 OCR 扩进当前小切片。
3. 对真实 LLM 只做本地 smoke；structured claim grounding v3 已能拦截非 claims JSON、空 claims、缺失/未知证据 ID，但完整 provider-native tool-use citation grounding 与语义级 hallucination reject 完成前仍不默认开放。
4. 根据内部预览反馈，在完整 tool-use grounding、network report export、runtime JSON → SQLite/PostgreSQL spike 中选一条作为下一轮主线。
