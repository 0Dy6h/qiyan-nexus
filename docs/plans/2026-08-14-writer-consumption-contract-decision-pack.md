# Writer 消费契约决策包：D1-D9 决定点逐条分析

- date: 2026-08-16
- status: decision-pack（供研究者拍板，未批准未实施）
- 关联草案：`docs/plans/2026-08-14-writer-consumption-contract-draft.md`（status: draft）
- 执行方：TraeWork
- 边界：不写实现代码、不代签任何确认、不翻转 `formal_network_ready`、消费记录不得写成科研就绪

---

## 阅读说明

本文档对草案 §7 的 D1-D9 逐条给出【选项】【工程权衡】【推荐项及理由】【风险】。研究者逐条拍板后，草案方可进入实现切片。每条推荐均标注与既有核心不变量（草案 §2）的对齐关系。

---

## D1：一次性消费严格度

### 问题

plan 是否 exactly-once（一个 plan 只能被一个 writer 消费一次）？还是允许同一仍为 latest 的 plan 被多个 writer 各自消费（各自在写前验证其为 latest）？

### 选项

| 选项 | 语义 | 消费记录 |
|---|---|---|
| A. exactly-once | 一个 plan 只能被消费一次；第二次消费报 `plan_already_consumed` | `(task_id, owner_id, plan_id)` 唯一 |
| B. 多 writer 各自消费 | 同一 latest plan 可被多个 writer 各自消费，每个 writer 产生独立输出 | `(task_id, owner_id, plan_id, writer_id)` 唯一 |

### 工程权衡

- **A 的优势**：审计流保持一对一（一个 plan → 一条消费记录），与 adjudication 审计流的 latest-wins 模式一致；`UNIQUE(task_id, owner_id, plan_id)` 约束天然兜底 exactly-once；不需要引入 `writer_id` 概念。
- **A 的劣势**：如果需要同一 plan 产生多种输出（如不同布局的网络图），必须重新 seal 新 plan。
- **B 的优势**：允许多 writer 对同一 plan 产生不同视角输出。
- **B 的劣势**：消费记录一对多，审计复杂度上升；需要引入 `writer_id` 作为第四唯一键；不同 writer 的输出之间可能产生不一致，需要额外仲裁机制。

### 推荐项：A. exactly-once

**理由**：
1. 审计流保持简单（一个 plan 一条消费记录），与 append-only 审计纪律一致。
2. 与 adjudication 审计流的 latest-wins 模式对称：判定流一次追加产生一个 latest event，消费一次追加产生一条消费记录。
3. 如需多种输出，可通过重新 seal 新 plan（新 `plan_sequence`）实现，不会破坏审计链。
4. D5 的幂等重放机制可解决 writer 崩溃后的安全重试需求，不需要多 writer 消费。
5. 引入 `writer_id` 会增加 owner-scoped 查询的复杂度，且当前无多 writer 场景。

### 风险

- 若未来确实需要同一 plan 产出多种输出（如同时生成网络图和通路报告），需要重新 seal plan 或引入 D1-B 方案。当前无此需求，不提前设计。
- exactly-once 依赖消费原语在锁/事务内完成「检查 + 写入」，JSON backend 的跨进程边界需在 D7 中如实标注。

---

## D2：消费后被 supersede 的输出去留

### 问题

writer 输出绑定到一个随后被新判定 supersede 的 plan 时，输出是保留（作为绑定历史的审计产物，标注 superseded）还是必须作废重算？

### 选项

| 选项 | 语义 | 审计影响 |
|---|---|---|
| A. 保留 + 标注 superseded | 输出保留为 append-only 审计产物，在只读投影上标注 `is_superseded_by` | 审计完整 |
| B. 作废重算 | 输出标记为 voided，必须基于新 plan 重新消费产出 | 审计有删除/作废操作 |

### 工程权衡

- **A 的优势**：与核心不变量 #3（append-only 可审计）完全一致；消费记录和输出都不删除、不覆盖、不回写；历史可追溯。
- **A 的劣势**：UI/报告需要显示 superseded 状态；可能存在多个版本的输出，用户需要理解版本关系。
- **B 的优势**：只有最新输出可见，UI 简单。
- **B 的劣势**：违反 append-only 原则（需要标记作废）；丢失审计历史；如果 supersede 后的 plan 也被消费又 supersede，需要递归作废；与「读取永不修复或推进状态」规则冲突。

### 推荐项：A. 保留 + 标注 superseded

**理由**：
1. 与核心不变量 #3（append-only 可审计）完全一致——旧 plan 不删除、不覆盖、不回写，消费记录和输出同理。
2. superseded 标记是只读投影（核心不变量 #5），不推进状态、不写 runtime。
3. 作废会引入状态修改操作，违反「读取永不修复或推进状态」规则。
4. 审计场景中，「writer 在某个 revision 上消费了哪个 plan」是不可篡改的历史事实，即使该 plan 后续被 supersede。
5. 与 D6 的只读投影配合：报告/UI 可显示「该输出绑定的 plan 是否当前 latest / 是否已 superseded」。

### 风险

- UI 需要处理多版本输出的展示逻辑，可能增加前端复杂度。
- 用户可能误解 superseded 输出为「错误输出」，需要在 UI 文案中明确区分「审计历史」与「当前状态」。

---

## D3：失败码优先级与映射

### 问题

409 细分码（`plan_superseded` / `adjudication_changed` / `plan_already_consumed` / `broken_parent_link`）与 500 integrity 的边界；当 R4（plan 非 latest）与 R6（判定流已变）同时失败时先报哪个码（保证确定性）。

### 选项

| 选项 | R4+R6 同时失败时优先报 | 确定性保证 |
|---|---|---|
| A. 先报 `plan_superseded`（R4） | writer 知道「有更新计划」，可操作性地重新获取 latest plan | 固定顺序：R3 → R4 → R6 → R7 |
| B. 先报 `adjudication_changed`（R6） | writer 知道「判定流已变」，需重新 seal | 固定顺序：R3 → R6 → R4 → R7 |

### 工程权衡

- **A 的优势**：`plan_superseded` 更具可操作性——writer 的下一步是「获取最新 plan」，不需要理解判定流细节；`adjudication_changed` 通常伴随新 plan seal，是 `plan_superseded` 的原因之一，可作为附加信息。
- **B 的优势**：`adjudication_changed` 更精确地描述了根因。
- **B 的劣势**：writer 需要理解判定流才能决定下一步操作，增加耦合。

### 推荐项：A. 先报 `plan_superseded`（R4）

**理由**：
1. writer 的主要关注点是「我的 plan 是否还是最新的」，`plan_superseded` 直接回答这个问题。
2. `adjudication_changed` 是 `plan_superseded` 的常见原因（判定追加 → 新 plan seal → 旧 plan superseded），先报更外层的 `plan_superseded` 让 writer 快速重定向到最新 plan。
3. writer 不需要理解判定流细节，降低 writer 与判定流的耦合。
4. 响应体中可附加 `hint` 字段说明根因（如 `"hint": "adjudication_changed_before_seal"`），但不改变主码。

### 完整失败码优先级建议

```
1. 404                      — task/plan 不存在或 foreign/legacy ownerless
2. 422                      — writer 请求本身畸形（字段缺失/类型错误）
3. 409 plan_already_consumed — R3 失败（先检查消费记录，快速失败）
4. 409 plan_superseded      — R4 失败（plan 非 latest）
5. 409 adjudication_changed — R6 失败（判定流已变）
6. 409 broken_parent_link   — R7 的 parent 部分失败
7. 500 integrity error      — R5/R7/R8/R9 失败（持久化状态自相矛盾）
```

注意：R3（已消费）排在 R4（非 latest）之前，因为消费记录检查成本低，且已消费的 plan 不需要继续校验 latest。

### 风险

- 固定优先级可能在极端情况下掩盖根因（如 R4 和 R6 同时失败但实际原因是 R8 provenance 损坏）。建议在 500 integrity error 日志中记录所有失败的校验项，不只报第一个。
- 409 与 500 的边界需要严格测试覆盖，特别是 R5（lineage 哈希不一致）是 500 还是 409 取决于是否由并发造成——并发造成的应报 409，非并发造成的应报 500。当前草案建议 R5 一律报 500（高严重度），因为 lineage 哈希不一致不可能由正常并发造成（seal 时已绑定）。

---

## D4：判定流绑定强度

### 问题

沿用 policy v1 的 `adjudication_selection_sha256`（依赖 latest-wins 快照对任何追加敏感，已有计划不受影响），还是扩展 plan 增加 `adjudication_stream_sha256`（绑定完整事件 id 元组，policy v2，会改变 `plan_id` 派生并使既有计划语义变化）？

### 选项

| 选项 | 绑定方式 | 对既有计划的影响 |
|---|---|---|
| A. policy v1（latest-wins 快照） | `adjudication_selection_sha256` = latest-wins 快照哈希 | 无影响（已有实现） |
| B. policy v2（完整事件流） | `adjudication_stream_sha256` = 完整事件 id 元组哈希 | 改变 `plan_id` 派生，既有计划语义变化 |

### 工程权衡

- **A 的优势**：已有实现，不引入 breaking change；`adjudication_selection_sha256` 对任何判定追加已敏感（草案 §3.1 R6 充分性说明已证明：`adjudication_id` 含随机 `nonce`，任何追加都改变 latest event id，从而改变快照哈希）。
- **A 的劣势**：理论上存在两个不同判定序列产生相同 latest-wins 快照的可能（同一行 include → exclude → include，最终状态相同但事件序列不同）。但 `adjudication_id` 含 nonce 使此概率可忽略。
- **B 的优势**：更严格的绑定，捕获完整事件序列。
- **B 的劣势**：改变 `plan_id` 派生公式，使既有已封存计划语义变化；需要存储完整事件 id 元组；增加 seal 和消费校验的计算复杂度。

### 推荐项：A. policy v1（latest-wins 快照）

**理由**：
1. 已有实现，不引入 breaking change，既有已封存计划语义不变。
2. 草案 §3.1 R6 充分性说明已证明：`submit_network_target_adjudication` 对不在冻结 lineage 内的 row 返回 `unknown_row`，判定只能追加到冻结行；`adjudication_id` 含随机 nonce，任何追加都改变 latest event id，从而改变快照哈希。因此 `adjudication_selection_sha256` 能捕获任何判定追加。
3. policy v2 的额外严格性在当前场景下收益极低——nonce 已使碰撞概率可忽略。
4. 如需升级到 policy v2，可在后续 ADR 中处理，不需要在本契约中提前设计。
5. 与核心不变量 #9（判定流是最权威的 revision 信号）一致：任何判定追加都使此前封存的 plan 不再可消费。

### 风险

- 极低概率的快照碰撞（nonce 碰撞）在理论上存在，但在 SHA-256 + 随机 nonce 的组合下实际不可能发生。
- 如果未来需要审计完整判定事件序列（而非仅 latest-wins 快照），需要扩展 plan 绑定。但当前 append-only 审计流已保存完整事件，消费校验只需知道「是否变化」而非「变化了什么」。

---

## D5：幂等重放

### 问题

是否允许同一 writer + 同一 plan + 同一 `output_sha256` 的重试返回已有输出（`created → existing` 语义）？

### 选项

| 选项 | 语义 | 重试行为 |
|---|---|---|
| A. 允许幂等重放 | 同 writer + plan + output_sha256 → 返回已有输出（`existing`） | writer 崩溃后可安全重试 |
| B. 不允许 | 任何重试报 `plan_already_consumed` | writer 崩溃后无法重试 |

### 工程权衡

- **A 的优势**：writer 崩溃后可安全重试（at-least-once delivery + idempotent consumer = effectively-once）；网络分区后重试不会产生重复输出；符合分布式系统最佳实践。
- **A 的劣势**：消费原语需要在写入前查找匹配的 `output_sha256`（在消费记录中按 `plan_id + output_sha256` 查找）；略微增加消费原语复杂度。
- **B 的优势**：实现简单，不需要查找逻辑。
- **B 的劣势**：writer 崩溃后无法安全重试；如果 writer 在写入消费记录后、返回响应前崩溃，调用方不知道是否成功，重试会被拒绝。

### 推荐项：A. 允许幂等重放

**理由**：
1. writer 崩溃恢复是常见场景（进程崩溃、网络中断、容器重启），不支持幂等重试会导致 writer 卡死。
2. `output_sha256` 匹配保证重试不会产生不同输出——同一 writer 用同一 plan 重新计算应产生确定性输出（如果非确定性，`output_sha256` 不匹配，重试会被正确拒绝）。
3. 与 D1 的 exactly-once 配合：exactly-once + 幂等重放 = effectively-once，是分布式系统的标准模式。
4. 消费记录中查找 `(plan_id, output_sha256)` 的成本可控（单 task 消费记录数量受 D8 容量上限限制）。
5. `existing` 语义与 seal 的幂等重封存语义对称（同输入返回原计划与原序号）。

### 风险

- 如果 writer 的计算是非确定性的（如含时间戳或随机数），`output_sha256` 每次不同，幂等重放永远不会命中。这实际上是正确行为——非确定性输出不应重试。
- 查找逻辑需要在锁/事务内执行，不能在锁外查找后再加锁（check-then-write 间隙）。

---

## D6：只读投影

### 问题

result 信封/报告是否增加「该 plan 是否当前 latest / 是否已消费」的只读标记（只读投影，不推进状态）？

### 选项

| 选项 | 语义 | 实现成本 |
|---|---|---|
| A. 增加只读标记 | 响应信封增加 `is_latest_plan` / `is_consumed` / `is_superseded_by` 字段 | 低（读取时计算） |
| B. 不增加 | 用户需额外查询才能知道 plan 状态 | 无 |

### 工程权衡

- **A 的优势**：UI/报告可直观显示 plan 当前状态；审计时可快速判断；只读投影不推进状态，符合核心不变量 #5。
- **A 的劣势**：需要在读取时实时计算 `is_latest`（查询该 task+owner 的 `max(plan_sequence)`）和 `is_consumed`（查询消费记录）。
- **B 的优势**：API 简单，不需要额外查询。
- **B 的劣势**：用户需要额外调用 `GET assembly-plans` 列表才能知道 plan 是否 latest，体验差。

### 推荐项：A. 增加只读标记

**理由**：
1. 只读投影不推进状态、不写 runtime，与核心不变量 #5（不写成 scientific readiness）和「读取永不修复或推进状态」规则一致。
2. 提升审计和 UI 可用性——用户打开一个 plan 详情时可直接看到其当前状态。
3. 实现成本低：`is_latest_plan` = 当前 plan 的 `plan_sequence` == `max(plan_sequence)`；`is_consumed` = 消费记录中存在该 plan 的条目；`is_superseded_by` = 如果 `is_latest_plan` 为 false，指向更高 sequence 的 plan_id。
4. 与 D2 的 superseded 标注配合：用户可同时看到「该输出绑定的 plan 是否已 superseded」和「该 plan 是否已消费」。

### 风险

- 实时计算 `is_latest` 需要额外查询（`max(plan_sequence)`），在高频读取场景下可能影响性能。可考虑缓存或延迟计算（标记为 `unknown` 而非强制计算）。
- 字段命名需与既有 `NetworkAssemblyPlanSummary` schema 对齐，避免引入命名冲突。

---

## D7：跨 backend 容忍度

### 问题

JSON 仅支持「同进程、同实例」writer（预览语义）是否可接受作为本契约的默认交付边界？还是要求消费契约只在 SQLite/PG 上声明安全（JSON 上直接禁止 writer）？

### 选项

| 选项 | JSON writer | 边界标注 |
|---|---|---|
| A. 可接受（JSON 支持同进程同实例 writer） | 允许，但标注预览边界 | 文档和测试如实标注 |
| B. 不可接受（JSON 禁止 writer） | 禁止，返回错误 | 只 SQLite/PG 声明安全 |

### 工程权衡

- **A 的优势**：当前预览阶段默认 backend 是 JSON，允许 JSON writer 可让开发者在本地快速验证消费流程；不需要强制切 SQLite 才能测试 writer。
- **A 的前提**：必须如实标注预览边界——JSON 仅支持「同进程、同实例」writer，不冒充跨进程安全；writer 以独立进程运行时必须切到 SQLite/PG。
- **B 的优势**：强制使用 SQLite/PG，消费原子性更有保障。
- **B 的劣势**：当前默认 backend 是 JSON，禁止 JSON writer 会阻碍本地开发和测试；开发者需要先配置 SQLite 才能测试 writer，增加摩擦。

### 推荐项：A. 可接受（JSON 支持同进程同实例 writer，标注预览边界）

**理由**：
1. 当前预览阶段默认 backend 是 JSON（`QIYAN_STATE_BACKEND` 默认未设或 json），允许 JSON writer 可让开发者在本地快速验证消费流程。
2. 草案 §4.2 已如实陈述 JSON 的边界：(1) 不同实例不共享锁；(2) 跨进程 writer 无法获得该锁；(3) JSON 只支持「同进程、同实例」writer。只要文档和测试如实标注，不冒充跨进程安全，这是可接受的预览边界。
3. 与核心不变量 #6（校验与写入原子）一致——JSON 在同实例 RLock 内完成「校验 + 写入」是原子的，只是锁的范围限定在同一进程同一实例。
4. 与既有 seal 的边界一致——`seal_assembly_plan` 在 JSON backend 上也是同实例 RLock，不提供跨进程保证。
5. writer 以独立 worker 进程运行时，必须切到 SQLite/PG，这一约束在文档和启动检查中强制。

### 风险

- 开发者可能误以为 JSON 支持跨进程 writer。缓解：在 `consume_assembly_plan` 实现中，JSON backend 检测到非同实例调用时返回明确错误（如 `json_backend_does_not_support_cross_process_writer`）。
- 如果未来需要多 worker 并发 writer，JSON 必须被替换为 SQLite/PG，这不是降级而是预期演进。

---

## D8：消费记录存储与容量

### 问题

消费记录表/文件的命名、字段与容量上限（是否沿用 10,000 rows / 100,000 events 护栏或另设）需确认。

### 选项

| 选项 | 命名 | 容量上限 |
|---|---|---|
| A. 独立文件/表，沿用 seal 护栏比例 | JSON: `*.assembly-consumptions.json`；SQLite/PG: `network_assembly_consumptions` | ≤1,000 消费记录 per task |
| B. 独立文件/表，无上限 | 同上 | 无上限 |

### 工程权衡

- **A 的优势**：有容量护栏，避免无限制增长；消费记录数量天然受 plan 数量限制（exactly-once 下每个 plan 最多 1 条消费记录），而 plan 数量受 seal 护栏限制（≤10,000 lineage rows 隐含 plan 数量上限）。
- **A 的劣势**：需要实现容量检查逻辑。
- **B 的优势**：实现简单。
- **B 的劣势**：无上限可能导致存储膨胀（虽然 exactly-once 下不太可能）。

### 推荐项：A. 独立文件/表，设容量上限

**理由**：
1. 消费记录是 append-only 审计流，天然不会无限增长（exactly-once 下每个 plan 最多 1 条消费记录 + 幂等重放不产生新记录）。
2. 但设置上限是防御性措施，与 seal 的护栏纪律一致。
3. 容量上限建议 ≤1,000 消费记录 per task：每个 plan 最多 1 条消费记录（D1 exactly-once），幂等重放不产生新记录（D5），因此 1,000 条已远超实际需求（plan 数量受 ≤10,000 lineage rows 限制，但不是每个 lineage row 都会产生新 plan）。
4. 命名建议：
   - JSON: `*.assembly-consumptions.json`（与 `*.assembly-plans.json` 对称）
   - SQLite: 表 `network_assembly_consumptions`（与 `network_assembly_plans` 对称）
   - PostgreSQL: 同 SQLite 表名
5. 字段沿用草案 §3.4 定义的最小字段集：`consumption_id`, `task_id`, `owner_id`, `plan_id`, `plan_sequence`, `canonical_plan_input_sha256`, `output_id`, `output_sha256`, `writer_id`, `consumed_at`。
6. 唯一约束：`UNIQUE(task_id, owner_id, plan_id)` 兜底 exactly-once（D1）。

### 风险

- 容量上限触发时的行为需要定义：建议返回 `429 consumption_limit_reached`，不允许继续消费，需要人工清理或归档。
- 归档策略（如将旧消费记录移到冷存储）不在本契约范围内，留后续运维切片。

---

## D9：writer 输出独立复核

### 问题

writer 输出是否需要独立的零共享 validator 重算路径（扩展 `validate_network_assembly_plan.py` 的输入包，校验输出信封与消费绑定）作为交付门禁的一部分？

### 选项

| 选项 | 时机 | 实现成本 |
|---|---|---|
| A. 当前切片实现 | 扩展 validator，覆盖输出信封 | 高（需要定义输出 schema + 校验规则） |
| B. 后续切片实现 | 当前只定义输出信封 schema，预留 validator 接口 | 低 |

### 工程权衡

- **A 的优势**：零共享重算路径保证输出一致性，与现有 `validate_network_assembly_plan.py` 的独立 validator 纪律一致。
- **A 的劣势**：增加当前切片复杂度；需要定义输出 schema 和校验规则；writer 输出格式尚未稳定，过早实现 validator 可能需要频繁调整。
- **B 的优势**：减少当前切片复杂度，聚焦消费契约核心；为后续 validator 扩展预留接口。
- **B 的劣势**：缺少独立验证，writer 输出一致性只能依赖消费原语自身的校验。

### 推荐项：B. 后续切片实现（当前预留接口）

**理由**：
1. 当前切片的核心价值是「写前原子校验 + 一次性消费契约」，不是 writer 输出的独立验证。validator 应在 writer 输出格式稳定后再实现。
2. 消费原语自身的 R1-R9 校验已覆盖 plan 绑定的完整性（lineage 哈希、判定流哈希、provenance 哈希、父子协议哈希），writer 输出只需绑定这些已校验的哈希。
3. 但当前切片应定义输出信封的最小 schema（草案 §3.5 已给出草案建议），为后续 validator 扩展留接口。
4. 后续切片实现时，扩展 `validate_network_assembly_plan.py` 的输入包，增加对输出信封 `output_id`、`output_sha256`、消费绑定（`plan_id`、`plan_sequence`、`canonical_plan_input_sha256`）的零共享重算。
5. 与核心不变量 #2（候选计划不是可执行授权）一致——即使有独立 validator，也不翻转 `formal_network_ready`。

### 风险

- 在 validator 实现前，writer 输出的一致性只能依赖消费原语自身的校验和测试覆盖。如果消费原语有 bug，writer 输出可能不一致但无法被独立发现。
- 缓解：当前切片的测试必须覆盖消费原语的全部分支（R1-R9 通过/失败、幂等重放、并发竞争），并在后续切片中尽快实现 validator。

---

## 汇总表

| 决定点 | 推荐项 | 与核心不变量对齐 |
|---|---|---|
| D1 一次性消费严格度 | A. exactly-once | #3 append-only, #4 owner-scoped |
| D2 消费后被 supersede 的输出去留 | A. 保留 + 标注 superseded | #3 append-only, #5 不写成 readiness |
| D3 失败码优先级与映射 | A. 先报 `plan_superseded`（R4） | #6 校验与写入原子 |
| D4 判定流绑定强度 | A. policy v1（latest-wins 快照） | #9 判定流是最权威 revision 信号 |
| D5 幂等重放 | A. 允许（同 writer + plan + output_sha256） | #6 校验与写入原子 |
| D6 只读投影 | A. 增加只读标记 | #5 不写成 readiness |
| D7 跨 backend 容忍度 | A. JSON 可接受（标注预览边界） | #6 校验与写入原子 |
| D8 消费记录存储与容量 | A. 独立文件/表，≤1,000 per task | #3 append-only |
| D9 writer 输出独立复核 | B. 后续切片实现（当前预留接口） | #2 候选计划不是可执行授权 |

---

## 研究者拍板清单

研究者逐条确认以下推荐项后，草案可进入实现切片：

- [x] D1: 确认 exactly-once
- [x] D2: 确认保留 + 标注 superseded
- [x] D3: 确认先报 `plan_superseded`，完整失败码优先级如上
- [x] D4: 确认 policy v1（latest-wins 快照），不升级到 policy v2
- [x] D5: 确认允许幂等重放（同 writer + plan + output_sha256 → existing）
- [x] D6: 确认增加只读标记（is_latest_plan / is_consumed / is_superseded_by）
- [x] D7: 确认 JSON 可接受为预览边界，需如实标注
- [x] D8: 确认独立文件/表命名与 ≤1,000 per task 容量上限
- [x] D9: 确认后续切片实现独立 validator，当前只预留接口

---

## 研究者确认记录

- **确认人**：研究者（蒜香）
- **确认时间**：2026-08-16
- **确认方式**：对话内逐条审批，全部接受推荐项 + 附加条件

### 附加条件（实现切片必须遵守）

以下条件由 TraeWork 在评审中提出，研究者确认一并纳入契约约束：

1. **D1 附加**：产物写入失败时消费记录必须回滚（同一事务内，不允许出现「计划已标记消费但产物丢失」的死锁状态）。
2. **D2 附加**：UI 默认只展示 latest 产物，superseded 产物仅在审计追溯视图可见。
3. **D3 附加**：契约文档中注明「plan 被 supersede 的当前唯一原因是 adjudication 变化」这一假设；如未来引入其他 supersede 原因，需重新评估失败码优先级。
4. **D5 附加**：契约文档中注明幂等重放的前提是 writer 输出确定性；如未来引入非确定性 writer（如 LLM 生成），output_sha256 匹配会失败，需重新设计。
5. **D7 附加（三项约束）**：
   - 5a. 响应中信封标注 `backend_fidelity: "preview"`（JSON）或 `"production"`（SQLite/PG）。
   - 5b. JSON 模式下检测到多进程访问时 fail closed（返回明确错误，不静默继续）。
   - 5c. 文档明确：JSON 模式不保证多进程 exactly-once。
6. **D8 附加**：容量上限通过环境变量配置（如 `QIYAN_CONSUMPTION_RECORD_LIMIT`），默认 1000，不硬编码。
7. **D9 附加**：契约中定义 writer 输出信封的最小 schema（`output_id`, `output_sha256`, 消费绑定字段），为后续 validator 扩展留明确目标。

### 确认后状态

- 决策包状态：`decision-pack` → `approved`
- 关联草案状态：`draft` → 待实现切片启动时转为 `approved`
- 下一步：启动 writer 消费原语 TDD 实现切片

---

*本决策包由 TraeWork 编制，2026-08-16。研究者确认记录由 TraeWork 代为记录，研究者本人在对话中逐条确认。不改契约草案本身，不翻转 `formal_network_ready`。*
