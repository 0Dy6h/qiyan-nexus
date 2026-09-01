# 独立疾病靶点导入契约

updated_at: 2026-07-12

## 目的与边界

本契约把独立疾病靶点 artifact 冻结为 network task 的不可变输入，并由服务端从 disease/compound 两侧 lineage 复算 canonical-symbol 候选交集。当前同时保留旧的客户端导入路径与新的服务端 raw-artifact 核验路径；两者都不把自动抽取升级为人工判定。

当前只接受 `open_targets_association_v1` profile。使用旧 `/api/network/analyze` 客户端导入路径时，服务端固定写入：

- `provenance_verification_status="unverified_client_import"`
- `import_payload_sha256=<canonical request payload SHA-256>`
- `formal_network_ready=false`

`import_payload_sha256` 证明的是系统封存内容未被改写，不是 Open Targets 原始 artifact 校验值。

## 服务端原始快照核验（推荐路径）

`POST /api/network/disease-import/verify` 接收一份离线保存的 Open Targets GraphQL association response、研究对象和声明元数据。该入口不发起 HTTP、GraphQL 或 `httpx` 请求；服务端只读取上传字节，执行静态 parser，按原始字节计算 `source_artifact_sha256`，并把原始文件以 content-addressed 文件名保存到 gitignored runtime 目录 `backend/data/runtime/network_raw_artifacts/`（可用 `NETWORK_RAW_ARTIFACT_DIR` 覆盖）。单次 artifact 上限为 5 MiB、association rows 上限为 500，未知 raw 字段失败关闭。

当前支持的 `open_targets_association_v1` 是 Open Targets GraphQL `disease.associatedTargets` response 结构；服务端从 `target.id`、`target.approvedSymbol` 与 `score` 派生 records：

```json
{"data":{"disease":{"id":"EFO_0000274","name":"atopic eczema","associatedTargets":{"count":1,"rows":[{"target":{"id":"ENSG00000136244","approvedSymbol":"IL6"},"score":0.91}]}}}}
```

仓库测试 fixture 只是按该 GraphQL response schema 裁剪的最小结构样本，不作为某个 Open Targets release 的官方真实性证据；真实运行必须由 operator 从获准来源保存原始 response，并在服务器 manifest 中登记其精确字节 hash 与获取事实。

Open Targets response 本身不携带可充分信任的 release、查询执行时间和本项目 mapping 版本。它们必须先由 operator 写入**服务器控制的可信 manifest**，以 raw-byte SHA-256 为 key，value 是完整的 `NetworkDiseaseTargetVerifyMetadata`。这里的“可信”只指 manifest 处于服务器控制的配置边界；其中 release、retrieved time 与 license note 仍是 operator-recorded facts，不构成 Open Targets 签名或官方真实性证明。运行服务前设置 `NETWORK_OPEN_TARGETS_MANIFEST_PATH` 指向该只读 JSON；浏览器不能提交或覆盖 manifest/hash。manifest 未配置、artifact hash 未登记、客户端声明与 manifest 不一致、空/损坏 JSON、disease query 不符或任一记录低于声明阈值都会返回 `422`，且不落盘、不创建 task。

manifest 结构：

```jsonc
{
  "artifacts": {
    "<64-hex raw-byte sha256>": {
      "source_profile": "open_targets_association_v1",
      "disease": "atopic_dermatitis",
      "phenotype": "特应性皮炎伴 2 型炎症与皮肤屏障异常",
      "species": "Homo sapiens",
      "source_database": "Open Targets Platform",
      "database_version": "25.06",
      "source_query_id": "EFO_0000274",
      "source_query_label": "atopic eczema",
      "source_query_parameters": {"datatype": "overall"},
      "query_date": "2026-07-12",
      "retrieved_at": "2026-07-12T08:30:00Z",
      "score_name": "association_score",
      "applied_threshold": 0.6,
      "threshold_operator": "gte",
      "identifier_mapping": "Ensembl target approvedSymbol",
      "identifier_mapping_version": "25.06",
      "usage_license_note": "Open Targets Platform data usage terms apply."
    }
  }
}
```

multipart 字段：

- `query`、`analysis_type`、`evidence_policy`；
- `metadata`：JSON 字符串，字段与下方客户端导入示例相同，但不含 `records`，并新增 `usage_license_note`；
- `file`：离线保存的原始 `.json` response。浏览器使用 `FormData`，不得手写 `Content-Type`。

`metadata` 使用 `extra="forbid"`。客户端提交 `records`、任何 hash、`provenance_verification_status`、readiness、intersection/lineage ID 或人工 adjudication 字段都会被拒绝。成功创建的 snapshot 固定为：

- `provenance_verification_status="server_verified_raw_artifact"`；
- `source_artifact_sha256=<服务端对原始字节计算的 SHA-256>`；
- `import_payload_sha256=<服务端解析 records 后 canonical payload 的 SHA-256>`；
- 保存 release/version、结构化查询、query/retrieved time、原始文件名/media type 与 usage/license note。

该状态只是中间态，不是终态 `verified`。`source_artifact_sha256` 锚定原始文件的字节身份与完整性，`import_payload_sha256` 锚定持久化 canonical disease snapshot；raw-to-records 派生由生产 parser 及其测试覆盖，当前独立 validator 不重演 GraphQL parser。两种 hash 都不证明所选 release 正确、文件一定来自官方渠道、表型映射正确或靶点具有生物学意义。`formal_network_ready` 仍为 `false`，compound 来源保真、阈值和逐边人工 adjudication 仍是后续门禁。

## 请求结构

`disease_target_import` 是 `POST /api/network/analyze` 的可选字段。以下为零命中结构示例；所有 `REPLACE_*` 值必须替换为真实查询事实，且 disease/phenotype/species/query_date 必须与同一请求的 `research_protocol` 完全一致。

```jsonc
{
  "source_profile": "open_targets_association_v1",
  "disease": "atopic_dermatitis",
  "phenotype": "特应性皮炎伴 2 型炎症与皮肤屏障异常",
  "species": "Homo sapiens",
  "source_database": "Open Targets Platform",
  "database_version": "REPLACE_WITH_SOURCE_RELEASE",
  "source_query_id": "EFO_0000274",
  "source_query_label": "atopic eczema",
  "source_query_parameters": {
    "datatypes": ["genetic_association", "literature"],
    "score_aggregation": "REPLACE_WITH_ACTUAL_METHOD"
  },
  "query_date": "2026-07-12",
  "retrieved_at": "2026-07-12T08:30:00Z",
  "score_name": "association_score",
  "applied_threshold": 0.6,
  "threshold_operator": "gte",
  "identifier_mapping": "Ensembl target approvedSymbol",
  "identifier_mapping_version": "REPLACE_WITH_MAPPING_RELEASE",
  "records": []
}
```

非空 `records` 的每一行是一个 source observation：

```json
{
  "raw_identifier": "ENSG00000136244",
  "canonical_symbol": "IL6",
  "source_record_id": "REPLACE_WITH_STABLE_SOURCE_RECORD_ID",
  "source_score": 0.91
}
```

约束：

- `canonical_symbol` 必须符合当前 human HGNC-symbol 形态门禁；映射真实性仍需后续服务端核验。
- `source_score` 必须在 `[0, 1]` 且满足 `source_score >= applied_threshold`。
- 完全重复 observation 被拒绝；同一 `source_record_id` 映射到多个 canonical symbol 被视为 ambiguous 并拒绝。
- `records=[]` 是旧客户端导入路径的合法零命中声明，但该路径的来源与查询执行仍未验证；不得为满足非空要求降低阈值或伪造行。服务端 raw-artifact 路径的零命中由 GraphQL response 的 `count=0, rows=[]` 与 trusted manifest 共同封存。
- 请求 schema 使用 `extra="forbid"`。客户端不能提交 `lineage_row_id`、`intersection_targets`、`reviewer_id`、`adjudication_status`、`decision`、`provenance_verification_status` 或 readiness 字段。

## 派生语义

- disease 与 compound source row 的 `lineage_row_id` 由服务端对规范化 provenance 字段计算 SHA-256；输入顺序不影响单行 ID。
- `intersection_targets` 每个 unique canonical symbol 恰好一行，`derivation="canonical_symbol_exact_match_v1"`。
- 每个 intersection row 必须完整引用该 symbol 两侧的所有 `disease_lineage_row_ids` 与 `compound_lineage_row_ids`，不生成笛卡尔积，也不复制单侧 source row 冒充交集 lineage。
- disease、compound 与 intersection 均保持 `pending/unreviewed`，直到未来 owner-scoped 人工 adjudication 明确落地。

## 独立验证

把完成任务的 `result` 对象或 `{ "result": ... }` 保存为 JSON 后运行：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\validate_network_target_lineage.py C:\path\to\network-result.json
```

对 `server_verified_raw_artifact` 额外提供原始文件，可独立复算字节 hash：

```powershell
& .\.uv-test-venv\Scripts\python.exe scripts\validate_network_target_lineage.py `
  C:\path\to\network-result.json `
  --source-artifact C:\path\to\open-targets.json
```

退出码 `0` 表示已检查的持久化 artifact 内部一致；退出码 `2` 表示计数、row ID、阈值、payload hash、raw-byte hash、协议字段、交集 symbol 或双侧 refs 至少一项不一致。验证器独立复算 raw bytes 与 canonical snapshot，但不独立重演生产 GraphQL raw-to-records parser；该验证不替代 release 选择核验、外部数据库真实性核验、领域专家判断或人工 adjudication。
