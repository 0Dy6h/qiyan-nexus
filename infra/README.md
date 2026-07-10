# Infra

本目录保存当前阶段可选本地基础设施配置。默认开发路径仍不依赖 Docker：

- 后端默认 `QIYAN_STATE_BACKEND="json"`
- 可选本地持久化 backend 是 SQLite
- PostgreSQL + pgvector 仅用于 spike / benchmark，不进入默认内部预览路径

## PostgreSQL + pgvector Spike

配置文件：

- `infra/docker-compose.postgresql-spike.yml`

用途：

- 启动本地 PostgreSQL 15 + pgvector
- 自动初始化 `backend/app/repositories/postgres_schema.sql`
- 配合 `backend/scripts/benchmark_storage_backends.py` 补跑 PostgreSQL runtime benchmark

### Prerequisites

当前机器需要先安装并启动 Docker Desktop，且 PowerShell 能找到：

```powershell
docker --version
docker compose version
```

Docker 可用性属于每台机器的运行前提，不在长期文档中记录瞬时主机状态。PostgreSQL/pgvector 的历史 benchmark 结论见 `docs/current-state.md`，默认 runtime backend 仍不因此翻转。

### Start

从仓库根目录运行：

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
docker inspect qiyan-postgres-spike --format "{{json .State.Health}}"
```

默认连接信息：

```text
host: 127.0.0.1
port: 5432
database: qiyan_nexus
user: qiyan_dev
password: qiyan_dev_pass
```

DSN:

```text
postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus
```

### Optional Env Overrides

可复制 `infra/postgresql-spike.env.example` 为本地 env 文件，然后通过 `--env-file` 使用：

```powershell
Copy-Item infra\postgresql-spike.env.example infra\postgresql-spike.env.local
docker compose --env-file infra/postgresql-spike.env.local -f infra/docker-compose.postgresql-spike.yml up -d
```

可覆盖项：

- `QIYAN_POSTGRES_DB`
- `QIYAN_POSTGRES_USER`
- `QIYAN_POSTGRES_PASSWORD`
- `QIYAN_POSTGRES_PORT`

### Schema Initialization

compose 会把以下文件挂载到 PostgreSQL entrypoint：

```text
backend/app/repositories/postgres_schema.sql
```

挂载目标：

```text
/docker-entrypoint-initdb.d/01_qiyan_schema.sql
```

这只会在 volume 第一次初始化时自动执行。若 volume 已存在，PostgreSQL 不会重新跑 entrypoint SQL；不过后端 PostgreSQL repository 也会在连接时执行 idempotent schema，因此日常 smoke 不需要手动 `psql < postgres_schema.sql`。

若要强制从空库重建：

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml down -v
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
```

注意：`down -v` 会删除本地 spike 数据。

### Backend Smoke

安装可选依赖：

```powershell
cd backend
uv pip install --python .\.uv-test-venv\Scripts\python.exe "psycopg[binary,pool]>=3.1.0"
```

运行 PostgreSQL benchmark smoke：

```powershell
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 1 --rag-runs 1 --json
```

完整 benchmark：

```powershell
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 30 --rag-runs 3 --json
```

### Stop

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml down
```

删除数据 volume：

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml down -v
```

## Deferred Infrastructure

以下仍是后续候选，不在当前默认路径中：

- PgBouncer
- Redis
- MinIO
- Celery worker
- Flower
- Nginx
