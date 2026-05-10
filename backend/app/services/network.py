from dataclasses import dataclass
from uuid import uuid4

from app.schemas.network import (
    AnalysisType,
    NetworkAnalysisResult,
    NetworkAnalyzeAccepted,
    NetworkChain,
    NetworkResultResponse,
)
from app.services.rag import DISCLAIMER


@dataclass
class _NetworkTaskState:
    query: str
    analysis_type: AnalysisType
    poll_count: int = 0


# Mock-only in-memory task store for the current MVP slice.
# This intentionally simulates a queued/running/completed flow inside one process
# and is not a durable multi-worker async backend.
_TASKS: dict[str, _NetworkTaskState] = {}


def _build_mock_chains(query: str, analysis_type: AnalysisType) -> list[NetworkChain]:
    herb_name = query if analysis_type == "herb" else "消风散"
    return [
        NetworkChain(
            herb=herb_name,
            compound="槲皮素",
            target="IL6",
            pathway="PI3K-Akt signaling pathway",
            disease="Atopic dermatitis",
            score=0.87,
        ),
        NetworkChain(
            herb=herb_name,
            compound="木犀草素",
            target="TNF",
            pathway="NF-kappa B signaling pathway",
            disease="Atopic dermatitis",
            score=0.82,
        ),
        NetworkChain(
            herb=herb_name,
            compound="山奈酚",
            target="STAT3",
            pathway="JAK-STAT signaling pathway",
            disease="Atopic dermatitis",
            score=0.79,
        ),
    ]


def create_network_analysis_task(query: str, analysis_type: AnalysisType) -> NetworkAnalyzeAccepted:
    task_id = f"network-{uuid4().hex[:12]}"
    _TASKS[task_id] = _NetworkTaskState(
        query=query.strip(),
        analysis_type=analysis_type,
        poll_count=0,
    )
    return NetworkAnalyzeAccepted(task_id=task_id, status="queued", progress=0)


def get_network_analysis_result(task_id: str) -> tuple[str, NetworkResultResponse | None]:
    task = _TASKS.get(task_id)
    if task is None:
        return "not_found", None

    if task.poll_count == 0:
        task.poll_count += 1
        return (
            "ok",
            NetworkResultResponse(
                task_id=task_id,
                status="running",
                progress=60,
                result=None,
            ),
        )

    task.poll_count += 1
    result = NetworkAnalysisResult(
        task_id=task_id,
        query=task.query,
        analysis_type=task.analysis_type,
        chains=_build_mock_chains(task.query, task.analysis_type),
        disclaimer=DISCLAIMER,
    )
    return (
        "ok",
        NetworkResultResponse(
            task_id=task_id,
            status="completed",
            progress=100,
            result=result,
        ),
    )
