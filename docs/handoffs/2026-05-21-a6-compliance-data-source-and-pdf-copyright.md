# A6 合规页扩展：数据来源说明 + PDF 版权声明

日期：2026-05-21
路线图：`docs/plans/2026-05-21-roadmap.md` §3.1 阶段 A · Slice A6
分支：`feat/rag-citation-pdf-provenance-batch`（沿用同一颗 feat 分支批量推进 A 阶段）

## Goal

按路线图阶段 A 第六颗 slice，在 `/compliance` 页面追加两段合规章节：「数据来源说明」与「PDF 版权声明」。

- 数据来源说明：解释 seed sample / PubMed live sync / 上传 PDF 三类来源的边界。
- PDF 版权声明：限定本地用途、不分发、用户须自证合法访问权、下架处理流程。

不接外部数据库授权、不动 runtime 行为、不动 RAG / 文献 API。纯前端文案 + 测试。

## Completed

### Frontend：`lib/compliance-page.ts`

- `getCompliancePageIntro().summary` 文案扩展：补「数据来源与 PDF 版权边界」。
- `getComplianceHighlights()` 从 4 段扩到 6 段，新增固定顺序的：
  - 「数据来源说明」3 条：CN seed 仅演示 / PubMed 实时同步遵守 NCBI 条款 / 上传 PDF 仅本地 runtime。
  - 「PDF 版权声明」3 条：仅本地用途与不再分发 / 用户自证权利 / 下架后清理 runtime 与 literature 状态。
- `getComplianceNavigationLinks()` 保持不变（A6 不涉及导航）。

页面 shell `app/compliance/page.tsx` 走的是 `highlights.map`，不需要改 tsx —— 两段新章节自动渲染为统一卡片。

### Frontend：测试

- `tests/compliance-page.test.ts` 扩到 5 条：
  - intro summary 文案 byte-level 锁定到新版。
  - highlights 6 段固定顺序与既有"非诊断结论"断言保留。
  - 数据来源段：关键词 `seed` / `PubMed` / `NCBI` / `上传 PDF` / `演示` 都必须出现。
  - PDF 版权段：`仅在本地` / `不公开|不分发|不再分发` / `版权` / `研究` 都必须出现。
  - navigation links 保持原断言。

按 TDD 节奏：先写 5 条（4 条 fail），再改 `lib/compliance-page.ts`，全部转绿。

## Verification

Backend gauntlet（未触碰，作为 sanity check）：
- `ruff format --check app tests` → 50 files already formatted
- `ruff check app tests` → All checks passed!
- `mypy app` → no issues in 30 source files
- `pytest -q` → **111 passed**

Frontend gauntlet 全绿：
- `pnpm test` → **81 passed**（本 slice 在原 4 条上扩了 1 条 intro + 改名 `six minimum` + 新增 2 条数据来源 / PDF 版权断言，共 5 子测试；总数差异来自累计其它 slice）
- `pnpm typecheck` → pass
- `pnpm build` → 7 routes，build OK

完整一行命令：
```bash
cd backend && .venv/bin/python -m ruff format --check app tests && .venv/bin/python -m ruff check app tests && .venv/bin/python -m mypy app && .venv/bin/python -m pytest -q && echo "BACKEND GAUNTLET GREEN"
cd frontend && pnpm test && pnpm typecheck && pnpm build && echo "FRONTEND GAUNTLET GREEN"
```

## Changed files

- `frontend/lib/compliance-page.ts`
- `frontend/tests/compliance-page.test.ts`
- `docs/handoffs/2026-05-21-a6-compliance-data-source-and-pdf-copyright.md`（本文档）

## Current caveats

- 「数据来源说明」与「PDF 版权声明」是文案级条款，**不绑定运行时**。下架请求落地需要后端 `DELETE /api/literature/{id}` 等接口配合，A 阶段没排，留给阶段 B 真实化时一起处理。
- 文案里出现的"NCBI / PubMed / CNKI / 万方"是事实陈述与边界声明，不是合同；正式上线前需要法务过一遍。
- `page-shell-consistency.test.ts` 之前没有覆盖 `/compliance` 自身（compliance 是其它页面的"模板"），所以本 slice 没有 page-shell 锁定的副作用。

## Recommended next step

阶段 A 还剩 4 颗：
- **A1.5 PubMed 同步前端入口**：已在 commit `24a9a3c` 里落了同步面板；如果验收 OK，可标记 A1 完成、推进下一颗。
- **A2 最小访问控制**（1.5d）：阻塞内部走查最关键的一颗；上线后必跑 `security-review` skill。
- **A4 Playwright E2E**（1d）：装 Playwright 写一条 `/literature → 详情 → /rag → 问答 → citation` 串联；需先 `update-config` 加 `pnpm e2e` allowlist。
- **A5 真实中文 PDF 人工验收**（0.5d）：依赖用户上传 2-3 个真实 PDF，无法独立推进。

下一颗推荐 **A2 最小访问控制**：纯后端中间件 + env 白名单 + 401/200 双路测试，无外部依赖，且是封闭走查前置条件。
