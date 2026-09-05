# 2026-09-05 交接：三轮 UX 评审循环（输入边界/生命周期导航/异步反馈）

## 今日工作概览

1. **三轮「试用体验 → 问题清单 → 整改方案 → 优化整改」循环全部收口**（延续 09-03/09-04 模式，本轮向下探一层：输入与校验边界 → 任务生命周期与导航连续性 → 加载态与异步反馈）
   - 走查与逐项验证详见 `docs/reports/2026-09-05-ux-review-cycles.md`；问题清单在 `.scratch/ux-loop-2026-09-05/`（issues 01-06，含根因/方案/验证/评论）
   - 第 1 轮 `58f9855`（输入与校验边界）：分析对象加长度上限（后端 `max_length=100` + 前端 maxLength）；表型过短前端补拦截；network POST 提交路径改抛 `ApiStatusError` 并分层报错，422 不再伪装成「后端未启动」；研究协议 query_date 补「不能晚于今天」validator + 前端 date max（与疾病导入路径口径一致）
   - 第 2 轮 `a3f720d`（生命周期与导航）：新增 `lib/format-text.ts` `truncateLabel`，任务列表/结果页摘要/aria-label 对超长对象名截断（title 保留全名）；/literature 无查询初始态与 0 结果空态共用可点示例词
   - 第 3 轮 `896048f`（异步反馈）：rag.ts 三处 POST 改抛 `ApiStatusError`，RAG 失败显示 HTTP 状态码；network 轮询非 404 分支同步诚实化；判定流复查为非问题
   - 收口提交：循环记录 + handoff + AGENTS.md 硬约束补「错误折叠家族」一条

2. **重要模式确认（连续第三天回归）**：「非 2xx 折叠成无状态码错误 → UI 统一说后端未启动」家族已出现三处（09-04 issue 06 轮询 GET、09-05 issue 02 network POST、09-05 issue 06 rag POST）。本轮已把 network/rag 全部 POST 与轮询分支收齐并加测试锁定；AGENTS.md 硬约束已补防回归条目。

3. **新增测试**：`frontend/tests/network-input-boundaries.test.ts`（4）、`frontend/tests/query-label-truncation.test.ts`（3）、rag-empty-state / literature-empty-state / network-focus-prefill 扩展；后端 `test_network_api.py` +2（超长 query 422、未来 query_date 422）。前端 300 tests。

## 测试与门禁状态

- 每轮提交前 `verify-local.ps1` 全绿；收口 `verify-local.ps1 -IncludeE2E -E2eBackendPort 8010 -E2eFrontendPort 3000` 全绿（E2E 4/4，跑在预览 runtime 上）
- 后端 schema 变更两项：`NetworkAnalyzeRequest.query max_length=100`、`NetworkResearchProtocol.query_date` future validator——既有 fixture 日期（2026-07-11/12）均为过去，不受影响

## 转人工 / 遗留（诚实清单）

- **2026-09-04 issue 05（RAG 实体命中透明化）**：本轮走查再次复现（问「黄芪皂苷」模板句仍称「检索到相关证据片段」且引用不含该实体）。修法牵动检索排序与 50 题 eval 基线，需先拍板产品口径，维持 `状态: 需人工`
- 沿袭记录：/network omics UI 入口、CORS 多端口、AL vs ANL 新 snapshot——均需研究者/产品拍板
- UI 的 PDF 文件选择走查受浏览器自动化限制（IAB 不支持 file chooser）未覆盖，smoke API 已覆盖上传两步流

## 环境备注（下会话直接用）

- 预览 runtime `.tmp/ux-loop-0905/`（backend 8010 / frontend 3000）收尾已 `-Stop`，保留可复查；重启：`.\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp/ux-loop-0905 -BackendPort 8010 -FrontendPort 3000`
- 8000 被另一项目常驻占用，全程不可触碰；前端 CORS 固定 3000
- 浏览器自动化坑再确认两条：role 定位点击会假超时（elementFromPoint 验证 + evaluate click 即可）；**本地确定性接口 fetch <10ms 完成，try/catch 抓 isLoading 窗口的密集采样会漏检，判定加载行为要用「提交前后全文对照」而不是时间采样**
- runtime 里留有 3 个故意制造的边界任务（3500 字符/未来日期/特殊字符 query），用于复查截断展示，下次清理 runtime 即消失
