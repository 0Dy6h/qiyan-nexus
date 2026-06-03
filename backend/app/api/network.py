from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.schemas.network import NetworkAnalyzeAccepted, NetworkAnalyzeRequest, NetworkResultResponse
from app.schemas.network_entities import NetworkEntitiesResponse
from app.services.network import (
    build_network_report_markdown,
    create_network_analysis_task,
    get_network_analysis_result,
    list_all_entities,
)

router = APIRouter(prefix="/api/network", tags=["network"])


@router.post(
    "/analyze", response_model=NetworkAnalyzeAccepted, status_code=status.HTTP_202_ACCEPTED
)
def analyze_network_endpoint(request: NetworkAnalyzeRequest = Body()) -> NetworkAnalyzeAccepted:
    return create_network_analysis_task(request.query, request.analysis_type)


@router.get("/result/{task_id}", response_model=NetworkResultResponse)
def network_result_endpoint(task_id: str) -> NetworkResultResponse:
    state, payload = get_network_analysis_result(task_id)
    if state == "not_found" or payload is None:
        raise HTTPException(status_code=404, detail="Network analysis task not found")
    return payload


@router.get("/result/{task_id}/report", response_class=PlainTextResponse)
def network_report_endpoint(task_id: str) -> PlainTextResponse:
    state, payload = get_network_analysis_result(task_id)
    if state == "not_found" or payload is None:
        raise HTTPException(status_code=404, detail="Network analysis task not found")
    if payload.status != "completed":
        raise HTTPException(status_code=202, detail="Network analysis task is still running")
    if payload.result is None:
        raise HTTPException(status_code=500, detail="Task completed but result is missing")
    markdown = build_network_report_markdown(payload.result)
    return PlainTextResponse(content=markdown, media_type="text/plain; charset=utf-8")


@router.get("/entities", response_model=NetworkEntitiesResponse)
def network_entities_endpoint() -> NetworkEntitiesResponse:
    return list_all_entities()
