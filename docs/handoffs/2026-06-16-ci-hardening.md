# 2026-06-16 CI hardening handoff

## Scope

本次只加固并对齐 GitHub Actions CI 配置与文档：

- 修改 `.github/workflows/ci.yml`
- 更新 `.github/workflows/README.md`
- 新增本 handoff

未触碰 `backend/app`、`backend/tests`、`frontend/app`、`frontend/components`、`frontend/lib`，也未修改 `scripts/verify-local.ps1` 行为。

## 审计发现

### HIGH

- `push.branches` 只覆盖 `main`、`feat/**`、`fix/**`，漏掉 `chore/**`、`docs/**`、`refactor/**`、`test/**`、`perf/**`、`ci/**`。结果是当前 `chore/preview-trial-readiness` 这类 conventional 分支 push 不触发 CI，仅 PR 到 `main` 时触发。

### MED

- workflow 缺少 `concurrency`，同一分支连续 push 会堆叠 run。
- workflow 缺少显式 `permissions`，未收敛到最小仓库读取权限。
- 三个 job 均缺少 `timeout-minutes`，卡死时可能跑满额度。
- `frontend` job 有 pnpm store cache，`e2e` job 没有，导致 E2E 重复下载前端依赖。

### LOW

- `actions/setup-python` 的 pip cache 未设置 `cache-dependency-path`，缓存 key 未显式绑定 `backend/pyproject.toml`。
- 后端依赖没有 lock 文件，`pip install -e ".[dev]"` 会解析 `backend/pyproject.toml` 里的 `>=` 约束，可能出现上游工具版本漂移导致的“CI 红、本地绿”。本次不引入 lock 迁移。

## 已修复

- 扩展 `on.push.branches` 到 `main`、`feat/**`、`fix/**`、`chore/**`、`docs/**`、`refactor/**`、`test/**`、`perf/**`、`ci/**`。
- 添加顶层最小权限：
  - `permissions.contents: read`
- 添加顶层并发取消：
  - `concurrency.group: ${{ github.workflow }}-${{ github.ref }}`
  - `cancel-in-progress: true`
- 添加 job 超时：
  - `backend`: 15 分钟
  - `frontend`: 15 分钟
  - `e2e`: 25 分钟
- 给 backend/e2e 的 `actions/setup-python` 添加：
  - `cache-dependency-path: backend/pyproject.toml`
- 给 `e2e` job 补上与 `frontend` job 一致的 pnpm store cache：
  - `pnpm store path`
  - `actions/cache@v4`
  - key: `${{ runner.os }}-pnpm-store-${{ hashFiles('**/pnpm-lock.yaml') }}`

## Parity 对账

CI 的门禁命令保持与 `scripts/verify-local.ps1` / `frontend/package.json` / `backend/pyproject.toml` 对齐；安装步骤属于 CI runner bootstrap，不改变默认业务运行路径。

| CI job | CI run step | CI 命令 | 本地/依赖事实源 | 对账结论 |
|--------|-------------|---------|-----------------|----------|
| backend | Install backend dependencies | `python -m pip install --upgrade pip` | CI bootstrap；本地脚本假定 `backend/.uv-test-venv` 已存在 | CI 专属安装步骤 |
| backend | Install backend dependencies | `python -m pip install -e ".[dev]"` | `backend/pyproject.toml` 的 project + `dev` extras | 与后端依赖声明一致 |
| backend | Ruff format check | `python -m ruff format --check app tests` | `& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests` | 除解释器路径外，module/参数逐字一致 |
| backend | Ruff lint | `python -m ruff check app tests` | `& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests` | 除解释器路径外，module/参数逐字一致 |
| backend | Mypy type check | `python -m mypy app` | `& .\.uv-test-venv\Scripts\python.exe -m mypy app` | 除解释器路径外，module/参数逐字一致 |
| backend | Pytest | `python -m pytest -q` | `& .\.uv-test-venv\Scripts\python.exe -m pytest -q` | 除解释器路径外，module/参数逐字一致 |
| frontend | Install dependencies | `pnpm install --frozen-lockfile` | `frontend/pnpm-lock.yaml` | CI 专属安装步骤，锁文件约束依赖 |
| frontend | Run tests | `pnpm test` | `verify-local.ps1` 调用 `pnpm test`; package script: `node --import tsx --test tests/*.test.ts` | pnpm 子命令逐字一致 |
| frontend | Type check | `pnpm typecheck` | `verify-local.ps1` 调用 `pnpm typecheck`; package script: `next typegen && tsc --noEmit` | pnpm 子命令逐字一致 |
| frontend | Build | `pnpm build` | `verify-local.ps1` 调用 `pnpm build`; package script: `next build --webpack` | pnpm 子命令逐字一致 |
| e2e | Install backend dependencies | `python -m pip install --upgrade pip` | CI bootstrap；本地脚本假定 `backend/.uv-test-venv` 已存在 | CI 专属安装步骤 |
| e2e | Install backend dependencies | `python -m pip install -e ".[dev]"` | `backend/pyproject.toml` 的 project + `dev` extras | 与后端依赖声明一致 |
| e2e | Install frontend dependencies | `pnpm install --frozen-lockfile` | `frontend/pnpm-lock.yaml` | CI 专属安装步骤，锁文件约束依赖 |
| e2e | Install Playwright browsers | `pnpm exec playwright install chromium --with-deps` | 本地 E2E 前置安装说明；Ubuntu runner 需要 `--with-deps` 安装系统依赖 | CI 专属环境准备 |
| e2e | Run E2E tests | `pnpm e2e` | `verify-local.ps1 -IncludeE2E` 调用 `pnpm e2e`; package script: `playwright test` | pnpm 子命令逐字一致 |

## 验证证据

- YAML 解析通过：
  - `& .\backend\.uv-test-venv\Scripts\python.exe -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"`
  - 输出：`yaml ok`
- actionlint 通过：
  - 安装：`go install github.com/rhysd/actionlint/cmd/actionlint@latest`
  - 检查：`& "$env:USERPROFILE\go\bin\actionlint.exe" .github\workflows\ci.yml`
  - 输出为空，退出码 0
- package script 拼写已核对：
  - `test`: `node --import tsx --test tests/*.test.ts`
  - `typecheck`: `next typegen && tsc --noEmit`
  - `build`: `next build --webpack`
  - `e2e`: `playwright test`

## 未做项与理由

- 未添加覆盖率报告：`pytest-cov>=5.0.0` 已在 dev 依赖中，但本地权威门禁不跑 coverage；本次目标是 CI 与本地门禁字面对齐，不新增默认质量阈值或额外报告。
- 未添加 actionlint 自校验 job：会改变现有 3-job 结构；本次仅做外科式加固，并在本地手动跑 actionlint 验证。
- 未新增 Dependabot、release/deploy/publish workflow、PR 评论机器人、Windows runner：均为范围外。
- 未引入真实 LLM key、pgvector、Neo4j、Celery、Redis、MinIO 或会改变默认路径的环境变量：保持默认 deterministic provider + keyword retrieval 边界。

## 后续决策选项

后端依赖未锁版本仍是残余风险，建议后续单独决策：

- 选项 A：新增 `constraints.txt`，只 pin `ruff`、`mypy`、`pytest`、`fastapi[standard]` 等门禁敏感工具。
- 选项 B：在 `backend/pyproject.toml` 中 pin 关键 dev 工具版本，保持业务依赖继续用范围约束。
- 选项 C：引入正式 lock 流程，例如 `uv.lock` 或生成型 requirements lock；这是更大依赖管理迁移，不应混入本次 CI 加固。
