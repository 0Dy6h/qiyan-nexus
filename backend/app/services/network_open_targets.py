import hashlib
import json
from pathlib import Path
from typing import Any

from app.schemas.network import (
    NetworkDiseaseTargetRecord,
    NetworkDiseaseTargetVerifyMetadata,
)


class OpenTargetsRawArtifactConnector:
    @staticmethod
    def parse_open_targets_associations(
        raw_bytes: bytes,
        *,
        expected: NetworkDiseaseTargetVerifyMetadata,
    ) -> list[NetworkDiseaseTargetRecord]:
        if not raw_bytes.strip():
            raise ValueError("Open Targets raw artifact is empty")
        try:
            payload = _load_json_without_duplicate_keys(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Open Targets raw artifact must be valid JSON") from exc

        root = _strict_object(payload, "root", {"data", "extensions"}, {"data"})
        data = _strict_object(root["data"], "data", {"disease"}, {"disease"})
        disease = _strict_object(
            data["disease"],
            "data.disease",
            {"id", "name", "associatedTargets"},
            {"id", "name", "associatedTargets"},
        )
        if (
            disease["id"] != expected.source_query_id
            or disease["name"] != expected.source_query_label
        ):
            raise ValueError("Open Targets disease query does not match declaration")
        associations = _strict_object(
            disease["associatedTargets"],
            "data.disease.associatedTargets",
            {"count", "rows"},
            {"count", "rows"},
        )
        rows = associations["rows"]
        if not isinstance(rows, list):
            raise ValueError("Open Targets associatedTargets.rows must be an array")
        if len(rows) > 500:
            raise ValueError("Open Targets artifact exceeds the 500-record limit")
        if associations["count"] != len(rows):
            raise ValueError("Open Targets associatedTargets count does not match rows")
        datatype = expected.source_query_parameters.get("datatype")
        if not isinstance(datatype, str) or not datatype:
            raise ValueError("Open Targets query parameters must declare one datatype")

        records: list[NetworkDiseaseTargetRecord] = []
        for index, value in enumerate(rows):
            row = _strict_object(
                value,
                f"associatedTargets.rows[{index}]",
                {"target", "score", "datatypeScores"},
                {"target", "score"},
            )
            target = _strict_object(
                row["target"],
                f"associatedTargets.rows[{index}].target",
                {"id", "approvedSymbol"},
                {"id", "approvedSymbol"},
            )
            score = row["score"]
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise ValueError(f"Open Targets row {index} association score must be numeric")
            if float(score) < expected.applied_threshold:
                raise ValueError("Open Targets record does not satisfy the applied threshold")
            raw_identifier = target["id"]
            canonical_symbol = target["approvedSymbol"]
            if not isinstance(raw_identifier, str) or not raw_identifier:
                raise ValueError(f"Open Targets row {index} target id must be non-empty")
            if not isinstance(canonical_symbol, str) or not canonical_symbol:
                raise ValueError(f"Open Targets row {index} approved symbol must be non-empty")
            records.append(
                NetworkDiseaseTargetRecord(
                    raw_identifier=raw_identifier,
                    canonical_symbol=canonical_symbol,
                    source_record_id=f"{expected.source_query_id}:{raw_identifier}:{datatype}",
                    source_score=float(score),
                )
            )
        return records

    @staticmethod
    def validate_trusted_manifest(
        raw_bytes: bytes,
        *,
        expected: NetworkDiseaseTargetVerifyMetadata,
        manifest_path: Path,
    ) -> None:
        try:
            manifest = _load_json_without_duplicate_keys(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                "trusted Open Targets artifact manifest is unavailable or invalid"
            ) from exc
        root = _strict_object(manifest, "manifest", {"artifacts"}, {"artifacts"})
        artifacts = root["artifacts"]
        if not isinstance(artifacts, dict):
            raise ValueError("trusted Open Targets manifest artifacts must be an object")
        artifact_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        manifest_metadata = artifacts.get(artifact_sha256)
        if manifest_metadata is None:
            raise ValueError("raw artifact hash is not registered in the trusted manifest")
        trusted = NetworkDiseaseTargetVerifyMetadata.model_validate(manifest_metadata)
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
        raise ValueError(f"Open Targets {name} must be an object")
    unknown = set(value) - allowed_keys
    missing = required_keys - set(value)
    if unknown:
        raise ValueError(f"Open Targets {name} contains unsupported fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"Open Targets {name} is missing fields: {sorted(missing)}")
    return value
