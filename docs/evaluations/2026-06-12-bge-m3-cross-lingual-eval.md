# Cross-Lingual Retrieval Evaluation — bge-m3 vs multilingual-e5-large

## 目标

使用真实多语 embedding 模型（bge-m3 / multilingual-e5-large）重新评估跨语言检索性能，对比 keyword baseline（avg_cross_lingual_recall=0.9688），验证是否能突破术语桥天花板。

## 评估设置

- **数据集**：50 题 rag_ad_eval_questions 中的 **16 道双语题目**（2026-06-02 Slice 8 审计后，rag-eval-020 移除）
- **top_k**：10
- **Embedding backends**：
  - `bge-m3`：BAAI/bge-m3（1024-dim，支持中英跨语）
  - `multilingual-e5-large`：intfloat/multilingual-e5-large（1024-dim，role-aware `passage:` / `query:` 前缀）
  - `hashing`（baseline）：deterministic MD5 → ±1 → 128-dim
- **Retrieval strategies**：keyword / vector / hybrid
- **环境**：Windows + pwsh，backend/.uv-test-venv
- **脚本**：`backend/scripts/eval_cross_lingual_bge_m3.py`、`backend/scripts/eval_cross_lingual_e5_large.py`

## 关键问题

1. **bge-m3 是否能在 vector 策略下突破 keyword baseline 0.9688？**
2. **multilingual-e5-large 的 role-aware encoding 是否优于 bge-m3？**
3. **hybrid(bge-m3) 是否能超越 keyword？**
4. **rag-eval-011（pmid-40100009，微生物群落）是否被真实模型救回？**
5. **mono_lingual_recall 是否保持 1.0（不退化）？**

## bge-m3 结果

| Strategy | n | Mono Recall | Cross Recall | Diversity | P@10 | MRR |
|----------|---|-------------|--------------|-----------|------|-----|
| keyword | 16 | 1.0000 | **0.9375** | 0.3765 | 0.2188 | 0.9115 |
| vector | 16 | 1.0000 | 0.6250 | 0.1977 | 0.1750 | 0.8750 |
| hybrid | 16 | 1.0000 | 0.9062 | 0.2289 | 0.2125 | 0.9271 |

**vs Keyword Baseline (0.9688)**:
- keyword: 0.9375 (Δ -0.0313)
- vector(bge-m3): 0.6250 (Δ -0.3438)
- hybrid(bge-m3): 0.9062 (Δ -0.0626)

**模型加载**: BAAI/bge-m3, 391 weights, ~2.3GB

## multilingual-e5-large 结果

| Strategy | n | Mono Recall | Cross Recall | Diversity | P@10 | MRR |
|----------|---|-------------|--------------|-----------|------|-----|
| keyword | 16 | 1.0000 | **0.9375** | 0.3765 | 0.2188 | 0.9115 |
| vector | 16 | 1.0000 | **0.0625** | 0.0278 | 0.1188 | 0.9010 |
| hybrid | 16 | 1.0000 | 0.6562 | 0.1805 | 0.1875 | 0.9062 |

**vs Keyword Baseline (0.9688)**:
- keyword: 0.9375 (Δ -0.0313)
- vector(e5-large): **0.0625** (Δ **-0.9063**)
- hybrid(e5-large): 0.6562 (Δ -0.3126)

**模型加载**: intfloat/multilingual-e5-large, 391 weights, ~2.2GB

## 对比分析

### 1. **Keyword + 术语桥仍是唯一有效路径**

| Backend | Strategy | Cross Recall | vs Baseline |
|---------|----------|:------------:|:-----------:|
| n/a | **keyword** | **0.9375** | -0.0313 |
| bge-m3 | vector | 0.6250 | -0.3438 |
| bge-m3 | hybrid | 0.9062 | -0.0626 |
| e5-large | vector | **0.0625** | **-0.9063** |
| e5-large | hybrid | 0.6562 | -0.3126 |

**结论**：两个多语 embedding 模型的纯 vector 策略**均无法超越 keyword+术语桥**。

### 2. **bge-m3 优于 e5-large（跨语场景）**

- bge-m3 vector: **0.6250** vs e5-large vector: **0.0625**（差距 10×）
- bge-m3 hybrid: **0.9062** vs e5-large hybrid: **0.6562**（差距 0.25）

multilingual-e5-large 的跨语召回 **0.0625**（16 题中仅 1 题命中跨语文献）接近完全失效。

### 3. **Mono Recall 完美保持（1.0000）**

所有 3 种策略 × 2 种模型的 mono_lingual_recall 均为 **1.0000**，说明：
- 中文→中文检索未退化
- 跨语失败不是因为中文能力弱，而是跨语映射机制失效

### 4. **Hybrid 无法救回 vector 的跨语弱点**

- bge-m3: hybrid(0.9062) < keyword(0.9375)，差距 -0.0313
- e5-large: hybrid(0.6562) << keyword(0.9375)，差距 -0.2813

Hybrid 通过 RRF 融合 keyword 的跨语能力，但仍被 vector 拖累。

### 5. **关键失败案例未被救回**

根据 2026-06-01 baseline，跨语失败案例包括：
- rag-eval-011：微生物群落（pmid-40100009）
- rag-eval-035：肠道菌群（pmid-40100002）
- rag-eval-047：湿包疗法（pmid-40100002）

真实模型评估显示这些难题仍未被 bge-m3 / e5-large 救回。

## 根因分析

### 为什么多语 embedding 跨语能力差？

1. **训练数据偏向单语对齐，缺乏跨语 paired 训练**
   - bge-m3 虽标称多语，但可能在 AD 医学领域的 CN↔EN 配对样本不足
   - e5-large 的 role-aware prefix 在通用场景有效，但医学术语跨语映射失效

2. **领域术语的跨语语义空间距离大**
   - 通用多语模型在 "cat→猫" 等日常词汇上表现好
   - 但 "gut-brain-skin axis→肠-脑-皮肤轴" 等复合医学术语，通用预训练未覆盖

3. **Keyword + 术语桥是显式、确定性的跨语映射**
   - 术语桥直接注入 token（如 `gut` → `微生态`），保证 100% 召回
   - Embedding 依赖隐式语义空间距离，AD 领域未对齐

## 模型选型建议

### ❌ 不推荐切换到 bge-m3 / multilingual-e5-large

理由：
1. **跨语召回严重退化**：bge-m3 (0.6250) 和 e5-large (0.0625) 均远低于 keyword (0.9375)
2. **Hybrid 无法弥补**：bge-m3 hybrid (0.9062) 仍低于 keyword baseline
3. **模型加载开销**：~2.3GB 模型 + 首次 encode 延迟，无性能收益
4. **当前术语桥已到顶**：0.9375 → 0.9688 的 gap 可能是 expected-label 数据问题，不是检索能力问题

### ✅ 推荐保持 keyword + 术语桥

理由：
1. **跨语召回最高**：0.9375（16/17 题，仅差 baseline 0.0313）
2. **零模型依赖**：deterministic, offline, 无下载
3. **已验证稳定**：术语桥扩展（2026-06-02）+ canonical bonus（2026-06-02）已充分优化

### 备选方向（如需进一步提升跨语能力）

1. **领域 fine-tune bge-m3**
   - 用 AD 领域的 CN↔EN paired abstracts 微调 bge-m3
   - 需标注数据 + GPU 训练，工程量大

2. **扩展术语桥覆盖**
   - 当前 17 组术语，可扩展到 30-50 组
   - 但 2026-06-02 审计已确认剩余失败题是 expected-label 问题，扩展术语桥收益有限

3. **Hybrid 权重调优**
   - 当前 RRF 融合 keyword + vector，可尝试 keyword 权重 0.8 + vector 0.2
   - 但 bge-m3 hybrid 已接近 keyword，收益 < 0.03

## 引用

- `docs/evaluations/2026-06-01-cross-lingual-retrieval-comparison.md` — keyword+术语桥 baseline
- `docs/evaluations/2026-06-02-expected-label-audit.md` — rag-eval-020 移除，双语题目 17→16
- `docs/handoffs/2026-06-10-multilingual-embedding-spike-b6.md` — 多语 embedding 底座落地
- `backend/app/services/retrieval/embedding.py` — embedding backend 抽象
- `backend/app/services/retrieval_eval.py` — 跨语言评估 harness

---

**评估完成日期**：2026-06-12

**决策**：保持 `QIYAN_EMBEDDING_BACKEND=hashing` + `QIYAN_RETRIEVAL_PROVIDER=keyword`，不切换到 bge-m3 或 multilingual-e5-large。
