"""ADR-0018 Gate 3 slice G3-1: omics manifest schema + raw artifact import gate.

The omics import freezes a transcriptomics raw artifact as an immutable,
content-addressed snapshot with server-computed SHA-256 — same discipline as
the Open Targets / ChEMBL raw artifacts. It performs no parsing and no
statistics, never touches ``formal_network_ready``, and rejects every
client-submitted sealed field.
"""

import gzip
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.omics import OmicsTranscriptomicsManifestV1
from app.services.network_omics import (
    OmicsSnapshotConflictError,
    build_verified_omics_import_snapshot,
    import_verified_omics_artifact,
)
from scripts.validate_omics_import import validate as validate_omics_store

OMICS_BYTES = gzip.compress(
    b'!Series_title\t"synthetic fixture"\n!Sample_geo_accession\t"GSMX1"\t"GSMX2"\n'
)
OMICS_SHA256 = hashlib.sha256(OMICS_BYTES).hexdigest()

MANIFEST: dict = {
    "manifest_version": "omics_transcriptomics_v1",
    "dataset": {
        "source": "geo",
        "accession": "GSE32924",
        "disease": "atopic_dermatitis",
        "organism": "Homo sapiens",
        "title": "Nonlesional atopic dermatitis skin (GSE32924 fixture)",
        "tissue": "skin biopsy (lesional, non-lesional, normal)",
        "platform": "GPL570 [HG-U133_Plus_2] Affymetrix Human Genome U133 Plus 2.0 Array",
        "sample_count": 3,
        "sample_groups": {"atopic_lesional": 1, "atopic_nonlesional": 1, "normal": 1},
        "sample_count_note": "synthetic fixture counts; real download governs the live dataset",
        "citation": "Suárez-Fariñas M et al. J Allergy Clin Immunol 2011;127(4):954-64",
        "license": "GEO/NCBI Open Access",
        "public_since": "2011-10-13",
    },
    "raw_artifact": {
        "filename": "GSE32924_series_matrix.txt.gz",
        "size_bytes": len(OMICS_BYTES),
        "format": "GEO series matrix (gzip text)",
    },
    "analysis_context": {
        "modality": "transcriptomics",
        "measurement_type": "gene_expression_microarray",
        "comparison": "atopic_lesional vs normal",
        "normalization": "geo_series_matrix_values",
        "deg_method": "welch_t_test",
        "fdr_correction": "benjamini_hochberg",
        "significance_threshold": 0.05,
        "log2fc_abs_threshold": 1.0,
    },
    "edge_mapping": {
        "network_layer": "disease_target_verification",
        "verified_edges": [],
        "corrected_edges": [],
        "edge_mapping_status": "pending_analysis",
        "mapping_rule": "DEG (adj_p < threshold, |log2FC| > threshold) matching canonical symbol",
    },
}


@pytest.fixture(autouse=True)
def _isolate_omics_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NETWORK_RAW_ARTIFACT_DIR", str(tmp_path / "network_raw_artifacts"))


def _manifest_bytes_field(payload: dict, **overrides: object) -> dict:
    merged = deepcopy(payload)
    merged["raw_artifact"].update(overrides)
    return merged


def _omics_store() -> Path:
    return Path(os.environ["NETWORK_RAW_ARTIFACT_DIR"]) / "omics"


# ── snapshot builder (service layer) ────────────────────────


def test_build_snapshot_seals_server_only_fields() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)

    snapshot = build_verified_omics_import_snapshot(
        OMICS_BYTES, manifest=manifest, frozen_by="operator-a"
    )

    assert snapshot.snapshot_id.startswith("omics-snapshot-")
    assert snapshot.raw_artifact.sha256 == OMICS_SHA256
    assert snapshot.raw_artifact.frozen_by == "operator-a"
    assert snapshot.raw_artifact.frozen_at
    assert snapshot.provenance.import_type == "server_verified_raw_artifact"
    assert snapshot.provenance.client_submitted is False
    assert snapshot.provenance.formal_network_ready_impact is False
    assert snapshot.provenance.evidence_level_upgrade == "none (pending analysis)"
    assert snapshot.formal_network_ready is False


def test_snapshot_id_is_deterministic_and_excludes_wall_clock() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)

    first = build_verified_omics_import_snapshot(
        OMICS_BYTES, manifest=manifest, frozen_by="operator-a"
    )
    second = build_verified_omics_import_snapshot(
        OMICS_BYTES, manifest=manifest, frozen_by="operator-b"
    )

    assert first.snapshot_id == second.snapshot_id
    expected_input = {
        "client_manifest": manifest.model_dump(mode="json"),
        "raw_artifact_sha256": OMICS_SHA256,
    }
    canonical = json.dumps(
        expected_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert (
        first.snapshot_id
        == "omics-snapshot-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )


@pytest.mark.parametrize(
    "sealed_payload",
    [
        {"provenance": {"import_type": "server_verified_raw_artifact"}},
        {"snapshot_id": "omics-snapshot-" + "0" * 64},
        {"formal_network_ready": True},
        {"raw_artifact": {"sha256": OMICS_SHA256}},
    ],
)
def test_client_manifest_rejects_sealed_fields(sealed_payload: dict) -> None:
    payload = deepcopy(MANIFEST)
    payload.update(sealed_payload)

    with pytest.raises(ValidationError):
        OmicsTranscriptomicsManifestV1.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    ["sha256", "frozen_at", "frozen_by"],
)
def test_client_manifest_rejects_sealed_raw_artifact_fields(field: str) -> None:
    payload = _manifest_bytes_field(MANIFEST, **{field: "x" * 64})

    with pytest.raises(ValidationError):
        OmicsTranscriptomicsManifestV1.model_validate(payload)


def test_declared_size_mismatch_fails_closed() -> None:
    payload = _manifest_bytes_field(MANIFEST, size_bytes=len(OMICS_BYTES) + 1)
    manifest = OmicsTranscriptomicsManifestV1.model_validate(payload)

    with pytest.raises(ValueError, match="size"):
        build_verified_omics_import_snapshot(OMICS_BYTES, manifest=manifest, frozen_by="op")


def test_organism_guard_is_enforced_outside_pydantic() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)
    tampered_dataset = manifest.dataset.model_construct(
        **{**manifest.dataset.model_dump(), "organism": "Mus musculus"}
    )
    tampered = manifest.model_copy(update={"dataset": tampered_dataset})

    with pytest.raises(ValueError, match="Homo sapiens"):
        build_verified_omics_import_snapshot(OMICS_BYTES, manifest=tampered, frozen_by="op")


# ── import + frozen store ───────────────────────────────────


def test_import_persists_content_addressed_artifact_and_snapshot() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)

    outcome = import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")

    assert outcome.idempotent is False
    artifact_path = _omics_store() / "artifacts" / f"{OMICS_SHA256}.bin"
    snapshot_path = _omics_store() / "GSE32924.json"
    assert artifact_path.read_bytes() == OMICS_BYTES
    stored = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert stored["snapshot_id"] == outcome.snapshot.snapshot_id
    assert stored["raw_artifact"]["sha256"] == OMICS_SHA256
    assert stored["provenance"]["client_submitted"] is False


def test_reimport_of_identical_input_is_idempotent() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)

    first = import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")
    second = import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")

    assert first.idempotent is False
    assert second.idempotent is True
    assert second.snapshot.snapshot_id == first.snapshot.snapshot_id
    artifacts = list((_omics_store() / "artifacts").iterdir())
    assert len(artifacts) == 1


def test_reimport_with_different_content_same_accession_conflicts() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)
    import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")
    snapshot_before = (_omics_store() / "GSE32924.json").read_bytes()

    alt_bytes = gzip.compress(b"different experiment payload\n")
    alt_manifest = OmicsTranscriptomicsManifestV1.model_validate(
        _manifest_bytes_field(MANIFEST, size_bytes=len(alt_bytes))
    )

    with pytest.raises(OmicsSnapshotConflictError):
        import_verified_omics_artifact(alt_bytes, manifest=alt_manifest, frozen_by="op")
    assert (_omics_store() / "GSE32924.json").read_bytes() == snapshot_before


def test_reimport_with_same_content_but_different_manifest_conflicts() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)
    import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")

    mutated = deepcopy(MANIFEST)
    mutated["analysis_context"]["significance_threshold"] = 0.01
    alt_manifest = OmicsTranscriptomicsManifestV1.model_validate(mutated)

    with pytest.raises(OmicsSnapshotConflictError):
        import_verified_omics_artifact(OMICS_BYTES, manifest=alt_manifest, frozen_by="op")


# ── HTTP endpoint ───────────────────────────────────────────


def _post_omics_import(payload_bytes: bytes, manifest_payload: dict, **extra_fields: str):
    client = TestClient(app)
    return client.post(
        "/api/network/omics-import/verify",
        data={"manifest": json.dumps(manifest_payload, ensure_ascii=False), **extra_fields},
        files={
            "file": (
                "GSE32924_series_matrix.txt.gz",
                payload_bytes,
                "application/gzip",
            )
        },
    )


def test_verify_endpoint_imports_snapshot_and_never_flips_readiness() -> None:
    response = _post_omics_import(OMICS_BYTES, MANIFEST)

    assert response.status_code == 201
    body = response.json()
    assert body["idempotent"] is False
    assert body["snapshot_id"] == body["snapshot"]["snapshot_id"]
    assert body["snapshot"]["provenance"]["formal_network_ready_impact"] is False
    assert body["formal_network_ready"] is False


def test_verify_endpoint_reimport_is_idempotent_with_200() -> None:
    first = _post_omics_import(OMICS_BYTES, MANIFEST)
    second = _post_omics_import(OMICS_BYTES, MANIFEST)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["idempotent"] is True
    assert second.json()["snapshot_id"] == first.json()["snapshot_id"]


def test_verify_endpoint_conflicts_on_different_content_same_accession() -> None:
    _post_omics_import(OMICS_BYTES, MANIFEST)
    alt_bytes = gzip.compress(b"another payload\n")

    response = _post_omics_import(
        alt_bytes, _manifest_bytes_field(MANIFEST, size_bytes=len(alt_bytes))
    )

    assert response.status_code == 409


def test_verify_endpoint_rejects_unexpected_multipart_fields() -> None:
    response = _post_omics_import(OMICS_BYTES, MANIFEST, records="[]")

    assert response.status_code == 422


def test_verify_endpoint_rejects_client_submitted_provenance() -> None:
    payload = deepcopy(MANIFEST)
    payload["provenance"] = {"import_type": "server_verified_raw_artifact"}

    response = _post_omics_import(OMICS_BYTES, payload)

    assert response.status_code == 422


def test_verify_endpoint_rejects_oversized_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api import network as network_api

    monkeypatch.setattr(network_api, "_MAX_OMICS_RAW_ARTIFACT_BYTES", 8)

    response = _post_omics_import(OMICS_BYTES, MANIFEST)

    assert response.status_code == 413


# ── independent validator ───────────────────────────────────


def test_validator_passes_a_clean_store() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)
    import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")

    ok, issues = validate_omics_store({"omics_dir": str(_omics_store()), "accession": "GSE32924"})

    assert ok, issues
    assert issues == []


def _import_once() -> None:
    manifest = OmicsTranscriptomicsManifestV1.model_validate(MANIFEST)
    import_verified_omics_artifact(OMICS_BYTES, manifest=manifest, frozen_by="op")


@pytest.mark.parametrize(
    ("tamper", "expected_fragment"),
    [
        ("flip_impact", "formal_network_ready_impact"),
        ("flip_sha", "sha256"),
        ("truncate_artifact", "artifact"),
        ("flip_threshold", "snapshot_id"),
        ("flip_client_submitted", "client_submitted"),
    ],
)
def test_validator_rejects_every_tamper_path(tamper: str, expected_fragment: str) -> None:
    _import_once()
    snapshot_path = _omics_store() / "GSE32924.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if tamper == "flip_impact":
        snapshot["provenance"]["formal_network_ready_impact"] = True
    elif tamper == "flip_sha":
        snapshot["raw_artifact"]["sha256"] = "0" * 64
    elif tamper == "truncate_artifact":
        artifact = _omics_store() / "artifacts" / f"{OMICS_SHA256}.bin"
        artifact.write_bytes(OMICS_BYTES[:-1])
    elif tamper == "flip_threshold":
        snapshot["analysis_context"]["significance_threshold"] = 0.2
    elif tamper == "flip_client_submitted":
        snapshot["provenance"]["client_submitted"] = True
    if tamper != "truncate_artifact":
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    ok, issues = validate_omics_store({"omics_dir": str(_omics_store()), "accession": "GSE32924"})

    assert ok is False
    assert any(expected_fragment in issue for issue in issues), issues
