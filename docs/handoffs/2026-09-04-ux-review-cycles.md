# 2026-09-04 交接：三轮 UX 评审循环（前端时区/深链/文案整改）

## 今日工作概览

1. **三轮「试用体验 → 问题清单 → 整改方案 → 优化整改」循环全部收口**（沿用 2026-09-03 首轮循环模式，本轮向下探一层：UI 实际操作、深链边界、同步/导出/文案一致性）
   - 走查与逐项验证详见 `docs/reports/2026-09-04-ux-review-cycles.md`；问题清单在 `.scratch/ux-loop-2026-09-04/`（issues 01-08，含根因/方案/验证/评论）
   - 第 1 轮 `8da1746`（UI 全页面走查）：默认查询日期 UTC→本地（东八区 8 点前慢一天）、任务创建时间 UTC→本地（慢 8 小时）、文献 0 结果空态补示例词引导、CardMetaRow 空 `<p>`
   - 第 2 轮 `df51b24`（深链/边界走查）：网络 fetcher 改抛 `ApiStatusError`，坏 task_id 深链 404 诚实报错 + 「回到我的研究」恢复链接；`?focus=` 实体深链从「自动建任务」降级为纯预填（点 chip 不再静默写入任务，target 不再被标「复方」）
   - 第 3 轮 `6a9b9d5`（同步/导出走查）：DemoDataBanner 删除「未对接 PubMed 真实库」旧话术（与 pubmed_live 实时同步自相矛盾），改为按 seed/PubMed live/上传 PDF 三类来源分述
   - 收口提交：循环记录 `e0c7916`；AGENTS.md 硬约束段补 omics 边界 `0107fdf`

2. **新增共享工具与测试**：`frontend/lib/format-date.ts`（本地日期/分钟格式化）；`ApiStatusError`（`lib/api/client.ts`）；format-date / card-meta 渲染 / 空态引导 / focus-prefill 重写 / demo-banner 等 6 处测试；前端 290 tests。

## 测试与门禁状态

- 每轮提交前 `verify-local.ps1` 全绿；收口 `verify-local.ps1 -IncludeE2E -E2eBackendPort 8010 -E2eFrontendPort 3000` 全绿（E2E 4/4）
- API 边界复查全诚实：装配门禁 409 结构化 blockers、DOCX 拒手工 payload（integrity 设计）、`source=uploaded` 422 结构化报错（UI 走 `has_pdf_upload`）、mock 任务靠读推进（惰性完成，既有设计）

## 转人工 / 遗留（诚实清单）

- **issue 05（`状态: 需人工`）**：RAG 回答模板句在问题实体无 chunk 命中时仍称「检索到相关证据片段」（问 IL6 时引用全文不含 IL6）。修法牵动检索排序与 50 题 eval 基线，需先拍板产品口径（实体未命中提示 / 降 citation / 改模板）
- 沿袭 2026-09-03 记录：/network omics UI 入口、CORS 多端口、AL vs ANL 新 snapshot——均需研究者/产品拍板
- UI 的 PDF 文件选择走查受浏览器自动化限制未覆盖（smoke API 已覆盖上传两步流）

## 环境备注（下会话直接用）

- 预览已停止，`.tmp/ux-loop-0904/`（isolated runtime，backend 8010 / frontend 3000）保留可复查；重启：`.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp/ux-loop-0904 -BackendPort 8010 -FrontendPort 3000`
- 8000 被另一项目常驻占用，全程不可触碰；前端 CORS 固定 3000
- `pnpm build` 会把 `frontend/next-env.d.ts` 的 routes 类型路径在 dev/build 间来回改——build 后若树脏，`git checkout -- frontend/next-env.d.ts` 即可，不是代码问题
- 浏览器自动化在本项目 dev 页面上 role 定位点击可能超时（`elementFromPoint` 验证无遮挡后改用 evaluate 触发 DOM click 即可），属工具行为非产品缺陷
