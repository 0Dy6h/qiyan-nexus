# 2026-09-11 记录：Track A 标签接受 + 3 行 compound-target 判定处置

- date: 2026-09-11
- 执行方：小蒜香（白班助理），研究者本人复核
- 关联：`docs/reports/2026-08-17-pubmed-seed-expansion-batch2-5-changelog.md`、`docs/adr/0018-open-questions-brief.md`（Q7）

## 一、Track A 150 标签：研究者接受，节点关闭

### 事实
- 30 题 × top-5 = 150 个相关性标签；语料 693 篇 `pubmed_live`；工程侧标注迭代至 p@5=0.400 / MRR@5=0.744（v6，详见关联 changelog）。
- 标签产生方式：**工程侧（AI）辅助标注 + 对抗性审查修正**，非独立真人盲标（worksheet manifest 保密纪律未构成「真人独立盲标」实验）。

### 接受口径（如实声明，不冒充）
- 研究者本人（丁祎涵）于 2026-09-11 复核该批标签结论并接受，作为默认检索质量的参考基线（precision@5 / MRR@5）。
- **不是**独立真人盲标实验；如需对外（论文/合作交付）声称「真人盲标验证」，须按 `docs/guides/track-a-labeling-guide.md` 另出题集由真人独立标注（对齐 0018 简报附加条件 6/7）。
- 标签结论仍以「AI 辅助 + 研究者复核接受」的 provenance 存档，不改写为「独立人工标注」。

## 二、3 行 compound-target 待判定：核实为 mock 样例行，不进入正式判定

### 核实过程（2026-09-11）
- 全仓扫 pending adjudication，唯一可复现的「3 行」集合在 `.tmp/gate2-evidence/run1-result.json`（消风散任务 `network-3c71351406fb48169602c187f3329140`，2026-08-15）：
  - IL6（source_score 0.87）、STAT3（0.79）、TNF（0.82）
  - 三行全部 `evidence_origin=mock`、`source_database=qiyan_sample_network`（样例数据）
- 平台自身警告：「当前任务使用 mock 数据，不能进入正式网络药理学研究」；`readiness.blocking_reasons` 亦如此表述。

### 处置建议（小蒜香出具，待研究者复核）
1. **对 mock 样例行不做 included/excluded 判定**——判定没有生物学意义，签了反而会在审计链留下「有人判定过」的虚假印象。
2. 保持 `adjudication_status=pending` 不动；等真实双侧 verified 导入（Open Targets + ChEMBL，`server_verified_raw_artifact`）落地后，再对真实行做逐行 adjudication（届时行数另行核实）。
3. 本记录未写入任何 runtime adjudication 数据。

*本记录为事实存档；未经研究者复核确认前，第二节「处置建议」不视为已拍板。*
