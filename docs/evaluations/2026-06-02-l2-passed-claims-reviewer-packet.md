# L2 Passed Claims Reviewer Packet

date: 2026-06-02
status: Codex technical evidence-support review completed and formally confirmed; default provider unchanged

## Purpose

This packet prepares the 2026-06-02 passed real-provider claims for formal reviewer sign-off.
It is delta-only: it does not repeat the 2026-06-01 §4c reviewer walkthrough that already verified gate, fallback, rollback, and UI metadata behavior.

## Codex Technical Evidence-Support Review

- Reviewer: Codex technical review
- Reviewer role: engineering evidence-support check, not clinician/research sign-off
- Review date: 2026-06-02
- Reviewed capture: `captured_real_claims_live_20260602_0846.json`
- Profile: `opencode_go + keyword + BGE=0.3 + NLI=0.5`
- Claims reviewed: 6
- Supported: 6
- Unsupported: 0
- Unclear: 0
- Overall verdict: All six passed claims are directly supported by their cited chunks in this technical review. This supports continued controlled L1 demo/evaluation use of the profile, but does not approve L2/default preview.
- Default-provider decision: keep `deterministic`; do not flip L2.
- Formal sign-off status: confirmed by user on 2026-06-02; no changes to the six Codex technical verdicts.

## Formal Reviewer Confirmation

- Confirmation date: 2026-06-02
- Confirmation source: user confirmation in the current session
- Confirmed verdicts: 6 supported / 0 unsupported / 0 unclear
- Reviewer action: confirmed the six Codex technical evidence-support verdicts without revision.
- Scope: claim-vs-cited-chunk support for the four passed answers only.
- Boundary: this confirms the passed-claim evidence support; it does not approve L2/default preview and does not replace the separate profile-governance decision.

## Capture Summary

- Source capture: `captured_real_claims_live_20260602_0846.json`
- Capture source: `live_opencode_go`
- Captured at: `2026-06-02T00:46:00+00:00`
- Provider: `opencode_go`
- Embedding backend: `bge`
- Semantic threshold: `0.3`
- Max tokens: `4000`
- Questions captured: `10`
- Total claims: `14`

## Selected Questions

| Question ID | Claims | Min semantic | Min entailment | Latency ms | Cost |
|---|---:|---:|---:|---:|---:|
| rag-eval-005 | 2 | 0.3394 | 0.9985 | 12647 | null |
| rag-eval-007 | 1 | 0.5893 | 0.9990 | 5252 | null |
| rag-eval-008 | 2 | 0.5783 | 0.9985 | 28540 | null |
| rag-eval-010 | 1 | 0.9553 | 0.7446 | 14797 | null |

## Reviewer Instructions

- This is a delta-only packet. The 2026-06-01 §4c reviewer walkthrough already verified gate, fallback, rollback, and UI metadata behavior.
- Review only whether each passed claim is directly supported by its cited chunk.
- Use one verdict per claim: `supported`, `unsupported`, or `unclear`.
- Do not treat this packet as a default-provider flip. The default RAG path remains offline `deterministic` unless ADR-0012 is changed separately.

## rag-eval-005

- Question: 英文文献中如何解释特应性皮炎的皮肤屏障损伤？
- Provider: `opencode_go`
- Retrieval strategy: `keyword`
- Grounding status: `passed`
- Semantic threshold: `0.3`
- NLI threshold: `0.5`
- Input tokens: `586`
- Output tokens: `1513`
- Provider latency ms: `12647`
- Estimated cost: `null`

Answer shown after grounding:

> 丝聚蛋白功能缺失变异导致经皮水分丢失增加和表皮屏障减弱 [chunk-pmid-40100006-filaggrin]。特应性皮炎中皮肤屏障破坏、警报素和2型炎症相互作用 [chunk-pmid-40100001-review]。

### Claim 1

Claim:

> 丝聚蛋白功能缺失变异导致经皮水分丢失增加和表皮屏障减弱。

- Evidence refs: `chunk-pmid-40100006-filaggrin`
- Semantic score: `0.3394`
- Entailment score: `0.9985`
- Reviewer verdict: `[x] supported` / `[ ] unsupported` / `[ ] unclear`
- Reviewer notes: cited chunk explicitly states that filaggrin loss-of-function variants drive transepidermal water loss and weaken the epidermal barrier in atopic dermatitis; the claim is a direct Chinese summary without added efficacy, guideline, or causal scope beyond the evidence.

Cited evidence:

- Chunk: `chunk-pmid-40100006-filaggrin`
- Literature: `pmid-40100006`
- Section: `review`

> Filaggrin loss-of-function variants drive transepidermal water loss and weaken the epidermal barrier in atopic dermatitis, enabling allergen penetration and downstream type 2 inflammation.

### Claim 2

Claim:

> 特应性皮炎中皮肤屏障破坏、警报素和2型炎症相互作用。

- Evidence refs: `chunk-pmid-40100001-review`
- Semantic score: `0.3865`
- Entailment score: `0.9990`
- Reviewer verdict: `[x] supported` / `[ ] unsupported` / `[ ] unclear`
- Reviewer notes: cited chunk explicitly describes interaction among barrier disruption, alarmins, and type 2 inflammation in atopic dermatitis; the claim preserves that relationship and does not add unsupported treatment conclusions.

Cited evidence:

- Chunk: `chunk-pmid-40100001-review`
- Literature: `pmid-40100001`
- Section: `review`

> This review summarizes how barrier disruption, alarmins, and type 2 inflammation interact in atopic dermatitis and discusses implications for targeted therapy.

## rag-eval-007

- Question: JAK-STAT 通路为什么会在特应性皮炎研究中被频繁提到？
- Provider: `opencode_go`
- Retrieval strategy: `keyword`
- Grounding status: `passed`
- Semantic threshold: `0.3`
- NLI threshold: `0.5`
- Input tokens: `578`
- Output tokens: `434`
- Provider latency ms: `5252`
- Estimated cost: `null`

Answer shown after grounding:

> JAK-STAT 细胞因子信号已成为特应性皮炎的主要治疗轴 [chunk-pmid-40100005-jak-stat]。

### Claim 1

Claim:

> JAK-STAT 细胞因子信号已成为特应性皮炎的主要治疗轴

- Evidence refs: `chunk-pmid-40100005-jak-stat`
- Semantic score: `0.5893`
- Entailment score: `0.9990`
- Reviewer verdict: `[x] supported` / `[ ] unsupported` / `[ ] unclear`
- Reviewer notes: cited chunk directly says JAK-STAT cytokine signaling has emerged as a major therapeutic axis in atopic dermatitis; the claim is aligned with that wording.

Cited evidence:

- Chunk: `chunk-pmid-40100005-jak-stat`
- Literature: `pmid-40100005`
- Section: `review`

> This review explains why JAK-STAT cytokine signaling has emerged as a major therapeutic axis in atopic dermatitis. Downstream STAT phosphorylation amplifies pathogenic transcription programs in epidermal and immune cells, motivating targeted therapy strategies.

## rag-eval-008

- Question: 网络药理学在特应性皮炎中药研究里通常怎么用？
- Provider: `opencode_go`
- Retrieval strategy: `keyword`
- Grounding status: `passed`
- Semantic threshold: `0.3`
- NLI threshold: `0.5`
- Input tokens: `606`
- Output tokens: `3439`
- Provider latency ms: `28540`
- Estimated cost: `null`

Answer shown after grounding:

> 网络药理学在特应性皮炎中药研究中优先筛选活性化合物、预测靶点和富集通路 [chunk-pmid-40100008-network]。特应性皮炎相关研究中PI3K-Akt、NF-kB、JAK-STAT等被频繁列为关键调控轴 [chunk-cn-ad-network-007-pathway]。

### Claim 1

Claim:

> 网络药理学在特应性皮炎中药研究中优先筛选活性化合物、预测靶点和富集通路。

- Evidence refs: `chunk-pmid-40100008-network`
- Semantic score: `0.5783`
- Entailment score: `0.9990`
- Reviewer verdict: `[x] supported` / `[ ] unsupported` / `[ ] unclear`
- Reviewer notes: cited chunk states that network pharmacology workflows prioritize active compounds, predicted targets, and enriched pathways for atopic dermatitis herbal formulas. The claim is supported, while the evidence caveat that these are hypothesis-generating leads still requires the platform's usual non-diagnostic boundary.

Cited evidence:

- Chunk: `chunk-pmid-40100008-network`
- Literature: `pmid-40100008`
- Section: `review`

> Network pharmacology workflows for atopic dermatitis herbal formulas prioritise active compounds, predicted targets, and enriched pathways such as PI3K-Akt and NF-kB, framing these as hypothesis-generating leads that still require experimental validation.

### Claim 2

Claim:

> 特应性皮炎相关研究中PI3K-Akt、NF-kB、JAK-STAT等被频繁列为关键调控轴。

- Evidence refs: `chunk-cn-ad-network-007-pathway`
- Semantic score: `0.9623`
- Entailment score: `0.9985`
- Reviewer verdict: `[x] supported` / `[ ] unsupported` / `[ ] unclear`
- Reviewer notes: cited chunk directly says PI3K-Akt, NF-kB, and JAK-STAT are frequently listed as key regulatory axes in atopic dermatitis network-pharmacology studies; the claim matches the cited evidence.

Cited evidence:

- Chunk: `chunk-cn-ad-network-007-pathway`
- Literature: `cn-ad-network-007`
- Section: `summary`

> 综述指出网络药理学方法常用于筛选中药复方的活性成分、靶点和信号通路，PI3K-Akt、NF-kB、JAK-STAT 等被频繁列为特应性皮炎相关研究的关键调控轴。

## rag-eval-010

- Question: 中西医结合专家共识对特应性皮炎长期管理强调了什么？
- Provider: `opencode_go`
- Retrieval strategy: `keyword`
- Grounding status: `passed`
- Semantic threshold: `0.3`
- NLI threshold: `0.5`
- Input tokens: `593`
- Output tokens: `1649`
- Provider latency ms: `14797`
- Estimated cost: `null`

Answer shown after grounding:

> 共识将皮肤屏障维护、规律外用润肤剂、辨证施治和长期管理列为特应性皮炎的核心要点 [chunk-cn-ad-guideline-004-management]。

### Claim 1

Claim:

> 共识将皮肤屏障维护、规律外用润肤剂、辨证施治和长期管理列为特应性皮炎的核心要点

- Evidence refs: `chunk-cn-ad-guideline-004-management`
- Semantic score: `0.9553`
- Entailment score: `0.7446`
- Reviewer verdict: `[x] supported` / `[ ] unsupported` / `[ ] unclear`
- Reviewer notes: cited chunk explicitly lists skin barrier maintenance, regular emollient use, syndrome-based treatment, and long-term management as core points in the consensus; the claim is supported. The cited reminder that conclusions require clinical judgment remains covered by the platform disclaimer and should not be treated as L2 approval.

Cited evidence:

- Chunk: `chunk-cn-ad-guideline-004-management`
- Literature: `cn-ad-guideline-004`
- Section: `consensus`

> 中西医结合诊疗专家共识把皮肤屏障维护、规律外用润肤剂、辨证施治和长期管理列为特应性皮炎的核心要点，并提醒所有结论须结合医生临床判断。
