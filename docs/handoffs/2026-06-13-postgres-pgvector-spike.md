# Session Closeout: PostgreSQL/pgvector Opt-in Spike

**Date:** 2026-06-13  
**Branch:** `feat/compute-platform-scripts` (继续使用现有分支)  
**Status:** ✅ Complete — 所有门禁绿色，PostgreSQL backend 可用

---

## 完成工作

### 阶段 1：修复后端门禁

修复了 4 个 lint 错误和 1 个 type 错误：

1. 移除 `app/repositories/literature.py` 和 `app/repositories/chunk.py` 中未使用的 `json` import
2. 规范 `app/services/pubmed.py` 和 `tests/test_llm_provider.py` 的 import 顺序
3. 修改 `app/repositories/_json_helpers.py::read_json_list`：使用 `object` 接收 `json.loads`，校验后返回 `list[dict[str, Any]]`，消除 `no-any-return` 错误

**验收：**
```bash
cd backend
.venv/Scripts/python.exe -m ruff format --check app tests  # ✅ 115 files
.venv/Scripts/python.exe -m ruff check app tests           # ✅ All checks passed
.venv/Scripts/python.exe -m mypy app                       # ✅ Success
.venv/Scripts/python.exe -m pytest -q                      # ✅ 489 passed, 1 skipped
```

### 阶段 2：PostgreSQL/pgvector Opt-in Backend

**基础设施：**

- `infra/docker-compose.yml`：PostgreSQL 16 + pgvector 容器定义
- `infra/postgres/init/001_schema.sql`：扁平化 schema（匹配 SQLite/JSON），`vector(128)` embedding 列
- `infra/README.md`：Docker 启动、seed、smoke test 指令

**Repository 实现：**

- `app/repositories/postgres_literature.py`：实现 `LiteratureRepository` protocol
- `app/repositories/postgres_chunk.py`：实现 `ChunkRepository` protocol
- `app/repositories/postgres_network_tasks.py`：实现 `NetworkTaskRepositoryProtocol` protocol
- 所有 repository 使用短连接（每方法 `_connect()`），`close()` 为 no-op，连接池推迟到生产优化

**工厂集成：**

- 更新 `app/repositories/runtime_storage.py`：三个工厂函数（`get_literature_repository`, `get_chunk_repository`, `get_network_task_repository`）均支持 `backend="postgres"`
- 新增环境变量：`QIYAN_POSTGRES_URL`（postgres backend 必需）
- 更新 `.env.example`：说明 postgres 是显式 opt-in

**脚本与工具：**

- `scripts/postgres_seed.py`：从 `sample_ad_literature.json` 和 `sample_ad_chunks.json` 导入；支持 `--reset` 清空重导
- `scripts/postgres_pgvector_smoke.py`：用 `HashingEmbeddingBackend` 写入 embedding，执行 cosine distance top-k 查询，验证 pgvector 端到端可用

**依赖：**

- `pyproject.toml`：新增 `psycopg[binary]>=3.2.0` 和 `pgvector>=0.3.0`

---

## 架构决策

1. **扁平化 schema 而非嵌套 JSONB**  
   PostgreSQL schema 匹配 SQLite/JSON 的扁平结构（`pdf_upload_id`, `pdf_file_name`, `pdf_parse_status`, ... 作为独立列），而不是嵌套的 `pdf_metadata` JSONB 对象。保持三个 backend 的 wire protocol 一致。

2. **短连接 + 推迟连接池**  
   每个 repository 方法打开新连接，方法结束后自动关闭（psycopg `with` 上下文）。连接池（PgBouncer / psycopg 内置池）推迟到生产压测后再引入。

3. **同步 psycopg3**  
   使用同步 `psycopg` 而非 `psycopg[async]`，与现有 SQLite/JSON repository 保持一致。异步 repository 是后续优化方向，不在本 spike 范围。

4. **pgvector 仅 smoke，不改默认检索**  
   `postgres_pgvector_smoke.py` 验证 pgvector 可用性，但不修改 `QIYAN_RETRIEVAL_PROVIDER` 默认值（仍为 `hashing + keyword`）。RAG 切到 pgvector 是后续独立 slice。

---

## 使用说明

### 启动 PostgreSQL

```bash
cd infra
docker compose up -d postgres
# 等待 healthy（~5-10 秒）
docker compose ps
```

### 配置环境变量

在 `backend/.env` 中添加：

```env
QIYAN_STATE_BACKEND=postgres
QIYAN_POSTGRES_URL=postgresql://qiyan:qiyan_dev_password@127.0.0.1:5432/qiyan_dev
```

### 导入 seed 数据

```bash
cd backend
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
   ✅ Inserted 20 literature items (skipped 0 existing)
📥 Seeding chunks...
   ✅ Inserted 45 chunks (skipped 0 existing)

✅ Seed complete!
   Literature: 20 rows
   Chunks:     45 rows
   Tasks:      0 rows
```

### 验证 pgvector

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
   ✅ Updated 45 chunks (skipped 0 with existing embeddings)

🔍 Running pgvector cosine distance query...
   Query: 特应性皮炎的发病机制
   Top 5 results:

   1. cn-ad-gbs-001-c0 (lit: cn-ad-gbs-001)
      Similarity: 0.8571
      Preview: 围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述...

   ...

✅ pgvector smoke test passed!
   - Embeddings written to literature_chunk.embedding
   - Cosine distance query returned stable results
   - Ready for future RAG integration
```

### 运行后端服务

```bash
cd backend
.venv/Scripts/python.exe -m fastapi dev app/main.py
# 或使用 bash wrapper: fastapi dev app/main.py
```

后端会读取 `.env` 中的 `QIYAN_STATE_BACKEND=postgres` 并连接 PostgreSQL。

### API smoke test

```bash
# 文献列表
curl http://127.0.0.1:8000/api/literature/search?q=特应性皮炎

# 单条文献
curl http://127.0.0.1:8000/api/literature/cn-ad-gbs-001

# RAG 回答（会引用 chunk）
curl -X POST http://127.0.0.1:8000/api/rag/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "特应性皮炎的中医治疗方法有哪些？"}'
```

### 停止并清理

```bash
cd infra
docker compose down        # 停止容器，保留数据
docker compose down -v     # 停止容器，删除数据卷（完全重置）
```

---

## 未完成工作（后续 slice）

1. **Postgres backend contract tests**  
   参数化现有 repository tests，增加 `QIYAN_RUN_POSTGRES_TESTS=1` 分支，仅在明确设置时运行 postgres 测试（避免 CI/默认 pytest 依赖 Docker）。

2. **连接池**  
   引入 PgBouncer 或 psycopg connection pool，测量压测下的连接复用收益。

3. **异步 repository**  
   探索 `psycopg[async]` + `asyncpg`，配合 FastAPI 异步路由使用。

4. **RAG 默认检索切到 pgvector**  
   修改 `services/rag.py` 使用 pgvector cosine distance 查询代替 keyword tokenization，需要先完成 embedding backend 切换和 grounding 阈值重新校准。

5. **生产迁移系统**  
   引入 Alembic / Flyway 管理 schema 版本和数据迁移。

6. **备份与恢复**  
   定义 PostgreSQL 备份策略（pg_dump / WAL archive / point-in-time recovery）。

---

## 不变量验收

- ✅ 默认无 env 时仍使用 JSON runtime backend
- ✅ `QIYAN_STATE_BACKEND=sqlite` 仍通过既有 repository tests
- ✅ `/api/rag/answer` 免责声明仍为 `非诊断结论、需结合临床。`
- ✅ CORS 仍仅 `GET, POST`
- ✅ 前端 `pnpm test` 与 `pnpm typecheck` 未受影响（本 slice 未修改前端）

---

## 提交建议

```bash
git add infra/ backend/app/repositories/postgres_*.py backend/scripts/postgres_*.py
git add backend/app/repositories/runtime_storage.py backend/pyproject.toml backend/.env.example
git add docs/handoffs/2026-06-13-postgres-pgvector-spike.md
git commit -m "feat(infra): PostgreSQL/pgvector opt-in backend spike

- Add Docker compose for postgres:16 + pgvector
- Implement PostgresLiteratureRepository, PostgresChunkRepository, PostgresNetworkTaskRepository
- Integrate into runtime_storage.py factory (QIYAN_STATE_BACKEND=postgres)
- Add postgres_seed.py and postgres_pgvector_smoke.py scripts
- Update .env.example and infra/README.md with usage instructions
- Fix lint/type errors: remove unused imports, normalize import order, fix _json_helpers return type

All gates green: ruff format ✅, ruff check ✅, mypy ✅, pytest 489 passed ✅

Ref: docs/handoffs/2026-06-13-postgres-pgvector-spike.md"
```

---

## 技术债务

1. **seed script 无事务回滚**  
   `postgres_seed.py` 在 insert 失败时不回滚已插入的行。生产迁移应使用 `BEGIN; ... COMMIT;` 或 Alembic。

2. **pgvector IVF index 未调优**  
   `001_schema.sql` 使用 `lists = 100`，适合小数据集（<1000 chunks）。生产数据量增长后需调整 `lists` 参数或切换到 HNSW。

3. **embedding 维度硬编码**  
   `vector(128)` 对应 `HashingEmbeddingBackend`，切换 embedding model（如 bge-m3 的 1024 维）需迁移 schema。

4. **短连接在高并发下低效**  
   每请求 1-3 次连接建立（~5-10ms overhead per connect）。压测后若成为瓶颈，引入连接池。

---

## 参考资料

- pgvector 官方文档：https://github.com/pgvector/pgvector
- pgvector-python：https://github.com/pgvector/pgvector-python
- psycopg3 文档：https://www.psycopg.org/psycopg3/docs/
- ADR-0010：模块路线图（MVP-A / MVP-B / MVP-C 边界）
