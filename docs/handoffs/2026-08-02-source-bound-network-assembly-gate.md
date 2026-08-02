# 交接：source-bound 网络装配门禁（候选装配计划）

date: 2026-08-02
status: 本地实现、独立复审契约修订、独立 validator 与统一门禁全部完成；未 commit、未 push
branch: `feat/pillar2-real-evidence-ranking`

## 1. 本次目标

按 2026-07-26 handoff 指定的唯一下一步，定义、实现并独立验证 source-bound 网络装配 gate。硬约束：该 gate 只证明「装配输入已封存」，不生成网络结论，不授权任何 writer，不翻转 `formal_network_ready`。

## 2. 契约（已独立复审修订）

`docs/plans/2026-08-02-source-bound-network-assembly-gate.md` 在实现前经独立审查修订，消除了三个高风险点：

1. **签发原子性**：计划封存与 child adjudication 流在 repository 锁/事务内绑定（SQLite `BEGIN IMMEDIATE` + event-id 序列比较，PostgreSQL `FOR UPDATE`，JSON 进程内锁），评估期间的判定追加会返回 `conflict`，绝不落陈旧授权。
2. **父子绑定完整**：parent/child 研究协议必须逐字段字节等价并分别绑定 hash；child 必须指向该 parent。
3. **产物降格**：产出是「不可变候选装配计划」，不是可执行授权；旧计划 append-only 可审计但默认不可执行，未来 writer 消费契约是独立切片。

## 3. 交付

- `POST /api/network/result/{task_id}/assembly-plans`：gate 评估 + 原子封存；首次 `201`，同输入幂等 `200`，被阻塞 `409`（结构化 blockers），未知/外人 task `404`。
- `GET /api/network/result/{task_id}/assembly-plans/{plan_id}`：owner-scoped 历史计划。
- result 信封新增 `assembly_gate` projection（state/blockers/latest_plan summary），报告新增「候选装配输入门禁」段，`/network` 前端新增封存面板；三者都只说「装配输入已封存」，从不说「网络/科研就绪」。
- 计划绑定：policy/canonicalization id、child+parent task id、双协议 hash、双侧 source artifact + import payload hash、冻结 lineage hash、latest-wins 判定快照 hash（含 latest event id，判定回滚也产生新计划）、冻结+selected 双侧 refs、确定性 `plan_id = assembly-plan-<input hash>`、`plan_sequence`、`created_at`。
- 独立 validator `backend/scripts/validate_network_assembly_plan.py`：与 producer 零共享代码，重算全部绑定、重新派生 selected intersections、raw artifact 存在时重算字节 hash；公共包不含 reviewer identity。

## 4. 验证

- 后端全量 `863 passed, 1 skipped`；ruff format/check、mypy 全通过。
- 新 API 测试：阻塞判定不完整 `409`、needs_review 阻塞、零 included 交集阻塞、双侧 backing 缺失阻塞、首次 `201`/幂等 `200`、判定回滚产生新计划且旧计划不变、`formal_network_ready` 恒 false、owner/reviewer 不泄漏、报告含门禁段。
- repository 参数化（json/sqlite）：幂等 + owner scope + 陈旧判定流 `conflict`。
- 独立 validator：对 live API 产出的真实计划通过；对每一种篡改（plan_id、input/lineage/adjudication hash、selected refs、协议、snapshot-only 违规、判定缺失/needs_review、raw artifact 字节）全部拒绝。
- 前端 `281 passed`、typecheck/build 通过；E2E `4 passed`。
- `git diff --check` 无 whitespace error。

## 5. 仍存边界（有意延后，不是本次缺陷）

- **writer 消费契约未定义**：未来网络装配 writer 必须在写前原子证明 plan 仍是当前 task/adjudication revision 的 latest plan；旧计划默认不可执行。
- **PostgreSQL 未做活库 parity**：repository 与 schema 已实现，但跨 backend 参数化测试仍只覆盖 json/sqlite；不得宣称 PG parity。
- **privileged audit HMAC 未实现**：reviewer identity 进入判定快照的服务端审计 HMAC 属于下一切片；公共 validator 不校验 reviewer identity。
- JSON backend 仍是单进程 preview 语义（与 adjudication 相同既有边界）。
- 判定能力与装配门禁均无真实领域 reviewer 记录；`formal_network_ready` 恒 false。

## 6. 关键文件

- `docs/plans/2026-08-02-source-bound-network-assembly-gate.md`（契约）
- `backend/app/schemas/network.py`、`backend/app/services/network.py`、`backend/app/api/network.py`
- `backend/app/repositories/{protocols,network_tasks,sqlite_network_tasks,postgres_network_tasks}.py`、`postgres_schema.sql`
- `backend/scripts/validate_network_assembly_plan.py`（独立 validator）
- `backend/tests/test_validate_network_assembly_plan.py`、`test_network_adjudication_api.py`、`test_network_task_repository_backends.py`
- `frontend/lib/api/network.ts`、`frontend/components/NetworkAnalysisClient.tsx`、`frontend/tests/network-adjudication-ui.test.ts`

## 7. 唯一推荐下一步

定义并批准未来 writer 消费契约（plan 作为 latest-revision 绑定的一次性输入），并在活库上补齐 PostgreSQL parity；在此之前不得把候选计划当作可执行授权，也不得写成 scientific readiness。真实领域 reviewer 判定与 Track A HITL 仍为并行人工事项。
