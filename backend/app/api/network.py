from fastapi import APIRouter, Body, HTTPException, status

from app.schemas.network import NetworkAnalyzeAccepted, NetworkAnalyzeRequest, NetworkResultResponse
from app.schemas.network_entities import NetworkEntitiesResponse
from app.services.network import (
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


@router.get("/entities", response_model=NetworkEntitiesResponse)
def network_entities_endpoint() -> NetworkEntitiesResponse:
    return list_all_entities()
