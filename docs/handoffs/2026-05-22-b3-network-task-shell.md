# B3 — 网络药理学任务壳（2026-05-22）

> 阶段 B 第三颗 slice。把现有 `_TASKS` in-memory mock 升级为 runtime state 持久化；前端补 `/network` 页面跑通「成分-靶点-通路-疾病」链。
> 前置 slice：B2（`docs/handoffs/2026-05-22-b2-rag-eval-50q.md`）。

## 落地点

- **runtime 存储**：新增 `backend/data/runtime/network_tasks_state.json`（gitignored），首次访问 bootstrap 成 `[]\n`，env 覆盖名 `NETWORK_TASKS_RUNTIME_STATE_PATH`。
- **repository**：新建 `app/repositories/network_tasks.py`，提供 `read_all / get / upsert`，直接 Path I/O 镜像 `literature.py` 模式。
- **schema**：`app/schemas/network.py` 新增 `NetworkTaskRecord`（task_id / query / analysis_type / status / progress / poll_count / result / created_at）。
- **service**：`app/services/network.py` 重写 —— 删除 `_TASKS: dict` 与 `_NetworkTaskState` dataclass，所有任务态走 repository；`create_*` 写 queued 行，`get_*_result` 按 `poll_count` 推进 queued→running→completed 并落盘。
- **前端 API**：新增 `frontend/lib/api/network.ts`，导出 `submitNetworkAnalysis` / `fetchNetworkResult` / URL builders / 类型 + 标签 helper。
- **前端组件**：新增 `frontend/components/NetworkAnalysisClient.tsx`，状态机 `idle | submitting | polling | completed | error`，提交后 `setTimeout` 递归轮询，间隔 800ms，最多 10 次，cleanup 用 `mountedRef`。
- **前端页面**：新增 `frontend/app/network/page.tsx`，镜像 `/rag` 页壳（`clamp(20px,4vw,48px)` padding + workbench nav + `Evidence workbench` eyebrow + `使用提醒` block）。
- **nav 接入**：`getComplianceNavigationLinks()` 数组追加 `/network`；首页 `app/page.tsx` 增加「进入网络药理学」按钮。
- **测试**：
  - 后端：`test_network_api.py` 已有 5 条 + 新增 1 条 `test_network_task_state_is_persisted_to_runtime_file`（覆盖：POST 后磁盘有 queued 行 → 第一次 GET 后变 running → 重新 `TestClient(app)` 模拟重启 → 第二次 GET 拿到 completed）；自动 fixture `_isolate_network_tasks_runtime` 隔离 runtime 路径。
  - 后端：`test_runtime_storage.py` 增 3 条覆盖 `resolve_network_tasks_storage_path`（bootstrap-to-empty / preserve-existing / once-only）。
  - 前端：新增 `tests/network-api.test.ts` 6 条（URL builders / label / submit happy path / 完成态 result shape / 错误路径 `Network result request failed`）。
  - 前端：`page-shell-consistency.test.ts` `pages` 数组追加 `["app/network/page.tsx", "/network"]`；`compliance-page.test.ts` deepEqual 同步追加 `/network` 项。

## 行为契约

| 维度 | 行为 |
|---|---|
| `POST /api/network/analyze` | 仍返回 `{task_id, status:"queued", progress:0}`；同时把 record 写到 runtime JSON |
| `GET /api/network/result/{task_id}` 首次 | status=running, progress=60, result=null（与 B3 前一致） |
| 同 task 第二次/以后 | status=completed, progress=100, result=mock 3-链；幂等（poll_count 单增但 status 不回退） |
| 跨进程重启 | 同 task 在新进程仍能查到 completed 状态（落盘 runtime file 验证） |
| 任务 ID 前缀 | `network-` |
| `query=""` | 422（unchanged） |
| nav 顺序 | `/ → /literature → /rag → /network → /evals/rag-ad`（compliance test deepEqual 锁） |
| 页面壳 | nav + `Evidence workbench` eyebrow + `使用提醒` block（page-shell-consistency test 锁） |
| `disclaimer` | 仍是 `非诊断结论、需结合临床。` byte-identical（service 复用 `app.services.rag.DISCLAIMER`） |

## 调试痕迹

无 fail 翻车，但有两处实现期判断：

1. **runtime 文件初始化策略**：literature/chunk 用 `write_bytes(_SAMPLE_PATH.read_bytes())` 从 seed 复制；network task 没 seed，初始化写 `[]\n`。否则 `json.loads` 在第一次跑时会 raise。
2. **service 层 repository 获取方式**：用 `_get_repository()` per-call 工厂，而不是模块顶层全局。原因：测试 `monkeypatch.setenv` 必须在 import 之后生效；若顶层就缓存 path，测试用例间会串。

## 不在 B3 范围

- 不接 KEGG / STRING / 真实 herb/compound/target/pathway 数据集（→ B4）
- 不做 RAG citation ↔ network entity 跳转（→ B5）
- 不做数据来源切换面板（→ B6）
- 不引入真实异步队列（Celery / Redis）；保留 poll_count 单进程模拟
- 不持久化「前端表单状态」；刷新页面回到 idle 是预期行为（后端 task 仍可被同 ID 查到）

## 验证

```bash
cd backend
.venv/bin/python -m ruff format --check app tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m pytest -q
# 147 passed (+8)

cd frontend
pnpm test       # 87 passed (+6)
pnpm typecheck  # silent OK
pnpm build      # 8 routes prerender，含新增的 /network
```

**人工 smoke 路径**：

1. `fastapi dev` + `pnpm dev` 同启 → 访问 `http://localhost:3000/network`。
2. 看到 nav 中 `/network` 高亮，标题 `网络药理学（mock）`。
3. 输入 `消风散`、选「复方」→ 提交 → 按钮文案 `提交中...` → `运行中... 60%` → 约 800ms 后切到 chain table（3 行 mock 链 + disclaimer）。
4. 打开 `backend/data/runtime/network_tasks_state.json`，看到 1 条 record，`status=completed`、`poll_count>=2`。
5. 用 curl 复用 task_id：`curl -sS http://127.0.0.1:8000/api/network/result/<task_id> | jq .status` 应一直返回 `completed`。

## 下一颗候选

- **B4**：herb / compound / target / pathway sample 数据集（roadmap 估 2d）—— 把 mock chain 换成 seed 数据查询。
- **B5**：RAG citation ↔ network entity 双向跳转（roadmap 估 1.5d，依赖 B4 数据集）。
- **B6**：数据来源切换面板（roadmap 估 0.5d，独立小活）。

按 roadmap §3.2 顺序，下一颗推荐 **B4**。
