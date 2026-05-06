# 岐研枢明日续接计划

> For Hermes: 明天继续时，先读 `AGENTS.md`、`CONTEXT.md`、本文件、`docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`、`docs/adr/0009-前端实际版本基线与AntDesign使用策略.md`。

Goal: 按“岐研枢 / Qiyan Nexus”新方案继续，把项目从命名与评估收口推进到“真实文献样本库 + repository 抽取”的下一条纵向切片。

Architecture: 保持 monorepo。短期仓库目录仍叫 `Tcm_tech`，产品展示名使用“岐研枢”。下一步只替换文献 mock 数据的数据来源与代码结构，不接 PostgreSQL、pgvector、Neo4j、Celery、真实 LLM 或 embedding 模型。

Tech Stack: FastAPI + pytest；Next.js 16 + React 19 + Ant Design 6（实际基线）；node:test；Markdown docs。

---

## 当前已完成并已验证

### 评估与命名

已新增评估报告：
- `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`

推荐产品名：
- 中文名：岐研枢
- 英文名：Qiyan Nexus
- MVP 副标题：AD 中医药证据与科研工作台

核心定位从“中医药精准诊疗与科研一体化平台”收敛为：
- 面向特应性皮炎（AD）医生与科研人员的中医药证据与科研工作台
- 少说诊疗，多说证据、科研、辅助、工作台

### 已应用的小改动

已修改：
- `README.md`：标题与定位改为“岐研枢（Qiyan Nexus）”
- `AGENTS.md`：标题改为“岐研枢（Qiyan Nexus）”
- `frontend/app/page.tsx`：首页展示名改为“岐研枢 · AD 专病科研工作台”
- `frontend/app/layout.tsx`：metadata 改为“岐研枢 Qiyan Nexus”
- `backend/app/main.py`：FastAPI title 改为 “Qiyan Nexus API”
- `backend/app/core/config.py`：默认 app_name 改为 “Qiyan Nexus API”
- `backend/.env.example`：APP_NAME 改为 “Qiyan Nexus API”
- `backend/tests/test_config.py`：同步测试期望
- `backend/pyproject.toml`：description 改为 “FastAPI backend for Qiyan Nexus”
- `docs/plans/2026-05-06-first-week-dev-start.md`：标题和 app_name 文案同步
- `docs/quality-score.md`：从“规划期 · 无代码”更新为“开发骨架启动期”评分

新增：
- `docs/adr/0009-前端实际版本基线与AntDesign使用策略.md`
- `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`
- `docs/plans/2026-05-07-literature-data-slice.md`（本文件）

### 验证结果

已执行并通过：

```bash
cd backend && .venv/bin/python -m pytest -q
# 15 passed
```

```bash
cd frontend && pnpm test && pnpm build
# 3 tests passed
# Next.js production build passed
```

---

## 明天优先目标

明天只做一个目标：把文献检索从硬编码 `_SAMPLE_ITEMS` 过渡到“本地样本文献数据 + repository 层”。

不要扩展到：
- PostgreSQL / pgvector
- Neo4j
- Celery
- PDF 解析
- 真实 RAG
- 真实 LLM API
- 真实 embedding 模型

---

## Success Criteria

完成后应满足：

1. 文献样本数据放到独立 JSON 文件。
2. 后端 service 不再直接维护 `_SAMPLE_ITEMS`。
3. 存在可测试的 repository 层。
4. `/api/literature/search` 行为保持不变或只增加合理字段。
5. 后端测试通过：`cd backend && .venv/bin/python -m pytest -q`。
6. 前端测试与构建通过：`cd frontend && pnpm test && pnpm build`。
7. 不引入数据库和外部服务依赖。

---

## Task 1: 固化当前命名与评估改动

Objective: 明天开工前先确认今天的评估、命名和文档改动都在工作区中，避免覆盖。

Files:
- Read: `docs/evaluations/2026-05-06-project-evaluation-and-optimization.md`
- Read: `docs/adr/0009-前端实际版本基线与AntDesign使用策略.md`
- Read: `README.md`
- Read: `AGENTS.md`

Steps:
1. 运行 `git status --short`，确认上述文件仍在改动列表中。
2. 运行后端测试。
3. 运行前端测试与构建。
4. 如果全部通过，可先提交当前命名和评估改动。

Suggested commit:

```bash
git add AGENTS.md README.md backend/.env.example backend/app/core/config.py backend/app/main.py backend/pyproject.toml backend/tests/test_config.py docs/adr/0009-前端实际版本基线与AntDesign使用策略.md docs/evaluations/2026-05-06-project-evaluation-and-optimization.md docs/plans/2026-05-06-first-week-dev-start.md docs/quality-score.md frontend/app/layout.tsx frontend/app/page.tsx
git commit -m "docs: rename project to qiyan nexus and record evaluation"
```

Do not commit if tests fail.

---

## Task 2: 创建文献样本 JSON

Objective: 把当前 mock 文献数据从 Python service 移到独立数据文件，为后续真实文献导入做准备。

Files:
- Create: `backend/data/literature/sample_ad_literature.json`
- Modify later: `backend/app/services/literature.py`
- Test later: `backend/tests/test_literature_repository.py`

Data shape:

```json
[
  {
    "id": "cn-ad-gbs-001",
    "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
    "authors": ["样本作者"],
    "language": "zh",
    "source_type": "cn_literature",
    "source": "中文本地样本文献库",
    "year": 2025,
    "keywords": ["特应性皮炎", "肠-脑-皮肤轴", "中医证候"],
    "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。"
  },
  {
    "id": "en-ad-barrier-001",
    "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
    "authors": ["Sample Author"],
    "language": "en",
    "source_type": "pubmed",
    "source": "PubMed sample",
    "year": 2024,
    "keywords": ["atopic dermatitis", "skin barrier", "immune pathways"],
    "snippet": "A sample English literature record for AD barrier and immune pathway retrieval."
  }
]
```

Verification:
- JSON must parse.
- Keep current fields used by frontend: `id`, `title`, `language`, `source_type`, `source`, `year`, `snippet`.

---

## Task 3: 新增 repository 层

Objective: 用 repository 封装样本文献加载与筛选，service 只负责业务排序和 response 组装。

Files:
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/literature.py`
- Test: `backend/tests/test_literature_repository.py`

Suggested API:

```python
from pathlib import Path
from app.schemas.literature import LiteratureItem

class InMemoryLiteratureRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path

    def list_items(self) -> list[LiteratureItem]:
        ...
```

Test cases:
1. loads all sample items from JSON
2. exposes required fields
3. fails clearly if JSON is malformed or missing required fields（只测 Pydantic validation 即可，不要写复杂异常封装）

Verification:

```bash
cd backend && .venv/bin/python -m pytest tests/test_literature_repository.py -q
```

Expected: pass.

---

## Task 4: service 改用 repository

Objective: 保持 `/api/literature/search` 行为稳定，把数据来源替换为 repository。

Files:
- Modify: `backend/app/services/literature.py`
- Test: `backend/tests/test_literature_service.py`
- Test: `backend/tests/test_literature_search.py`

Steps:
1. 先运行现有测试确认 baseline。
2. 修改 service，让 `search_literature` 从 repository 读取 items。
3. 保持中文 query 优先中文文献、英文 query 优先 PubMed。
4. 保持 source 过滤逻辑。
5. 运行后端全量测试。

Verification:

```bash
cd backend && .venv/bin/python -m pytest -q
```

Expected: 15+ tests passed。

---

## Task 5: 前端兼容新增字段但不扩大 UI

Objective: 如果后端 schema 增加 authors/keywords，前端类型可同步；但 UI 不必展开复杂展示。

Files:
- Modify if needed: `frontend/lib/api/literature.ts`
- Modify if needed: `frontend/lib/api/literature.mjs`
- Modify if needed: `frontend/tests/literature-api.test.mjs`

Rule:
- 只同步类型或字段解析。
- 不重做页面设计。
- 不引入复杂 AntD 组件。

Verification:

```bash
cd frontend && pnpm test && pnpm build
```

Expected: tests and build pass。

---

## Task 6: 更新文档和 wiki

Objective: 完成文献数据切片后，把事实源更新到 README/wiki，方便后续继续。

Files:
- Modify: `README.md`
- Modify: `~/.hermes/wiki/projects/Tcm_tech.md`
- Modify or create: `~/.hermes/wiki/notes/2026-05-07-Tcm_tech-文献数据切片记录.md`

Content should include:
- 新增 sample JSON 路径
- repository 层路径
- 当前验证命令与结果
- 下一步建议：文献详情页或 RAG mock endpoint

Verification:

```bash
python3 ~/.hermes/wiki/wiki_tool.py index
```

---

## 明天结束时建议状态

理想结束状态：
- 当前命名/评估改动已提交一次。
- 文献数据 repository 切片已提交一次。
- 后端与前端验证全部通过。
- wiki 已更新。

建议提交顺序：
1. `docs: rename project to qiyan nexus and record evaluation`
2. `feat: load literature samples through repository`
3. `docs: record literature data slice handoff`
