import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.network import (
    NetworkCompoundTargetRecord,
    NetworkCompoundTargetVerifyMetadata,
)


class ChEMBLRawArtifactConnector:
    @staticmethod
    def parse_known_activities(
        raw_bytes: bytes,
        *,
        expected: NetworkCompoundTargetVerifyMetadata,
    ) -> list[NetworkCompoundTargetRecord]:
        if not raw_bytes.strip():
            raise ValueError("ChEMBL raw artifact is empty")
        try:
            payload = _load_json_without_duplicate_keys(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("ChEMBL raw artifact must be valid JSON") from exc

        root = _strict_object(payload, "root", {"activities"}, {"activities"})
        activities = root["activities"]
        if not isinstance(activities, list):
            raise ValueError("ChEMBL activities must be an array")
        if len(activities) > 500:
            raise ValueError("ChEMBL artifact exceeds the 500-record limit")

        records: list[NetworkCompoundTargetRecord] = []
        seen_observations: set[tuple[str, str, str]] = set()
        seen_activity_ids: set[str] = set()
        for index, value in enumerate(activities):
            row = _strict_object(
                value,
                f"activities[{index}]",
                {
                    "activity_id",
                    "molecule_chembl_id",
                    "target_chembl_id",
                    "target_gene_symbol",
                    "target_organism",
                    "pchembl_value",
                },
                {
                    "activity_id",
                    "molecule_chembl_id",
                    "target_chembl_id",
                    "target_gene_symbol",
                    "target_organism",
                    "pchembl_value",
                },
            )
            molecule_chembl_id = row["molecule_chembl_id"]
            target_organism = row["target_organism"]
            if molecule_chembl_id != expected.compound_id:
                raise ValueError("ChEMBL artifact compound does not match declaration")
            if target_organism != expected.species:
                raise ValueError("ChEMBL artifact species does not match declaration")
            score = row["pchembl_value"]
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise ValueError(f"ChEMBL row {index} pchembl_value must be numeric")
            if float(score) < expected.applied_threshold:
                raise ValueError("ChEMBL record does not satisfy the applied threshold")
            activity_id = row["activity_id"]
            target_chembl_id = row["target_chembl_id"]
            target_gene_symbol = row["target_gene_symbol"]
            if not all(
                isinstance(value, str) and value
                for value in (activity_id, target_chembl_id, target_gene_symbol)
            ):
                raise ValueError(f"ChEMBL row {index} identifiers must be non-empty strings")
            if activity_id in seen_activity_ids:
                raise ValueError("ChEMBL activity_id values must be unique")
            seen_activity_ids.add(activity_id)
            observation_key = (activity_id, target_chembl_id, target_gene_symbol)
            if observation_key in seen_observations:
                raise ValueError("ChEMBL activity observations must be unique")
            seen_observations.add(observation_key)
            try:
                records.append(
                    NetworkCompoundTargetRecord(
                        raw_identifier=target_chembl_id,
                        canonical_symbol=target_gene_symbol,
                        source_record_id=activity_id,
                        source_score=float(score),
                    )
                )
            except ValidationError as exc:
                raise ValueError(f"ChEMBL row {index} is invalid") from exc
        return records

    @staticmethod
    def validate_trusted_manifest(
        raw_bytes: bytes,
        *,
        expected: NetworkCompoundTargetVerifyMetadata,
        manifest_path: Path,
    ) -> None:
        try:
            manifest = _load_json_without_duplicate_keys(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("trusted ChEMBL artifact manifest is unavailable or invalid") from exc
        root = _strict_object(manifest, "manifest", {"artifacts"}, {"artifacts"})
        artifacts = root["artifacts"]
        if not isinstance(artifacts, dict):
            raise ValueError("trusted ChEMBL manifest artifacts must be an object")
        artifact_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        manifest_metadata = artifacts.get(artifact_sha256)
        if manifest_metadata is None:
            raise ValueError("raw artifact hash is not registered in the trusted manifest")
        try:
            trusted = NetworkCompoundTargetVerifyMetadata.model_validate(manifest_metadata)
        except ValidationError as exc:
            raise ValueError("trusted ChEMBL artifact manifest metadata is invalid") from exc
        if trusted.model_dump(mode="json") != expected.model_dump(mode="json"):
            raise ValueError("declared metadata does not match the trusted artifact manifest")


def _load_json_without_duplicate_keys(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is not allowed: {key}")
        result[key] = value
    return result


def _strict_object(
    value: Any,
    name: str,
    allowed_keys: set[str],
    required_keys: set[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"ChEMBL {name} must be an object")
    unknown = set(value) - allowed_keys
    missing = required_keys - set(value)
    if unknown:
        raise ValueError(f"ChEMBL {name} contains unsupported fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"ChEMBL {name} is missing fields: {sorted(missing)}")
    return value
