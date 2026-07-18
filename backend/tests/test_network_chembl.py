import hashlib
import json
from pathlib import Path

import pytest

from app.schemas.network import NetworkCompoundTargetVerifyMetadata
from app.services.network_chembl import ChEMBLRawArtifactConnector

FIXTURE = Path(__file__).parent / "data" / "chembl_known_activities_34.json"


def _expected(**updates: object) -> NetworkCompoundTargetVerifyMetadata:
    payload: dict[str, object] = {
        "source_profile": "chembl_known_activity_v1",
        "compound_id": "CHEMBL1201587",
        "compound_label": "Quercetin",
        "species": "Homo sapiens",
        "source_database": "ChEMBL",
        "database_version": "34",
        "source_query_id": "CHEMBL1201587",
        "source_query_label": "Quercetin",
        "source_query_parameters": {
            "assay_organism": "Homo sapiens",
            "standard_type": "IC50",
            "pchembl_value_min": 6.0,
        },
        "query_date": "2026-07-12",
        "retrieved_at": "2026-07-12T08:30:00Z",
        "score_name": "pchembl_value",
        "applied_threshold": 6.0,
        "threshold_operator": "gte",
        "identifier_mapping": "ChEMBL target component gene symbol",
        "identifier_mapping_version": "34",
        "usage_license_note": "ChEMBL data; see database terms.",
    }
    payload.update(updates)
    return NetworkCompoundTargetVerifyMetadata.model_validate(payload)


def test_parser_derives_compound_target_records_from_chembl_artifact() -> None:
    records = ChEMBLRawArtifactConnector.parse_known_activities(
        FIXTURE.read_bytes(), expected=_expected()
    )

    assert [record.model_dump() for record in records] == [
        {
            "raw_identifier": "CHEMBL1792",
            "canonical_symbol": "IL6",
            "source_record_id": "CHEMBL_ACTIVITY_1001",
            "source_score": 6.4,
        },
        {
            "raw_identifier": "CHEMBL203",
            "canonical_symbol": "EGFR",
            "source_record_id": "CHEMBL_ACTIVITY_1002",
            "source_score": 6.1,
        },
    ]


def test_parser_allows_a_valid_zero_hit_activity_artifact() -> None:
    records = ChEMBLRawArtifactConnector.parse_known_activities(
        b'{"activities": []}',
        expected=_expected(),
    )

    assert records == []


def test_parser_rejects_reused_activity_id_even_when_symbol_matches() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["activities"].append(
        {
            "activity_id": "CHEMBL_ACTIVITY_1001",
            "molecule_chembl_id": "CHEMBL1201587",
            "target_chembl_id": "CHEMBL9999",
            "target_gene_symbol": "IL6",
            "target_organism": "Homo sapiens",
            "pchembl_value": 6.5,
        }
    )

    with pytest.raises(ValueError, match="activity_id"):
        ChEMBLRawArtifactConnector.parse_known_activities(
            json.dumps(payload).encode("utf-8"),
            expected=_expected(),
        )


@pytest.mark.parametrize(
    ("raw_bytes", "expected", "message"),
    [
        (b"{tampered", _expected(), "valid JSON"),
        (
            FIXTURE.read_bytes(),
            _expected(compound_id="CHEMBL999999", source_query_id="CHEMBL999999"),
            "compound",
        ),
        (
            FIXTURE.read_bytes(),
            _expected(
                applied_threshold=6.5,
                source_query_parameters={
                    "assay_organism": "Homo sapiens",
                    "standard_type": "IC50",
                    "pchembl_value_min": 6.5,
                },
            ),
            "threshold",
        ),
        (b"", _expected(), "empty"),
    ],
)
def test_parser_rejects_inconsistent_compound_artifacts(
    raw_bytes: bytes,
    expected: NetworkCompoundTargetVerifyMetadata,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ChEMBLRawArtifactConnector.parse_known_activities(raw_bytes, expected=expected)


def test_trusted_manifest_rejects_an_unregistered_raw_artifact(tmp_path: Path) -> None:
    manifest_path = tmp_path / "trusted-chembl-manifest.json"
    manifest_path.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="not registered"):
        ChEMBLRawArtifactConnector.validate_trusted_manifest(
            FIXTURE.read_bytes(),
            expected=_expected(),
            manifest_path=manifest_path,
        )


def test_parser_rejects_duplicate_json_object_keys() -> None:
    duplicated = FIXTURE.read_text(encoding="utf-8").replace(
        '"pchembl_value": 6.4',
        '"pchembl_value": 1.0, "pchembl_value": 6.4',
        1,
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        ChEMBLRawArtifactConnector.parse_known_activities(
            duplicated.encode("utf-8"),
            expected=_expected(),
        )


def test_trusted_manifest_rejects_duplicate_json_object_keys(tmp_path: Path) -> None:
    artifact_hash = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    metadata_json = json.dumps(_expected().model_dump(mode="json"), ensure_ascii=False)
    manifest_path = tmp_path / "trusted-chembl-manifest.json"
    manifest_path.write_text(
        f'{{"artifacts":{{"{artifact_hash}":{metadata_json},"{artifact_hash}":{metadata_json}}}}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        ChEMBLRawArtifactConnector.validate_trusted_manifest(
            FIXTURE.read_bytes(),
            expected=_expected(),
            manifest_path=manifest_path,
        )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"source_query_id": "CHEMBL999999"}, "source_query_id"),
        (
            {
                "source_query_parameters": {
                    "assay_organism": "Homo sapiens",
                    "pchembl_value_min": 5.5,
                }
            },
            "pchembl_value_min",
        ),
        (
            {
                "source_query_parameters": {
                    "assay_organism": "Homo sapiens",
                    "pchembl_value_min": 6.0,
                    "client_hash": "not-query-semantics",
                }
            },
            "Extra inputs",
        ),
        (
            {
                "applied_threshold": True,
                "source_query_parameters": {
                    "assay_organism": "Homo sapiens",
                    "pchembl_value_min": True,
                },
            },
            "not boolean",
        ),
    ],
)
def test_metadata_rejects_inconsistent_or_unsupported_query_contract(
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _expected(**updates)
