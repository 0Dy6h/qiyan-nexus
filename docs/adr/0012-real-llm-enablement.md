# ADR-0012: 真实 LLM 启用决策与不变量

日期：2026-05-31

## 状态

Accepted

## 背景

C 阶段路线图（`docs/plans/2026-05-21-roadmap.md`）的最后一项是「MVP-A LLM 化」：让真实 LLM provider 从仅本地显式 smoke，推进到一条有治理、可回滚的内部预览启用路径。前置工作已完成：

- C1 真实 provider（`opencode_go` 优先，`anthropic` 后置）已接入并可回退 deterministic；
- 结构化 + 证据 ID + BGE 语义 grounding gate 已落地并验证（`docs/evaluations/2026-05-31-bge-semantic-evaluation.md`）；
- 2026-05-31 真实 live smoke 完成（`docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`）；
- 成本/延迟 SLI 已暴露到 API/前端/日志；
- 外部数据流向与 PIPL 措辞已记录（ADR-0011）。

live smoke 暴露了两个必须写入启用决策的事实：
1. `deepseek-v4-flash`（thinking mode）拒绝强制 `tool_choice`（HTTP 400），真实路径只能走 structured claims v3，而非 provider-native tool use；
2. 默认 `max_tokens=1200` 会被 reasoning 吃光导致空 content → deterministic fallback，需 ≥4000 才能让真实路径生效。

同时，0.78 阈值（在 20 对标注集上校准）对真实、较长、含改写的 LLM claim 偏严，会把若干可能忠实的 claim 拦截（`semantic_low_support`）。这意味着「打开真实模型」与「让真实模型答案默认对用户可见」是两个不同的成熟度。

## 决策

1. **保留 deterministic 为默认**：真实 provider 始终是显式 opt-in（`QIYAN_LLM_PROVIDER`），默认用户路径不外发、不依赖 key。

2. **真实 provider 启用的强制不变量**（任何启用场景都必须满足，否则不得启用）：
   - **免责声明**：`非诊断结论、需结合临床。` 在每个回答 byte-identical 存在（由后端 `DISCLAIMER` 与前后端测试锁定，不得改写）。
   - **grounding gate 常开**：外部 provider 的回答必须经过 grounding gate（结构化 claims + 证据 ID 白名单 + BGE 语义阈值）；未通过即替换为 hard-block 文案、`grounding.status="blocked"`，绝不展示未校验草稿。
   - **安全回退**：缺 key、HTTP 错误、网关失败、空 content、响应结构异常都必须回退 deterministic，`/api/rag/answer` 不对用户硬失败。
   - **secret 仅 env**：key 只从 `QIYAN_OPENCODE_GO_API_KEY` 读取，不入仓库/README/handoff/测试/日志。

3. **模型相关配置约束**（基于 live smoke）：
   - `deepseek-v4-flash` 不支持强制 tool_choice；启用时按 structured claims v3 路径预期，不假设 provider-native tool grounding。
   - `QIYAN_OPENCODE_GO_MAX_TOKENS` 必须 ≥4000（thinking 模型需在 reasoning 之后留出 content 余量）；过低会静默退化为 deterministic。

4. **分两级启用成熟度**：
   - **L1 — 受控 smoke / 演示（当前可启用）**：本地或受控环境用真实 provider 演示，grounding gate 常开。允许出现 `semantic_low_support` 拦截，并向观众解释这是反幻觉护栏在工作。无需阈值重校准。
   - **L2 — 默认预览路径（暂不启用，需补前置）**：把真实 provider 作为内部预览默认 RAG 路径，前置条件：
     a. 扩充 `backend/data/evals/grounding_semantic_pairs.json` 至包含真实 LLM 风格 claim，并用 `run_grounding_semantic_separation` 重新校准阈值（候选区间 0.55–0.72），使忠实改写不被过度拦截；
     b. 用真实合同单价配置 `QIYAN_OPENCODE_GO_PRICE_*`，并记录成本/延迟 SLI 基线；
     c. 完成一次真人内部 reviewer 走查（`docs/checklists/internal-preview-smoke.md`）。

5. **回滚开关**：设 `QIYAN_LLM_PROVIDER=deterministic`（或清空）即时关闭真实 provider，无需改代码。这是唯一且充分的回滚动作。

## 后果

正面：
- 真实模型可在 L1 受控场景启用，路线图「MVP-A LLM 化」的工程底座收口。
- 不变量写明后，启用/回滚动作可被任何运维或下一会话安全执行。
- L1/L2 分级避免把「能调真实模型」误当成「真实答案默认可见」。

代价：
- L2（默认预览）仍被阈值重校准与真人走查阻塞，不在本轮交付范围。
- thinking 模型的 token 余量与 tool 限制属于模型相关约束，换模型需重跑 smoke 复核。

## 验证

- 启用与回滚步骤见 `docs/guides/real-llm-enablement-runbook.md`。
- 不变量回归由现有后端/前端 grounding、disclaimer、fallback 测试覆盖（`tests/test_rag_service.py`、`tests/test_grounding_semantic.py`、前端 `rag-export` / `client-section-consistency`）。
- live 行为证据见 `docs/evaluations/2026-05-31-opencode-go-bge-smoke.md`。

## 2026-06-01 更新：§4a「阈值重校准」结论 — 被 cosine 模型类限制阻塞

按 §4a 做了阈值重校准分析（`docs/evaluations/2026-06-01-threshold-recalibration.md`、
`backend/scripts/sweep_threshold_recalibration.py`、fixture
`backend/data/evals/grounding_semantic_pairs_bge.json`）：把 7 条**逐字取自 2026-05-31 live smoke**
的忠实 claim，与 7 条**同主题硬负例**（复用被引 chunk 词汇，但臆造治愈率/因果/数字/指南地位）配对，
在 bge backend 上扫 0.55–0.78。

结果：忠实 claim 落在 **0.863–0.963**，硬负例落在 **0.736–0.870**，**分布重叠（gap = −0.007）**。
不存在任何阈值能同时「放行忠实改写、拦截硬负例」；候选区间 0.55–0.72 内会**放行全部 7 条硬负例**，
比当前 0.78 更弱。生产中差距更大：同一批忠实 claim 在 live smoke 实测仅 0.591–0.881。

根因是模型类问题而非 fixture bug：BGE 是句向量**相似度**模型，cosine 度量主题/词汇相关性而非事实
**蕴含**；停留在主题内的幻觉（如「菌群干预治愈率90%」）与源 chunk 主题高度相似，得分与忠实改写相当，
cosine 在结构上无法区分「忠实复述」与「同主题、附加未支撑结论的臆造」。

**决策**：不下调阈值（任何能救回忠实 claim 的阈值都会放行硬负例，削弱反幻觉护栏）。**§4a 在 BGE-cosine
单独条件下不可达**，故 **L2 经由「纯阈值重校准」这条路被阻塞**；**保持 L1**，默认 RAG 仍为离线
`deterministic`，不做默认切换。闭合该 gap 需换一类 gate（中文 NLI/蕴含或 claim 核验模型，度量
entailment 而非 similarity），属独立的、更大的架构决策，不在本轮范围。§4b（真实单价 + SLI 基线）、
§4c（真人走查）保持开放，但在 §4a 以新 gate 形式解决前不构成启用 L2 的充分条件。

## 2026-06-01 更新（二）：NLI 蕴含 gate spike 验证通过 + opt-in 落地

上一条提出的「换一类 gate」已做 spike 验证（`docs/evaluations/2026-06-01-nli-grounding-spike.md`、
`backend/scripts/spike_nli_grounding.py`）。用多语 NLI 模型 `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`
（premise=被引 chunk，hypothesis=claim，取 entailment 概率）在**同一 14 对 fixture** 上评分：

- 忠实 claim entailment **0.997–0.999**（7 中 6 条），硬负例 **≤0.001**（7 中 7 条）；
- 在 0.10–0.90 全阈值区间 **false accept = 0**（cosine 是 7/7 false accept）；
- 唯一一条忠实「误拒」（entailment 0.0073）实为标注过宽：该 claim 额外断言「提供潜在靶点」而 chunk 未述，
  NLI 实际抓对了一个 scope 越界。

**实现（opt-in，默认关闭）**：新增 `app/services/nli.py`（`NliBackend` Protocol + 懒加载
`TransformersNliBackend` + `select_nli_backend`，默认/未知名 → `None`）；`evaluate_answer_grounding`
在 cosine 预筛之后追加 NLI 二级 gate，未过阈值时 `blocked_reason="nli_low_entailment"`；schema 增
`entailment_score` / `nli_threshold` / `min_entailment_score`；config 增 `QIYAN_NLI_BACKEND`（默认空=关）、
`QIYAN_NLI_MODEL`、`QIYAN_NLI_THRESHOLD`（默认 0=关）。**默认行为逐字节不变**：未配置时 gate 为 no-op，
CI 不导入 transformers、不下载权重（测试用确定性 fake backend）。所有不变量（免责声明、拦截替换、安全回退）保持。

**这不等于自动晋级 L2。** 该 gate 解决了 §4a 的技术阻塞，但默认切换到真实 provider 之前仍需：在更大、更多样的
标注集上复核并定生产阈值；把每条 claim 一次 NLI 前向的延迟/成本计入 SLI 基线（§4b）；完成真人走查（§4c）。
gate 默认关闭，在上述完成且明确翻转默认前不改变现有用户路径。

## 2026-06-01 更新（三）：Slices 1-5 执行完成 + §4c 走查结论 — L2 不翻转

### 工程闭环（Slices 1-5）

按 `docs/plans/2026-06-01-execution-plan.md` 执行的 5 颗 slice 全部完成：

| Slice | 内容 | 关键指标 |
|---|---|---|
| 1 | 真实 claim 语料采集 | capture 脚本 live/offline 双模式 |
| 2 | 人工标注验证集 | `grounding_real_answer_pairs.json`（20 对：7 real + 13 hard neg） |
| 3 | NLI 真实分布评估 | **0 FP, 0 FN, gap +0.9549**，阈值 0.5 极度保守有效 |
| 4 | NLI 批处理降延迟 | batch entailment，3-claim 回答 ~2.1s（约 1.1x speedup） |
| 5 | §4c 走查准备 | 7 步验证 checklist 写入 `docs/checklists/internal-preview-smoke.md` §4c 节 |

### §4c 走查核验（2026-06-01，opencode_go + transformers NLI gate）

启用配置：`QIYAN_LLM_PROVIDER=opencode_go`、`QIYAN_EMBEDDING_BACKEND=bge`、`QIYAN_NLI_BACKEND=transformers`、`QIYAN_NLI_THRESHOLD=0.5`、`max_tokens=4000`。

**走查结果**：

| 步骤 | 检查项 | 结果 |
|---|---|---|
| R1 | `provider_name="opencode_go"`（非 fallback） | ✅ |
| R2 | NLI gate 运行（`nli_threshold=0.5` 可见，claims 带 `entailment_score`） | ✅ |
| R3 | Disclaimer 逐字节一致 | ✅ |
| R4 | 缺 key → deterministic fallback | ✅ |
| R5 | `QIYAN_LLM_PROVIDER=deterministic` 瞬时回滚 | ✅ |
| R6 | 前端 UI 展示 provider/grounding 元数据 | ✅ |
| R7 | Blocked 时硬屏蔽文案 + 引用卡片仍展示 | ✅ |

**关键观察**：

1. **BGE=0.78 是穿透瓶颈**：在默认配置（BGE threshold 0.78）下，走查全程没有一条回答穿透 BGE 门到达 NLI gate。中文问题配英文 chunk（keyword retriever 跨语匹配）直接 BGE blocked。需将阈值临时降至 0.3 方能让 NLI gate 执行。

2. **NLI gate 正确拦截了不支持 entailment 的 claim**：4 次查询全部 `blocked_reason="nli_low_entailment"`，entailment 在 0.004–0.86 范围。其中一条 claim 的 entailment=0.86 单独通过了 NLI 门（> 0.5），但同回答的另一条 claim 只有 0.004，被保守的 min-score 策略拦截。

3. **NLI gate 能区分好 claim 和差 claim**：entailment 0.86 vs 0.004 的同一回答内分化，证明了 gate 的判别力——不是一刀切全部拒绝，而是精准识别了不被 chunk 充分蕴涵的 claim。

4. **走查全程 0 条回答通过**：openCode Go 生成的 claim 倾向于跨 chunk 综合、添加推断、自由改写，NLI gate 一致拦截。这是 gate 的正确行为，但意味着在当前 retrieval 质量（keyword 匹配）和 LLM 改写风格下，真实 provider 不会产生默认可见的输出。

### 决策：L2 不翻转，保持 L1

**理由**：

- NLI gate 工程成熟度已验证（3 个独立 fixture 上 0 false accept，生产走查也未见误放行）
- 但真实 provider 在当前 retrieval + BGE 门槛下几乎无法产生用户可见输出
- 可治理的启用路径已于 ADR-0011/ADR-0012 写明，瞬时回滚（1 个 env var）充分
- **不翻转默认不等于放弃**：存 `QIYAN_OPENCODE_GO_API_KEY` 者设 3 个 env var 即可启用 L1

**若未来重新评估 L2 翻转，需解决的前置条件**：

| 条件 | 当前状态 | 难度 |
|---|---|---|
| ① retrieval 中英跨语匹配 | keyword 匹配中英不对应，BGE cross-lingual 低分 | 中（需 bilingual retrieval 或中文 seed 增强） |
| ② BGE 阈值重新校准 | 0.78 来自 easy fixture，对真实改写过度拦截 | 中（NLI gate 可替代，但 BGE 预筛门槛需调低） |
| ③ LLM claim 质量控制 | openCode Go free-form 常额外推断、跨 chunk 综合 | 高（需 prompt 层约束或 structured output 优化） |

**本次「MVP-A LLM 化」工程底座正式收口。** L1 受控启用路径完整、有治理、可回滚。默认路径保持离线 deterministic。

## 2026-06-01 更新（四）：跨语言检索改进 — 条件①部分缓解，L2 仍不翻转

### 背景

更新（三）识别了 L2 翻转的三项前置条件，其中条件①「retrieval 中英跨语匹配」被列为根因：
keyword retriever 存在 `language_bonus` 主排序硬屏障 + `_KEYWORD_ALIASES` 覆盖不足，导致中文
查询对英文 PubMed 文献的跨语言召回为零（中文查询 → cn 文献 100% 命中，pmid 文献 0% 命中）。

### 改进（Slice 1-3, feat/cross-lingual-retrieval）

实施了 3 个 slices 的跨语言检索改进：

| Slice | 内容 | 关键结果 |
|---|---|---|
| **1** | 跨语言检索 eval harness | 新增 `run_cross_lingual_retrieval_eval()`，测量 cross_lingual_recall@10、MRR、language_diversity |
| **2** | 确定性 CN↔EN 术语桥 | (a) 排序键从 `(language_bonus, score, year)` → `(score, language_bonus, year)`；(b) 17 组 AD 领域双语术语映射（`cross_lingual_terms.json`）；(c) `tokenize_query` 注入跨语言等价 token |
| **3** | 检索后端对比 | keyword+bridge、vector(hashing)、vector(bge)、hybrid 四种策略对比 |

### 结果

**keyword + cross-lingual bridge** 是唯一有效的跨语言策略：

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| cross_lingual_recall@10 | **0.00** | **0.76** |
| monolingual_recall@10 | 1.00 | 1.00（未退化） |
| language_diversity | 0.00 | 0.31 |

对比其他后端：

| Strategy | Backend | Cross Recall |
|----------|---------|:-----------:|
| keyword | n/a | **0.7647** |
| vector | bge | 0.1765 |
| hybrid | bge | 0.6471 |

### 对 L2 决策的影响

条件①（retrieval 中英跨语匹配）**部分缓解**：

- ✅ 关键词层面的跨语言召回显著改善（0.76），中文查询可以找到英文文献
- ✅ 改进是确定性的、离线的，不引入新依赖，不改变默认路径
- ✅ 现有 50 题 RAG eval 通过率无退化（347 测试全绿）

**但仍不足够翻转 L2**：

- ⚠️ BGE embedding 层面的跨语言匹配依然薄弱（0.1765）；BGE-cosine 预筛门（条件②）在中英跨语场景下仍会拦截
- ⚠️ NLI gate 拦截率取决于 LLM 生成的 claim 是否被其引用的 chunk 充分蕴含；keyword bridge 改善了"找到英文 chunk"的能力，但不改善"LLM 改写是否忠实"（条件③）
- ⚠️ 最终验证仍需真人 reviewer 用真实 LLM + NLI gate 重新走查

### 决策

**L2 不翻转，保持 L1。** 条件① 从阻塞降级为部分缓解，但条件②（BGE 阈值）和条件③（LLM claim 质量）未解决。若后续重新评估 L2 翻转，三条件现状更新为：

| 条件 | 当前状态 | 难度 |
|------|---------|------|
| ① retrieval 中英跨语匹配 | ✅ 部分缓解（keyword bridge, 0.76 cross recall） | 低（可继续扩展术语映射覆盖剩余 4/17 弱召回题） |
| ② BGE 阈值重新校准 | ❌ BGE-cosine 模型类限制未解决（NLI gate 作为替代存在但需 BGE 先放行） | 中（需 BGE 预筛门槛调低 + NLI 二级 gate 配合验证） |
| ③ LLM claim 质量控制 | ❌ openCode Go 自由改写风格未变 | 高（需 prompt 层约束） |

**回滚不变**：`QIYAN_LLM_PROVIDER=deterministic` 或清空即时关闭。
