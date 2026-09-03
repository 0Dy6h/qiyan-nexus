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
    OmicsProvenanceSealedFields,
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
) -> OmicsTranscriptomicsVerifiedSnapshot:
    # Defense in depth: the schema Literals already pin these, but the seal must
    # not depend on the caller having validated through pydantic.
    if manifest.dataset.organism != "Homo sapiens":
        raise ValueError("omics dataset organism must be Homo sapiens")
    if manifest.dataset.disease != "atopic_dermatitis":
        raise ValueError("omics dataset disease must be atopic_dermatitis")
    if manifest.raw_artifact.size_bytes != len(raw_bytes):
        raise ValueError("declared raw artifact size_bytes does not match the uploaded payload")
    artifact_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    snapshot_input = {
        "client_manifest": manifest.model_dump(mode="json"),
        "raw_artifact_sha256": artifact_sha256,
    }
    snapshot_id = f"omics-snapshot-{_canonical_sha256(snapshot_input)}"
    return OmicsTranscriptomicsVerifiedSnapshot.model_validate(
        {
            **manifest.model_dump(mode="json"),
            "snapshot_id": snapshot_id,
            "raw_artifact": {
                **manifest.raw_artifact.model_dump(mode="json"),
                "sha256": artifact_sha256,
                "frozen_at": datetime.now(UTC).isoformat(),
                "frozen_by": frozen_by,
            },
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
) -> OmicsImportOutcome:
    snapshot = build_verified_omics_import_snapshot(
        raw_bytes, manifest=manifest, frozen_by=frozen_by
    )
    snapshot_path = omics_artifact_dir() / f"{snapshot.dataset.accession}.json"
    if snapshot_path.exists():
        existing = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if existing.get("snapshot_id") == snapshot.snapshot_id:
            artifact_path = (
                omics_artifact_dir() / "artifacts" / f"{snapshot.raw_artifact.sha256}.bin"
            )
            if not (
                artifact_path.exists()
                and hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                == snapshot.raw_artifact.sha256
            ):
                # Same sealed snapshot but the content-addressed copy is missing
                # or corrupt: rewriting identical bytes mutates nothing sealed.
                artifact_path = _persist_raw_omics_artifact(raw_bytes, snapshot.raw_artifact.sha256)
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
    _persist_omics_snapshot(snapshot)
    return OmicsImportOutcome(
        snapshot=snapshot,
        idempotent=False,
        snapshot_path=snapshot_path,
        artifact_path=artifact_path,
    )
