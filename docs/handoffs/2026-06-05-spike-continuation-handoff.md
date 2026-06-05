# 2026-06-05 Spike Continuation Handoff

date: 2026-06-05  
session: continuation  
status: completed

---

## 背景

继续完成两个 spike 的剩余工作：
1. **PostgreSQL + pgvector Spike**: Phase 1-2 已完成（代码实现），Phase 3-4 待完成（性能测试）
2. **PDF Quality Spike**: Phase 1-3 已完成（代码实现 + 单元测试 + A5 验证 + 结论）

---

## PostgreSQL Spike 状态

### 已完成（Phase 1-2）

**文件**：
- `infra/docker-compose.postgresql-spike.yml` - Docker Compose 配置
- `backend/app/repositories/postgres_schema.sql` - PostgreSQL schema（3 张表 + pgvector 索引）
- `backend/app/repositories/postgres_literature.py` - PostgresLiteratureRepository 实现
- `backend/app/repositories/postgres_chunk.py` - PostgresChunkRepository 实现
- `backend/app/repositories/runtime_storage.py` - 工厂函数集成

**Commit**: `680bb38 feat(spike): add PostgreSQL + pgvector backend implementation (partial)`

### 待完成（Phase 3-4）

**前提条件**：
- Docker 可用
- 安装 `psycopg[binary,pool]>=3.1.0`

**任务**：
1. 启动 PostgreSQL 容器：
   ```bash
   docker compose -f infra/docker-compose.postgresql-spike.yml up -d
   ```

2. 初始化 schema：
   ```bash
   docker exec -i qiyan-postgres-spike psql -U qiyan_dev -d qiyan_nexus < backend/app/repositories/postgres_schema.sql
   ```

3. 安装依赖：
   ```powershell
   cd backend
   & .\.uv-test-venv\Scripts\python.exe -m pip install "psycopg[binary,pool]>=3.1.0"
   ```

4. 实现性能基准测试脚本：
   - 文件：`backend/scripts/benchmark_storage_backends.py`
   - 测试场景：
     - RAG eval retrieval (50 questions)
     - Single literature insert
     - Bulk chunk insert (10, 50 chunks)
     - Get literature by ID (100 iterations)
     - List chunks by literature_id (100 iterations)
   - 对比：JSON / SQLite / PostgreSQL

5. 运行基准测试：
   ```bash
   python -m scripts.benchmark_storage_backends --backend json
   python -m scripts.benchmark_storage_backends --backend sqlite
   python -m scripts.benchmark_storage_backends --backend postgresql
   ```

6. 分析结果并编写结论（更新 `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`）

**预计时间**：3-4 小时

---

## PDF Quality Spike 状态

### 已完成（Phase 1-2）

**实现**（`backend/app/services/literature.py`）：
- `_calculate_cjk_ratio()` - CJK 字符密度计算
- `_detect_low_text_density()` - 低文本密度检测
- `_filter_header_footer_pages()` - 页眉页脚过滤（跳过顶部/底部 15%）
- `extract_pdf_preview_text()` - 集成页眉页脚过滤
- `detect_pdf_text_quality_warning()` - 提高 NUL 容忍度从 2% 到 5%

**单元测试**（`backend/tests/test_pdf_quality_helpers.py`）：
- 28 个测试用例，覆盖所有辅助函数

**验证脚本**（`backend/scripts/validate_pdf_quality_improvements.py`）：
- 自动化 A5 样本测试
- 生成质量指标报告

**Commit**: `24eac7e feat(spike): improve PDF text extraction quality (needs testing)`

### 待完成（Phase 3）— ✅ 已完成 2026-06-05

**验证结果**：
- 单元测试 24/24 通过
- cn-ad-formula-002: NUL 12.60%（未达 <5%，quality_warning 仍触发）
- pruritus/barrier/external: 0 NUL，无 regression
- 结论：部分采纳（见 `docs/evaluations/2026-06-05-pdf-quality-spike.md` Phase 5）

---

## 当前分支状态

```
Branch: feat/multilingual-bge-m3-backend
Status: clean working tree

Recent commits:
24eac7e feat(spike): improve PDF text extraction quality (needs testing)
680bb38 feat(spike): add PostgreSQL + pgvector backend implementation (partial)
66675ec docs: add post-reviewer-readiness execution plan
```

---

## 推荐下一步

### 选项 1: 完成 PDF Quality Spike 验证（推荐）

**理由**：
- 不需要 Docker，只需要本地测试环境
- 预计时间更短（1-2 小时 vs 3-4 小时）
- 改进效果可以立即体现（用户可见）
- A5 样本已经存在于 `backend/uploads/`

**步骤**：
1. 运行单元测试
2. 运行验证脚本
3. 记录质量指标
4. 编写 spike 结论
5. 提交 + 推送

### 选项 2: 完成 PostgreSQL Spike 性能测试

**理由**：
- 生产数据库选型的关键决策依据
- 需要 Docker 环境

**步骤**：
1. 启动 PostgreSQL 容器
2. 初始化 schema
3. 实现基准测试脚本
4. 运行测试并记录数据
5. 编写 spike 结论
6. 提交 + 推送

### 选项 3: 同时推进（如果时间充裕）

**顺序**：
1. 先完成 PDF Quality Spike 验证（短平快）
2. 再完成 PostgreSQL Spike 性能测试（需要更多时间）

---

## 文件清单

### 新增文件

1. `backend/tests/test_pdf_quality_helpers.py` - PDF 质量辅助函数单元测试
2. `backend/scripts/validate_pdf_quality_improvements.py` - A5 样本验证脚本
3. `backend/app/repositories/postgres_literature.py` - PostgreSQL literature repository
4. `backend/app/repositories/postgres_chunk.py` - PostgreSQL chunk repository
5. `backend/app/repositories/postgres_schema.sql` - PostgreSQL schema
6. `infra/docker-compose.postgresql-spike.yml` - Docker Compose 配置

### 修改文件

1. `backend/app/services/literature.py` - PDF 质量改进（新增 3 个辅助函数，修改 2 个核心函数）
2. `backend/app/repositories/runtime_storage.py` - 工厂函数集成 PostgreSQL 支持
3. `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md` - PostgreSQL spike 文档
4. `docs/evaluations/2026-06-05-pdf-quality-spike.md` - PDF quality spike 文档

---

## 验证清单

### PDF Quality Spike

- [x] 单元测试全部通过（24 个测试用例）
- [x] 验证脚本运行成功
- [ ] cn-ad-formula-002 NUL 比例 <5%（实际 12.60%，未达标）
- [x] 其他样本无 regression
- [x] 更新 spike 文档（实际结果 + 结论）

### PostgreSQL Spike

- [ ] PostgreSQL 容器启动成功
- [ ] Schema 初始化成功
- [ ] 基准测试脚本实现完成
- [ ] JSON/SQLite/PostgreSQL 三种 backend 测试完成
- [ ] 性能数据记录到文档
- [ ] 更新 spike 文档（实际结果 + 决策）

---

## 注意事项

1. **单元测试**：PDF quality 单元测试中，`TestFilterHeaderFooterPages` 是集成测试占位符，需要真实 PDF 或 mock PdfReader 才能完整测试。当前只验证函数签名。

2. **A5 样本**：验证脚本假设以下文件存在于 `backend/uploads/`：
   - `pdf-cn-ad-formula-002-pdf-5ffc0e56.pdf`（已知问题样本）
   - `pdf-cn-ad-barrier-006-pdf-2c576156.pdf`
   - `pdf-cn-ad-external-008-pdf-d28de853.pdf`
   - `pdf-cn-ad-gbs-001-43-pdf.pdf`
   - `pdf-cn-ad-gbs-001-cc-1-pdf.pdf`

3. **PostgreSQL 依赖**：需要手动安装 `psycopg[binary,pool]`，不在默认 `[dev]` 依赖中。

4. **时间盒原则**：两个 spike 总计预算 8-12 小时（PostgreSQL 8h + PDF 4h）。如果时间不够，优先完成 PDF Quality Spike（用户可见改进）。

---

**记录时间**：2026-06-05  
**记录人**：Claude Opus 4.8
