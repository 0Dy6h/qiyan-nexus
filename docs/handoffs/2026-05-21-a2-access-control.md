# A2 最小访问控制：X-Access-Token 中间件 + env 白名单

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A2
分支：`feat/rag-citation-pdf-provenance-batch`（沿用 A 阶段批量分支）

## Goal

按路线图阶段 A 第二颗 slice，给后端加最小访问控制：
- env `QIYAN_ACCESS_TOKENS` 是逗号分隔白名单。
- 空（dev 默认）→ 全开放，行为与今天一致。
- 配置后 → 所有请求必须带 `X-Access-Token` 请求头匹配白名单，否则 401。
- `/health` 与 `OPTIONS`（CORS preflight）永不拦截。
- CORS allow_origins / allow_methods / allow_headers 保持不变。
- 前端不动（A2 不动 fetch wrapper）。

## Completed

### Backend：中间件实现

- `app/core/access_control.py`（新增）：
  - `parse_access_tokens(raw)`：把 `"alpha, beta ,"` 之类原始 env 字符串 strip + 过滤空段 → `frozenset[str]`。
  - `AccessTokenMiddleware(BaseHTTPMiddleware)`：构造时拿到 allowlist；dispatch 时
    1. 空 allowlist → 直接 `call_next`（dev open 模式）。
    2. `request.method == "OPTIONS"` → 放行（CORS preflight）。
    3. path ∈ `{"/health"}` → 放行。
    4. 取 header `X-Access-Token`，不匹配返回 `JSONResponse(401, detail="missing or invalid X-Access-Token")`。
  - `install_access_token_middleware(app)`：在 app 启动时读 env、把 middleware 装到 app。
- `app/main.py`：导入并调用 `install_access_token_middleware(app)`，紧跟在 `CORSMiddleware` 之后；router 注册顺序不变。

### Backend：测试（7 条）

`tests/test_access_control.py`：
1. `open_when_tokens_env_unset` — env 不设时全部开放，200。
2. `returns_401_when_token_missing` — env 设了、header 没带 → 401 with `detail` 标识。
3. `returns_401_when_token_invalid` — env 设了、header 带的 token 不在 allowlist → 401。
4. `returns_200_with_matching_token` — header 命中 allowlist → 200。
5. `skips_health_endpoint` — env 设了、`/health` 不带 header → 200。
6. `allows_cors_preflight_without_token` — env 设了、OPTIONS preflight → 200 且 `access-control-allow-origin` 仍然返回。
7. `strips_whitespace_in_token_list` — `" alpha , beta , "` 解析后 `alpha` 命中 200、`" alpha "`（带空格的 header）401，验证 strip 行为是 parse 端而不是 compare 端。

`reload_app` fixture 通过 `importlib.reload(app.main)` 让中间件重新读 env；teardown 时先 `monkeypatch.delenv` 再 reload，避免污染下一个测试模块（之前漏了这步会让 `test_literature_sync_api.py` 跑成 401）。

### Backend：env / 文档

- `backend/.env.example`：加 `QIYAN_ACCESS_TOKENS=""` + 注释解释含义。
- `README.md`：在「健康检查」段后加「访问控制（可选，A2）」小节，给 curl 与 `fastapi dev` 启动示例。
- `CLAUDE.md`：在 Conventions 段加 access-control 条目，指向 `app/core/access_control.py`。

## Verification

Backend gauntlet 全绿：
- `ruff format --check app tests` → 52 files already formatted
- `ruff check app tests` → All checks passed!
- `mypy app` → no issues in 31 source files（30 + access_control）
- `pytest -q` → **118 passed**（111 + 7 新）

Frontend sanity（未改动）：
- `pnpm test` → 81 passed
- typecheck / build 不再跑（无前端改动）

完整一行：
```bash
cd backend && .venv/bin/python -m ruff format --check app tests && .venv/bin/python -m ruff check app tests && .venv/bin/python -m mypy app && .venv/bin/python -m pytest -q && echo "BACKEND GAUNTLET GREEN"
```

## Real-world smoke (manual)

未在 commit 前跑真网络冒烟，但行为完全本地化：
- 不设 env 启动 `fastapi dev` → 现有 curl 调用全部正常（dev 默认开放）。
- 设 `QIYAN_ACCESS_TOKENS="dev-1"` 重启 → `curl /api/literature/search` 返 401；带 `-H "X-Access-Token: dev-1"` 返 200。

## Changed files

- `backend/app/core/access_control.py`（新增）
- `backend/app/main.py`
- `backend/tests/test_access_control.py`（新增）
- `backend/.env.example`
- `README.md`
- `CLAUDE.md`
- `docs/handoffs/2026-05-21-a2-access-control.md`（本文档）

## Current caveats

- **前端尚未带 token 调用**。如果生产环境配置了 `QIYAN_ACCESS_TOKENS`，浏览器端会全 401；当前路线图把"前端 fetch wrapper 带 token"挪到 A2.1（如有需要）或阶段 B 真实化阶段处理。封闭走查时建议同时设置 env 与 `NEXT_PUBLIC_ACCESS_TOKEN` 之类的简单方案，但不在本 slice 范围内。
- token 是明文字符串、走 HTTP header，**不是真正的 auth 层**。它的目标是阻挡偶然访问 / 内部走查白名单，不应替代 OAuth / API key 管理。
- 401 响应不带 `WWW-Authenticate` 头（不是 HTTP Basic / Bearer），是有意的；不希望浏览器弹原生登录框。
- 错误消息固定 `"missing or invalid X-Access-Token"`，不区分"未带"与"带错"，避免给攻击者额外信息。
- `parse_access_tokens` 用 `frozenset`，token 之间无优先级；如果未来要按 token 区分人/权限需要换成 dict[token, role]。
- middleware 用 `BaseHTTPMiddleware` 而非纯 ASGI middleware，方便测试但每次请求多一次包装；目前 QPS 远低于该开销有意义的阈值。
- mypy 让 `__init__(self, app: ASGIApp, ...)` 而不是 `FastAPI`，是为了通过 starlette 的 `_MiddlewareFactory` 协议——把类型放宽到 ASGIApp 即可。

## Security review

按路线图要求，本 slice 上线后需要跑 `security-review` skill 走一遍。该 skill 检查 pending changes —— 本 commit 推完后另起一颗 review 提示用户。

## Recommended next step

阶段 A 还剩：
- **A4 Playwright E2E**（1d）：装 Playwright 写一条 `/literature → 详情 → /rag → 问答 → citation` 串联；需要先 `update-config` 加 `pnpm e2e` allowlist。
- **A5 真实中文 PDF 人工验收**（0.5d）：依赖用户上传 2-3 个真实 PDF，无法独立推进。
- **A2.1 前端 token 适配**（可选 0.5d）：在 `lib/api/*` fetch wrapper 里统一塞 `X-Access-Token: process.env.NEXT_PUBLIC_ACCESS_TOKEN`；若不打算配置 env，可跳过。

下一颗推荐 **跑 `security-review`**（本 slice 引入了 auth surface，路线图明文要求）；之后再决定 A2.1 还是 A4。
