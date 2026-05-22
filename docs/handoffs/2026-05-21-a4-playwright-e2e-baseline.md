# A4 Playwright E2E baseline

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A4
分支：`feat/rag-citation-pdf-provenance-batch`

## Goal

按路线图阶段 A 第四颗 slice，引入 Playwright E2E baseline：装 `@playwright/test`、写一条 `/literature → 详情 → /rag → 问答 → citation` 串联主路径、提供 `pnpm e2e` 命令。这是封闭走查前的必要回归网。

不在范围：覆盖 PDF 上传 / PubMed sync UI / evals 页面（留给后续 slice 增量加 spec）。

## Completed

### Frontend：依赖

- `frontend/package.json` `devDependencies` 加 `@playwright/test ^1.60.0`（pnpm 解析的实际版本）。
- `frontend/pnpm-lock.yaml` 同步。
- `package.json` `scripts` 加：
  - `"e2e": "playwright test"`
  - `"e2e:install": "playwright install chromium"` — 给 CI / 新机器一行命令拉浏览器
- 通过 `pnpm exec playwright install chromium` 装好 Chrome Headless Shell v1223 到 `~/.cache/ms-playwright/`。

### Frontend：配置

- `frontend/playwright.config.ts`（新增）：
  - `testDir: "./e2e"`，60s timeout，10s expect timeout
  - `fullyParallel: false`，`workers: 1` —— 当前只有一条 spec，且共享一份后端 runtime，串行更稳
  - `baseURL: "http://127.0.0.1:3000"`
  - `trace: "retain-on-failure"`、`screenshot: "only-on-failure"`、`video: "off"`
  - `webServer` 数组（playwright 1.13+）：
    - backend：`cd ../backend && QIYAN_ACCESS_TOKENS='' LITERATURE_RUNTIME_STATE_PATH=/tmp/qiyan-e2e-runtime.json UPLOAD_STORAGE_DIR=/tmp/qiyan-e2e-uploads .venv/bin/fastapi dev app/main.py --port 8000`，URL `http://127.0.0.1:8000/health`
    - frontend：`pnpm dev`，URL `http://127.0.0.1:3000`
    - 两侧 `reuseExistingServer: !process.env.CI` —— 本地已有 dev server 时直接复用、CI 永远重新拉

### Frontend：spec

`frontend/e2e/main-path.spec.ts`（新增）—— 单条测试覆盖 6 步：
1. `goto /literature` → 工作台导航 + 检索关键词输入框默认值 `"特应性皮炎"`。
2. 点 `开始检索|检索中` submit 按钮 → 等 `查看详情 →` 链接出现。
3. 点击第一个详情链接 → URL `/literature/<id>` + 工作台导航仍渲染。
4. `goto /rag` → `RAG 问题` textbox 可见 → 填 `"特应性皮炎 肠皮轴"` → 点 `生成回答|生成中`。
5. 等 `回答结果` heading → 断言 disclaimer 文案 `非诊断结论、需结合临床。` byte-identical 可见 → `引用卡片` heading + 至少一条 `查看文献详情` 链接可见。
6. A3 落地的 `导出答案为 Markdown` 按钮仍存在 —— 把 A3 的成果一并锁住。

selector 用 `getByRole` + regex 命名（`/查看详情/`、`/生成回答|生成中/`），抗文案微调。

### Frontend：辅助

- `frontend/e2e/README.md`（新增）：first-time 安装步骤、`sudo apt-get install libnspr4 libnss3 libxss1 libasound2 libxshmfence1 libgbm1` 系统依赖、本地 vs CI 跑法、写新 spec 的 selector / runtime state 约定。
- 根 `.gitignore` 加 4 行：`frontend/test-results/`、`frontend/playwright-report/`、`frontend/blob-report/`、`frontend/playwright/.cache/`。
- `CLAUDE.md`：
  - 在 Frontend 命令段补 `pnpm e2e` 与"see frontend/e2e/README.md"提示。
  - Conventions 段加 **E2E gate (A4)** 条目：明确 e2e **不是** per-commit gauntlet，是 branch / pre-walkthrough gate；失败按 branch-level blocker 对待。

## Verification

Frontend gauntlet（per-commit）全绿：
- `pnpm test` → 81 passed（无变更）
- `pnpm typecheck` → pass（`e2e/*.ts` 也走 tsc，无类型错）
- `pnpm build` → 7 routes，build OK

Backend gauntlet（未触碰）：
- 上一颗 slice 已留 121 passed / ruff / mypy strict 全绿，本 slice 不动 `backend/`，未重跑。

E2E baseline（**本机无法验证**）：
- `pnpm e2e` 本机跑到 chromium 启动阶段，因 WSL 环境缺 `libnspr4.so` 等系统库且当前 shell 无 sudo 权限，浏览器进程退出码 127 → spec 1 failed。
- spec 代码与 config 已就位；首次跑通需要在能 sudo 的环境跑 `pnpm exec playwright install --with-deps chromium`（或手装 `libnspr4 libnss3 libxss1 libasound2 libxshmfence1 libgbm1`）。
- 这不是 spec 本身的 bug，是 host 系统依赖缺失。`frontend/e2e/README.md` 第一节就是为此写的。

一行命令（不含 e2e）：
```bash
cd frontend && pnpm test && pnpm typecheck && pnpm build && echo "FRONTEND GAUNTLET GREEN"
```

## Changed files

- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `frontend/playwright.config.ts`（新增）
- `frontend/e2e/main-path.spec.ts`（新增）
- `frontend/e2e/README.md`（新增）
- `.gitignore`
- `CLAUDE.md`
- `docs/handoffs/2026-05-21-a4-playwright-e2e-baseline.md`（本文档）

## Current caveats

- **首次跑必须先装系统依赖**。Playwright 1.60 在 WSL/Linux 默认下载的 chromium-headless-shell 链接 `libnspr4`、`libnss3`、`libxss1`、`libasound2` 等共享库；apt 安装一定要 sudo。`pnpm exec playwright install --with-deps chromium` 是官方推荐做法。
- **测试只有 1 条**。覆盖主路径但不覆盖 PDF 上传 / PubMed sync / evals 页面。新增 spec 时遵循 `e2e/README.md` 末段约定（`getByRole` + regex name + 隔离 runtime state）。
- **runtime state 落 /tmp**。本机长跑下来 `/tmp/qiyan-e2e-runtime.json` 与 `/tmp/qiyan-e2e-uploads` 会越积越多，需要手动清理。如果有人重启 WSL 这两个文件会自动消失（/tmp 是 tmpfs）。
- **`reuseExistingServer` 在 CI 必须 false**。配置里用 `!process.env.CI` 守住，CI 跑前要确保 `CI=1` 环境变量存在（Github Actions 默认存在）。
- **未跑 `playwright install --with-deps` 的环境**调试方法：
  - 看 `frontend/test-results/<test-name>/error-context.md`
  - 看 `trace.zip`（用 `pnpm exec playwright show-trace`）
  - 这两个文件 .gitignore 已忽略，不入仓
- **没有 video 录制**。`video: "off"`，只在失败时 trace + screenshot。如果排查需要可以临时切到 `video: "retain-on-failure"`。
- **没装 firefox/webkit**。`projects` 只配了 chromium；如果以后需要 cross-browser，加 `pnpm exec playwright install firefox webkit` 与 projects 数组项。

## Recommended next step

阶段 A 剩：
- **A5 真实中文 PDF 人工验收**（0.5d）：依赖你上传 2-3 个真实 PDF，本机无法独立推进。
- **A2.2 前端 token 适配**（可选 0.5h）：fetch wrapper 里塞 `NEXT_PUBLIC_ACCESS_TOKEN`。
- **CI workflow**（未排号）：把 `pnpm e2e` 接入 Github Actions，先在 ubuntu-latest 上加 `playwright install --with-deps chromium` 步骤；保证封闭走查前可信。

下一颗推荐先 **push 上 origin**（已超 4 commits，外加本 slice 即 5 commits，越积越多 review 起来越累），等 Windows 代理恢复后立刻推。如果用户先要看 A5 / CI，可以并行推进。
