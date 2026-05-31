# ADR-0010: 科研工作台长期模块路线图

日期：2026-05-08

## 状态

Accepted

## 背景

Qiyan Nexus 当前定位是面向特应性皮炎（AD）方向医生与科研人员的中医药证据与科研工作台。

当前开发重心已经从纯规划切换到可运行工程骨架，并完成了文献检索、文献详情、RAG mock 问答与引用卡片的最小证据链雏形。

长期来看，中医药科研工作流不止包含文献检索与 RAG。常见研究路径还包括网络药理学、分子对接、分子动力学模拟、机制图谱与报告生成。Qiyan Nexus 应保留这些长期模块方向，但当前阶段不能让重计算模块抢占证据工作台的开发主线。

## 决策

1. Qiyan Nexus 长期会包含网络药理学和分子模拟模块。
2. 当前阶段只实现“证据工作台 MVP-A”，包括文献检索、文献详情、PDF/样本文献入库、RAG 问答、引用卡片、合规声明与最小访问控制。
3. 网络药理学作为 MVP-B，在证据链稳定后推进。
4. 分子对接与分子动力学模拟作为 MVP-C 或 Pro 级增强模块，在网络药理学任务模型与候选成分/靶点对象稳定后推进。
5. 所有科研模块共享 task model、evidence model、citation model 的设计理念。
6. 当前阶段只做概念预留，不接真实重计算，不引入完整网络药理学 pipeline，不接分子对接或分子动力学运行环境。
7. 当前阶段不新建 herb、formula、compound、target、pathway、disease、protein、ligand、simulation_task 等完整业务表或模型；只在 literature、chunk、citation 设计时避免与这些未来对象冲突。

## 分阶段产品边界

### MVP-A：证据工作台

目标：让用户完成“查、读、问、引、导出”的 AD 中医药证据闭环。

包含：
- 文献检索
- 文献详情
- PDF 或样本文献入库
- RAG 问答
- 引用卡片
- chunk/citation 证据追溯
- 合规声明与数据来源说明
- 最小登录或白名单访问控制

暂不包含：
- 真实网络药理学计算
- 分子对接
- 分子动力学模拟
- 大规模知识图谱导入
- 完整 Celery/Redis/Neo4j/pgvector 基础设施

### MVP-B：网络药理学科研分析

目标：从文献、方剂、中药、成分、靶点和通路出发，生成可追溯的机制研究线索。

候选能力：
- 网络药理学任务壳
- herb / formula / compound / target / pathway / disease 概念对象
- 成分-靶点交集
- 疾病靶点交集
- PPI 网络
- GO/KEGG 富集
- 中药-成分-靶点-通路图谱
- 分析报告草稿
- 图表导出

推进原则：
- 先用 sample JSON 验证任务交互和数据模型。
- 再接真实数据库和异步任务。
- 每个分析结果必须能回指证据来源、参数版本和 citation。

### MVP-C：分子对接与分子动力学模拟

目标：把网络药理学筛出的关键成分-靶点组合推进到计算验证层。

候选能力：
- protein / ligand 概念对象
- 分子对接任务
- 分子动力学模拟任务
- 轨迹分析
- RMSD / RMSF / Rg / SASA / hydrogen bonds 等指标
- 图表与报告导出

推进原则：
- 分子对接优先于分子动力学模拟。
- 分子动力学只用于少数高价值候选组合，不做早期批量重计算。
- 任务必须异步执行，并保存输入、参数、工具版本、运行日志和输出文件。
- 早期只提供推荐模板参数，不开放复杂自由参数。

## 概念预留对象

后续 literature、chunk、citation 设计时，需要考虑它们未来可能关联以下科研对象：

- herb：中药
- formula：方剂
- compound：活性成分
- target：靶点
- pathway：通路
- disease：疾病或病理状态
- protein：蛋白结构对象
- ligand：小分子配体对象
- simulation_task：分子对接或分子动力学模拟任务

当前阶段只做命名和关系方向预留，不创建完整表结构，不实现真实计算。

## 共享模型方向

### task model

用于未来所有异步科研分析任务，包括网络药理学、分子对接、分子动力学模拟、PDF 解析和报告生成。

概念字段包括：
- task_id
- task_type
- status
- progress
- input
- output
- error
- created_at
- completed_at

当前阶段不要求实现完整 task model；只在 API 和数据设计中避免未来冲突。

### evidence model

用于统一表达文献、片段、数据库条目、图谱边、计算结果背后的证据来源。

概念字段包括：
- evidence_id
- evidence_type
- source
- source_url
- literature_id
- chunk_id
- database_version
- note

当前阶段优先服务 literature/chunk/citation。

### citation model

用于把 RAG 输出、网络药理学结论和模拟报告中的结论回指到具体证据。

概念字段包括：
- citation_id
- literature_id
- chunk_id
- quote
- reason
- related_entity_ids

当前阶段优先保证 RAG citation 可回指 literature/chunk。

## 后果

正面：
- 长期模块方向明确，避免每次讨论都重新定义网药和分子模拟的位置。
- 当前阶段仍然聚焦证据工作台，降低早期范围失控风险。
- literature/chunk/citation 的设计可以自然承接未来科研对象。
- 为后续 task model 和异步科研任务保留一致抽象。

代价：
- 网络药理学和分子模拟短期不会提供真实能力。
- 部分用户可感知的高级科研功能需要等证据链稳定后再开发。
- 早期文档需要反复强调“概念预留，不代表当前实现”。

## 验证

当前阶段的验证标准不是运行网药或分子动力学，而是：

1. MVP-A 的文献证据链稳定可用。
2. literature/chunk/citation 命名不阻碍未来关联 herb、formula、compound、target、pathway、protein、ligand 和 simulation_task。
3. README、AGENTS.md 或后续计划中明确说明网药为 MVP-B，分子对接/MD 为 MVP-C，避免近期开发误接真实重计算。

## 实施状态

**更新日期**: 2026-06-01

### MVP-A（证据工作台）
- ✅ 已完成：文献检索、文献详情、PDF 上传/解析、RAG 问答、引用卡片、合规声明、访问控制
- ✅ 已完成：PubMed 实时同步、RAG eval（50 题）、Playwright E2E

### MVP-B（网络药理学）
- ✅ 已完成：网络药理学任务壳（`/api/network/analyze`、`/network` 页面）
- ✅ 已完成：herb/formula/compound/target/pathway/disease 概念对象（sample 数据）
- ✅ 已完成：成分-靶点-通路链条展示
- ✅ 已完成：GO/KEGG 富集分析（mock，本地 JSON 字典 + scipy 超几何分布）
- ✅ 已完成：Markdown 报告导出（包含链条 + 富集分析）
- ✅ 已完成：citation/entity 双向跳转
- ❌ 未实现：真实 KEGG REST API、STRING 数据库、PPI 网络、网络图可视化

### MVP-C（分子对接/MD 模拟）
- ✅ **已完成（2026-06-01）**：Schema 预留（`backend/app/schemas/molecular.py`）
  - `Protein` - 蛋白结构对象
  - `Ligand` - 小分子配体对象
  - `DockingResult` - 分子对接结果
  - `MDSimulationConfig` - MD 模拟配置
  - `MDSimulationResult` - MD 模拟结果
  - `SimulationTask` - 对接/MD 模拟任务
- ✅ 测试覆盖：11 个 schema 验证测试
- ❌ 无 router、service 或 repository 实现
- ❌ 无前端页面或 API 集成
- ❌ 不应在当前代码中使用这些对象

**下一步**：MVP-C schema 已预留，实际功能实施需等待 MVP-B 稳定后再推进。
