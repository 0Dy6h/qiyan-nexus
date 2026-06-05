# PostgreSQL + pgvector Spike — 2026-06-05

date: 2026-06-05  
status: COMPLETE — PostgreSQL runtime benchmark completed; default backend unchanged
time_box: 1 day

---

## Verdict

**结论：暂不推荐切换默认 backend。**

本次 spike 已把 PostgreSQL + pgvector 做成显式 opt-in 的工程路径：schema、repository、factory、可选依赖、Docker Compose 配置与 benchmark harness 均已落地，并在 Docker Desktop + `pgvector/pgvector:pg15` 上完成真实 runtime smoke 和 JSON/SQLite/PostgreSQL 三后端 benchmark。

实测结论支持继续保持 SQLite 作为当前内部预览最合适的可选本地持久化 backend：SQLite 在本 benchmark 的所有 p50 场景中均快于 PostgreSQL，且不引入容器、连接池、迁移与运维复杂度。PostgreSQL 写路径显著优于 JSON，但当前没有超过 SQLite；RAG keyword eval 在 PostgreSQL 上明显慢于 SQLite。PostgreSQL 应继续保持 explicit opt-in spike/backend，不进入默认路径；只有在明确出现多人并发、真实 pgvector 检索、ANN 调参、备份恢复或生产数据库治理需求后，再进入生产化 ADR。

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

实测机器环境：

- OS: Windows 11 `10.0.26100`
- CPU: 13th Gen Intel(R) Core(TM) i7-13700H, 14 cores / 20 logical processors
- RAM: ~16 GB
- Python: `backend/.uv-test-venv`, Python 3.13.12
- Docker Desktop: 4.76.0
- Docker Engine / CLI: 29.5.2
- Docker Compose: v5.1.4
- Docker context: `desktop-linux`
- PostgreSQL image: `pgvector/pgvector:pg15`
- Container: `qiyan-postgres-spike`, healthcheck `healthy`, port `5432`
- PostgreSQL version: 15.18 from the `pgvector/pgvector:pg15` image
- pgvector extension: installed and visible in `pg_extension`
- Schema auto-init: `backend/app/repositories/postgres_schema.sql` mounted into `/docker-entrypoint-initdb.d/01_qiyan_schema.sql` and executed on a fresh volume.
- `backend/.uv-test-venv` already has `psycopg` and `psycopg_pool` available for the optional PostgreSQL path.

Docker Hub access initially failed from the Docker daemon with `EOF`; Docker Desktop was then configured to use the host Clash/Mihomo proxy (`127.0.0.1:7897`) via manual proxy settings. After Docker Desktop restart, `docker pull hello-world` and `docker compose -f infra/docker-compose.postgresql-spike.yml up -d` both succeeded.

PostgreSQL runtime smoke:

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
docker inspect qiyan-postgres-spike --format "{{json .State.Health}}"
docker exec qiyan-postgres-spike psql -U qiyan_dev -d qiyan_nexus -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker exec qiyan-postgres-spike psql -U qiyan_dev -d qiyan_nexus -c "\dt"
```

Observed:

- health status: `healthy`
- extension: `vector`
- tables: `literature`, `chunks`, `network_tasks`

## Benchmark Results

命令：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend json --iterations 30 --rag-runs 3 --json
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend sqlite --iterations 30 --rag-runs 3 --json
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 30 --rag-runs 3 --json
```

环境说明：

- Windows 11 + PowerShell
- Python: `backend/.uv-test-venv`, Python 3.13.12
- Docker Desktop 4.76.0 + Docker Engine 29.5.2
- PostgreSQL 15.18 + pgvector via `pgvector/pgvector:pg15`
- RAG provider forced to deterministic
- retrieval provider forced to keyword
- 每个 backend 使用隔离临时 seed/runtime 数据
- PostgreSQL run used `--reset-postgresql` to truncate spike tables before the measurement

| Backend | Scenario | Iterations | p50 ms | p95 ms | p99 ms | total ms |
|---|---|---:|---:|---:|---:|---:|
| json | rag_eval_50q_keyword | 3 | 139.667 | 140.628 | 140.628 | 416.893 |
| json | single_literature_insert | 30 | 13.861 | 20.146 | 23.726 | 421.632 |
| json | bulk_chunk_insert_10 | 30 | 148.186 | 171.648 | 182.541 | 4470.056 |
| json | bulk_chunk_insert_50 | 30 | 1011.225 | 1320.686 | 1350.035 | 31605.554 |
| json | get_literature_by_id | 30 | 0.351 | 0.594 | 12.559 | 23.353 |
| json | list_chunks_by_literature_id | 30 | 8.412 | 19.020 | 19.278 | 273.703 |
| sqlite | rag_eval_50q_keyword | 3 | 68.714 | 72.767 | 72.767 | 210.067 |
| sqlite | single_literature_insert | 30 | 0.316 | 0.429 | 0.511 | 9.821 |
| sqlite | bulk_chunk_insert_10 | 30 | 3.400 | 4.192 | 4.450 | 103.660 |
| sqlite | bulk_chunk_insert_50 | 30 | 16.535 | 24.183 | 24.556 | 520.754 |
| sqlite | get_literature_by_id | 30 | 0.017 | 0.025 | 0.117 | 0.619 |
| sqlite | list_chunks_by_literature_id | 30 | 10.207 | 22.353 | 34.111 | 363.228 |
| postgresql | rag_eval_50q_keyword | 3 | 702.888 | 803.375 | 803.375 | 2202.348 |
| postgresql | single_literature_insert | 30 | 1.755 | 2.623 | 3.392 | 57.066 |
| postgresql | bulk_chunk_insert_10 | 30 | 16.207 | 21.846 | 22.222 | 497.769 |
| postgresql | bulk_chunk_insert_50 | 30 | 77.854 | 91.913 | 158.212 | 2454.118 |
| postgresql | get_literature_by_id | 30 | 0.872 | 1.161 | 1.251 | 27.392 |
| postgresql | list_chunks_by_literature_id | 30 | 13.896 | 27.322 | 38.597 | 469.770 |

Interpretation:

- SQLite 比 JSON 在写路径上明显更快：
  - single literature insert p50: ~44x faster
  - 10 chunk insert p50: ~44x faster
  - 50 chunk insert p50: ~61x faster
- PostgreSQL 也明显快于 JSON 写路径：
  - single literature insert p50: ~7.9x faster
  - 10 chunk insert p50: ~9.1x faster
  - 50 chunk insert p50: ~13.0x faster
- SQLite 在当前本地 benchmark 中仍显著快于 PostgreSQL：
  - single literature insert p50: PostgreSQL ~5.6x slower than SQLite
  - 10 chunk insert p50: PostgreSQL ~4.8x slower than SQLite
  - 50 chunk insert p50: PostgreSQL ~4.7x slower than SQLite
  - RAG eval p50: PostgreSQL ~10.2x slower than SQLite
- `list_chunks_by_literature_id` 在该 benchmark 中会受前序 chunk upsert 增长影响；SQLite、JSON、PostgreSQL 结果接近，不应过度解读为各 backend 在索引/并发条件下的真实上限。
- PostgreSQL 当前没有提供足以抵消运维复杂度的性能收益。它的价值仍在未来多人并发、生产数据库治理和真实 pgvector ANN 检索，而不是当前内部预览默认 runtime。

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
- `pytest -q`: `498 passed, 1 skipped`

Additional smoke:

```powershell
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 1 --rag-runs 1 --json
```

结果：PostgreSQL readiness + seed bootstrap + repository read/write smoke 通过，`failures={}`。

## How To Reproduce PostgreSQL Numbers

从仓库根目录运行：

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
cd backend
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 30 --rag-runs 3 --json
```

说明：

- compose 会在 fresh volume 上自动执行 `backend/app/repositories/postgres_schema.sql`；repository 连接时也会执行 idempotent schema，不需要手动 `psql < postgres_schema.sql`。
- `--reset-postgresql` 会 `TRUNCATE` spike 表，仅用于本地 spike 数据库。
- 如果本地数据库连接慢，可通过 `QIYAN_POSTGRES_CONNECT_TIMEOUT` / `QIYAN_POSTGRES_POOL_TIMEOUT` 调整 timeout。

## Decision Criteria For Reopening

当前决策：继续保持 SQLite，不发 PostgreSQL 生产化 ADR。只有满足以下任一条件，才建议重新打开 PostgreSQL 生产化：

- 进入多人并发 reviewer/demo 场景，SQLite 文件锁成为实际瓶颈。
- 需要真正的 pgvector 相似度检索、ANN 索引调参或 embedding 数据治理。
- 需要生产级数据库能力：备份恢复、权限隔离、审计、迁移、监控。
- 在更接近生产的 workload 上，PostgreSQL 实测显著优于 SQLite，尤其是大规模 chunk 写入、并发写入和真实 vector retrieval 路径。

否则保持：

- 默认 backend: JSON
- 可选本地持久化 backend: SQLite
- PostgreSQL: explicit opt-in spike/backend only

## Residual Risks

- 当前 schema 仍是 spike schema，不是 Alembic 管理的生产迁移。
- pgvector 列和 IVFFlat index 只做结构预留，没有接入 retrieval provider。
- optional dependency 已在当前 venv 安装用于 smoke，但默认开发路径仍不应要求 PostgreSQL 依赖。
- benchmark 仍是本地单机、单进程、small seed workload；不能替代生产级并发、长事务、备份恢复、迁移和权限治理评估。
