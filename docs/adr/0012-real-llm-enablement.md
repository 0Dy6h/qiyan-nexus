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

## 2026-06-01 更新（五）：Claim 质控 prompt/schema v2 落地，默认仍不翻转

针对更新（三）（四）中识别的条件③「openCode Go 自由改写、跨 chunk 综合、额外推断」，
已落地一轮 AFK 可测的 claim 质控收紧：

- `GROUNDING_SYSTEM_PROMPT` 明确要求每条 claim 只能引用 1 个证据 ID，并且只能由该证据 ID
  对应的 `证据文本` 直接蕴含。
- prompt 明确禁止跨引用综合，禁止把多个证据片段合并成一条 claim。
- prompt 明确禁止添加引用片段没有明示的治疗疗效、靶点、生活质量、因果或指南地位。
- 发给 provider 的 citation 文本把 `证据文本（claim 只能基于此字段）` 与标题、来源、匹配依据、
  置信度等元数据分离，减少模型把元数据扩写成事实 claim 的机会。
- OpenCode Go function schema 从最多 4 条 claim 收紧为最多 3 条 claim，并要求每条 claim 最多
  1 个 `evidence_ref`。兼容 structured-claims v3 的后端解析与 grounding 校验保持不变。
- `/rag` 前端类型、元数据区与 Markdown 导出补齐 NLI 字段：
  `nli_threshold`、`min_entailment_score`、`structured_claims[].entailment_score`。

**决策不变**：这不是 L2 默认翻转。默认 RAG 路径仍为离线 `deterministic`；真实 provider 仍只在
L1 受控 smoke/演示中通过 env 显式启用。该收紧降低了 provider 生成越界 claim 的概率，但真实效果
必须通过有 key 的 live 采样重新验证，不能由离线单测替代。

**下一次重新评估 L2 时的额外验收**：

1. 用 `backend/scripts/capture_real_answer_claims.py` 对 prompt/schema v2 重新采集 5-10 个真实问题。
2. 记录每条回答的 `claim_count`、每条 claim 的 `evidence_refs` 数量、`blocked_reason`、
   `semantic_score` 与 `entailment_score`。
3. 确认没有 raw provider draft 泄漏；blocked 时仍只展示 hard-block 文案与 citation cards。
4. 若仍全部 blocked，保持 L1；若出现 passed 回答，再做 reviewer 逐条核对后单独记录启用判断。

## 2026-06-02 更新（六）：Claim 质控 v2 live validation 完成，L2 仍不翻转

按更新（五）的额外验收，已用真实 `opencode_go` key 对 prompt/schema v2 重新采样 10 个问题。
记录见 `docs/evaluations/2026-06-02-claim-quality-v2-live-validation.md`，runtime 原始采样为
`backend/data/runtime/captured_real_claims_live_20260602_0846.json`（gitignored，不提交）。

### 配置

- `QIYAN_LLM_PROVIDER=opencode_go`
- `QIYAN_OPENCODE_GO_MAX_TOKENS=4000`
- `QIYAN_EMBEDDING_BACKEND=bge`
- `QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0.3`
- `QIYAN_NLI_BACKEND=transformers`
- `QIYAN_NLI_THRESHOLD=0.5`

`BGE=0.3` 是本次技术验证 profile：上一轮 §4c 已证明 `BGE=0.78` 会在真实跨语/改写 claim 上先于
NLI 过度拦截。本次降低 cosine 预筛是为了让 NLI gate 评估事实蕴含，不代表默认预览配置。

### 结果

| 指标 | 结果 |
|---|---:|
| 问题数 | 10 |
| claim 总数 | 14 |
| provider fallback | 0 |
| grounding passed | 4 个回答 |
| grounding blocked | 6 个回答 |
| blocked reason | 6 个 `nli_low_entailment` |
| 0 evidence ref claims | 0 |
| 1 evidence ref claims | 14 |
| multi evidence refs claims | 0 |
| unsupported ref / schema parse failure | 0 |
| semantic score range | 0.3394-0.9553 |
| entailment score range | 0.0004-0.9990 |

快速 claim-level review 显示 4 个 passed 回答均可从其 cited chunk 直接核对：英文 PubMed chunk 支撑
filaggrin/barrier/JAK-STAT/network-pharmacology claims，中文 consensus chunk 支撑长期管理 claim。
但这只是技术走查，不是正式医生/科研 reviewer sign-off。

### 决策

**L2 仍不翻转，保持 L1。**

本次 live validation 的正面结论是：claim-quality v2 已明显改善结构化输出质量（14/14 单证据引用，
无 unsupported refs，无 parse failure），并且在 `BGE=0.3 + NLI=0.5` profile 下首次出现 4 个
真实 provider passed 回答。负面/未闭合点是：该 profile 需要显式降低 BGE 预筛；NLI 仍拦截 6/10
回答；成本 SLI 仍未配置真实合同价格；正式 reviewer sign-off 尚未完成。

后续若继续推进 L2，不应再做“是否能调用真实模型”的工程验证，而应聚焦三件事：

1. 正式 reviewer 逐条核验 4 个 passed 回答的 claim 与 cited chunk。
2. 单独决策是否接受 lower-BGE-prefilter + NLI gate 作为 L1/L2 profile。
3. 配置真实 `QIYAN_OPENCODE_GO_PRICE_*` 并记录成本/延迟 SLI 基线。

## 2026-06-02 更新（七）：Passed-claim reviewer packet 已生成，避免重复 §4c 走查

针对更新（六）的第 1 项，已新增 `backend/scripts/build_reviewer_packet.py`，从 gitignored
runtime capture `backend/data/runtime/captured_real_claims_live_20260602_0846.json` 抽取 4 个
`grounding.status="passed"` 的回答，生成正式 reviewer 可填写的 delta-only packet：
`docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md`。

该 packet 覆盖 `rag-eval-005`、`rag-eval-007`、`rag-eval-008`、`rag-eval-010`，逐条列出
claim、唯一 evidence ref、cited chunk text、semantic score、entailment score、latency/token/cost
字段，以及 `supported` / `unsupported` / `unclear` verdict 空位。脚本会拒绝缺失 question id
或非 passed question，并对非单 evidence-ref claim 给出 warning；输出会脱敏 key-like 字符串。

**边界**：这不是新的 §4c reviewer walkthrough。2026-06-01 的 §4c 已验证 gate、fallback、
rollback 和 UI metadata 行为；本 packet 只处理 2026-06-02 新出现的 passed claims 的
claim-vs-chunk verdict。verdict 尚未填写，因此正式 reviewer sign-off 仍未完成。

**决策不变**：L2/default preview 仍不翻转；默认路径保持离线 `deterministic`。后续治理只应基于
packet verdict、真实价格 SLI 和单独 ADR 决策推进，不应重复“真实 provider 能否调用”或完整 §4c。

## 2026-06-02 更新（八）：Codex technical verdict 已填

`docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md` 已由 Codex 完成技术性
claim-vs-chunk 支撑核对。范围仅限 2026-06-02 live capture 中 4 个 passed answers 的 6 条
claims：

| Verdict | Count |
|---|---:|
| supported | 6 |
| unsupported | 0 |
| unclear | 0 |

技术判断：6 条 claim 均可由各自 cited chunk 直接支持，没有发现 evidence-ref 越界、跨 chunk
综合或证据外疗效/指南地位扩写。该结果支持 `BGE=0.3 + NLI=0.5` profile 继续作为 L1 受控
demo/evaluation profile 使用。

**边界**：这不是正式 clinician/research reviewer sign-off。正式 reviewer 仍需确认或修订 packet
中的 6 条 verdict；真实价格 SLI 也仍未闭合。

**决策不变**：L2/default preview 仍不翻转；默认 provider 仍为离线 `deterministic`。后续如要
考虑默认预览启用，必须先完成正式 reviewer 确认、真实价格 SLI，并另行做 ADR-quality profile
决策。

## 2026-06-02 更新（九）：Price SLI baseline 已记录，L2 仍不翻转

已补齐 2026-06-02 live capture 的成本/延迟 SLI 基线：
`docs/evaluations/2026-06-02-opencode-go-price-sli-baseline.md`。

配置价格：

| Env | Value |
|---|---:|
| `QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK` | `0.14` |
| `QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK` | `0.28` |

该价格对应当前 `deepseek-v4-flash` 公开 token 价格基线（input `$0.14` / 1M，output `$0.28` / 1M）。
因 capture artifact 只记录 `prompt_tokens` / `completion_tokens`，未区分 cache hit / cache miss，基线按
cache-miss input 计算，偏保守。

2026-06-02 10 题 capture 成本/延迟：

| Metric | Value |
|---|---:|
| Input tokens | 6,040 |
| Output tokens | 14,984 |
| Estimated total cost | `$0.005042` |
| Passed-answer cost | `$0.002301` |
| Blocked-answer cost | `$0.002741` |
| Provider latency | min 5.252s / avg 13.148s / max 28.540s |

**解释**：成本基线已闭合到 captured profile 级别；原始 capture 中 `estimated_cost_usd=null` 仍正确，
因为当时未配置 `QIYAN_OPENCODE_GO_PRICE_*`。生产预算前仍需复核 OpenCode Go / DeepSeek 实际合同
价格与 billing 口径。

**决策不变**：L2/default preview 仍不翻转；默认 provider 仍为离线 `deterministic`。当前剩余前置
主要是正式 reviewer 确认 Codex technical verdict，以及是否接受 `BGE=0.3 + NLI=0.5` profile 的
单独治理决策。

## 2026-06-02 更新（十）：Passed-claim verdict 已由用户确认，L2 仍不翻转

用户已确认 `docs/evaluations/2026-06-02-l2-passed-claims-reviewer-packet.md` 中 6 条
Codex technical evidence-support verdict，无需修订：

| Verdict | Count |
|---|---:|
| supported | 6 |
| unsupported | 0 |
| unclear | 0 |

该确认闭合了 2026-06-02 passed-claim verdict delta。结合更新（九），当前 L2 线的已完成项包括：

- §4c gate/fallback/rollback/UI metadata 真人走查已完成（2026-06-01）。
- claim-quality v2 live validation 已完成（10 题，4 passed / 6 blocked）。
- passed-claim evidence-support verdict 已确认（6 supported / 0 unsupported / 0 unclear）。
- price SLI baseline 已记录（10 题估算 `$0.005042`，provider latency avg 13.148s）。

**决策不变**：L2/default preview 仍不翻转；默认 provider 仍为离线 `deterministic`。剩余问题不再是
“是否能调用真实 provider”或“passed claims 是否有证据支持”，而是治理选择：是否接受
`BGE=0.3 + NLI=0.5` 这个 lower-BGE-prefilter profile 进入 L2/default-preview 讨论。任何默认切换
仍必须另起 ADR-quality profile decision，并在生产预算前复核实际合同价格。

## 2026-06-02 更新（十一）：跨语言术语桥扩展 — 条件① 纯术语桥到顶，L2 仍不翻转

按更新（四）条件①「可继续扩展术语映射覆盖剩余 4/17 弱召回题」，做了一轮**纯数据**术语桥扩展
（记录见 `docs/evaluations/2026-06-02-cross-lingual-term-bridge-extension.md`）。

**诊断先行**发现 4 个弱召回题根因各异：只有 **rag-eval-011** 是真正缺桥（查询词「微生态」触发不了
任何 microbiome/gut 桥），其余 3 题受 raw-rank 评分结构所限：**035/047** 是中文单字 token 淹没英文
文献（40100002 仅差 1 名落在 rank 11），**020** 是合规题、期望「草药系统综述」与问题无主题重叠（弱标注）。

**改动**：`backend/data/retrieval/cross_lingual_terms.json` 的 `gut` 条目 zh 加「微生态」一词。`gut`
canonical 同时是 `_KEYWORD_ALIASES` 键，注入后让带 `gut_skin_axis` 标签的 40100002 吃到 `+7` chunk
tag-bonus，从 score 2 升到 13 进入 top-10。全 50 题仅 rag-eval-011 含「微生态」，零副作用。未改
`provider.py` / 排序键，默认检索路径不变。

**结果**：

| 指标 | 前 | 后 |
|---|---:|---:|
| avg_cross_lingual_recall | 0.7647 | **0.7941** |
| avg_monolingual_recall | 1.0 | 1.0（未退化） |
| rag-eval-011 cross_recall | 0.0 | **0.5**（40100002 进；40100009 缺 gut_skin_axis 标签，纯数据无法拉进，属已知上限） |

新增回归锁 `test_rag_eval_011_cross_lingual_recall_above_zero` 与
`test_cross_lingual_term_bridge_no_aggregate_regression`；全量 361 测试 + ruff/mypy 全绿。

**条件① 状态更新**：

| 条件 | 当前状态 | 难度 |
|------|---------|------|
| ① retrieval 中英跨语匹配 | ✅ **纯术语桥已到顶**（0.7941 cross recall，011 闭合）。剩余 035/047/020 不是缺词，而是 raw-rank 评分结构（中文单字淹没 + `+7` tag-bonus 仅限 8 个 `_KEYWORD_ALIASES` 键）与弱标注 | 余量需**受控打分修复**（改默认排序，中风险）或多语 embedding，属独立决策 |
| ② BGE 阈值重新校准 | ❌ 未解决（NLI gate 作为替代存在但需 BGE 先放行） | 中 |
| ③ LLM claim 质量控制 | 🟡 prompt/schema v2 已落地并 live 验证结构改善（更新五/六），但默认风格未根治 | 高 |

**决策不变**：L2/default preview 仍不翻转，默认 provider 仍为离线 `deterministic`。本轮只把条件① 的
纯数据余量收口，并明确「纯术语桥天花板」；任何进一步跨语提升（受控打分 / 多语 embedding）需独立决策。
**回滚不变**：`QIYAN_LLM_PROVIDER=deterministic` 或清空即时关闭。
