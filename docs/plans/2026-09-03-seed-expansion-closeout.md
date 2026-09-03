# 2026-09-03 方案：PubMed 种子扩展收尾（batch2-5 补记 + 提交）

> 执行人：研究者本人（2026-09-03 晚）。前置事实已核实，命令按 Windows + pwsh 照抄。
> 本方案只做收尾与文档同步，不改任何检索行为代码，不改任何测试预期。

## 0. 已核实的硬事实（写文档时直接引用，不要再猜）

| 事实 | 值 | 来源 |
|---|---|---|
| batch 查询条数 | all=46（=默认 8 + b1 12 + b2 12 + b3 14）、b1_supplement=5、b4=26、b5=8 | `backend/scripts/pubmed_seed_expansion_*.json` |
| supplement∩batch4 重复 | 2 条 | 脚本比对 2026-09-03 |
| b5 与现有 all 重复 | 0 条（8 条全为新） | 同上 |
| 合并后 all.json 应为 | **83 条 unique**（46+5+26+8−2） | 同上 |
| 语料规模 | 344 →（batch1 后）527 →（batch2-5 后）**693** `pubmed_live` | `.tmp/retrieval-validation-v1/literature_state.json`（2026-08-17 15:44）；batch1 数字见 `corpus_expansion_batch1_changelog.json` |
| 指标演进（30 题，top-5，工程侧标注） | v1 0.113/0.163 → v2 0.100/0.268 → v3 0.28/0.488 → v4 0.32/0.566 → v5 0.34/0.606 → **v6 0.400/0.744**（p@5 / MRR@5，零结果 0 题） | `.tmp/retrieval-validation-v1/metrics*.json` |
| 诚实边界 | 标签为工程侧「协助标注 + 对抗性审查」，provenance 仍为 engineering draft 待 domain review；v3→v6 的提升是**语料扩展与跨语言术语补充（commit 1624862）的合并效果**，无法按因素拆分归因；batch2-5 无逐批中间快照，只有 batch1 的 344→527 和最终 693 是硬数字 | `docs/handoffs/2026-08-17-track-a-labeling-and-retrieval-tuning.md`、`.tmp` 产物 |
| 未提交物 | `backend/scripts/pubmed_seed_expansion_batch5.json`（untracked）、`docs/competitive-analysis-qingtuanyun.md`（untracked）、`AGENTS.md`（modified，已是较新内容） | `git status` 2026-09-03 |

## 1. 步骤（按序执行，每步可独立提交）

### Step 0 提交本方案与 Gate 3 方案

```powershell
git add docs/plans/2026-09-03-seed-expansion-closeout.md docs/plans/2026-09-03-gate3-omics-implementation-plan.md
git commit -m "docs(plans): 种子扩展收尾方案 + ADR-0018 Gate 3 组学验证层实现计划"
```

### Step 1 合并 all.json（46 → 83 条）

```powershell
cd "D:\螃蟹's Projects\Tcm_tech"
& .\backend\.uv-test-venv\Scripts\python.exe -c "
import json, itertools
base = 'backend/scripts/pubmed_seed_expansion_'
load = lambda n: json.load(open(base + n + '.json', encoding='utf-8'))
merged = list(dict.fromkeys(itertools.chain(
    load('all'), load('batch1_supplement'), load('batch4'), load('batch5'))))
assert len(merged) == 83, f'unexpected merge size: {len(merged)}'
json.dump(merged, open(base + 'all.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print('merged:', len(merged))
"
```

注意：该文件会因 `indent`/`ensure_ascii` 与旧格式不同而整文件 diff，属预期（操作员工具输入，无代码消费方，已在 app/ 与 backend/data/ 中 grep 确认零引用）。

### Step 2 提交查询清单

```powershell
git add backend/scripts/pubmed_seed_expansion_batch5.json backend/scripts/pubmed_seed_expansion_all.json
git commit -m "feat(retrieval): 补交 batch5 查询清单并把 all.json 总表合并到 83 条（补 supplement/batch4/batch5）"
```

### Step 3 写 batch2-5 语料变更补记

新建 `docs/reports/2026-08-17-pubmed-seed-expansion-batch2-5-changelog.md`，骨架如下（数字已填好，主题清单从各 batch JSON 现抄，禁止编造逐主题候选变化）：

```markdown
# PubMed 种子扩展 batch2-5 语料变更补记（记录于 2026-09-03）

## 事实
- batch1 已有独立 changelog（.tmp，344→527，+183）。batch2-5 执行时未留存逐批中间快照，
  本补记按最终态合并记录：语料 527 → 693 pubmed_live（+168）。
- 查询清单：batch2 12 条、batch3 14 条、batch4 26 条、batch5 8 条（3 条 nemolizumab 新主题 +
  5 条马拉色菌/益生菌/MTX/AZA 改写变体）；去重后总表 all.json = 83 条。
- 逐批主题：〔从 backend/scripts/pubmed_seed_expansion_batch{2,3,4}.json 抄查询串，按主题归类〕

## 指标演进（30 题 top-5，工程侧标注，非真人 domain reviewer）
v2 0.100/0.268（344 语料基线）→ v3 0.28/0.488 → v4 0.32/0.566 → v5 0.34/0.606 →
v6 0.400/0.744（693 语料，零结果 0 题）。

## 诚实边界（不得删）
1. 标签为工程侧协助标注 + 对抗性审查，v2 题集 provenance 仍为 engineering draft 待真人
   domain reviewer 接受；在真人数字出现前不声称检索有效。
2. v3→v6 提升是语料扩展与跨语言术语补充（commit 1624862）的合并效果，未做单因素拆分。
3. batch1 changelog 与 metrics 原件在 .tmp（gitignored），本文件是唯一版本化记录。
```

```powershell
git add docs/reports/2026-08-17-pubmed-seed-expansion-batch2-5-changelog.md
git commit -m "docs: 补记 PubMed 种子扩展 batch2-5 语料变更（527→693，工程侧 v6 指标）"
```

### Step 4 提交竞品分析笔记

```powershell
git add docs/competitive-analysis-qingtuanyun.md
git commit -m "docs: 提交青团云竞品对标笔记（仅公开官网信息，非决策记录，不改 ADR-0017/0018 边界）"
```

### Step 5 刷新 AGENTS.md 两处过时表述

- **L7 仓库性质段**：把「检索质量已有实测基线：Track A 150 标签完成（precision@5=0.113、MRR@5=0.163），Track A+ 复验 MRR@5=0.268（+64%），主要失败根因是 344 篇语料的覆盖缺口而非检索器；PubMed 种子查询扩展进行中（`backend/scripts/pubmed_seed_expansion_batch5.json` 是未提交的进行中产物）。」替换为：

  > 检索质量基线：Track A 首版 150 标签（precision@5=0.113、MRR@5=0.163）；2026-08-17 种子扩展 batch1-5 完成（总表 83 条查询，runtime 语料 344→693 pubmed_live），工程侧 v2 盲评迭代至 p@5=0.400、MRR@5=0.744（补记见 `docs/reports/2026-08-17-pubmed-seed-expansion-batch2-5-changelog.md`）；标签仍是工程侧，真人 domain reviewer 数字出现前不声称检索有效。

- **L119 检索排序约束**：在「对应 Track A/A+ 实测基线（MRR@5 0.268）」后补一句：

  > （该基线对应 seed fixture 上的确定性检索；扩展语料只存在于 gitignored runtime state，不进测试语料，测试预期不受 v6 数字影响）

### Step 6 刷新 docs/current-state.md 两处

- L25 Track A 段末尾追加一句：2026-08-17 种子扩展已完成并提交（83 条查询、693 篇 runtime 语料），工程侧 v6 指标 p@5=0.400 / MRR@5=0.744，仍待真人 reviewer，详见补记文档。
- L103 「当前唯一工程主线」段末尾追加：Gate 3 组学验证层实现计划已立项（`docs/plans/2026-09-03-gate3-omics-implementation-plan.md`），代码尚未开始。
- 另起一行加竞品笔记指针：`docs/competitive-analysis-qingtuanyun.md`（仅公开官网信息，非决策记录）。

```powershell
git add AGENTS.md docs/current-state.md
git commit -m "docs: 刷新检索基线事实（种子扩展收尾）并挂竞品笔记与 Gate 3 实现计划指针"
```

### Step 7 全量门禁

```powershell
.\scripts\verify-local.ps1
```

本轮全部是 docs/查询清单改动，预期全绿；若红，先按 AGENTS.md 工具链三步（重装依赖、清 `.next`、`git stash` 复跑）排除环境，不要凭印象归因。

## 2. 验收清单

- [ ] `all.json` 83 条且无重复，batch5.json 已跟踪
- [ ] batch2-5 补记存在，含三条诚实边界，无编造的逐主题数字
- [ ] AGENTS.md / current-state.md 不再出现「batch5 未提交」「扩展进行中」表述
- [ ] 所有 v6 数字旁都有「工程侧标注」限定语
- [ ] `verify-local.ps1` 全绿
- [ ] 明确不做：不改检索器、不改测试预期、不把 v6 写成「检索有效」结论

## 3. 真人 reviewer 环节（外部，不阻塞本次提交）

并行 HITL 线保持原样：由未参与调参的真实 reviewer 接受 held-out 题集并产出标签后，才替换为「真人数字」。工程侧只保证标签 provenance 与数字出处可追溯。
