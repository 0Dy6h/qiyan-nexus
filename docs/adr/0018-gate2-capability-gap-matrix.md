# ADR-0018 Gate 2：夏枯草四步路径能力/差距/前置门禁矩阵

- 关联 ADR：[ADR-0018](0018-omics-strategy-platform-contract.md)（Accepted）
- 日期：2026-08-15
- 执行方：TraeWork
- 状态：已完成

---

## 目的

根据 ADR-0018 Gate 2 要求，将北极星案例——夏枯草干预甲状腺疾病整合研究的四步路径（古籍数据挖掘 → 网络药理学 → 分子对接 → 分子动力学）映射为平台当前能力、差距与前置门禁矩阵。

**边界声明**：
- 本矩阵只作能力蓝图，不批准任何代码实现
- 不新增甲状腺病种（仍为特应性皮炎）
- 不实现对接/MD（仍为 schema 预留）
- 不接组学数据
- `formal_network_ready` 保持 `false`

---

## 四步路径总览

```
古籍数据挖掘 → 网络药理学 → 分子对接 → 分子动力学
     ↑              ↑            ↑           ↑
  Step 1        Step 2       Step 3     Step 4
  知识层        系统层       计算验证    计算验证
```

跨步骤依赖关系：
- Step 1 → Step 2：文献/古籍证据支撑网络边的科研 claim
- Step 2 → Step 3：网络靶点成为对接的蛋白靶标
- Step 3 → Step 4：对接结果（结合构象）作为 MD 模拟的初始构象
- Step 4 → Step 2：MD 验证结果回投网络边，修正证据等级

---

## Step 1：古籍数据挖掘

### 当前能力

| 能力 | 状态 | 说明 |
|---|---|---|
| 文献检索 | ✅ 可用 | `/api/literature/search` 支持 CN/EN/ PubMed 四来源视图，关键词检索与排序 |
| PDF 上传与解析 | ✅ 可用 | `POST /api/uploads/pdf` + `POST /api/uploads/pdf/auto-parse`，pypdf 文本预览 |
| RAG 证据问答 | ✅ 可用 | `/api/rag/answer` deterministic + keyword，返回 citation cards + 免责声明 |
| 引用导出 | ✅ 可用 | Markdown + DOCX 导出，HMAC integrity_token 签名 |
| 跨语言术语桥 | ✅ 可用 | CN↔EN 术语桥 + entity token 注入（消风散/黄芪等可匹配关联文献） |
| 记录来源标注 | ✅ 可用 | `record_origin` 区分 seed_sample / pubmed_live |

### 差距

| 差距 | 影响 | 优先级 |
|---|---|---|
| 无古籍专项数据源 | 平台无结构化古籍文本数据库，无法做古籍数据挖掘 | 高（但属证据服务层扩展，不占工程主线） |
| 古籍文本无结构化标注 | 无法从古籍文本中自动抽取方药-证候-治法关联 | 中 |
| 文献库为小型构造样本 | seed 约数十篇，不可当作外部真实文献引用 | 中（可用 `seed_pubmed_corpus.py` 拉取真实 PubMed） |
| 检索质量未验证 | `precision@5` / `MRR@5` 仍为 null，150 个 Track A 标签未填 | 高（并行 HITL，不占工程主线） |

### 前置门禁

1. 证据服务层必须按网络研究对象绑定（ADR-0017 强制要求）
2. 古籍数据源需确认许可/授权/伦理边界
3. 古籍挖掘是成为证据服务层专项能力还是仅作方法学参照（开放问题 5，待 Gate 3 前决策）

---

## Step 2：网络药理学（系统层核心）

### 当前能力

| 能力 | 状态 | 说明 |
|---|---|---|
| 研究协议门禁 | ✅ 已落地 | 疾病/表型/物种/证据策略/查询日期强制持久化 |
| Mock 网络分析 | ✅ 已落地 | seed graph 包含消风散→荆芥→槲皮素→IL6→PI3K-Akt→AD 等 5 条链 |
| Live 网络分析 | ✅ opt-in | TCMSP→PubChem→ChEMBL→UniProt→STRING→KEGG 多步链路 |
| 双侧 raw-artifact provenance | ✅ 已落地 | Open Targets 疾病侧 + ChEMBL 成分侧，SHA-256 + manifest + 不可变快照 |
| 逐行 lineage | ✅ 已落地 | disease/compound/intersection 分开建模，stable row ID，canonical symbol 交集 |
| 人工 adjudication | ✅ 已落地 | append-only 审计流，latest-wins 投影，reviewer_id 持久化 |
| 候选装配门禁 | ✅ 已落地 | source_bound_network_assembly_v1，原子封存不可变计划 |
| GO/KEGG 富集 | ✅ mock | 本地 JSON 字典 + scipy 超几何分布，14 个显著富集项 |
| 证据分级 | ✅ 已落地 | mock_inferred / predicted / literature_supported / experimental 确定性纯函数 |
| Markdown 报告导出 | ✅ 已落地 | 协议、lineage、证据分级、阻塞项、免责声明 |
| 独立 validator | ✅ 已落地 | 零共享代码路径复算 hash/count/refs/阈值 |
| 网络图可视化 | ✅ 已落地 | 确定性 SVG node-link 图，五层固定布局，键盘/a11y 支持 |
| Owner-scoped 任务隔离 | ✅ 已落地 | task_id + owner_id 查询/推进，foreign/legacy fail closed |

### 差距

| 差距 | 影响 | 优先级 |
|---|---|---|
| `formal_network_ready=false` | 无科学就绪结论 | 高（核心阻塞） |
| 无真人 reviewer 判定 | 工程能力已上线但 0 条真实判定记录 | 高（并行 HITL） |
| 检索指标为 null | precision@5/MRR@5 未验证 | 高（并行 HITL） |
| Mock 富集非科研级 | 本地字典模拟，非真实 KEGG REST API 或 FDR 校正 | 中 |
| 疾病靶点默认为空 | 默认不导入疾病靶点，intersection 为空 | 中（需双侧 artifact 核验后才有交集） |
| compound child 为 snapshot-only | 不生成机制链/PPI/通路/富集 | 低（设计如此，非差距） |
| 真实组学验证不存在 | 缺真实测量数据验证 | 高（Gate 3 范围） |

### 前置门禁

1. 真人 reviewer 完成逐行 adjudication（当前 3 行 compound targets 全部 pending）
2. Track A 标注完成 150 个 blinded 标签
3. 双侧 raw-artifact 核验完成（disease + compound import）
4. 候选装配计划封存（需全部 lineage latest-wins 终态 + 双侧 verified + 至少一条 included intersection）
5. `formal_network_ready` 翻转须通过科学验证，不是工程 provenance

---

## Step 3：分子对接

### 当前能力

| 能力 | 状态 | 说明 |
|---|---|---|
| Schema 定义 | ✅ 已预留 | `Protein`（PDB ID/UniProt ID/序列）、`Ligand`（SMILES/InChI/分子量）、`DockingResult`（结合亲和力/位点/RMSD） |
| Schema 测试 | ✅ 已覆盖 | 11 个 schema 验证测试 |
| compound_id 关联 | ✅ 已预留 | 与 network 模块的 compound 通过 `compound_id` 关联 |

### 差距

| 差距 | 影响 | 优先级 |
|---|---|---|
| 无 router/service/repository | 无 API 端点、无业务逻辑、无存储 | 高（需独立 ADR 立项） |
| 无对接引擎 | 无 AutoDock/Vina/LeDock 等对接计算能力 | 高 |
| 无蛋白结构准备 | 无 PDB 下载/清理/质子化流水线 | 高 |
| 无配体准备 | 无 SMILES→3D 构象生成/力场参数分配 | 高 |
| 无前端页面 | `/docking` 等页面不存在 | 中 |
| 无独立 validator | 无法复算对接结果一致性 | 中 |

### 前置门禁

1. 独立 ADR 将对接从 schema 预留提升为实际功能
2. 对接引擎选型与许可确认
3. 蛋白结构数据源（PDB）与配体数据源确认
4. 计算资源（CPU/GPU）评估
5. Step 2 的 `formal_network_ready` 至少接近翻转（对接验证的是网络预测的靶点，网络本身未就绪时对接缺乏输入基础）
6. ADR-0018 明确：分子对接/MD 最终是平台内功能还是保持外部工具链 + 报告导入（开放问题 6）

---

## Step 4：分子动力学

### 当前能力

| 能力 | 状态 | 说明 |
|---|---|---|
| Schema 定义 | ✅ 已预留 | `MDSimulationConfig`（温度/压力/时长/力场）、`MDSimulationResult`（轨迹/能量/RMSD/RMSF）、`SimulationTask`（异步任务管理） |
| Schema 测试 | ✅ 已覆盖 | 与 Step 3 共享 11 个 schema 验证测试 |

### 差距

| 差距 | 影响 | 优先级 |
|---|---|---|
| 无 router/service/repository | 无 API 端点、无业务逻辑、无存储 | 高（需独立 ADR 立项） |
| 无 MD 引擎 | 无 GROMACS/AMBER/OpenMM 等模拟能力 | 高 |
| 无轨迹分析 | 无 RMSD/RMSF/氢键/自由能计算 | 高 |
| 无 GPU 计算资源 | MD 模拟需要 GPU 加速 | 高 |
| 无前端页面 | 无 MD 结果展示 | 中 |
| 无异步任务调度 | `SimulationTask` schema 存在但无实际调度 | 高 |

### 前置门禁

1. 独立 ADR 将 MD 从 schema 预留提升为实际功能
2. MD 引擎选型与许可确认
3. 力场选型（AMBER ff14SB/GAFF 等）
4. GPU 计算资源确认
5. Step 3 对接结果已产出（MD 初始构象来自对接结果）
6. 异步任务调度机制（Celery 等）需先通过 ADR 评估引入

---

## 跨步骤差距与依赖

| 依赖路径 | 当前状态 | 阻塞原因 |
|---|---|---|
| Step 1 → Step 2 | 部分可用 | 文献可支撑网络边证据，但古籍挖掘不存在、检索质量未验证 |
| Step 2 → Step 3 | 不可用 | `formal_network_ready=false`，网络靶点未经验证，不宜作为对接输入 |
| Step 3 → Step 4 | 不可用 | Step 3 无实际功能，无法提供对接构象作为 MD 初始构象 |
| Step 4 → Step 2 | 不可用 | Step 4 无实际功能，无法回投验证结果修正证据等级 |

---

## 平台整体能力/差距汇总

### 已具备的工程能力

1. 研究协议门禁与 owner-scoped 任务隔离
2. 双侧 raw-artifact engineering provenance（Open Targets + ChEMBL）
3. 逐行 lineage 与 canonical symbol 交集派生
4. Owner-scoped 人工 adjudication（append-only 审计流）
5. Source-bound 候选装配门禁
6. GO/KEGG 富集分析（mock）
7. 证据分级（确定性纯函数）
8. 独立 validator 零共享复算
9. Markdown 报告导出
10. 网络图可视化（确定性 SVG）
11. 文献/PDF/RAG 证据服务层
12. 分子对接/MD schema 预留

### 尚未具备的关键能力

1. `formal_network_ready=true`（科学就绪）
2. 真人 reviewer 判定记录
3. 检索质量 baseline（precision@5/MRR@5）
4. 真实组学数据验证
5. 分子对接实际功能
6. 分子动力学实际功能
7. 古籍数据挖掘能力
8. 真实 KEGG/STRING REST API 集成
9. 异步任务调度（Celery 等）
10. GPU 计算资源

---

## 结论

Gate 2 基础流程已在现有 AD 平台跑通（mock 模式），证明平台「定协议 → 建网络 → 核证据 → 富集 → 报告」工程链路完整可用。但当前所有输出均为 mock 级别，`formal_network_ready=false`，不构成科学结论。

夏枯草四步路径中：
- **Step 1（古籍挖掘）**：证据服务层有基础检索/RAG 能力，但缺古籍专项
- **Step 2（网络药理学）**：工程能力最完整，缺真人判定与科学验证
- **Step 3（分子对接）**：仅 schema 预留，无实际功能
- **Step 4（分子动力学）**：仅 schema 预留，无实际功能

下一步推进须先完成 Step 2 的科学验证（真人 reviewer sign-off + 检索指标 baseline），再评估 Step 3/4 的独立 ADR 立项。

---

*本矩阵由 TraeWork 根据 ADR-0018 Gate 2 要求编制，2026-08-15。*
