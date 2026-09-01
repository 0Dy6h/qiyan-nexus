# PostgreSQL/pgvector Spike 验证清单

## ✅ 已完成工作

### 代码与配置
- [x] 修复所有 lint/type 门禁错误
- [x] 新增 `postgres_literature.py`, `postgres_chunk.py`, `postgres_network_tasks.py`
- [x] 更新 `runtime_storage.py` 工厂函数支持 postgres backend
- [x] 新增 `psycopg[binary]>=3.2.0` 和 `pgvector>=0.3.0` 依赖
- [x] 创建 `infra/docker-compose.yml` 和 `001_schema.sql`
- [x] 创建 `postgres_seed.py` 和 `postgres_pgvector_smoke.py` 脚本
- [x] 更新 `.env.example` 和 `README.md` 文档

### 门禁验收
```bash
cd backend
.venv/Scripts/python.exe -m ruff format --check app tests  # ✅ 115 files
.venv/Scripts/python.exe -m ruff check app tests           # ✅ All checks passed
.venv/Scripts/python.exe -m mypy app                       # ✅ Success, 59 files
.venv/Scripts/python.exe -m pytest -q                      # ✅ 489 passed, 1 skipped
```

## 🔧 待验证（需要 Docker Desktop 运行）

### 1. 启动 PostgreSQL
```bash
# 先启动 Docker Desktop，然后：
cd infra
docker compose up -d postgres
docker compose ps  # 确认状态为 healthy
```

### 2. 导入 seed 数据
```bash
cd backend
# 设置环境变量
export QIYAN_POSTGRES_URL="postgresql://qiyan:qiyan_dev_password@127.0.0.1:5432/qiyan_dev"
# 或在 .env 中添加 QIYAN_POSTGRES_URL

.venv/Scripts/python.exe scripts/postgres_seed.py --reset
```

预期输出：
```
📦 Loading seed data from D:\Projects\Tcm_tech\backend\data
   Found 20 literature items, 45 chunks
🔌 Connecting to PostgreSQL...
⚠️  Clearing all tables...
✅ Tables cleared
📥 Seeding literature...
   ✅ Inserted 20 literature items
📥 Seeding chunks...
   ✅ Inserted 45 chunks
✅ Seed complete!
   Literature: 20 rows
   Chunks:     45 rows
   Tasks:      0 rows
```

### 3. 验证 pgvector smoke
```bash
cd backend
.venv/Scripts/python.exe scripts/postgres_pgvector_smoke.py
```

预期输出：
```
🔌 Connecting to PostgreSQL...
📦 Loading chunks from database...
   Found 45 chunks
🧮 Generating embeddings...
   ✅ Updated 45 chunks
🔍 Running pgvector cosine distance query...
   Query: 特应性皮炎的发病机制
   Top 5 results:
   1. cn-ad-gbs-001-c0 (Similarity: 0.8571)
   ...
✅ pgvector smoke test passed!
```

### 4. API smoke test
```bash
# 在 backend/.env 中设置：
# QIYAN_STATE_BACKEND=postgres
# QIYAN_POSTGRES_URL=postgresql://qiyan:qiyan_dev_password@127.0.0.1:5432/qiyan_dev

cd backend
.venv/Scripts/python.exe -m fastapi dev app/main.py

# 在另一个终端：
curl "http://127.0.0.1:8000/api/literature/search?q=特应性皮炎"
curl "http://127.0.0.1:8000/api/literature/cn-ad-gbs-001"
curl -X POST "http://127.0.0.1:8000/api/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{"question": "特应性皮炎的中医治疗方法有哪些？"}'
```

### 5. 停止容器
```bash
cd infra
docker compose down        # 停止，保留数据
docker compose down -v     # 停止并删除数据卷
```

## 📋 后续工作（未来 slice）

1. **Repository backend contract tests**  
   参数化现有 repository tests，增加 `QIYAN_RUN_POSTGRES_TESTS=1` 分支。

2. **连接池优化**  
   引入 PgBouncer 或 psycopg connection pool。

3. **异步 repository**  
   探索 `psycopg[async]` + FastAPI 异步路由。

4. **RAG 切到 pgvector**  
   修改 `services/rag.py` 使用 pgvector cosine distance 查询。

5. **生产迁移系统**  
   引入 Alembic / Flyway。

## 🎯 提交命令

```bash
git add infra/ backend/app/repositories/postgres_*.py backend/scripts/postgres_*.py
git add backend/app/repositories/runtime_storage.py backend/pyproject.toml backend/.env.example
git add backend/app/repositories/_json_helpers.py backend/app/repositories/literature.py backend/app/repositories/chunk.py
git add backend/app/services/pubmed.py backend/tests/test_llm_provider.py
git add docs/handoffs/2026-06-13-postgres-pgvector-spike.md infra/README.md README.md
git status  # 检查是否有遗漏

git commit -m "feat(infra): PostgreSQL/pgvector opt-in backend spike

- Add Docker compose for postgres:16 + pgvector
- Implement PostgresLiteratureRepository, PostgresChunkRepository, PostgresNetworkTaskRepository
- Integrate into runtime_storage.py factory (QIYAN_STATE_BACKEND=postgres)
- Add postgres_seed.py and postgres_pgvector_smoke.py scripts
- Update .env.example, README.md, and infra/README.md with usage instructions
- Fix lint/type errors: remove unused imports, normalize import order, fix _json_helpers return type

All gates green: ruff format ✅, ruff check ✅, mypy ✅, pytest 489 passed ✅

Ref: docs/handoffs/2026-06-13-postgres-pgvector-spike.md"
```

## 🔍 当前状态

- **Docker Desktop**: 未运行（需要手动启动后才能验证 PostgreSQL 功能）
- **代码质量**: 所有门禁绿色
- **默认行为**: 仍使用 JSON backend，不依赖 Docker
- **PostgreSQL**: 可选 opt-in，文档和脚本已就绪

## ℹ️ 说明

PostgreSQL backend 是**可选功能**，不影响默认开发流程：
- 无需 Docker 即可运行现有测试和开发服务器
- 默认使用 `backend/data/runtime/*.json` 存储
- PostgreSQL 仅在显式设置 `QIYAN_STATE_BACKEND=postgres` 时启用
