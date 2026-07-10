---
name: qiyan-adversarial-hardening
description: Audit and harden Qiyan Nexus changes from first principles. Use for access control, reviewer identity, owner isolation, RAG export integrity, network-task state transitions, SQLite concurrency, internal-preview PowerShell scripts, cloud trial runbooks, or security-sensitive pre-commit review.
---

# Qiyan Adversarial Hardening

Use this workflow to turn an adversarial finding into a small, verifiable, fail-closed change without expanding the project's frozen dependency boundary.

## Establish the security property

1. Read `AGENTS.md`, `docs/current-state.md`, the latest hardening handoff, and the affected tests.
2. State the protected asset, trusted principal, trust boundary, attacker-controlled input, and required failure behavior.
3. Trace the full lifecycle, not only the entry endpoint: create -> store -> query -> mutate -> export/download -> delete or terminal state.
4. Prefer an explicit invariant such as "a task is accessible only by `task_id + owner_id`" over a patch-specific description.

## Write the adversarial test first

Create a RED test for the smallest counterexample:

- foreign reviewer reads or advances another reviewer's object;
- legacy ownerless data becomes visible;
- GET/report polling changes state or writes runtime data;
- client-modified RAG payload exports successfully;
- two repositories using the same SQLite path race;
- token, reviewer, port, path, or curl config input changes command interpretation.

Confirm the test fails for the intended reason before implementing.

## Implement fail-closed boundaries

- Build reviewer identity only after access-token verification. Ignore untrusted reviewer headers in open mode.
- Carry ownership through schemas, repository protocols, every backend implementation, services, routers, SSR forwarding, and projections.
- Return 404 for foreign or ambiguous ownership to avoid existence disclosure. Quarantine or reject legacy ownerless records.
- Keep observation endpoints read-only. Separate status advancement from report/export retrieval.
- Sign server-issued export payloads over canonical fields; reject missing, incomplete, or modified data.
- Share network-task SQLite locks by canonical database path and rollback on failure. Treat literature/chunk locks as instance-local until code proves otherwise. Never claim cross-process safety from an in-process lock.
- Pass executable arguments structurally. Never place unvalidated operator input or secrets into `PowerShell -Command` or shell fragments. A curl config may be generated only from strict allowlisted input and passed through stdin or another controlled non-command channel.
- Keep real LLM, embedding, PostgreSQL, and heavy infrastructure opt-in unless an ADR explicitly changes the default.

## Verify the complete slice

Run focused tests during RED -> GREEN, then execute:

```powershell
.\scripts\verify-local.ps1
.\scripts\verify-local.ps1 -IncludeE2E
cd frontend
pnpm audit --prod
```

Also parse changed PowerShell files, run the protected smoke with two distinct reviewers, inspect process command lines for secrets, and run `git diff --check`. Require an independent reviewer to search specifically for fail-open behavior, cross-owner leakage, hidden mutation, and command injection.

## Close out safely

Update `docs/current-state.md` and one dated handoff with verified facts, deferred boundaries, and exactly one recommended next slice. Add only durable hard rules to `AGENTS.md` or `CLAUDE.md`.

Stage expected files explicitly. Inspect `git diff --cached --name-status` and `git diff --cached --check`. Exclude `.mcp.json`, `components.json`, runtime state, uploads, secrets, and unrelated user changes. Never push unless the user explicitly requests it.
