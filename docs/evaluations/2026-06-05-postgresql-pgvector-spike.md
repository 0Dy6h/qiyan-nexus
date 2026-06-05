# PostgreSQL + pgvector Spike — 2026-06-05

date: 2026-06-05  
status: PARTIAL — engineering path implemented, PostgreSQL runtime benchmark blocked by local environment
time_box: 1 day

---

## Verdict

**结论：暂不推荐切换默认 backend。**

本次 spike 已把 PostgreSQL + pgvector 做成显式 opt-in 的工程路径：schema、repository、factory、可选依赖与 benchmark harness 均已落地，并通过默认后端门禁验证。但当前 Windows 环境没有 Docker、psql/pg_ctl、Podman 或 PostgreSQL service，因此无法启动 PostgreSQL/pgvector 实例，PostgreSQL 性能数据缺失。

在可用证据范围内，SQLite 仍是当前内部预览最合适的 runtime backend：它已经是默认之外的可用本地持久化路径，读写性能显著优于 JSON，且不引入容器、连接池、迁移与运维复杂度。PostgreSQL 应继续保持 opt-in spike/backend，不进入默认路径；只有在有真实 PostgreSQL benchmark 且明确出现多用户/并发/pgvector 检索需求后，再进入生产化 ADR。

## Scope

本次 spike 验证的问题：

- PostgreSQL + pgvector 是否能按现有 repository protocol 接入。
- 是否能保持 JSON/SQLite 默认路径不变。
- 是否能提供可复跑的 JSON/SQLite/PostgreSQL backend benchmark。
- 当前规模下是否已有足够证据推动 PostgreSQL 默认化。

明确不包含：

- 不做 Alembic 迁移体系。
- 不做 seed → PostgreSQL 生产迁移脚本。
- 不做 PgBouncer、备份恢复、权限分层等生产运维。
- 不实现 pgvector 相似度检索，只预留 `chunks.embedding vector(384)` 与索引。
- 不替换默认 backend。

## Implemented

### Infrastructure

- 新增 `infra/docker-compose.postgresql-spike.yml`
  - image: `pgvector/pgvector:pg15`
  - database: `qiyan_nexus`
  - user/password: `qiyan_dev` / `qiyan_dev_pass`
  - port: `5432`
  - healthcheck: `pg_isready`

### Schema

- 新增 `backend/app/repositories/postgres_schema.sql`
- 表：
  - `literature`
  - `chunks`
  - `network_tasks`
- 关键设计：
  - JSON list/object 字段使用 `JSONB`
  - `chunks.embedding vector(384)` 预留 BGE-small/BGE 类 embedding 维度
  - `idx_chunks_embedding` 使用 IVFFlat + cosine ops
  - `trigger_literature_updated_at` 现在先 `DROP TRIGGER IF EXISTS`，保证 schema 可重复执行

### Repositories

- 新增 `backend/app/repositories/postgres_common.py`
  - `create_postgres_pool()`
  - `ensure_postgres_schema()`
  - pool/connect timeout 默认 5 秒，避免无服务环境卡 30 秒
- 更新 `backend/app/repositories/postgres_literature.py`
  - 对齐 `LiteratureRepository`
  - 支持 seed bootstrap
  - 使用 `Jsonb(...)` 做 JSONB 绑定
  - `update_pdf_metadata()` 与 JSON/SQLite 一样 reset parse fields
  - `update_pdf_parse_status()` 与 JSON/SQLite 一样要求已有 PDF metadata
  - `bulk_upsert_pubmed_items()` 保留 PDF/runtime 字段，只覆盖 PubMed-owned fields
- 更新 `backend/app/repositories/postgres_chunk.py`
  - 对齐 `ChunkRepository`
  - 支持 seed bootstrap
  - chunk bootstrap 前确保 literature seed 已存在，避免外键顺序问题
  - 上传 PDF chunk 的 `section/source_type/pdf_upload_id/default related_entity_ids` 与 JSON/SQLite 一致
- 新增 `backend/app/repositories/postgres_network_tasks.py`
  - 对齐 `NetworkTaskRepositoryProtocol`
  - 避免 `QIYAN_STATE_BACKEND="postgresql"` 时 network task 仍落回 JSON

### Factory / Config

- 更新 `backend/app/repositories/runtime_storage.py`
  - `get_literature_repository()` 支持 `postgresql`
  - `get_chunk_repository()` 支持 `postgresql`
  - `get_network_task_repository()` 支持 `postgresql`
  - cache clear 会关闭 SQLite/PostgreSQL closeable resources
- 更新 `backend/pyproject.toml`
  - `[project.optional-dependencies].postgresql = ["psycopg[binary,pool]>=3.1.0"]`
  - mypy 对 `psycopg*`/`psycopg_pool` 使用 missing-import override，保证默认环境不被可选依赖拖垮
- 更新 `backend/.env.example`
  - 文档化 `QIYAN_STATE_BACKEND="postgresql"`
  - 文档化 `QIYAN_POSTGRES_DSN`

### Benchmark Harness

- 新增 `backend/scripts/benchmark_storage_backends.py`
- 支持：
  - `--backend json`
  - `--backend sqlite`
  - `--backend postgresql`
  - `--backend all`
  - `--iterations`
  - `--rag-runs`
  - `--json`
  - `--reset-postgresql`
- 场景：
  - 50 题 RAG eval keyword retrieval
  - 单条 literature upsert
  - 10 chunk 批量 upsert
  - 50 chunk 批量 upsert
  - get literature by ID
  - list chunks by literature ID
- PostgreSQL 分支先执行短连接 readiness check；无数据库服务时输出明确失败，不再卡住或打印 pool worker 噪声。

## Environment Findings

当前机器环境：

- `docker` 命令不存在。
- `psql` 命令不存在。
- `pg_ctl` 命令不存在。
- `podman` 命令不存在。
- 未发现 Windows PostgreSQL service。
- `backend/.uv-test-venv` 没有 `pip` 模块；可选依赖通过 `uv pip install --python .\.uv-test-venv\Scripts\python.exe "psycopg[binary,pool]>=3.1.0"` 安装完成。

PostgreSQL benchmark smoke 输出：

```json
{
  "results": {},
  "failures": {
    "postgresql": "RuntimeError: PostgreSQL is not reachable. Start infra/docker-compose.postgresql-spike.yml and retry."
  }
}
```

## Benchmark Results

命令：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend json --iterations 30 --rag-runs 3 --json
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend sqlite --iterations 30 --rag-runs 3 --json
```

环境说明：

- Windows + PowerShell
- Python: `backend/.uv-test-venv`
- RAG provider forced to deterministic
- retrieval provider forced to keyword
- 每个 backend 使用隔离临时 seed/runtime 数据
- PostgreSQL 未跑通，因为本机无可用数据库服务

| Backend | Scenario | Iterations | p50 ms | p95 ms | p99 ms | total ms |
|---|---|---:|---:|---:|---:|---:|
| json | rag_eval_50q_keyword | 3 | 156.281 | 169.323 | 169.323 | 476.612 |
| json | single_literature_insert | 30 | 14.136 | 17.641 | 17.795 | 420.007 |
| json | bulk_chunk_insert_10 | 30 | 136.553 | 168.994 | 183.472 | 4292.305 |
| json | bulk_chunk_insert_50 | 30 | 1062.796 | 1214.501 | 1280.154 | 31272.322 |
| json | get_literature_by_id | 30 | 0.357 | 0.595 | 21.400 | 32.248 |
| json | list_chunks_by_literature_id | 30 | 8.400 | 18.499 | 28.100 | 282.393 |
| sqlite | rag_eval_50q_keyword | 3 | 75.193 | 84.886 | 84.886 | 229.591 |
| sqlite | single_literature_insert | 30 | 0.341 | 0.693 | 1.255 | 11.803 |
| sqlite | bulk_chunk_insert_10 | 30 | 3.805 | 4.720 | 5.095 | 115.887 |
| sqlite | bulk_chunk_insert_50 | 30 | 17.574 | 21.264 | 21.745 | 540.708 |
| sqlite | get_literature_by_id | 30 | 0.018 | 0.028 | 0.114 | 0.658 |
| sqlite | list_chunks_by_literature_id | 30 | 9.900 | 11.930 | 21.237 | 311.806 |

Interpretation:

- SQLite 比 JSON 在写路径上明显更快：
  - single literature insert p50: ~41x faster
  - 10 chunk insert p50: ~36x faster
  - 50 chunk insert p50: ~60x faster
- RAG eval retrieval 在 SQLite 上约 2x faster。
- `list_chunks_by_literature_id` 在该 benchmark 中会受前序 chunk upsert 增长影响；SQLite 与 JSON 结果接近，不应过度解读为 indexed DB 的真实上限。
- PostgreSQL 缺实测数据，不能判断是否超过 SQLite。

## Verification

已运行：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

结果：

- `ruff format --check app tests`: pass
- `ruff check app tests`: pass
- `mypy app`: pass
- `pytest -q`: `498 passed, 1 skipped in 15.14s`

Additional smoke:

```powershell
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --iterations 1 --rag-runs 1 --json
```

结果：PostgreSQL readiness fail（本机无服务），输出见上。

## How To Finish PostgreSQL Numbers Later

在有 Docker 的机器上从仓库根目录运行：

```powershell
cd backend
uv pip install --python .\.uv-test-venv\Scripts\python.exe "psycopg[binary,pool]>=3.1.0"
cd ..
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
cd backend
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 30 --rag-runs 3 --json
```

说明：

- repository 会自动执行 idempotent schema，不需要手动 `psql < postgres_schema.sql`。
- `--reset-postgresql` 会 `TRUNCATE` spike 表，仅用于本地 spike 数据库。
- 如果本地数据库连接慢，可通过 `QIYAN_POSTGRES_CONNECT_TIMEOUT` / `QIYAN_POSTGRES_POOL_TIMEOUT` 调整 timeout。

## Decision Criteria For Reopening

只有满足以下任一条件，才建议继续投入 PostgreSQL 生产化：

- PostgreSQL 实测在当前关键路径上显著优于 SQLite，尤其是大规模 chunk 写入和检索路径。
- 进入多人并发 reviewer/demo 场景，SQLite 文件锁成为实际瓶颈。
- 需要真正的 pgvector 相似度检索、ANN 索引调参或 embedding 数据治理。
- 需要生产级数据库能力：备份恢复、权限隔离、审计、迁移、监控。

否则保持：

- 默认 backend: JSON
- 可选本地持久化 backend: SQLite
- PostgreSQL: explicit opt-in spike/backend only

## Residual Risks

- PostgreSQL repository 尚未在真实 PostgreSQL/pgvector 实例上通过 CRUD/benchmark。
- 当前 schema 仍是 spike schema，不是 Alembic 管理的生产迁移。
- pgvector 列和 IVFFlat index 只做结构预留，没有接入 retrieval provider。
- optional dependency 已在当前 venv 安装用于 smoke，但默认开发路径仍不应要求 PostgreSQL 依赖。
