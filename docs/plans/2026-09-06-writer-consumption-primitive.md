# Writer 消费原语实现切片计划（候选装配计划 → 一次性消费契约）

- date: 2026-09-06
- status: implemented（实现切片；契约与决策依据见下）
- 契约草案：`docs/plans/2026-08-14-writer-consumption-contract-draft.md`
- 决策包：`docs/plans/2026-08-14-writer-consumption-contract-decision-pack.md`（2026-08-16 研究者逐条拍板 D1-D9 全部接受推荐项 + 附加条件）
- 边界：不实现 writer 的装配计算逻辑（独立切片）；不翻转 `formal_network_ready`；不做 PostgreSQL 活库 parity 测试；不扩展独立 validator（D9=B，仅预留输出信封 schema）

## 1. 切片范围

按已批准决策包落地 `consume_assembly_plan` 消费原语：writer 在写任何装配产物前，于同一临界区内原子完成 R1-R9 校验 + 输出写入 + 消费记录追加。旧计划默认不可执行从「声明」变成「写前强制校验」。

## 2. 拍板决策 → 实现映射

| 决策 | 拍板 | 实现 |
|---|---|---|
| D1 | exactly-once | `UNIQUE(task_id, owner_id, plan_id)`（SQLite/PG 表约束；JSON 锁内检查）+ 消费记录 append-only |
| D2 | 输出保留 + 标注 superseded | 输出不删除；`is_superseded_by` 只读投影（audit view + gate summary），UI 只默认展示 latest |
| D3 | 失败码优先级 R3→R4→R6→R7→500 | 见 §4 失败码表；500 integrity 记录全部失败检查项 |
| D4 | policy v1（latest-wins 快照） | 消费时重算 `adjudication_selection_sha256` 与 plan 绑定比对；不改 plan schema |
| D5 | 幂等重放 | 同 `writer_id + plan_id + output_sha256` → `existing` 返回原消费记录；否则 `plan_already_consumed` |
| D6 | 只读投影 | plan audit view（`is_latest_plan`/`is_consumed`/`is_superseded_by`）+ result 信封 `latest_plan.is_consumed` + 报告消费状态行 |
| D7 | JSON 预览边界可接受 + 5a/5b/5c | 响应信封 `backend_fidelity: "preview"/"production"`；JSON 输出/消费文件记录进程 token，检出异进程写入 fail closed（`json_backend_multi_process_blocked`）；文档明示 JSON 不保证跨进程 exactly-once |
| D8 | 独立文件/表 ≤1,000/task | JSON `*.assembly-outputs.json` + `*.assembly-consumptions.json`；SQLite/PG `network_assembly_outputs` + `network_assembly_consumptions`；上限 env `QIYAN_CONSUMPTION_RECORD_LIMIT`（默认 1000）→ 429 |
| D9 | validator 后续切片 | 本切片只定义输出信封最小 schema（`output_id`/`output_sha256`/消费绑定字段），validator 预留接口 |

附加条件落实：D1-附加（输出写失败 → 消费记录回滚：SQLite/PG 同事务，JSON 同锁内先写输出、失败回滚重写旧内容）；D3-附加（文档注明「plan 被 supersede 的当前唯一原因是判定变化」）；D5-附加（文档注明幂等重放前提是 writer 输出确定性）。

## 3. 校验编排（服务层 + 仓储层分工）

服务层（锁外预检，均 fail closed）：

- R1 owner/completed：`get_owned` 失败 → 404；plan 不存在 → 404
- R2 防伪造呈现：`canonical_plan_input_sha256` 呈现值 ≠ 存储值 → 422
- R9 计划自洽：`plan_id` 派生 / `assembly_input_ready` / `formal_network_ready` 违反 → 500 integrity
- R5+R8 预检：当前 lineage 重算 hash ≠ plan 绑定 → 500 integrity（provenance 位于 lineage 内，被 R5 覆盖）
- R7 父子绑定：parent 不可解析/非 root/未完成 → 409 `broken_parent_link`；协议 hash 不符 → 500 integrity
- R6 预检：当前 latest-wins 快照重算 ≠ `adjudication_selection_sha256` → 409 `adjudication_changed`

仓储层（同一临界区内重校验 + 写入，防「读→锁」间隙）：

- task 行存在且 owner 匹配（R1 间隙防护）
- 消费记录查重（R3：replay → `existing`；他者 → `already_consumed`）
- `plan_sequence == max`（R4）→ `superseded`
- 判定流元组与服务层读取一致（R6 间隙防护）→ `conflict`
- 当前 lineage 重算 hash == plan 绑定（R5 锁内重算，de-jure 防 result 变更通道）→ `integrity_failed`
- 容量上限（D8）→ `capacity_exceeded`
- JSON 专属：输出/消费文件进程 token 校验（D7-5b）→ `multi_process_blocked`
- 全部通过 → INSERT 输出 + 消费记录 → commit；任何失败不产生部分写入

## 4. 失败码表（HTTP 映射）

| 顺序 | 仓储/服务状态 | HTTP | detail.code |
|---|---|---|---|
| 1 | `not_found` | 404 | （detail 字符串） |
| 2 | `invalid_request` | 422 | `invalid_consume_request`（含 checks） |
| 3 | `already_consumed` | 409 | `plan_already_consumed` |
| 4 | `superseded` | 409 | `plan_superseded` |
| 5 | `conflict` | 409 | `adjudication_changed` |
| 6 | `broken_parent_link` | 409 | `broken_parent_link` |
| 7 | `integrity_failed` | 500 | `assembly_integrity_failed`（含 checks） |
| 8 | `capacity_exceeded` | 429 | `consumption_limit_reached` |
| 9 | `multi_process_blocked` | 409 | `json_backend_multi_process_blocked` |
| 成功 | `created` / `existing` | 201 / 200 | — |

## 5. 数据契约

- `NetworkAssemblyConsumeRequest`：`writer_id`（1-64）、`canonical_plan_input_sha256?`（呈现句柄）、`output_payload`（不透明 JSON 对象，服务端 canonical 化算 `output_sha256`；序列化 ≤ 256KB → 422）。`extra="forbid"`。
- `NetworkAssemblyOutput`（不可变输出信封）：`output_id = "assembly-output-" + sha256(plan 绑定 + output_sha256)`（确定性派生）、task/plan 绑定全字段、`consumed_at`、`assembly_input_ready: Literal[True]`、`formal_network_ready: Literal[False]`、`disclaimer`（byte-identical `非诊断结论、需结合临床。`）。
- `NetworkAssemblyConsumptionRecord`：`consumption_id`（含时间 + nonce，参照 adjudication_id 模式）、task/plan/output 绑定、`writer_id`、`consumed_at`；`owner_id` 持久化但 API 投影丢弃。
- 消费是审计不是推进：不写回 task 冻结字段，读取永不修复或推进状态。

## 6. 测试口径

- 仓储层参数化 json/sqlite：created/existing/already_consumed/superseded/conflict/integrity/not_found/capacity/JSON token + 双 writer 并发（线程）+ 变异验证（去掉锁内重校验后测试必须变红）
- API 层 TestClient 全失败码 + 幂等重放 + 判定追加→adjudication_changed / 重封存→plan_superseded + 文件篡改→500/broken_parent_link + sqlite backend_fidelity=production
- 跨端字段：result 信封 `latest_plan.is_consumed` 后端断言 + 前端类型/UI 断言两侧各一
