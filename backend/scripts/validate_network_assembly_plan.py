"""Independently validate a sealed source-bound network assembly plan.

This script recomputes every binding of a candidate assembly plan from a
public evidence package and reports pass/fail. It deliberately shares no code
with ``app.services.network``: the producer's hashing and selection logic is
re-derived here from first principles so a coordinated producer bug or a
tampered artifact cannot pass both paths.

Evidence package (JSON):
    {
      "plan": { ... full NetworkAssemblyPlan JSON ... },
      "child_result": { ... frozen NetworkAnalysisResult JSON ... },
      "parent_protocol": { ... research protocol JSON ... },
      "child_protocol": { ... research protocol JSON ... },
      "adjudications": [
        {"adjudication_id": "...", "lineage_row_id": "...",
         "decision": "...", "reason": "...|null", "decided_at": "..."}
      ],
      "raw_artifact_dir": "optional path to the server raw-artifact store"
    }

The package intentionally excludes reviewer identity: this is the public
consistency path. Privileged audit of reviewer identity is a separate slice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_PLAN_ID_PATTERN = re.compile(r"^assembly-plan-[0-9a-f]{64}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ROW_ID_PATTERN = re.compile(r"^(disease|compound|intersection)-[0-9a-f]{64}$")
_TERMINAL_DECISIONS = {"included", "excluded"}


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _rows(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    return [_object(item, f"{name}[{index}]") for index, item in enumerate(value)]


def _row_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ROW_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a lineage row id")
    return value


def _latest_decisions(
    child_result: dict[str, Any],
    adjudications: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Return latest-wins decision per frozen row plus the row id list.

    Latest wins by append order (last event for a row wins), mirroring the
    producer's projection over the append-only audit stream.
    """
    lineage = _object(child_result.get("target_lineage"), "child_result.target_lineage")
    row_ids: list[str] = []
    for set_name in ("disease_targets", "compound_targets"):
        for row in _rows(lineage.get(set_name), f"child_result.target_lineage.{set_name}"):
            row_ids.append(_row_id(row.get("lineage_row_id"), f"{set_name} row lineage_row_id"))
    for row in _rows(
        lineage.get("intersection_targets"), "child_result.target_lineage.intersection_targets"
    ):
        row_ids.append(_row_id(row.get("lineage_row_id"), "intersection row lineage_row_id"))
    row_ids = sorted(set(row_ids))
    latest: dict[str, dict[str, Any]] = {}
    for entry in adjudications:
        event = _object(entry, "adjudications[]")
        row_id = _row_id(event.get("lineage_row_id"), "adjudication lineage_row_id")
        decision = event.get("decision")
        if decision not in _TERMINAL_DECISIONS and decision != "needs_review":
            raise ValueError(f"adjudication decision is invalid: {decision!r}")
        latest[row_id] = event
    return latest, row_ids


def _recompute_selected_intersections(
    child_result: dict[str, Any],
    latest: dict[str, dict[str, Any]],
    issues: list[str],
) -> list[dict[str, Any]]:
    lineage = _object(child_result.get("target_lineage"), "child_result.target_lineage")
    included_disease = {
        row_id
        for row in _rows(
            lineage.get("disease_targets"), "child_result.target_lineage.disease_targets"
        )
        if (row_id := _row_id(row.get("lineage_row_id"), "disease row id")) in latest
        and latest[row_id].get("decision") == "included"
    }
    included_compound = {
        row_id
        for row in _rows(
            lineage.get("compound_targets"), "child_result.target_lineage.compound_targets"
        )
        if (row_id := _row_id(row.get("lineage_row_id"), "compound row id")) in latest
        and latest[row_id].get("decision") == "included"
    }
    selected: list[dict[str, Any]] = []
    for row in _rows(
        lineage.get("intersection_targets"), "child_result.target_lineage.intersection_targets"
    ):
        decision = latest.get(_row_id(row.get("lineage_row_id"), "intersection row id"))
        if decision is None or decision.get("decision") != "included":
            continue
        frozen_disease = sorted(
            _row_id(item, "frozen disease ref") for item in row.get("disease_lineage_row_ids", [])
        )
        frozen_compound = sorted(
            _row_id(item, "frozen compound ref") for item in row.get("compound_lineage_row_ids", [])
        )
        selected_disease = sorted(set(frozen_disease) & included_disease)
        selected_compound = sorted(set(frozen_compound) & included_compound)
        if not selected_disease or not selected_compound:
            issues.append(
                f"included intersection {row.get('lineage_row_id')} lacks included backing rows"
            )
            continue
        selected.append(
            {
                "lineage_row_id": row.get("lineage_row_id"),
                "canonical_symbol": row.get("canonical_symbol"),
                "frozen_disease_lineage_row_ids": frozen_disease,
                "frozen_compound_lineage_row_ids": frozen_compound,
                "selected_disease_lineage_row_ids": selected_disease,
                "selected_compound_lineage_row_ids": selected_compound,
            }
        )
    return selected


def validate(evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a plan evidence package; returns (ok, issues)."""
    issues: list[str] = []
    plan = _object(evidence.get("plan"), "plan")
    child_result = _object(evidence.get("child_result"), "child_result")
    parent_protocol = _object(evidence.get("parent_protocol"), "parent_protocol")
    child_protocol = _object(evidence.get("child_protocol"), "child_protocol")
    adjudications = _rows(evidence.get("adjudications"), "adjudications")

    plan_id = plan.get("plan_id")
    input_hash = plan.get("canonical_plan_input_sha256")
    if not isinstance(plan_id, str) or not _PLAN_ID_PATTERN.fullmatch(plan_id):
        issues.append("plan.plan_id must match assembly-plan-<sha256>")
    if not isinstance(input_hash, str) or not _SHA256_PATTERN.fullmatch(input_hash):
        issues.append("plan.canonical_plan_input_sha256 must be a sha256 hex digest")

    if plan.get("policy_id") != "source_bound_network_assembly_v1":
        issues.append("plan.policy_id must be source_bound_network_assembly_v1")
    if plan.get("canonicalization_id") != "qiyan_canonical_json_v1":
        issues.append("plan.canonicalization_id must be qiyan_canonical_json_v1")
    if plan.get("assembly_input_ready") is not True:
        issues.append("plan.assembly_input_ready must be true")
    if plan.get("formal_network_ready") is not False:
        issues.append("plan.formal_network_ready must be false")

    # Snapshot-only boundary: the frozen child must not carry network outputs.
    if child_result.get("chains"):
        issues.append("child_result.chains must be empty (snapshot-only)")
    if child_result.get("enrichment") is not None:
        issues.append("child_result.enrichment must be null (snapshot-only)")
    for field in ("ppi_edges", "data_sources", "pipeline_steps"):
        if child_result.get(field):
            issues.append(f"child_result.{field} must be empty (snapshot-only)")

    # Protocol bindings.
    parent_protocol_hash = _canonical_sha256(parent_protocol)
    child_protocol_hash = _canonical_sha256(child_protocol)
    if plan.get("parent_protocol_sha256") != parent_protocol_hash:
        issues.append("plan.parent_protocol_sha256 does not match parent_protocol")
    if plan.get("child_protocol_sha256") != child_protocol_hash:
        issues.append("plan.child_protocol_sha256 does not match child_protocol")
    if parent_protocol_hash != child_protocol_hash:
        issues.append("parent and child research protocols are not byte-equivalent")
    for field in ("disease", "phenotype", "species", "evidence_policy", "query_date"):
        if parent_protocol.get(field) != child_protocol.get(field):
            issues.append(f"parent/child protocol field mismatch: {field}")

    # Source provenance bindings (frozen values, re-hashed when raw bytes exist).
    lineage = _object(child_result.get("target_lineage"), "child_result.target_lineage")
    disease_provenance = _object(
        lineage.get("disease_import_provenance"),
        "child_result.target_lineage.disease_import_provenance",
    )
    compound_provenance = _object(
        lineage.get("compound_import_provenance"),
        "child_result.target_lineage.compound_import_provenance",
    )
    for side, provenance, plan_field, payload_field in (
        (
            "disease",
            disease_provenance,
            "disease_source_artifact_sha256",
            "disease_import_payload_sha256",
        ),
        (
            "compound",
            compound_provenance,
            "compound_source_artifact_sha256",
            "compound_import_payload_sha256",
        ),
    ):
        if provenance.get("provenance_verification_status") != "server_verified_raw_artifact":
            issues.append(f"{side} provenance must be server_verified_raw_artifact")
        artifact_hash = provenance.get("source_artifact_sha256")
        payload_hash = provenance.get("import_payload_sha256")
        if plan.get(plan_field) != artifact_hash:
            issues.append(f"plan.{plan_field} does not match frozen {side} source artifact hash")
        if plan.get(payload_field) != payload_hash:
            issues.append(f"plan.{payload_field} does not match frozen {side} import payload hash")

    # Raw byte re-hash when the store is available.
    raw_dir = evidence.get("raw_artifact_dir")
    if raw_dir:
        for side, provenance in (
            ("disease", disease_provenance),
            ("compound", compound_provenance),
        ):
            artifact_hash = provenance.get("source_artifact_sha256")
            artifact_path = Path(raw_dir) / f"{artifact_hash}.json"
            if not artifact_path.is_file():
                issues.append(f"{side} raw artifact bytes missing at {artifact_path.name}")
                continue
            if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != artifact_hash:
                issues.append(f"{side} raw artifact bytes do not match their frozen sha256")

    # Frozen lineage and adjudication selection bindings.
    if plan.get("target_lineage_sha256") != _canonical_sha256(lineage):
        issues.append("plan.target_lineage_sha256 does not match child_result.target_lineage")

    latest, row_ids = _latest_decisions(child_result, adjudications)
    incomplete = sorted(
        row_id
        for row_id in row_ids
        if row_id not in latest or latest[row_id].get("decision") == "needs_review"
    )
    if incomplete:
        issues.append(f"adjudication is incomplete for rows: {incomplete}")
    adjudication_snapshot = [
        {
            "adjudication_id": latest[row_id].get("adjudication_id"),
            "lineage_row_id": row_id,
            "decision": latest[row_id].get("decision"),
            "reason": latest[row_id].get("reason"),
            "decided_at": latest[row_id].get("decided_at"),
        }
        for row_id in sorted(latest)
    ]
    if plan.get("adjudication_selection_sha256") != _canonical_sha256(adjudication_snapshot):
        issues.append("plan.adjudication_selection_sha256 does not match the latest-wins snapshot")

    # Selected intersections must equal the independent recomputation.
    recomputed_selected = _recompute_selected_intersections(child_result, latest, issues)
    plan_selected = plan.get("selected_intersections")
    if not isinstance(plan_selected, list):
        issues.append("plan.selected_intersections must be an array")
        plan_selected = []
    if not recomputed_selected:
        issues.append("no included intersection with included backing rows can be derived")
    if plan_selected != recomputed_selected:
        issues.append("plan.selected_intersections do not match the independent recomputation")
        if recomputed_selected:
            issues.append(
                "expected: " + json.dumps(recomputed_selected, ensure_ascii=False, sort_keys=True)
            )

    # Canonical plan input and idempotent plan id.
    if not isinstance(plan_selected, list) or not plan_selected:
        return False, issues
    recomputed_input = {
        "policy_id": "source_bound_network_assembly_v1",
        "canonicalization_id": "qiyan_canonical_json_v1",
        "task_id": plan.get("task_id"),
        "source_task_id": plan.get("source_task_id"),
        "parent_protocol_sha256": plan.get("parent_protocol_sha256"),
        "child_protocol_sha256": plan.get("child_protocol_sha256"),
        "disease_source_artifact_sha256": plan.get("disease_source_artifact_sha256"),
        "compound_source_artifact_sha256": plan.get("compound_source_artifact_sha256"),
        "disease_import_payload_sha256": plan.get("disease_import_payload_sha256"),
        "compound_import_payload_sha256": plan.get("compound_import_payload_sha256"),
        "target_lineage_sha256": plan.get("target_lineage_sha256"),
        "adjudication_selection_sha256": plan.get("adjudication_selection_sha256"),
        "selected_intersections": recomputed_selected,
    }
    recomputed_input_hash = _canonical_sha256(recomputed_input)
    if plan.get("canonical_plan_input_sha256") != recomputed_input_hash:
        issues.append("plan.canonical_plan_input_sha256 does not match the recomputed plan input")
    if plan.get("plan_id") != f"assembly-plan-{recomputed_input_hash}":
        issues.append("plan.plan_id does not derive from the canonical plan input")

    return not issues, issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_path", type=Path, help="path to the evidence package JSON")
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read evidence package: {exc}")
        return 2
    ok, issues = validate(evidence)
    for issue in issues:
        print(f"FAIL: {issue}", file=sys.stderr)
    print("VALID" if ok else "INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
