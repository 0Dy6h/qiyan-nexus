from datetime import UTC, datetime
from uuid import uuid4

from app.repositories.network_tasks import NetworkTaskRepository
from app.repositories.runtime_storage import resolve_network_tasks_storage_path
from app.schemas.network import (
    AnalysisType,
    NetworkAnalysisResult,
    NetworkAnalyzeAccepted,
    NetworkChain,
    NetworkResultResponse,
    NetworkTaskRecord,
)
from app.services.rag import DISCLAIMER


def _get_repository() -> NetworkTaskRepository:
    return NetworkTaskRepository(resolve_network_tasks_storage_path())


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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_network_analysis_task(query: str, analysis_type: AnalysisType) -> NetworkAnalyzeAccepted:
    task_id = f"network-{uuid4().hex[:12]}"
    repo = _get_repository()
    repo.upsert(
        task_id=task_id,
        query=query.strip(),
        analysis_type=analysis_type,
        status="queued",
        progress=0,
        poll_count=0,
        result=None,
        created_at=_now_iso(),
    )
    return NetworkAnalyzeAccepted(task_id=task_id, status="queued", progress=0)


def _advance(record: NetworkTaskRecord) -> tuple[NetworkTaskRecord, NetworkResultResponse]:
    repo = _get_repository()
    if record.poll_count == 0:
        next_record = repo.upsert(
            task_id=record.task_id,
            query=record.query,
            analysis_type=record.analysis_type,
            status="running",
            progress=60,
            poll_count=record.poll_count + 1,
            result=None,
            created_at=record.created_at,
        )
        return (
            next_record,
            NetworkResultResponse(
                task_id=next_record.task_id,
                status="running",
                progress=60,
                result=None,
            ),
        )

    result_payload = NetworkAnalysisResult(
        task_id=record.task_id,
        query=record.query,
        analysis_type=record.analysis_type,
        chains=_build_mock_chains(record.query, record.analysis_type),
        disclaimer=DISCLAIMER,
    )
    next_record = repo.upsert(
        task_id=record.task_id,
        query=record.query,
        analysis_type=record.analysis_type,
        status="completed",
        progress=100,
        poll_count=record.poll_count + 1,
        result=result_payload,
        created_at=record.created_at,
    )
    return (
        next_record,
        NetworkResultResponse(
            task_id=next_record.task_id,
            status="completed",
            progress=100,
            result=result_payload,
        ),
    )


def get_network_analysis_result(task_id: str) -> tuple[str, NetworkResultResponse | None]:
    repo = _get_repository()
    record = repo.get(task_id)
    if record is None:
        return "not_found", None
    _, response = _advance(record)
    return "ok", response
