---
name: qiyan-adversarial-hardening
description: Audit and harden Qiyan Nexus changes from first principles. Use for access control, reviewer identity, owner isolation, RAG export integrity, network-task state transitions, target lineage, raw-artifact provenance and scientific-readiness integrity, SQLite concurrency, internal-preview PowerShell scripts, cloud trial runbooks, or security- and research-sensitive pre-commit review.
---

# Qiyan Adversarial Hardening

Use this workflow to turn an adversarial finding into a small, verifiable, fail-closed change without expanding the project's frozen dependency boundary.

## Establish the security property

1. Read `AGENTS.md`, `docs/current-state.md`, the latest hardening handoff, and the affected tests.
2. State the protected asset, trusted principal, trust boundary, attacker-controlled input, and required failure behavior.
3. Trace the full lifecycle, not only the entry endpoint: create -> store -> query -> mutate -> export/download -> delete or terminal state.
4. Prefer an explicit invariant such as "a task is accessible only by `task_id + owner_id`" over a patch-specific description.

## Preserve scientific set integrity

- Model disease targets, compound targets, and their intersection as separate sets. Never infer the disease set from the compound set or accept a client-declared intersection without recomputation.
- Treat an empty set as a valid fail-closed result. If independent disease-target evidence is absent, keep disease and intersection empty and expose the blocker.
- Use source record as the lineage observation unit. Preserve multiple rows when distinct records map to the same canonical symbol; report unique-target counts separately from lineage-row counts.
- Separate automatic extraction from human adjudication. Default extracted rows to pending/unreviewed with no invented reviewer, timestamp, decision, or rationale.
- Freeze source database, version, query date, species, score, threshold, identifier mapping, and source record IDs before claiming reproducibility. Missing values must lower readiness rather than disappear from the UI or report.
- Keep artifact consistency separate from scientific readiness. Internal agreement proves neither source validity nor biological or clinical truth.
- When a verified artifact establishes only a frozen upstream snapshot, return a snapshot-only projection: do not invoke downstream providers or populate graph, pathway, PPI, enrichment, or other derived-analysis fields. Keep readiness false with an explicit remaining-gate blocker, and have the independent validator, report, and UI enforce the same boundary.
- Keep a human-decision audit stream parallel to the frozen snapshot, never inside it. Project it on the response envelope, resolve repeat decisions as latest-wins over an append-only history, persist reviewer identity without ever projecting it back, and keep it structurally unable to flip readiness. Recording a decision is not the same as a decision having been made, and neither is scientific validity.
- Build important validators independently of the producer path. Recompute counts, intersections, protocol consistency, canonical payload hashes, and raw-byte hashes without importing the service that generated the artifact. State explicitly when a validator does not independently replay the producer's parser.
- When a gate authorizes a later computation, seal a candidate plan rather than an executable authorization. Bind every input (protocols, source hashes, lineage, latest-wins adjudication snapshot, selected rows) into a canonical input hash that derives the plan id, keep old plans append-only and readable but not implicitly executable, and require the future writer to atomically prove the plan is still the latest for the current revision before writing. Never let "a plan exists" mean "a writer may run".
- Make gate issuance atomic against the state it evaluated. Evaluating adjudications and then persisting a plan in separate steps lets a concurrent decision create a stale authorization. Compare the evaluated revision (for example the full ordered adjudication event ids) inside the same lock/transaction as the insert — SQLite `BEGIN IMMEDIATE` plus event-id compare, PostgreSQL `FOR UPDATE`, JSON in-process lock only — and return a conflict instead of persisting.

## Write the adversarial test first

Create a RED test for the smallest counterexample:

- foreign reviewer reads or advances another reviewer's object;
- legacy ownerless data becomes visible;
- GET/report polling changes state or writes runtime data;
- client-modified RAG payload exports successfully;
- disease targets are absent but a non-empty intersection is declared;
- two source records mapping to one canonical target are silently collapsed;
- automatic extraction is presented as accepted human adjudication;
- a client-controlled artifact and a sibling client declaration are accepted as independent proof of source or release;
- a forbidden derived field is rejected inside metadata but accepted as a sibling top-level multipart field;
- oversized, chunked, ambiguously framed, truncated, or hash-mismatched raw uploads reach parsing or persistence;
- provenance text changes Markdown structure or injects active output;
- two repositories using the same SQLite path race;
- token, reviewer, port, path, or curl config input changes command interpretation.

Confirm the test fails for the intended reason before implementing.

A concurrency test must be able to observe the race it claims to cover. Two repository instances in one process share the module-level path lock, so they cannot demonstrate a cross-process lost update — such a test passes with the guard removed and proves nothing. Force the interleaving explicitly, for example by committing an out-of-band write on a separate connection between the read and the guarded write, then delete the guard and confirm the test actually fails.

## Implement fail-closed boundaries

- Build reviewer identity only after access-token verification. Ignore untrusted reviewer headers in open mode.
- Carry ownership through schemas, repository protocols, every backend implementation, services, routers, SSR forwarding, and projections.
- For a derived task, resolve its parent through the same owner-scoped lookup, persist an immutable non-self-referential parent ID through every storage and projection path, and reject recursive derivation. A legacy derived record without that link must fail closed on result, report, and export reads without being repaired or advanced by the read.
- Return 404 for foreign or ambiguous ownership to avoid existence disclosure. Quarantine or reject legacy ownerless records.
- Keep observation endpoints read-only. Separate status advancement from report/export retrieval.
- Sign server-issued export payloads over canonical fields; reject missing, incomplete, or modified data.
- Treat the uploaded bytes and all declarations from the same client as one trust domain. For a provenance upgrade, compute the raw hash server-side and bind it to server-controlled acquisition metadata; never let a client-supplied hash, record set, or release envelope attest to its sibling input.
- Apply strict allowlists at every envelope layer. A strict nested metadata model does not constrain sibling multipart fields, headers, filenames, media types, or request framing.
- Reject unsupported transfer framing and enforce byte/row/resource caps before multipart parsing, spooling, domain parsing, or repository writes.
- Persist content-addressed artifacts through a same-directory temporary file, complete write plus flush/fsync, server-side rehash, and atomic replace. A hash-shaped filename alone does not make a partial write safe.
- Escape or structurally encode provenance fields at every HTML/Markdown/export boundary; provenance is attacker-controlled output even after its bytes are integrity-checked.
- Share network-task SQLite locks by canonical database path and rollback on failure. Treat literature/chunk locks as instance-local until code proves otherwise. Never claim cross-process safety from an in-process lock. Any new read-modify-write on a shared row needs the same compare-and-set plus retry the neighbouring methods already use — an existing guard in the same file is the requirement statement, and a new method that skips it is a defect.
- Keep a write and the read that refreshes the UI afterwards in separate error paths. Sharing one `catch` reports a durable write as failed, which in an append-only audit domain invites a retry that pollutes the history with an event that should never have existed.
- Assert the location of a cross-boundary field on both sides. A projection the backend returns on the response envelope but the client reads off the nested snapshot yields zeros with no error anywhere — silent data loss that no type checker or happy-path test catches.
- Pass executable arguments structurally. Never place unvalidated operator input or secrets into `PowerShell -Command` or shell fragments. A curl config may be generated only from strict allowlisted input and passed through stdin or another controlled non-command channel.
- Keep real LLM, embedding, PostgreSQL, and heavy infrastructure opt-in unless an ADR explicitly changes the default.

## Verify the complete slice

When a gate is red, rule out the toolchain before editing code. pnpm writes absolute symlinks, so moving the repository leaves every frontend dependency dangling and every frontend gate failing for reasons unrelated to the diff; `rm -rf frontend/node_modules && pnpm install --frozen-lockfile` restores it. `.next` carries the same pre-migration absolute paths: after a directory move, dev servers and Playwright can fail intermittently (for example `waitForLoadState("networkidle")` timeouts) until `rm -rf frontend/.next`. Attribute a pre-existing failure by stashing the working changes and re-running **on a clean toolchain** (dependencies reinstalled, caches cleared): a failure reproduced without the cache fix is not proof the code is innocent. Avoid `waitForLoadState("networkidle")` in E2E against Next dev servers entirely — rely on `goto`'s load wait plus `expect(...).toBeVisible()` auto-waiting.

Inheriting an unverified work-in-progress means running the gate first, not adding features. Unverified code carries defects that only a green baseline can expose.

Run focused tests during RED -> GREEN, then execute:

```powershell
.\scripts\verify-local.ps1
.\scripts\verify-local.ps1 -IncludeE2E
cd frontend
pnpm audit --prod
```

If the audit command fails before returning an advisory result, for example because registry endpoints return HTTP 410, record it as a tooling compatibility blocker. Never translate that failure or a stale prior run into "0 vulnerabilities".

Also parse changed PowerShell files, run the protected smoke with two distinct reviewers, inspect process command lines for secrets, and run `git diff --check`. Require an independent reviewer to search specifically for fail-open behavior, cross-owner leakage, hidden mutation, and command injection.

## Close out safely

Update `docs/current-state.md` and one dated handoff with verified facts, deferred boundaries, and exactly one recommended next slice. Add only durable hard rules to `AGENTS.md` or `CLAUDE.md`.

If the user authorized a commit workflow, stage expected files explicitly and inspect `git diff --cached --name-status` plus `git diff --cached --check`. Otherwise leave the index untouched. Always exclude `.mcp.json`, `components.json`, runtime state, uploads, secrets, and unrelated user changes. Never commit or push unless the user explicitly requests it.
