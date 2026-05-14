# Qiyan Nexus frontend workbench polish handoff

## Goal
为 Qiyan Nexus 当前前端 workbench 做一轮最小可提交的体验统一收口，聚焦 `/literature`、`/rag`、`/literature/[id]` 与 PDF upload / citation metadata copy，一并整理出方便从电脑端继续接手的交接入口。

## Current state
- 当前主工作副本仍是 WSL：`/home/dyh2026/Projects/Tcm_tech`
- Windows 副本仍在：`/mnt/d/开发/TCM_tech`
- 当前分支：`main`
- 本轮未扩到新功能，仅做现有 workbench 页面的一致性 polish
- 工作树在本 handoff 落地前处于未提交状态；完成本文件后将一并 commit

## Completed in this session
- `/literature/[id]` 顶部切到与 workbench 一致的导航壳，使用 `getComplianceNavigationLinks()` 与 `clamp(20px, 4vw, 48px)` 页面 padding
- `/literature/[id]` intro 补上 `Evidence workbench` 与 review-first supporting copy
- 文献详情、文献检索结果卡、PDF 上传状态行、RAG citation card 的 metadata 统一改为显式标签化文案
- 新增/更新 source-level tests，锁定壳层一致性与 metadata 文案契约
- 人工巡检确认本轮改动是单一主题的最小 polish slice，没有扩到逻辑层重构

## Still open / intentionally deferred
- 本轮尚未重新跑 `pnpm test && pnpm typecheck && pnpm build`
- 尚未做浏览器级人工视觉验收
- 尚未进入更大范围的 `/compliance`、首页或新功能扩展
- 尚未推进真实 PDF 解析、异步任务、真实检索/RAG

## Key files and artifacts
- `frontend/app/literature/[id]/page.tsx`
- `frontend/components/LiteratureSearchClient.tsx`
- `frontend/components/LiteraturePdfUploadClient.tsx`
- `frontend/components/RagAnswerClient.tsx`
- `frontend/tests/client-section-consistency.test.mjs`
- `frontend/tests/literature-detail-meta.test.mjs`
- `frontend/tests/page-shell-consistency.test.mjs`
- `frontend/tests/pdf-upload-status.test.mjs`
- `~/.hermes/wiki/notes/2026-05-14-Qiyan Nexus-frontend-workbench-polish-computer-handoff.md`

## Verification
- `git diff` / targeted source review — completed
- 提交前人工边界审查 — completed
- `pnpm test` — not yet run in this handoff round
- `pnpm typecheck` — not yet run in this handoff round
- `pnpm build` — not yet run in this handoff round

## Recommended next step
从电脑端接手时，先以这次 commit 为基线，在 WSL 主副本中跑 `cd frontend && pnpm test && pnpm typecheck && pnpm build`；若全绿，再决定是否继续做下一颗最小 UI polish slice。

## Recommended reading order
1. `AGENTS.md`
2. `docs/handoffs/2026-05-14-frontend-workbench-polish.md`
3. `~/.hermes/wiki/projects/Qiyan Nexus.md`
4. `~/.hermes/wiki/notes/2026-05-14-Qiyan Nexus-frontend-workbench-polish-computer-handoff.md`
5. 上述 4 个 frontend 代码文件与 4 个测试文件

## Recommended skill / toolset
- `qiyan-ui-defaults`
- `codex`
- `terminal`, `file`

## Source of truth
后续继续开发时，仍以 WSL 主工作副本 `/home/dyh2026/Projects/Tcm_tech` 为唯一主事实源，Windows 副本仅在明确同步时再更新。
