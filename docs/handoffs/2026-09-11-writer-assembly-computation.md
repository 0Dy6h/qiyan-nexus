# Handoff：writer 装配计算切片落地（2026-09-11 夜班）

- date: 2026-09-11（夜班首班 23:30 开工，切片提交 `bfff01d`）
- 依据：`docs/plans/2026-09-11-writer-assembly-computation.md`（研究者 2026-09-11 拍板，7 条规则）+ 消费契约 D1-D9（2026-08-16 拍板）
- 前序：`docs/handoffs/2026-09-06-writer-consumption-primitive.md`（消费原语，本切片在其写前门禁之上补「怎么算」半边）

## 实现了什么

1. **输出信封扩展**（`backend/app/schemas/network.py`）：`NetworkAssemblyOutput` 新增 `chains: list[NetworkChain]` 与 `warnings: list[str]`。两者为**服务端派生**，刻意不进 `output_sha256` hash 域（hash 仍只键 writer `output_payload`，D5 幂等重放语义不变）；消费是审计不是推进，`formal_network_ready` 仍恒 `false`。
2. **装配纯函数**（`backend/app/services/network.py` 的 `_assemble_chains_from_plan`）：consume 时从 plan `selected_intersections` 确定性派生链——
   - 成分×靶点组合一条链，同 canonical symbol 的多来源行不合并（拍板 #1）；
   - compound 取冻结行 `raw_identifier`（target ChEMBL ID）；score 按 `score_name=pchembl_value` 走 /10 归一口径（与 `network_connectors._pchembl_to_score` 一致），None→0.0；
   - pathway 由本地 KEGG 字典（`backend/data/network/sample_kegg_pathways.json`）按文件序首命中填 `name`，未命中留空并计数进 warnings（拍板 #3）；
   - **herb/formula 诚实留空**（拍板 #4）：已核实冻结协议 `NetworkResearchProtocol` 与 plan 均无 herb/formula 结构化字段，不从 mock 样例实体字典反查归属；
   - 不跑富集（拍板 #5），warnings 固定含 herb/formula 留空与富集不跑两条诚实说明（拍板 #6）。
3. **证据分级按行 provenance 判定**（拍板 #2 宁低不高）：verified 行（`evidence_origin=known_activity/disease_association`）的链 `target_evidence_type` 压为 `predicted`（ChEMBL known_activity **不上浮** experimental）→ `grade_chains_evidence(data_mode="live")` 出 `predicted`，未来有文献引用来源时 `evidence_refs` 非空自动升 `literature_supported`。**不按任务 `data_mode` 判**：verified 导入任务的 data_mode 只是 provider 开关（默认仍 mock），按任务级判会把真实行错标 `mock_inferred`；mock 行防御分支（理论上过不了装配门禁）恒 `mock_inferred`。
4. **Fail closed**：selected 行解析失败（lineage hash 绑定下不可能，持久化矛盾）→ 500 integrity `assembly_input_unresolvable`，不落盘。

## 测试与验证

- repo 级 `test_consume_roundtrips_assembled_chains`（json/sqlite 参数化）：created 返回与 D5 重放从落盘读回的 chains 逐字段相等（SQLite `output_json` 全文序列化，加字段零迁移）。
- API 级 `test_consume_output_envelope_carries_assembled_chains`：真实双侧 verified 导入→逐行判定→seal→consume 全链路，断言恰 2 条链（IL6/CHEMBL1792/0.64、EGFR/CHEMBL203/0.61）、恒 predicted、herb=""、formula=None、pathway 命中、warnings、重放 chains 相等。
- **变异验证**：装配链分级变异为 known_activity（会上浮 experimental）→ API 测试即红；还原后绿。
- 门禁：后端 **953 passed + 1 skipped**（基线 950 + 新增 3）、前端 302 pass + typecheck + build 全绿；隔离预览官方 smoke passed（`.tmp/night-first-0911` 已清理）。
- 独立 validator 未动（D9=B，只校验 plan 不校验输出信封）。

## 待办（顺序即拍板）

1. **研究者抽样目视验收**（拍板 #7）：本切片出链后需研究者点头才算收工——可起隔离预览（`-OpenTargetsManifestPath` 注入 trusted manifest 走 verified 流程）或直接看 API 测试断言的链内容。
2. 切片 2：D9 独立 validator 扩展（校验输出信封/chains）。
3. 切片 3：PG 活库 parity。

## 边界重申

装配产物仍是「装配输入已封存」的工程事实：无逐边人工判定、无真实 reviewer sign-off，`formal_network_ready` 恒 false，不得写成 scientific readiness。
