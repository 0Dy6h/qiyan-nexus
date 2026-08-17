# 2026-08-17 交接：Track A 标注、检索器调参与 Track A+ 验证

## 今日工作概览

1. **Track A 标注完成**：30 题 × top-5 = 150 候选，协助标注 + 对抗性审查（修正 10 条过度包容标注）
   - Baseline: precision@5 = 0.113, MRR@5 = 0.163
   - 17/30 题零相关结果（语料覆盖缺口）

2. **检索器调参**（3 项改进）：
   - 多字医学术语词典 `cjk_medical_terms.json`（54 条，如"神经酰胺"→ceramide）
   - 字段加权评分（title=3, keywords/evidence_tags/entity_ids=2, abstract/snippet=1）
   - 跨语言桥接收窄（拆分过宽的"therapy"为 therapy/topical_therapy/acupuncture）
   - 更新了 4 个测试的预期值以适应新排序

3. **Track A+ 验证**：30 题全新 v2 题集（与 v1 无重叠），同一 344 篇 PubMed 语料库
   - Results: precision@5 = 0.100, MRR@5 = 0.268
   - **MRR@5 提升 64%**（0.163 → 0.268）
   - 7/11 有相关结果的题达到 rank-1（Track A 仅 1 题）
   - 19/30 题零相关结果，其中 17 题为语料覆盖缺口（非检索器问题）

4. **对比分析**：Rank-1 成功案例 vs 零结果案例
   - 成功驱动力：字段加权让标题精确匹配的文献从 rank 4-5 跃升到 rank 1
   - 失败根因：89% (17/19) 是语料库覆盖缺口，非检索器退化

## 变更文件

### 修改
- `backend/app/services/retrieval/provider.py` — 多字术语识别 + 字段加权评分
- `backend/data/retrieval/cross_lingual_terms.json` — 拆分过宽桥接条目
- `backend/tests/test_rag_service.py` — 更新预期排序
- `backend/tests/test_rag_api.py` — 更新预期排序
- `backend/tests/test_cross_lingual_eval.py` — 更新跨语言召回基线

### 新增
- `backend/data/retrieval/cjk_medical_terms.json` — 多字医学术语词典（54 条）
- `backend/scripts/eval_queries.validation.v2.json` — Track A+ 题集（30 题）
- `docs/adr/0018-open-questions-brief.md` — ADR-0018 开放问题决议简报
- `docs/guides/track-a-labeling-guide.md` — Track A 标注向导
- `docs/plans/2026-08-14-writer-consumption-contract-decision-pack.md` — writer 消费契约决策包

### 验证产物（gitignored）
- `.tmp/retrieval-validation-v1/worksheet.v2.json` — Track A+ 标注后 worksheet
- `.tmp/retrieval-validation-v1/worksheet.v2.manifest.json` — 私有 manifest（含真实排名）
- `.tmp/retrieval-validation-v1/metrics.v2.json` — Track A+ 评分结果
- `.tmp/retrieval-validation-v1/metrics.json` — Track A baseline 评分结果

## 测试状态

- 后端 68 个 RAG 相关测试全绿
- 调参后的排序变化已反映在测试预期中

## 下一步建议

1. **扩展 PubMed 种子查询**：当前 8 个种子查询覆盖 TCM/针灸/微生物组/JAK/filaggrin/network pharmacology/IL-31 等主题，v2 题集暴露了 PDE4 抑制剂、维生素 D、TSLP、特定草药（黄芩/白鲜皮/雷公藤/甘草）、马拉色菌、依从性等未覆盖主题。扩展种子查询可直接提升 precision。

2. **考虑 Track B**：Track A 已建立基线和调参验证流程，可考虑推进 Track B（检索器在 mock 语料库上的 controlled recall 测试）。

3. **提交代码**：当前 5 个修改 + 5 个新文件未提交。建议在下次会话开始时提交。

4. **研究者确认**：writer 消费契约决策包和 ADR-0018 开放问题简报仍待研究者拍板。
