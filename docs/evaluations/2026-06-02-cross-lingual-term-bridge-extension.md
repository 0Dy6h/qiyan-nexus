# 跨语言术语桥扩展评估 — 2026-06-02（条件①收尾，纯数据 + 诚实上限）

## 背景与目标

ADR-0012 更新（四）把 L2 翻转的**条件①「retrieval 中英跨语匹配」**列为「部分缓解」，剩余增量是「可继续扩展术语映射覆盖剩余 4/17 弱召回题」。`run_cross_lingual_retrieval_eval()`（keyword 策略，top_k=10，17 道双语题）扩展前 `avg_cross_lingual_recall = 0.7647`（13/17 完美），4 题为 `0.0`：rag-eval-011 / 020 / 035 / 047。

本轮以**纯数据**（只改 `backend/data/retrieval/cross_lingual_terms.json`）闭合可桥接的题，**不动默认检索排序**，并诚实记录数据手段无法闭合的结构性上限。

## 方法：诊断先行

先用只读诊断打印 4 个失败题的注入 token、`cross_lingual_recall` 与 `rank()` 全量排名（id, score, language_bonus），定位每题期望英文文献的实际排名位置与根因，再决定加哪个桥词、挂到哪个条目。

两条被验证的底层机制（`backend/app/services/retrieval/provider.py`）：

1. **`+7` chunk tag-bonus 只对 8 个硬编码 `_KEYWORD_ALIASES` 键生效**（`gut / skin_barrier / immune / pruritus / formula / network / pediatric / targeted_therapy`）。跨语桥注入的 **canonical token 若恰好等于某个 `_KEYWORD_ALIASES` 键，就能触发该 `+7`**（`alias_tag_bonus` 只看 `token in _KEYWORD_ALIASES`）。→ 把「微生态」挂到 canonical=`gut` 的条目上，命中带 `gut_skin_axis` 标签的英文文献可吃到 `+9`（item +2 / chunk +7），这是纯数据能用的最强杠杆。
2. **eval harness 直接调 `rank()`，绕过 `answer_question` 的跨语 surfacing**（`retrieval_eval.py`）。而那个 swap 很窄（`rag.py`：仅 `top_k>=3` 触发，默认 `top_k=2` 不触发，且只换入 1 篇），所以 eval 的 raw-rank 数值是合理的检索质量代理，不是被低估的假象。

## 诊断结果：4 题根因各异

| 题 | 期望英文文献 | 扩展前排名 (rank, score) | 根因 | 纯数据可修？ |
|---|---|---|---|---|
| **rag-eval-011**「比较中英文献对 AD **微生态**研究的关注点」 | 40100002, 40100009 | 40100002 **rank 12 (score 2)**；40100009 rank 20 | 查询词「微生态」**触发不了任何 microbiome/gut 桥**，只注入 `atopic_dermatitis`，期望英文文献拿不到主题性跨语 token | **能**（真缺桥） |
| **rag-eval-035**「肠道菌群结构改变和 AD 免疫稳态…」 | 40100002 | 40100002 **rank 11 (score 13)**，cutoff 14 | 桥已触发（肠道菌群→gut，40100002 已吃 gut bonus），但被「免疫稳态」注入的免疫向英文文献（40100001/40100005=14、40100007=15）与单字 CJK 淹没的中文文献（microbiome-003=42）挤出 | 否（结构性） |
| **rag-eval-047**「把肠道菌群与皮肤屏障整合到 AD 综述」 | 40100002 | 40100002 **rank 11 (score 12)** | 皮肤屏障+肠道菌群把大量文献抬进 score 12–13 密集簇，40100002 仅差 1 名 | 否（结构性） |
| **rag-eval-020**「引用 AD 文献最少应满足哪些合规要求」 | 40100004 | 40100004 **rank 14 (score 2)** | 合规题，期望的「草药系统综述」与问题无任何主题重叠 | 否（弱标注） |

## 改动（纯数据，一处）

`backend/data/retrieval/cross_lingual_terms.json` 的 `gut` 条目 `zh` 增加 `"微生态"`：

```json
{ "canonical": "gut", "zh": ["肠", "肠道", "肠-脑", "微生态"], "en": ["gut", "microbiome", "intestinal", "microbiota"] }
```

理由：AD/TCM 语境中「微生态」≈「肠道微生态」，落在 gut/microbiome 簇语义正确；且 `gut` canonical 是 `_KEYWORD_ALIASES` 键，注入后让带 `gut_skin_axis` 标签的 40100002 吃到 `+9` tag-bonus，从 score 2 升到 13，进入 top-10（rank 6）。**全 50 题中只有 rag-eval-011 含「微生态」，故零副作用**（诊断确认仅 011 的 cross_recall 变化）。

未改 `provider.py`、`_KEYWORD_ALIASES`、任何排序键，默认检索路径行为不变。

## 结果

| 指标 | 扩展前 | 扩展后 |
|---|---:|---:|
| avg_cross_lingual_recall | **0.7647** | **0.7941** |
| avg_monolingual_recall | 1.0000 | 1.0000（未退化） |
| avg_mrr | 0.8578 | 0.8873 |
| 完美跨语题（cross=1.0） | 13/17 | 13/17 |
| rag-eval-011 cross_recall | 0.0 | **0.5**（40100002 进 top-10 @rank 6） |

- **rag-eval-011**：`0.0 → 0.5`。40100002 召回；**40100009 仍在 top-10 外**——它缺 `gut_skin_axis` 标签（标签为 microbiome/skin_barrier/flare），而 011 查询不含「屏障」，纯数据无法给它 `+7`。这是**已知结构性上限**，不强行用语义错误的映射（如「微生态→skin_barrier」）去凑 1.0。
- **rag-eval-035 / 047 / 020**：维持 `0.0`，根因是 raw-rank 评分结构（中文单字 token 淹没 + `+7` tag-bonus 仅限 8 键）与弱跨语标注，**不属本轮纯数据范围**。

## 验证

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests\test_cross_lingual_eval.py -q   # 22 passed
& .\.uv-test-venv\Scripts\python.exe -m ruff format --check app tests                # clean
& .\.uv-test-venv\Scripts\python.exe -m ruff check app tests                         # clean
& .\.uv-test-venv\Scripts\python.exe -m mypy app                                     # clean
& .\.uv-test-venv\Scripts\python.exe -m pytest -q                                    # 361 passed
```

新增回归锁：`test_rag_eval_011_cross_lingual_recall_above_zero`（011 cross>0 且 40100002 在 top-10）、`test_cross_lingual_term_bridge_no_aggregate_regression`（avg_cross ≥ 0.7647 且 mono == 1.0）。

## 对 L2 决策的影响

条件①进一步收敛：从「部分缓解」到「**关键词跨语桥已覆盖可桥接题，011 闭合**」。但 035/047/020 揭示：纯术语桥的天花板已到——剩余跨语失败不是「缺词」，而是 raw-rank 评分结构（中文单字淹没、`+7` 仅限 8 键）与个别弱标注。**L2 仍不翻转**；任何进一步跨语提升需独立、更大的决策，不属本轮纯数据范围。

## 范围外 / 后续候选（独立决策）

1. **受控打分修复**：让 `microbiome` 参与 `+7` tag-bonus，或抑制中文单字 token 淹没——会改默认检索排序，需全量重验 50 题 RAG eval。可救回 035/047（两者均仅差 1 名）。
2. **expected-label 复核**：rag-eval-020（合规题配草药综述）、rag-eval-011 的 40100009 是否为合理跨语期望。
3. **多语 embedding**（bge-m3 / multilingual-e5-large）替代/补充 keyword 桥——更大的架构方向。

---

*评估日期：2026-06-02 | 配置：keyword 检索 + 跨语术语桥，离线确定性，无外部依赖*
