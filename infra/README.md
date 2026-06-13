# Qiyan Nexus Infrastructure

本目录包含本地开发和生产部署所需的基础设施配置。

## 本地开发环境

### PostgreSQL + pgvector

用于 runtime state 持久化和向量相似度搜索的可选后端。

**启动 Postgres：**

```bash
docker compose up -d postgres
```

**验证健康状态：**

```bash
docker compose ps
# 等待 healthy 状态（~5-10 秒）
```

**配置后端环境变量：**

在 `backend/.env` 中添加：

```env
QIYAN_STATE_BACKEND=postgres
QIYAN_POSTGRES_URL=postgresql://qiyan:qiyan_dev_password@127.0.0.1:5432/qiyan_dev
```

**初始化 schema（自动）：**

Schema 在容器启动时由 `postgres/init/001_schema.sql` 自动创建。

**导入 seed 数据：**

```bash
cd backend
./.venv/Scripts/python.exe scripts/postgres_seed.py --reset
```

**验证 pgvector smoke：**

```bash
cd backend
./.venv/Scripts/python.exe scripts/postgres_pgvector_smoke.py
```

**停止并清理：**

```bash
docker compose down
# 删除数据卷（重置所有数据）
docker compose down -v
```

### 默认行为

- **无 `QIYAN_STATE_BACKEND` 或 `QIYAN_STATE_BACKEND=json`**：使用 JSON 文件存储（`backend/data/runtime/`），无需 Docker。
- **`QIYAN_STATE_BACKEND=sqlite`**：使用 SQLite 存储（`backend/data/runtime/*.db`），无需 Docker。
- **`QIYAN_STATE_BACKEND=postgres`**：需要运行 Postgres 容器。

## 目录结构

```
infra/
├── docker-compose.yml          # 本地开发服务编排
├── postgres/
│   └── init/
│       └── 001_schema.sql      # Postgres schema 初始化
└── README.md                   # 本文件
```

## 后续计划

未来本地开发栈可能包含：
- PgBouncer（连接池）
- Redis（缓存）
- MinIO（对象存储）
- Celery worker + Flower（异步任务）
- Nginx（反向代理）

## 生产部署

生产环境配置（Kubernetes、Terraform、云服务配置等）将在后续添加。当前配置仅用于本地开发和 spike 验证。
