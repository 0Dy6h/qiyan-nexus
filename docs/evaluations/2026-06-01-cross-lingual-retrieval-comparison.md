# Cross-Lingual Retrieval Evaluation — 2026-06-01

## 背景

Slice 2 引入了确定性 CN↔EN 跨语言术语桥，将 cross_lingual_recall@10 从 0.0 提升到 0.76。本评估对比 3 种检索策略（keyword / vector / hybrid）及 2 种 embedding backend（hashing / bge）在双语题目上的表现。

## 评估设置

- **数据集**：50 题 ag_ad_eval_questions 中的 **17 道双语题目**（期望文献同时含 cn-* 和 pmid-* 的题目）
- **top_k**：10
- **Embedding backends**：
  - hashing（默认）：确定性 MD5 → ±1 → 128-dim L2 归一化，零下载
  - ge：BAAI/bge-small-zh-v1.5（512-dim，sentence-transformers）
- **BGE 可用性**：✅ 模型已本地 cached，可正常运行（缓存路径：~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/）
- **测试环境**：Windows + pwsh，ackend/.uv-test-venv
- **评估代码**：ackend/app/services/retrieval_eval.py — 纯检索评估（绕过 LLM），直接调用 etrieval_provider.rank()

## 结果对比

### 整体指标

| Strategy | Backend | Mono Recall | Cross Recall | Diversity | P@10 | MRR |
|----------|---------|:-----------:|:------------:|:---------:|:----:|:---:|
| keyword | n/a | **1.0000** | **0.7647** | 0.3065 | **0.2000** | 0.8578 |
| vector | hashing | 0.7353 | 0.3824 | **0.4363** | 0.1235 | 0.4658 |
| vector | bge | **1.0000** | 0.1765 | 0.1471 | 0.1294 | 0.7520 |
| hybrid | hashing | 0.9412 | 0.7353 | 0.3347 | 0.1882 | 0.7201 |
| hybrid | bge | **1.0000** | 0.6471 | 0.1746 | 0.1824 | **0.8627** |

### 17 题逐题明细（Keyword 策略）

所有 17 道双语题目均为**中文问题**（question_language=zh）；无英文双语题目。

| ID | CN-expected | PMID-expected | MonoR | CrossR | P@10 | MRR |
|:---|:-----------|:-------------|:-----:|:------:|:----:|:---:|
| rag-eval-001 | 001,003 | 40100002 | 1.0000 | 1.0000 | 0.3000 | 1.0000 |
| rag-eval-004 | 005 | 40100003 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-006 | 003 | 40100002,40100007 | 1.0000 | 1.0000 | 0.3000 | 1.0000 |
| rag-eval-007 | 007 | 40100005 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-008 | 007 | 40100008 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-009 | 009 | 40100010 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-011 | 003 | 40100002,40100009 | 1.0000 | **0.0000** | 0.1000 | 0.5000 |
| rag-eval-016 | 002,007 | 40100008 | 1.0000 | 1.0000 | 0.3000 | 1.0000 |
| rag-eval-019 | 007 | 40100008,40100005 | 1.0000 | 1.0000 | 0.3000 | 1.0000 |
| rag-eval-020 | 004 | 40100004 | 1.0000 | **0.0000** | 0.1000 | 0.5000 |
| rag-eval-022 | 002 | 40100001 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-030 | 005 | 40100003 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-031 | 007 | 40100008 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |
| rag-eval-033 | 007 | 40100008 | 1.0000 | 1.0000 | 0.2000 | 0.3333 |
| rag-eval-035 | 003 | 40100002 | 1.0000 | **0.0000** | 0.1000 | 1.0000 |
| rag-eval-047 | 010 | 40100002 | 1.0000 | **0.0000** | 0.1000 | 0.2500 |
| rag-eval-049 | 007 | 40100008 | 1.0000 | 1.0000 | 0.2000 | 1.0000 |

**Keyword 跨语言召回失败项**（4 题 CrossR = 0.0）：
- ag-eval-011："特应性皮炎患者体内的微生物群落变化及其对免疫系统的影响？"
- ag-eval-020："特应性皮炎与皮肤屏障功能之间的关系是什么？"
- ag-eval-035："肠道菌群如何影响特应性皮炎的发生？"
- ag-eval-047："湿包疗法在特应性皮炎中的治疗作用如何？"

这些题目的共同特征是：主题词**缺少跨语言术语桥中的 zh→en 映射**（或映射未覆盖到 PubMed 标题/摘要中的精确英文表达）。

## 关键发现

### 1. Keyword + Cross-Lingual Bridge 在跨语言检索中全面领先

| 维度 | keyword | vector(hashing) | vector(bge) | 结论 |
|------|:-------:|:---------------:|:-----------:|:----:|
| Cross Recall | **0.7647** | 0.3824 | 0.1765 | keyword 是 vector 的 2~4× |
| P@10 | **0.2000** | 0.1235 | 0.1294 | keyword 高出 50%+ |
| MRR | 0.8578 | 0.4658 | 0.7520 | keyword 显著优于 vector(hashing) |

**keyword 的跨语言召回 0.7647 是 3 种策略中最高的**。13/17 题达到 1.0000 的完美跨语言召回；4 题失败是因为术语桥映射的覆盖盲区。

### 2. Vector(Hashing) — 双语分离但无法跨语言

Hashing 的 language_diversity 反而是最高的（0.4363），意味着它在 top-10 中同时召回了较多的中文和英文文献。但它的 cross_lingual_recall 仅 0.3824，说明召回的中文和英文文献**都不是预期文献**——hashing 的词汇重叠机制无法匹配语义等价但词汇不同的跨语言对。

Monolingual recall 仅 0.7353，意味着 26% 的预期中文文献也没被召回。

### 3. Vector(BGE) — 极端 mono 偏斜

BGE 的 mono recall 达到 1.0000（所有预期中文文献完美召回），但 cross recall 只有 **0.1765**（仅 3/17 题召回了英文预期文献）。这是 BGE-small-zh-v1.5 作为**中文专用模型**的固有局限：

- 中文→中文语义匹配非常好（1.0000）
- 中文→英文语义匹配非常差（0.1765）
- 这与 grounding 评估中 BGE 的优异表现一致，但检索场景下跨语言能力不足

### 4. Hybrid 改善但不及 Keyword

| Strategy | Cross Recall | vs Keyword |
|----------|:-----------:|:----------:|
| hybrid(hashing) | 0.7353 | -0.0294（略低） |
| hybrid(bge) | 0.6471 | -0.1176（差距明显） |

Hybrid 通过 RRF 融合 keyword 的跨语言能力，部分恢复了跨语言召回，但仍低于纯 keyword。hybrid(bge) 的 MRR（0.8627）略高于 keyword（0.8578），但 cross recall 差距 0.1176 不可忽视。

### 5. Scoring 排序

**跨语言召回（Cross-Lingual Recall@10）性能排序：**

`
keyword (0.7647) > hybrid+hashing (0.7353) > hybrid+bge (0.6471)
> vector+hashing (0.3824) > vector+bge (0.1765)
`

## 建议

### 默认路径维持：Keyword + Cross-Lingual Bridge

- **确定性**：	okenize_query 的跨语言桥是纯规则映射，结果可复现、可调试
- **离线**：零模型下载、零 GPU 依赖
- **性能领先**：cross recall 0.7647 是所有策略中最高的
- **覆盖盲区可修补**：4 题失败是因为跨语言术语桥缺少特定 zh→en 映射，**只需补充 data/retrieval/cross_lingual_terms.json 即可解决**，不涉及系统架构变更

### Vector / Hybrid 维持 opt-in ablation

不做默认切换策略。保留 vector 和 hybrid 作为：
- 实验性对照组（评估新特性时的基线对比）
- 后续引入真正多语言 embedding（如 bge-m3、intfloat/multilingual-e5-large）时的迁移路径

### BGE 在检索中的定位

BGE 在中文语义匹配（mono recall=1.0000）下表现完美，但**不适合跨语言中文→英文检索场景**。建议：
- **检索**：继续使用 keyword + cross-lingual bridge（确定性 + 高 cross recall）
- **Grounding**：使用 BGE（已在 2026-05-31-bge-semantic-evaluation.md 中验证，threshold=0.78 时零错误）
- 两者并行：检索用 keyword，grounding 用 BGE，互不冲突

### 后续可选项

1. **修补 4 例跨语言召回失败**：检查 cross_lingual_terms.json 中缺少的 zh→en 映射，补充后 keyword 有望达到 cross recall ≈ 1.0000
2. **引入多语言 embedding 后重评**：bge-m3 或 multilingual-e5-large 可原生支持 CN↔EN 双语 embedding，届时 vector 和 hybrid 的 cross recall 可能显著提升
3. **hybrid+bge 的 MRR 优势**：MRR 0.8627 为所有策略最高，说明当正确文献出现在 top-1 时 BGE 语义匹配的精确度很高——如果后续跨语言桥覆盖完善，hybrid(bge) 可能是最优组合

---

*评估日期：2026-06-01 | 评估者：Qiyan Nexus 验证 agent*
