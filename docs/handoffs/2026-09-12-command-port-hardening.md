# Handoff — 命令入口硬化：tcmtech -Stop 与 8000 禁区 fail-closed（2026-09-12）

## 背景

2026-09-12 命令健康审计（当日会话）发现两个命令层陷阱，按第一性原则归因后修复：

1. **`tcmtech -Stop` 不但不停止、还会重启预览**。根因：`scripts/tcmtech.ps1` 的 `param()` 没有 `[CmdletBinding()]`，未知参数被静默吞进 `$args`，脚本照常执行启动路径。用户意图（停止）被静默反转为反面操作（重启）。
2. **禁区端口 8000 是多个命令入口的合法默认值**。本机 8000 被另一项目（python 常驻服务）占用、全程不可触碰，但裸跑 `pnpm preview`、`collect-internal-preview-evidence.ps1`、`verify-local.ps1 -IncludeE2E`、`pnpm e2e`（playwright fallback）都会试图绑定 8000；`smoke-internal-preview.ps1` 默认 URL 指向回环 8000——smoke 会写 runtime state，打到对方系统等于污染。审计期间恰逢 8000 空闲窗口，风险是真实可触发的（当日 08:22 外部 python 服务回归即冲突）。

## 修复（第一性原则：意图不得静默反转；禁区在绑定前 fail closed）

| 文件 | 改动 |
|---|---|
| `scripts/tcmtech.ps1` | 加 `[CmdletBinding()]`（未知参数显式报错）+ `[switch]$Stop` 转发 `run-internal-preview.ps1 -Stop`，停止分支在启动/浏览器之前 |
| `scripts/run-internal-preview.ps1` | 默认 `BackendPort` 8000→8010；绑定前守卫 `-eq 8000` 一律 throw（ choke point，collect/tcmtech 透传也被兜住） |
| `scripts/verify-local.ps1` | E2E 默认 `E2eBackendPort` 8000→8010（env 覆盖路径同受守卫）+ 8000 throw |
| `scripts/smoke-internal-preview.ps1` | 默认 `BackendUrl` → `http://127.0.0.1:8010`；回环 `127.0.0.1/localhost:8000` 一律 throw（任何路径，含显式传参） |
| `scripts/collect-internal-preview-evidence.ps1` | 默认 `BackendPort` "8000"→"8010"（绑定守卫由 run-internal-preview choke point 承担） |
| `frontend/playwright.config.ts` | `QIYAN_E2E_BACKEND_PORT ?? 8010` |
| `frontend/e2e/start-backend.mjs` | `?? "8010"`；注释中 `:8000` 表述改中性 |
| `frontend/e2e/README.md` | 两处端口表述同步 8010 |

测试（TDD，先红后绿）：`frontend/tests/internal-preview-command-hardening.test.ts` 新增 2 个 test 块（tcmtech -Stop/CmdletBinding 断言 + 七文件 8010 默认与守卫断言）；`internal-preview-command-hardening.test.ts` 与 `internal-preview-ops-source.test.ts` 中共 3 处钉死 8000 旧默认的断言翻转为 8010。前端测试总数 302→304。

行为实测（当日会话）：`tcmtech -Stop` 无服务时干净退出零启动；四入口显式传 8000 全部 throw；`tcmtech -Stopp` 报 `A parameter cannot be found that matches parameter name 'Stopp'`；全程无端口残留。

## 已知边界（刻意不改，留待单独切片）

- `frontend/lib/api/rag.ts` 的 `getBackendBaseUrl()` 浏览器默认仍是 `http://127.0.0.1:8000`，全仓库 36 处测试断言该字面量。改它牵动 dev 组合流语义（`pnpm dev` + `pnpm dev:backend`）与大量断言，且 sanctioned 路径（preview/tcmtech）已显式注入 `NEXT_PUBLIC_API_BASE_URL`，不属于本次命令层安全修复。它只是 HTTP 客户端目标、不绑定端口，风险等级低于绑定类入口。
- `package.json` 的 `dev:backend` 仍指向 8000：AGENTS.md 已声明 8000 被占时该命令响亮失败（bind error），8000 空闲窗口裸跑才会绑上。与前端默认 base URL 属同一 dev 组合流，需一并切片处理。
- `run-internal-preview.ps1` 的 `Assert-PortAvailable` 对 8010/3000 被占仍会响亮报错，行为未变；非 CI 下 Playwright `reuseExistingServer` 可复用 8010 上已运行的预览后端，属既有特性（e2e README 有述）。

## 验证口径

- 定向：`node --import tsx --test tests/internal-preview-command-hardening.test.ts tests/internal-preview-ops-source.test.ts` → 10/10。
- 全量：`.\scripts\verify-local.ps1`（backend 4 项 + frontend test/typecheck/build）当日全绿。
- PowerShell 语法：5 个改动脚本 Parser 零错误。

## 后续可选项

- 把前端默认 base URL + `dev:backend` 一并切到 8010（需同步 ~36 处断言与 AGENTS.md dev 段落，建议单独切片）。
