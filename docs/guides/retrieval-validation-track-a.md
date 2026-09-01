# Track A：真实 PubMed 盲检索验证

## 目的与不可伪造的边界

本流程只回答一个问题：默认 `keyword` 检索在独立真实 PubMed 语料上，是否把真人 reviewer 判断为相关的文献排进产品实际展示的 top-5。

受保护的决策资产是“是否继续投入检索算法”的诚实证据；可信主体是未参与 ranker 调参的临床/科研 reviewer；信任边界是 reviewer worksheet 与私有 retrieval manifest 的分离。可能污染结论的输入包括 synthetic seed、看得见的 rank/score、看过结果后补写的问题、非布尔标签和未完成标签。任一污染出现时，脚本应拒绝构建或拒绝评分，而不是给出一个看似完整的数字。

本流程可以在完整真人 top-5 标签后报告 `precision@5` 与 `MRR@5`。它不能报告 recall、未截断 MRR、nDCG、临床有效率或“没有漏检”。

## 1. 在看结果前冻结问题集

当前候选问题集是 `backend/scripts/eval_queries.validation.v1.json`：30 题，无 expected literature ID，覆盖临床与科研问题。其状态明确为 `candidate_frozen_pending_domain_reviewer_acceptance`，因为这些问题由工程侧按真实工作流起草，尚不能冒充医生/科研专家原创。

真人 reviewer 应先只看问题文件并做以下二选一：

1. 接受 v1，不改题，随后开始标注。
2. 修改问题并另存 `eval_queries.validation.v2.json`，在任何人查看 v2 retrieval output 前重新生成 worksheet。

禁止看过候选结果后原地增删问题；这会重新引入循环评估。

## 2. 建立独立 real-only PubMed runtime

从仓库根目录执行：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe scripts\seed_pubmed_corpus.py `
  --runtime-root ..\.tmp\retrieval-validation-v1\corpus `
  --per-query 50 `
  --min-live-records 300
```

`--runtime-root` 会先显式创建空的 `literature_state.json` 与 `chunk_state.json`，从机制上阻止 repository 自动复制 20 条 synthetic seed。若目录已有状态，脚本默认拒绝复用；只有明确要继续同一快照时才传 `--resume`。

该命令调用 NCBI E-utilities，结果会随 PubMed 排序和时间变化。每次正式 packet 必须以 manifest 中的 corpus SHA-256、PMID/literature ID 清单、git commit 和生成时间为准，不能只写“约 344 条”。任一 PubMed query 失败、混入非 `pubmed_live` 记录或 live 数不足，validation 模式返回非零退出码。

PubMed seeder 当前只创建 literature records，不创建 chunks。因此 v1 是默认 keyword 产品路径的基线；不能把同一快照直接宣称为 vector/hybrid 的公平比较。

## 3. 生成真正盲标的双文件 packet

```powershell
$env:QIYAN_STATE_BACKEND = "json"
$env:LITERATURE_RUNTIME_STATE_PATH = "..\.tmp\retrieval-validation-v1\corpus\literature_state.json"
$env:CHUNK_RUNTIME_STATE_PATH = "..\.tmp\retrieval-validation-v1\corpus\chunk_state.json"

& .\.uv-test-venv\Scripts\python.exe scripts\eval_blind_labeling.py build `
  --queries scripts\eval_queries.validation.v1.json `
  --out ..\.tmp\retrieval-validation-v1\worksheet.json `
  --manifest-out ..\.tmp\retrieval-validation-v1\worksheet.manifest.json `
  --top-k 5 `
  --min-live-records 300 `
  --retrieval-provider keyword
```

构建器调用产品实际 `answer_question()` citation selection，而不是只截取 provider 原始排序，因此覆盖 off-topic guard、正分过滤、entity 过滤、network 特排和跨语言候选替换。

只把 `worksheet.json` 交给 reviewer。该文件中的候选顺序经过确定性打乱，不含 retrieval rank、retrieval score 或 `match_score`。`worksheet.manifest.json` 保存真实排名和 corpus/config 事实，在标注结束前必须对 reviewer 隐藏。两份文件均含真实摘要，只能放在 gitignored `.tmp/` 或 `backend/data/runtime/`，不得提交为 fixture。

## 4. 真人二元标注

Reviewer 对每个候选只填写：

- `relevant: true`：标题/摘要直接提供回答问题所需的临床或科研证据。
- `relevant: false`：只是宽泛主题相近，或只能回答疗效/安全性/机制中的另一维度。
- `reviewer_notes`：可选；摘要不足时说明原因，但 `relevant` 仍填 `false`。

标签必须是 JSON boolean，不能填字符串 `"true"` / `"false"`。不要编辑 `query_id`、`candidate_id`、问题或候选文本。

## 5. 评分

```powershell
& .\.uv-test-venv\Scripts\python.exe scripts\eval_blind_labeling.py score `
  --worksheet ..\.tmp\retrieval-validation-v1\worksheet.json `
  --manifest ..\.tmp\retrieval-validation-v1\worksheet.manifest.json `
  --out ..\.tmp\retrieval-validation-v1\metrics.json
```

存在任何未标问题时，命令返回退出码 3。非布尔标签、candidate/query 不匹配、manifest 不对应或 rank 非法时返回退出码 2。缺失结果按 top-k 的空槽计为不相关，因此不会通过“只对返回足 5 条的问题评分”美化指标。

在真人标签完成前，允许报告的只有 corpus/query/返回条数等运行事实；`precision@5` 和 `MRR@5` 必须保持 `null`。通过/不通过阈值应由产品负责人和 domain reviewer 在揭盲前书面冻结；若未预先冻结阈值，只报告数字与逐题结果，不做事后改口径。

## 当前首版 packet（2026-07-11）

首版 packet 复用了已有的 `.tmp/real-only/` 快照，避免为了文档刷新重新请求 NCBI 并改变 corpus：

- worksheet：`.tmp/retrieval-validation-v1/worksheet.json`
- private manifest：`.tmp/retrieval-validation-v1/worksheet.manifest.json`
- worksheet ID：`rag-blind-3a50687a3424ac3b`
- query-set SHA-256：`2b734b4999d620a65005f07499a208ad617c1b8346187252bda0c68797c22d0b`
- corpus：344/344 `pubmed_live`，0 `seed_sample`
- corpus SHA-256：`861cd184e0081dd12573e81db81a9c4134cc9fea4a07bbb7903a1fd83c34a34d`
- chunks：0；chunk SHA-256：`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`
- query：30；每题返回 5 条；共 150 个 `relevant: null`
- selection：`rag_answer_citations`；strategy：`keyword`
- 当前质量指标：`precision@5 = null`，`MRR@5 = null`，因为 0/30 题完成人工标签

这不是检索质量基线，只是一个可交付给真人 reviewer 的、没有循环标签和可见排名污染的基线 packet。
