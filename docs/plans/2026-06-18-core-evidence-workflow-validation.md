# Core Evidence Workflow Validation Implementation Plan

> **For Hermes:** Use this plan task-by-task as a validation gate. Do not add new product scope before the human evidence-workflow gate is complete.

**Goal:** Validate whether real clinician / research users are willing to use Qiyan Nexus to complete one AD TCM evidence-organization task, and whether they trust the citation traceability enough to continue trial use.

**Architecture:** Keep the current default offline preview path: deterministic provider + keyword retrieval + isolated runtime. The plan narrows existing reviewer materials into one 10-15 minute north-star workflow before the broader S1-S4 walkthrough, so user judgment focuses on product value rather than module inventory.

**Tech Stack:** No code changes required. Existing Next.js frontend, FastAPI backend, PowerShell preview scripts, reviewer task card, and trial feedback templates are reused.

---

## Product Hypothesis

If a clinician or researcher can select or upload an AD TCM literature item, ask one evidence question, inspect citation cards, trace the answer back to source material, and export a Markdown evidence note, then Qiyan Nexus has a credible core value as a traceable evidence workbench even before real LLM, real embedding, or real network-pharmacology computation is enabled by default.

## Non-goals

- Do not enable real LLM by default.
- Do not enable real embedding, PostgreSQL / pgvector, Neo4j, Celery, Redis, MinIO, or production auth.
- Do not expand MVP-B network pharmacology beyond its existing mock / opt-in boundaries.
- Do not add molecular docking or MD simulation UI.
- Do not treat AI technical review, internal rehearsal, smoke evidence, or automated tests as human sign-off.

## North-star Workflow

The first human validation task should take 10-15 minutes:

1. Open `/literature`.
2. Search `特应性皮炎` or another reviewer-chosen AD TCM keyword.
3. Open one result or upload the main local PDF sample from the task card.
4. Open `/rag`.
5. Ask one real evidence question, such as `健脾养血祛风法治疗特应性皮炎的证据主要支持哪些观察指标？`
6. Inspect the answer, disclaimer, citation cards, and literature-detail links.
7. Export the answer as Markdown.
8. Answer three validation questions:
   - Would you use this to organize AD TCM evidence again?
   - Are the cited sources traceable enough to trust the answer as a research/clinical reference aid?
   - Did any sample, mock, uploaded-PDF, or AI-output boundary feel misleading?

## Success Metrics

For the first 3-5 real users:

- At least 80% complete the north-star workflow without engineering intervention.
- 0 users mistake seed / mock data for externally verified real database results.
- 0 P0 issues and 0 unresolved P1 issues in medical safety, compliance, or core workflow completion.
- At least 2 users answer yes to "Would you use this to organize AD TCM evidence again?"
- At least 2 users rate citation traceability 4/5 or higher.
- Every exported RAG Markdown note includes the exact disclaimer string: `非诊断结论、需结合临床。`

## Failure Triggers

Pause broader trial expansion if any of these occur:

- A user treats the output as diagnostic or prescriptive clinical advice.
- A user cannot distinguish demo seed, uploaded PDF, PubMed live record, or network mock boundaries after reading the UI.
- RAG citations cannot be followed back to literature details during the session.
- The exported Markdown omits the disclaimer or loses citation context.
- A clinician or researcher flags a P0/P1 terminology, safety, or evidence-support problem.

## Execution Tasks

### Task 1: Prepare The Trial Runtime

**Objective:** Start from a clean, isolated runtime and preserve objective smoke evidence before human review.

**Files:**
- Read: `docs/checklists/reviewer-walkthrough-task-card.md`
- Read: `docs/evaluations/2026-06-05-reviewer-feedback.md`
- Read: `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`

**Steps:**

1. Run the local gate if code changed since the last trusted baseline:

   ```powershell
   .\scripts\verify-local.ps1 -IncludeE2E
   ```

2. Start isolated preview:

   ```powershell
   .\scripts\run-internal-preview.ps1 -RuntimeRoot .tmp\core-evidence-trial
   ```

3. Run smoke and save artifacts:

   ```powershell
   .\scripts\smoke-internal-preview.ps1 -OutputJson .tmp\core-evidence-trial\smoke.json -OutputMarkdown .tmp\core-evidence-trial\smoke.md
   ```

4. Record the runtime root, access profile, evidence package path, and verification result in `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`.

**Expected:** Smoke passes for literature, PDF upload/auto-parse, RAG answer/export, and network mock flows.

### Task 2: Run The North-star Workflow First

**Objective:** Validate the core evidence-workbench value before asking the reviewer to evaluate all modules.

**Files:**
- Fill: `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`
- Fill, for formal reviewer sign-off: `docs/evaluations/2026-06-05-reviewer-feedback.md`

**Steps:**

1. Give the reviewer the 10-15 minute "核心证据整理任务" from `docs/checklists/reviewer-walkthrough-task-card.md`.
2. Ask them to think aloud while completing the task.
3. Do not coach them through product meanings unless they are blocked.
4. Capture:
   - Whether they completed the workflow unaided.
   - Whether citation traceability was clear.
   - Whether they would use it again for AD TCM evidence organization.
   - Any misleading data-source or mock-boundary moment.
5. Record P0-P3 issues using the existing issue template.

**Expected:** The reviewer can complete literature/PDF -> RAG -> citation trace -> Markdown export and provide a clear judgment on value.

### Task 3: Run The Broader S1-S4 Walkthrough

**Objective:** After the core workflow, check the broader internal-preview boundaries without diluting the first value signal.

**Files:**
- Use: `docs/checklists/reviewer-walkthrough-task-card.md`
- Optional details: `docs/checklists/internal-preview-reviewer-walkthrough.md`

**Steps:**

1. Run S1 文献四来源检索.
2. Run S2 PDF 上传 → 解析 → RAG 引用.
3. Run S3 RAG 答案 + 免责声明.
4. Run S4 网络药理学 mock 边界, especially with research reviewers.
5. Keep objective automation evidence separate from human professional judgment.

**Expected:** Reviewer feedback distinguishes product value, safety/compliance risk, data-source clarity, and mock-boundary clarity.

### Task 4: Triage And Decide

**Objective:** Convert human feedback into a go / fix / pause decision.

**Files:**
- Update: `docs/evaluations/2026-06-05-reviewer-feedback.md`
- Update: `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`
- Create if needed: `docs/plans/YYYY-MM-DD-reviewer-feedback-fixes.md`

**Steps:**

1. Consolidate issues by P0-P3.
2. If any P0/P1 exists, stop expansion and write a fix plan.
3. If no P0/P1 exists and success metrics are met, proceed to broader internal trial.
4. If users complete the flow but do not perceive enough value, do not add more modules yet; revise the evidence-workflow UX and product copy first.

**Expected:** The project has an explicit human decision record before L2 governance, real network computation, or productionization work resumes.

## Recommended Next Commit

Commit only documentation and validation-scope changes:

```powershell
git add docs/plans/2026-06-18-core-evidence-workflow-validation.md docs/checklists/reviewer-walkthrough-task-card.md docs/evaluations/2026-06-06-small-scale-trial-feedback.md
git commit -m "docs: define core evidence workflow validation gate"
```
