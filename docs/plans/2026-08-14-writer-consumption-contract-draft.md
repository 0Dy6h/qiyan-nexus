# Writer 消费契约设计草案（候选装配计划 → 网络装配 writer）

- date: 2026-08-14
- status: draft（待审草案，未批准，未实施）
- branch: `feat/pillar2-real-evidence-ranking`
- 前置切片：`docs/plans/2026-08-02-source-bound-network-assembly-gate.md`（已实现）与 `docs/handoffs/2026-08-02-source-bound-network-assembly-gate.md`
- 一句话定位：为「未来的网络装配 writer」定义一条写前原子校验 + 一次性消费契约，使候选装配计划在写前仍保持「当前 task/adjudication revision 的 latest plan」成为可证明、可执行、可审计的工程不变量。

---

## 1. 目标与范围

### 1.1 解决什么问题

上一片切（source-bound 网络装配门禁，commit `2a97880`）已把「候选装配计划」封存为不可变记录：计划绑定双侧 artifact hash、冻结 lineage hash、latest-wins 判定快照 hash、父子协议 hash 与确定性 `plan_id`；封存与判定流在同一事务/临界区内原子完成，评估期间的判定追加返回 `conflict`。但该切片**没有定义任何消费方**——计划只是「装配输入已封存」的证据，不是可执行授权。

本契约解决的核心问题是：**未来网络装配 writer 在写任何东西之前，如何原子地证明它消费的候选计划仍是当前 task / adjudication revision 的 latest plan**，从而保证：

- writer 不会基于已被后续判定取代（supersede）的旧计划写出装配产物；
- writer 不会在判定流已变化的情况下基于陈旧快照写出装配产物；
- 「谁在什么 revision 上消费了哪个 plan」成为 append-only、owner-scoped、可审计的记录；
- 旧计划默认不可执行、只可审计的边界从「声明」变成「写前强制校验」。

### 1.2 约束谁

- 约束对象是**未来的网络装配 writer**：任何要依据候选计划生成网络装配产物（边/链/装配运行）的组件，无论它是同进程 service、独立 worker 还是未来 API 端点，都必须走本契约的「写前原子校验 + 一次性消费」原语。
- 约束同时施加在**仓储层**：三种 backend（json / sqlite / postgres）必须提供语义一致的原子消费原语（见 §4）。
- 约束也施加在**结果/报告/前端投影**：消费状态与「已 supersede」的展示沿用「装配输入已封存」式工程措辞，不得写成科研就绪（见 §2、§5）。

### 1.3 不解决什么

- 不定义 writer 的计算逻辑本身（如何从 `selected_intersections` 生成边、链或通路）——那是 writer 实现切片。
- 不授予任何「可执行授权」：即使消费成功，也只是「该计划在该时刻是 latest 且被消费」，不翻转 `formal_network_ready`，不产生科研结论。
- 不引入 PostgreSQL 活库 parity 测试、privileged reviewer-identity audit HMAC、真实领域 reviewer 判定、Track A HITL 标注（见 §6）。
- 不引入队列、图数据库、真实 LLM/embedding 等重依赖；消费原语只用现有仓储层的锁/事务机制。

---

## 2. 核心不变量

以下不变量必须与现有体系逐条一致，writer 消费契约的任何实现都不得违反：

1. **`formal_network_ready` 恒为 false**：候选计划、消费记录、writer 输出信封都不携带也不隐含 `formal_network_ready=true`。现有 plan schema 用 `Literal[False]` 钉死；writer 输出信封必须同样钉死（schema 层 `Literal[False]`），且任何投影/报告不得宣称网络或科研就绪。
2. **候选计划不是可执行授权**：本契约不把 plan 升级为授权凭证。即使 plan 是 latest，writer 每次写前仍要重新证明其绑定成立；「能消费」不等于「科学有效」。
3. **append-only 可审计**：plan 与消费记录都是 append-only 审计流。旧 plan 不删除、不覆盖、不回写；消费记录只追加。读取永不修复或推进状态。
4. **owner-scoped**：task、plan、parent、消费记录的全部解析都以 `task_id + owner_id` 为键；foreign 或 legacy ownerless 一律 fail closed（404），与 `get_owned`/`seal_assembly_plan` 既有语义一致。
5. **不写成 scientific readiness**：UI/报告措辞沿用「装配输入已封存」「计划已消费」的工程表述，从不说「网络/科研就绪」。
6. **校验与写入原子**：writer 在任何写入之前，于同一临界区/事务内完成全部校验；校验失败不产生部分输出、不追加任何记录。
7. **plan 作为 latest-revision 绑定的一次性输入（草案主张，待决定点 D1 确认）**：消费成功后 plan 被标记为已消费，不可再次消费；消费记录与判定流平行，是另一条 append-only 审计流。
8. **消费不修改冻结状态**：消费记录不写回 task 的 `result`/`target_lineage`/provenance/adjudication 字段；冻结 lineage 行与既有判定快照保持只读。
9. **判定流是最权威的 revision 信号**：plan 绑定 latest-wins 判定快照（含每条 lineage row 的 latest event id）；任何判定追加都产生新 revision，使此前封存的 plan 不再可消费（写前校验必须失败关闭）。
10. **免责声明保持 byte-identical**：writer 输出/报告如包含 AI 或装配结论性文字，须携带 `非诊断结论、需结合临床。`，与 `services/rag.py` 的 `DISCLAIMER` 逐字节一致。

---

## 3. writer 写前原子校验的语义

### 3.1 「current revision 的 latest plan」的精确定义

记计划 `P = (plan_id, canonical_plan_input_sha256, plan_sequence, ...)`。对 `(task_id, owner_id)`，`P` 在时刻 t 是「可消费的 latest plan」，当且仅当**在同一个事务/临界区内**以下条件全部成立：

- **R1 task 前置**：task 存在、属于该 owner、`status == "completed"` 且 `result` 非空（与 seal 的授权前置一致）。
- **R2 计划归属与防伪造呈现**：`P` 经 owner-scoped 解析存在；writer 呈现的 `canonical_plan_input_sha256` 与存储的 `P.canonical_plan_input_sha256` 一致（客户端不得自行构造哈希字段）。
- **R3 尚未消费**：消费记录中无 `(task_id, owner_id, plan_id)` 条目（除非允许幂等重放，见决定点 D5）。
- **R4 仍是 latest**：`P.plan_sequence == max(该 task+owner 全部计划的 plan_sequence)`。`plan_sequence` 在封存时由仓储单调分配（JSON 为 `len(task_plans)+1`，SQLite/PG 为 `MAX(plan_sequence)+1`），幂等重封存返回原计划与原序号，因此按 `max(plan_sequence)` 判定 latest 是确定性的。
- **R5 冻结结果绑定未变**：对当前 `record.result.target_lineage` 按 `qiyan_canonical_json_v1` 重算 `canonical_sha256`，等于 `P.target_lineage_sha256`。
- **R6 判定流绑定未变**：对当前 `record.adjudications` 重算 latest-wins 判定快照（每条 lineage row 的 latest event 的 `adjudication_id`/`lineage_row_id`/`decision`/`reason`/`decided_at`，按 row id 排序），`canonical_sha256` 等于 `P.adjudication_selection_sha256`。
- **R7 父子协议绑定仍成立**：当前 child 的 `research_protocol` 重算等于 `P.child_protocol_sha256`；经 `record.source_task_id + owner_id` 解析出的 parent 必须为 root（`source_task_id is None`）、`completed`、其 `research_protocol` 重算等于 `P.parent_protocol_sha256`，且 child 仍指向该 parent（`source_task_id` 在 `NetworkTaskRecord` 模型中不可变、不可自指）。
- **R8 双侧 provenance 绑定仍成立**：当前 `result.target_lineage` 的 disease/compound provenance 的 `source_artifact_sha256` 与 `import_payload_sha256` 分别等于 `P.disease_source_artifact_sha256` / `P.disease_import_payload_sha256` / `P.compound_source_artifact_sha256` / `P.compound_import_payload_sha256`；若 raw artifact 存储存在，可再对字节重算 sha256（与独立 validator 的 `raw_artifact_dir` 路径一致）。
- **R9 计划自洽**：`P.plan_id == "assembly-plan-" + P.canonical_plan_input_sha256`（确定性派生），且 `P.assembly_input_ready is True`、`P.formal_network_ready is False`。

其中：R1/R2 证明「消费的就是这个 task 的这个 plan」；R3 执行「一次性」；R4 证明「latest」；R5–R8 重新证明「plan 的所有绑定在写前仍然成立」；R9 是计划自身自洽性护栏。

**关于 R6 的充分性说明**：`submit_network_target_adjudication` 对不在冻结 lineage 内的 `lineage_row_id` 返回 `unknown_row`，因此判定只能追加到冻结行；任何追加都会改变该行 latest event 的 `adjudication_id`（其派生含随机 `nonce`），从而改变 latest-wins 快照哈希。故 `adjudication_selection_sha256` 能捕获**任何**判定追加。更严格的「事件流不变」校验需要把 seal 时的完整事件 id 元组绑定进 plan（policy v2 扩展，见决定点 D4）；当前 policy v1 下不强制。

### 3.2 必须比对的字段

| 字段 | 角色 | 比对方式 | 失败语义 |
|---|---|---|---|
| `task_id` + `owner_id` | owner-scope | `get_owned(task_id, owner_id)` 解析 | 404 |
| `plan_id` | 消费句柄 | 与存储计划一致，且等于 `"assembly-plan-" + canonical_plan_input_sha256` | 404 / 500 integrity |
| `canonical_plan_input_sha256` | 防伪造呈现 | writer 呈现值 == 存储值 | 409 / 422 |
| `plan_sequence` | latest 判定 | == `max(plan_sequence)`（同 task+owner） | 409 `plan_superseded` |
| `adjudication_selection_sha256` | 判定流绑定 | 当前 latest-wins 快照重算 == 存储值 | 409 `adjudication_changed` |
| `target_lineage_sha256` | 冻结 lineage 绑定 | 当前 `result.target_lineage` 重算 == 存储值 | 500 `lineage_integrity_failed` |
| `child_protocol_sha256` | 协议绑定 | 当前 child 协议重算 == 存储值 | 500 integrity |
| `parent_protocol_sha256` | 父子绑定 | parent 解析 + 重算 == 存储值 | 409 `broken_parent_link` / 500 |
| `disease_source_artifact_sha256` / `disease_import_payload_sha256` | 疾病侧绑定 | 当前 provenance == 存储值（可选：raw 字节重算） | 500 integrity |
| `compound_source_artifact_sha256` / `compound_import_payload_sha256` | 成分侧绑定 | 当前 provenance == 存储值（可选：raw 字节重算） | 500 integrity |
| `assembly_input_ready` / `formal_network_ready` | 状态护栏 | 存储值必须为 `True` / `False` | 500 integrity |
| 消费记录 | 一次性 | 无 `(task_id, owner_id, plan_id)` 条目 | 409 `plan_already_consumed` |

> 说明：比对对象一律是**存储中的计划与当前状态**，绝不信任客户端提交的任何哈希或判定字段；writer 只提交 `plan_id`（以及可选的 `canonical_plan_input_sha256` 作为呈现句柄）。

### 3.3 校验顺序与失败关闭（fail closed）

writer 在全部校验通过之前**不得写入任何东西**，包括不得写入部分装配产物或消费记录。失败时按确定性顺序返回（具体码表待决定点 D3 拍板，以下为草案建议）：

1. `404`：task 未知/外人/legacy ownerless；或该 `(task_id, owner_id, plan_id)` 计划不存在。
2. `409 plan_superseded`：R4 失败（存在更新的计划）。
3. `409 adjudication_changed`：R6 失败（判定流已变，通常已伴随新 plan 封存）。
4. `409 plan_already_consumed`：R3 失败（该 plan 已被消费）。
5. `409 broken_parent_link`：R7 的 parent 部分失败（parent 不可解析 / 非 root / 未完成 / 协议不匹配）。
6. `500`（高严重度 integrity error）：R5 / R7 / R8 / R9 失败——即持久化状态自相矛盾（如当前 lineage 哈希与 plan 绑定不一致且非并发造成）。与既有 gate 的「internally inconsistent persisted hashes → fail closed with a high-severity integrity error」一致，**绝不**呈现为用户可纠正的 readiness，**绝不**由读取修复。
7. `422`：writer 请求本身畸形。

当 R4 与 R6 同时失败（判定追加后重新 seal 出新 plan，旧 plan 同时 superseded 且判定流已变）时，报告哪一个码需要人工拍板（见 D3）；但无论报哪个，writer 都必须失败关闭。

### 3.4 消费记录：一次性输入的执行

- 消费是一个 **append-only 记录**，与 adjudication 审计流平行，不写回 task 的冻结字段，不翻转 `formal_network_ready`。
- 建议新增仓储原语 `consume_assembly_plan(task_id, owner_id, plan_id, output)`，语义：**在同一事务/临界区内完成 R1–R9 + 写入装配输出 + 追加消费记录**；返回 `created` / `existing`（幂等重放命中）/ `conflict`（判定流变化或已消费）/ `superseded` / `not_found`。
- 消费记录最小字段（草案）：`consumption_id`（确定性派生，参照 `adjudication_id` 的 `task_id + lineage/plan + 时间 + sequence + nonce` 模式）、`task_id`、`owner_id`、`plan_id`、`plan_sequence`、`canonical_plan_input_sha256`、`output_id`、`output_sha256`、`writer_id`、`consumed_at`。
- exactly-once 执行：SQLite/PG 用表级唯一约束 `UNIQUE(task_id, owner_id, plan_id)` 兜底；JSON 由同一实例的锁内检查保证（跨实例/跨进程不提供，见 §4）。
- 消费是「审计」不是「推进」：report/UI 读取消费记录属于只读观察，不得借读取推进状态或写 runtime。

### 3.5 writer 输出信封的最小绑定（草案建议）

writer 的装配输出本身应是**新的不可变、append-only artifact**（如 `network-assembly-run-<hash>`），信封至少绑定：

- `output_id`（确定性派生自 plan 绑定 + 输出内容）；
- `task_id`、`source_task_id`、`plan_id`、`plan_sequence`、`canonical_plan_input_sha256`；
- 输出内容哈希（`output_sha256`）与 `consumed_at`；
- `assembly_input_ready: True`、`formal_network_ready: False`（schema 层钉死）；
- 免责声明 `非诊断结论、需结合临床。`（byte-identical）。

可选（后续切片）：独立 validator 扩展复用 `validate_network_assembly_plan.py` 的零共享重算路径，对 writer 输出做独立重算（见决定点 D9）。输出信封不得包含 reviewer identity、服务端私有 audit HMAC 或任何 `formal_network_ready=true` 表达。

---

## 4. 跨 backend 一致性

### 4.1 共同原子原语

三种 backend 必须提供语义等价的原语：**R1–R9 校验 + 写入输出 + 追加消费记录在同一个临界区/数据库事务内完成**。任何实现都不允许「先检查、后写入」之间存在间隙——这是本契约不可妥协的部分（见 4.5）。

### 4.2 json（进程内锁）

- 现状：`NetworkTaskRepository` 持**实例级** `RLock`；正常 API 路径经 `runtime_storage.get_network_task_repository()` 模块级单例共享同一实例，因此同一进程内经该单例的 seal / adjudication / 消费是串行化的。计划存于独立文件 `*.assembly-plans.json`，消费记录建议同样独立文件（如 `*.assembly-consumptions.json`），单文件读改写整体在锁内。
- 边界（必须如实陈述）：(1) **不同实例不共享锁**——同一进程内两个 `NetworkTaskRepository` 实例也互不串行；(2) **跨进程 writer 无法获得该锁**——JSON 不支持跨进程消费原子性；(3) 因此 JSON 只支持「同进程、同实例」的 writer，且不得把 JSON 描述为多 worker 安全。若 writer 以独立 worker 进程运行，必须切到 SQLite/PG。

### 4.3 sqlite（BEGIN IMMEDIATE + event-id）

- 现状：`seal_assembly_plan` 在进程内 path 级 `RLock`（同一 canonical DB path 共享）内执行 `BEGIN IMMEDIATE`，读 task 行的 `adjudications`，比对 `expected_adjudication_ids` 元组，再插入计划并 commit。
- 消费原语沿用同一模式：`BEGIN IMMEDIATE` 获取数据库写锁（跨进程串行化一次一个写事务；path 锁只是单进程优化）→ 读 task 行（adjudications）与最新计划 → 校验 R1–R9 → 插入输出与消费记录（唯一约束兜底）→ commit。
- 硬约束：**输出表与消费记录表必须在同一个 SQLite 文件内**，否则单事务无法覆盖两个表，原子性被打破。

### 4.4 postgres（FOR UPDATE）

- 现状：`seal_assembly_plan` 对 `network_tasks` 行 `SELECT ... FOR UPDATE`（与 `append_adjudication` 同一行锁），事务内比对判定流、插入计划（`INSERT ... ON CONFLICT` / 唯一约束）。
- 消费原语：同一事务内 `SELECT ... FOR UPDATE` 锁住 task 行（与判定追加、seal 互斥）→ 校验 R1–R9 → INSERT 输出与消费记录 → commit；唯一约束 `(task_id, owner_id, plan_id)` 兜底 exactly-once。
- 注意：PG 的 runtime parity 需活库测试后才能声明（见 §6），本契约不承诺、不补测。

### 4.5 可接受差异 vs 不可接受差异

**可接受差异（实现细节不同，语义必须一致）：**

- 锁/事务机制不同：RLock vs `BEGIN IMMEDIATE` vs `FOR UPDATE`——但「校验 + 写入原子」的隔离保证必须等价。
- 错误映射的 HTTP 呈现可略有差异，但语义结果集必须一致：`created` / `existing` / `conflict` / `superseded` / `not_found`。
- `plan_sequence` 的具体生成实现可不同，但必须对 `(task_id, owner_id)` 单调递增且与幂等重封存语义一致（同输入返回原序号）。
- JSON 仅支持同进程同实例 writer——**这是可接受的预览边界**，前提是文档与测试如实标注，不冒充跨进程安全。

**不可接受差异（任何 backend 出现即违约）：**

- 校验与写入不原子（存在 check-then-write 间隙）。
- 允许消费 superseded plan（`plan_sequence` 非 latest 仍通过）。
- 并发判定追加后仍基于旧判定流写入（R6 未重算或重算不原子）。
- exactly-once 被打破：同一 plan 被消费两次且无幂等语义。
- 把 JSON 的跨进程/多实例行为描述为安全，或任何未标注预览边界的实现。

---

## 5. 竞态与边界

- **判定回滚产生新计划**：reviewer 把某行从 `included` 改为 `excluded`（或 include → exclude → include），每次 append 都是新事件；旧 plan 的 `adjudication_selection_sha256` 立即失效，重新 seal 产生新 plan（新 `plan_id`、更高 `plan_sequence`）。持旧 plan 的 writer 在写前校验得到 `adjudication_changed`（或 `plan_superseded`），必须失败关闭、不得写入。
- **并发判定追加**：writer 事务与 `append_adjudication` 竞争。SQLite 靠 `BEGIN IMMEDIATE`、PG 靠 `FOR UPDATE`、JSON 靠同实例 RLock 串行化。writer 要么在判定提交前完成校验并写入（该 plan 在当时是 latest，写入合法且可审计），要么看到新判定而失败。**绝不允许**读到旧判定却按旧 plan 写入。
- **plan 被后续判定 supersede**：若消费已完成（输出已写入），随后新判定使该 plan 不再 latest——输出**保留**，但其绑定的是一个已 supersede 的 plan；报告/投影必须显示该绑定及其 superseded 状态，不得静默呈现为当前（处理口径见决定点 D2）。
- **并发 seal 与 writer**：seal 与 consume 在同一锁/行锁内互斥。若 seal 先提交（新 plan 成为 latest），writer 的 R4 失败；若 writer 先提交（消费了当时 latest 的 plan），随后 seal 产生更高 sequence 的新 plan，已消费的 plan 成为历史。两种次序都合法、都可审计，不产生「陈旧授权」。
- **并发双 writer**：同一 latest plan 被两个 writer 同时消费。串行化后第一个成功并写消费记录；第二个在消费记录检查或唯一约束处失败（`plan_already_consumed`），除非允许按 output 幂等重放（决定点 D5）。
- **reader 读到旧 plan**：`GET /api/network/result/{task_id}/assembly-plans/{plan_id}` 保持 owner-scoped 历史可读（审计），但**可读 ≠ 可消费**；可考虑在只读投影上增加「是否当前 latest / 是否已消费」标记（只读投影，不推进状态、不写 runtime，见决定点 D6）。
- **幂等重放**：同 writer、同 plan、同输出内容（`output_sha256` 相同）的重试应返回已有输出（`existing` 语义）而非报错；不同输出内容的重试必须失败（见决定点 D5）。
- **内部一致性损坏**：持久化哈希自相矛盾（如当前 lineage 哈希与 plan 绑定不一致且非并发造成）→ 高严重度 integrity error；不得当作可纠正的 readiness，不得由读取修复，与既有「读取永不修复」规则一致。
- **写操作与刷新读取分开捕获错误**：消费成功后再读取用于刷新 UI 的接口若失败，不得把已落库的消费报成失败——append-only 审计域里这会诱导重试并污染历史（复用 AGENTS.md 既有规则）。
- **容量边界**：沿用 seal 的护栏（≤10,000 冻结 lineage rows、≤100,000 adjudication events 每 task）；消费记录同样需要上限或保留策略（见决定点 D8）。

---

## 6. 明确排除项

本契约**不包含**以下事项，列明即可，不展开实现：

1. **PostgreSQL 活库 parity**：PG repository 与 schema 已实现（`network_assembly_plans` 表、`FOR UPDATE`），但跨 backend 参数化测试仍只覆盖 json/sqlite；本契约不承诺 PG parity，也不在本契约内补活库测试。PG 的消费语义按 §4.4 描述，但完成度以活库测试为准。
2. **privileged reviewer-identity audit HMAC**：判定快照的服务端私有审计 HMAC 属于独立切片；公共 validator 与 writer 消费路径都不校验 reviewer identity，writer 契约不依赖、不暴露 reviewer identity。
3. **真实领域 reviewer 判定**：当前没有任何真人判定记录；「能记录判定」不等于「已有人判定」，更不等于科学有效；`formal_network_ready` 恒 false。本契约不引入领域 reviewer。
4. **Track A HITL 人工标注**：证据服务层的真实检索人工标注是并行人工事项，与本契约无关。
5. **writer 的计算逻辑**：如何从 `selected_intersections` 生成边/链/通路不在本契约内；本契约只定义写前的消费校验与输出绑定。
6. **重依赖**：不引入队列、图数据库、真实 LLM/embedding；消费原语只用现有仓储层的锁/事务机制。

---

## 7. 待用户批准的决定点

以下口径需要人类拍板，批准前本草案的任何实现都不应启动：

- **D1 一次性消费严格度**：plan 是否 exactly-once（一个 plan 只能被一个 writer 消费一次）？还是允许同一仍为 latest 的 plan 被多个 writer 各自消费（各自在写前验证其为 latest）？本草案默认主张 exactly-once。
- **D2 消费后被 supersede 的输出去留**：writer 输出绑定到一个随后被新判定 supersede 的 plan 时，输出是保留（作为绑定历史的审计产物，标注 superseded）还是必须作废重算？本草案默认主张保留 + 标注。
- **D3 失败码优先级与映射**：409 细分码（`plan_superseded` / `adjudication_changed` / `plan_already_consumed` / `broken_parent_link`）与 500 integrity 的边界；当 R4 与 R6 同时失败时先报哪个码（保证确定性）。
- **D4 判定流绑定强度**：沿用 policy v1 的 `adjudication_selection_sha256`（依赖 latest-wins 快照对任何追加敏感，已有计划不受影响），还是扩展 plan 增加 `adjudication_stream_sha256`（绑定完整事件 id 元组，policy v2，会改变 `plan_id` 派生并使既有计划语义变化）？
- **D5 幂等重放**：是否允许同一 writer + 同一 plan + 同一 `output_sha256` 的重试返回已有输出（`created → existing` 语义）？
- **D6 只读投影**：result 信封/报告是否增加「该 plan 是否当前 latest / 是否已消费」的只读标记（只读投影，不推进状态）？
- **D7 跨 backend 容忍度**：JSON 仅支持「同进程、同实例」writer（预览语义）是否可接受作为本契约的默认交付边界？还是要求消费契约只在 SQLite/PG 上声明安全（JSON 上直接禁止 writer）？
- **D8 消费记录存储与容量**：消费记录表/文件的命名、字段与容量上限（是否沿用 10,000 rows / 100,000 events 护栏或另设）需确认。
- **D9 writer 输出独立复核**：writer 输出是否需要独立的零共享 validator 重算路径（扩展 `validate_network_assembly_plan.py` 的输入包，校验输出信封与消费绑定）作为交付门禁的一部分？

---

## 8. 参考文件

- `docs/handoffs/2026-08-02-source-bound-network-assembly-gate.md`（上一切片交接，§5「仍存边界」、§7「唯一推荐下一步」）
- `docs/plans/2026-08-02-source-bound-network-assembly-gate.md`（上一切片契约，§4 不可变计划契约、§5 API 与持久化）
- `docs/adr/0017-network-pharmacology-first-product-contract.md`（产品契约：只 AD、只 `Homo sapiens`、证据完整性）
- `docs/adr/0015-网络药理学证据分级与指南一致性层.md`（证据分级与护栏）
- `backend/app/services/network.py`（`seal_network_assembly_plan`、`_build_assembly_plan`、`_assembly_gate_blockers`、`submit_network_target_adjudication`）
- `backend/app/api/network.py`（`POST /result/{task_id}/assembly-plans`、`GET /result/{task_id}/assembly-plans/{plan_id}`）
- `backend/app/schemas/network.py`（`NetworkAssemblyPlan`、`NetworkAssemblyPlanSummary`、`NetworkAssemblyGateProjection`）
- `backend/app/repositories/protocols.py`、`network_tasks.py`、`sqlite_network_tasks.py`、`postgres_network_tasks.py`、`postgres_schema.sql`（锁/事务/幂等/owner scope）
- `backend/scripts/validate_network_assembly_plan.py`（独立 validator，零共享代码重算绑定）
