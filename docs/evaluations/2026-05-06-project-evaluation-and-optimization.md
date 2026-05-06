# Qiyan Nexus 项目评估报告与优化方案

日期：2026-05-06

## 1. 建议项目名称

推荐正式名称：Qiyan Nexus

一句话定位：面向特应性皮炎的中医药证据检索、RAG 问答与网络药理学科研工作台。

命名理由：
- Qiyan 可保留“岐研”的读音联想，能指向中医药与科研，但对外呈现为更国际化的英文品牌。
- Nexus 表示知识、文献、图谱、任务与报告的汇聚中枢。
- 比旧项目名更像产品名，也比长中文描述更短、更容易传播。

建议命名分层：
- 产品展示名：Qiyan Nexus
- 技术仓库名：qiyan-nexus；短期不建议立刻改本地目录名，避免破坏已有路径和脚本。
- 当前 MVP 副标题：AD 中医药证据与科研工作台

## 2. 当前状态判断

当前项目已经越过纯规划阶段，进入“可运行工程骨架 + 第一个文献检索切片”阶段。

已验证事实：
- 后端 FastAPI 骨架存在，含 /health 与 /api/literature/search mock API。
- 前端 Next.js 页面存在，含首页与 /literature 文献检索页。
- 后端测试通过：15 passed。
- 前端测试与构建通过：3 passed，pnpm build 通过。
- 当前业务实现仍是 mock 文献数据，不是真实文献检索、RAG、PDF 解析或图谱分析。

代码规模概览（排除 .git、node_modules、.venv、.next、__pycache__）：
- 总文件：67
- Markdown：22 文件 / 1285 行
- Python：17 文件 / 615 行
- TS/TSX/JS：8 文件 / 304 行
- HTML 原型：8 文件 / 8787 行

关键结论：这是一个“规划材料很丰富、工程实现刚起步”的项目。下一步不应继续扩愿景，而应收敛成可验证的临床科研工作流闭环。

## 3. 主要优点

### 3.1 病种聚焦正确
只做特应性皮炎（AD）是正确选择。它让文献库、知识图谱、RAG 评估和内测用户都能聚焦，避免一开始做成泛病种医疗 AI 平台。

### 3.2 产品边界较清晰
已有 Non-Goals：不做全病种、不替代诊断、不做普通患者 C 端、不自训大模型。这些边界对合规和交付都很重要。

### 3.3 技术路线基本合理
Next.js + FastAPI + PostgreSQL/pgvector + Redis/Celery + Neo4j 的组合可以支撑 MVP。

### 3.4 已形成工程验证习惯
后端有 pytest，前端有 node:test 与 build 验证。第一个文献检索切片已经按小步 TDD 推进，这是好的方向。

### 3.5 领域语言资产已经存在
CONTEXT.md 已定义 AD、GBS-Axis、NetPharm、Evidence-Chain、Citation-Card 等术语，适合作为后续 agent 和开发协作的统一上下文。

## 4. 核心问题与风险

### 4.1 产品定位里“诊疗”表述过重
原中文长名容易让用户和监管侧理解为临床诊断/治疗系统。实际 MVP 更接近“证据检索 + 科研辅助 + 报告生成”。

优化建议：
- 对外尽量使用“证据”“科研”“辅助”“工作台”。
- 避免首页主标题直接使用“精准诊疗”。
- AI 输出始终保留“非诊断结论、需结合临床”。

### 4.2 MVP 范围仍偏大
当前 MVP 包含文献检索、RAG、PDF 上传、网络药理学、知识图谱、认证、合规页面。对早期项目来说仍然是 6-7 条主线并行。

优化建议：把 MVP 拆为两层：
- MVP-A：证据工作台闭环
  1. 文献检索
  2. PDF 入库/解析
  3. RAG 问答 + 引用卡片
  4. 合规免责声明
- MVP-B：科研分析增强
  1. 网络药理学异步分析
  2. 知识图谱浏览
  3. 报告导出

先把 MVP-A 做到能给 5-10 个种子用户试用，再接 MVP-B。

### 4.3 任务拆解还是“模块级”，不是“交付切片级”
tasks.md 仍是 8 个大任务，很多任务依赖 Task 1，容易导致先搭一堆基础设施，但没有用户可感知的闭环。

优化建议：改成纵向切片：
1. 静态样本文献检索闭环（已完成）
2. 本地 JSON/SQLite 文献源替换 mock 数据
3. PDF 上传后生成文献记录
4. RAG 问答返回引用卡片
5. 登录白名单保护页面
6. 异步任务只先跑一个 mock NetPharm 任务
7. 再接 Redis/Celery/pgvector/Neo4j 等真实依赖

### 4.4 技术文档与实际依赖存在漂移
文档写 Next.js 15、Ant Design 5；实际 package.json 使用 Next.js 16.2.4、antd 6.1.0、React 19.2.3。

风险：后续开发者按文档排错时会误判。AntD 6 与 Next 16 的渲染行为也可能与早期方案不同。

优化建议：
- 要么冻结回文档版本；要么更新 ADR/AGENTS/README，把实际版本作为当前事实源。
- 现阶段建议接受实际版本，但补一个 ADR：前端实际基线为 Next.js 16 + React 19 + Ant Design 6。

### 4.5 文献数据策略需要更现实
ADR-0001 说中文约 1000 篇手动 PDF 入库、英文 PubMed API 实时检索。方向合理，但缺少最小数据治理标准。

优化建议先定义最小文献 schema：
- id
- title
- authors
- year
- language
- source_type
- source_name
- abstract/snippet
- keywords
- file_id（可选）
- citation_url 或 pubmed_id（可选）

先用 20-50 篇人工精选 AD 文献作为黄金样本集，用它做检索与 RAG 质量评估，不要一开始追求 1000 篇。

### 4.6 RAG 质量评估缺失
当前需求要求“引用卡片”和“置信度”，但没有定义如何判定答案可用。

优化建议新增一个 RAG eval 数据集：
- 20 个 AD/GBS-Axis/方剂/通路问题
- 每题标准引用文献或片段
- 评价维度：引用准确性、是否超出证据、是否出现诊断建议、回答完整度
- 先用人工评分，不急着引入复杂评测框架

### 4.7 过早引入 Neo4j 可能增加复杂度
知识图谱是亮点，但如果在文献/RAG 之前接 Neo4j，容易让工程复杂度上升而用户价值不明显。

优化建议：
- 第一阶段用后端返回简单 nodes/edges JSON，前端先完成图谱交互壳。
- 真实 Neo4j 导入放到 MVP-B。
- 图谱数据先从小型草药-成分-靶点样本集开始，不直接导入大库。

### 4.8 合规页面还不够落地
已有免责声明，但还缺：隐私政策、用户协议、数据来源声明、AI 使用说明、上传 PDF 版权/合规提示。

优化建议：
- 合规作为 P0，不是上线前再补。
- 所有上传、RAG、报告页都显示用途边界。
- 对内测用户明确：仅科研辅助，不处理真实可识别患者隐私数据。

## 5. 推荐优化后的产品方案

### 5.1 新定位
Qiyan Nexus 是一款面向特应性皮炎方向医生与科研人员的中医药证据与科研工作台，提供中英文文献检索、引用可追溯的 RAG 问答、PDF 文献管理，以及后续网络药理学与知识图谱分析。

### 5.2 第一版用户
优先只服务三类人：
1. 中医/皮肤科研究生：查文献、整理引用、生成研究思路。
2. 皮肤科/中医皮肤科医生：快速查证据，但不替代诊断。
3. PI/方法学合作者：看网络药理学报告和图谱导出。

### 5.3 第一阶段核心闭环
建议第一阶段只做一条闭环：

检索 AD 相关文献 → 打开文献详情 → 对文献或检索结果提问 → 返回带引用卡片的回答 → 导出/复制证据摘要。

这条闭环完成后，项目才真正具备可内测价值。

### 5.4 功能优先级重排
P0：
- 文献数据 schema 与本地样本库
- 文献检索真实数据替换 mock
- RAG 问答 API mock → 最小真实实现
- 引用卡片组件
- 合规声明与数据来源声明
- 基础登录/白名单，可先极简实现

P1：
- PDF 上传与解析
- pgvector 接入
- RAG eval 样本集
- 用量限制

P2：
- Celery 异步网络药理学
- Neo4j 图谱
- 报告导出
- Sentry/BetterStack/Nginx/PgBouncer

暂缓：
- 复杂付费策略
- 移动端适配
- 大规模知识图谱导入
- 多病种扩展

## 6. 技术方案优化

### 6.1 保持 monorepo，但明确事实源
建议结构：
- README.md：给人看的启动入口
- AGENTS.md：给 agent 的仓库地图
- CONTEXT.md：领域词典
- docs/adr/：决策记录
- docs/plans/：执行计划
- docs/evaluations/：评估报告
- frontend/：Next.js
- backend/：FastAPI
- infra/：只放已验证的本地基础设施

Cursordos/ 与 Traedos/ 建议保留为 archive，不再作为事实源继续修改。

### 6.2 先抽象 repository，不急着上数据库
当前 search_literature 直接读 _SAMPLE_ITEMS。下一步最好抽成：
- LiteratureRepository 接口/协议
- InMemoryLiteratureRepository
- 后续 PgvectorLiteratureRepository

这样可以在不接 PostgreSQL 的情况下，先把 API、测试和前端交互稳定下来。

### 6.3 API 路径建议稳定下来
建议：
- GET /api/literature/search
- GET /api/literature/{id}
- POST /api/rag/query
- POST /api/documents/upload
- POST /api/netpharm/tasks
- GET /api/netpharm/tasks/{task_id}

先不要频繁改路径，避免前端和测试漂移。

### 6.4 配置管理需要提前补齐
当前配置只有 APP_NAME 和 ENVIRONMENT。下一步建议补：
- CORS_ORIGINS
- DATABASE_URL
- REDIS_URL
- STORAGE_ENDPOINT
- DEEPSEEK_API_KEY（只在 .env.example 写变量名）
- CLAUDE_API_KEY 或代理入口变量

但不要马上实现所有外部连接。先让配置入口稳定。

### 6.5 前端先别急着重 Ant Design
当前页面用原生 inline style，构建稳定。考虑到此前 AntD 组件在静态构建阶段可能有坑，建议下一步仍优先保证 build 通过。可以先抽出设计 token 和普通组件，再逐步引入 AntD。

## 7. 未来两周建议执行路线

### 第 1-2 天：收口命名与文档事实源
- 将 README、首页、metadata 的展示名统一为 “Qiyan Nexus”。
- 新增 ADR：前端实际版本基线。
- 更新 quality-score.md，不再写“规划期 · 无代码”。
- 标记 Cursordos/Traedos 为历史资料。

### 第 3-5 天：真实文献样本库
- 定义 LiteratureItem schema。
- 建立 data/literature/sample_ad_literature.json。
- 把 _SAMPLE_ITEMS 从 service 移到 repository/data 层。
- 后端测试覆盖中文/英文/来源筛选/空结果。
- 前端展示空状态、错误状态、结果数量。

### 第 6-8 天：文献详情 + 引用卡片
- 新增 GET /api/literature/{id}。
- 新增 /literature/[id] 页面。
- 建立 CitationCard 组件。
- 所有引用展示必须包含来源、片段、年份、来源类型。

### 第 9-12 天：RAG 最小闭环
- POST /api/rag/query 先接 mock retriever。
- 返回 answer + citations。
- 前端新增 /rag 页面。
- 建立 20 条 RAG eval 问题。

### 第 13-14 天：内测前合规壳
- 新增 /compliance 页面。
- 新增隐私政策、用户协议、AI 使用说明草案。
- 在上传、RAG、报告入口统一提示“不上传真实可识别患者隐私数据”。

## 8. 建议改动清单

立即改：
- README 标题与首页展示名统一改为 “Qiyan Nexus”。
- docs/quality-score.md 从规划期评分改为开发启动期评分。
- 新建 docs/evaluations/2026-05-06-project-evaluation-and-optimization.md（本文件）。

近期改：
- 新增 ADR-0009：前端实际版本基线与 AntD 使用策略。
- 新增 docs/plans/2026-05-06-literature-data-slice.md：真实文献样本库切片计划。
- 把 tasks.md 拆成 issue 级任务。

不要急着改：
- 不要立刻接完整 Docker Compose。
- 不要立刻接 Neo4j Aura。
- 不要立刻下载/部署双 embedding 模型。
- 不要现在改仓库目录名，避免路径和 wiki 指针失效。

## 9. 最终判断

项目方向值得继续，但应该从“宏大中医药精准诊疗平台”降维成“AD 专病证据与科研工作台”。

更好的产品叙事是：
- 少说诊疗，多说证据。
- 少说一体化，多说工作流闭环。
- 少做横向功能堆叠，多做纵向可用切片。

推荐名称 “Qiyan Nexus” 可以承接中医药特色、科研定位和知识中枢的产品心智，同时降低医疗诊断承诺感。