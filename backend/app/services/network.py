import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.core.config import get_settings
from app.repositories.network_entities import NetworkEntityRepository
from app.repositories.runtime_storage import get_network_task_repository
from app.schemas.network import (
    AnalysisType,
    DataMode,
    EvidenceLevel,
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
from app.services.network_providers import select_network_provider

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
            return []
        formula_label = formula.name
        allowed_herb_ids = set(formula.herb_ids)
    else:
        herb = repo.find_herb_by_query(query)
        if herb is None:
            return []
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

    candidate_chains.sort(key=lambda pair: pair[1], reverse=True)
    return [chain for chain, _ in candidate_chains[:_MAX_CHAINS_PER_QUERY]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _select_data_mode() -> DataMode:
    provider_name = get_settings().network_data_provider.strip().lower()
    return "live" if provider_name == "live" else "mock"


def create_network_analysis_task(
    query: str,
    analysis_type: AnalysisType,
    reviewer_id: str = "local-preview",
) -> NetworkAnalyzeAccepted:
    task_id = f"network-{uuid4().hex[:12]}"
    repo = _get_repository()
    data_mode = _select_data_mode()
    repo.upsert(
        task_id=task_id,
        owner_id=reviewer_id,
        query=query.strip(),
        analysis_type=analysis_type,
        status="queued",
        progress=0,
        poll_count=0,
        result=None,
        created_at=_now_iso(),
        data_mode=data_mode,
    )
    return NetworkAnalyzeAccepted(task_id=task_id, status="queued", progress=0, data_mode=data_mode)


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


def _advance_record(record: NetworkTaskRecord) -> NetworkTaskRecord:
    if record.status in {"completed", "failed"}:
        return record
    if record.poll_count == 0:
        return record.model_copy(
            update={
                "status": "running",
                "progress": 60,
                "poll_count": record.poll_count + 1,
                "result": None,
            }
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

    provider = select_network_provider(record.data_mode)
    result_payload = provider.build_result(
        task_id=record.task_id,
        query=record.query,
        analysis_type=record.analysis_type,
        chains=chains,
        enrichment=enrichment,
    )
    # ADR-0015: grade every chain's evidence level deterministically before
    # it is persisted or returned. Mock chains are hard-pinned to the floor.
    result_payload = result_payload.model_copy(
        update={"chains": grade_chains_evidence(result_payload.chains, data_mode=record.data_mode)}
    )
    if record.data_mode == "live" and not result_payload.chains:
        error_message = "No live target chains could be assembled."
        return record.model_copy(
            update={
                "status": "failed",
                "progress": 100,
                "poll_count": record.poll_count + 1,
                "result": None,
                "error": error_message,
                "warnings": result_payload.warnings,
            }
        )
    return record.model_copy(
        update={
            "status": "completed",
            "progress": 100,
            "poll_count": record.poll_count + 1,
            "result": result_payload,
            "error": None,
            "warnings": result_payload.warnings,
        }
    )


def _result_response(record: NetworkTaskRecord) -> NetworkResultResponse:
    return NetworkResultResponse(
        task_id=record.task_id,
        status=record.status,
        progress=record.progress,
        data_mode=record.data_mode,
        result=record.result,
        error=record.error,
        warnings=record.warnings,
    )


def get_network_analysis_result(
    task_id: str,
    reviewer_id: str = "local-preview",
) -> tuple[str, NetworkResultResponse | None]:
    repo = _get_repository()
    current = repo.get_owned(task_id, reviewer_id)
    if current is None:
        return "not_found", None
    if current.status in {"completed", "failed"}:
        return "ok", _result_response(current)
    record = repo.advance(task_id, reviewer_id, _advance_record)
    if record is None:
        return "not_found", None
    return "ok", _result_response(record)


def get_network_analysis_task(
    task_id: str,
    reviewer_id: str = "local-preview",
) -> tuple[str, NetworkResultResponse | None]:
    """Read an owner-scoped task without advancing its state machine."""
    record = _get_repository().get_owned(task_id, reviewer_id)
    if record is None:
        return "not_found", None
    return "ok", _result_response(record)


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


def _target_evidence_type_label(value: str) -> str:
    if value == "known_activity":
        return "已知活性证据"
    if value == "predicted":
        return "预测靶点"
    if value == "mixed":
        return "已知+预测"
    return "Mock"


# ── Evidence grading (ADR-0015) ─────────────────────────────
# A mechanism chain's trustworthiness is bounded by its weakest provenance
# link, so mock chains are hard-pinned to the lowest level. Deterministic:
# no randomness, no external calls, no probability/efficacy estimate.
_EVIDENCE_LEVEL_ORDER: list[EvidenceLevel] = [
    "experimental",
    "literature_supported",
    "predicted",
    "mock_inferred",
]
_EVIDENCE_LEVEL_LABELS: dict[EvidenceLevel, str] = {
    "experimental": "实验证据",
    "literature_supported": "文献支撑",
    "predicted": "预测证据",
    "mock_inferred": "演示推断（未验证）",
}


def derive_chain_evidence_level(chain: NetworkChain, *, data_mode: DataMode) -> EvidenceLevel:
    """Deterministically grade one chain's evidence support (ADR-0015)."""
    # Honesty invariant: mock data can never claim real evidence strength.
    if data_mode != "live":
        return "mock_inferred"
    if chain.target_evidence_type == "known_activity":
        return "experimental"
    if chain.target_evidence_type == "mixed" or chain.evidence_refs:
        return "literature_supported"
    # Live but only predicted / unresolved targets: weakest live tier.
    return "predicted"


def grade_chains_evidence(chains: list[NetworkChain], *, data_mode: DataMode) -> list[NetworkChain]:
    """Return new chains with ``evidence_level`` filled (immutable copy)."""
    return [
        chain.model_copy(
            update={"evidence_level": derive_chain_evidence_level(chain, data_mode=data_mode)}
        )
        for chain in chains
    ]


def _evidence_level_label(level: EvidenceLevel | None) -> str:
    return _EVIDENCE_LEVEL_LABELS.get(level or "mock_inferred", "演示推断（未验证）")


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
    lines.append(f"- 数据模式：{result.data_mode}")
    lines.append(f"- 链路数量：{len(result.chains)}")
    if result.data_mode == "live":
        lines.append("- 数据来源：显式 opt-in 真实数据链路（含缓存/导入来源）")
    else:
        lines.append("- 数据来源：本报告基于本地 mock seed graph 生成")
    lines.append("")
    if result.data_mode == "live":
        lines.append(
            "> **数据说明**：本报告来自显式启用的真实数据链路；仍需核对外部数据库版本、"
            "缓存时间、授权边界与原始记录，不可直接作为临床决策结论。"
        )
    else:
        lines.append(
            "> **数据说明**：本报告基于本地演示数据生成，仅用于功能验证与评审走查；"
            "不可作为科研发表、临床决策或真实数据库分析结果。"
        )
    lines.append("")

    if result.data_mode == "live":
        lines.append("## 数据来源与参数版本")
        lines.append("")
        if result.data_sources:
            lines.append(
                "| Source | Record ID | URL | Retrieved at | Cache | Usage note | Cache key |"
            )
            lines.append("|---|---|---|---|---|---|---|")
            for source in result.data_sources:
                cells = [
                    source.name,
                    source.source_record_id,
                    source.url,
                    source.retrieved_at,
                    "cache" if source.from_cache else "live",
                    source.license_note,
                    source.cache_key,
                ]
                escaped = [_escape_table_cell(c) for c in cells]
                lines.append(f"| {' | '.join(escaped)} |")
        else:
            lines.append("（当前结果未返回外部数据来源元数据。）")
        lines.append("")

        lines.append("## 运行步骤")
        lines.append("")
        if result.pipeline_steps:
            lines.append("| Step | Status | Duration ms | Requests | Cache hits | Warning |")
            lines.append("|---|---|---:|---:|---:|---|")
            for step in result.pipeline_steps:
                pipeline_cells: list[str | int | float | None] = [
                    step.name,
                    step.status,
                    step.duration_ms,
                    step.external_request_count,
                    step.cache_hit_count,
                    step.warning,
                ]
                escaped = [_escape_table_cell(c) for c in pipeline_cells]
                lines.append(f"| {' | '.join(escaped)} |")
        else:
            lines.append("（当前结果未返回运行步骤元数据。）")
        lines.append("")

        if result.warnings:
            lines.append("## 运行警告")
            lines.append("")
            for warning in result.warnings:
                lines.append(f"- {_escape_table_cell(warning)}")
            lines.append("")

    # ── Chains table ────────────────────────────────────────
    lines.append("## 链路结果")
    lines.append("")
    if not result.chains:
        lines.append("（当前报告没有可导出的 mock 链路。）")
    else:
        if result.data_mode == "live":
            lines.append(
                "| 序号 | 方剂 | 单味中药 | 成分 | 靶点 | 靶点证据类型 | 通路 | 疾病 | 置信度 | Evidence refs |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---:|---|")
        else:
            lines.append(
                "| 序号 | 方剂 | 单味中药 | 成分 | 靶点 | 通路 | 疾病 | Mock 置信度 | 相关实体 ID |"
            )
            lines.append("|---|---|---|---|---|---|---|---:|---|")
        for idx, chain in enumerate(result.chains, start=1):
            if result.data_mode == "live":
                cells = [
                    str(idx),
                    chain.formula,
                    chain.herb,
                    chain.compound,
                    chain.target,
                    _target_evidence_type_label(chain.target_evidence_type),
                    chain.pathway,
                    chain.disease,
                    _format_score(chain.score),
                    _format_entity_ids(chain.evidence_refs),
                ]
            else:
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

    # ── Evidence grading section (ADR-0015) ─────────────────
    lines.append("## 证据分级")
    lines.append("")
    lines.append(
        "> 依据《网络药理学评价方法指南》的可靠性/规范性/可解释性原则，对每条机制链按其"
        "最弱一环的来源给出确定性证据等级（不改变链路排序，不表示概率或疗效）。"
    )
    lines.append("")
    grading_counts: dict[EvidenceLevel, int] = {level: 0 for level in _EVIDENCE_LEVEL_ORDER}
    for graded_chain in result.chains:
        grading_counts[graded_chain.evidence_level or "mock_inferred"] += 1
    lines.append("| 证据等级 | Level | 链路数 |")
    lines.append("|---|---|---:|")
    for level in _EVIDENCE_LEVEL_ORDER:
        lines.append(f"| {_evidence_level_label(level)} | `{level}` | {grading_counts[level]} |")
    lines.append("")
    if result.data_mode != "live":
        lines.append(
            "> **边界**：本报告为 mock 演示数据，所有链路证据等级恒为 `mock_inferred`，"
            "不代表指南意义上的可靠性达标，也不可作为真实证据强度。"
        )
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
    if result.data_mode == "live":
        lines.append("- 本报告来自显式 opt-in 真实数据链路，仍需人工核对外部来源版本与缓存时间。")
        lines.append("- 预测靶点来自本地导入 artifact，不自动爬取 SwissTargetPrediction。")
        lines.append("- TCMSP 入口仅在 operator 明确允许或已有缓存时使用。")
    else:
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
