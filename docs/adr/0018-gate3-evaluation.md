# ADR-0018 Gate 3：组学数据验证层评估

- 关联 ADR：[ADR-0018](0018-omics-strategy-platform-contract.md)（Accepted）
- 关联证据等级：[ADR-0015](0015-网络药理学证据分级与指南一致性层.md)（Accepted）
- 日期：2026-08-15
- 执行方：TraeWork
- 状态：已确认（2026-08-16，研究者本人补确认）

---

## 目的

根据 ADR-0018 Gate 3 要求，需完成三件事：
1. 选定一种组学模态
2. 选定一个许可/伦理/授权清楚的数据集
3. 定义最小元数据与 manifest 契约

同时回答 ADR-0018 开放问题 1-3：
- Q1：首个组学验证层应选转录组、蛋白质组还是代谢组？使用哪一份已授权数据？
- Q2：组学数据的最小 manifest/元数据标准由谁定义、如何与 raw-artifact 纪律统一？
- Q3：组学测量证据如何映射到 ADR-0015 的证据等级，避免「有文件即 experimental」？

---

## 一、组学模态选择

### 评估维度

| 维度 | 转录组 | 蛋白质组 | 代谢组 |
|---|---|---|---|
| AD 公开数据集数量 | 多（GEO 10+） | 少 | 极少 |
| 与网络药理学靶点直接关联 | 高（基因表达 = 靶点活性） | 中（蛋白丰度 ≠ 酶活性） | 低（代谢物 ≠ 靶点） |
| 分析管线成熟度 | 高（DEG/limma/DESeq2） | 中（MaxQuant） | 低（XCMS） |
| 平台现有富集分析复用 | 可直接复用 GO/KEGG | 部分复用 | 需重建 |
| 数据格式标准化 | 高（GEO/SRA） | 中 | 低 |
| 许可清晰度 | 高（GEO/NCBI open access） | 中 | 低 |

### 推荐：转录组（Transcriptomics）

**理由**：
1. AD 公开转录组数据集最丰富，可选取人类数据满足 `Homo sapiens` 约束
2. 基因表达差异直接反映靶点活性变化，与网络药理学的「成分→靶点」边映射最直接
3. GO/KEGG 富集分析管线已在平台 mock 层落地，可自然扩展到真实数据
4. GEO/NCBI 的 open access 许可清晰，无伦理灰区
5. 蛋白质组与代谢组在 AD 领域公开数据稀缺，且与靶点-通路映射不直接

---

## 二、数据集评估

### 候选数据集

| 属性 | GSE32924 | GSE224783 | GSE121212 |
|---|---|---|---|
| 标题 | Nonlesional AD skin: differentiation defects & immune abnormalities | AD RNA-seq cohort | AD lesional skin RNA-seq |
| 物种 | Homo sapiens ✅ | Homo sapiens ✅ | Homo sapiens ✅ |
| 平台 | GPL570 Affymetrix HG-U133 Plus 2.0 | GPL16791 Illumina HiSeq 2500 | RNA-seq |
| 类型 | 微阵列 | RNA-seq (125bp PE) | RNA-seq |
| 样本数 | 33（12 ANL + 12 AL + 8 正常 + 1） | 33（11 患者 × 急性/慢性/非皮损） | 21 AD |
| 组织 | 皮肤活检 | 皮肤活检 | 皮肤活检 |
| 公开日期 | 2011-10-13 | 2023 | 2019 |
| 原始数据 | GSE32924_RAW.tar (202.4 Mb CEL) | 可下载 | 可下载 |
| 许可 | GEO open access (NIH/NCBI) | GEO open access | GEO open access |
| 引用 | J Allergy Clin Immunol 2011, PMID: 21388663 | 多篇引用 | 多篇引用 |

### 推荐：GSE32924（首选）

**理由**：
1. **人类数据**：Homo sapiens，满足 ADR-0017 物种约束
2. **对照设计完整**：含正常皮肤对照（n=8），可直接做 AD vs normal 差异分析
3. **配对设计**：12 例患者同时提供非皮损（ANL）和皮损（AL）样本，可区分疾病状态
4. **数据稳定**：Affymetrix 微阵列平台成熟，批次效应小，原始 CEL 文件可下载
5. **广泛引用**：被多篇 AD 转录组研究引用为基准数据集
6. **许可清晰**：GEO/NCBI open access，无伦理灰区
7. **靶点验证直接**：可提取 IL6、STAT3、TNF 等平台 mock 网络中靶点的表达差异，验证「靶点→疾病」边

**局限**：
- 微阵列（非 RNA-seq），覆盖度低于全转录组测序
- 无 TCM 处理条件，只能验证疾病侧靶点，不能验证成分→靶点边
- 2011 年数据，可能不含近年新发现靶点

### 备选：GSE224783（RNA-seq 深度测序）

作为方法学验证的备选，GSE224783 提供 RNA-seq 深度测序数据，可在 GSE32924 验证后用于交叉验证或扩展分析。

---

## 三、Manifest 契约草案

### 设计原则

与现有 raw-artifact provenance 纪律统一（Open Targets 疾病侧 + ChEMBL 成分侧），组学数据 manifest 必须：

1. **服务端 SHA-256 哈希**：原始数据文件（CEL/FASTQ）的 content-addressed 标识
2. **operator-controlled trusted manifest**：由运营者控制的受信任清单，不可由客户端提交
3. **不可变快照**：数据导入后冻结，不可后改
4. **不自动授权**：manifest 只建立数据快照，不翻转 `formal_network_ready`

### 最小元数据字段

```json
{
  "manifest_version": "omics_transcriptomics_v1",
  "dataset": {
    "source": "geo",
    "accession": "GSE32924",
    "title": "Nonlesional atopic dermatitis skin is characterized by broad terminal differentiation defects and variable immune abnormalities",
    "organism": "Homo sapiens",
    "tissue": "skin biopsy (lesional, non-lesional, normal)",
    "platform": "GPL570 [HG-U133_Plus_2] Affymetrix Human Genome U133 Plus 2.0 Array",
    "sample_count": 33,
    "sample_groups": {
      "atopic_lesional": 13,
      "atopic_nonlesional": 12,
      "normal": 8
    },
    "sample_count_note": "GEO 官方文本（2026-08-16 核实）：overall design 为 12 例患者配对 ANL/AL + 正常皮肤 n=8，个别患者仅 1 样本；摘要正文 normal 写作 n=10。以实际下载样本清单（GSM815426 起）为准，契约中的 33/13/12/8 仅为草案估计。",
    "citation": "Suárez-Fariñas M et al. J Allergy Clin Immunol 2011;127(4):954-64. PMID: 21388663",
    "license": "GEO/NCBI Open Access",
    "public_since": "2011-10-13"
  },
  "raw_artifact": {
    "sha256": "<server-computed hash of GSE32924_RAW.tar>",
    "filename": "GSE32924_RAW.tar",
    "size_bytes": 202400000,
    "format": "CEL (Affymetrix)",
    "frozen_at": "<ISO 8601 timestamp>",
    "frozen_by": "<operator identity>",
    "artifact_dir": "<NETWORK_RAW_ARTIFACT_DIR>/omics/"
  },
  "analysis_context": {
    "modality": "transcriptomics",
    "measurement_type": "gene_expression_microarray",
    "comparison": "atopic_lesional vs normal",
    "normalization": "RMA (default for Affymetrix)",
    "deg_method": "limma",
    "fdr_correction": "Benjamini-Hochberg",
    "significance_threshold": 0.05
  },
  "edge_mapping": {
    "network_layer": "disease_target_verification",
    "verified_edges": [],
    "corrected_edges": [],
    "edge_mapping_status": "pending_analysis",
    "mapping_rule": "differentially expressed gene (adj_p < 0.05, |log2FC| > 1) matching canonical symbol in disease_targets lineage"
  },
  "provenance": {
    "import_type": "server_verified_raw_artifact",
    "client_submitted": false,
    "formal_network_ready_impact": false,
    "evidence_level_upgrade": "none (pending analysis)"
  }
}
```

### 与现有 raw-artifact 纪律的统一

| 维度 | Open Targets / ChEMBL | 组学数据（本契约） |
|---|---|---|
| 哈希 | SHA-256 of raw JSON | SHA-256 of raw CEL/FASTQ |
| Manifest | operator-controlled trusted | operator-controlled trusted（同） |
| Parser | 服务端 GraphQL/CSV parser | 服务端 CEL/表达矩阵 parser（需新增） |
| 持久化 | content-addressed | content-addressed（同） |
| 快照冻结 | 不可变 | 不可变（同） |
| formal_network_ready | 不翻转 | 不翻转（同） |
| 证据等级 | 不自动升级 | 不自动升级（同） |

---

## 四、证据等级映射提案（回答开放问题 Q3）

### 问题

ADR-0015 定义了四级证据：`mock_inferred` → `predicted` → `literature_supported` → `experimental`。组学测量数据如何映射？

### 核心原则

**「有文件即 experimental」必须被禁止。** 组学数据文件的存在不等于实验验证。

### 提案：新增 `omics_validated` 等级

在 `literature_supported` 与 `experimental` 之间新增一级：

| level | 含义 | 触发条件 |
|---|---|---|
| `mock_inferred` | 演示/推断，无外部来源 | data_mode=mock（不变） |
| `predicted` | 计算预测靶点 | live, target_evidence_type=predicted（不变） |
| `literature_supported` | 有文献/关系证据 | live, target_evidence_type=mixed 或有 evidence_refs（不变） |
| **`omics_validated`** | **组学测量数据支持靶点差异表达** | **满足下列全部条件** |
| `experimental` | 已知实验活性证据（ChEMBL 等） | live, target_evidence_type=known_activity（不变） |

### `omics_validated` 升级条件（全部满足）

1. **数据来源验证**：原始数据文件已通过 manifest 契约的 SHA-256 哈希 + operator manifest 核验
2. **分析管线确定**：使用确定性分析管线（如 RMA + limma + BH FDR），管线参数在 manifest 中冻结
3. **直接靶点测量**：差异表达基因的 canonical symbol 与网络 lineage 中的靶点 canonical symbol 匹配
4. **统计显著性**：adjusted p-value < 0.05 且 |log2FC| > 1（或等价阈值）
5. **实验条件匹配**：数据来自 AD 相关组织（皮肤/血液），物种为 Homo sapiens
6. **人工确认**：研究者确认该差异表达结果生物学上支持对应网络边

### 不升级的情况

- 仅有数据文件但未完成差异分析 → 维持原等级
- 差异分析完成但靶点不在网络 lineage 中 → 不影响任何边
- 靶点在 lineage 中但 adjusted p-value ≥ 0.05 → 不升级
- 靶点显著差异但研究者判定生物学上不支持该边 → 不升级
- 数据来自非人类物种 → 不升级（违反 ADR-0017 物种约束）

### 与 `formal_network_ready` 的关系

`omics_validated` 等级的出现**不翻转** `formal_network_ready`。`formal_network_ready` 的翻转仍需通过 ADR-0017 定义的科学验证门禁（逐边人工判定 + 双侧 artifact 核验 + 候选装配封存 + 交集存在）。组学验证只是证据来源之一，不是唯一判据。

---

## 五、边映射计划

### GSE32924 可验证的网络边

平台 mock 网络中的靶点：IL6、STAT3、TNF

GSE32924 可验证的映射：

| 网络边 | 验证方式 | 预期结果 |
|---|---|---|
| IL6 → AD | AD 皮损 vs 正常皮肤中 IL6 表达差异 | 预期上调（AD 炎症驱动） |
| STAT3 → AD | AD 皮损 vs 正常皮肤中 STAT3 表达差异 | 预期上调（JAK-STAT 通路激活） |
| TNF → AD | AD 皮损 vs 正常皮肤中 TNF 表达差异 | 预期上调（炎症因子） |

### 不可验证的边

| 网络边 | 原因 | 后续方案 |
|---|---|---|
| 消风散 → IL6 | GSE32924 无 TCM 处理条件 | 需 TCM 处理转录组数据（如二妙丸研究） |
| 消风散 → STAT3 | 同上 | 同上 |
| 消风散 → TNF | 同上 | 同上 |

### 跨步骤依赖声明

Gate 3 的组学验证只覆盖「靶点 → 疾病」边（disease target verification），不覆盖「成分 → 靶点」边（compound target verification）。后者需要 TCM 处理条件的组学数据，属于 Gate 3 后续扩展范围，不在本 Gate 3 范围内。

---

## 六、边界遵守

| 边界 | 遵守情况 |
|---|---|
| 不新增甲状腺病种 | ✅ 仍为特应性皮炎 |
| 不实现对接/MD | ✅ 仅 schema 预留 |
| 不接真实组学数据到默认路径 | ✅ 组学数据走显式 opt-in 验证层 |
| `formal_network_ready` 保持 false | ✅ 组学验证不翻转 readiness |
| 不写代码 | ✅ Gate 3 只做评估与契约定义 |
| 不改 README 产品边界 | ✅ 未修改 |

---

## 七、需要研究者确认的事项

1. **模态选择**：确认转录组（Transcriptomics）作为首个组学验证模态
2. **数据集选择**：确认 GSE32924 作为首个验证数据集
3. **证据等级提案**：确认新增 `omics_validated` 等级及其升级条件
4. **边映射范围**：确认 Gate 3 只覆盖 disease target verification（靶点→疾病边），compound target verification 留后续

---

*本评估由 TraeWork 根据 ADR-0018 Gate 3 要求编制，已于 2026-08-16 经研究者本人确认通过。*
