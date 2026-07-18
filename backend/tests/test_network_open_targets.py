import hashlib
import json
from pathlib import Path

import pytest

from app.schemas.network import NetworkDiseaseTargetVerifyMetadata
from app.services.network_open_targets import OpenTargetsRawArtifactConnector

FIXTURE = Path(__file__).parent / "data" / "open_targets_graphql_associations_25_06.json"


def _expected(**updates: object) -> NetworkDiseaseTargetVerifyMetadata:
    payload: dict[str, object] = {
        "source_profile": "open_targets_association_v1",
        "disease": "atopic_dermatitis",
        "phenotype": "特应性皮炎伴 2 型炎症",
        "species": "Homo sapiens",
        "source_database": "Open Targets Platform",
        "database_version": "25.06",
        "source_query_id": "EFO_0000274",
        "source_query_label": "atopic eczema",
        "source_query_parameters": {"datatype": "overall"},
        "query_date": "2026-07-11",
        "retrieved_at": "2026-07-11T08:30:00Z",
        "score_name": "association_score",
        "applied_threshold": 0.6,
        "threshold_operator": "gte",
        "identifier_mapping": "Ensembl target approvedSymbol",
        "identifier_mapping_version": "25.06",
        "usage_license_note": "Open Targets Platform data; see platform terms.",
    }
    payload.update(updates)
    return NetworkDiseaseTargetVerifyMetadata.model_validate(payload)


def test_parser_derives_records_from_open_targets_graphql_response() -> None:
    records = OpenTargetsRawArtifactConnector.parse_open_targets_associations(
        FIXTURE.read_bytes(), expected=_expected()
    )

    assert [record.model_dump() for record in records] == [
        {
            "raw_identifier": "ENSG00000136244",
            "canonical_symbol": "IL6",
            "source_record_id": "EFO_0000274:ENSG00000136244:overall",
            "source_score": 0.91,
        },
        {
            "raw_identifier": "ENSG00000146648",
            "canonical_symbol": "EGFR",
            "source_record_id": "EFO_0000274:ENSG00000146648:overall",
            "source_score": 0.78,
        },
    ]


@pytest.mark.parametrize(
    ("raw_bytes", "expected", "message"),
    [
        (b"{tampered", _expected(), "valid JSON"),
        (
            FIXTURE.read_bytes(),
            _expected(applied_threshold=0.8),
            "applied threshold",
        ),
        (b"", _expected(), "empty"),
    ],
)
def test_parser_rejects_untrusted_or_inconsistent_artifacts(
    raw_bytes: bytes,
    expected: NetworkDiseaseTargetVerifyMetadata,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        OpenTargetsRawArtifactConnector.parse_open_targets_associations(
            raw_bytes, expected=expected
        )


def test_parser_rejects_duplicate_json_object_keys() -> None:
    duplicated = FIXTURE.read_text(encoding="utf-8").replace(
        '"score":0.91',
        '"score":0.1,"score":0.91',
        1,
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        OpenTargetsRawArtifactConnector.parse_open_targets_associations(
            duplicated.encode("utf-8"),
            expected=_expected(),
        )


def test_trusted_manifest_rejects_duplicate_json_object_keys(tmp_path: Path) -> None:
    artifact_hash = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    metadata_json = json.dumps(_expected().model_dump(mode="json"), ensure_ascii=False)
    manifest_path = tmp_path / "trusted-open-targets-manifest.json"
    manifest_path.write_text(
        f'{{"artifacts":{{"{artifact_hash}":{metadata_json},"{artifact_hash}":{metadata_json}}}}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        OpenTargetsRawArtifactConnector.validate_trusted_manifest(
            FIXTURE.read_bytes(),
            expected=_expected(),
            manifest_path=manifest_path,
        )
