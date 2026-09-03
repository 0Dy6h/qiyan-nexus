# Gate 3 G3-2 真实数据验收记录（GSE32924，2026-09-03）

> 操作与数字均为工程侧生成；IL6/STAT3/TNF 断言按计划要求「以实际数据为准，不凑数」如实记录。
> 本记录是切片 G3-2 验收的两条硬性证据之一（另一条是 `tests/test_network_omics.py` 全绿）。

## 1. 冻结输入（不入 git，均在 gitignored 存储）

| 项目 | 值 |
|---|---|
| 表达矩阵 | `GSE32924_series_matrix.txt.gz`，6,033,264 字节，SHA-256 `3ef0577e77dc5942247238c6d460aa26a00a1504f6ca6a342429e52061871166` |
| 平台注释 | `GPL570.annot.gz`（2016-08-09 版），8,471,521 字节，SHA-256 `d7cd44352127b1e34f3a720ebea86093ef255a38f1612a85a2962b71bde8f394` |
| snapshot_id | `omics-snapshot-6fb6acf85730c3314f2ce4d81bcff67cd0a77341986e8e2d85f2093819c0454d` |
| 样本分组（下载实物核对） | 33 = 13 AL + 12 ANL + 8 Normal（condition characteristic 行），与 manifest `sample_groups` 一致；GEO 摘要正文 normal n=10 为已知草案差异，`sample_count_note` 已声明以实物为准 |
| 独立 validator | `validate_omics_import.py` 对该 store 通过（hash 重算、封存字段、snapshot_id 重绑定全部复算一致） |

## 2. 管线与产出（analysis_context 冻结值：welch_t_test + benjamini_hochberg，adj_p<0.05 且 |log2FC|>1）

- 解析：54,675 探针 × 33 样本（log2 尺度 series matrix values，非 RMA 重归一化——与 D-G3-A=a 的偏离已在 manifest `analysis_context` 如实记录）
- symbol 映射：GPL570 annot `Gene symbol` 列，`///` 取首；多探针基因按最大平均表达折叠、并列取 probe id 字典序最大（规则文本随投影输出 `symbol_mapping_rule`）
- 折叠后 21,755 个唯一基因；**每基因一个 Welch 检验；BH 在 21,755 个基因层面校正**（不可检验基因——两组零方差——不计入 BH 分母且恒 adj=1.0）
- **通过阈值：1,178 个基因**
- 确定性：同输入重算 `model_dump_json` 逐字节一致（单元测试 + 真实数据双重验证）

## 3. 独立复算（与 producer 零共享代码）

独立脚本（独立 parser、独立 BH 实现、独立折叠循环，仅共享 numpy/scipy 库本身）对同一冻结快照复算：21,755 基因、**1,178 通过，完全一致**。

复算排障记录（对将来复现者有用）：两轮不一致均为诊断脚本自身 bug——(1) BH 散射把有限子集索引当全量索引用；(2) 先在 54,675 探针层面做 BH（分母错误）。修正后逐数字一致。

## 4. v1 验证对象的真实结果（诚实记录，不凑数）

计划预期：IL6 / STAT3 / TNF 在 AD 皮损 vs 正常皮肤中差异表达（预期上调）。

| 基因 | 选中探针 | log2FC (AL vs Normal) | p | adj_p | 通过？ |
|---|---|---:|---|---|---|
| IL6 | 205207_at | +0.323 | 1.101e-01 | 2.332e-01 | **否** |
| STAT3 | 208991_at | +0.202 | 1.258e-01 | 2.565e-01 | **否** |
| TNF | 207113_s_at | +0.313 | 3.080e-02 | 9.153e-02 | **否** |

结论：三者在 AL vs Normal 方向均为上调，但**无一通过冻结阈值**（|log2FC| 远小于 1；TNF 原始 p 显著但 BH 后不显著）。这与其他组学文献的普遍观察一致：单基因 DEG 层面 AL vs Normal 的免疫信号远弱于 AL vs ANL 配对对比（原文献 Suárez-Fariñas 2011 的核心对比即 AL vs ANL）。

**含义**：v1 若要给出 IL6/STAT3/TNF 的 `omics_validated` 候选，当前冻结的 AL vs Normal 分析不支持。后续若研究者决定验证 AL vs ANL 对比，必须以新的 analysis_context 冻结新 snapshot（同 accession 不同 comparison 会被不可变快照门禁拒绝，需新 accession 别名或新快照版本策略——先与研究者确认，不在本切片内自作主张）。

## 5. 对计划的偏离（已回写）

- 计划原假设 series matrix 自带 symbol 映射；实际 GPL570 series matrix 只有探针 ID。因此增加 **platform_annotation 第二 raw artifact**（GPL570.annot.gz），封存纪律与主 artifact 相同（服务端 SHA-256、content-addressed、客户端不可提交封存字段、独立 validator 覆盖）。G3-2 解析在快照缺少注解 artifact 时 fail closed。
- D-G3-A=a 的 series matrix values 非重归一化值（非 RMA+limma），`analysis_context.normalization="geo_series_matrix_values"` 如实记录。
