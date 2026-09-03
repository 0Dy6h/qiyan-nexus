"""ADR-0018 Gate 3 omics import service (slice G3-1).

Freezes a transcriptomics raw artifact as an immutable, content-addressed
snapshot — same discipline as the Open Targets / ChEMBL raw artifacts:

- the server computes the artifact SHA-256; clients can never submit it,
- the snapshot is sealed once per dataset accession and never rewritten,
- re-importing identical input is idempotent; conflicting input fails closed,
- nothing here touches ``formal_network_ready`` or derives evidence levels.

Slice G3-1 intentionally performs no parsing and no statistics.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.omics import (
    OmicsTranscriptomicsManifestV1,
    OmicsTranscriptomicsVerifiedSnapshot,
)


class OmicsSnapshotConflictError(Exception):
    """A different snapshot is already sealed for this dataset accession."""


@dataclass(frozen=True)
class OmicsImportOutcome:
    snapshot: OmicsTranscriptomicsVerifiedSnapshot
    idempotent: bool
    snapshot_path: Path
    artifact_path: Path


def _canonical_sha256(payload: Any) -> str:
    canonical_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def omics_artifact_dir() -> Path:
    configured_dir = os.environ.get("NETWORK_RAW_ARTIFACT_DIR")
    base_dir = (
        Path(configured_dir)
        if configured_dir
        else Path(__file__).resolve().parents[2] / "data" / "runtime" / "network_raw_artifacts"
    )
    return base_dir / "omics"


def build_verified_omics_import_snapshot(
    raw_bytes: bytes,
    *,
    manifest: OmicsTranscriptomicsManifestV1,
    frozen_by: str,
    annotation_bytes: bytes | None = None,
) -> OmicsTranscriptomicsVerifiedSnapshot:
    # Defense in depth: the schema Literals already pin these, but the seal must
    # not depend on the caller having validated through pydantic.
    if manifest.dataset.organism != "Homo sapiens":
        raise ValueError("omics dataset organism must be Homo sapiens")
    if manifest.dataset.disease != "atopic_dermatitis":
        raise ValueError("omics dataset disease must be atopic_dermatitis")
    if manifest.raw_artifact.size_bytes != len(raw_bytes):
        raise ValueError("declared raw artifact size_bytes does not match the uploaded payload")
    annotation_sha256: str | None = None
    if manifest.platform_annotation is not None:
        if annotation_bytes is None:
            raise ValueError(
                "manifest declares a platform annotation artifact but none was uploaded"
            )
        if manifest.platform_annotation.size_bytes != len(annotation_bytes):
            raise ValueError(
                "declared platform annotation size_bytes does not match the uploaded payload"
            )
        annotation_sha256 = hashlib.sha256(annotation_bytes).hexdigest()
    elif annotation_bytes is not None:
        raise ValueError("platform annotation bytes uploaded without a matching manifest field")
    artifact_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    frozen_at = datetime.now(UTC).isoformat()
    snapshot_input = {
        "client_manifest": manifest.model_dump(mode="json"),
        "raw_artifact_sha256": artifact_sha256,
        "platform_annotation_sha256": annotation_sha256,
    }
    snapshot_id = f"omics-snapshot-{_canonical_sha256(snapshot_input)}"
    sealed_annotation = (
        None
        if manifest.platform_annotation is None or annotation_bytes is None
        else {
            **manifest.platform_annotation.model_dump(mode="json"),
            "sha256": annotation_sha256,
            "frozen_at": frozen_at,
            "frozen_by": frozen_by,
        }
    )
    return OmicsTranscriptomicsVerifiedSnapshot.model_validate(
        {
            **manifest.model_dump(mode="json"),
            "snapshot_id": snapshot_id,
            "raw_artifact": {
                **manifest.raw_artifact.model_dump(mode="json"),
                "sha256": artifact_sha256,
                "frozen_at": frozen_at,
                "frozen_by": frozen_by,
            },
            "platform_annotation": sealed_annotation,
            "provenance": {
                "import_type": "server_verified_raw_artifact",
                "client_submitted": False,
                "formal_network_ready_impact": False,
                "evidence_level_upgrade": "none (pending analysis)",
            },
        }
    )


def _persist_raw_omics_artifact(raw_bytes: bytes, artifact_sha256: str) -> Path:
    """Content-addressed raw artifact store: tmp write, fsync, atomic replace, re-verify."""
    artifacts_dir = omics_artifact_dir() / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifacts_dir / f"{artifact_sha256}.bin"
    if (
        artifact_path.exists()
        and hashlib.sha256(artifact_path.read_bytes()).hexdigest() == artifact_sha256
    ):
        return artifact_path
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=artifacts_dir,
            prefix=f".{artifact_sha256}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(raw_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        if hashlib.sha256(temporary_path.read_bytes()).hexdigest() != artifact_sha256:
            raise ValueError("temporary omics raw artifact hash does not match expected bytes")
        os.replace(temporary_path, artifact_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return artifact_path


def _persist_omics_snapshot(snapshot: OmicsTranscriptomicsVerifiedSnapshot) -> Path:
    snapshot_dir = omics_artifact_dir()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{snapshot.dataset.accession}.json"
    payload = snapshot.model_dump(mode="json")
    encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=snapshot_dir,
            prefix=f".{snapshot.dataset.accession}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, snapshot_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    reread = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if reread != payload:
        raise ValueError("sealed omics snapshot does not round-trip; refusing to continue")
    return snapshot_path


def import_verified_omics_artifact(
    raw_bytes: bytes,
    *,
    manifest: OmicsTranscriptomicsManifestV1,
    frozen_by: str,
    annotation_bytes: bytes | None = None,
) -> OmicsImportOutcome:
    snapshot = build_verified_omics_import_snapshot(
        raw_bytes, manifest=manifest, frozen_by=frozen_by, annotation_bytes=annotation_bytes
    )
    snapshot_path = omics_artifact_dir() / f"{snapshot.dataset.accession}.json"
    if snapshot_path.exists():
        existing = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if existing.get("snapshot_id") == snapshot.snapshot_id:
            artifact_path = _restore_artifact_if_missing(raw_bytes, snapshot.raw_artifact.sha256)
            sealed_annotation = snapshot.platform_annotation
            if sealed_annotation is not None and annotation_bytes is not None:
                _restore_artifact_if_missing(annotation_bytes, sealed_annotation.sha256)
            return OmicsImportOutcome(
                snapshot=snapshot,
                idempotent=True,
                snapshot_path=snapshot_path,
                artifact_path=artifact_path,
            )
        raise OmicsSnapshotConflictError(
            f"dataset {snapshot.dataset.accession} is already sealed with a different "
            "snapshot; frozen omics snapshots are immutable"
        )
    artifact_path = _persist_raw_omics_artifact(raw_bytes, snapshot.raw_artifact.sha256)
    if snapshot.platform_annotation is not None and annotation_bytes is not None:
        _persist_raw_omics_artifact(annotation_bytes, snapshot.platform_annotation.sha256)
    _persist_omics_snapshot(snapshot)
    return OmicsImportOutcome(
        snapshot=snapshot,
        idempotent=False,
        snapshot_path=snapshot_path,
        artifact_path=artifact_path,
    )


def _restore_artifact_if_missing(raw_bytes: bytes, artifact_sha256: str) -> Path:
    """Re-write identical content-addressed bytes when the copy went missing.

    Never mutates a sealed snapshot document; the sealed hash governs identity.
    """
    artifact_path = omics_artifact_dir() / "artifacts" / f"{artifact_sha256}.bin"
    if not (
        artifact_path.exists()
        and hashlib.sha256(artifact_path.read_bytes()).hexdigest() == artifact_sha256
    ):
        return _persist_raw_omics_artifact(raw_bytes, artifact_sha256)
    return artifact_path


def load_frozen_omics_snapshot(accession: str) -> OmicsTranscriptomicsVerifiedSnapshot:
    """Load a sealed snapshot from the frozen store (fail closed on any mismatch)."""
    snapshot_path = omics_artifact_dir() / f"{accession}.json"
    if not snapshot_path.is_file():
        raise OmicsSnapshotConflictError(
            f"no frozen omics snapshot is sealed for dataset {accession}"
        )
    snapshot = OmicsTranscriptomicsVerifiedSnapshot.model_validate(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    if snapshot.dataset.accession != accession:
        raise ValueError("frozen omics snapshot accession does not match requested dataset")
    return snapshot


def load_frozen_omics_bytes(*, expected_sha256: str) -> bytes:
    """Read artifact bytes from the frozen content-addressed store by sealed sha256.

    This is the only sanctioned byte source for downstream analysis: client
    re-uploads are never accepted (G3-2 fail-closed rule).
    """
    artifact_path = omics_artifact_dir() / "artifacts" / f"{expected_sha256}.bin"
    if not artifact_path.is_file():
        raise ValueError(f"frozen artifact bytes missing for sha256 {expected_sha256}")
    raw_bytes = artifact_path.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != expected_sha256:
        raise ValueError(f"frozen artifact bytes fail SHA-256 verification for {expected_sha256}")
    return raw_bytes


# ── slice G3-2: series matrix parsing + deterministic DEG candidates ──

import gzip  # noqa: E402
import re  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats as scipy_stats  # noqa: E402

from app.schemas.network import (  # noqa: E402
    NetworkAnalysisResult,
    OmicsDegAnalysisProjection,
    OmicsDegCandidate,
)

_GROUP_ALIASES: dict[str, str] = {
    "al": "atopic_lesional",
    "atopic_lesional": "atopic_lesional",
    "lesional": "atopic_lesional",
    "anl": "atopic_nonlesional",
    "atopic_nonlesional": "atopic_nonlesional",
    "nonlesional": "atopic_nonlesional",
    "non-lesional": "atopic_nonlesional",
    "normal": "normal",
    "healthy": "normal",
    "control": "normal",
}
_SYMBOL_MAPPING_RULE = (
    "GPL annot 'Gene symbol' split on '///' (first entry); multi-probe symbols "
    "collapsed by max mean expression with lexicographic probe-id tie-break"
)
_COMPARISON_PATTERN = re.compile(r"^([a-z_]+)\s+vs\s+([a-z_]+)$")


class OmicsVerificationBlockedError(Exception):
    """Deterministic blocker list for a refused omics verification request."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


def _split_row(line: str) -> list[str]:
    return [cell.strip().strip('"') for cell in line.split("\t")]


def _canonical_group_label(label: str) -> str:
    return _GROUP_ALIASES.get(label.strip().lower(), label.strip().lower())


def _parse_sample_group_assignment(raw_text: str) -> list[str]:
    """Assign every sample column a canonical group key; fail closed on unknown labels."""
    groups: list[str] | None = None
    for line in raw_text.splitlines():
        if line.startswith("!Sample_characteristics_ch1\t"):
            cells = _split_row(line)[1:]
            if cells and all(cell.startswith("condition:") for cell in cells):
                groups = [_canonical_group_label(cell.split(":", 1)[1]) for cell in cells]
                break
        if line.startswith("!Sample_source_name_ch1\t") and groups is None:
            groups = [_canonical_group_label(cell) for cell in _split_row(line)[1:]]
    if groups is None:
        raise OmicsVerificationBlockedError(
            ["series matrix is missing condition characteristics and source_name rows"]
        )
    unknown = sorted({group for group in groups if group not in _GROUP_ALIASES.values()})
    if unknown:
        raise OmicsVerificationBlockedError(
            [f"series matrix contains unmapped condition labels: {unknown}"]
        )
    return groups


def _parse_series_matrix_values(raw_text: str) -> tuple[list[str], dict[str, list[float]]]:
    """Return (probe order, per-probe expression values keyed by probe id)."""
    probe_values: dict[str, list[float]] = {}
    probe_order: list[str] = []
    in_table = False
    for line in raw_text.splitlines():
        if line == "!series_matrix_table_begin":
            in_table = True
            continue
        if line == "!series_matrix_table_end":
            break
        if not in_table or not line.strip():
            continue
        cells = _split_row(line)
        if cells[0] == "ID_REF":
            continue
        try:
            values = [float(cell) for cell in cells[1:]]
        except ValueError as exc:
            raise OmicsVerificationBlockedError(
                [f"probe {cells[0]!r} has a non-numeric expression value"]
            ) from exc
        probe_values[cells[0]] = values
        probe_order.append(cells[0])
    if not probe_values:
        raise OmicsVerificationBlockedError(["series matrix contains no expression rows"])
    if len({len(values) for values in probe_values.values()}) != 1:
        raise OmicsVerificationBlockedError(["expression rows have inconsistent column counts"])
    return probe_order, probe_values


def _parse_platform_annotation_symbols(raw_bytes: bytes) -> dict[str, str]:
    """Return probe id → gene symbol (first '///' entry) from the frozen annotation."""
    text = gzip.decompress(raw_bytes).decode("utf-8")
    symbol_column: int | None = None
    mapping: dict[str, str] = {}
    in_table = False
    for line in text.splitlines():
        if line == "!platform_table_begin":
            in_table = True
            continue
        if line == "!platform_table_end":
            break
        if not in_table or not line.strip():
            continue
        cells = line.split("\t")
        if symbol_column is None:
            symbol_column = cells.index("Gene symbol") if "Gene symbol" in cells else -1
            continue
        if symbol_column < 0 or symbol_column >= len(cells):
            continue
        raw_symbol = cells[symbol_column].strip()
        if not raw_symbol:
            continue
        mapping[cells[0].strip()] = raw_symbol.split("///")[0].strip()
    if not mapping:
        raise OmicsVerificationBlockedError(
            ["platform annotation contains no probe-to-symbol rows"]
        )
    return mapping


def _benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """BH correction over the finite p-values only.

    Rows with a non-finite p (zero variance in both groups ⇒ undefined Welch
    test) are not testable hypotheses: they cannot enter the multiple-testing
    denominator, and they are returned as adj = 1.0 so they can never pass.
    """
    result = np.ones(p_values.size, dtype=np.float64)
    finite_mask = np.isfinite(p_values)
    tested = p_values[finite_mask]
    if tested.size == 0:
        return result
    order = np.argsort(tested, kind="stable")
    ranked = tested[order] * tested.size / np.arange(1, tested.size + 1, dtype=np.float64)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    corrected = np.empty(tested.size, dtype=np.float64)
    corrected[order] = np.clip(adjusted, 0.0, 1.0)
    result[finite_mask] = corrected
    return result


def compute_omics_deg_projection(
    result: NetworkAnalysisResult,
    *,
    accession: str,
) -> OmicsDegAnalysisProjection:
    """Deterministically derive lineage-matched DEG candidates for one task.

    Reads only frozen store bytes (never client re-uploads), recomputes Welch
    t-tests + BH from the frozen manifest thresholds, and matches passing genes
    against the task's frozen disease lineage. Emits candidates only — no
    evidence level, no readiness change, no lineage mutation.
    """
    if result.source_task_id is not None:
        raise OmicsVerificationBlockedError(
            ["compound child tasks are snapshot-only; omics verification never touches them"]
        )
    disease_rows = [row for row in result.target_lineage.disease_targets if row.lineage_row_id]
    if not disease_rows:
        raise OmicsVerificationBlockedError(["task has no frozen disease target lineage"])
    snapshot = load_frozen_omics_snapshot(accession)
    if snapshot.platform_annotation is None:
        raise OmicsVerificationBlockedError(
            ["frozen omics snapshot has no sealed platform annotation artifact"]
        )
    matrix_text = gzip.decompress(
        load_frozen_omics_bytes(expected_sha256=snapshot.raw_artifact.sha256)
    ).decode("utf-8")
    annotation_bytes = load_frozen_omics_bytes(expected_sha256=snapshot.platform_annotation.sha256)

    groups = _parse_sample_group_assignment(matrix_text)
    observed_counts: dict[str, int] = {}
    for group in groups:
        observed_counts[group] = observed_counts.get(group, 0) + 1
    declared_groups = dict(snapshot.dataset.sample_groups)
    if observed_counts != declared_groups:
        raise OmicsVerificationBlockedError(
            [
                "downloaded sample groups do not match manifest sample_groups: "
                f"observed {observed_counts}, manifest {declared_groups}"
            ]
        )

    comparison_match = _COMPARISON_PATTERN.match(snapshot.analysis_context.comparison.strip())
    if comparison_match is None:
        raise OmicsVerificationBlockedError(
            ["analysis_context.comparison is not of the form 'case_group vs control_group'"]
        )
    case_group, control_group = comparison_match.group(1), comparison_match.group(2)
    for group in (case_group, control_group):
        if group not in observed_counts:
            raise OmicsVerificationBlockedError(
                [f"comparison group {group!r} is not present in the sealed sample groups"]
            )

    probe_order, probe_values = _parse_series_matrix_values(matrix_text)
    matrix = np.array([probe_values[probe] for probe in probe_order], dtype=np.float64)
    if matrix.shape[1] != len(groups):
        raise OmicsVerificationBlockedError(
            [
                f"expression matrix has {matrix.shape[1]} columns but the series matrix "
                f"metadata declares {len(groups)} samples"
            ]
        )
    group_array = np.array(groups)
    case_mask = group_array == case_group
    control_mask = group_array == control_group

    probe_symbols = _parse_platform_annotation_symbols(annotation_bytes)
    probe_means = matrix.mean(axis=1)
    best: dict[str, tuple[float, str]] = {}
    for index, probe in enumerate(probe_order):
        symbol = probe_symbols.get(probe)
        if not symbol:
            continue
        candidate = (float(probe_means[index]), probe)
        current = best.get(symbol)
        if current is None or candidate > current:
            best[symbol] = candidate
    probe_index = {probe: idx for idx, probe in enumerate(probe_order)}
    symbols = sorted(best)
    gene_rows = np.array([probe_index[best[symbol][1]] for symbol in symbols], dtype=np.intp)
    gene_matrix = matrix[gene_rows]
    case_values = gene_matrix[:, case_mask]
    control_values = gene_matrix[:, control_mask]

    test = scipy_stats.ttest_ind(case_values, control_values, axis=1, equal_var=False)
    p_values = np.asarray(test.pvalue, dtype=np.float64)
    log2fc = case_values.mean(axis=1) - control_values.mean(axis=1)
    adj_p = _benjamini_hochberg(p_values)

    significance = snapshot.analysis_context.significance_threshold
    log2fc_threshold = snapshot.analysis_context.log2fc_abs_threshold
    passing_mask = (
        (adj_p < significance) & (np.abs(log2fc) > log2fc_threshold) & np.isfinite(p_values)
    )

    lineage_rows: dict[str, list[str]] = {}
    for row in disease_rows:
        lineage_rows.setdefault(row.canonical_symbol, []).append(str(row.lineage_row_id))

    candidates: list[OmicsDegCandidate] = []
    for position, symbol in enumerate(symbols):
        if not passing_mask[position] or symbol not in lineage_rows:
            continue
        candidates.append(
            OmicsDegCandidate(
                canonical_symbol=symbol,
                lineage_row_ids=sorted(lineage_rows[symbol]),
                mean_case=float(case_values[position].mean()),
                mean_control=float(control_values[position].mean()),
                log2fc=float(log2fc[position]),
                p_value=float(p_values[position]),
                adj_p_value=float(adj_p[position]),
            )
        )

    return OmicsDegAnalysisProjection(
        snapshot_id=snapshot.snapshot_id,
        accession=snapshot.dataset.accession,
        comparison=snapshot.analysis_context.comparison,
        case_group=case_group,
        control_group=control_group,
        significance_threshold=significance,
        log2fc_abs_threshold=log2fc_threshold,
        analyzed_probe_count=len(probe_order),
        analyzed_gene_count=len(symbols),
        passing_gene_count=int(passing_mask.sum()),
        sample_groups_used=observed_counts,
        symbol_mapping_rule=_SYMBOL_MAPPING_RULE,
        candidates=candidates,
    )
