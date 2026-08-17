# ADR-0018 开放问题 5/6/7 决议简报

- 关联 ADR：[ADR-0018](0018-omics-strategy-platform-contract.md)（Accepted，Gate 1 已确认）
- 关联契约：[ADR-0017](0017-network-pharmacology-first-product-contract.md)（Accepted，继续有效）
- 日期：2026-08-16
- 执行方：TraeWork
- 状态：供研究者拍板（只调研与建议，不做决策，不改任何 ADR 状态）

---

## 背景

ADR-0018 在「风险与开放问题」中列出 7 个开放问题，其中 Q1-Q4 已在 Gate 1/3 中回答。本文档针对剩余的 Q5、Q6、Q7 逐条给出【背景事实】【选项】【推荐及理由】【风险/成本】，供研究者拍板。

参考文件：
- [ADR-0017](0017-network-pharmacology-first-product-contract.md) — 产品契约基线
- [ADR-0018](0018-omics-strategy-platform-contract.md) — 组学策略方向
- [Gate 2 能力/差距矩阵](0018-gate2-capability-gap-matrix.md) — 夏枯草四步路径能力映射
- [Gate 3 评估](0018-gate3-evaluation.md) — 组学数据验证层评估
- `docs/current-state.md` — 当前事实源

---

## Q5：北极星案例的古籍数据挖掘是否成为证据服务层的专项能力，还是仅作方法学参照？

### 背景事实

1. 北极星案例是研究者本人的夏枯草干预甲状腺疾病整合研究，路径为「古籍数据挖掘 → 网络药理学 → 分子对接 → 分子动力学」。
2. Gate 2 能力矩阵显示：Step 1（古籍挖掘）当前无古籍专项数据源、无结构化标注能力；但文献检索、PDF 上传/解析、RAG 证据问答、引用导出等证据服务层基础能力已具备。
3. ADR-0017 强制要求证据服务层「必须逐步绑定到研究项目、靶点、通路、网络边或科研 claim」。
4. ADR-0018 对北极星案例设定边界：「研究本身不改动」「平台先按现有样子跑通基础流程」「四步路径只作能力蓝图」。
5. ADR-0018 明确：「不因方向升级提前引入重依赖」「不因组学平台方向立即引入工作流引擎、云计算组学平台、GPU 重计算」。

### 选项

| 选项 | 含义 | 工程投入 |
|---|---|---|
| A. 成为证据服务层专项能力 | 在平台内开发古籍数据挖掘能力：结构化古籍文本数据库、方药-证候-治法关联抽取、古籍 NLP 管线 | 高（需新建数据源、NLP 管线、存储 schema） |
| B. 仅作方法学参照 | 古籍挖掘作为研究方法论参考，不在平台内实现；研究者在平台外完成古籍挖掘后，通过 PDF 上传/RAG 引用导入结果 | 无（复用现有证据服务层） |

### 推荐项：B. 仅作方法学参照

**理由**：

1. **古籍数据挖掘是独立领域**：需要结构化古籍文本数据库、古文 NLP/实体识别、方药-证候-治法关联抽取等专项能力，与当前网络药理学系统层主线无直接工程关系。
2. **当前无基础设施**：Gate 2 矩阵明确标注「无古籍专项数据源」「古籍文本无结构化标注」，从零建设成本高、周期长。
3. **ADR-0018 边界明确**：「四步路径只作能力蓝图」，古籍挖掘映射为平台当前能力/差距矩阵中的「差距」，不是「待实现功能」。
4. **现有证据服务层已可承载古籍内容**：研究者可通过 PDF 上传（`POST /api/uploads/pdf`）将古籍文献导入平台，RAG 引用（`/api/rag/answer`）可检索和引用古籍内容。古籍文献作为文献来源之一被证据服务层绑定到网络研究对象，不需要专项能力。
5. **不提前引入重依赖**：古籍 NLP 管线需要额外模型、数据集和计算资源，违反 ADR-0018「不提前重依赖」纪律。
6. **如未来需要，可通过独立 ADR 立项**：与分子对接/MD 同样的门禁——独立 ADR + 许可/授权/伦理确认 + 工程优先级评估。

### 风险/成本

| 风险 | 缓解 |
|---|---|
| 研究者需在平台外手动完成古籍挖掘，工作流断裂 | 通过 PDF 上传 + RAG 引用无缝导入古籍文献内容；标注为「外部来源」 |
| 古籍挖掘结果缺乏结构化 provenance | 通过 PDF 上传 metadata（文件名、上传时间、parse 状态）提供基础 provenance；如需更结构化的 provenance，走 raw-artifact 门禁 |
| 北极星案例的古籍挖掘步骤在平台内无对应能力 | Gate 2 矩阵已如实标注为「差距」，不冒充已有能力 |

---

## Q6：分子对接/分子动力学最终是平台内功能，还是保持外部工具链 + 报告导入的边界？

### 背景事实

1. Gate 2 能力矩阵显示：
   - Step 3（分子对接）：仅 schema 预留（`Protein`、`Ligand`、`DockingResult`），无 router/service/repository，无对接引擎（AutoDock/Vina/LeDock），无蛋白/配体准备管线。
   - Step 4（分子动力学）：仅 schema 预留（`MDSimulationConfig`、`MDSimulationResult`、`SimulationTask`），无 MD 引擎（GROMACS/AMBER/OpenMM），无 GPU 计算资源，无异步任务调度。
2. ADR-0018 明确：「不提前引入重依赖——不因组学平台方向立即引入工作流引擎、云计算组学平台、GPU 重计算、图数据库或生产级多组学存储」。
3. 前置门禁：Step 2 的 `formal_network_ready` 至少接近翻转，对接才有输入基础（对接验证的是网络预测的靶点）。当前 `formal_network_ready=false`。
4. ADR-0018 修订边界：「把分子对接/MD 从 schema 预留提升为实际功能」必须通过新的 ADR 或对 0017 的显式修订。
5. 现有 raw-artifact provenance 纪律已支持外部数据导入（Open Targets 疾病侧、ChEMBL 成分侧），可扩展到对接/MD 结果报告。

### 选项

| 选项 | 含义 | 工程投入 | 依赖 |
|---|---|---|---|
| A. 平台内功能 | 在平台内集成对接/MD 引擎、计算资源、异步调度、结果展示 | 极高（引擎、GPU、Celery、存储） | formal_network_ready 接近翻转 + 独立 ADR |
| B. 外部工具链 + 报告导入 | 研究者在平台外完成对接/MD，导入结果报告；平台只做结果展示、证据绑定和可复算审计 | 低（扩展 raw-artifact 门禁） | 无新重依赖 |
| C. 当前阶段 B，远期重新评估 A | 短期走 B，待网络验证完成且计算资源就绪后通过独立 ADR 评估 A | 分阶段 | B 不阻塞 A |

### 推荐项：C. 当前阶段 B（外部工具链 + 报告导入），远期重新评估 A

**理由**：

1. **当前 `formal_network_ready=false`，对接缺乏输入基础**：对接验证的是网络预测的靶点，网络本身未经验证时对接无意义。Gate 2 矩阵明确标注 Step 2 → Step 3「不可用」，阻塞原因就是 `formal_network_ready=false`。
2. **重依赖明确排除**：对接引擎（AutoDock/Vina）、MD 引擎（GROMACS/AMBER）、GPU 计算资源、异步任务调度（Celery）都是 ADR-0018 明确排除的重依赖，当前阶段不可引入。
3. **外部工具链 + 报告导入与现有纪律一致**：研究者已在平台外完成夏枯草四步路径的对接/MD（北极星案例「四步完整跑通、可复算」），结果可作为外部 artifact 通过 raw-artifact provenance 门禁导入，与 Open Targets / ChEMBL 的导入模式对称。
4. **平台内的核心价值是证据绑定和可复算审计**：不是计算引擎本身。研究者在外部完成计算后，平台负责绑定结果到网络边、展示证据分级、提供独立 validator 复算。
5. **远期可重新评估**：如果网络验证完成（`formal_network_ready` 翻转）、计算资源就绪、对接/MD 需求明确，可通过独立 ADR 将对接/MD 提升为平台内功能。这与 ADR-0018「每个新模态都必须单独立项」一致。
6. **schema 预留不浪费**：当前 `Protein`/`Ligand`/`DockingResult`/`MDSimulationConfig`/`MDSimulationResult` schema 已覆盖，未来无论走 A 还是 B，schema 都可复用。

### 风险/成本

| 风险 | 缓解 |
|---|---|
| 外部工具链的版本/参数/结果格式不一致，影响可复算性 | 导入时走 raw-artifact 门禁：SHA-256 哈希 + operator manifest + 不可变快照 + 服务端 parser provenance，与 ChEMBL 导入纪律统一 |
| 导入报告需要新的 parser | 后续切片定义对接/MD 结果的最小 manifest 契约（参照 Gate 3 组学 manifest 模式），不提前实现 |
| 研究者需在多个工具间切换 | 工作流断裂是可接受代价——平台聚焦证据管理和可复算审计，不替代专业计算工具 |
| 远期升級 A 的时机不确定 | 明确触发条件：`formal_network_ready` 翻转 + 计算资源就绪 + 研究者明确需求 → 启动独立 ADR |

---

## Q7：真实 reviewer 判定与 Track A 标注由谁完成、何时完成，如何与本方向 Gate 排序？

### 背景事实

1. ADR-0018 诚实承认：
   - 尚无任何真人 reviewer 判定记录（「能记录判定」不等于「已有人判定」）。
   - `precision@5` / `MRR@5` 仍为 `null`，150 个 Track A 人工标签尚未填写。
   - `formal_network_ready` 仍为 `false`。
2. Gate 2 矩阵的前置门禁明确列出：
   - 真人 reviewer 完成逐行 adjudication（当前 3 行 compound targets 全部 pending）。
   - Track A 标注完成 150 个 blinded 标签。
3. Track A 标注材料已就绪：`.tmp/retrieval-validation-v1/worksheet.json`（30 题 × top-5 = 150 个候选）和 `worksheet.manifest.json` 已于 2026-07-11 生成，状态为 0/30 题完成人工标签。
4. ADR-0017 要求「真实检索 Track A 标注仍有价值，但属于证据服务层质量验证，不再占用唯一工程主线；应由独立真人 reviewer 以 HITL 方式继续」。
5. Track A guide 明确：「可信主体是未参与 ranker 调参的临床/科研 reviewer」——标注者不能看过 retrieval rank/score，不能在查看结果后修改问题。

### 选项

| 选项 | Track A 标注 | 逐行 Adjudication | Gate 排序 |
|---|---|---|---|
| A. 研究者本人完成全部 | 研究者完成 Track A + adjudication | 研究者本人 | 并行，无先后 |
| B. 研究者找领域 reviewer 完成全部 | 领域 reviewer 完成 Track A + adjudication | 领域 reviewer | 并行，无先后 |
| C. 分阶段完成 | 研究者先完成 Track A，领域 reviewer 后完成 adjudication | 分阶段 | Track A 先行，adjudication 后行 |

### 推荐项：C. 分阶段完成

**理由**：

1. **Track A 和 adjudication 是两个不同的验证维度**：
   - **Track A**：验证检索质量（`precision@5` / `MRR@5`），回答「默认 keyword 检索是否把真人判断为相关的文献排进 top-5」。标注者需未参与 ranker 调参。
   - **Adjudication**：验证网络边的生物学正确性，回答「这条 lineage row 的靶点-疾病/成分-靶点边是否应 included」。判定者需有领域知识。
2. **研究者本人适合 Track A，不一定适合 adjudication**：
   - 如果研究者未参与 ranker 调参（ranker 是 deterministic keyword 方案，无调参），研究者本人可作为 Track A 标注者。预计耗时约 30 分钟（150 个布尔标签）。
   - Adjudication 需要领域 reviewer 确认靶点-疾病边的生物学合理性，研究者本人可能有确认偏差（自己构建的网络自己判定）。
3. **分阶段可与 Gate 排序**：
   - **当前阶段**：研究者立即完成 Track A 标注（材料已就绪，只需填写 150 个布尔标签）。完成后获得检索质量 baseline（`precision@5` / `MRR@5`）。
   - **下一步**：邀请领域 reviewer（临床/科研）完成逐行 adjudication。当前只有 3 行 compound targets 需判定，工作量小。如双侧 artifact 核验后 disease targets 也需判定，行数会增加。
   - **之后**：双侧 artifact 核验 → 候选装配封存 → `formal_network_ready` 评估。
4. **Track A 不阻塞 adjudication**：Track A 是证据服务层质量验证（ADR-0017 明确），adjudication 是网络药理学验证层。两者可并行，但 Track A 材料已就绪可立即启动，adjudication 需要领域 reviewer 时间。
5. **Track A guide 的盲标纪律**：标注者在标注完成前不得查看 `worksheet.manifest.json`（含真实排名）；标注完成后揭盲评分。

### Gate 排序建议

```
当前阶段（立即可启动）：
  ├── Track A 标注（研究者本人，~30 分钟，材料已就绪）
  └── 揭盲评分（运行 eval_blind_labeling.py score）

下一阶段（需领域 reviewer）：
  ├── 逐行 adjudication（领域 reviewer，当前 3 行 compound targets）
  └── 双侧 raw-artifact 核验（disease + compound import verify）

之后：
  ├── 候选装配计划封存（需全部 lineage latest-wins 终态 + 双侧 verified + ≥1 条 included intersection）
  └── formal_network_ready 评估（科学验证，不是工程 provenance）
```

Track A 和 adjudication 都不是 ADR-0018 的 Gate 4/5，而是 Gate 2 前置门禁中并列的 HITL 事项。Gate 2/3 已完成工程侧能力验证，HITL 事项是 `formal_network_ready` 翻转的前置条件。

### 风险/成本

| 风险 | 缓解 |
|---|---|
| 研究者本人参与 Track A 标注可能引入偏差 | ranker 是 deterministic keyword 方案，无调参；研究者标注的是文献相关性，不是 ranker 参数；Track A guide 的盲标纪律（不看 rank/score）进一步降低偏差 |
| 领域 reviewer 难以找到或时间不确定 | 当前 adjudication 工作量极小（3 行 compound targets），可快速完成；如需扩大，提前规划 reviewer 时间 |
| 两阶段完成拉长 `formal_network_ready` 翻转周期 | Track A 可立即启动（~30 分钟），不阻塞主线；adjudication 可与双侧 artifact 核验并行 |
| 研究者既是网络构建者又是 Track A 标注者 | Track A 标注的是文献检索相关性，不是网络边判定，与网络构建无直接利益冲突；adjudication 由领域 reviewer 独立完成，避免自评 |

---

## 汇总表

| 开放问题 | 推荐项 | 核心理由 |
|---|---|---|
| Q5 古籍数据挖掘定位 | B. 仅作方法学参照 | 古籍挖掘是独立领域，当前无基础设施；现有证据服务层可通过 PDF/RAG 承载古籍内容 |
| Q6 分子对接/MD 边界 | C. 当前 B（外部 + 报告导入），远期重新评估 A | `formal_network_ready=false`，对接无输入基础；重依赖明确排除；外部导入与 raw-artifact 纪律一致 |
| Q7 reviewer 判定与 Track A | C. 分阶段完成 | Track A 立即可启动（材料已就绪），adjudication 需领域 reviewer；两者是不同验证维度，不互相阻塞 |

---

## 研究者拍板清单

- [x] Q5: 确认古籍数据挖掘仅作方法学参照，不成为证据服务层专项能力
- [x] Q6: 确认当前阶段走外部工具链 + 报告导入，远期通过独立 ADR 重新评估平台内功能
- [x] Q7: 确认分阶段完成——研究者先完成 Track A 标注，领域 reviewer 后完成 adjudication
- [x] Q7 附加: 确认研究者本人作为 Track A 标注者（未参与 ranker 调参）
- [x] Q7 附加: 确认 Gate 排序如上（Track A 立即启动，adjudication 与 artifact 核验并行）

---

## 研究者确认记录

- **确认人**：研究者（蒜香）
- **确认时间**：2026-08-16
- **确认方式**：对话内逐条审批，全部接受推荐项 + 对抗性审查补充条件

### 对抗性审查补充条件（研究者确认一并纳入）

以下条件由 TraeWork 在对抗性审查中提出，研究者确认一并纳入：

**Q5 补充（2 项）**：
1. RAG 对古汉语支持有限（当前按字符切分，异体字/通假字/无标点断句支持差）；古籍内容建议先人工转译为现代汉语再录入平台，原始古籍 PDF 仅作溯源附件。
2. ADR-0018 中明确标注：北极星案例的「古籍→网络药理学」环节是人工前置工作，平台从「网络药理学」环节开始参与；「古籍挖掘」在 Gate 2 矩阵中保持「差距」标注。

**Q6 补充（3 项）**：
3. 对接/MD 结果导入时必须遵循与双侧 raw-artifact 相同的 provenance 纪律（SHA-256 哈希 + operator-controlled manifest + server-side parsing + 不可变快照）。
4. 导入时必须记录外部工具版本、计算参数、输入文件哈希，确保结果可追溯和可复算。
5. 「远期重新评估」的触发条件明确定义为：`formal_network_ready` 翻转 + 计算资源就绪 + 研究者明确需求 → 启动独立 ADR。

**Q7-a 补充（2 项）**：
6. 当前是单一标注者，结果可能存在个人偏差；如未来扩大标注规模（100+ 题），应引入第二个标注者计算 inter-rater agreement。
7. 标注是一次性的；标注完成后可调参，但调参后应另出题集，不重新标注同一 worksheet（避免知情偏差）。

**Q7-b 补充（2 项）**：
8. 如研究者自我判定，adjudication 独立性有限，应在结果中如实标注；如邀请外部专家，平台已支持 owner-scoped adjudication + access token 管理。
9. 当前 3 行 compound targets 可管理；如靶点规模显著增长（50+），需考虑批量判定工具或分级判定流程。

**Q7-c 补充（1 项）**：
10. 排序确定：**Track A 先做**（首要目标是先验证检索质量基础，避免 adjudication 返工）。研究者已确认此排序。

### 确认后状态

- 简报状态：`供研究者拍板` → `已确认`
- Q5/Q6/Q7 开放问题：可关闭
- 下一步行动：
  1. 研究者完成 Track A 标注（~30-45 分钟，材料已就绪）
  2. 揭盲评分，获得 precision@5 / MRR@5 baseline
  3. 根据检索质量决定是否调参
  4. 领域 reviewer 完成逐行 adjudication
  5. 双侧 raw-artifact 核验
  6. 候选装配计划封存
  7. formal_network_ready 评估

---

*本简报由 TraeWork 编制，2026-08-16。研究者确认记录由 TraeWork 代为记录，研究者本人在对话中逐条确认。只调研与建议、不做决策、不改任何 ADR 状态、不写实现代码。*
