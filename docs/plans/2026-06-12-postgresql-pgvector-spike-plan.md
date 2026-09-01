# PostgreSQL + pgvector Spike Plan

## 目标

从当前 SQLite runtime backend 迁移到 PostgreSQL + pgvector，为生产级向量检索和数据持久化建立基础设施。

## 背景

- **当前状态**：SQLite runtime backend 已落地（2026-06-02，commit 4144357）
- **repository 协议抽象**：已完成（`backend/app/repositories/protocols.py`）
- **切换机制**：通过 `QIYAN_STATE_BACKEND` env 切换（当前支持 `json` / `sqlite`）
- **测试覆盖**：两个 backend 均通过完整测试套件（489 passed）

## 技术栈

- **PostgreSQL 16**：核心关系数据库
- **pgvector extension**：向量相似度搜索（cosine distance, HNSW index）
- **psycopg3**（或 asyncpg）：Python PostgreSQL 驱动
- **Docker Compose**（可选）：本地开发环境

## 实施计划

### Phase 1: 环境准备（1 小时）

**1.1 本地 PostgreSQL + pgvector 安装**

选项 A：Docker Compose（推荐）
```yaml
# infra/docker-compose.yml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: qiyan
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: qiyan_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

选项 B：本地直装（Windows）
- 下载 PostgreSQL 16 installer
- 编译或下载 pgvector extension（Windows 二进制）
- 配置环境变量

**1.2 数据库初始化脚本**

```sql
-- backend/infra/schema.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE literature (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT[],
    year INTEGER,
    abstract TEXT,
    keywords TEXT[],
    source_type TEXT NOT NULL,
    evidence_tags TEXT[],
    related_entity_ids TEXT[],
    pdf_upload_id TEXT,
    pdf_file_name TEXT,
    pdf_parse_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    literature_id TEXT NOT NULL REFERENCES literature(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    evidence_tags TEXT[],
    vector vector(128),  -- 当前 hashing backend dim=128，真实 embedding 改为 512/1024
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(literature_id, chunk_index)
);

CREATE INDEX idx_literature_source ON literature(source_type);
CREATE INDEX idx_chunks_lit_id ON chunks(literature_id);
CREATE INDEX idx_chunks_vector ON chunks USING hnsw (vector vector_cosine_ops);
```

**1.3 依赖安装**

```bash
# backend/pyproject.toml [project.dependencies]
psycopg[binary] >= 3.1.0
pgvector >= 0.2.0
```

### Phase 2: Repository 实现（2 小时）

**2.1 PostgresLiteratureRepository**

```python
# backend/app/repositories/literature_postgres.py
from typing import List, Optional
import psycopg
from psycopg.rows import dict_row
from app.repositories.protocols import LiteratureRepository
from app.schemas.literature import Literature

class PostgresLiteratureRepository(LiteratureRepository):
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
    
    def get_by_id(self, literature_id: str) -> Optional[Literature]:
        with psycopg.connect(self.conn_string, row_factory=dict_row) as conn:
            result = conn.execute(
                "SELECT * FROM literature WHERE id = %s",
                (literature_id,)
            ).fetchone()
            return Literature(**result) if result else None
    
    def search(
        self,
        query: str,
        source: str = "all",
        limit: int = 10,
        offset: int = 0,
    ) -> List[Literature]:
        # 实现 full-text search 或简单 LIKE 匹配
        # 后续可用 tsvector + tsquery 优化
        ...
    
    def update_pdf_metadata(self, literature_id: str, ...) -> None:
        with psycopg.connect(self.conn_string) as conn:
            conn.execute(
                """UPDATE literature 
                   SET pdf_upload_id = %s, pdf_file_name = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s""",
                (pdf_upload_id, file_name, literature_id)
            )
            conn.commit()
```

**2.2 PostgresChunkRepository**

```python
# backend/app/repositories/chunk_postgres.py
from typing import List, Optional
import psycopg
import numpy as np
from pgvector.psycopg import register_vector
from app.repositories.protocols import ChunkRepository
from app.schemas.chunk import LiteratureChunk

class PostgresChunkRepository(ChunkRepository):
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
    
    def get_by_id(self, chunk_id: str) -> Optional[LiteratureChunk]:
        with psycopg.connect(self.conn_string, row_factory=dict_row) as conn:
            register_vector(conn)
            result = conn.execute(
                "SELECT * FROM chunks WHERE chunk_id = %s",
                (chunk_id,)
            ).fetchone()
            return self._row_to_chunk(result) if result else None
    
    def search_by_literature_ids(
        self,
        literature_ids: List[str],
        limit: int = 100,
    ) -> List[LiteratureChunk]:
        with psycopg.connect(self.conn_string, row_factory=dict_row) as conn:
            register_vector(conn)
            results = conn.execute(
                "SELECT * FROM chunks WHERE literature_id = ANY(%s) LIMIT %s",
                (literature_ids, limit)
            ).fetchall()
            return [self._row_to_chunk(r) for r in results]
    
    def search_by_vector(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
    ) -> List[LiteratureChunk]:
        with psycopg.connect(self.conn_string, row_factory=dict_row) as conn:
            register_vector(conn)
            results = conn.execute(
                """SELECT *, vector <=> %s::vector AS distance
                   FROM chunks 
                   ORDER BY vector <=> %s::vector
                   LIMIT %s""",
                (query_vector.tolist(), query_vector.tolist(), top_k)
            ).fetchall()
            return [self._row_to_chunk(r) for r in results]
```

**2.3 Repository 工厂**

```python
# backend/app/repositories/factory.py
import os
from app.repositories.protocols import LiteratureRepository, ChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.repositories.literature_postgres import PostgresLiteratureRepository
# ... 其他 imports

def get_literature_repository() -> LiteratureRepository:
    backend = os.getenv("QIYAN_STATE_BACKEND", "json")
    if backend == "postgres":
        conn_string = os.getenv("QIYAN_POSTGRES_URL", "postgresql://qiyan:dev_password@localhost:5432/qiyan_dev")
        return PostgresLiteratureRepository(conn_string)
    elif backend == "sqlite":
        return SqliteLiteratureRepository(...)
    else:
        return InMemoryLiteratureRepository(...)

def get_chunk_repository() -> ChunkRepository:
    # 同样逻辑
    ...
```

### Phase 3: 迁移脚本（1 小时）

**3.1 Seed JSON → PostgreSQL**

```python
# backend/scripts/migrate_seed_to_postgres.py
"""Migrate seed JSON data to PostgreSQL."""
import json
import psycopg
from pathlib import Path

def migrate_literature(conn, seed_path: Path):
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    with conn.cursor() as cur:
        for item in data:
            cur.execute(
                """INSERT INTO literature 
                   (id, title, authors, year, abstract, keywords, source_type, evidence_tags, related_entity_ids)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP""",
                (item["id"], item["title"], item["authors"], item["year"], 
                 item["abstract"], item["keywords"], item["source_type"],
                 item.get("evidence_tags", []), item.get("related_entity_ids", []))
            )
    conn.commit()

def migrate_chunks(conn, seed_path: Path):
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    with conn.cursor() as cur:
        for item in data:
            cur.execute(
                """INSERT INTO chunks 
                   (chunk_id, literature_id, chunk_index, text, evidence_tags, vector)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (chunk_id) DO NOTHING""",
                (item["chunk_id"], item["literature_id"], item["chunk_index"],
                 item["text"], item.get("evidence_tags", []), None)  # vector 后续填充
            )
    conn.commit()

def main():
    conn_string = "postgresql://qiyan:dev_password@localhost:5432/qiyan_dev"
    with psycopg.connect(conn_string) as conn:
        migrate_literature(conn, Path("data/literature/sample_ad_literature.json"))
        migrate_chunks(conn, Path("data/literature/sample_ad_chunks.json"))
    print("Migration complete.")

if __name__ == "__main__":
    main()
```

### Phase 4: 测试与验证（1 小时）

**4.1 Repository 单元测试**

```python
# backend/tests/test_postgres_repository.py
import pytest
from app.repositories.literature_postgres import PostgresLiteratureRepository

@pytest.fixture
def postgres_repo():
    # 使用测试数据库
    return PostgresLiteratureRepository("postgresql://qiyan:test@localhost:5432/qiyan_test")

def test_get_by_id(postgres_repo):
    lit = postgres_repo.get_by_id("cn-ad-gbs-001")
    assert lit is not None
    assert lit.title is not None

def test_search(postgres_repo):
    results = postgres_repo.search("特应性皮炎", limit=5)
    assert len(results) > 0
```

**4.2 性能对比**

```python
# backend/scripts/benchmark_backends.py
"""Benchmark SQLite vs PostgreSQL repository performance."""
import time
from app.repositories.factory import get_literature_repository

def benchmark_search(backend: str, iterations: int = 100):
    import os
    os.environ["QIYAN_STATE_BACKEND"] = backend
    repo = get_literature_repository()
    
    start = time.time()
    for _ in range(iterations):
        repo.search("特应性皮炎", limit=10)
    elapsed = time.time() - start
    
    print(f"{backend}: {iterations} searches in {elapsed:.2f}s ({elapsed/iterations*1000:.2f}ms per search)")

if __name__ == "__main__":
    benchmark_search("sqlite", 100)
    benchmark_search("postgres", 100)
```

**4.3 完整测试套件**

```bash
# 设置测试环境
export QIYAN_STATE_BACKEND=postgres
export QIYAN_POSTGRES_URL=postgresql://qiyan:test@localhost:5432/qiyan_test

# 运行测试
cd backend
./.uv-test-venv/Scripts/python.exe -m pytest -q
```

### Phase 5: 文档与配置（0.5 小时）

**5.1 README 更新**

```markdown
## PostgreSQL Backend (Optional)

当前默认使用 SQLite runtime backend。如需切换到 PostgreSQL：

1. 启动 PostgreSQL + pgvector：
   ```bash
   cd infra
   docker-compose up -d postgres
   ```

2. 初始化数据库：
   ```bash
   psql -U qiyan -d qiyan_dev -f infra/schema.sql
   ```

3. 迁移 seed 数据：
   ```bash
   cd backend
   ./.uv-test-venv/Scripts/python.exe scripts/migrate_seed_to_postgres.py
   ```

4. 配置环境变量：
   ```bash
   export QIYAN_STATE_BACKEND=postgres
   export QIYAN_POSTGRES_URL=postgresql://qiyan:dev_password@localhost:5432/qiyan_dev
   ```

5. 启动服务：
   ```bash
   ./.uv-test-venv/Scripts/fastapi.exe dev app/main.py
   ```
```

**5.2 .env.example 补充**

```bash
# PostgreSQL backend (optional, default: json)
QIYAN_STATE_BACKEND=postgres
QIYAN_POSTGRES_URL=postgresql://qiyan:dev_password@localhost:5432/qiyan_dev
```

## 验收标准

- [ ] PostgreSQL + pgvector 环境可在 Docker 或本地启动
- [ ] Schema 初始化脚本无错误执行
- [ ] PostgresLiteratureRepository / PostgresChunkRepository 实现完整
- [ ] Repository 协议测试全部通过（复用既有测试）
- [ ] 迁移脚本成功导入 seed JSON
- [ ] 性能对比报告（SQLite vs PostgreSQL，10/100/1000 条查询延迟）
- [ ] Backend 测试套件全绿（`pytest -q` with `QIYAN_STATE_BACKEND=postgres`）
- [ ] 文档更新（README, infra/, .env.example）

## 预期产出

1. `infra/docker-compose.yml` — PostgreSQL + pgvector 服务
2. `infra/schema.sql` — 数据库初始化脚本
3. `backend/app/repositories/literature_postgres.py`
4. `backend/app/repositories/chunk_postgres.py`
5. `backend/app/repositories/factory.py` — repository 工厂
6. `backend/scripts/migrate_seed_to_postgres.py` — 迁移脚本
7. `backend/scripts/benchmark_backends.py` — 性能对比脚本
8. `backend/tests/test_postgres_repository.py` — PostgreSQL 专项测试
9. `docs/handoffs/2026-06-XX-postgresql-pgvector-spike.md` — 实施交接

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| Windows pgvector 编译困难 | 优先使用 Docker，或预编译二进制 |
| 测试数据污染 | 使用独立 `qiyan_test` 数据库 + 每次测试清空 |
| 性能回归 | 对比 benchmark，确保 PostgreSQL >= SQLite 延迟 |
| 迁移脚本失败 | 先小数据集验证，再完整迁移 |

## 后续扩展（Out of Scope）

- 生产级配置（连接池、只读副本、备份策略）
- 真实 embedding vector 更新（当前 None，需接入 bge / e5）
- Full-text search 优化（tsvector + GIN index）
- 分表策略（literature / chunks 分别存储）

---

**计划创建日期**：2026-06-12  
**预估工作量**：4-5 小时  
**优先级**：中等（基础设施准备）  
**前置条件**：SQLite backend 已落地（✅ 2026-06-02）  
**阻塞项**：无
