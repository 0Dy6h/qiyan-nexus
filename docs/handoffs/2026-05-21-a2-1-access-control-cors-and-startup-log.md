# A2.1 修 W1 (CORS on 401) + W2 (startup log)

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A2 收尾
分支：`feat/rag-citation-pdf-provenance-batch`

## Goal

A2 落地后跑了 `security-review` skill，结论是没有 BLOCKER，但有两条 WARNING 值得在同一阶段闭环：

- **W1**：原 main.py 把 `add_middleware(CORS)` 写在 `install_access_token_middleware` 之前。Starlette `add_middleware` 走 `user_middleware.insert(0, ...)`，再 `reversed` 构建栈 → **后加的成最外层**。结果 AccessToken 是最外层，CORS 在它内层。401 短路返回时 CORS 根本不会被执行，前端拿到的是 opaque CORS error 而不是可读的 401。
- **W2**：env 没设时不打日志，部署忘配 `QIYAN_ACCESS_TOKENS` 等于完全开放且无 trace 痕迹。

W3（timing-safe compare）按路线图 handoff 显式标注为"非 real auth"，本 slice 不处理。

## Completed

### Backend：交换 middleware 安装顺序

`app/main.py`：
- 先 `install_access_token_middleware(app)`，再 `add_middleware(CORSMiddleware, ...)`。
- 加注释说明 Starlette `insert(0, ...) + reversed` 的语义，避免下次有人想"按视觉顺序排"再改回来。

效果：CORS 成最外层，AccessToken 401 响应在出栈时被 CORS 包一层 `Access-Control-Allow-Origin` 头，浏览器能看到真正的 401。

中间件代码里 `if request.method == "OPTIONS"` 分支保留，作为 CORSMiddleware 不接管（例如缺 Origin 头的 OPTIONS）时的防御兜底。dispatch 注释里写了这层意图。

### Backend：startup 日志

`app/core/access_control.py`：
- 模块级 `logger = logging.getLogger(__name__)`。
- `install_access_token_middleware` 在 `add_middleware` 之前根据 allowed 集合大小打 INFO：
  - 空：`"access control disabled: QIYAN_ACCESS_TOKENS unset or empty (open mode)"`
  - 非空：`"access control enabled with N token(s) via QIYAN_ACCESS_TOKENS"`
- token 值永远不出现在日志里，只 log 数量。

### Backend：测试

`tests/test_access_control.py` 加 3 条（总 10 条）：
- `401_response_carries_cors_headers_for_browser_origin`：env 设了、带 Origin 头、不带 X-Access-Token → 401 且响应头有 `access-control-allow-origin: http://localhost:3000`。锁住 W1 修复。
- `install_access_token_middleware_logs_open_mode_when_env_unset`：reload `app.main`，断言 caplog 包含 `disabled` + `open`。锁住 W2 上半。
- `install_access_token_middleware_logs_token_count_when_env_set`：reload `app.main`，断言 log 含 `3` + `enabled`，且不含 `alpha` / `beta` / `gamma`（不泄露 token 值）。锁住 W2 下半 + 防泄露不变量。

`reload_app` fixture 已经在 A2 加了 teardown 时 `monkeypatch.delenv` 的逻辑，本 slice 沿用。

## Verification

Backend gauntlet 全绿：
- `ruff format --check app tests` → 52 files already formatted
- `ruff check app tests` → All checks passed!
- `mypy app` → no issues in 31 source files
- `pytest -q` → **121 passed**（118 + 3 新）

ruff 跑了一次 reformat（test 文件原来手写时分行有点窄），格式化后差异只是函数签名换行。

Frontend：未触碰，不再跑。

完整一行：
```bash
cd backend && .venv/bin/python -m ruff format --check app tests && .venv/bin/python -m ruff check app tests && .venv/bin/python -m mypy app && .venv/bin/python -m pytest -q && echo "BACKEND GAUNTLET GREEN"
```

## Changed files

- `backend/app/main.py`
- `backend/app/core/access_control.py`
- `backend/tests/test_access_control.py`
- `docs/handoffs/2026-05-21-a2-1-access-control-cors-and-startup-log.md`（本文档）

## Current caveats

- middleware 顺序现在依赖 Starlette 内部 `insert(0, ...) + reversed` 语义。如果 Starlette / FastAPI 未来改 API（例如 `add_middleware` 改成 `append`），需要回来重排顺序。`app/main.py` 注释已记录这点。
- 日志是 module logger，没改 uvicorn 全局 log 配置，默认 dev 模式输出到 stderr。生产部署如果禁用了 stderr 或把 logging level 调到 WARNING 以上，这条 INFO 会丢；建议运维侧把 `app.core.access_control` 至少保留在 INFO。
- 仍然没有 `constant-time` 比较；按 review NOTES 与原 handoff 一致——这是"防偶然访问"工具，不是密码学认证。

## Recommended next step

阶段 A 还剩：
- **A4 Playwright E2E**（1d）：装 Playwright 写 `/literature → 详情 → /rag → 问答 → citation` 串联；需先 `update-config` 加 `pnpm e2e` allowlist。
- **A5 真实中文 PDF 人工验收**（0.5d）：依赖用户上传 2-3 个真实 PDF。
- **A2.2 前端 token 适配**（可选 0.5h）：在 `lib/api/*.ts` fetch wrapper 里塞 `X-Access-Token: process.env.NEXT_PUBLIC_ACCESS_TOKEN`。配套 `.env.local` 与 `.env.example`。

下一颗推荐 **A4**（启动 E2E baseline，封闭走查必备），或者把当前分支 push 上 origin（已超 origin 3 个 commit）。
