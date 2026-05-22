# A1.5 前端「同步 PubMed」入口

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A1 后续配套（前端入口）
分支：`feat/rag-citation-pdf-provenance-batch`

## Goal

A1 已经把 `POST /api/literature/sync` 后端打通；本 slice 是它的前端补全：在 `/literature` 页面顶部加一颗「同步 PubMed」面板，承接 query + max_results、显示 fetched/created/updated 计数与本次涉及到的条目，让用户不靠 curl 就能拉真实 PubMed 数据。

## Completed

### Frontend：API client

- `lib/api/literature.ts`：
  - 新增 `LiteratureSyncRequest` / `LiteratureSyncResponse` 类型，与后端 `LiteratureSyncResponse` 字段对齐。
  - 新增常量 `LITERATURE_SYNC_MAX_RESULTS_CAP = 50`（与后端硬约束一致）。
  - 新增 `buildLiteratureSyncUrl()` / `buildLiteratureSyncRequest(query, maxResults)` —— 后者负责 trim + clamp。
  - 新增 `syncLiteratureFromPubmed(query, maxResults)`，POST `application/json`，错误时抛 `Literature sync failed`。

### Frontend：同步面板组件

- `components/LiteraturePubmedSyncClient.tsx`（新增）：
  - 客户端组件，状态机：`query / maxResults / result / error / isLoading`。
  - 表单含「检索关键词」+ 「拉取数量 max_results」（受控 input，本地 clamp 到 [1, 50]）+ 「同步 PubMed」按钮，沿用现有 `#0d9488` 主色 + 44px 最小高度 + 现有 surface/section style。
  - 提交后：
    - 显示一行 `CardMetaRow`：检索关键词 / 拉取条数 / 新增 / 刷新。
    - 列出本次返回的 `items`，每条卡片显示 `PMID xxxxx`、年份、来源、标题、snippet 与「查看文献详情 →」链接（直接跳到既有的 `/literature/[id]` 路由）。
    - 空结果或网络异常时分别走 `StatusPanel`。

### Frontend：页面挂载

- `app/literature/page.tsx`：在 `<LiteratureSearchClient />` 上方插入 `<LiteraturePubmedSyncClient />`；现有 nav / DemoDataBanner / intro / 使用提醒 4 块完全不动，确保 `page-shell-consistency.test.ts` 仍通过。

### Tests

- `tests/literature-sync-api.test.ts`（新增，4 条）：
  - `buildLiteratureSyncUrl` 命中默认 base URL。
  - `buildLiteratureSyncRequest` trim + clamp 行为（0 / -3 / 999 / 7.8）。
  - `syncLiteratureFromPubmed` 用 fetch-mock 验证 POST body、headers、URL；解析返回。
  - 非 200 时抛 `Literature sync failed`。
- `tests/literature-sync-section.test.ts`（新增，3 条）：
  - 源码断言：组件含 `/api/literature/sync`、aria-label、关键 import、`minHeight: 44`。
  - 源码断言：成功路径输出 4 个 `CardMetaRow` 字段（query / fetched / created / updated）。
  - 源码断言：`/literature` 页面 import 了 `LiteraturePubmedSyncClient` 并把它渲染在 `LiteratureSearchClient` 之上。

## Verification

Frontend gauntlet 全绿：
- `pnpm test` → **79 passed**（72 + 7 新增）。
- `pnpm typecheck` → pass。
- `pnpm build` → 7 routes，build OK（路由本身没新增）。

```bash
cd frontend && pnpm test && pnpm typecheck && pnpm build && echo "FRONTEND GAUNTLET GREEN"
```

后端未改动，gauntlet 无需重跑。

## Changed files

- `frontend/lib/api/literature.ts`
- `frontend/components/LiteraturePubmedSyncClient.tsx`（新增）
- `frontend/app/literature/page.tsx`
- `frontend/tests/literature-sync-api.test.ts`（新增）
- `frontend/tests/literature-sync-section.test.ts`（新增）
- `docs/handoffs/2026-05-21-a1-5-pubmed-sync-ui.md`（本文档）

## Current caveats

- 没做人工浏览器走查。提交后建议：起 `pnpm dev` + `fastapi dev`，在 `/literature` 跑一次「同步 PubMed」表单，确认能拉到真实 PMID。本机走 WSL 时记得在后端启动时带 `HTTPS_PROXY=http://172.26.0.1:7897`。
- 没有去重「正在同步」按钮 disabled 的国际化，只用了「同步中...」简单文案。
- `SyncResultItem` 的「查看文献详情 →」目前直接拼 `/literature/{id}`；当 sync 返回的新条目还没在 runtime 上 trigger 一次后端 reload（实际上 bulk_upsert 已经写盘），点进去应该能拿到。如果点进 404 说明 runtime 还在缓存，先重启后端。
- 没加 `LiteratureSearchClient` 顶部的「同步后立即检索」联动；同步完用户得自己再点检索。可作为后续 polish。
- 没有 toast / aria-live 通知，错误只展示在面板内。

## Recommended next step

阶段 A 还剩 3 颗：
- **A6 合规页扩展**（0.5d）：`/compliance` 加「数据来源说明」「PDF 版权声明」段，page-shell test 同步。建议下一颗推这个，跟 A1 + A1.5 共同把「真实 PubMed + 合规说明」这条产品线讲完整。
- **A2 最小访问控制**（1.5d）：sync 端点已经能写 runtime 状态，越早上 X-Access-Token 越好；security-review skill 上线后强制跑一遍。
- **A4 Playwright E2E**（1d）：装 Playwright，写一条 `/literature → 同步 PubMed → 选条目跳详情 → /rag → 问答 → 看 citation` 主路径。

我会建议：**A6 → A2 → A4**。先把合规面板完整，再上访问控制，最后用 E2E 把这条新链路锁住。
