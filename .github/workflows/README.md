# GitHub Actions CI/CD

本目录包含 Qiyan Nexus 的持续集成配置。CI 的定位是把本地权威门禁
`scripts/verify-local.ps1` 复刻到 Ubuntu runner；默认运行边界保持 deterministic
provider + keyword retrieval，不在 CI 注入真实 LLM key、pgvector、Neo4j、Celery 等重依赖。

## Workflows

### `ci.yml` - 持续集成

**触发条件**：
- Push 到 `main`、`feat/**`、`fix/**`、`chore/**`、`docs/**`、`refactor/**`、`test/**`、`perf/**`、`ci/**` 分支
- 针对 `main` 分支的 Pull Request

**运行治理**：
- `permissions: contents: read`：workflow 只需要读取仓库内容；E2E 失败上传 artifact 不需要额外写权限
- `concurrency.group: ${{ github.workflow }}-${{ github.ref }}`：同一分支连续 push 时取消旧 run
- `timeout-minutes`：backend 15 分钟，frontend 15 分钟，e2e 25 分钟

**Jobs**：

1. **backend** - 后端门禁
   - Python 3.11
   - Ruff format check
   - Ruff lint
   - Mypy type check
   - Pytest（所有测试）

2. **frontend** - 前端门禁
   - Node.js 20 + pnpm 10
   - 单元测试（node:test）
   - TypeScript type check
   - Next.js build

3. **e2e** - 端到端测试
   - Python 3.11 + Node.js 20 + pnpm 10
   - Playwright + Chromium
   - 启动后端 + 前端 webServer
   - 运行 E2E specs

**缓存策略**：
- Python pip 缓存：`actions/setup-python` 内置缓存，依赖 key 显式绑定 `backend/pyproject.toml`
- pnpm store 缓存：frontend 与 e2e 均基于 `pnpm-lock.yaml` hash
- Playwright 浏览器缓存：通过 `pnpm exec playwright install chromium --with-deps` 安装

**失败处理**：
- E2E 失败时自动上传 Playwright 报告（保留 7 天）
- 可在 Actions 页面 Artifacts 区下载

## 本地验证 vs. CI

本地门禁脚本：`scripts/verify-local.ps1`

| CI job | CI run step | CI 命令 | 本地/依赖事实源 | 对账结论 |
|--------|-------------|---------|-----------------|----------|
| backend | Install backend dependencies | `python -m pip install --upgrade pip` | CI bootstrap；本地脚本假定 `backend/.uv-test-venv` 已存在 | CI 专属安装步骤 |
| backend | Install backend dependencies | `python -m pip install -e ".[dev]"` | `backend/pyproject.toml` 的 project + `dev` extras | 与后端依赖声明一致 |
| backend | Ruff format check | `python -m ruff format --check app tests` | `& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` | 除解释器路径外，module/参数逐字一致 |
| backend | Ruff lint | `python -m ruff check app tests` | `& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` | 除解释器路径外，module/参数逐字一致 |
| backend | Mypy type check | `python -m mypy app` | `& .\.uv-test-venv\Scripts\python.exe -m mypy app` | 除解释器路径外，module/参数逐字一致 |
| backend | Pytest | `python -m pytest -q` | `& .\.uv-test-venv\Scripts\python.exe -m pytest -q` | 除解释器路径外，module/参数逐字一致 |
| frontend | Install dependencies | `pnpm install --frozen-lockfile` | `frontend/pnpm-lock.yaml` | CI 专属安装步骤，锁文件约束依赖 |
| frontend | Run tests | `pnpm test` | `Invoke-NativeStep ... -Arguments @("test")`; package script: `node --import tsx --test tests/*.test.ts` | pnpm 子命令逐字一致 |
| frontend | Type check | `pnpm typecheck` | `Invoke-NativeStep ... -Arguments @("typecheck")`; package script: `next typegen && tsc --noEmit` | pnpm 子命令逐字一致 |
| frontend | Build | `pnpm build` | `Invoke-NativeStep ... -Arguments @("build")`; package script: `next build --webpack` | pnpm 子命令逐字一致 |
| e2e | Install backend dependencies | `python -m pip install --upgrade pip` | CI bootstrap；本地脚本假定 `backend/.uv-test-venv` 已存在 | CI 专属安装步骤 |
| e2e | Install backend dependencies | `python -m pip install -e ".[dev]"` | `backend/pyproject.toml` 的 project + `dev` extras | 与后端依赖声明一致 |
| e2e | Install frontend dependencies | `pnpm install --frozen-lockfile` | `frontend/pnpm-lock.yaml` | CI 专属安装步骤，锁文件约束依赖 |
| e2e | Install Playwright browsers | `pnpm exec playwright install chromium --with-deps` | 本地 E2E 前置安装说明；Ubuntu runner 需要 `--with-deps` 安装系统依赖 | CI 专属环境准备 |
| e2e | Run E2E tests | `pnpm e2e` | `verify-local.ps1 -IncludeE2E` 调用 `pnpm e2e`; package script: `playwright test` | pnpm 子命令逐字一致 |

## 注意事项

1. **E2E runtime 隔离**：CI 使用临时 runtime 目录，不会污染 seed data。
2. **Playwright 首次运行**：安装浏览器 + 系统依赖可能需要 2-3 分钟。
3. **并行执行**：3 个 jobs 并行运行，总耗时约等于最慢的 job（通常是 E2E）。
4. **Windows vs. Linux**：本地是 Windows + PowerShell，CI 是 Ubuntu + Bash；门禁命令的 module/参数保持一致。
5. **后端依赖未锁版本**：`backend/pyproject.toml` 使用 `>=` 约束，CI 的 `pip install -e ".[dev]"` 可能受上游工具版本漂移影响；后续可选择 constraints 文件或 pin 关键工具版本。

## 未来增强方向

- [x] 扩展 conventional 分支 push 触发覆盖
- [x] 添加 workflow concurrency、最小权限和 job timeout
- [x] 对齐 frontend/e2e 的 pnpm store 缓存，并稳定 pip cache dependency path
- [ ] 添加代码覆盖率报告（pytest-cov，不设 fail-under 时再纳入）
- [ ] 添加 workflow 自校验（actionlint job 或轻量 step）
- [ ] 添加 PR 的覆盖率变化评论
- [ ] 添加 nginx Basic Auth + server-only backend token 的部署级 smoke（浏览器 bundle 不承载 token）
- [ ] 添加性能回归检测（API latency baseline）
- [ ] 添加 dependabot 自动依赖更新
