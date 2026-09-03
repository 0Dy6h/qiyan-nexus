# PubMed 种子扩展 batch2-5 语料变更补记（记录于 2026-09-03）

## 事实
- batch1 已有独立 changelog（.tmp，344→527，+183）。batch2-5 执行时未留存逐批中间快照，
  本补记按最终态合并记录：语料 527 → 693 pubmed_live（+168）。
- 查询清单：batch2 12 条、batch3 14 条、batch4 26 条、batch5 8 条（3 条 nemolizumab 新主题 +
  5 条马拉色菌/益生菌/MTX/AZA 改写变体）；去重后总表 all.json = 83 条。
- 逐批主题（查询串从 `backend/scripts/pubmed_seed_expansion_batch{2,3,4,5}.json` 现抄，按主题归类）：

### batch2（12 条）
- 系统免疫抑制剂：methotrexate atopic dermatitis；azathioprine atopic dermatitis systemic；cyclosporine atopic dermatitis；cyclosporin atopic dermatitis systemic treatment
- 光疗：narrowband UVB phototherapy atopic dermatitis；NB-UVB atopic dermatitis treatment
- 局部护理：wet wrap therapy atopic dermatitis；wet wrap eczema treatment
- 生物标志物：TARC CCL17 atopic dermatitis biomarker；thymus and activation regulated chemokine eczema
- 雷公藤：Tripterygium wilfordii atopic dermatitis；triptolide eczema dermatitis anti-inflammatory

### batch3（14 条）
- 空气污染：air pollution particulate matter atopic dermatitis exacerbation；PM2.5 PM10 atopic dermatitis epidemiology prevalence mechanism
- 黄芩：baicalin atopic dermatitis anti-inflammatory mechanism；wogonin baicalein eczema dermatitis immunomodulation
- 雷公藤：Tripterygium wilfordii polyglycosides atopic dermatitis clinical efficacy；triptolide eczema dermatitis mechanism safety toxicity
- 甘草：Glycyrrhiza uralensis atopic dermatitis eczema anti-inflammatory；glycyrrhizin liquiritin eczema dermatitis mechanism
- 马拉色菌：Malassezia atopic dermatitis scalp face lesional skin colonization；Malassezia pityrosporum eczema pathogenesis microbiome
- 益生菌：probiotic Lactobacillus Bifidobacterium atopic dermatitis strain specific；Lactobacillus rhamnosus atopic dermatitis prevention treatment randomized
- 依从性：treatment adherence compliance atopic dermatitis patient barriers；topical therapy adherence eczema persistence interventions

### batch4（26 条）
- upadacitinib/dupilumab 头对头与不良反应：upadacitinib dupilumab atopic dermatitis；upadacitinib versus dupilumab eczema；dupilumab conjunctivitis atopic dermatitis；dupilumab ocular adverse events；dupilumab eye facial erythema
- 环孢素：cyclosporine atopic dermatitis efficacy；cyclosporin eczema treatment response；cyclosporine dermatitis safety monitoring renal
- 瘙痒与睡眠：nocturnal pruritus atopic dermatitis sleep；nighttime itch eczema sleep disturbance；circadian pruritus atopic dermatitis
- 黄芩：baicalin dermatitis；Scutellaria baicalensis skin inflammation；wogonin eczema
- 雷公藤：Tripterygium wilfordii dermatitis eczema；tripterygium glycosides dermatitis；triptolide skin inflammation
- 甘草：glycyrrhizin atopic dermatitis；licorice eczema dermatitis；Glycyrrhiza glabra skin inflammation
- 短链脂肪酸：short-chain fatty acids atopic dermatitis；SCFA butyrate eczema inflammation；short-chain fatty acids gut skin axis
- PRO 量表：POEM atopic dermatitis validation；DLQI atopic dermatitis psychometric；patient-reported outcome atopic dermatitis validation

### batch5（8 条）
- nemolizumab（新主题）：nemolizumab atopic dermatitis pruritus；nemolizumab IL-31 receptor eczema clinical trial；nemolizumab dermatitis safety efficacy
- 改写变体：Malassezia atopic dermatitis scalp face lesional；Malassezia pityrosporum eczema colonization pathogenesis；probiotic strain comparison atopic dermatitis Lactobacillus Bifidobacterium；methotrexate atopic dermatitis efficacy safety systemic；azathioprine atopic dermatitis moderate severe treatment

## 指标演进（30 题 top-5，工程侧标注，非真人 domain reviewer）
v2 0.100/0.268（344 语料基线）→ v3 0.28/0.488 → v4 0.32/0.566 → v5 0.34/0.606 →
v6 0.400/0.744（693 语料，零结果 0 题）。

## 诚实边界（不得删）
1. 标签为工程侧协助标注 + 对抗性审查，v2 题集 provenance 仍为 engineering draft 待真人
   domain reviewer 接受；在真人数字出现前不声称检索有效。
2. v3→v6 提升是语料扩展与跨语言术语补充（commit 1624862）的合并效果，未做单因素拆分。
3. batch1 changelog 与 metrics 原件在 .tmp（gitignored），本文件是唯一版本化记录。
