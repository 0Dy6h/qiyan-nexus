# Session Wrap + Handoff — 2026-06-01 (Slices 1-6, Final)

branch: feat/l2-real-llm-promotion (15 commits ahead of origin/main)
default RAG path: offline deterministic, unchanged
gauntlet: backend 324 passed, mypy/ruff clean

---

## 交付清单

| # | 内容 | Commit |
|---|---|---|
| T0 | 分支收口（push feat + chore 分支） | — |
| 1 | `scripts/capture_real_answer_claims.py`（live + offline 双模式） | cf3d6e5 |
| 2 | `grounding_real_answer_pairs.json`（20 对标注验证集）+ 8 fixture tests | 04a494a |
| 3 | `run_nli_real_distribution_eval()` + 评估脚本 — **0 FP, 0 FN, gap +0.9549** | 2a1d764 |
| 4 | `entailment_batch()` — NLI 批处理，~1.1x speedup | 959acba |
| 5 | §4c walkthrough checklist + current-state 刷新 | 496be82 |
| 6 | ADR-0012 走查 addendum — **决策：L2 不翻转，保持 L1** | f515e7c |

---

## 关键决策

**L2 不翻转。** NLI gate 工程成熟度已验证（3 fixture × 0 false accept + 生产走查），但 BGE=0.78 + keyword retriever 跨语匹配弱 + openCode Go 自由改写导致生产上无回答穿透。保持 L1（受控启用）：设 3 个 env var 即可开启真实 provider。

## 新增文件

- `backend/scripts/capture_real_answer_claims.py`
- `backend/scripts/eval_nli_real_distribution.py`
- `backend/data/evals/grounding_real_answer_pairs.json`
- `backend/tests/test_real_answer_pairs_fixture.py`
- `docs/evaluations/2026-06-01-nli-real-distribution.md`
- `docs/handoffs/2026-06-01-slices-1-5.md`

## 修改文件

- `backend/app/services/nli.py`（+entailment_batch）
- `backend/app/services/grounding.py`（batch NLI + bugfix min_entailment_score）
- `backend/app/services/eval.py`（+run_nli_real_distribution_eval）
- `backend/app/schemas/eval.py`（+RealAnswerPair）
- `backend/scripts/bench_nli_latency.py`（+batch comparison）
- `backend/tests/test_grounding_nli.py`（+entailment_batch）
- `docs/adr/0012-real-llm-enablement.md`（2026-06-01 更新三）
- `docs/current-state.md`（L2 状态更新）
- `docs/checklists/internal-preview-smoke.md`（§4c 走查节 + 完成记录）

## 下一步候选

1. **retrieval 改进**：keyword 匹配对中英跨语题支持弱，BGE cross-lingual 分低。可考虑 bilingual retrieval 或中文 seed 增强。
2. **BGE 阈值重校**：0.78 来自 easy fixture，对真实 LLM 改写过严。在 retrieval 改进后可重新扫描。
3. **LLM prompt 约束**：openCode Go 自由改写常额外推断。可试验 structured prompt 限制 claim scope。
4. **网络图可视化**（MVP-B 增强）：用户可见、演示力强。
5. **PDF 抽取质量**：表格重建、OCR 探索。

## 回滚操作

`QIYAN_LLM_PROVIDER=deterministic`（或清空）即时回滚，无需改代码。
