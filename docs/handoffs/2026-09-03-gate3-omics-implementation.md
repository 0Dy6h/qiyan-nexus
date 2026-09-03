# 2026-09-03 交接：种子扩展收尾 + ADR-0018 Gate 3 组学验证层落地

## 今日工作概览

1. **种子扩展收尾（`docs/plans/2026-09-03-seed-expansion-closeout.md` Step 0-7 全部执行）**
   - all.json 合并到 83 条 unique 查询；batch5.json 已跟踪
   - batch2-5 语料补记：`docs/reports/2026-08-17-pubmed-seed-expansion-batch2-5-changelog.md`（527→693 pubmed_live，工程侧 v6 p@5=0.400 / MRR@5=0.744，诚实边界三条齐全）
   - AGENTS.md / current-state.md 检索基线表述已刷新；`verify-local.ps1` 全绿（108.8s）

2. **ADR-0018 Gate 3 组学验证层三个切片全部落地（D-G3-A=a / D-G3-B=a 拍板，计划已生效）**

### G3-1：omics manifest schema + raw artifact 冻结导入门禁
- `POST /api/network/omics-import/verify`：服务端 SHA-256、按 accession 封存不可变 snapshot、同输入重导幂等（201/200）、不同内容同 accession 409、multipart strict allowlist（manifest/file/annotation_file）
- 客户端 manifest（`app/schemas/omics.py` `OmicsTranscriptomicsManifestV1`）`extra="forbid"` 结构性排除全部封存字段（sha256/frozen_at/frozen_by/provenance）
- 独立 validator `backend/scripts/validate_omics_import.py` 与 producer 零共享代码，拒绝全部篡改路径
- **计划偏离（已如实记录）**：GSE32924 series matrix 不含探针→基因符号映射，新增 `platform_annotation` 第二 raw artifact（GPL570.annot.gz），封存纪律与主 artifact 相同

### G3-2：series matrix 解析 + 确定性 DEG 候选（不自动定级）
- gzip parser + condition 分组与 manifest `sample_groups` 校验（不符 fail closed；未映射 condition label fail closed）
- Welch t-test（scipy，`equal_var=False`）+ 纯 Python Benjamini-Hochberg **在折叠后的 21,755 基因层面**（两组零方差的基因不入 BH 分母且恒 adj=1.0）
- 多探针基因折叠：最大平均表达、并列取 probe id 字典序最大（规则随投影 `symbol_mapping_rule` 输出）
- 投影 `OmicsDegAnalysisProjection` 挂结果信封（`GET /api/network/result/{task_id}?omics_verification=true&omics_accession=...` 显式 opt-in），不写入 `NetworkAnalysisResult`、不回写 lineage row；重算逐字节一致
- **真实数据验收**（`docs/reports/2026-09-03-gate3-g32-real-data-verification.md`）：
  - 54,675 探针 → 21,755 基因 → **1,178 DEG 通过**；独立零共享脚本复算一致
  - **IL6/STAT3/TNF 方向均上调但无一通过冻结阈值**（adj_p 0.233/0.256/0.092，|log2FC|<1）——按计划要求如实记录，不凑数；AL vs ANL 对比是原文献核心对比，如需验证须新 snapshot（先与研究者确认）

### G3-3：`omics_validated` 证据等级 + HITL 绑定
- `EvidenceLevel` Literal 插入 `omics_validated`（literature_supported 与 experimental 之间）；后端 `_EVIDENCE_LEVEL_ORDER`/`_EVIDENCE_LEVEL_LABELS`（组学验证）/报告分级表与前端 `NetworkEvidenceLevel`/`getNetworkEvidenceLevelLabel` 两侧同步，两侧各有测试断言
- `derive_chain_evidence_level` 永不产出 `omics_validated`（属性测试覆盖全部输入组合）——跳过人工判定没有任何路径让边显示该等级
- HITL：既有 append-only adjudication 流扩展 `decision="omics_confirmed"` + `omics` 上下文；服务端在判定时刻重验机器条件（row/symbol 绑定、冻结快照存在、候选存在、阈值满足、数据集 Homo sapiens + AD），任一失败 fail closed（422/404）；确认时刻的 DEG 统计量随事件封存
- 读时 overlay `_with_omics_evidence_overlay`：仅 live 结果、仅 literature_supported/predicted 升级；experimental 不降级、mock 恒 `mock_inferred`；存储结果不改写（纯投影）；`formal_network_ready` 全程 `Literal[False]` 未动
- README 补 curl 示例；current-state/AGENTS 已刷新

## 测试与门禁状态

- 后端 911 passed, 1 skipped（omics 48 条新增）+ ruff format/check + mypy strict 全绿
- 前端 282 tests（+1 omics 标签断言）+ typecheck 全绿
- 上午种子收尾后全量门禁通过；Gate 3 提交后待跑 `verify-local.ps1 -IncludeE2E` 收口

## 未做 / 边界（诚实清单）

- IL6/STAT3/TNF 在当前冻结的 AL vs Normal 分析下**没有** `omics_validated` 候选；真人 reviewer 未确认任何行
- compound target verification、RNA-seq、CEL 原档解析、AL vs ANL 新 snapshot：明确不做（后者需研究者拍板）
- PostgreSQL repository 未做活库 parity 验证（沿袭既有边界）
- writer 消费契约仍未定义
