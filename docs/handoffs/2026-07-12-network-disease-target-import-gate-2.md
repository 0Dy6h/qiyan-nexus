# 网络疾病靶点导入 Gate 2 交接

date: 2026-07-12  
status: partial foundation completed  
scientific_readiness: false

## 本轮目标与结果

本轮在现有 Gate 2 lineage harness 上完成了任务级“独立疾病靶点导入”纵向切片。核心不变量是：疾病 artifact 在 task 创建时封存，浏览器声明的来源不能冒充已验证 provenance，intersection 必须是同时引用 disease/compound 两侧 lineage 的服务端派生记录。

- `POST /api/network/analyze` 新增可选 `disease_target_import`，仅接受严格 `open_targets_association_v1` profile。
- 请求冻结 disease/phenotype/species、source database/version、结构化 query parameters、query/retrieved time、score threshold 与 mapping version。
- 请求 schema `extra="forbid"`；客户端不能提交 row ID、intersection、readiness、provenance verification 或人工判定字段。
- 服务端计算 canonical request payload SHA-256，写入 `provenance_verification_status="unverified_client_import"`，并把 snapshot 持久化到 JSON/SQLite/PostgreSQL network task。
- existing task 的后续 upsert 不覆盖原始 disease snapshot；owner scope 与原子状态推进保持不变。
- `records=[]` 是合法零命中结果，与“未导入”分开显示。
- `/network` 支持选择 JSON artifact、提交前协议一致性检查、来源摘要、disease/compound 高密度 lineage 表与派生 intersection refs 表。

## Lineage 与交集语义

- disease/compound source row 各自获得服务端生成的稳定 SHA-256 `lineage_row_id`；records 重排不改变单行 ID，provenance 字段变化会改变 ID。
- 同一 canonical symbol 的不同 source records 继续保留多行；unique target count 与 source row count 分开。
- `intersection_targets` 每个 unique canonical symbol 恰好一条 row，`derivation="canonical_symbol_exact_match_v1"`。
- 每条 intersection row 完整引用该 symbol 两侧所有 `disease_lineage_row_ids` 与 `compound_lineage_row_ids`；不生成笛卡尔积，不复制 disease row 冒充交集。
- disease/compound 自动行保持 `extracted + pending + unreviewed`；intersection 保持 `derived + pending + unreviewed`，reviewer/time/rationale 均为空。

## 独立验证器

`backend/scripts/validate_network_target_lineage.py` 仍为 stdlib-only，且不 import producer service。当前独立复算：

- disease/compound/intersection unique counts 与 source/derivation row counts；
- provenance-bound disease/compound row IDs 与 intersection row ID；
- disease/compound canonical-symbol 真实交集；
- intersection 双侧 refs 的存在性、同 symbol、完整覆盖和无额外引用；
- disease import payload hash、record count、threshold 与 protocol 一致性；
- 自动/人工状态边界，以及未验证客户端来源不得进入 formal readiness。

伪造 count、row ID、payload hash、threshold、protocol、intersection symbol、悬空/跨 symbol/不完整 refs 或人工状态时退出 2；合法非空 artifact 退出 0。

## 关键文件

- schema：`backend/app/schemas/network.py`
- service/readiness/report：`backend/app/services/network.py`
- API：`backend/app/api/network.py`
- repositories：`backend/app/repositories/{protocols,network_tasks,sqlite_network_tasks,postgres_network_tasks}.py`
- PostgreSQL schema：`backend/app/repositories/postgres_schema.sql`
- validator：`backend/scripts/validate_network_target_lineage.py`
- 前端 API/types：`frontend/lib/api/network.ts`
- 前端 JSON parser：`frontend/lib/network-disease-import.ts`
- 前端工作面：`frontend/components/NetworkAnalysisClient.tsx`
- 操作说明：`docs/guides/network-disease-target-import.md`

## 当前验证

- backend network focused：87 passed。
- backend full pytest：662 passed / 1 skipped。
- backend ruff check、mypy：通过。
- frontend：235 tests、typecheck、production build：通过。
- `./scripts/verify-local.ps1`：通过。
- `./scripts/verify-local.ps1 -IncludeE2E`：通过；Playwright 4/4。
- `pnpm audit --prod`：0 known vulnerabilities。
- `git diff --check`：通过，仅有既有 Windows line-ending warning。

## 不能宣称的内容

- 不能宣称当前 snapshot 来自真实 Open Targets 原始响应；source/version/query 都仍是客户端声明。
- `import_payload_sha256` 不能称为 source artifact hash，只证明服务端封存 payload 的完整性。
- 不能把当前派生 intersection 称为可信核心靶点；默认 compound 仍是 mock，live compound lineage 也尚未完整保留真实数据库版本与阈值。
- 不能宣称 Gate 2 closed 或 `formal_network_ready=true`；两侧人工 adjudication、真实 compound provenance 与服务端疾病来源核验均未完成。
- 自动化 validator 只证明 artifact consistency，不替代外部数据库真实性核验、领域专家判断或生物学验证。

## 唯一推荐下一切片

为一个明确 AD 表型实现服务端 Open Targets 原始快照核验/connector：保存真实 release/version、完整结构化 query、retrieved time、usage/license note 与 `source_artifact_sha256`，并由服务端转换为现有 disease snapshot。只有该路径可以在未来引入 verified provenance 状态；在 compound 来源保真与人工 adjudication 完成前仍不得翻转 scientific readiness。

## 工作树边界

- 当前分支仍是 `feat/pillar2-real-evidence-ranking`，工作树包含用户既有 Track A、Gate 1/Gate 2 与本轮改动。
- 本轮没有 stage、commit 或 push，也没有清理用户既有文件。
- `.mcp.json`、`components.json`、runtime state、uploads、`.tmp` 与 secrets 不应提交。
