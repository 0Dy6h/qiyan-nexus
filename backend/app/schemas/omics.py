"""ADR-0018 Gate 3 omics transcriptomics manifest schemas.

The client-submittable manifest (``OmicsTranscriptomicsManifestV1``) deliberately
excludes every server-sealed field: ``raw_artifact.sha256`` / ``frozen_at`` /
``frozen_by``, the whole ``provenance`` section, ``snapshot_id`` and
``formal_network_ready``. ``extra="forbid"`` makes any client attempt to submit
them fail closed. Sealed values are injected by the service layer when the
immutable snapshot is built (mirror of the network raw-artifact allowlist
discipline).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.network import DiseaseScope, ResearchSpecies

OmicsManifestVersion = Literal["omics_transcriptomics_v1"]
OmicsDataSource = Literal["geo"]
OmicsSampleGroupKey = Literal["atopic_lesional", "atopic_nonlesional", "normal"]
OmicsEdgeMappingStatus = Literal["pending_analysis"]
OmicsNetworkLayer = Literal["disease_target_verification"]
OmicsModality = Literal["transcriptomics"]
OmicsMeasurementType = Literal["gene_expression_microarray"]


class OmicsDatasetDescription(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: OmicsDataSource
    accession: str = Field(min_length=3, max_length=20, pattern=r"^GSE[0-9]+$")
    disease: DiseaseScope = "atopic_dermatitis"
    organism: ResearchSpecies = "Homo sapiens"
    title: str = Field(min_length=4, max_length=500)
    tissue: str = Field(min_length=1, max_length=300)
    platform: str = Field(min_length=1, max_length=200)
    sample_count: int = Field(ge=1)
    sample_groups: dict[OmicsSampleGroupKey, int] = Field(min_length=1)
    sample_count_note: str = Field(min_length=1, max_length=2000)
    citation: str = Field(min_length=1, max_length=1000)
    license: str = Field(min_length=1, max_length=300)
    public_since: str = Field(min_length=8, max_length=10, pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class OmicsRawArtifactClientFields(BaseModel):
    """Client-submittable half of ``raw_artifact``; hash and freeze metadata are sealed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=1)
    format: str = Field(min_length=1, max_length=100)


class OmicsAnalysisContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    modality: OmicsModality
    measurement_type: OmicsMeasurementType
    comparison: str = Field(min_length=3, max_length=200)
    normalization: str = Field(min_length=1, max_length=200)
    deg_method: str = Field(min_length=1, max_length=100)
    fdr_correction: str = Field(min_length=1, max_length=100)
    significance_threshold: float = Field(gt=0, le=1)
    log2fc_abs_threshold: float = Field(gt=0)


class OmicsEdgeMapping(BaseModel):
    """Frozen at import time: edges are derived downstream, never mutated here."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    network_layer: OmicsNetworkLayer
    verified_edges: list[str] = Field(max_length=0)
    corrected_edges: list[str] = Field(max_length=0)
    edge_mapping_status: OmicsEdgeMappingStatus
    mapping_rule: str = Field(min_length=1, max_length=500)


class OmicsTranscriptomicsManifestV1(BaseModel):
    """Operator-submitted manifest. Sealed fields are structurally inexpressible.

    ``platform_annotation`` freezes the probe→gene-symbol annotation table
    (e.g. GPL570 annot) alongside the expression matrix; without it the DEG
    pipeline cannot map canonical symbols, so G3-2 refuses to run when it is
    absent. It obeys the same sealing discipline as the primary artifact.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    manifest_version: OmicsManifestVersion = "omics_transcriptomics_v1"
    dataset: OmicsDatasetDescription
    raw_artifact: OmicsRawArtifactClientFields
    platform_annotation: OmicsRawArtifactClientFields | None = None
    analysis_context: OmicsAnalysisContext
    edge_mapping: OmicsEdgeMapping


class OmicsRawArtifactSealedFields(OmicsRawArtifactClientFields):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_at: str = Field(min_length=20, max_length=64)
    frozen_by: str = Field(min_length=1, max_length=200)


class OmicsProvenanceSealedFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    import_type: Literal["server_verified_raw_artifact"]
    client_submitted: Literal[False]
    formal_network_ready_impact: Literal[False]
    evidence_level_upgrade: Literal["none (pending analysis)"]


class OmicsTranscriptomicsVerifiedSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    manifest_version: OmicsManifestVersion = "omics_transcriptomics_v1"
    snapshot_id: str = Field(pattern=r"^omics-snapshot-[0-9a-f]{64}$")
    dataset: OmicsDatasetDescription
    raw_artifact: OmicsRawArtifactSealedFields
    platform_annotation: OmicsRawArtifactSealedFields | None = None
    analysis_context: OmicsAnalysisContext
    edge_mapping: OmicsEdgeMapping
    provenance: OmicsProvenanceSealedFields
    formal_network_ready: Literal[False] = False


class OmicsImportAccepted(BaseModel):
    snapshot_id: str
    accession: str
    idempotent: bool
    snapshot: OmicsTranscriptomicsVerifiedSnapshot
    formal_network_ready: Literal[False] = False
