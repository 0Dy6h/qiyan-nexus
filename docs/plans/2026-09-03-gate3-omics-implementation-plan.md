# 2026-09-03 方案：ADR-0018 Gate 3 组学验证层 — 实现计划（切片 G3-1 → G3-3）

> 本文件就是 ADR-0018 L120 要求的「单独计划、契约与验收」。
> 状态：**Active（2026-09-03 生效）**。研究者本人当日指示「继续开发！先推进方案」，据此按本文件推荐项拍板：**D-G3-A = a（GEO series matrix + scipy 确定性统计）、D-G3-B = a（冻结 `GSE32924_series_matrix.txt.gz`）**。前置的种子扩展收尾方案已于同日先执行完毕（干净基线）。

## 一、授权与范围

- 依据：ADR-0018（Accepted）+ Gate 3 评估（`docs/adr/0018-gate3-evaluation.md`，状态已确认 2026-08-16）。Gate 3 只覆盖 **disease target verification（靶点→疾病边）**；compound target verification 明确不在范围（gate3-eval L239）。
- 验证数据集：GSE32924（33 例人类 AD 皮肤活检微阵列，GPL570，GEO open access，PMID 21388663）。v1 验证对象：IL6 / STAT3 / TNF 在 AD 皮损 vs 正常皮肤中差异表达（预期上调）。
- 新证据等级 `omics_validated`：插入 `literature_supported` 与 `experimental` 之间；6 项升级条件全部满足才升级；「有文件即 experimental」禁止；**`omics_validated` 的出现不翻转 `formal_network_ready`**。
- 默认路径不接组学：omics 端点是显式 opt-in，不属于默认离线 profile。

## 二、现状锚点（2026-09-03 核实）

| 锚点 | 位置 |
|---|---|
| 组学代码 | 前后端 **零命中**（grep omics/gse/transcript 均空）；GSE32924 数据未下载 |
| `EvidenceLevel` Literal | `backend/app/schemas/network.py:11-16` |
| `formal_network_ready` 类型级钉死 | `schemas/network.py:611/621`（`Literal[False]`，不动）、`:654`、`services/network.py:378` |
| 证据等级推导与标签 | `services/network.py:1449`（`_EVIDENCE_LEVEL_ORDER`）、`:1455`（`_EVIDENCE_LEVEL_LABELS`）、`:1463`（`derive_chain_evidence_level`）、`:1476`（`grade_chains_evidence`）、`:1929-1939`（报告分级表） |
| 可复用模板（producer 侧） | `services/network.py:221-256` `_persist_verified_raw_artifact`（content-addressed、tmp+原子替换、hash 复验）；`:164/:190` `build_verified_{disease,compound}_import_snapshot`；`api/network.py:61-66/:136-141` 两个 verify 端点 |
| 前端报告标签同步点 | `frontend/lib/network-report-export.ts`（与 `services/network.py:1490-1496` docstring 约定严格对齐）；相关测试 `network-report-ui.test.ts`、`network-evidence-grading-ui.test.ts` |
| 统计依赖 | **`numpy`、`scipy` 已在 `backend/pyproject.toml`**，G3-2 不需要新增任何依赖 |
| manifest 契约草案 | `docs/adr/0018-gate3-evaluation.md` L101-153（五段：dataset / raw_artifact / analysis_context / edge_mapping / provenance） |

## 三、决策点（生效前必须拍板）

### D-G3-A：DEG 计算管线的 v1 数据源（推荐 a）

- **a（推荐）：GEO series matrix + scipy 确定性统计。** 解析 `GSE32924_series_matrix.txt.gz`（GEO 分发的已处理表达值，gzip 文本，纯 Python 可解析），组间比较用 `scipy.stats.ttest_ind(equal_var=False)`（Welch）+ 纯 Python Benjamini-Hochberg；阈值 adj_p<0.05 且 |log2FC|>1。零新增依赖、完全确定性、可独立复算。**与 gate3 草案的 RMA+limma 有偏离**：manifest 的 `analysis_context` 必须如实记录实际管线（`geo_series_matrix_values + welch_t_test + benjamini_hochberg`）并注明偏离；管线参数属 manifest 冻结内容，不触犯 ADR-0018 L94-99 需新 ADR 的修订边界清单。
- b：操作员离线跑 R（affy/oligo RMA + limma）后导入结果矩阵。更贴草案原文，但引入 R 工具链、跨版本不可复现风险与额外操作员负担。留作后续升级路径，不在 v1。

### D-G3-B：G3-1 冻结哪个 raw artifact（推荐 a）

- **a（推荐）：`GSE32924_series_matrix.txt.gz`**（几 MB，是 v1 管线的真实分析输入）。manifest `raw_artifact.filename/format` 字段本就允许非 CEL。
- b：`GSE32924_RAW.tar`（202 MB CEL 原档）。仅在采纳 D-G3-A(b) 时才需要冻结。
- 无论选哪个：下载是操作员动作（NCBI GEO），不进代码、不进 git；样本计数以下载实物为准（manifest `sample_count_note` 已声明 33/13/12/8 是草案估计），G3-2 解析时分组与 manifest 不符必须 fail closed。

## 四、切片 G3-1：omics manifest schema + raw artifact 导入门禁

**目标**：把组学数据文件以服务端 SHA-256、operator-controlled trusted manifest、content-addressed、不可变快照方式冻结——与 Open Targets / ChEMBL raw artifact 同级纪律。**不做任何解析与统计。**

改动面：
1. 新建 `backend/app/schemas/omics.py`：`OmicsTranscriptomicsManifestV1` 五段结构照 gate3-eval L101-153；**客户端提交模型不含** `raw_artifact.sha256/frozen_at/frozen_by` 与整段 `provenance`（服务端构建 snapshot 时注入，镜像 `_build_import_snapshot` 的 allowlist 思路）。
2. 新建 `backend/app/services/network_omics.py`：`build_verified_omics_import_snapshot` + 持久化（复用/抽取 `_persist_verified_raw_artifact` 的 content-addressed 逻辑；产物目录 `backend/data/runtime/network_raw_artifacts/omics/`，gitignored）。manifest 校验硬编码检查：`organism == "Homo sapiens"`、病种 `atopic_dermatitis`、`formal_network_ready_impact: false`、`evidence_level_upgrade: none (pending analysis)`。
3. `backend/app/api/network.py` 新增 verify 导入端点：**完全镜像 `verify_disease_import_endpoint` 的 auth/owner 处理与 multipart strict allowlist**；服务端算 SHA-256；同文件重导幂等返回既有 snapshot。
4. 独立 validator `backend/scripts/validate_omics_import.py`：与 producer 零共享代码；重算 hash、验证快照不可变、验证 manifest 字段封存、拒绝客户端提交封存字段的每一种篡改路径。
5. 测试 `backend/tests/test_network_omics.py`（TDD，先红后绿）。

验收（测试即验收）：
- 客户端提交 sha256/provenance/frozen 字段 → 422/400，绝不入库
- multipart 外层字段 strict allowlist，多一个字段即拒
- 快照落盘 content-addressed、重导幂等、二次导入不同内容同路径 → 拒绝
- `formal_network_ready` 全程不被触碰（显式断言）；`EvidenceLevel` 本切片**不改**
- 默认离线 profile 与现有 863+ 后端测试零行为变化
- `ruff format/check` + `mypy app`（strict）+ `pytest -q` 全绿

## 五、切片 G3-2：series matrix 解析 + 确定性 DEG 候选（不自动定级）

**目标**：从已冻结快照解析表达矩阵，复算 DEG，与某 task 的 `disease_targets` lineage canonical symbol 匹配，产出 **`pending_human_confirmation` 候选**——只出候选，不写任何等级。

改动面：
1. `services/network_omics.py` 增加：gzip 文本 parser（只接受按 sha256 从冻结存储解析的字节，绝不接受客户端重传）；`!Sample_*` 特征列分组并与 manifest `sample_groups` 校验（不符即 fail closed）；Welch t-test + BH；阈值从 manifest `analysis_context` 读取（不从请求读）。
2. 输出投影：挂 task 结果响应信封（与 adjudication projection 同模式），**不写入 `NetworkAnalysisResult`、不回写冻结 lineage row**；同一输入重算必须逐字节一致（确定性断言测试）。
3. symbol 匹配：任务 lineage 查询必须 owner-scoped（复用 `task_id + owner_id` 纪律）。
4. 测试：分组不符 fail closed、非冻结输入拒绝、确定性复算、只出候选不断级、compound 侧零触及。

验收：DEG 结果可用独立脚本对同一冻结快照复算一致；IL6/STAT3/TNF 出现在候选中的断言以实际数据为准（若数据不支持预期，如实记录，不凑数）。

## 六、切片 G3-3：`omics_validated` 证据等级 + HITL 绑定

**目标**：等级进入 schema 与报告，且唯一升级路径是人工判定。

改动面：
1. `schemas/network.py:11-16` Literal 插入 `"omics_validated"`（literature_supported 与 experimental 之间）；`services/network.py` 的 `_EVIDENCE_LEVEL_ORDER` / `_EVIDENCE_LEVEL_LABELS`（中文标签建议「组学验证」）/ 报告分级表同步；mypy strict 会暴露所有需要穷举的分支。
2. 前端 `frontend/lib/network-report-export.ts` 标签同步；`network-report-ui` / `network-evidence-grading-ui` 测试补断言（跨端字段两侧各有断言——AGENTS.md 硬约束）。
3. HITL：在现有 append-only adjudication 流上扩展一个 omics 确认型 decision；服务端在判定时刻**重验** 5 项机器条件（候选存在于冻结 DEG 快照、阈值满足、数据集条件匹配 Homo sapiens + AD 组织），第 6 项（人工确认）即该判定本身。latest-wins 投影、`reviewer_id` 持久化不回投、冻结 row 的 `adjudication_status`/`decision` 不回写、结构上不可能翻转 `formal_network_ready`（`Literal[False]` 不动）。
4. README 补新端点 curl 示例；`docs/current-state.md`、AGENTS.md L7「三个 Gate 均未写代码」表述按落地进度更新；新 handoff。

验收：跳过人工判定没有任何路径让某条边显示 `omics_validated`；评估期间追加判定返回 `conflict` 的既有语义不被破坏；全门禁 + `verify-local.ps1 -IncludeE2E` 绿。

## 七、硬约束清单（每条有代码锚点，写测试时逐一对应）

1. fail closed：未过 manifest 门禁的组学数据不得进入分析层（ADR-0018 不变量 6）
2. `formal_network_ready` 恒 false：`schemas/network.py:611/621` `Literal[False]` 不动
3. omics 只作显式 opt-in，不进默认路径、不成为放松其他纪律的理由
4. HITL 不可绕过：pipeline 只出候选，升级必须走 adjudication（不变量 8）
5. 不新增重依赖：G3-1/G3-2 零新增（scipy/numpy 已有）；G3-3 零新增
6. 冻结快照不可变、客户端不提交封存字段、multipart strict allowlist
7. 病种/物种 Literal 复用 `schemas/network.py:17-18`
8. mock 证据恒 `mock_inferred`：`omics_validated` 只作用于 live + 已核验 lineage 的边

## 八、明确不做

compound target verification、RNA-seq、CEL 原档解析（除非 D-G3-A 选 b）、任何 `formal_network_ready` 翻转路径、把组学接入默认离线 profile、真实 LLM/embedding。

## 九、执行顺序建议

1. 先完成 `2026-09-03-seed-expansion-closeout.md`（干净基线后再开新代码）
2. 拍板 D-G3-A / D-G3-B（推荐都选 a）
3. 操作员下载 `GSE32924_series_matrix.txt.gz` 到本地（不入 git），核对实际样本分组
4. G3-1 TDD（约一个晚上）；G3-2、G3-3 各自独立会话推进，每切片结束跑全门禁并更新文档状态
