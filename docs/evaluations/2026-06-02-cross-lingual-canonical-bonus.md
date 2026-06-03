# 跨语言 canonical tag-bonus 扩展评估 — 2026-06-02（Slice 7，受控打分修复）

## 背景与目标

`docs/evaluations/2026-06-02-cross-lingual-term-bridge-extension.md` 把「受控打分修复：让 `microbiome` 参与 `+7` tag-bonus」列为 Slice 6 后的范围外候选 1。本轮（Slice 7）执行该方向，闭合 rag-eval-035 / 047 两道仅差 1 名的题。

## 根因复述（来自 Slice 6 诊断）

`backend/app/services/retrieval/provider.py:173-180` 的 `alias_tag_bonus` 只对**硬编码的 8 个 `_KEYWORD_ALIASES` 键**（gut / skin_barrier / immune / pruritus / formula / network / pediatric / targeted_therapy）发 `+2` item / `+7` chunk 奖励，**完全不识别** `tokenize_query` 从 `cross_lingual_terms.json` 注入的 17 个 cross-lingual canonical（`microbiome / atopic_dermatitis / tcm_syndrome / neuroimmune / quality_of_life / …`）。

后果：当中文查询「肠道菌群结构改变…」触发 `microbiome` canonical 注入、目标文档（pmid-40100002）的 chunk 又携带 `microbiome` 标签时，结构性 `+7` 奖励**静默丢失**，英文文档相对中文被压制。035 / 047 双双卡在 rank 11。

## 改动（最小 surgical fix）

`alias_tag_bonus` 的 canonical 识别集从 `_KEYWORD_ALIASES.keys()` 扩展为「`_KEYWORD_ALIASES.keys()` ∪ `cross_lingual_terms.json` 中所有 canonical」：

```python
def _canonical_token_set() -> set[str]:
    canonicals: set[str] = set(_KEYWORD_ALIASES.keys())
    cross_map = _load_cross_lingual_aliases()
    for entry in cross_map.get("alias_map", []):
        canonical = entry.get("canonical", "")
        if canonical:
            canonicals.add(canonical)
    return canonicals
```

权重保持 `+2` / `+7` 不变。无 API、Schema、env、router、repository 变化。

## 结果

| 指标 | Slice 6 后 | Slice 7 后 |
|---|---:|---:|
| `avg_cross_lingual_recall` | 0.7941 | **0.9118** |
| `avg_monolingual_recall` | 1.0000 | 1.0000（未退化） |
| `avg_mrr` | 0.8873 | 0.8823 |
| 完美跨语题（cross=1.0） | 13/17 | **15/17** |
| rag-eval-011 cross_recall | 0.5 | 0.5（pmid-40100009 仍缺标签，已知上限） |
| rag-eval-035 cross_recall | 0.0 | **1.0**（pmid-40100002 进 top-10） |
| rag-eval-047 cross_recall | 0.0 | **1.0**（pmid-40100002 进 top-10） |

## 副作用 & 缓解

对纯中文查询「特应性皮炎和肠-脑-皮肤轴有什么关系？」，top-1 从 `cn-ad-gbs-001` 切到 `cn-ad-microbiome-003`：

- `chunk-microbiome-003` 标签 `["microbiome", "gut_skin_axis", "immune_pathway"]` 现在吃 `+14`（gut + microbiome 各 +7）
- `chunk-gbs-001` 标签 `["gut_skin_axis", "tcm_syndrome", "skin_barrier"]` 仍只吃 `+7`（gut）
- 两文档都在 top-2，**rag-eval-001 把两者都列为 expected_literature**，因此是合理 tie-break swap，不是质量回退
- 7 个固定 top-1 的测试已对应更新；3 个 provider-swap mock 加 `QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0`（mock claim 文本原本为 gbs-001 wording 定制，sem 重叠下降，与该测试主题无关，沿用 `test_answer_question_estimates_cost_from_tokens_and_env_prices` 的同种豁免）

## 验证

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_cross_lingual_eval.py -q   # 25 passed
.venv/Scripts/python.exe -m ruff format --check app tests                # clean
.venv/Scripts/python.exe -m ruff check app tests                         # clean
.venv/Scripts/python.exe -m mypy app                                     # clean
.venv/Scripts/python.exe -m pytest -q                                    # 447 passed, 1 skipped
```

新增回归锁：
- `test_alias_tag_bonus_honours_cross_lingual_canonicals`（单元，覆盖 microbiome / atopic_dermatitis canonical 都吃 +weight）
- `test_rag_eval_035_cross_lingual_recall_equals_one`（035 单题 cross=1.0 且 pmid-40100002 在 top-10）
- `test_rag_eval_047_cross_lingual_recall_equals_one`（047 同上）
- `_CROSS_LINGUAL_RECALL_BASELINE` 从 `0.7647` 收紧到 **`0.9118`**

## 对 L2 决策的影响

条件①「retrieval 中英跨语匹配」从 Slice 6 的「关键词跨语桥已覆盖可桥接题，011 闭合」收紧到「**关键词跨语桥 + canonical tag-bonus 已覆盖可桥接题，015/17 完美**」。但 L2 仍不翻转：剩余拦点是 NLI low-entailment 60% 拦截率（见 `2026-06-02-claim-quality-v2-live-validation.md`），与 retrieval recall 无关。

## 范围外 / 仍开放（独立决策）

1. **rag-eval-011 的 pmid-40100009**：缺 `gut_skin_axis` 标签，纯打分扩展救不回。数据侧补标签需要 expected-label 审计（Slice 6 handoff 已列）。
2. **rag-eval-020**：合规题与「草药系统综述」期望弱关联，仍属 expected-label 审计候选。
3. **多语 embedding**（bge-m3 / multilingual-e5-large）替代或补充 keyword 桥，跨架构方向。
4. **L2 翻转**：阻塞点不在 retrieval 而在 grounding（NLI 阈值或 BGE prefilter 重新校准）。

---

*评估日期：2026-06-02 | 配置：keyword 检索 + 跨语术语桥 + canonical tag-bonus 扩展，离线确定性，无外部依赖*
