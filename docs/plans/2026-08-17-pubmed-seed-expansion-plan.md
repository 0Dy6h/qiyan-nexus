# PubMed 种子查询扩展规划（2026-08-17）

- 规划人：蒜香（依据 TraeWork 2026-08-17 建议与 Track A+ 缺口分析）
- 执行方：TraeWork（待派单）
- 背景：Track A+ 分析显示 19/30 零结果题中 17 题为**语料覆盖缺口**（非检索器退化）。当前 8 个种子查询覆盖 TCM/针灸/微生物组/JAK/filaggrin/network pharmacology/IL-31 等主题。排序能力已优化（MRR@5 0.268），**瓶颈在语料覆盖**。
- 参考：`.tmp/retrieval-validation-v1/metrics.v2.json` 逐题零结果原因。

---

## 优先级与分批

### 第一批：高优先级（直接对应 v2 题集错题，见效最快）

| # | 主题 | 示例种子查询 | 对应 v2 错题 |
|---|---|---|---|
| 1 | PDE4 抑制剂 | PDE4 inhibitor atopic dermatitis crisaborole | PDE4 相关题 |
| 2 | TSLP | TSLP atopic dermatitis [MeSH:Thymic Stromal Lymphopoietin] | TSLP 相关题 |
| 3 | 维生素 D | vitamin D atopic dermatitis [MeSH:Vitamin D] | 维D 相关题 |
| 4 | 黄芩 | Scutellaria baicalensis eczema atopic dermatitis | 草药题 |
| 5 | 白鲜皮 | Cortex Dictamni OR dictamnine atopic dermatitis | 草药题 |
| 6 | 马拉色菌 | Malassezia atopic dermatitis [MeSH:Malassezia] | 微生物题 |

### 第二批：中优先级（临床常用、relevance 高）

| # | 主题 | 示例种子查询 | 对应 v2 错题 |
|---|---|---|---|
| 7 | MTX / 硫唑嘌呤 | methotrexate atopic dermatitis OR azathioprine | 药物题 |
| 8 | 环孢素 A | cyclosporine atopic dermatitis | 药物题 |
| 9 | NB-UVB 光疗 | narrowband UVB phototherapy atopic dermatitis | 治疗题 |
| 10 | 湿包疗法 | wet wrap therapy atopic dermatitis | 治疗题 |
| 11 | TARC/CCL17 | TARC CCL17 atopic dermatitis biomarker | 生物标志物题 |
| 12 | 雷公藤 | Tripterygium wilfordii atopic dermatitis | 草药题 |

### 第三批：中低优先级（机制/共病/患者维度，可后置）

| # | 主题 | 示例种子查询 |
|---|---|---|
| 13 | 心理应激 / HPA 轴 | psychological stress HPA axis atopic dermatitis itch |
| 14 | 夜间瘙痒 / 睡眠 | nocturnal pruritus sleep atopic dermatitis |
| 15 | 甘草 | Glycyrrhiza atopic dermatitis |
| 16 | 益生菌菌株特异性 | probiotic strain specific atopic dermatitis RCT |
| 17 | SCFAs | short chain fatty acids atopic dermatitis microbiome |
| 18 | 特应性 march | atopic march [MeSH] |
| 19 | 共患病（心血管/精神） | atopic dermatitis cardiovascular comorbidity OR depression OR anxiety |
| 20 | PROM 验证 | POEM DLIM atopic dermatitis validation |
| 21 | 治疗依从性 | treatment adherence atopic dermatitis |

---

## 执行步骤（TraeWork 接单后）

1. 按上面的分批，对每批写种子查询 → 跑 PubMed E-utilities 拉取 → 追加进语料库（保持 344 篇基线不变，新增部分单独记账）。
2. 每批完成后用 **v2 题集**（30 题）重跑 metrics，记录 precision@5 / MRR@5 变化。
3. 目标：v2 题集 precision@5 从 0.100 显著提升（覆盖缺口下降），零结果题数从 19 降到个位数。
4. 若某主题新增语料对现有指标无改善，标注「低收益」并考虑跳过，避免语料无脑膨胀。

## 验收标准

- 全部批次完成后：v2 题集 precision@5 ≥ 0.20，零结果题 ≤ 5（或给出逐题理由）。
- 后端测试保持全绿（68 个 RAG 测试）。
- 语料库变更记录在案（数量、主题、来源批次），不破坏既有 344 篇基线可复现性。