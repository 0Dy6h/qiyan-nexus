# 当前状态

updated_at: 2026-07-15T20:45:24+08:00
artifact_consistency_pass: true（限方向纠偏、Gate 1、Gate 2 双侧 raw-artifact provenance、lineage 与 snapshot-only 输出契约）
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
- 最终门禁：network-focused backend `219 passed`；backend 全量 `794 passed, 1 skipped`；frontend `240 passed`，typecheck/build 通过；Playwright `4 passed`；`git diff --check` 无 whitespace error。
- `pnpm audit --prod` 本轮未形成漏洞结论：npm quick 与 fallback audit endpoint 均返回 HTTP 410 retired。该结果是 tooling compatibility blocker，不是“0 vulnerabilities”。
- 当前工作树保持未 stage、未 commit、未 push；既有 Track A、Gate 1/Gate 2 与其他用户改动均未清理或回滚。

## 阻塞项

- 没有真实领域 reviewer 完成 Track A 的 150 个 blinded 标签，真实检索质量仍未知。
- 双侧 raw hash 与 trusted manifest 不证明 artifact 来自官方渠道、release/query/mapping 选择正确、靶点具有生物学意义或临床价值。
- disease、compound 与 intersection lineage 尚无 owner-scoped 逐行人工 adjudication；自动抽取不能翻转 readiness。
- 尚未定义并独立验证 source-bound 网络装配 gate；当前不能导出机制链、PPI、通路或 enrichment 科研结论。
- JSON/SQLite 的单进程锁不提供多 worker exactly-once；若扩展多进程，必须先设计数据库 claim/lease 或等价原子协议。

## 当前检查点

Gate 1 与 Gate 2 的双侧 artifact/lineage 工程闭环已完成，但科学就绪度仍为 false。唯一下一工程切片是 owner-scoped 的 disease/compound/intersection 人工 adjudication；完成后仍需单独定义、验证并批准 source-bound network-assembly gate，不能由人工判定本身翻转 `formal_network_ready`。
