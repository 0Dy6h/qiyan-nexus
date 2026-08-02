# Source-bound Network Assembly Gate

date: 2026-08-02
status: implemented and independently verified (2026-08-02); PostgreSQL live parity and privileged audit HMAC are deferred
scope: first vertical slice only

## 1. Goal

Add a fail-closed gate that can seal the candidate inputs for a later controlled network-assembly computation from one completed, owner-scoped compound child task. The gate creates an immutable candidate assembly plan; it does not authorize a writer by itself and does not generate chains, PPI, pathways, enrichment, or scientific conclusions.

The gate separates three states:

- artifact consistency: frozen source artifacts and lineage are internally reproducible;
- assembly stage readiness: a specific frozen selection may enter a controlled writer later;
- scientific readiness: evidence supports research interpretation or publication.

This slice may establish only an `assembly_input_ready` state. It does not satisfy future per-edge adjudication, and `formal_network_ready` remains false.

## 2. Observation Unit

The formal assembly selection unit is one server-derived `intersection_targets` row, identified by its immutable `lineage_row_id` and backed by included disease and compound source-record lineage rows.

Source records remain separate observations. Rows sharing a canonical symbol are not collapsed before adjudication.

## 3. Authorization Preconditions

The gate fails closed unless all conditions hold:

1. The task exists for the authenticated owner and is `completed` with a frozen result.
2. It is a compound child with a non-self `source_task_id`.
3. The owner can still resolve the completed disease parent; the parent is a root task and the child points to exactly that parent.
4. Parent and child research protocols are canonically byte-equivalent across disease, phenotype, species, evidence policy, and query date, and remain within the accepted atopic-dermatitis contract.
5. Disease and compound imports both have `provenance_verification_status=server_verified_raw_artifact`.
6. Both source artifact SHA-256 values, canonical import payload hashes, versions, thresholds, query metadata, and mappings are present.
7. The compound child remains snapshot-only: `chains=[]`, `enrichment=null`, and no PPI, provider sources, or pipeline steps.
8. Every frozen disease, compound, and intersection lineage row has a latest-wins adjudication in the child task's own append-only stream and in a terminal state: `included` or `excluded`. Parent adjudications are not merged.
9. `pending`, missing, or `needs_review` adjudications block authorization.
10. At least one intersection row is `included`.
11. Each included intersection row references at least one included disease lineage row and at least one included compound lineage row. The plan preserves the complete frozen refs separately from the selected included subsets; it never rewrites the frozen intersection.
12. All selected row IDs exist in the frozen lineage and the intersection references are independently recomputable.

## 4. Immutable Plan Contract

Policy identifier: `source_bound_network_assembly_v1`.

Canonicalization identifier: `qiyan_canonical_json_v1`:

- validate every hash input through its Pydantic schema and dump with `mode="json"`;
- encode UTF-8 JSON with sorted keys and compact separators, with NaN/Infinity forbidden;
- use schema-normalized date/time strings and explicit null/default fields;
- sort row collections by `lineage_row_id`, adjudication snapshots by `lineage_row_id`, and selected refs lexicographically;
- hash only the field allowlists specified below, never database-native JSON rendering.

A candidate plan binds at least:

- `plan_id`;
- policy and canonicalization identifiers;
- child `task_id`, parent `task_id`, and their immutable link;
- parent and child research protocol canonical SHA-256 values;
- disease and compound raw-artifact SHA-256 values;
- disease and compound canonical import-payload SHA-256 values;
- frozen target-lineage canonical SHA-256;
- public latest-wins adjudication selection SHA-256 over each latest event's ID, row ID, decision, reason, and decided time; latest-wins follows append order and rows sort by row ID;
- an internal audit HMAC that additionally covers reviewer identity; it is never returned publicly and privileged verification is outside this first slice;
- sorted selected intersection rows with canonical symbol, complete frozen disease/compound refs, and selected included disease/compound backing refs;
- canonical plan-input SHA-256;
- creation timestamp and monotonic per-task `plan_sequence`.

`canonical_plan_input_sha256` excludes `plan_id`, `created_at`, and server-private audit fields. `plan_id` is deterministically derived from that hash. Because the latest immutable adjudication event ID is part of the input, every later adjudication event creates a new input even if its final decision returns to an earlier value. The same canonical input is idempotent and returns the original plan and timestamp. Old plans are append-only and owner-readable for audit, but are never implicitly executable.

Plans never contain or imply `formal_network_ready=true`.

Issuance is atomic with respect to the child adjudication stream. The repository compares the evaluated adjudication snapshot hash/revision inside the same critical section or database transaction used to insert the plan. A conflict is retried from fresh state or returns `409 gate_input_changed`; it must never return a stale `assembly_input_ready` plan as current.

A future writer must present the plan ID and input hash and, immediately before writing, atomically prove that the plan is still the latest plan for the current task/adjudication revision. That writer contract is a separate slice; plans created here are candidate inputs only.

## 5. API And Persistence

First slice API:

- `POST /api/network/result/{task_id}/assembly-plans` evaluates the gate and seals or returns the idempotent immutable candidate plan (`201` first creation, `200` idempotent hit).
- `GET /api/network/result/{task_id}/assembly-plans/{plan_id}` returns one owner-scoped historical plan.
- `GET /api/network/result/{task_id}` exposes an owner-scoped assembly-gate projection and the latest plan summary on the response envelope, not inside `NetworkAnalysisResult`.
- Reports render the gate status and latest plan binding while retaining the snapshot-only warning.

Authorization failures use existing owner semantics:

- unknown, foreign, or legacy ownerless task: `404`;
- incomplete/failed task, broken parent link, snapshot boundary violation, incomplete gate inputs, unfinished adjudication, or zero selectable intersections: structured `409` with deterministic blocker codes;
- malformed request/path input: `422` through ordinary request validation;
- internally inconsistent persisted hashes or lineage: fail closed with a high-severity integrity error, never present it as user-correctable readiness.

The public projection is fixed on the response envelope and contains only the policy ID, `blocked`/`assembly_input_ready` state, deterministically sorted structured blockers, and a latest-plan summary. It never exposes owner, reviewer identity, internal audit HMAC, or reasons from superseded events. UI/report wording is “装配输入已封存”, never “网络已就绪” or “科研就绪”.

Plans use append-only persistence with uniqueness on `(task_id, owner_id, canonical_plan_input_sha256)`. SQLite stores plans in a dedicated table and evaluates/inserts under one transaction. PostgreSQL uses row locking plus `INSERT ... ON CONFLICT`; its runtime parity requires a live-database test before claiming completion. JSON remains single-process preview only and must not be described as multi-worker safe. Reads never repair or advance task state.

First-slice capacity is bounded and fail-closed: at most 10,000 frozen lineage rows and 100,000 adjudication events per task; exceeding either bound blocks sealing without truncation.

## 6. Independent Verification

Extend the independent target-lineage validator to accept a public evidence package containing the plan, child result, parent/child protocols, and adjudication events with reviewer identity removed, and recompute:
- both protocol hashes, import-payload, artifact, lineage, public adjudication selection, and canonical plan-input hashes;
- complete terminal adjudication coverage;
- selected row existence and included decisions;
- intersection derivation and selected backing references;
- snapshot-only output boundary;
- deterministic plan ID.

The public validator does not verify reviewer identity or the server-private audit HMAC. It cannot prove external source officiality, mapping correctness, biological meaning, or scientific validity. Those remain explicit blockers.

Implementation note (2026-08-02): the public validator is `backend/scripts/validate_network_assembly_plan.py`, a producer-independent recomputation path. It re-derives both protocol hashes, the lineage hash, the latest-wins adjudication selection hash, the canonical plan input hash, the deterministic plan id, and the selected intersection/backing rows, and re-hashes raw artifact bytes when the store is present. Mutation tests in `backend/tests/test_validate_network_assembly_plan.py` prove it rejects every tampered binding and accepts a plan sealed through the live API. PostgreSQL repository behavior is implemented but runtime parity is not claimed without a live-database run; the privileged reviewer-identity audit HMAC remains outside this slice.

## 7. RED Acceptance Tests

Add failing tests before implementation for:

1. successful candidate-plan issuance from a completed same-owner compound child with complete terminal adjudication;
2. idempotent re-issuance for unchanged inputs;
3. new immutable plan after any later adjudication event, including include -> exclude -> include;
4. unknown, foreign, and legacy ownerless task `404`;
5. queued/running/failed or missing-result task rejection with structured `409` blockers;
6. root disease task and unlinked/self-linked/child-of-child task rejection;
7. missing or non-server-verified disease/compound provenance rejection;
8. any pending, missing, or `needs_review` row rejection;
9. zero included intersections rejection;
10. included intersection without an included disease or compound backing row rejection;
11. forged/unknown lineage references rejection;
12. post-plan response and report call the state `assembly_input_ready`, keep `formal_network_ready=false`, and keep snapshot-only outputs empty;
13. plan projection does not expose owner or reviewer identity;
14. JSON single-process and SQLite repository behavior, including same-input concurrency and adjudication-during-seal race regressions; PostgreSQL is not claimed complete without a live database run;
15. validator catches altered hashes, selected rows, decisions, refs, plan ID, and snapshot-only output mutation;
16. frontend displays blockers/plan binding without calling it network or scientific readiness;
17. first creation returns `201`, idempotent hit returns `200`, and historical plan GET remains owner-scoped;
18. capacity overflow blocks without truncating hash inputs.

## 8. Non-goals

- No chain, PPI, pathway, enrichment, or mechanism generation.
- No automatic promotion of adjudication into frozen lineage fields or future network-edge decisions.
- No `formal_network_ready` promotion.
- No live provider expansion, new scientific database, queue, or graph database.
- No claim that engineering provenance, completed source-row review, or a candidate plan proves biological validity or authorizes execution.

## 9. Verification

Required before closeout:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

Also run focused backend repository/API/validator tests and adversarial mutation checks for every signed field.
