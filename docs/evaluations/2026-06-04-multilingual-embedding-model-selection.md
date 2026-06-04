# 多语 embedding 模型选型 — 2026-06-04（spike sub-slice ①，纯文档静态对比）

## 背景与范围

`docs/plans/2026-06-04-mvp-a-closeout.md` §阶段 B 入口准备 推荐下一 session 起手「多语 embedding spike」，并把它拆为三个 sub-slice：

| Sub-slice | 内容 | 状态 |
|---|---|---|
| ① | 模型选型纯文档对比（bge-m3 vs e5-multilingual vs labse） | **本文档** |
| ② | 接 `EmbeddingBackend` 最小可跑（lazy load + dim 注册） | 未启动，依赖本文档结论 |
| ③ | `run_cross_lingual_retrieval_eval()` 复跑，目标突破 0.97 天花板 | 未启动，依赖 ② |

**本 sub-slice 边界**：0 行代码改动，0 配置改动，0 新依赖；只产出选型依据与推荐。CI / pytest / mypy / ruff 全部不动。任何模型 benchmark 数字仅引用**公开发布**来源，不在本 sub-slice 自行跑测。

## 问题陈述

当前 cross-lingual retrieval 路径（keyword + 跨语术语桥 + canonical tag-bonus）的工程上限：

| 指标 | 当前值 | 出处 |
|---|---:|---|
| `avg_cross_lingual_recall@10` | 0.9118（17 双语题） | `docs/evaluations/2026-06-02-cross-lingual-canonical-bonus.md` §结果 |
| 完美跨语题 | 15 / 17 | 同上 |
| 残留卡题 | rag-eval-011（pmid-40100009 缺 `gut_skin_axis` 标签） | 同上，已列入 expected-label 审计候选 |
| 上一 session wrap 引用的"近 0.97"上限 | 多次小修后逼近，但**纯关键字桥无法跨过**结构鸿沟 | `docs/handoffs/2026-06-03-session-wrap.md:49` |

为什么不再扩 `cross_lingual_terms.json`：

- Slice 6 / 7 / 8 / 9 已四轮扩 17 组 canonical，每轮收益递减；剩余卡题的失败模式不是**词典没覆盖**，而是**对齐颗粒度错位**——例如 `microbiome` canonical 覆盖了「微生态」但 `chunk-40100009` 的语义不是 microbiome 而是 gut-skin axis；这类失配在词典层无解。
- expected-label 审计是另一条**数据侧**路径，独立于本 spike（架构侧）。两条路径不冲突。

本 spike 的命题：**用真正进入共享语义空间的多语 embedding 替代 / 补充 keyword 桥**，让 zh 查询在 EN 向量库（反之亦然）能直接通过余弦距离对齐，而不依赖人工维护的 alias 表。

## 选型轴

| 轴 | 为什么重要 |
|---|---|
| 跨语对齐质量（CN↔EN） | spike 的存在理由；如不能压过 keyword 桥就没有动机 |
| 维度 dim | 与 `EmbeddingBackend.dim` 抽象解耦，但影响 faiss index 重建 + RRF 融合 |
| 模型体积 / CPU 推理成本 | 本机无 GPU，首次下载 + 单次 encode 延迟 |
| 许可证 | 医生 / 科研产品端可用 |
| 已发布对比数据 | MTEB Multilingual / MIRACL / BEIR-zh / Flores 等公开榜单 |
| 与现有 retrieval 接入面 | `EmbeddingBackend` Protocol 已抽象（`backend/app/services/retrieval/embedding.py`），新 backend 只需注册一类 + `select_embedding_backend` 注册表 + env 切换 |
| 是否需要 query/passage 前缀 | 若需要，集成时要在 `encode()` 内处理，不能透传原文 |

## 候选

### A. BGE-M3（`BAAI/bge-m3`）

| 项 | 值 |
|---|---|
| 团队 | BAAI（北京智源） |
| 参数量 | ~568M（dense 头） |
| dim | 1024（dense） |
| 模型大小 | ~1.4GB |
| 语言 | 100+，含 zh / en |
| 上下文 | 8192 tokens |
| 许可 | MIT |
| 集成 | sentence-transformers 直接加载；不需要 query/passage 前缀 |
| 特点 | 多功能（dense / sparse / colbert 三头）；多粒度（句 / 段 / 长文） |

公开对比定位：
- MTEB Multilingual 长期前列；同期跨语 retrieval 任务（如 MIRACL）位居 SOTA 段。
- 与现有 `bge-small-zh-v1.5`（ADR-0014 默认 dev backend）同团队同体系，缓存路径、`sentence-transformers` 调用形态完全一致。

**对本项目的特殊价值**：
- 多功能头里的 sparse 输出是天然的 keyword-like 信号，未来可作为 ADR-0014 hybrid（RRF）的第三条候选 —— 即 dense + sparse 同一模型出两路 → RRF 融合，比当前「keyword + dense」更自洽。
- BAAI 中文医学语料覆盖通常优于通用多语模型，TCM 术语（"辨证"/"湿热"/"脾虚"）的嵌入质量预期高于 e5-multi。

### B. Multilingual-E5-Large（`intfloat/multilingual-e5-large`）

| 项 | 值 |
|---|---|
| 团队 | Microsoft |
| 参数量 | ~560M |
| dim | 1024 |
| 模型大小 | ~2.2GB |
| 语言 | 94 |
| 上下文 | 512 tokens |
| 许可 | MIT |
| 集成 | sentence-transformers 直接加载；**必须**加 `query: ` / `passage: ` 前缀才能发挥设计性能 |
| 特点 | 弱监督对比预训练 + 多任务 fine-tune；MIRACL 强表现 |

公开对比定位：
- MIRACL 多语 retrieval 接近 BGE-M3，部分子任务互有胜负。
- 生态成熟，sentence-transformers / langchain 文档充分。

**对本项目的代价**：
- 前缀要求是**陷阱**：现有 `EmbeddingBackend.encode(texts: list[str])` 不区分 query / passage 调用面，需要在 backend 实现内根据上下文加前缀，或在 retrieval provider 层显式分两次调用。任一选择都增加一处**整改面**，违背本 spike "最小可跑"取向。
- 模型体积比 BGE-M3 大 ~50%（首次下载体感差异显著），跨语对齐质量未见明显领先。

### C. LaBSE（`sentence-transformers/LaBSE`）

| 项 | 值 |
|---|---|
| 团队 | Google |
| 参数量 | ~470M |
| dim | 768 |
| 模型大小 | ~1.9GB |
| 语言 | 109 |
| 上下文 | 512 tokens |
| 许可 | Apache-2.0 |
| 集成 | sentence-transformers 直接加载；不需要前缀 |
| 特点 | BERT-based；专为 cross-lingual sentence similarity / bitext mining 优化（2020） |

公开对比定位：
- 跨语句子对齐 / bitext mining 历久弥稳；早期 cross-lingual 工作的标准基线。
- 2024+ MTEB Multilingual 上被 BGE-M3 / E5-multi 系列拉开差距，但在「短句对齐」子任务仍有竞争力。

**对本项目的特殊价值**：
- dim 768 与 ADR-0005 的「text2vec-base-chinese / PubMedBERT 双模型 768」选型一致。**意味着如果未来真要落 ADR-0005 的双轨架构，LaBSE 是同维度的多语补丁**——适合作为「保守备选」。
- 集成最简单：单一 encode，无前缀，dim 与历史决策对齐。

## 横向对比

| 维度 | BGE-M3 | E5-Multi-Large | LaBSE |
|---|---|---|---|
| dim | 1024 | 1024 | 768 |
| 体积（~MB） | 1400 | 2200 | 1900 |
| 上下文 token | **8192** | 512 | 512 |
| 跨语对齐（公开榜近况） | **顶** | 顶 | 中位（稳） |
| 集成复杂度 | 直接 | **需前缀**（破坏当前 `encode` 形态） | 直接 |
| 许可 | MIT | MIT | Apache-2.0 |
| 与现有 `bge` backend 同源 | **是** | 否 | 否 |
| 与 ADR-0005 dim 一致 | 否（1024） | 否（1024） | **是**（768） |
| 与 ADR-0014 hybrid 自然延伸 | **是**（dense + sparse 同模型） | 部分 | 否 |
| TCM 中文医学语料适配 | **较强**（BAAI 体系） | 中等 | 中等 |

## 推荐

**首选：BGE-M3**

四点决定性原因：

1. **跨语对齐质量在公开榜上当前段最优**，且对中文医学语料的适配显著优于通用多语模型——这是 spike 命题的核心。
2. **集成路径最短**：与现有 `SentenceTransformerEmbeddingBackend`（`bge-small-zh-v1.5`）同 BAAI 体系，sentence-transformers 调用形态、缓存路径、lazy-load 模式完全一致；sub-slice ② 落地时只需在 `_BACKENDS` 注册表追加 1 类，无需重构 `encode()` 调用面。
3. **与 ADR-0014 hybrid 自然衔接**：sparse 头未来可作为 RRF 第三路融合候选，省一笔工程债。
4. **MIT 许可**，产品端零顾虑。

**备选：multilingual-e5-large**

如果 sub-slice ③ 在本地 50 题 + 17 跨语题数据上发现 BGE-M3 实测不及预期，e5-multi 是稳定 fallback，但**预算 1-2 小时**给「在 `encode()` 内统一加前缀」的整改面（建议方式：在 backend 实现内对 `encode(texts)` 输入默认加 `passage: `，并新增一个 `encode_query(texts)` 接口；这要改 `EmbeddingBackend` Protocol，是显著的接口变更，需独立 ADR）。

**不推荐 LaBSE 作为 spike 主选，但保留为长期参考**

- 跨语对齐在 2024+ 榜单上已落后 BGE-M3 / E5-multi。
- 768 维与 ADR-0005 兼容这一优势，只有在「未来回归 ADR-0005 双轨架构」的前提下才兑现；本 spike 的命题恰恰是**用单一多语模型替代分流**，这条优势在当前架构方向下没有兑现窗口。

## 对既有 ADR 的关系

| ADR | 关系 | 解释 |
|---|---|---|
| ADR-0005（双 Embedding 模型分流：text2vec-base-chinese + PubMedBERT） | **追加，不否定** | ADR-0005 在 mono-language 场景（zh 查 zh、en 查 en）仍有效；本 spike 攻克的是**跨语**场景的结构鸿沟。落地后两者**并存**，按 env / use case 切换。如果 sub-slice ③ 实测 BGE-M3 的 mono-zh 召回也压过 text2vec-base-chinese，再考虑由 BGE-M3 单模型取代 ADR-0005 的双轨——这是后续 ADR 议题，不在本 spike。 |
| ADR-0014（RetrievalProvider + Hybrid + faiss） | **零接口变更，仅注册新 backend** | `RetrievalProvider` 接口不动；`EmbeddingBackend` Protocol 不动（BGE-M3 满足现签名）；`_BACKENDS` 注册表追加 `multilingual_bge_m3` 一类；env `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` 显式 opt-in；default 仍为 `hashing`。faiss `IndexFlatIP` 不动（dim 1024 与 bge-small 的 512 不同，需要 fingerprint rebuild——ADR-0014 §7 的「lazy build + fingerprint rebuild」机制本来就处理这种 dim 漂移）。 |
| ADR-0012（real-llm-enablement / L2 治理） | **正交** | L2 阻塞点在 NLI grounding 拦截率（见 `2026-06-02-claim-quality-v2-live-validation.md`），不在 retrieval recall；本 spike 不解 L2 阻塞，但**有可能**让 BGE prefilter 阈值的语义更稳，间接利好 L2 重新校准——这是 sub-slice ③ 之后的衍生议题。 |

## CI / 边界承诺

- 本 sub-slice：0 代码、0 配置、0 依赖；ruff / mypy / pytest / e2e 全部不动。
- 后续 sub-slice ② 落地时：
  - default backend 仍为 `HashingEmbeddingBackend`（CI 走的就是这条，零下载）；
  - 新 backend 仅在 env `QIYAN_EMBEDDING_BACKEND=multilingual_bge_m3` 显式 opt-in 时启用；
  - 单元测用 `monkeypatch` 替换 `_load_sentence_transformer` 返回 mock，不真下载（沿用现有 `SentenceTransformerEmbeddingBackend` 的测试模式）；
  - `[project.optional-dependencies].dev` 已有 `sentence-transformers`，BGE-M3 走同一依赖，无需新增 pip 包。
- 后续 sub-slice ③ 落地时：
  - eval 复跑需本地预下载 `BAAI/bge-m3` 权重（~1.4GB，首次 ~2-5 分钟），属一次性 dev-setup 步；CI 仍不跑这条路径；
  - `_CROSS_LINGUAL_RECALL_BASELINE` 收紧只发生在 sub-slice ③ 的最终 eval 通过之后，不在 ② 内。

## 决策门

- 本 sub-slice 进入 ② 的门：**用户认可推荐（BGE-M3 主、E5-multi-large 备）**，或显式选择不同方向。
- 退路（若 spike 整体被否决）：
  - 走 expected-label 数据补齐（rag-eval-011 / 020）—— 已列 candidate，无需架构变更；
  - 维持当前 0.91 / 近 0.97 上限作为 MVP-A 出口形态——closeout doc 已记录此为已知工程上限，无产品阻塞。

## 范围外（明确不在本 sub-slice 做）

- 任何代码改动（包括 placeholder 文件、空 backend 类、注册表桩）。
- 任何 benchmark 跑测（本机 / 远端 / CI 都不跑）；本文档所有质量定位均引用公开榜单 + 模型卡描述。
- 跨语术语桥的下一步扩展——已在另一条数据侧路径，独立于本 spike。
- L2 阈值重新校准——独立议题，见 ADR-0012。

## 引用

- `docs/plans/2026-06-04-mvp-a-closeout.md` §阶段 B 入口准备
- `docs/handoffs/2026-06-03-session-wrap.md` §Recommended next action
- `docs/handoffs/2026-06-02-cross-lingual-canonical-bonus.md`（cross_lingual_recall 0.9118 当前定位）
- `docs/evaluations/2026-06-01-cross-lingual-retrieval-comparison.md`（keyword vs vector vs hybrid 后端对比基线）
- `docs/adr/0005-双Embedding模型分流.md`
- `docs/adr/0014-retrieval-provider-and-hybrid-search.md`
- `backend/app/services/retrieval/embedding.py`（`EmbeddingBackend` Protocol + 现 `bge` backend lazy load 范式）
- `backend/data/retrieval/cross_lingual_terms.json`（17 组 canonical，已逼近词典层工程上限）

---

*文档日期：2026-06-04 | 类型：spike sub-slice ① 纯文档静态对比 | 0 代码改动 | 下一步：用户对 BGE-M3 主选 + E5-multi-large 备选 的认可，触发 sub-slice ②*
