# Session Handoff — 2026-06-02（SQLite runtime backend 文档补丁）

branch: feat/cross-lingual-term-bridge（仅文档/配置补丁，未提交）
default state backend: `json`，未变
stopped at: SQLite 后端已在 commit 4144357 实装，本次只补齐 .env.example / current-state / handoff 文档缺口

## Goal

commit `4144357 feat(runtime): add sqlite backend and network report enhancements`
落地了 protocol-based repository 抽象 + SQLite 后端 + 工厂层 + 双 backend 测试，但
没有写 handoff、`.env.example` 未列新 env、`docs/current-state.md` 仍把 SQLite 列为
"future spike 候选"。本次只做**最小文档补丁**沉淀事实，不再写新代码。

## Current state

- Repository 层：`backend/app/repositories/protocols.py` 定义 `LiteratureRepository`、
  `ChunkRepository`、`NetworkTaskRepositoryProtocol` 三个 Protocol；服务层
  （`services/literature.py`、`services/rag.py`、`services/network.py`、
  `services/fake_parser.py`）通过 `runtime_storage.py` 的工厂函数取实现，不直接
  import in-memory / sqlite 类。
- SQLite 实现：`sqlite_literature.py`（293 行）、`sqlite_chunk.py`（200 行）、
  `sqlite_network_tasks.py`（196 行）；纯 stdlib `sqlite3`、WAL mode、JSON TEXT 列
  存复杂类型、首次访问时从 JSON seed bootstrap、`close()` 释放连接（Windows tmp
  清理需要）。
- 工厂：`runtime_storage.py` 读取 `QIYAN_STATE_BACKEND`（默认 `json`），模块级缓存，
  `clear_*_repository_cache()` 供测试隔离；数据库路径默认
  `backend/data/runtime/qiyan_state.sqlite3`，可通过 `QIYAN_SQLITE_DB_PATH` 覆盖。
- 测试：`test_literature_repository_backends.py`、`test_chunk_repository_backends.py`、
  `test_network_task_repository_backends.py` 参数化覆盖两个 backend；
  `conftest.py` 的 `isolate_runtime_state` fixture 按 env 切 backend、隔离 SQLite
  到 tmp 目录、test 前后清缓存。
- gitignore：`backend/data/runtime/**` 已覆盖 `qiyan_state.sqlite3`，无需新增。

## Completed in this session

- 双 backend 全量验证：
  - `QIYAN_STATE_BACKEND=sqlite QIYAN_SQLITE_DB_PATH=/tmp/...sqlite3 pytest -q` → 439 passed, 6 skipped。
  - 默认（json）`pytest -q` → 444 passed, 1 skipped。
  - 两边 skip 数差异是 backend-specific 测试主动 skip，不是失败。
- 补 `backend/.env.example`：新增 `QIYAN_STATE_BACKEND="json"` 与 `QIYAN_SQLITE_DB_PATH=""`
  两个变量及注释，说明默认 / 切换路径 / 路径覆盖语义。
- 改 `docs/current-state.md`：
  - "数据" 段补充 SQLite backend 已落地、走 protocol 抽象、env 切换的事实。
  - "下一步候选" §6 把 "runtime JSON → SQLite spike" 改为 "已落地（commit 4144357）"，
    PostgreSQL spike 仍保留为后续候选。

## Still open / blocked

- 没写 ADR：protocol-based repository abstraction + env-toggled backend 是架构决策，
  当前认为属于 "JSON 的等价升级"，不强制写 ADR；如需补，可另开。
- README.md 没加 backend 切换说明：本次按"最小补丁"指令未动 README，仅靠
  `.env.example` 注释自证；如需 README 一段，另开。
- Commit 4144357 同时改了 `app/api/network.py`、`services/network.py`（+156 行）、
  `frontend/components/NetworkGraph.tsx`（+161 行）、`test_network_report_service.py`
  （+187 行新文件），本次未审 network 报告相关新增；如需单独走查 network 增量，另开任务。
- 本次改动均未 commit。

## Key files and artifacts

- `backend/app/repositories/protocols.py`、`runtime_storage.py`、`sqlite_*.py`
- `backend/app/repositories/literature.py`、`chunk.py`、`network_tasks.py`（in-memory 实现）
- `backend/tests/test_*_repository_backends.py`、`backend/tests/conftest.py`
- `backend/.env.example`（本次新增 2 个 env）
- `docs/current-state.md`（本次更新 "数据" 段与 §6 候选）
- 数据库文件：`backend/data/runtime/qiyan_state.sqlite3`（gitignored，bootstrap 自 seed）

## Verification

- `QIYAN_STATE_BACKEND=sqlite QIYAN_SQLITE_DB_PATH=/tmp/test_sqlite_$$.sqlite3 ./.uv-test-venv/Scripts/python.exe -m pytest -q` — 439 passed, 6 skipped。
- `./.uv-test-venv/Scripts/python.exe -m pytest -q` — 444 passed, 1 skipped。
- 未跑 ruff format / ruff check / mypy / frontend gauntlet：本次只改文档与 `.env.example`，
  没动 `app/` 或 `tests/` Python 源码，也未触前端。

## Recommended next step

跨语线纯术语桥已收口（见 `2026-06-02-cross-lingual-term-bridge.md`）。SQLite 文档
补丁后，下一步候选维持 `docs/current-state.md` §下一步候选 列表，可选方向：

1. 受控打分修复（让 `microbiome` 参与 `+7` tag-bonus 救回 rag-eval-035/047，需全量重验 50 题 RAG eval）
2. BGE=0.3 + NLI=0.5 是否升 L2 治理决策
3. 网络图交互增强（hover 高亮边、节点点击聚焦）
4. PostgreSQL spike（仅当真的要演示并发 / 跨进程读写时再做）

## Recommended reading order

1. `docs/current-state.md`（已更新）
2. `backend/.env.example`（已更新）
3. `backend/app/repositories/protocols.py`、`runtime_storage.py`
4. `backend/app/repositories/sqlite_literature.py`（其余两个 sqlite 文件结构相同）
5. `backend/tests/conftest.py` 的 `isolate_runtime_state` fixture
