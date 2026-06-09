# GitHub Actions CI/CD

本目录包含 Qiyan Nexus 的持续集成配置。

## Workflows

### `ci.yml` - 持续集成

**触发条件**：
- Push 到 `main`、`feat/**`、`fix/**` 分支
- 针对 `main` 分支的 Pull Request

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
   - Playwright + Chromium
   - 启动后端 + 前端 webServer
   - 运行 4 个 E2E spec

**缓存策略**：
- Python pip 缓存：基于 `setup-python` 内置
- pnpm store 缓存：基于 `pnpm-lock.yaml` hash
- Playwright 浏览器缓存：包含在 `--with-deps` 安装中

**失败处理**：
- E2E 失败时自动上传 Playwright 报告（保留 7 天）
- 可在 Actions 页面 Artifacts 区下载

## 本地验证 vs. CI

| 步骤 | 本地命令 | CI Job |
|------|---------|--------|
| 后端格式检查 | `ruff format --check` | backend |
| 后端 lint | `ruff check` | backend |
| 后端类型检查 | `mypy app` | backend |
| 后端测试 | `pytest -q` | backend |
| 前端测试 | `pnpm test` | frontend |
| 前端类型检查 | `pnpm typecheck` | frontend |
| 前端构建 | `pnpm build` | frontend |
| E2E 测试 | `pnpm e2e` | e2e |

本地门禁脚本：`scripts/verify-local.ps1`

## 注意事项

1. **E2E runtime 隔离**：CI 使用临时 runtime 目录，不会污染 seed data
2. **Playwright 首次运行**：安装浏览器 + 系统依赖可能需要 2-3 分钟
3. **并行执行**：3 个 jobs 并行运行，总耗时约等于最慢的 job（通常是 E2E）
4. **Windows vs. Linux**：本地是 Windows + PowerShell，CI 是 Ubuntu + Bash；已验证跨平台兼容性

## 未来增强方向

- [ ] 添加代码覆盖率报告（pytest-cov）
- [ ] 添加 PR 的覆盖率变化评论
- [ ] 添加 shared-token profile 的 E2E 测试
- [ ] 添加性能回归检测（API latency baseline）
- [ ] 添加 dependabot 自动依赖更新
