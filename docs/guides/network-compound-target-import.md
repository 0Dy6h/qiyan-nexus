# ChEMBL 成分-靶点离线导入

`POST /api/network/compound-import/verify` 为已服务端核验的疾病靶点任务补充成分-靶点 provenance。它使用仓库定义的离线 `chembl_known_activity_v1` profile，不会请求 ChEMBL HTTP API，也不会把自动抽取写成人工判定。

## 原始文件与 Manifest

artifact 必须是 UTF-8 JSON，根对象和每一项都只允许下列字段；空文件、未知/缺失字段、超过 500 项、重复 observation、同一 `activity_id` 映射多个 symbol、compound/species 不符或低于阈值都会以 `422` 失败关闭。文件上限为 5 MiB。

```json
{
  "activities": [
    {
      "activity_id": "CHEMBL_ACTIVITY_1001",
      "molecule_chembl_id": "CHEMBL1201587",
      "target_chembl_id": "CHEMBL1792",
      "target_gene_symbol": "IL6",
      "target_organism": "Homo sapiens",
      "pchembl_value": 6.4
    }
  ]
}
```

服务启动前由 operator 设置 `NETWORK_CHEMBL_MANIFEST_PATH` 到服务器控制、只读的 JSON。它以 raw-byte SHA-256 为 key；浏览器不能提交或改写 hash、manifest 或 records。上传 metadata 必须与该 key 的条目逐字段一致：

```json
{
  "artifacts": {
    "<64-hex-raw-byte-sha256>": {
      "source_profile": "chembl_known_activity_v1",
      "compound_id": "CHEMBL1201587",
      "compound_label": "Quercetin",
      "species": "Homo sapiens",
      "source_database": "ChEMBL",
      "database_version": "34",
      "source_query_id": "CHEMBL1201587",
      "source_query_label": "Quercetin",
      "source_query_parameters": {"assay_organism": "Homo sapiens", "standard_type": "IC50", "pchembl_value_min": 6.0},
      "query_date": "2026-07-15",
      "retrieved_at": "2026-07-15T08:30:00Z",
      "score_name": "pchembl_value",
      "applied_threshold": 6.0,
      "threshold_operator": "gte",
      "identifier_mapping": "ChEMBL target component gene symbol",
      "identifier_mapping_version": "34",
      "usage_license_note": "ChEMBL data; see database terms."
    }
  }
}
```

## 请求与任务边界

multipart 仅允许 `source_task_id`、`metadata`、`file`，并要求 `Content-Length`；不得额外传 `records`、hash、provenance、readiness、lineage、人工作业字段、owner 或 reviewer。`metadata` 是上方 manifest metadata 的 JSON 字符串，`file` 是原始 `.json`；使用 `FormData` 时不要手写 `Content-Type`。

服务端仅按已认证身份的 `task_id + owner_id` 查 source task。它必须有研究协议和 `server_verified_raw_artifact` disease snapshot，且 compound metadata 的 `species`、`query_date` 必须与父 task 协议相同。已有 `compound_target_import` 的 child task 不得继续作为新的 compound parent。成功时创建一个新 immutable child task，冻结父 task 的 query、analysis type、研究协议和 disease snapshot；父 task 不会被修改。

## Child 输出边界

child 会持久化并在 result/report 中导出 `source_task_id`，它只表示服务端创建时绑定的疾病 parent。服务端与独立 validator 可检查该 ID 的格式和非自指；没有同时提供 parent artifact 时，不能据此独立证明 parent 仍存在或属于同一 owner。

当前 child 是 snapshot-only：它只返回冻结的 disease/compound source rows 和服务端派生交集，刻意不调用 network provider，也不生成机制链、PPI、通路或富集。完成结果固定为 `chains=[]`、`ppi_edges=[]`、`data_sources=[]`、`pipeline_steps=[]`、`enrichment=null`，并给出精确 blocker `导入靶点尚未构建可复算的成分-靶点-通路网络闭环。`。即使 parent task 使用 `data_mode="live"`，这也不表示已形成真实网络链路。

没有 `source_task_id` 的历史 compound child 在结果和报告读取时失败关闭；GET 不会借此写入或推进 runtime state。

## Hash、复核与非声明

服务端计算 `source_artifact_sha256`（原始字节）和 `import_payload_sha256`（canonical metadata/records），把 raw bytes 原子保存到 gitignored 的 `NETWORK_RAW_ARTIFACT_DIR/<sha256>.json`。`formal_network_ready` 仍为 `false`，所有自动 source row 与派生 intersection 都是 `pending/unreviewed`。

`source_artifact_filename` 与 `source_artifact_media_type` 只保留客户端上传时的传输标签；它们会在 Markdown 输出时转义，但不受 manifest 或任一 hash 绑定，不能作为来源真实性、官方文件名或格式证明。可信字节身份只看服务端计算的 `source_artifact_sha256`。

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\validate_network_target_lineage.py `
  C:\path\to\network-result.json `
  --disease-source-artifact C:\path\to\open-targets-response.json `
  --compound-source-artifact C:\path\to\chembl-known-activities.json
```

退出码 `0` 只表示 raw hash、canonical payload、阈值、lineage 和双侧 refs 内部一致；脚本不重演生产 parser。上述 hash 不证明 artifact 来自 ChEMBL 官方、release/query/mapping 选择正确、靶点有生物学意义，亦不替代 owner-scoped 人工 adjudication 或科学验证。
