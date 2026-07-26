# 当前状态

updated_at: 2026-07-26T20:30:00+08:00
artifact_consistency_pass: true（限方向纠偏、Gate 1、Gate 2 双侧 raw-artifact provenance、lineage、snapshot-only 输出契约与 owner-scoped 人工 adjudication 审计流）
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
- 最终门禁（2026-07-26）：backend 全量 `851 passed, 1 skipped`，ruff/mypy 全通过；frontend `278 passed`，typecheck/build 通过；`./scripts/verify-local.ps1` 通过；`git diff --check` 无 whitespace error。
- **`-IncludeE2E` 当前为红且为既有回归**：`e2e/main-path.spec.ts` 与 `e2e/literature-data-source.spec.ts` 因 `waitForLoadState("networkidle")` 超时失败；已 stash 本次全部改动后复现同样两条失败，确认与 adjudication 切片无关。2026-07-15 记录当时 Playwright `4 passed`，故为此后引入。
- 项目目录迁移会使 pnpm 绝对 symlink 全部悬空，前端门禁全红且与代码无关；迁移后必须 `rm -rf frontend/node_modules && pnpm install --frozen-lockfile` 才能取得可信结果。
- `pnpm audit --prod` 本轮未形成漏洞结论：npm quick 与 fallback audit endpoint 均返回 HTTP 410 retired。该结果是 tooling compatibility blocker，不是“0 vulnerabilities”。
- 当前工作树保持未 stage、未 commit、未 push；既有 Track A、Gate 1/Gate 2 与其他用户改动均未清理或回滚。

## 阻塞项

- 没有真实领域 reviewer 完成 Track A 的 150 个 blinded 标签，真实检索质量仍未知。
- 双侧 raw hash 与 trusted manifest 不证明 artifact 来自官方渠道、release/query/mapping 选择正确、靶点具有生物学意义或临床价值。
- 人工判定已可记录，但**没有任何真实领域 reviewer 实际判定过任何一行**；判定能力落地不等于判定已发生，更不等于科学有效。
- `-IncludeE2E` 既有红线未修（两条 literature spec 的 `networkidle` 超时），分支级收口被此阻塞。
- 尚未定义并独立验证 source-bound 网络装配 gate；当前不能导出机制链、PPI、通路或 enrichment 科研结论。人工判定不能代替该 gate。
- JSON/SQLite 的单进程锁不提供多 worker exactly-once；若扩展多进程，必须先设计数据库 claim/lease 或等价原子协议。SQLite 的 `advance()` 与 `append_adjudication()` 已用 CAS + 重试缓解丢更新，JSON backend 全部写方法仍无跨进程守卫。
- Postgres 的 `list_records_for_owner` / `append_adjudication` 仅经代码审阅确认，跨 backend 参数化测试仍只覆盖 json/sqlite。
- adjudications 数组无长度上限，重试循环可无界增长，且每次 append 重写整条记录。

## 当前检查点

Gate 1、Gate 2 双侧 artifact/lineage 工程闭环与 owner-scoped 人工 adjudication 审计流均已完成，但科学就绪度仍为 false —— 判定**能力**存在，判定**事实**为零，且 readiness 仍硬编码 false。下一步先修 E2E 既有红线恢复绿色基线，再单独定义、验证并批准 source-bound network-assembly gate；不能由人工判定或 artifact 一致性翻转 `formal_network_ready`。
