# 交接：ChEMBL 成分-靶点 Raw-Artifact Provenance

date: 2026-07-15
status: 本地实现、对抗性收口与全量门禁已完成；未 stage、commit 或 push

## 本次完成

Gate 2 的第二个 artifact 侧已实现。`POST /api/network/compound-import/verify` 只接受 `source_task_id`、`metadata`、`file`；它通过已认证的 `task_id + owner_id` 解析 parent，要求服务端核验的 disease snapshot，以 operator-controlled SHA-256 manifest 核验 ChEMBL artifact，并创建新的 immutable child task。parent task 不会被修改。

受保护模式 HTTP 回归现已直接覆盖 reviewer B 使用 reviewer A 的 `source_task_id` 提交 compound import：接口返回 `404`，且不会新增 child task 或落盘 compound artifact。

离线 `chembl_known_activity_v1` parser 只接受严格的 known-activities JSON。它冻结 ChEMBL version、query facts、pChEMBL threshold、identifier mapping、raw-byte `source_artifact_sha256` 与 canonical `import_payload_sha256`。`source_artifact_filename` 与 `source_artifact_media_type` 仅保存不可信的上传传输标签，不受 manifest 或 hash 绑定。raw bytes 以 content-addressed 方式原子写入 gitignored runtime storage。compound lineage 只从该 snapshot 派生；intersection rows 仍由服务端派生并完整引用两侧。

compound child 现在持久化 `source_task_id`，拒绝 child 作为新的 compound parent，并在 JSON、SQLite、PostgreSQL backend 中保持该 link 不可覆盖。child 完成时只生成冻结 lineage 与交集，明确跳过 provider、机制链、PPI、通路和 enrichment（`chains=[]`、`enrichment=null`）；这避免把 snapshot 与任意 provider/seed graph 混写。没有 parent link 的 legacy child 在 result/report GET 中以非持久化失败投影 fail closed，读取不会推进状态或改写 runtime。独立 validator 同时要求 snapshot-only result 的 chains/PPI/data sources/pipeline steps 为空、enrichment 为 null、warning/readiness 带 network-assembly blocker；它只能校验 parent link 的格式和非自指，不能在没有 parent artifact 时证明 owner 或 parent 的存在。

已同步 `README.md`、`backend/.env.example`、`docs/current-state.md`、`docs/quality-score.md` 与 `docs/guides/network-compound-target-import.md`。

## 最终验证

- network-focused backend suite：`219 passed`。
- `backend`：`ruff format --check app tests`、`ruff check app tests`、`mypy app` 均通过；全量 `pytest -q` 为 `794 passed, 1 skipped`。
- `frontend`：`pnpm test` 为 `240 passed`；`pnpm typecheck` 与 `pnpm build` 均通过。
- `./scripts/verify-local.ps1` 与 `./scripts/verify-local.ps1 -IncludeE2E` 均通过；Playwright 为 `4 passed`。
- `git diff --check` 退出码为 `0`；仅有既有工作树的 LF/CRLF 预警，无 whitespace error。
- `pnpm audit --prod` 未形成漏洞结果：npm audit 的 quick 与 fallback endpoint 均返回 HTTP 410 retired。该项是 registry/tooling compatibility blocker，不能解释为“0 vulnerabilities”。

没有 stage、commit、push、reset 或清理文件；已保留工作树中原有的脏改动。

## 仍存边界

- `chembl_known_activity_v1` 是仓库离线 artifact profile，不是 live ChEMBL integration。
- `server_verified_raw_artifact` 是工程 provenance state，不是科学意义上的 `verified` claim。
- raw-byte 与 canonical-payload hash 不能证明来源官方性、release/query/mapping 正确性、生物学相关性或临床价值。
- 独立 validator 检查持久化一致性，但不重跑生产 Open Targets 或 ChEMBL parser。
- 默认 network execution 仍为 mock，自动行仍为 `pending/unreviewed`，且 `formal_network_ready=false` 必须保持。
- compound child 的 artifact consistency、人工 adjudication 或 `data_mode="live"` 都不等于完成可复算的成分-靶点-通路网络；在新的 source-bound network-assembly gate 被独立定义、验证和批准前，不能导出网络/富集结论。

## 唯一推荐下一切片

为 disease、compound 与派生 intersection lineage rows 实现 owner-scoped human adjudication。它必须使用已验证 request identity 加 `task_id + owner_id`，保持 artifact snapshots immutable，使 report reads 保持 non-mutating，并在科学验证 gate 被明确定义且通过前维持 `formal_network_ready=false`。该切片不能单独产生机制链、PPI、通路或 enrichment，也不能替代后续独立的可复算 source-bound network-assembly gate。不要优先增加 provider、network-analysis、enrichment 或 infrastructure。
