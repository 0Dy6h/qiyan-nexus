# 当前状态

updated_at: 2026-08-03T00:20:00+08:00
artifact_consistency_pass: true（限方向纠偏、Gate 1、Gate 2 双侧 raw-artifact provenance、lineage、snapshot-only 输出契约、owner-scoped 人工 adjudication 审计流与 source-bound 网络装配门禁）
scientific_readiness_network_pharmacology: false
scientific_readiness_literature_retrieval: false
scientific_readiness_rag_synthesis: false

## 已确认事实

- ADR-0017 已接受：网络药理学是唯一产品主轴，文献/PDF/RAG 为证据服务层；默认 network execution 仍为 mock。
- Gate 1 已完成最小研究协议、owner-scoped task、read-only report GET 与 `formal_network_ready` 失败关闭。
- Gate 2 双侧工程 provenance 已完成：疾病侧静态解析 Open Targets GraphQL artifact，成分侧静态解析离线 `chembl_known_activity_v1` known-activities JSON；二者均由服务端计算 raw-byte SHA-256、匹配 operator-controlled trusted manifest，并保存 canonical payload hash。
- compound import 只能从同 owner 的 `server_verified_raw_artifact` disease parent 创建 immutable child；`source_task_id` 跨 JSON/SQLite/PostgreSQL、result 与 report 保真，self-link、child-of-child 与 foreign parent 均失败关闭。
- compound child 是 snapshot-only：只输出冻结 disease/compound lineage 与服务端派生交集，不调用 provider，不生成机制链、PPI、通路或 enrichment；legacy unlinked child 在 result/report 读取时返回非持久化失败投影。
- disease/compound source rows 保留 source-record 观察单元；同一 canonical symbol 的不同来源记录不折叠。intersection 每个 unique symbol 一条 derivation row，并完整引用双侧所有匹配 row IDs。
- 自动 source row 与 intersection row 均保持 `pending/unreviewed`；artifact consistency 不等于人工 adjudication、科学有效性或临床价值。
- 独立 validator 可复算协议、计数、row IDs、双侧 refs、阈值、canonical payload hash、raw-byte hash、parent-link 形状和 snapshot-only 输出；它不重演 Open Targets/ChEMBL parser，也不能在没有 parent artifact 时证明 parent 存在或 owner 归属。
- 受保护模式 HTTP 回归已直接证明 reviewer B 使用 reviewer A 的 `source_task_id` 时返回通用 `404`，且不会新增 child task 或写入 compound artifact。
- owner-scoped 逐行人工 adjudication 已完成（2026-07-26）：`POST /api/network/result/{task_id}/adjudications` append-only 追加判定，`GET /api/network/tasks` 提供 owner-scoped 任务列表。判定 projection 挂在结果响应信封而非冻结快照上，同一 row latest wins，`reviewer_id` 持久化但从不回投；未知/外人/legacy ownerless task `404`，非 completed `409`，未知 lineage row 或伪造派生字段 `422`。活体回归与 8 路并发回归均已确认 readiness 不翻转、冻结 row 保持 `pending/unreviewed`、无丢失 append。
- 人工判定与冻结 lineage row 上的 `adjudication_status` / `decision` 是**两套并行语义**：本切片的判定是独立审计流，不回写 lineage row，后者仍恒为 `pending` / `unreviewed`。若未来要统一需单独 ADR。
- source-bound 网络装配门禁已完成（2026-08-02，契约见 `docs/plans/2026-08-02-source-bound-network-assembly-gate.md`，交接见 `docs/handoffs/2026-08-02-source-bound-network-assembly-gate.md`）：`POST /api/network/result/{task_id}/assembly-plans` 在 child 三类 lineage 全部 latest-wins 终态判定、双侧来源 `server_verified_raw_artifact`、父子协议字节等价、snapshot-only 边界与至少一条带双侧 included backing 的交集后，原子封存不可变候选计划（首次 `201`，同输入幂等 `200`，阻塞 `409` 结构化 blockers，未知/外人 task `404`）；任何判定事件追加都会产生新计划，旧计划 append-only 可审计但默认不可执行。计划签发与 child adjudication 流在 repository 锁/事务内绑定（SQLite `BEGIN IMMEDIATE` + event-id 序列比较，PostgreSQL `FOR UPDATE`，JSON 单进程），评估期间的判定追加返回 `conflict` 绝不落陈旧授权。
- 独立 validator `backend/scripts/validate_network_assembly_plan.py` 与 producer 零共享代码：重算双协议 hash、lineage hash、latest-wins 判定快照 hash、canonical plan input hash、确定性 plan id 与 selected intersections，raw artifact 存在时重算字节 hash；公共证据包不含 reviewer identity。突变测试证明对每一种篡改（plan_id、各类 hash、selected refs、协议、snapshot-only 违规、判定缺失/needs_review、raw 字节）全部拒绝。
- result 信封、报告与 `/network` 前端只展示 `assembly_input_ready` 与结构化 blockers；`formal_network_ready` 恒 false；冻结 lineage row 的 `adjudication_status` / `decision` 恒为 `pending` / `unreviewed`。
- **`-IncludeE2E` 红线已修复（2026-08-02）**：根因是项目目录迁移后遗留的 `.next` 绝对路径缓存，而非 adjudication 或 gate 行为回归；清理缓存后冷/热两轮均为 Playwright `4 passed`，并已移除 4 个 spec 对脆弱 `waitForLoadState("networkidle")` 的依赖（改 goto load + expect auto-wait）。
- 最终门禁（2026-08-02）：backend 全量 `863 passed, 1 skipped`，ruff format/check、mypy 全通过；frontend `281 passed`，typecheck/build 通过；`./scripts/verify-local.ps1 -IncludeE2E` 通过；`git diff --check` 无 whitespace error；`2a97880` 与 `a6e15fa` 已 push 到 `feat/pillar2-real-evidence-ranking`。
- 项目目录迁移会使 pnpm 绝对 symlink 全部悬空，前端门禁全红且与代码无关；迁移后必须 `rm -rf frontend/node_modules && pnpm install --frozen-lockfile`，并同时清理 `frontend/.next`（同样含迁移前绝对路径，会导致 dev/E2E 间歇性失败如 Playwright `networkidle` 超时）。判断失败是否既有时，复跑必须处于干净工具链（已重装依赖、已清缓存），否则会把缓存问题误判为"既有红线"。
- `pnpm audit --prod` 本轮未形成漏洞结论：npm quick 与 fallback audit endpoint 均返回 HTTP 410 retired。该结果是 tooling compatibility blocker，不是“0 vulnerabilities”。

## 阻塞项

- 没有真实领域 reviewer 完成 Track A 的 150 个 blinded 标签，真实检索质量仍未知。
- 双侧 raw hash 与 trusted manifest 不证明 artifact 来自官方渠道、release/query/mapping 选择正确、靶点具有生物学意义或临床价值。
- 人工判定已可记录，但**没有任何真实领域 reviewer 实际判定过任何一行**；判定能力落地不等于判定已发生，更不等于科学有效。
- **未来 writer 消费契约未定义**：网络装配 writer 必须在写前原子证明 plan 仍是当前 task/adjudication revision 的 latest plan；旧候选计划默认不可执行。当前不能导出机制链、PPI、通路或 enrichment 科研结论。
- **PostgreSQL 未做活库 parity**：`network_assembly_plans` 表与 repository 已实现，但跨 backend 参数化测试仍只覆盖 json/sqlite；不得宣称 PG parity。
- **privileged audit HMAC 未实现**：reviewer identity 进入判定快照的服务端审计 HMAC 属于下一切片；公共 validator 不校验 reviewer identity。
- JSON/SQLite 的单进程锁不提供多 worker exactly-once；若扩展多进程，必须先设计数据库 claim/lease 或等价原子协议。SQLite 的 `advance()` / `append_adjudication()` / `seal_assembly_plan()` 已用 CAS + 重试缓解丢更新，JSON backend 全部写方法仍无跨进程守卫。
- adjudications 数组无长度上限，重试循环可无界增长，且每次 append 重写整条记录。

## 当前检查点

Gate 1、Gate 2 双侧 artifact/lineage 工程闭环、owner-scoped 人工 adjudication 审计流与 source-bound 网络装配门禁（候选装配计划 + 独立 validator）均已完成并 push，但科学就绪度仍为 false —— 判定**能力**存在，判定**事实**为零；候选计划是受控装配输入而非授权，readiness 仍硬编码 false。下一步定义并批准未来 writer 消费契约并在活库补齐 PostgreSQL parity；在此之前不得把 artifact consistency、人工判定或候选计划写成 scientific readiness。
