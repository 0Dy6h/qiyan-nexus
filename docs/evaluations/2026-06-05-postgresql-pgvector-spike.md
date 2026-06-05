# PostgreSQL + pgvector Spike — 2026-06-05

date: 2026-06-05  
status: in_progress  
time_box: 1 day (8 hours)

---

## 目标

评估 PostgreSQL + pgvector 作为生产级 runtime backend 的可行性，对比 JSON/SQLite/PostgreSQL 三种 backend 的性能。

## 背景

- 当前默认：JSON files in `backend/data/runtime/`
- 2026-06-02 已落地：SQLite runtime backend（`QIYAN_STATE_BACKEND="sqlite"`）
- PostgreSQL + pgvector 是生产数据库候选方向

## Spike 范围

### ✅ 包含（In Scope）

1. **环境准备**
   - Docker Compose 配置：PostgreSQL 15+ with pgvector extension
   - 本地连接验证

2. **Schema 设计**
   - 基于 `app/repositories/protocols.py` 设计 PostgreSQL schema
   - 关键表：`literature`, `chunks`, `network_tasks`
   - pgvector：`chunks.embedding vector(384)` for BGE-small-zh-v1.5

3. **Repository 实现原型**
   - `PostgresLiteratureRepository` 符合 `LiteratureRepositoryProtocol`
   - `PostgresChunkRepository` 符合 `ChunkRepositoryProtocol`
   - 使用 `psycopg` (psycopg3) 异步驱动
   - 保持 JSON/SQLite 为默认，PostgreSQL 为 `QIYAN_STATE_BACKEND="postgresql"` opt-in

4. **性能基准测试**
   - 对比 JSON / SQLite / PostgreSQL 三种 backend
   - 测试场景：
     - **Retrieval performance**: 50 题 RAG eval 检索性能（keyword provider）
     - **Single write**: 单次 literature insert/update
     - **Bulk write**: Bulk chunk insert（模拟 PDF 解析后批量写入 10-50 chunks）
     - **Read latency**: Get literature by ID, list chunks by literature_id
   - 记录：延迟（p50/p95/p99）、吞吐量

5. **记录 Spike 结论**
   - 写入 `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`
   - 包含：性能数据、迁移复杂度评估、推荐决策

### ❌ 不包含（Out of Scope）

- ❌ 完整数据迁移脚本（seed → PostgreSQL）
- ❌ 生产级连接池（PgBouncer）
- ❌ Alembic 迁移自动化
- ❌ 替换默认 backend（保持 JSON 或 SQLite）
- ❌ pgvector 相似度搜索实现（仅创建 embedding 列，不实现 vector retrieval）
- ❌ 真实 embedding 数据填充（可用 dummy vectors）

---

## 设计

### 1. Docker Compose 配置

```yaml
# infra/docker-compose.postgresql-spike.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    container_name: qiyan-postgres-spike
    environment:
      POSTGRES_DB: qiyan_nexus
      POSTGRES_USER: qiyan_dev
      POSTGRES_PASSWORD: qiyan_dev_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qiyan_dev -d qiyan_nexus"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

启动命令：
```bash
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
```

### 2. PostgreSQL Schema

```sql
-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Literature table
CREATE TABLE literature (
    id                    TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    language              TEXT NOT NULL,
    source_type           TEXT NOT NULL,
    source                TEXT NOT NULL,
    year                  INTEGER NOT NULL,
    snippet               TEXT NOT NULL,
    authors               JSONB NOT NULL DEFAULT '[]',
    keywords              JSONB NOT NULL DEFAULT '[]',
    evidence_tags         JSONB NOT NULL DEFAULT '[]',
    abstract              TEXT,
    citation_url          TEXT,
    pubmed_id             TEXT,
    doi                   TEXT,
    pdf_upload_id         TEXT,
    pdf_file_name         TEXT,
    pdf_parse_status      TEXT,
    pdf_parse_message     TEXT,
    pdf_parse_started_at  TIMESTAMP,
    pdf_parse_finished_at TIMESTAMP,
    pdf_parse_result      JSONB,
    last_parse_trigger    TEXT,
    parse_attempt_count   INTEGER,
    related_entity_ids    JSONB NOT NULL DEFAULT '[]',
    created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_literature_source_type ON literature(source_type);
CREATE INDEX idx_literature_year ON literature(year DESC);
CREATE INDEX idx_literature_pubmed_id ON literature(pubmed_id) WHERE pubmed_id IS NOT NULL;

-- Chunks table
CREATE TABLE chunks (
    chunk_id           TEXT PRIMARY KEY,
    literature_id      TEXT NOT NULL REFERENCES literature(id) ON DELETE CASCADE,
    section            TEXT NOT NULL,
    text               TEXT NOT NULL,
    source_quote       TEXT NOT NULL,
    evidence_tags      JSONB NOT NULL DEFAULT '[]',
    related_entity_ids JSONB NOT NULL DEFAULT '[]',
    source_type        TEXT NOT NULL DEFAULT 'sample',
    pdf_upload_id      TEXT,
    embedding          vector(384),  -- BGE-small-zh-v1.5 dimension
    created_at         TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunks_literature_id ON chunks(literature_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Network tasks table
CREATE TABLE network_tasks (
    task_id       TEXT PRIMARY KEY,
    query         TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    status        TEXT NOT NULL,
    progress      INTEGER NOT NULL DEFAULT 0,
    poll_count    INTEGER NOT NULL DEFAULT 0,
    result        JSONB,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_network_tasks_status ON network_tasks(status);
CREATE INDEX idx_network_tasks_created_at ON network_tasks(created_at DESC);
```

### 3. 依赖更新

```toml
# backend/pyproject.toml - 新增 optional dependencies
[project.optional-dependencies]
dev = [
    "ruff>=0.6.0",
    "mypy>=1.10.0",
    "fastapi[standard]>=0.115.0",
    "sentence-transformers>=3.0.0",
    "transformers>=4.40.0",
]
postgresql = [
    "psycopg[binary]>=3.1.0",  # PostgreSQL async driver
    "psycopg[pool]>=3.1.0",    # Connection pool
]
```

安装命令：
```bash
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pip install -e ".[postgresql]"
```

### 4. Repository 实现结构

```
backend/app/repositories/
├── protocols.py                    # Protocol definitions (unchanged)
├── literature.py                   # InMemory implementation (default)
├── sqlite_literature.py            # SQLite implementation
├── postgres_literature.py          # NEW: PostgreSQL implementation
├── chunk.py                        # InMemory implementation (default)
├── sqlite_chunk.py                 # SQLite implementation
├── postgres_chunk.py               # NEW: PostgreSQL implementation
└── runtime_storage.py              # Factory that selects backend
```

### 5. 性能测试脚本

```python
# backend/scripts/benchmark_storage_backends.py
"""
Benchmark JSON / SQLite / PostgreSQL backends.

Usage:
    python -m scripts.benchmark_storage_backends --backend json
    python -m scripts.benchmark_storage_backends --backend sqlite
    python -m scripts.benchmark_storage_backends --backend postgresql
"""
```

测试场景：
1. **RAG eval retrieval** (50 questions)
2. **Single literature insert**
3. **Bulk chunk insert** (10, 50 chunks)
4. **Get literature by ID** (100 iterations)
5. **List chunks by literature_id** (100 iterations)

---

## 实施计划

### Phase 1: 环境准备 (1 hour)
- [ ] 创建 `infra/docker-compose.postgresql-spike.yml`
- [ ] 启动 PostgreSQL 容器
- [ ] 验证连接：`psql -h localhost -U qiyan_dev -d qiyan_nexus`
- [ ] 创建 schema：`backend/app/repositories/postgres_schema.sql`

### Phase 2: Repository 实现 (3 hours)
- [ ] 实现 `PostgresLiteratureRepository`
  - `list_items()`
  - `get_item_by_id()`
  - `update_pdf_metadata()`
  - `update_pdf_parse_status()`
  - `bulk_upsert_pubmed_items()`
- [ ] 实现 `PostgresChunkRepository`
  - `list_chunks()`
  - `list_chunks_by_literature_id()`
  - `get_chunk_by_id()`
  - `upsert_uploaded_pdf_chunk()`
- [ ] 更新 `runtime_storage.py` 工厂函数
- [ ] 单元测试（复用 SQLite 测试模式）

### Phase 3: 性能基准测试 (2 hours)
- [ ] 实现 `scripts/benchmark_storage_backends.py`
- [ ] 运行 JSON baseline
- [ ] 运行 SQLite baseline
- [ ] 运行 PostgreSQL baseline
- [ ] 记录结果到本文档

### Phase 4: 结论与清理 (2 hours)
- [ ] 分析性能数据
- [ ] 评估迁移复杂度
- [ ] 编写推荐决策
- [ ] 清理临时容器和数据

---

## 预期结果

### 性能假设

| Backend    | RAG Eval (50q) | Single Insert | Bulk Insert (50) | Get by ID | List Chunks |
|------------|----------------|---------------|------------------|-----------|-------------|
| JSON       | ~2s            | ~50ms         | ~500ms           | ~20ms     | ~30ms       |
| SQLite     | ~1.5s          | ~10ms         | ~200ms           | ~5ms      | ~10ms       |
| PostgreSQL | ~1s            | ~5ms          | ~100ms           | ~2ms      | ~5ms        |

（实际结果待测试填写）

### 决策标准

- ✅ **推荐 PostgreSQL** 如果：
  - 性能显著优于 SQLite（>2x improvement）
  - 迁移复杂度可接受（<3 天工作量）
  - pgvector 索引构建时间可接受（<10 分钟 for seed data）

- ⚠️ **保持 SQLite** 如果：
  - 性能差异不显著（<1.5x）
  - 迁移复杂度高（需要 Alembic, 数据迁移脚本）
  - 当前规模下 SQLite 足够（<10k literature, <100k chunks）

- ❌ **不推荐 PostgreSQL** 如果：
  - 性能劣于 SQLite
  - 运维复杂度显著增加
  - pgvector 索引构建/查询有问题

---

## 实际结果

### Environment Setup

（待填写）

### Repository Implementation

（待填写）

### Performance Benchmark Results

（待填写）

### 决策

（待填写）

---

## 遗留问题

（待填写）

---

**时间盒提醒**：如果 Phase 2 结束时已超过 5 小时，跳过完整性能测试，仅做smoke测试并记录"需要更多时间"结论。
