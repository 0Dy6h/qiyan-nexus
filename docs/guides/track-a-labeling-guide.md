# Track A 标注向导

## 你在做什么

你在为「岐研枢」平台的默认检索系统做一次独立质量验证。

平台用关键词检索 PubMed 文献，对每个问题返回 top-5 篇文献。你需要做的是：**不看检索排名，仅根据文献标题和摘要判断它是否直接回答了问题**。

你的标签将用于计算 `precision@5`（top-5 中相关文献比例）和 `MRR@5`（第一篇相关文献的排名倒数）。这两个指标回答一个问题：默认检索是否把真人认为相关的文献排进了产品实际展示的 top-5。

这不是考试，没有标准答案——你的专业判断就是标准。

---

## 准备

### 你需要什么

1. **worksheet 文件**：`.tmp/retrieval-validation-v1/worksheet.json`
   - 包含 30 个问题，每个问题 5 篇候选文献（共 150 个候选）
   - 候选顺序已确定性打乱，**不含检索排名、分数或算法信息**
   - 每个候选有标题、摘要和 `relevant` 字段（当前为 `null`，需要你填写）

2. **文本编辑器**：VS Code、Notepad++ 或任何能编辑 JSON 的工具

### 你不能看什么

**`worksheet.manifest.json` 在标注完成前禁止查看。**

该文件包含：
- 检索排名和分数
- corpus 配置和算法参数
- 真实文献 ID 与排名的映射

提前查看 manifest 会污染你的判断（你会知道哪篇是"第一名"从而倾向标 true），使整个验证失去意义。

---

## 标注流程

### 第 1 步：打开 worksheet

用文本编辑器打开 `worksheet.json`。你会看到类似这样的结构：

```json
{
  "queries": [
    {
      "query_id": "ad-val-001",
      "question": "特应性皮炎患者使用保湿剂和神经酰胺类产品修复皮肤屏障的临床证据如何？",
      "language": "zh",
      "candidates": [
        {
          "candidate_id": "6b290a7240be2d61",
          "title": "Monoclonal Antibodies in Pediatric Atopic Dermatitis...",
          "abstract": "BACKGROUND: Atopic dermatitis (AD)...",
          "relevant": null,
          "reviewer_notes": ""
        },
        ...
      ]
    },
    ...
  ]
}
```

### 第 2 步：逐题逐候选标注

对每个问题（共 30 题），阅读问题文本，然后逐篇阅读候选文献的标题和摘要，判断：

- `relevant: true`：标题/摘要**直接提供**回答该问题所需的临床或科研证据。
- `relevant: false`：只是宽泛主题相近，或只能回答问题的另一个维度（如问疗效但只讲机制）。

### 第 3 步：填写标签

将 `relevant` 字段从 `null` 改为 `true` 或 `false`（JSON boolean，不是字符串）：

```json
"relevant": true
```

或

```json
"relevant": false
```

可选：在 `reviewer_notes` 中记录判断理由（特别是信息不足以判断时）：

```json
"relevant": false,
"reviewer_notes": "摘要只讨论了银屑病，未涉及特应性皮炎"
```

### 第 4 步：保存

保存 `worksheet.json`。不要修改 `query_id`、`candidate_id`、问题文本或候选文本。

### 第 5 步：完成后通知研究者

全部 150 个标签填完后，通知研究者运行评分脚本揭盲。

---

## 相关性判定标准

### 标 `true` 的条件

标题或摘要**直接提供**回答该问题所需的临床或科研证据。具体来说：

| 问题类型 | 标 `true` 的例子 |
|---|---|
| 疗效问题 | 文献直接报告了该干预对 AD 的疗效数据（RCT、Meta 分析、队列研究） |
| 安全性问题 | 文献直接报告了该干预的不良反应、肝肾安全性数据 |
| 机制问题 | 文献直接阐释了该靶点/通路在 AD 病理中的机制 |
| 中药复方问题 | 文献直接报告了该复方治疗 AD 的临床或实验研究 |
| 微生态问题 | 文献直接报告了肠道/皮肤菌群与 AD 的关联数据 |

### 标 `false` 的条件

以下情况标 `false`：

1. **宽泛主题相近但不直接回答问题**：文献讨论了 AD，但聚焦的是与问题不同的维度（如问保湿剂屏障修复，但文献讲的是单抗治疗）。
2. **只回答了另一维度**：问题问疗效，文献只讲机制；问题问安全性，文献只讲疗效。
3. **综述但未覆盖问题所需的具体证据**：综述提及了主题，但没有提供问题所需的直接证据。
4. **摘要信息不足以判断**：标题和摘要提供的信息不足以确定文献是否直接回答问题。在 `reviewer_notes` 中记录原因。
5. **物种或人群不匹配**：文献研究的是动物模型或非 AD 人群（如只研究哮喘不研究 AD），除非问题明确涉及跨疾病比较。

### 边界情况

- **系统综述/Meta 分析**：如果直接覆盖了问题所需的主题，标 `true`；如果只是宽泛提及，标 `false`。
- **基础研究**：如果问题问的是机制，且文献直接提供了该机制的证据，标 `true`；如果问题问的是临床疗效，且文献只有体外/动物实验数据，标 `false`。
- **中文文献**：与英文文献同样的标准判断。
- **同一主题不同干预**：如果问题问的是干预 A，文献讲的是干预 B（即使都在 AD 领域），标 `false`。

---

## JSON 格式要求

### 必须是 JSON boolean

```json
"relevant": true     ✓
"relevant": false    ✓
"relevant": "true"   ✗ (字符串，不是 boolean)
"relevant": "false"  ✗ (字符串，不是 boolean)
"relevant": 1        ✗ (数字，不是 boolean)
"relevant": null     ✗ (未标注，评分脚本会拒绝)
```

### 不要修改其他字段

不要修改以下字段：
- `query_id`
- `candidate_id`
- `title`
- `abstract`
- `snippet`
- `literature_id`
- `record_origin`
- `source`

### 可选字段

- `reviewer_notes`：可选，记录判断理由。特别是标 `false` 但摘要看起来相关时，简述为什么不直接回答问题。

---

## 预计耗时

| 项目 | 数量 | 预估时间 |
|---|---|---|
| 问题数 | 30 | — |
| 每题候选数 | 5 | — |
| 总候选数 | 150 | — |
| 每篇候选阅读时间 | ~10-15 秒 | — |
| 每题标注时间 | ~1-2 分钟 | — |
| **总耗时** | — | **约 30-45 分钟** |

建议一次性完成，避免中断后忘记判定标准。如果必须中断，标注前重读本向导的判定标准部分。

---

## 常见问题

### Q: 如果一篇文献的摘要太长或太短怎么办？

A: 阅读标题和摘要中能获取的全部信息。如果摘要不足以判断，标 `false` 并在 `reviewer_notes` 中写"摘要信息不足"。

### Q: 如果所有 5 篇候选都不相关怎么办？

A: 正常情况。全标 `false` 即可。这意味着检索系统对该问题没有返回相关文献。

### Q: 如果问题本身我无法理解怎么办？

A: 先尝试根据问题中的关键词判断。如果确实无法理解，在 `reviewer_notes` 中记录。不要跳过——每个候选都必须有 `true` 或 `false` 标签。

### Q: 如果候选文献是中文的怎么办？

A: 与英文文献同样的标准判断。平台支持中英文双语检索，中文文献是正常候选。

### Q: 我可以搜索文献全文吗？

A: 不建议。标注应基于 worksheet 中提供的标题和摘要。如果你认为摘要严重不足，标 `false` 并在 `reviewer_notes` 中说明。

### Q: 如果两篇候选看起来完全一样怎么办？

A: 可能是同一文献的不同版本。按各自内容独立标注。

---

## Manifest 保密纪律

### 什么是 manifest

`worksheet.manifest.json` 是与 worksheet 配对的私有文件，包含：

- 每篇候选的**真实检索排名**（第 1 名、第 2 名……）
- 每篇候选的**检索分数**
- corpus 配置（344 篇 PubMed live 文献的 ID 清单）
- 检索算法和参数
- corpus SHA-256 哈希

### 为什么不能看

Track A 的核心是**盲标**——你在不知道检索排名的情况下判断文献相关性。如果你提前看到排名：

- 你可能倾向于标"第 1 名"为 `true`（因为检索系统认为它最相关）
- 你的标签不再是独立的人类判断，而是对检索系统的确认
- precision@5 / MRR@5 会变成循环验证（用系统输出验证系统输出）

### 什么时候可以看

**在你完成全部 150 个标签之后**。研究者运行评分脚本揭盲后，manifest 中的排名和你的标签会一起展示，用于分析检索质量。

### 如果你已经看了

如果你不小心看了 manifest，请通知研究者。可能需要重新生成 worksheet（候选顺序会重新打乱）并重新标注。

---

## 评分

标注完成后，研究者运行：

```powershell
cd backend
$env:QIYAN_STATE_BACKEND = "json"
$env:LITERATURE_RUNTIME_STATE_PATH = "..\.tmp\real-only\literature_state.json"
$env:CHUNK_RUNTIME_STATE_PATH = "..\.tmp\real-only\chunk_state.json"

& .\.uv-test-venv\Scripts\python.exe scripts\eval_blind_labeling.py score `
  --worksheet ..\.tmp\retrieval-validation-v1\worksheet.json `
  --manifest ..\.tmp\retrieval-validation-v1\worksheet.manifest.json `
  --out ..\.tmp\retrieval-validation-v1\metrics.json
```

评分脚本会：
1. 验证所有 150 个标签都是 JSON boolean（否则退出码 2）
2. 验证 candidate/query 与 manifest 匹配（否则退出码 2）
3. 计算 `precision@5` 和 `MRR@5`（有未标问题时退出码 3）
4. 输出逐题结果到 `metrics.json`

通过/不通过阈值应在揭盲前由产品负责人和 domain reviewer 书面冻结。若未预先冻结阈值，只报告数字与逐题结果，不做事后改口径。

---

## 当前 packet 信息

| 属性 | 值 |
|---|---|
| worksheet ID | 见 `worksheet.json` 中的 `worksheet_id` |
| 问题数 | 30 |
| 每题候选数 | 5 |
| 总候选数 | 150 |
| corpus | 344 篇 PubMed live 文献 |
| corpus SHA-256 | 见 `worksheet.manifest.json` |
| 检索策略 | keyword（deterministic） |
| 问题集状态 | `candidate_frozen_pending_domain_reviewer_acceptance` |
| 当前标签状态 | 0/150（全部 `null`，未标注） |

---

## 问题集说明

30 个问题覆盖以下维度：

- **临床治疗**：保湿剂、外用激素、钙调神经磷酸酶抑制剂、JAK 抑制剂、生物制剂
- **中医药**：中药复方、外用中药、针灸、消风散、黄芪
- **机制研究**：Th2 炎症、JAK-STAT 通路、皮肤屏障、微生态、肠-皮轴
- **研究方法**：网络药理学预测验证、偏倚风险、方剂异质性

问题由工程侧按真实工作流起草，状态为 `candidate_frozen_pending_domain_reviewer_acceptance`。标注者可在标注前先只看问题文件决定是否接受 v1 问题集；如需修改，应另存 v2 并在查看 v2 retrieval output 前重新生成 worksheet。

---

*本向导由 TraeWork 编制，2026-08-16。不得填任何标签（150 个标签必须真人填写）、不改问题集与候选文本、不修改 ranking、不外发数据。*
