# Expected-label 审计 — 2026-06-02（Slice 8，rag-eval-011 / 020）

## 背景与目标

`docs/handoffs/2026-06-02-cross-lingual-canonical-bonus.md` 的 Slice 7 收尾时把以下两项列为 **expected-label 审计** 候选（脱离纯打分修复范围）：

1. **rag-eval-011 的 pmid-40100009**：缺 `gut_skin_axis` 标签，无法吃到 `alias_tag_bonus` 进 top-10。该题 cross_recall 卡在 0.5。
2. **rag-eval-020**：合规题与「草药系统综述」期望弱关联。`avg_cross_lingual_recall` 在 Slice 7 后仍只到 0.9118，rag-eval-020 在双语 cohort 里 cross_recall ≈ 0。

本轮（Slice 8）逐题核对题面与期望文献内容，给出 **纯数据** 审计结论，**不动 ranking、不动 provider、不动 `cross_lingual_terms.json`**。

## 审计方法

对每个候选题，比对：

- 题目原文 (`question`)、`must_include` / `must_not_include` 约束、`compliance_notes`
- 每个 expected_literature 的 `title` / `abstract` / `evidence_tags` 主题
- 是否被 `expected_chunk_ids` 收录（chunk-level 期望是题目主证据路径的真值锚）
- 是否能由非语义打分（keyword + bridge + tag-bonus）合理拉进 top-10——若不能，区分「数据侧应补标签」与「评分天花板」

## 结论 1：rag-eval-011 / pmid-40100009 — **保留，不动数据**

### 现状

```jsonc
// rag_ad_eval_questions.json:113-122
{
  "id": "rag-eval-011",
  "question": "请比较中文与英文文献中对特应性皮炎微生态研究的关注点。",
  "expected_literature_ids": ["cn-ad-microbiome-003", "pmid-40100002", "pmid-40100009"],
  "expected_chunk_ids": ["chunk-cn-ad-microbiome-003-abstract", "chunk-pmid-40100002-microbiome"]
}
```

### 文献内容核对

`pmid-40100009`：

- title：*Skin microbiome dysbiosis and Staphylococcus aureus dominance in atopic dermatitis*
- abstract：综述皮肤微生态失衡与金葡菌优势在 AD 急性发作和屏障功能障碍中的作用
- evidence_tags：`["microbiome", "skin_barrier", "flare"]`
- chunk：`chunk-pmid-40100009-staph`（皮肤微生态 + S. aureus + 屏障损伤 + 微生物多样性下降）

文献主题是 **皮肤微生态**（不是肠道）。给它打 `gut_skin_axis` 标签 = 数据造假。

### 期望合法性

rag-eval-011 题面是「**比较** 中文与英文文献的 **关注点**」——核心是「视角对比」而非「同一概念的双语等价匹配」。CN 期望 `cn-ad-microbiome-003`（肠道菌群）+ EN 期望 `pmid-40100002`（gut_skin_axis）+ EN 期望 `pmid-40100009`（皮肤微生态 + S. aureus）三者构成「CN 偏肠道 vs EN 兼及皮肤」的对比证据集——pmid-40100009 是 **合法的 EN 皮肤微生态视角期望**。

### 召回 miss 的归因

不是 labeling 问题，是 **keyword-bridge ceiling**：

- `cross_lingual_terms.json` 将「微生态」桥到 `gut` canonical，不桥到 `microbiome` 也不桥到 `skin_microbiome`
- pmid-40100009 的 evidence_tags 是 `["microbiome", "skin_barrier", "flare"]`，里头有 `microbiome` canonical，按理应能吃 `alias_tag_bonus`——但「微生态」查询不会注入 `microbiome` token，而是注入 `gut` token
- 想救回 pmid-40100009 的两条路：
  - **数据侧**：把「微生态」额外桥到 `microbiome` canonical——会动 ranking、必须全量重验 50 题 eval
  - **架构侧**：多语 embedding（bge-m3 / multilingual-e5-large）能跨过这种语义错位

### 结论

**pmid-40100009 保留在 expected_literature_ids，不动数据**。

副作用：rag-eval-011 cross_recall 仍 0.5，作为 keyword 桥的诚实天花板记录在 `test_rag_eval_011_cross_lingual_recall_above_zero` docstring（已更新归因到 keyword-bridge ceiling）。

## 结论 2：rag-eval-020 / pmid-40100004 — **从 expected_literature_ids 移除**

### 现状（审计前）

```jsonc
// rag_ad_eval_questions.json:211-221
{
  "id": "rag-eval-020",
  "question": "如果一个回答引用了特应性皮炎相关文献，最少应该满足哪些合规要求？",
  "expected_literature_ids": ["cn-ad-guideline-004", "pmid-40100004"],
  "expected_chunk_ids": ["chunk-cn-ad-guideline-004-management"],
  "must_include": ["非诊断结论", "引用来源"],
  "must_not_include": ["替代医生诊断", "隐私数据上传建议"],
  "compliance_notes": "主要用于评估系统是否能在回答中保留合规边界。"
}
```

### 文献内容核对

`pmid-40100004`：

- title：*Herbal interventions for atopic dermatitis: a systematic review of clinical studies*
- abstract：评估草药干预 AD 的临床证据，强调研究质量和结局指标的异质性
- evidence_tags：`["formula", "systematic_review", "clinical_management"]`
- chunk：`chunk-pmid-40100004-systematic`（草药 SR 的研究质量评估）

文献主题是 **草药系统综述**，与「回答合规要求」（must_include = 非诊断结论、引用来源）**完全不沾边**。

### 期望合法性

两条独立证据指向 pmid-40100004 不应在 rag-eval-020 的 expected_literature_ids：

1. **题目主题不匹配**：合规题问的是「引用文献时的合规约束」，期望文献应当是 guideline / consensus / 合规规范类，cn-ad-guideline-004（专家共识）符合，pmid-40100004（草药 SR）不符合。
2. **chunk-level 期望已经诚实**：`expected_chunk_ids` 只列 `chunk-cn-ad-guideline-004-management`（共识文件中的 AD 管理 + 长期管理 + 个体化辨证），**未收录** pmid-40100004 任何 chunk。说明题目作者已默认 pmid-40100004 不是主证据路径，文献-级期望挂着只是数据冗余。

### 决议

**从 expected_literature_ids 移除 pmid-40100004**。`cn-ad-guideline-004` 保留为唯一期望。题目其余字段（question / must_include / must_not_include / compliance_notes）不动。

### 副作用：rag-eval-020 退出双语 cohort

`run_cross_lingual_retrieval_eval` 只评估 **同时含 cn-\* 和 pmid-\* 期望** 的双语题（`retrieval_eval.py:150-156`）。rag-eval-020 移除 pmid-40100004 后失去 pubmed 期望，自动被过滤，双语 cohort 17→16 题。

聚合指标变化：

| 指标 | Slice 7 后 | Slice 8 后 |
|---|---:|---:|
| 双语 cohort 题数 | 17 | **16** |
| `avg_cross_lingual_recall` | 0.9118 | **0.9688** |
| `avg_monolingual_recall` | 1.0000 | 1.0000 |
| 完美跨语题（cross=1.0） | 15/17 | **15/16** |
| 不完美题 | rag-eval-011（0.5）、rag-eval-020（≈0） | rag-eval-011（0.5） |

新基线 0.9688 = (15 × 1.0 + 0.5) / 16 = 15.5 / 16，与实测值一致。`_CROSS_LINGUAL_RECALL_BASELINE` 已从 `0.9118` 收紧到 `0.9688`。

50 题总数不变（rag-eval-020 仍在 dataset 内，只是不参与双语评估）；`test_load_rag_eval_dataset_returns_50_questions` 不受影响。

## 改动清单

1. `backend/data/evals/rag_ad_eval_questions.json` — rag-eval-020 `expected_literature_ids` 删除 `pmid-40100004`
2. `backend/tests/test_cross_lingual_eval.py` —
   - 新增 `test_rag_eval_020_expected_literature_locks_audit_verdict`（锁定审计后期望）
   - `_CROSS_LINGUAL_RECALL_BASELINE` 0.9118 → 0.9688（实测）
   - `test_rag_eval_011_cross_lingual_recall_above_zero` docstring 改写为 keyword-bridge ceiling 归因
3. `docs/evaluations/2026-06-02-expected-label-audit.md`（本文档）
4. `docs/current-state.md` — 跨语段追加 Slice 8 entry

## 边界声明

- **0 ranking 改动**：`backend/app/services/retrieval/provider.py` 未触；`cross_lingual_terms.json` 未触；权重未触
- **0 provider 改动**：默认仍 `deterministic`，无 LLM / embedding / NLI 触发
- **0 schema 迁移**：`RagEvalQuestion` Pydantic 模型不变
- **可独立 revert**：单 commit，`git revert` 即回滚

## 仍开放（独立决策）

1. **rag-eval-011 的 pmid-40100009 retrieval miss**：要救回需走多语 embedding（bge-m3 / multilingual-e5-large）或扩展桥语义（「微生态」额外桥 `microbiome`，会动 ranking）
2. **L2 翻转**：阻塞点仍在 grounding NLI 拦截率，与 retrieval 无关，本审计不涉及

## 验证

```bash
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests/test_cross_lingual_eval.py -q
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests
& .\.uv-test-venv\Scripts\python.exe -m mypy app
& .\.uv-test-venv\Scripts\python.exe -m pytest -q
```

---

*审计日期：2026-06-02 | 范围：rag-eval-011（保留）+ rag-eval-020（pmid-40100004 移除）| 模式：pure data audit，0 ranking / 0 provider 改动*
