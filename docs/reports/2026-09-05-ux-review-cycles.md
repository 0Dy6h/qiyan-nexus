# 2026-09-05 UX 评审循环记录（三轮：使用体验 → 问题清单 → 整改方案 → 实施验证）

> 环境：内部预览 isolated runtime（backend 8010 / frontend 3000，open dev mode，`-RuntimeRoot .tmp/ux-loop-0905`）。
> 延续 `docs/reports/2026-09-03-ux-review-cycles.md`、`docs/reports/2026-09-04-ux-review-cycles.md`；本轮向下探一层，避开已收口面（工具链、全流程 happy path、深链 404/focus 预填、同步/导出/文案、时区/空态引导）与遗留产品决策项（RAG 实体命中透明化、/network omics UI、CORS 多端口、AL vs ANL snapshot）。
> 问题清单与逐项验证记录：`.scratch/ux-loop-2026-09-05/`（PRD + issues 01-06）。

## 第 1 轮：输入与校验边界（/network 协议表单、/literature、/rag）

**走查路径**：/network 表单逐字段边界（空提交、纯空白、3500 字符超长、`<script>`/emoji 特殊字符、表型清空与过短、未来查询日期）→ /literature 特殊字符深链 → /rag 空问题、top_k 0/9999。

**问题清单（3 项）与整改**（commit `58f9855`）：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 01 | P2：分析对象无长度上限，3500 字符可建成任务并整串多处渲染 | `NetworkAnalyzeRequest.query` 只有 `min_length=1`（schema 其余字段均有上限，唯独 query 缺）；前端无 maxLength | 后端 `max_length=100` + 前端 maxLength/提交校验 | 后端 422 测试；前端超长输入被截断 |
| 02 | P1：表型过短（1-3 字）前端不拦，后端 422 被 UI 折叠成「提交分析任务失败，请确认后端服务已启动」 | `submitNetworkAnalysis` 抛无状态码 Error（09-04 ApiStatusError 修复只覆盖 GET，POST 漏修）+ 组件裸 catch | POST 路径改抛 `ApiStatusError`；catch 分层（422/HTTP 状态码/真网络故障）；前端补 4-200 字校验 | UI：`AD` 提交 → 前端拦截；500/422 不再出现 backend-down 误导 |
| 03 | P2：未来查询日期前后端都不拦，与疾病导入路径校验口径矛盾 | `NetworkResearchProtocol` 无 future validator；date input 无 max | 协议补 `query_date cannot be in the future` validator；前端 `max` + 提交校验 | 后端 2099 → 422；UI 拦截 |

**非问题记录**：空/纯空白提交有校验且不建任务；特殊字符 React 转义安全（script 不执行）；疾病范围/研究物种为 readOnly 固定值与枚举一致；/literature 特殊字符查询空态引导正常；/rag 空问题拦截、top_k min=1 浏览器钳制（9999 上限缺失在演示语料下被服务端收敛，无实际影响）。

## 第 2 轮：任务生命周期与导航连续性（列表/详情/后退/多任务）

**走查路径**：/tasks 列表（含 R1 留下的超长对象任务、特殊字符任务、未来日期任务三个"垃圾"任务的呈现）→ 超长任务结果页深链 → 后退/前进 → /literature 分页与详情 → 侧栏 active 状态。

**问题清单（2 项）与整改**（commit `a3f720d`）：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 04 | P2：超长对象名在任务列表单元格/结果页摘要句/查看 aria-label 整串渲染，列表成文字墙 | 展示层无截断；R1 输入上限只管新任务，legacy/导入数据无防御 | 新增 `lib/format-text.ts` `truncateLabel(40)`；列表、摘要句、aria-label 全部走截断，全名经 `title` 保留 | UI：怪物任务列表页从上万字符回到 724 字符，title 悬停见全名 |
| 05 | P3：/literature 无查询初始态只有纯文本提示，示例词不可点，弱于 0 结果空态 | 示例词按钮块整体包在 `hasSearched` 条件里 | chips 移出条件与 idle 共用；idle 补独立引导文案；语料边界说明保持 0 结果专属 | UI：无查询进入可见可点示例词，点击出 6 条结果 |

**非问题记录**：后退/前进导航连续（结果深链回载正常）；侧栏 `aria-current="page"` 已实现；legacy 任务展示冻结的未来查询日期属审计语义（协议运行前冻结，不改写历史）；文献分页/详情返回正常。

## 第 3 轮：加载态与异步反馈（防重/错误态/恢复）

**走查路径**：/network 开始分析三连点（提交/轮询窗口）→ /rag 二次提交密集采样（200 点）→ 页内拦截 fetch 注入 500 的错误态与恢复 → 判定流双击与错误分离复查 → PubMed 同步防重 → 文献/RAG 提交按钮防重复。

**问题清单（1 项）与整改**（commit `896048f`）：

| # | 问题 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| 06 | P2：RAG 生成失败把服务端 500 折叠成「请求失败，请确认后端服务已启动」，误导排查方向 | `rag.ts` answer/导出三处 POST 抛无状态码 Error + 组件裸 catch（同折叠家族第三处） | 三处改抛 `ApiStatusError`；catch 分层；network 轮询非 404 分支同步诚实化 | UI：注入 500 → 「生成回答失败（HTTP 500）」，backend-down 文案消失；撤拦截重试恢复 |

**非问题记录**：三个提交按钮均有 `isBusy`/`isLoading` 防护（/network 三连点仅 +1 任务）；判定流写/读错误分离 + 同步 ref 双击防护为既有设计；PubMed 同步有防重；「RAG 加载期旧答案残留」为采样假象——localhost fetch <10ms 完成，加载窗口真实存在但极短，二次提交实测正常换新答案。

## 门禁与提交

- 第 1 轮 `58f9855`、第 2 轮 `a3f720d`、第 3 轮 `896048f`；每轮提交前 `verify-local.ps1` 全绿（后端 45 tests 含 2 新增；前端 294→298→300 tests）。
- 收口：`verify-local.ps1 -IncludeE2E -E2eBackendPort 8010 -E2eFrontendPort 3000` 全绿（E2E 4/4）。

## 遗留候选（不在本次范围）

- 2026-09-04 issue 05（RAG 实体命中透明化）：本轮实测再次复现其现象（问「黄芪皂苷」仍称「检索到相关证据片段」且引用不含该实体），维持 `状态: 需人工`，待产品口径拍板
- /network omics UI 入口、CORS 多端口、AL vs ANL 新 snapshot——维持 2026-09-03/09-04 记录
- UI 的 PDF 文件选择走查继续受浏览器自动化限制（IAB 不支持 file chooser），smoke API 已覆盖上传两步流，维持转人工
