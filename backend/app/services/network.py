from datetime import UTC, datetime
from uuid import uuid4

from app.repositories.network_entities import NetworkEntityRepository
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
from app.schemas.network_entities import (
    Compound,
    Pathway,
    Target,
)
from app.services.rag import DISCLAIMER

_MAX_CHAINS_PER_QUERY = 5


def _get_repository() -> NetworkTaskRepository:
    return NetworkTaskRepository(resolve_network_tasks_storage_path())


def _build_chains_from_seed(
    query: str,
    analysis_type: AnalysisType,
    entity_repo: NetworkEntityRepository | None = None,
) -> list[NetworkChain]:
    repo = entity_repo or NetworkEntityRepository()
    compounds = repo.list_compounds()
    targets_by_id: dict[str, Target] = {t.id: t for t in repo.list_targets()}
    pathways_by_id: dict[str, Pathway] = {p.id: p for p in repo.list_pathways()}
    compounds_by_id: dict[str, Compound] = {c.id: c for c in compounds}

    herb_id_to_name: dict[str, str] = {herb.id: herb.name for herb in repo.list_herbs()}
    formula_label: str | None = None
    allowed_herb_ids: set[str] | None = None

    if analysis_type == "formula":
        formula = repo.find_formula_by_query(query)
        if formula is None:
            return [chain for chain, _ in _fallback_chains(query, analysis_type, repo)][
                :_MAX_CHAINS_PER_QUERY
            ]
        formula_label = formula.name
        allowed_herb_ids = set(formula.herb_ids)
    else:
        herb = repo.find_herb_by_query(query)
        if herb is None:
            return [chain for chain, _ in _fallback_chains(query, analysis_type, repo)][
                :_MAX_CHAINS_PER_QUERY
            ]
        allowed_herb_ids = {herb.id}

    candidate_chains: list[tuple[NetworkChain, float]] = []
    for edge in repo.list_chains():
        compound = compounds_by_id.get(edge.compound_id)
        target = targets_by_id.get(edge.target_id)
        pathway = pathways_by_id.get(edge.pathway_id)
        if compound is None or target is None or pathway is None:
            continue
        candidate_herb_ids = compound.herb_ids
        if allowed_herb_ids is not None:
            candidate_herb_ids = [hid for hid in candidate_herb_ids if hid in allowed_herb_ids]
        for herb_id in candidate_herb_ids:
            herb_name = herb_id_to_name.get(herb_id)
            if not herb_name:
                continue
            chain = NetworkChain(
                herb=herb_name,
                formula=formula_label,
                compound=compound.name,
                target=target.symbol,
                pathway=pathway.name,
                disease=edge.disease,
                score=edge.score,
            )
            candidate_chains.append((chain, edge.score))

    if not candidate_chains:
        candidate_chains = _fallback_chains(query, analysis_type, repo)

    candidate_chains.sort(key=lambda pair: pair[1], reverse=True)
    return [chain for chain, _ in candidate_chains[:_MAX_CHAINS_PER_QUERY]]


def _fallback_chains(
    query: str,
    analysis_type: AnalysisType,
    repo: NetworkEntityRepository,
) -> list[tuple[NetworkChain, float]]:
    """When the query matches no herb or formula, echo the query as the herb label
    and emit a small set of top-scoring chains so the page never goes empty.
    """
    compounds_by_id = {c.id: c for c in repo.list_compounds()}
    targets_by_id = {t.id: t for t in repo.list_targets()}
    pathways_by_id = {p.id: p for p in repo.list_pathways()}
    label = query.strip() or "未识别对象"
    fallback: list[tuple[NetworkChain, float]] = []
    for edge in repo.list_chains():
        compound = compounds_by_id.get(edge.compound_id)
        target = targets_by_id.get(edge.target_id)
        pathway = pathways_by_id.get(edge.pathway_id)
        if compound is None or target is None or pathway is None:
            continue
        chain = NetworkChain(
            herb=label,
            formula=label if analysis_type == "formula" else None,
            compound=compound.name,
            target=target.symbol,
            pathway=pathway.name,
            disease=edge.disease,
            score=edge.score,
        )
        fallback.append((chain, edge.score))
    return fallback


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
        chains=_build_chains_from_seed(record.query, record.analysis_type),
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
