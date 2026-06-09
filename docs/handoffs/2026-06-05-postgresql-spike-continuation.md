# PostgreSQL Spike Continuation — 2026-06-05

date: 2026-06-05  
status: PARTIAL, waiting for Docker/PostgreSQL runtime  

## Completed

- Hardened the opt-in PostgreSQL backend implementation:
  - `backend/app/repositories/postgres_literature.py`
  - `backend/app/repositories/postgres_chunk.py`
  - `backend/app/repositories/postgres_network_tasks.py`
  - `backend/app/repositories/postgres_common.py`
- Added optional dependency group:
  - `backend/pyproject.toml` → `[project.optional-dependencies].postgresql`
- Documented env knobs:
  - `QIYAN_STATE_BACKEND="postgresql"`
  - `QIYAN_POSTGRES_DSN`
  - `QIYAN_POSTGRES_CONNECT_TIMEOUT`
  - `QIYAN_POSTGRES_POOL_TIMEOUT`
- Added benchmark harness:
  - `backend/scripts/benchmark_storage_backends.py`
- Updated spike result document:
  - `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`

## Evidence

Backend gates:

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

Result:

- format: pass
- lint: pass
- mypy: pass
- pytest: `498 passed, 1 skipped in 15.14s`

Benchmark evidence:

- JSON and SQLite baselines recorded in `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md`
- PostgreSQL smoke fails cleanly because this machine has no Docker/PostgreSQL service:

```json
{
  "results": {},
  "failures": {
    "postgresql": "RuntimeError: PostgreSQL is not reachable. Start infra/docker-compose.postgresql-spike.yml and retry."
  }
}
```

Environment check:

- no `docker`
- no `psql`
- no `pg_ctl`
- no `podman`
- no Windows PostgreSQL service found

## Remaining Work

When a machine with Docker is available:

```powershell
cd backend
uv pip install --python .\.uv-test-venv\Scripts\python.exe "psycopg[binary,pool]>=3.1.0"
cd ..
docker compose -f infra/docker-compose.postgresql-spike.yml up -d
cd backend
& .\.uv-test-venv\Scripts\python.exe -m scripts.benchmark_storage_backends --backend postgresql --reset-postgresql --iterations 30 --rag-runs 3 --json
```

Then update:

- `docs/evaluations/2026-06-05-postgresql-pgvector-spike.md` with PostgreSQL numbers
- final verdict if PostgreSQL materially changes the SQLite recommendation

## Current Recommendation

Keep JSON as the default runtime backend and SQLite as the practical local persistent backend. PostgreSQL remains explicit opt-in spike code until real PostgreSQL/pgvector numbers justify productionization.

