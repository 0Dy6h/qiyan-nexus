import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.repositories.network_entities import NetworkEntityRepository
from app.repositories.runtime_storage import get_network_task_repository
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
    NetworkEntitiesResponse,
    Pathway,
    Target,
)
from app.services.enrichment import build_enrichment_result
from app.services.rag import DISCLAIMER

if TYPE_CHECKING:
    from app.repositories.protocols import NetworkTaskRepositoryProtocol

_MAX_CHAINS_PER_QUERY = 5


def _get_repository() -> "NetworkTaskRepositoryProtocol":
    return get_network_task_repository()


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
                related_entity_ids=[herb_id, compound.id, target.id, pathway.id],
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
            related_entity_ids=[compound.id, target.id, pathway.id],
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


def _load_go_terms() -> list[Any]:
    """Load GO terms from sample data."""
    path = Path(__file__).resolve().parents[2] / "data" / "network" / "sample_go_terms.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data: list[Any] = json.load(f)
        return data


def _load_kegg_pathways() -> list[Any]:
    """Load KEGG pathways from sample data."""
    path = Path(__file__).resolve().parents[2] / "data" / "network" / "sample_kegg_pathways.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data: list[Any] = json.load(f)
        return data


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

    chains = _build_chains_from_seed(record.query, record.analysis_type)

    # Extract target symbols from chains for enrichment analysis
    target_symbols = list({chain.target for chain in chains})

    # Build enrichment result if we have enough targets
    enrichment = None
    if len(target_symbols) >= 2:
        go_terms = _load_go_terms()
        kegg_pathways = _load_kegg_pathways()
        enrichment = build_enrichment_result(target_symbols, go_terms, kegg_pathways)

    result_payload = NetworkAnalysisResult(
        task_id=record.task_id,
        query=record.query,
        analysis_type=record.analysis_type,
        chains=chains,
        enrichment=enrichment,
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


def list_all_entities(
    entity_repo: NetworkEntityRepository | None = None,
) -> NetworkEntitiesResponse:
    repo = entity_repo or NetworkEntityRepository()
    return NetworkEntitiesResponse(
        herbs=repo.list_herbs(),
        formulas=repo.list_formulas(),
        compounds=repo.list_compounds(),
        targets=repo.list_targets(),
        pathways=repo.list_pathways(),
    )


def _escape_table_cell(value: str | int | float | None) -> str:
    """Escape a value for use in a Markdown table cell.

    - None / empty string → "无"
    - Pipe characters → escaped as \\|
    - Whitespace collapsed to single space
    """
    if value is None or value == "":
        return "无"
    text = str(value)
    text = text.replace("|", "\\|")
    text = " ".join(text.split())
    return text


def _format_score(score: float) -> str:
    """Format a 0-1 score as a percentage string like '85%'."""
    return f"{int(round(score * 100))}%"


def _format_entity_ids(ids: list[str]) -> str:
    """Format a list of entity IDs as a comma-separated string, or '无' if empty."""
    return ", ".join(ids) if ids else "无"


def _analysis_type_label(analysis_type: AnalysisType) -> str:
    """Return the Chinese display label for an analysis type."""
    return "单味中药" if analysis_type == "herb" else "复方"


def build_network_report_markdown(
    result: NetworkAnalysisResult,
    exported_at: str | None = None,
) -> str:
    """Build a Markdown report string equivalent to the frontend
    ``buildNetworkReportMarkdown`` function.

    The output format is strictly aligned with
    ``frontend/lib/network-report-export.ts``.
    """
    timestamp = exported_at or datetime.now(UTC).isoformat()
    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────
    lines.append("# Qiyan Nexus 网络药理学报告导出")
    lines.append("")
    lines.append(f"- 导出时间（UTC）：{timestamp}")
    lines.append(f"- task_id：{result.task_id}")
    lines.append(f"- 分析对象：{result.query}")
    lines.append(f"- 分析类型：{_analysis_type_label(result.analysis_type)}")
    lines.append(f"- 链路数量：{len(result.chains)}")
    lines.append("- 数据来源：本报告基于本地 mock seed graph 生成")
    lines.append("")
    lines.append(
        "> **数据说明**：本报告基于本地演示数据生成，仅用于功能验证与评审走查；"
        "不可作为科研发表、临床决策或真实数据库分析结果。"
    )
    lines.append("")

    # ── Chains table ────────────────────────────────────────
    lines.append("## 链路结果")
    lines.append("")
    if not result.chains:
        lines.append("（当前报告没有可导出的 mock 链路。）")
    else:
        lines.append(
            "| 序号 | 方剂 | 单味中药 | 成分 | 靶点 | 通路 | 疾病 | Mock 置信度 | 相关实体 ID |"
        )
        lines.append("|---|---|---|---|---|---|---|---:|---|")
        for idx, chain in enumerate(result.chains, start=1):
            cells = [
                str(idx),
                chain.formula,
                chain.herb,
                chain.compound,
                chain.target,
                chain.pathway,
                chain.disease,
                _format_score(chain.score),
                _format_entity_ids(chain.related_entity_ids),
            ]
            escaped = [_escape_table_cell(c) for c in cells]
            lines.append(f"| {' | '.join(escaped)} |")
    lines.append("")

    # ── Enrichment section ──────────────────────────────────
    if result.enrichment and result.enrichment.terms:
        lines.append("## 富集分析结果")
        lines.append("")
        lines.append(f"- 输入基因数：{result.enrichment.input_gene_count}")
        lines.append(f"- 背景基因数：{result.enrichment.background_gene_count}")
        lines.append(f"- 分析类型：{result.enrichment.analysis_type}")
        lines.append(f"- 富集通路/功能数：{len(result.enrichment.terms)}")
        lines.append("")
        lines.append(
            "| Term ID | 通路/功能 | 类别 | 重叠基因 | P-value | 校正后 P-value | 基因列表 |"
        )
        lines.append("|---|---|---|---:|---:|---:|---|")
        for term in result.enrichment.terms:
            term_name = term.term_name_zh or term.term_name
            overlap = f"{term.overlap_count}/{term.gene_count}"
            p_val = f"{term.p_value:.2e}"
            adj_p_val = f"{term.adjusted_p_value:.2e}"
            genes = ", ".join(term.genes)
            cells = [
                term.term_id,
                term_name,
                term.category,
                overlap,
                p_val,
                adj_p_val,
                genes,
            ]
            escaped = [_escape_table_cell(c) for c in cells]
            lines.append(f"| {' | '.join(escaped)} |")
        lines.append("")
        lines.append("### 参数说明")
        lines.append("")
        lines.append("- **P-value**：超几何分布计算的原始 p 值")
        lines.append("- **校正后 P-value**：Bonferroni 校正后的 p 值")
        lines.append("- **重叠基因**：输入基因与该通路/功能的交集数量")
        lines.append("- **过滤条件**：p < 0.05 且重叠基因数 >= 2")
        lines.append("")

    # ── Network graph placeholder ───────────────────────────
    lines.append("## 网络图")
    lines.append("")
    lines.append("![成分-靶点-通路网络图](placeholder-network-graph.png)")
    lines.append("")
    lines.append("*注：图片占位符，实际图片生成功能待后续实现*")
    lines.append("")

    # ── Boundary notes ──────────────────────────────────────
    lines.append("## 边界说明")
    lines.append("")
    lines.append("- 不是正式网络药理学计算。")
    lines.append(
        "- 富集分析基于本地 JSON 字典（mock），不代表真实 KEGG REST API 或 STRING 数据库。"
    )
    lines.append("- 不构成诊断或治疗建议，实际判断需核对原始文献、参数版本与临床背景。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(result.disclaimer)
    lines.append("")

    return "\n".join(lines)
