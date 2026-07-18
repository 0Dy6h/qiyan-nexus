import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import TypeAdapter, ValidationError
from starlette.datastructures import UploadFile

from app.core.reviewer_identity import require_reviewer_id
from app.schemas.network import (
    AnalysisType,
    EvidencePolicy,
    NetworkAnalyzeAccepted,
    NetworkAnalyzeRequest,
    NetworkCompoundTargetVerifyMetadata,
    NetworkDiseaseTargetVerifyMetadata,
    NetworkResultResponse,
)
from app.schemas.network_entities import NetworkEntitiesResponse
from app.services.network import (
    build_network_report_markdown,
    create_network_analysis_task,
    create_verified_compound_network_analysis_task,
    create_verified_network_analysis_task,
    get_network_analysis_result,
    get_network_analysis_task,
    list_all_entities,
)

router = APIRouter(prefix="/api/network", tags=["network"])
_MAX_RAW_ARTIFACT_BYTES = 5 * 1024 * 1024
_MAX_VERIFY_REQUEST_BYTES = _MAX_RAW_ARTIFACT_BYTES + 256 * 1024
_ANALYSIS_TYPE_ADAPTER: TypeAdapter[AnalysisType] = TypeAdapter(AnalysisType)
_EVIDENCE_POLICY_ADAPTER: TypeAdapter[EvidencePolicy] = TypeAdapter(EvidencePolicy)


@router.post(
    "/analyze", response_model=NetworkAnalyzeAccepted, status_code=status.HTTP_202_ACCEPTED
)
def analyze_network_endpoint(
    reviewer_id: Annotated[str, Depends(require_reviewer_id)],
    request: NetworkAnalyzeRequest = Body(),
) -> NetworkAnalyzeAccepted:
    return create_network_analysis_task(
        request.query,
        request.analysis_type,
        reviewer_id,
        request.research_protocol,
        request.disease_target_import,
    )


@router.post(
    "/disease-import/verify",
    response_model=NetworkAnalyzeAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def verify_disease_import_endpoint(
    request: Request,
    reviewer_id: Annotated[str, Depends(require_reviewer_id)],
) -> NetworkAnalyzeAccepted:
    if request.headers.get("transfer-encoding") is not None:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    content_length = request.headers.get("content-length")
    if content_length is None:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    try:
        declared_length = int(content_length)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid Content-Length") from exc
    if declared_length < 0:
        raise HTTPException(status_code=422, detail="invalid Content-Length")
    if declared_length > _MAX_VERIFY_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="Open Targets raw artifact is too large")
    form = await request.form(max_files=1, max_fields=5, max_part_size=_MAX_RAW_ARTIFACT_BYTES)
    submitted_fields = set(form.keys())
    allowed_fields = {"query", "metadata", "file", "analysis_type", "evidence_policy"}
    extra_fields = submitted_fields - allowed_fields
    if extra_fields:
        raise HTTPException(
            status_code=422,
            detail=f"unexpected multipart fields: {sorted(extra_fields)}",
        )
    repeated_or_missing_fields = sorted(
        [field for field in {"query", "metadata", "file"} if len(form.getlist(field)) != 1]
        + [field for field in {"analysis_type", "evidence_policy"} if len(form.getlist(field)) > 1]
    )
    if repeated_or_missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"multipart fields have invalid cardinality: {repeated_or_missing_fields}",
        )
    query_value = form.get("query")
    metadata_value = form.get("metadata")
    file_value = form.get("file")
    if not isinstance(query_value, str) or not query_value.strip():
        raise HTTPException(status_code=422, detail="query is required")
    if not isinstance(metadata_value, str):
        raise HTTPException(status_code=422, detail="metadata is required")
    if not isinstance(file_value, UploadFile):
        raise HTTPException(status_code=422, detail="Open Targets raw artifact file is required")
    try:
        analysis_type = _ANALYSIS_TYPE_ADAPTER.validate_python(form.get("analysis_type", "formula"))
        evidence_policy = _EVIDENCE_POLICY_ADAPTER.validate_python(
            form.get("evidence_policy", "direct_human_first")
        )
        metadata_payload = json.loads(metadata_value)
        verified_metadata = NetworkDiseaseTargetVerifyMetadata.model_validate(metadata_payload)
        raw_bytes = await file_value.read(_MAX_RAW_ARTIFACT_BYTES + 1)
        if len(raw_bytes) > _MAX_RAW_ARTIFACT_BYTES:
            raise HTTPException(status_code=413, detail="Open Targets raw artifact is too large")
        return create_verified_network_analysis_task(
            query=query_value,
            analysis_type=analysis_type,
            reviewer_id=reviewer_id,
            evidence_policy=evidence_policy,
            metadata=verified_metadata,
            raw_bytes=raw_bytes,
            source_artifact_filename=file_value.filename or "open-targets-associations.json",
            source_artifact_media_type=file_value.content_type or "application/octet-stream",
        )
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/compound-import/verify",
    response_model=NetworkAnalyzeAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def verify_compound_import_endpoint(
    request: Request,
    reviewer_id: Annotated[str, Depends(require_reviewer_id)],
) -> NetworkAnalyzeAccepted:
    if request.headers.get("transfer-encoding") is not None:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    content_length = request.headers.get("content-length")
    if content_length is None:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    try:
        declared_length = int(content_length)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid Content-Length") from exc
    if declared_length < 0:
        raise HTTPException(status_code=422, detail="invalid Content-Length")
    if declared_length > _MAX_VERIFY_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="ChEMBL raw artifact is too large")
    form = await request.form(max_files=1, max_fields=3, max_part_size=_MAX_RAW_ARTIFACT_BYTES)
    submitted_fields = set(form.keys())
    allowed_fields = {"source_task_id", "metadata", "file"}
    extra_fields = submitted_fields - allowed_fields
    if extra_fields:
        raise HTTPException(
            status_code=422,
            detail=f"unexpected multipart fields: {sorted(extra_fields)}",
        )
    repeated_or_missing_fields = sorted(
        field for field in allowed_fields if len(form.getlist(field)) != 1
    )
    if repeated_or_missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"multipart fields must each appear exactly once: {repeated_or_missing_fields}",
        )
    source_task_id = form.get("source_task_id")
    metadata_value = form.get("metadata")
    file_value = form.get("file")
    if not isinstance(source_task_id, str) or not source_task_id.strip():
        raise HTTPException(status_code=422, detail="source_task_id is required")
    if not isinstance(metadata_value, str):
        raise HTTPException(status_code=422, detail="metadata is required")
    if not isinstance(file_value, UploadFile):
        raise HTTPException(status_code=422, detail="ChEMBL raw artifact file is required")
    try:
        metadata_payload = json.loads(metadata_value)
        verified_metadata = NetworkCompoundTargetVerifyMetadata.model_validate(metadata_payload)
        raw_bytes = await file_value.read(_MAX_RAW_ARTIFACT_BYTES + 1)
        if len(raw_bytes) > _MAX_RAW_ARTIFACT_BYTES:
            raise HTTPException(status_code=413, detail="ChEMBL raw artifact is too large")
        return create_verified_compound_network_analysis_task(
            source_task_id=source_task_id.strip(),
            reviewer_id=reviewer_id,
            metadata=verified_metadata,
            raw_bytes=raw_bytes,
            source_artifact_filename=file_value.filename or "chembl-known-activities.json",
            source_artifact_media_type=file_value.content_type or "application/octet-stream",
        )
    except HTTPException:
        raise
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Network analysis task not found") from exc
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/result/{task_id}", response_model=NetworkResultResponse)
def network_result_endpoint(
    task_id: str,
    reviewer_id: Annotated[str, Depends(require_reviewer_id)],
) -> NetworkResultResponse:
    state, payload = get_network_analysis_result(task_id, reviewer_id)
    if state == "not_found" or payload is None:
        raise HTTPException(status_code=404, detail="Network analysis task not found")
    return payload


@router.get("/result/{task_id}/report", response_class=PlainTextResponse)
def network_report_endpoint(
    task_id: str,
    reviewer_id: Annotated[str, Depends(require_reviewer_id)],
) -> PlainTextResponse:
    state, payload = get_network_analysis_task(task_id, reviewer_id)
    if state == "not_found" or payload is None:
        raise HTTPException(status_code=404, detail="Network analysis task not found")
    if payload.status == "failed":
        raise HTTPException(status_code=409, detail=payload.error or "Network analysis task failed")
    if payload.status != "completed":
        raise HTTPException(status_code=202, detail="Network analysis task is still running")
    if payload.result is None:
        raise HTTPException(status_code=500, detail="Task completed but result is missing")
    markdown = build_network_report_markdown(payload.result)
    return PlainTextResponse(content=markdown, media_type="text/plain; charset=utf-8")


@router.get("/entities", response_model=NetworkEntitiesResponse)
def network_entities_endpoint() -> NetworkEntitiesResponse:
    return list_all_entities()
