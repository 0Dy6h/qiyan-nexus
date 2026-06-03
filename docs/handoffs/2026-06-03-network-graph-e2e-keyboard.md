# Session Handoff — 2026-06-03（NetworkGraph e2e 键盘交互回归，Slice 12）

branch: `feat/network-graph-e2e-keyboard`（从 main `5556df0` 切，2 个 commit）
default RAG path: offline `deterministic`，未变
stopped at: `pnpm e2e` 3 spec 全绿；PR 待开

## Goal

闭合 Slice 11 handoff 留下的唯一 TODO —— "e2e 键盘交互测仍未加（独立 gate）"。Slice 10/11 通过 `tests/network-graph-ui.test.ts` 的 regex 源码断言确认了 API 表面（tabIndex / role / aria-pressed / onKeyDown 各分支存在），但**真浏览器里 Tab 是否真的落焦、Arrow 是否真的搬运 focus、Enter 是否真触发 toggle**，源码断言看不到。本 slice 用 Playwright 真 chromium 驱动键盘事件去验。

## Current state

- `frontend/e2e/network-graph-keyboard.spec.ts`：单 spec 单测，跑 `/network` 默认 mock 分析（消风散 formula → 6 条 chain，多 compound / target 节点，保证 ArrowDown 同层有下一节点），然后驱动：
  1. herb 层节点 `focus()` → `aria-pressed="false"`
  2. Enter → `aria-pressed="true"` + 「聚焦：中药/复方:」提示文本可见
  3. Enter 再按 → toggle 回 false，提示文本消失
  4. Space → 同样 toggle on（验证 Slice 10 的 Space 等价分支）
  5. Escape → toggle off + 提示清
  6. ArrowRight → focus 落到 compound 层（`:focus` 的 aria-label 前缀切到「化合物:」）
  7. ArrowDown → 仍在 compound 层但 aria-label 切换（验证 Slice 11 的同层 Y 排序）
  8. ArrowLeft → 反向跨层回到 herb 层
- `frontend/e2e/start-frontend.mjs`：兜底 `pnpm.cmd` 分支补 `shell: needsShell`（仅 Windows + 没拿到 `npm_execpath` 时为 true）。Node ≥20 因 CVE-2024-27980 拒绝 shell:false spawn `.cmd` / `.bat`，playwright webServer 直 `node start-frontend.mjs` 时 `npm_execpath` 未传 → 触发兜底 → EINVAL。Linux / 走 pnpm wrapper 路径不受影响（shell:false 保留）。

## Completed in this session

- 合到 main 后 cleanup（main → `5556df0`，本地/远端 `feat/cross-lingual-term-bridge` 已清）。
- Slice 12 新分支 `feat/network-graph-e2e-keyboard`。
- commit 1 `fix(e2e): allow Windows pnpm.cmd spawn under Node 20+`
- commit 2 `test(e2e): NetworkGraph keyboard regression — close Slice 11 tail`
- 全 e2e 套件本机绿（`pnpm e2e` 3 passed in 12.9s：main-path、internal-preview、network-graph-keyboard）。
- per-commit gauntlet：`pnpm test` 162 passed / `pnpm typecheck` clean / `pnpm build` clean。后端未触碰。

## Still open / blocked

- `node:internal/.../spawn` 的 `DEP0190` 警告：`shell:true` + args 数组在 Node 22+ 已 deprecated（拼字符串无转义安全风险）。本 case 的 args 全是硬编码常量 + `port` 数字字符串，无注入面，警告仅信息性。要彻底消可改成单字符串 + 自己拼引号，但 Windows 路径含中文（实测 `D:\辅助应用\node.js\node.exe`）拼字符串风险更大。**留 as-is**。
- e2e 仍非 per-commit gauntlet（CLAUDE.md / e2e/README.md 明文），本 slice 不动这条边界。CI 接入仍是后续工作。
- 其它 5 个 page route（`/`、`/literature`、`/literature/[id]`、`/compliance`、`/evals/rag-ad`）的 a11y 键盘交互暂未补 e2e；当前只有 main-path 走 happy path。

## Key files and artifacts

- `frontend/e2e/network-graph-keyboard.spec.ts`（新）
- `frontend/e2e/start-frontend.mjs`（+3 行注释 + 1 行 needsShell + 替 `shell:false` 为 `shell: needsShell`）
- `docs/current-state.md`（Slice 11 entry 后续加 Slice 12 一句）
- 本 handoff

## Verification

- `cd frontend && pnpm exec playwright test e2e/network-graph-keyboard.spec.ts` — 1 passed (2.5s spec / 26s 含 webServer 启动)
- `cd frontend && pnpm exec playwright test` — **3 passed (12.9s)**
- `cd frontend && pnpm test` — **162 passed**
- `cd frontend && pnpm typecheck` — clean
- `cd frontend && pnpm build` — clean

## Recommended next step

- 推 PR 走查（单 commit 体量小，scope 干净：1 e2e 测 + 1 infra 修）。
- 候选下一切片不变：多语 embedding、PDF OCR spike、PostgreSQL spike、L2 governance。

## Recommended reading order

1. `docs/current-state.md`（Slice 12 entry）
2. 本 handoff
3. `frontend/e2e/network-graph-keyboard.spec.ts`（验的行为对照表）
4. `docs/handoffs/2026-06-02-network-graph-arrow-key-nav.md`（Slice 11 上下文）
5. `frontend/e2e/start-frontend.mjs`（spawn 兜底）
