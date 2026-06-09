# PDF Extractor Comparison Results

Generated: 2026-06-05T20:36:46+0800

## Environment

| Package | Version |
|---|---|
| pypdf | 6.12.2 |
| pdfplumber | 0.11.9 |
| pdfminer.six | 20251230 |

## Samples

| Sample | Source File | Expectation |
|---|---|---|
| cn-ad-formula-002 | 中医辨证治疗异位性皮炎临床观察_周海啸.pdf | known embedded-font numeric garbling; current path should warn |
| cn-ad-pruritus-005 | 中药健脾止痒颗粒合铍宝消炎癣湿药膏治疗特应性皮炎疗效分析_杨瑛 - 副本.pdf | clean text-layer sample |
| cn-ad-barrier-006 | 健脾养血祛风法治疗特应性皮炎临床疗效及对皮肤屏障功能的影响_杨雪松.pdf | clean text-layer sample |
| cn-ad-external-008 | 除湿糊剂治疗特应性皮炎的实验与临床观察_王琼 - 副本.pdf | clean text-layer sample |

## Metrics

| Sample | Extractor | Chars | NUL | NUL % | CJK % | CID | Terms | Current warning | Flags | ms |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| cn-ad-formula-002 | pypdf_full | 6249 | 805 | 12.88 | 42.87 | 0 | 4 | yes | nul_warning | 214.94 |
| cn-ad-formula-002 | pypdf_current_middle_lines | 4084 | 596 | 14.59 | 40.52 | 0 | 4 | yes | nul_warning | 126.84 |
| cn-ad-formula-002 | pdfplumber_default | 4431 | 805 | 18.17 | 60.46 | 0 | 4 | yes | nul_warning | 524.59 |
| cn-ad-formula-002 | pdfplumber_layout | 9858 | 805 | 8.17 | 27.18 | 0 | 4 | yes | nul_warning | 412.65 |
| cn-ad-pruritus-005 | pypdf_full | 8681 | 0 | 0.00 | 35.42 | 0 | 6 | no | none | 199.08 |
| cn-ad-pruritus-005 | pypdf_current_middle_lines | 5423 | 0 | 0.00 | 47.02 | 0 | 6 | no | none | 221.95 |
| cn-ad-pruritus-005 | pdfplumber_default | 7359 | 0 | 0.00 | 41.79 | 0 | 6 | no | none | 646.33 |
| cn-ad-pruritus-005 | pdfplumber_layout | 13353 | 0 | 0.00 | 23.03 | 0 | 6 | no | none | 635.20 |
| cn-ad-barrier-006 | pypdf_full | 9414 | 0 | 0.00 | 33.55 | 0 | 7 | no | none | 238.40 |
| cn-ad-barrier-006 | pypdf_current_middle_lines | 6871 | 0 | 0.00 | 36.04 | 0 | 6 | no | none | 263.56 |
| cn-ad-barrier-006 | pdfplumber_default | 10242 | 0 | 0.00 | 30.83 | 0 | 7 | no | none | 792.38 |
| cn-ad-barrier-006 | pdfplumber_layout | 25313 | 0 | 0.00 | 12.48 | 0 | 7 | no | low_cjk_ratio | 811.52 |
| cn-ad-external-008 | pypdf_full | 6750 | 0 | 0.00 | 46.47 | 0 | 6 | no | none | 147.06 |
| cn-ad-external-008 | pypdf_current_middle_lines | 4746 | 0 | 0.00 | 48.06 | 0 | 4 | no | none | 178.05 |
| cn-ad-external-008 | pdfplumber_default | 5312 | 0 | 0.00 | 59.05 | 0 | 6 | no | none | 449.10 |
| cn-ad-external-008 | pdfplumber_layout | 10926 | 0 | 0.00 | 28.71 | 0 | 6 | no | none | 434.62 |

## Short Preview Samples

Short preview samples are intentionally capped to avoid committing article-scale extracted text.

| Sample | Extractor | Preview sample | Digest |
|---|---|---|---|
| cn-ad-formula-002 | pypdf_full | 中国 中医 药信 息 杂志 [NUL][NUL][NUL][NUL]年… | 859983f737e0 |
| cn-ad-formula-002 | pypdf_current_middle_lines | 病 程 长 、 难 治疗 、 易 复 发等特 点 。 我们 于 [NU… | a2b1e2fa4da2 |
| cn-ad-formula-002 | pdfplumber_default | 中国中医药信息杂志 [NUL][NUL][NUL][NUL]年第[NU… | a5168426558e |
| cn-ad-formula-002 | pdfplumber_layout | 中国中医药信息杂志 [NUL][NUL][NUL][NUL]年第[NU… | 4c11ce7551f5 |
| cn-ad-pruritus-005 | pypdf_full | 中 国 中 西 医 结 合 皮 肤 性 病 学 杂 志 2007 年 … | 199001d8080d |
| cn-ad-pruritus-005 | pypdf_current_middle_lines | medicinalherbTripterygiumwilfordiiH… | 5742a28e856a |
| cn-ad-pruritus-005 | pdfplumber_default | 中国中西医结合皮肤性病学杂志2007年第6卷第3期 ·135· ·论著… | e6ec483464c6 |
| cn-ad-pruritus-005 | pdfplumber_layout | 中国中西医结合皮肤性病学杂志2007年第6卷第3期 ·135· ·论著… | 78981a75f19e |
| cn-ad-barrier-006 | pypdf_full | 第 32卷第 3期 2009年 6月 云南中医学院学报 Ｊｏｕｒｎａｌ… | 0e4b39382b98 |
| cn-ad-barrier-006 | pypdf_current_middle_lines | 摘 要：目的：研究健脾养血祛风法治疗特应性皮炎的临床疗效及对皮肤屏障功… | b7e980a778aa |
| cn-ad-barrier-006 | pdfplumber_default | DOI:10．19288／j．cnki．issn．1000—2723．… | 4963911eb262 |
| cn-ad-barrier-006 | pdfplumber_layout | DOI:10．19288／j．cnki．issn．1000—2723．… | 2b402b8ec540 |
| cn-ad-external-008 | pypdf_full | 特应性皮炎 (AD) 是一种与遗传过敏素质有关的皮肤炎症性 疾病。表现… | d48a8d2b5937 |
| cn-ad-external-008 | pypdf_current_middle_lines | 动物部提供。 1.1.2 主 要 药 品 及 试 剂 : 除 湿 糊 … | 98bef038d35c |
| cn-ad-external-008 | pdfplumber_default | 王 琼 除湿糊剂治疗特应性皮炎的实验与临床观察 ·1399· 除湿糊剂… | 985f4f2cd67d |
| cn-ad-external-008 | pdfplumber_layout | 王 琼 除湿糊剂治疗特应性皮炎的实验与临床观察 ·1399· 除湿糊剂… | cdad5facfaab |
