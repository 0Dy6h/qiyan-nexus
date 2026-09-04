# 2026-09-04 UX 评审循环记录（三轮：使用体验 → 问题清单 → 整改方案 → 实施验证）

> 环境：内部预览 isolated runtime（backend 8010 / frontend 3000，open dev mode，`-RuntimeRoot .tmp/ux-loop-0904`）。
> 延续 `docs/reports/2026-09-03-ux-review-cycles.md`；本轮向下探一层，避开已收口面（工具链、全流程 happy path、负路径 API）与遗留产品决策项（/network omics UI、CORS 多端口、IL6/STAT3/TNF 真实数据）。
> 问题清单与逐项验证记录：`.scratch/ux-loop-2026-09-04/`（PRD + issues 01-08）。

## 第 1 轮：前端 UI 全页面走查（浏览器实际操作）

**走查路径**：首页 → /network 建任务（mock，5 链）→ 结果渲染（门禁/lineage/图谱/富集/免责声明）→ 逐行人工判定（IL6 纳入，进度投影更新）→ /tasks 列表 → /literature?q=IL6（诚实 0 结果）→ /rag 深链问答（2 citations + 免责声明）→ 文献详情 → /compliance → `?task_id=` 回载（判定投影持久）。

**问题清单（4 项）与整改**（commit `8da1746`）：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 01 | P1：默认查询日期是 UTC，东八区 8 点前默认成昨天（实测 09-03） | `NetworkAnalysisClient` 用 `toISOString().slice(0,10)` | 新增 `lib/format-date.ts` 本地日期工具，默认值改本地日历日 | UI 默认=当天；format-date 测试 |
| 02 | P1：任务创建时间显示 UTC 原串，慢 8 小时 | `formatNetworkTaskCreatedAt` 字符串切片不转时区 | 先 `new Date` 解析按本地分钟渲染，非时间串回退旧切片 | UI 时间与本地钟一致；时区无关断言 |
| 03 | P2：链路「查相关文献」深链（IL6/TNF/STAT3）必 0 结果且空态无引导 | 空态只有通用文案，未说明演示语料覆盖 | 空态补语料边界说明 + 「消风散/特应性皮炎/atopic dermatitis」一键示例检索 | 深链 0 结果 → 点建议词 6 条 |
| 04 | P3：CardMetaRow 全空项渲染空 `<p>` | 无条件渲染 join 结果 | 空串返回 null | renderToStaticMarkup 断言 |

**非问题记录**：role-based click 超时是自动化工具动作性问题（`elementFromPoint` 验证无遮挡，JS click 生效）；`retrievedAt`/`chemblRetrievedAt` 保持 UTC（机器元数据语义正确）；报告导出文件名内 UTC 为机器标识不改。

**转人工**（issue 05，`状态: 需人工`）：RAG 回答模板句在问题实体无 chunk 命中时仍称「检索到相关证据片段」（问 IL6 时引用全文不含 IL6）。属检索质量域，牵动 eval 基线（AGENTS.md 检索排序约束），需先拍板产品口径。

## 第 2 轮：报告 / 判定边界 / 装配门禁 / 深链走查

**走查路径**：判定任务 report markdown（人工判定段、逐行表、免责声明齐全，判定时间明确标 UTC）→ 坏 task_id 的 result/report（404）→ 装配计划 POST（409 `assembly_gate_blocked` 全量结构化 blockers）→ RAG 引用卡 PDF 预览链（200 application/pdf）→ `/evals/rag-ad` 运行（96% 通过、50 题明细）→ `/network?focus=` 实体深链。

**问题清单（2 项）与整改**（commit `df51b24`）：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 06 | P1：坏 task_id 深链误报「轮询失败，请确认后端已启动」且无恢复入口 | fetcher 把所有非 2xx 折叠成无状态码 Error | 新增 `ApiStatusError`；404 显示「未找到该任务…」+「← 回到我的研究」链接 | UI 复查；源码断言 |
| 07 | P1：focus 实体深链被动触发分析写入（点 chip 即建任务、target 被标「复方」、离开页面任务卡 running） | focus effect 直接 `runAnalysis`，kind 映射 `herb ? herb : formula` | focus 降级为纯预填：herb/formula 预填+提示确认；compound/target/pathway 不预填并指路文献/RAG | 任务数 walk-through 前后恒 3；重写 focus-prefill 测试 |

**非问题记录**：mock 任务靠读推进（惰性完成）为既有设计，随 07 取消 auto-run 后不再产生卡 running 的新任务；报告 GET 只读边界由既有测试覆盖。

## 第 3 轮：筛选 / 同步 / 导出 / 文案一致性走查

**走查路径**：文献排序（year_desc 有序）、来源过滤（pubmed 过滤 seed PubMed 样本且 record_origin 标注诚实）、`has_pdf_upload` 过滤、RAG answer → DOCX 导出全链（integrity_token 拒手工 payload 422/409 为防篡改设计；正规 round trip 200 且 zip 结构合法）、UI「同步 PubMed」（真实拉取 5 条 pubmed_live，成功面板「新增 5 · 刷新 0」）。

**问题清单（1 项）与整改**（commit `6a9b9d5`）：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 08 | P2：演示数据横幅声称「未对接知网/PubMed 真实库」，与同页来源说明及刚发生的实时同步自相矛盾 | banner 文案是 PubMed live sync 上线前的旧话术 | 按来源分述：中文 seed 未对接知网/万方、PubMed 为 NCBI 实时同步（守条款限速）、上传 PDF 仅本地 runtime；测试显式禁止旧短语回归 | /literature、/rag 横幅复查 |

**非问题记录**：`source=uploaded` 422 是探测参数用错（API 结构化报错正确，UI 走 `has_pdf_upload`）；DOCX 拒绝手工 payload 为 integrity 设计。

## 门禁与提交

- 第 1 轮 `8da1746`、第 2 轮 `df51b24`、第 3 轮 `6a9b9d5`；每轮提交前 `verify-local.ps1` 全绿（前端 290 tests）。
- 收口：`verify-local.ps1 -IncludeE2E`（隔离端口）全绿。

## 遗留候选（不在本次范围）

- issue 05（RAG 实体命中透明化）转人工拍板口径
- /network omics UI 入口、CORS 多端口、AL vs ANL 新 snapshot——维持 2026-09-03 记录
