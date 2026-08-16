# ADR-0018 Gate 2：基础流程跑通证据包与交付总结

- 关联 ADR：[ADR-0018](0018-omics-strategy-platform-contract.md)（Accepted）
- 日期：2026-08-15
- 执行方：TraeWork
- 状态：已完成

---

## 交付物清单

| 交付物 | 文件 | 说明 |
|---|---|---|
| 可复算证据包 — 运行 1 结果 | `.tmp/gate2-evidence/run1-result.json` | 完整结果 JSON（含 chains、enrichment、lineage、readiness） |
| 可复算证据包 — 运行 1 报告 | `.tmp/gate2-evidence/run1-report.md` | 5593 字 Markdown 报告 |
| 可复算证据包 — 运行 2 结果 | `.tmp/gate2-evidence/run2-result.json` | 相同输入第二次运行，用于复现验证 |
| 复现验证结论 | 本文件 §复现验证 | chains/enrichment terms/lineage/readiness 全部一致 |
| 能力/差距矩阵 | [0018-gate2-capability-gap-matrix.md](0018-gate2-capability-gap-matrix.md) | 夏枯草四步路径能力/差距/前置门禁矩阵 |

---

## 基础流程执行记录

### 执行环境

- 模式：mock（默认离线，未启用 live provider）
- 后端：FastAPI + uvicorn，127.0.0.1:8000
- 运行时：本地 JSON seed + runtime state
- 日期：2026-08-15

### 研究协议

| 字段 | 值 |
|---|---|
| 疾病 | atopic_dermatitis |
| 表型 | 特应性皮炎伴2型炎症与皮肤屏障异常 |
| 物种 | Homo sapiens |
| 证据策略 | direct_human_first |
| 查询日期 | 2026-08-15 |
| 分析对象 | 消风散（复方） |
| 分析类型 | formula |

### 流程步骤与产出

| 步骤 | 对应 ADR-0018 流程 | 产出 |
|---|---|---|
| 定协议 | 数据层 — 研究协议 | ✅ protocol_complete=true，6 项协议字段全部持久化 |
| 建网络 | 分析层 — 网络构建 | ✅ 5 条 mock 链路：消风散→荆芥/牛蒡子/防风→槲皮素/木犀草素/山奈酚→IL6/STAT3/TNF→PI3K-Akt/NF-κB/JAK-STAT→AD |
| 核证据 | 验证层 — 证据核验 | ✅ 全部 5 条链 evidence_level=mock_inferred；formal_network_ready=false；6 项阻塞原因；候选装配门禁 blocked（7 项 blocker） |
| 富集 | 分析层 — 富集分析 | ✅ 14 个显著富集项（GO + KEGG），p-value 范围 4.2e-11 ~ 1.17e-6，Bonferroni 校正 |
| 报告 | 报告层 — 报告导出 | ✅ 5593 字 Markdown 报告，含协议/lineage/证据分级/富集/阻塞项/免责声明 |

### 靶点集合与 Lineage

| 集合 | 行数 | 说明 |
|---|---|---|
| disease_targets | 0 | 未导入疾病靶点 artifact |
| compound_targets | 3 | IL6（score 0.87）、STAT3（0.79）、TNF（0.82），全部 mock、pending/unreviewed |
| intersection_targets | 0 | 无疾病靶点，禁止自造交集 |

### 人工判定

| 纳入 | 排除 | 待复核 | 待判定 |
|---|---|---|---|
| 0 | 0 | 0 | 3 |

（尚无人工判定记录——「能记录判定」不等于「已有人判定」。）

### 候选装配门禁

- Policy：source_bound_network_assembly_v1
- 状态：**blocked**
- 阻塞项：adjudication_incomplete（3 行）、broken_parent_link、compound_provenance_unverified、disease_provenance_unverified、no_included_intersection、not_compound_child、snapshot_only_boundary_violated

---

## 复现验证

### 方法

使用完全相同的输入（query=消风散, analysis_type=formula, research_protocol 相同），在同一个后端实例上连续运行两次，对比结果。

### 对比结果

| 字段 | 一致性 | 说明 |
|---|---|---|
| chains | ✅ 完全一致 | 5 条链路内容完全相同 |
| enrichment.terms | ✅ 完全一致 | 14 个富集项内容完全相同 |
| enrichment.timestamp | ❌ 不同 | 预期行为：每次运行生成不同时间戳 |
| target_lineage | ✅ 完全一致 | 3 行 compound_targets 完全相同 |
| readiness | ✅ 完全一致 | formal_network_ready=false，6 项阻塞原因相同 |
| task_id | ❌ 不同 | 预期行为：每次运行生成不同 task_id |

### 结论

mock 模式下相同输入产出相同分析结果（chains、enrichment terms、lineage、readiness 全部一致），证明平台可复算性。task_id 与 timestamp 的差异是预期行为，不影响可复算性。

---

## Gate 2 边界遵守

| 边界 | 遵守情况 |
|---|---|
| 不新增甲状腺病种 | ✅ 仍为特应性皮炎 |
| 不实现对接/MD | ✅ 仅 schema 预留，无实际功能 |
| 不接组学数据 | ✅ 无组学数据接入 |
| `formal_network_ready` 保持 false | ✅ false，6 项阻塞原因 |
| 不写代码 | ✅ Gate 2 只运行现有 mock 流程，未修改代码 |
| 不改 README 产品边界 | ✅ 未修改 README |

---

## Gate 2 结论

基础流程已在现有 AD 平台跑通，产出可复算证据包与能力/差距矩阵。平台「定协议 → 建网络 → 核证据 → 富集 → 报告」工程链路完整可用，mock 模式下结果可复现。`formal_network_ready` 保持 `false`，不构成科学结论。

夏枯草四步路径中，Step 2（网络药理学）工程能力最完整但缺科学验证；Step 1（古籍挖掘）有基础检索能力但缺专项；Step 3/4（对接/MD）仅 schema 预留。

---

## 下一步

- **Gate 3**：选定一种组学模态和一个许可/伦理/授权清楚的数据集，定义最小元数据与 manifest 契约。进入时机应与 ADR-0017 主线的真实网络闭环状态一起评估。
- **并行 HITL**：真人 reviewer 完成逐行 adjudication 与 Track A 标注。
- **Step 3/4 独立 ADR**：在 Step 2 科学验证接近完成后，评估分子对接/MD 的立项时机。

---

*本总结由 TraeWork 根据 ADR-0018 Gate 2 要求编制，2026-08-15。*
