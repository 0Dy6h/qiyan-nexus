# Writer 装配计算逻辑切片计划（2026-09-11 研究者拍板）

- date: 2026-09-11
- status: planned（已拍板规则，待实现；夜班可开工）
- 依据：消费契约 `docs/plans/2026-08-14-writer-consumption-contract-decision-pack.md`（D1-D9，2026-08-16 拍板）§1.3 排除项 + `docs/current-state.md`「未完成边界」；前序切片 `docs/plans/2026-09-06-writer-consumption-primitive.md`（已 implemented）。
- 边界：实现 writer 的装配计算逻辑本身；不翻转 `formal_network_ready`；不扩展独立 validator（D9=B，后续切片 2）；不做 PG 活库 parity（后续切片 3）。

## 1. 切片范围

从 candidate plan 的 selected intersections（已 included 的 `intersection_targets` 行）生成 `NetworkChain` 列表，并经消费原语 `POST .../assembly-plans/{plan_id}/consume` 原子落盘为不可变输出信封。写前强制门禁（R1-R9）已由消费原语保证，本切片只实现「怎么算」这半边。

## 2. 关键事实（来自装配门契约）

- selection unit = 一行 `intersection_targets`（`lineage_row_id` 不可变），携带 canonical_symbol + 冻结的 disease/compound 来源行 refs + included 的 backing refs。
- plan 不包含或暗示 `formal_network_ready=true`；输出信封 schema 已钉死 `formal_network_ready: Literal[False]`。
- 消费记录 exactly-once；输出确定性（幂等重放前提，D5-附加）。

## 3. 装配规则（2026-09-11 研究者拍板，按建议值确认）

| # | 决策点 | 拍板结果 |
|---|---|---|
| 1 | 展开粒度 | **按「成分 × 靶点」组合展开**，一个组合一条链；同一 canonical symbol 的多行来源不合并（对齐装配门口径） |
| 2 | 证据分级 | 真实 ChEMBL/OpenTargets 来源、无文献引用 → 恒 **`predicted`**；有 `evidence_refs` 且被引用支持 → 最高 `literature_supported`；`data_mode=mock` 恒 `mock_inferred`（ADR-0015 不变，宁低不高） |
| 3 | 通路层 | **本地通路字典**填（复用 `backend/data/network/sample_kegg_pathways.json` 类本地源）；填不上留空，不编造 |
| 4 | 药材/复方层 | **先核实** task/plan 是否携带 herb/formula 信息（compound child 的冻结协议/查询载荷里有没有）；没有则诚实留空 |
| 5 | 富集分析 | **本切片不跑**（既有 mock 超几何不是科研结论） |
| 6 | 输出信封 | chains + evidence_refs + warnings；`formal_network_ready` 恒 false；`assembly_input_ready: Literal[True]`；disclaimer byte-identical |
| 7 | 验收 | 出链后研究者**抽样目视**确认，点头才算本切片收工 |

## 4. 实现要点

- 消费原语/信封/仓储已就位，本切片主要新增：装配计算函数（plan selected rows → chains）、证据分级接线（复用 `derive_chain_evidence_level` / `grade_chains_evidence`）、通路/药材层的可选填入、相应测试。
- 测试口径：repo 级（json/sqlite 参数化）+ API 级（消费返回的信封含正确 chains），参照 09-06 切片；变异验证照 AGENTS.md 硬约束。
- 验证：`verify-local.ps1` 全绿；隔离预览 smoke 走查「真实 verified 双侧导入 → 判定 → seal → consume → 读信封 chains」。

## 5. 给夜班的首班提示

- 本计划即开工依据；开工前先核实决策 #4（herb/formula 信息是否存在）。
- 遗留清单中「writer 后续切片拍板」两项（D9 validator、PG parity）按研究者 2026-09-11 口径：顺序 2、3，本切片后接续。
- 其余拍板项不变：真人 adjudication 只在真实 verified 导入后按行执行；mock 样例行不判定（见 `docs/reports/2026-09-11-track-a-acceptance-and-adjudication.md`）。
