# PostgreSQL Runtime Benchmark Follow-up Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 在有 Docker/PostgreSQL 环境的机器上补跑 PostgreSQL + pgvector 实测数据，并据此决定是否继续生产化投入。

**Architecture:** 当前 PostgreSQL backend 已作为 explicit opt-in spike path 落地，默认 backend 仍是 JSON，SQLite 仍是当前推荐的本地持久化路径。下一步只补运行环境验证、CRUD smoke、benchmark 数据和决策文档，不扩大到 Alembic、PgBouncer 或默认切换。

**Tech Stack:** Windows PowerShell, Docker Compose, PostgreSQL 15 + pgvector, FastAPI repositories, psycopg3, pytest, `backend/scripts/benchmark_storage_backends.py`.

---

## Context

当前事实源：

- `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`
- `docs/handoffs/2026-06-05-postgresql-spike-continuation.md`
- `backend/scripts/benchmark_storage_backends.py`
- `infra/docker-compose.postgresql-spike.yml`
- `infra/postgresql-spike.env.example`
- `backend/app/repositories/postgres_schema.sql`

当前结论：

- PostgreSQL 工程接入已完成。
- JSON/SQLite benchmark 已有数据，SQLite 明显优于 JSON。
- 当前机器无 Docker/PostgreSQL 服务，因此 PostgreSQL runtime benchmark 未完成。
- 默认不变：`QIYAN_STATE_BACKEND="json"`。

## Acceptance Criteria

- PostgreSQL + pgvector 容器可启动并通过 healthcheck。
- PostgreSQL repository CRUD smoke 覆盖 literature、chunk、network task 三类 state。
- `benchmark_storage_backends.py --backend postgresql` 成功输出数据。
- PostgreSQL 数据补写到 `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`。
- 给出明确决策：继续保持 SQLite、推进 PostgreSQL 生产化 ADR，或关闭 PostgreSQL 路线。
- 后端门禁仍全绿。

---

### Task 1: Verify Docker/PostgreSQL Runtime

**Objective:** 确认可运行 PostgreSQL + pgvector spike 容器。

**Files:**

- Read: `infra/docker-compose.postgresql-spike.yml`
- Read: `infra/postgresql-spike.env.example`
- Read: `backend/app/repositories/postgres_schema.sql`

**Step 1: Check Docker availability**

Run:

```powershell
docker --version
docker compose version
```

Expected: both commands print versions.

**Step 2: Start spike database**

Run from repo root:

```powershell
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
docker inspect qiyan-postgres-spike --format "{{json .State.Health}}"
```

Expected: health status becomes `healthy`.

**Step 3: Optional local env override smoke**

If port or credential overrides are needed, create a local env file that stays untracked:

```powershell
Copy-Item infra\postgresql-spike.env.example infra\postgresql-spike.env.local
docker compose --env-file infra/postgresql-spike.env.local -f infra/docker-compose.postgresql-spike.yml up -d
```

Expected: container uses the overridden `QIYAN_POSTGRES_*` values.

**Step 4: Verify pgvector extension path**

Run:

```powershell
docker exec qiyan-postgres-spike psql -U qiyan_dev -d qiyan_nexus -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

Expected: query returns `vector`.

**Step 5: Verify schema auto-init path**

Run:

```powershell
docker exec qiyan-postgres-spike psql -U qiyan_dev -d qiyan_nexus -c "\dt"
```

Expected: tables from `backend/app/repositories/postgres_schema.sql` are present on a fresh volume.

**Step 6: Commit only if compose changes were required**

If `infra/docker-compose.postgresql-spike.yml` needed edits:

```powershell
git add infra/docker-compose.postgresql-spike.yml infra/README.md infra/postgresql-spike.env.example
git commit -m "fix(spike): make PostgreSQL benchmark compose runnable"
```

If no edits were needed, do not commit.

---

### Task 2: Install Optional PostgreSQL Dependencies

**Objective:** Ensure the backend test venv can import psycopg and psycopg_pool.

**Files:**

- Read: `backend/pyproject.toml`

**Step 1: Install optional dependency group**

Run:

```powershell
cd backend
uv pip install --python .\.uv-test-venv\Scripts\python.exe "psycopg[binary,pool]>=3.1.0"
```

Expected: installs `psycopg`, `psycopg-binary`, and `psycopg-pool`.

**Step 2: Smoke import**

Run:

```powershell
& .\.uv-test-venv\Scripts\python.exe -c "import psycopg, psycopg_pool; print(psycopg.__version__)"
```

Expected: prints a psycopg version.

---

### Task 3: Run PostgreSQL Repository CRUD Smoke

**Objective:** Verify the opt-in repository path works against real PostgreSQL before benchmarking.

**Files:**

- Read: `backend/app/repositories/postgres_literature.py`
- Read: `backend/app/repositories/postgres_chunk.py`
- Read: `backend/app/repositories/postgres_network_tasks.py`
- Read: `backend/app/repositories/runtime_storage.py`

**Step 1: Reset spike tables**

Run from `backend`:

```powershell
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 1 --rag-runs 1 --json
```

Expected: benchmark succeeds, proving schema + seed bootstrap + repository reads/writes work.

**Step 2: If it fails, isolate the failing repository**

Run:

```powershell
$env:QIYAN_STATE_BACKEND="postgresql"
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -c "from app.repositories.runtime_storage import get_literature_repository, get_chunk_repository, get_network_task_repository; print(len(get_literature_repository().list_items())); print(len(get_chunk_repository().list_chunks())); print(get_network_task_repository().read_all())"
```

Expected: literature/chunk counts are non-zero and network task list is valid.

**Step 3: Fix only contract mismatches**

If code changes are needed, keep them scoped to:

- `backend/app/repositories/postgres_common.py`
- `backend/app/repositories/postgres_literature.py`
- `backend/app/repositories/postgres_chunk.py`
- `backend/app/repositories/postgres_network_tasks.py`
- `backend/app/repositories/postgres_schema.sql`

Do not change JSON/SQLite defaults.

---

### Task 4: Run Comparable Benchmarks

**Objective:** Produce comparable JSON/SQLite/PostgreSQL benchmark numbers.

**Files:**

- Read/Run: `backend/scripts/benchmark_storage_backends.py`
- Modify: `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`

**Step 1: Run JSON baseline**

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend json --iterations 30 --rag-runs 3 --json
```

Expected: JSON result payload with no failures.

**Step 2: Run SQLite baseline**

```powershell
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend sqlite --iterations 30 --rag-runs 3 --json
```

Expected: SQLite result payload with no failures.

**Step 3: Run PostgreSQL baseline**

```powershell
$env:QIYAN_POSTGRES_DSN="postgresql://qiyan_dev:qiyan_dev_pass@localhost:5432/qiyan_nexus"
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 30 --rag-runs 3 --json
```

Expected: PostgreSQL result payload with no failures.

**Step 4: Record benchmark table**

Update `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`:

- Add PostgreSQL rows to the benchmark table.
- Keep JSON/SQLite rows from the same run when possible.
- Note hardware/runtime environment.
- Preserve the current caveat that pgvector retrieval is not implemented.

---

### Task 5: Decide Whether To Productionize

**Objective:** Convert benchmark evidence into a clear product/engineering decision.

**Files:**

- Modify: `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`
- Optional Create: `docs/adr/0015-postgresql-runtime-backend.md`

**Step 1: Apply decision rules**

Use these rules:

- If PostgreSQL is not meaningfully faster than SQLite and no concurrent/multi-user pressure exists, keep SQLite and stop.
- If PostgreSQL is faster but adds operational complexity without near-term need, keep it opt-in and defer production ADR.
- If PostgreSQL clearly wins and product roadmap needs concurrent writes or pgvector retrieval, draft an ADR.

**Step 2: Update verdict**

Expected verdict format:

```markdown
## Final Verdict

Decision: KEEP_SQLITE | PRODUCTIONIZE_POSTGRESQL | CLOSE_POSTGRESQL_PATH

Rationale:
- ...

Next action:
- ...
```

**Step 3: Commit documentation update**

```powershell
git add docs/evaluations/2026-06-05-postgresql-pgvector-spike.md
git commit -m "docs(spike): add PostgreSQL runtime benchmark verdict"
```

---

### Task 6: Run Backend Gates

**Objective:** Ensure the repository remains healthy after any fixes or docs updates.

**Files:**

- No direct edits expected.

**Step 1: Run standard backend gate**

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Expected:

- format pass
- lint pass
- mypy pass
- pytest pass

**Step 2: Check diff hygiene**

```powershell
cd ..
git diff --check
git status --short
```

Expected: no whitespace errors; only intended files changed.

---

## Stop Conditions

Stop and record a PARTIAL result if:

- Docker cannot be installed or started on the target machine.
- `pgvector/pgvector:pg15` cannot be pulled.
- PostgreSQL container starts but pgvector extension cannot be created.
- Repository CRUD smoke fails in a way that requires broader migration architecture.

Do not silently broaden scope into:

- production migration framework
- PgBouncer
- real embedding/vector retrieval
- default backend switch
- cloud PostgreSQL provisioning
