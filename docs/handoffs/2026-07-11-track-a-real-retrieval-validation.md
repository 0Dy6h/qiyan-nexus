# Track A 真实检索验证交接（2026-07-11）

## Goal

把优先级从继续加固内部对象边界，切回核心价值验证：在独立真实 PubMed corpus 上，对产品实际展示的 keyword top-5 做非循环、rank/score-blind 的真人相关性评估。

## Completed

- 修复原 blind harness 的三个根本性偏差：
  - 不再直接评估 `provider.rank()`；改为复用 `answer_question()` 的实际 citation selection。
  - reviewer worksheet 不再暴露 rank、score 或排序；候选确定性打乱，真实 rank 单独写入 private manifest。
  - real-only 模式对 synthetic seed、live 数不足、非布尔标签、worksheet/manifest 不匹配 fail closed。
- 指标改为准确命名的 `precision@k` / `MRR@k`；缺失 top-k 槽位按不相关计入分母；recall 明确不计算。
- `seed_pubmed_corpus.py` 新增 `--runtime-root`、`--resume`、`--min-live-records`，可显式创建空 JSON runtime，避免 resolver 自动复制 20 条 seed。
- 新增 30 题 held-out v1 候选问题集，无 expected IDs；其状态明确为待真人 domain reviewer 接受，不能冒充专家原创。
- 基于已有 344/344 `pubmed_live`、0 seed 快照生成首版 30×5 packet。全部 150 个标签为空，因此当前 `precision@5` / `MRR@5` 均为 `null`，没有伪造 baseline。
- 新增正式运行指南 `docs/guides/retrieval-validation-track-a.md`。

## Verified facts

- worksheet ID：`rag-blind-3a50687a3424ac3b`
- query-set SHA-256：`2b734b4999d620a65005f07499a208ad617c1b8346187252bda0c68797c22d0b`
- corpus SHA-256：`861cd184e0081dd12573e81db81a9c4134cc9fea4a07bbb7903a1fd83c34a34d`
- corpus：344 real / 0 seed；chunks：0，chunk SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`（PubMed keyword item-text baseline）
- strategy：keyword；selection mode：`rag_answer_citations`
- queries：30；full top-5：30；zero-result：0
- labels：0/30 complete，150/150 candidate labels 为 null
- 聚焦测试：14 passed；最终统一门禁为 backend `640 passed, 1 skipped`、frontend `229 passed`、typecheck/build 全绿；同一工作树的 Playwright branch closeout 为 `4 passed`，其后改动仅限 backend operator scripts/tests 与文档；`pnpm audit --prod` 为 0 known vulnerabilities；最终 ruff format/check 全绿

## Deliberately not changed

- 未调整 alias/tag bonus、off-topic 阈值或排序权重，避免在第一份真人 baseline 前继续调参。
- 未修 `match_score` top hit 饱和；private manifest 保留 displayed match score，待真人 baseline 后单独做透明度切片。它不参与盲标展示。
- 未推进 `PdfUploadRecord` owner isolation；在核心检索价值数字出现前继续暂缓。
- 未 push、未提交 `.tmp` 语料/worksheet/manifest，也未触碰本机 `.mcp.json`、`components.json`。

## Exactly one recommended next slice

由一名未参与检索器调参的真实临床或科研 reviewer：先在不看 worksheet 的前提下接受 v1 问题集或另存 v2，然后只接收 blinded worksheet，完成 150 个二元相关性标签；随后运行 scorer，首次产出诚实的 `precision@5` 与 `MRR@5`。在这两个数字出现前，不改 ranker/off-topic/match-score，也不恢复 PDF owner-isolation 为主线。
