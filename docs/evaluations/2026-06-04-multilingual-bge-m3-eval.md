# 多语 embedding BGE-M3 实测评估 — 2026-06-04（spike sub-slice ③，eval 复跑）

## 背景与范围

`docs/plans/2026-06-04-mvp-a-closeout.md` §阶段 B 入口准备 推荐的多语 embedding spike 三 sub-slice 的最后一步：在 sub-slice ①（model 选型纯文档）与 ② （`MultilingualBgeM3EmbeddingBackend` 工程接入）落地后，在本地预下载 `BAAI/bge-m3` 权重（~1.4GB，首次 sentence_transformers 自动拉到 `~/.cache/huggingface/`），跑 `run_cross_lingual_retrieval_eval()` 对比当前 keyword + 跨语术语桥 + canonical tag-bonus 基线，**目标判断 BGE-M3 能否突破 cross-lingual recall 0.97 工程上限并触发 ADR-0015 议题**。

**结论先行**：BGE-M3 **没有突破上限，反而在最强配置（hybrid + BGE-M3）下净 -0.03**（0 题救回 + 1 题退化）。spike 整体收尾，BGE-M3 backend 保留为 env-opt-in 可选项，默认路径不变。**不发 ADR-0015**。

## 测试配置

- 数据集：`backend/data/evals/rag_ad_eval_questions.json` 50 题，过滤为既含 `cn-*` 又含 `pmid-*` 期望 ID 的双语 cohort，N = **16 题**（与 closeout doc 引用的 17 题相比少 1，因为 Slice 8 expected-label 审计把 rag-eval-020 从 expected_literature 移除，bilingual filter 自动剔除）
- 评估机制：调 `retrieval_provider.rank()` 直接打分，绕过 `answer_question()`、不走 LLM、不走 grounding，纯 retrieval 隔离评测
- top_k：10
- 主机：Windows 11，CPU encode（无 GPU），代理：huggingface 直连（未走 7897），权重 cache 已落地 `~/.cache/huggingface/models--BAAI--bge-m3`
- 脚本：`backend/scripts/eval_multilingual_bge_m3.py`，原始数据 `docs/evaluations/bge_m3_eval_data.json` + `docs/evaluations/keyword_baseline_eval_data.json`

四组对比配置：

| label | retrieval | embedding | 角色 |
|---|---|---|---|
| `keyword` | keyword | hashing | **当前默认基线** —— keyword + cross_lingual_terms.json 桥 + canonical tag-bonus |
| `vector_hashing` | vector | hashing | 噪声 floor —— hashing 是确定性 md5 ±1，不具语义 |
| `vector_bge_m3` | vector | multilingual_bge_m3 | BGE-M3 单独 dense 检索 |
| `hybrid_bge_m3` | hybrid | multilingual_bge_m3 | RRF 融合 keyword + BGE-M3 dense（ADR-0014 §6） |

## 汇总结果

| label | strategy | embedding | N | mono | **cross** | div | MRR | elapsed |
|---|---|---|---:|---:|---:|---:|---:|---:|
| keyword | keyword | hashing | 16 | **1.0000** | **0.9375** | 0.3765 | 0.9115 | 0.03s |
| vector_hashing | vector | hashing | 16 | 0.8438 | 0.3438 | 0.3405 | 0.4734 | 0.31s |
| vector_bge_m3 | vector | multilingual_bge_m3 | 16 | **1.0000** | 0.6250 | 0.1977 | 0.8750 | 179.53s（含权重加载） |
| **hybrid_bge_m3** | hybrid | multilingual_bge_m3 | 16 | **1.0000** | **0.9062** | 0.2289 | **0.9271** | 12.08s |

**核心数字**：
- 当前 keyword baseline cross-lingual recall = **0.9375**
- BGE-M3 最强配置 hybrid_bge_m3 = **0.9062** → **净 -0.0313（绝对 -0.5/16 题）**
- BGE-M3 单独 vector = 0.6250 → 比 keyword 直接掉 31 个百分点

## 单题级诊断

逐题对比 `cross_lingual_recall`（baseline keyword vs vec_bge vs hyb_bge）：

| id | keyword | vec_bge_m3 | hyb_bge_m3 | 解读 |
|---|---:|---:|---:|---|
| rag-eval-001 | 1.000 | 1.000 | 1.000 | 三者齐平 |
| rag-eval-004 | 1.000 | **0.000** | 1.000 | vector 单独失败，hybrid 救回 |
| rag-eval-006 | 1.000 | **0.000** | 1.000 | 同上 |
| rag-eval-007 | 1.000 | 1.000 | 1.000 | 齐平 |
| rag-eval-008 | 1.000 | **0.000** | 1.000 | vector 失败 hybrid 救回 |
| rag-eval-009 | 1.000 | 1.000 | 1.000 | 齐平 |
| **rag-eval-011** | **0.500** | 0.000 | **0.500** | **closeout doc 点名瓶颈题：pmid-40100009 仍未进 top-10。BGE-M3 没救回** |
| rag-eval-016 | 1.000 | 1.000 | 1.000 | 齐平 |
| **rag-eval-019** | **0.500** | 0.000 | **0.000** | **退化：keyword 命中 pmid-40100008 (rank 8)；hybrid 被 BGE-M3 钓出 pmid-40100001 挤掉了它** |
| rag-eval-022 | 1.000 | 0.000 | 1.000 | vector 失败 hybrid 救回 |
| rag-eval-030 | 1.000 | 1.000 | 1.000 | 齐平 |
| rag-eval-031 | 1.000 | 1.000 | 1.000 | 齐平 |
| rag-eval-033 | 1.000 | 1.000 | 1.000 | 齐平 |
| rag-eval-035 | 1.000 | 1.000 | 1.000 | 齐平 |
| rag-eval-047 | 1.000 | 1.000 | 1.000 | 齐平 |
| rag-eval-049 | 1.000 | 1.000 | 1.000 | 齐平 |

**hybrid_bge_m3 vs keyword 的全部 diff** 只有两题：

1. **rag-eval-011**：双方齐为 0.5 —— 闭合不了的瓶颈题原状保留
2. **rag-eval-019**：keyword 0.5 → hybrid_bge_m3 0.0，**退化**

### rag-eval-019 退化的具体 swap

`keyword` 的 top-10：`['cn-ad-network-007', 'cn-ad-formula-002', 'cn-ad-barrier-006', 'cn-ad-pruritus-005', 'cn-ad-external-008', 'cn-ad-gbs-001', 'pmid-40100001', 'pmid-40100008', 'cn-ad-microbiome-003', 'cn-ad-review-010']`

`hybrid_bge_m3` 的 top-10：`['cn-ad-network-007', 'pmid-40100001', 'cn-ad-gbs-001', 'cn-ad-external-008', 'cn-ad-formula-002', 'cn-ad-review-010', 'cn-ad-pruritus-005', 'cn-ad-barrier-006', 'cn-ad-microbiome-003', 'cn-ad-child-009']`

- expected pubmed 是 `pmid-40100008`，`keyword` 在 rank 8 命中
- `hybrid_bge_m3` 把 `pmid-40100001`（**非**期望）从 rank 7 提到 rank 2，**`pmid-40100008` 直接掉出 top-10**，被 `cn-ad-child-009` 替换
- 根因：BGE-M3 dense score 把 `pmid-40100001` 的相似度推高，RRF 把它的最终 rank 拉到 #2；`pmid-40100008` 在 BGE-M3 的命中带可能 > 10 名外，RRF 救不回

## 为什么 BGE-M3 在本数据集上失利

四点诊断：

1. **本地 cohort 极小（16 题、10 篇 cn + 10 篇 pmid 文献）**：BGE-M3 在 MIRACL / MTEB 的 SOTA 表现建立在大规模 corpus 上；小 corpus 里所有 chunk 的余弦相似度都偏高，"语义 prior" 反而稀释了 keyword 桥的 surgical precision
2. **keyword + canonical tag-bonus 已经做了高度 surgical 的对齐**：Slice 6/7/8 累计 17 组 canonical + `+2/+7` tag-bonus，目标命中题在 keyword 路径上是「显式 hit」；BGE-M3 dense 是「全局 prior 概率」，前者比后者 sharp
3. **chunk-level dense 不区分 strong evidence vs weak association**：BGE-M3 把 `pmid-40100001`（与 019 同领域但非期望）的相似度推到很高，RRF 融合时把 keyword 路径上正命中的 `pmid-40100008` 挤掉
4. **rag-eval-011 的 pmid-40100009 失败不是「关键词桥的天花板」而是「数据语义本质失配」**：CN 查询语义重心是「肠道菌群」，pmid-40100009 是「皮肤微生态 + S. aureus」，两者在任何 embedding 空间里距离都远；keyword 救不回、BGE-M3 也救不回 —— **这道题需要的不是更好的 retrieval 而是 expected-label 数据修正**

## 与 sub-slice ① / ② 决策门的对账

`docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md` 中的退路条款：

> 若 sub-slice ③ 显示 cross-lingual recall 显著突破且 mono 不退化 → 写 ADR-0015 草案，决议 BGE-M3 是否成为「跨语 retrieval 默认路径」
> 若 cross-lingual 仅小幅提升或 mono 退化 → spike 写 evaluation 收尾报告，BGE-M3 backend 作为可选项保留但不推默认

本次实测命中第二条（**cross 净下降 0.03，mono 持平**）。**触发 spike 收尾分支，不发 ADR-0015**。

## sub-slice ② 保留状态

`MultilingualBgeM3EmbeddingBackend`（commit `408da92`）**保留作为可选 backend**：

- `env QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` 仍可显式 opt-in
- 默认 `hashing` 不变；retrieval default `keyword` 不变；50 题 RAG eval 默认 pass_rate 不变
- 后续如出现新数据集 / 新 cohort（例如未来 cn 文献从 10 篇扩到 100+），可直接复用本 backend 重测，无需重新工程接入
- BGE-M3 单题 encode latency 在本机 CPU 下：首次 ~180s（含权重加载），第二次 cache 复用 ~12s。dev 体验可接受但不适合默认路径

## sub-slice ② 的 evaluation 之外的两个观察（不影响决策）

- **mono 完全不退化（1.0000）**：BGE-M3 在 CN 查 CN / EN 查 EN 至少与 keyword + cross_lingual_terms.json 同水平。如果未来要追求 cross-architecture 简化（替代 ADR-0005 的双轨 text2vec-base-chinese + PubMedBERT），BGE-M3 是单模型候选；但在本 spike 范围外。
- **hybrid_bge_m3 的 avg_MRR 0.9271 > keyword 0.9115**：top-1 rank 略好，但 cross-lingual recall 是主指标，MRR 改善不足以换 recall 退化

## 真正的 ceiling 在哪里

实测数据指向：**剩余两题失败（011 / 019）都不是 retrieval 算法层能解的**。

- **rag-eval-011 / pmid-40100009**：需要 expected-label 审计，明确「皮肤微生态」cohort 是否应保留为该题的合法期望（与 closeout doc Loose ends 一致）
- **rag-eval-019**：keyword 0.5 已是可接受水位（半命中 pmid-40100008）；任何 dense 召回都会引入 false positive 风险

**下一条可行路径不再是「更好的 embedding」，而是 expected-label 数据修正（Slice 8 已开半步）**。这是 spike 的有效负面结论：把工程力气投在数据侧而不是架构侧。

## 验证命令

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\eval_multilingual_bge_m3.py keyword vector_hashing --json ..\docs\evaluations\keyword_baseline_eval_data.json
& .\.uv-test-venv\Scripts\python.exe scripts\eval_multilingual_bge_m3.py vector_bge_m3 hybrid_bge_m3 --json ..\docs\evaluations\bge_m3_eval_data.json
& .\.uv-test-venv\Scripts\python.exe scripts\_diff_bge_m3.py
```

注意首次跑 `vector_bge_m3` 会自动下载 ~1.4GB BGE-M3 权重到 `~/.cache/huggingface/`，本机实测无需 HF 代理（与 github 不同，huggingface.co 当前直连可达）。CI 永远不走这条路径，因为 default `QIYAN_EMBEDDING_BACKEND=hashing`。

## 范围外 / 收尾

- ❌ **不发 ADR-0015**（spike 触发收尾分支，不推默认）
- ❌ **不动 retrieval default**（`keyword` 保留）
- ❌ **不动 RAG default**（`deterministic` 保留）
- ❌ **不动 50 题 RAG eval baseline**（pass_rate 锁定不动）
- ✅ **保留 BGE-M3 backend 工程接入**（env-opt-in 可选）
- ✅ **下一条可行路径明确**：expected-label 数据补齐（rag-eval-011 / 020 候选项）

## 引用

- `docs/plans/2026-06-04-mvp-a-closeout.md` §阶段 B 入口准备
- `docs/evaluations/2026-06-04-multilingual-embedding-model-selection.md`（sub-slice ① 选型推荐）
- `docs/handoffs/2026-06-04-multilingual-embedding-spike-sub-slice-2.md`（sub-slice ② 接入交接）
- `docs/evaluations/2026-06-02-cross-lingual-canonical-bonus.md`（Slice 7 受控打分修复）
- `docs/evaluations/2026-06-02-expected-label-audit.md`（Slice 8 expected-label 审计）
- `docs/adr/0014-retrieval-provider-and-hybrid-search.md` §6（RRF k=60）、§7（fingerprint rebuild）
- `backend/scripts/eval_multilingual_bge_m3.py`（本次评估脚本）
- `docs/evaluations/bge_m3_eval_data.json`（vec_bge / hyb_bge 原始 per-item）
- `docs/evaluations/keyword_baseline_eval_data.json`（keyword / vec_hashing 原始 per-item）

---

*评估日期：2026-06-04 | 类型：spike sub-slice ③ eval 复跑 | 结论：spike 负面收尾，BGE-M3 作可选 backend 保留，不推默认；下一可行路径转入数据侧 expected-label 审计*
