from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.config import get_settings
from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.schemas.network import (
    AnalysisType,
    DataMode,
    EnrichmentResult,
    NetworkAnalysisResult,
    NetworkChain,
    NetworkDataSource,
    NetworkPipelineStep,
    NetworkPpiEdge,
    TargetEvidenceType,
)
from app.services.enrichment import build_enrichment_result
from app.services.network_connectors import (
    ChemblConnector,
    CompoundCandidate,
    CompoundIdentity,
    KeggConnector,
    PpiEdge,
    PubChemConnector,
    StringConnector,
    TargetCandidate,
    TargetPredictionImporter,
    TcmspConnector,
    UniProtConnector,
)
from app.services.network_external_client import NetworkExternalClient
from app.services.rag import DISCLAIMER


class NetworkProvider(Protocol):
    data_mode: DataMode

    def build_result(
        self,
        *,
        task_id: str,
        query: str,
        analysis_type: AnalysisType,
        chains: list[NetworkChain],
        enrichment: EnrichmentResult | None,
    ) -> NetworkAnalysisResult: ...


class MockNetworkProvider:
    data_mode: DataMode = "mock"

    def build_result(
        self,
        *,
        task_id: str,
        query: str,
        analysis_type: AnalysisType,
        chains: list[NetworkChain],
        enrichment: EnrichmentResult | None,
    ) -> NetworkAnalysisResult:
        return NetworkAnalysisResult(
            task_id=task_id,
            query=query,
            analysis_type=analysis_type,
            data_mode="mock",
            chains=chains,
            enrichment=enrichment,
            disclaimer=DISCLAIMER,
        )


@dataclass(frozen=True)
class _LoadMetrics:
    external_request_count: int = 0
    cache_hit_count: int = 0
    duration_ms: int = 0


class LiveNetworkProvider:
    data_mode: DataMode = "live"

    def __init__(
        self,
        *,
        cache_repo: NetworkCacheRepository | None = None,
        prediction_file: Path | None = None,
        allow_tcmsp_scrape: bool | None = None,
        external_client: NetworkExternalClient | None = None,
    ) -> None:
        settings = get_settings()
        self.cache_repo = cache_repo or NetworkCacheRepository(settings.network_cache_dir)
        self.prediction_file = (
            prediction_file
            if prediction_file is not None
            else settings.network_target_prediction_file
        )
        self.allow_tcmsp_scrape = (
            allow_tcmsp_scrape
            if allow_tcmsp_scrape is not None
            else settings.network_allow_tcmsp_scrape
        )
        self.external_client = external_client or NetworkExternalClient(
            cache_repo=self.cache_repo,
            timeout_seconds=settings.network_http_timeout_seconds,
            rate_limit_per_second=settings.network_rate_limit_per_second,
        )

    def build_result(
        self,
        *,
        task_id: str,
        query: str,
        analysis_type: AnalysisType,
        chains: list[NetworkChain],
        enrichment: EnrichmentResult | None,
    ) -> NetworkAnalysisResult:
        del chains, enrichment
        warnings: list[str] = []
        data_sources: list[NetworkDataSource] = []
        pipeline_steps: list[NetworkPipelineStep] = []

        compounds_result = TcmspConnector(
            cache_repo=self.cache_repo,
            allow_scrape=self.allow_tcmsp_scrape,
            external_client=self.external_client,
        ).resolve_compounds(query=query, analysis_type=analysis_type)
        compounds = compounds_result.items
        warnings.extend(compounds_result.warnings)
        data_sources.extend(compounds_result.data_sources)
        pipeline_steps.append(
            NetworkPipelineStep(
                name="tcmsp-compound-resolution",
                status="completed" if compounds else "degraded",
                duration_ms=compounds_result.duration_ms,
                external_request_count=compounds_result.external_request_count,
                cache_hit_count=compounds_result.cache_hit_count
                or sum(1 for source in compounds_result.data_sources if source.from_cache),
                warning="; ".join(compounds_result.warnings) or None,
            )
        )

        target_candidates: list[TargetCandidate] = []
        known_request_count = 0
        known_cache_hits = 0
        known_duration_ms = 0
        for compound in compounds:
            identity, pubchem_metrics = self._load_pubchem_identity(
                compound, data_sources, warnings
            )
            known_request_count += pubchem_metrics.external_request_count
            known_cache_hits += pubchem_metrics.cache_hit_count
            known_duration_ms += pubchem_metrics.duration_ms
            targets, chembl_metrics = self._load_chembl_targets(
                compound, identity, data_sources, warnings
            )
            target_candidates.extend(targets)
            known_request_count += chembl_metrics.external_request_count
            known_cache_hits += chembl_metrics.cache_hit_count
            known_duration_ms += chembl_metrics.duration_ms
        pipeline_steps.append(
            NetworkPipelineStep(
                name="known-activity-targets",
                status="completed" if target_candidates else "degraded",
                duration_ms=known_duration_ms,
                external_request_count=known_request_count,
                cache_hit_count=known_cache_hits,
            )
        )

        prediction_result = TargetPredictionImporter(self.prediction_file).load()
        prediction_targets = _filter_predictions_for_compounds(prediction_result.items, compounds)
        target_candidates.extend(prediction_targets)
        warnings.extend(prediction_result.warnings)
        data_sources.extend(prediction_result.data_sources)
        pipeline_steps.append(
            NetworkPipelineStep(
                name="predicted-target-import",
                status="completed" if prediction_targets else "skipped",
                warning="; ".join(prediction_result.warnings) or None,
            )
        )

        uniprot_result = UniProtConnector.normalize_targets(target_candidates, self.external_client)
        normalized_targets = uniprot_result.items
        warnings.extend(uniprot_result.warnings)
        data_sources.extend(uniprot_result.data_sources)
        pipeline_steps.append(
            NetworkPipelineStep(
                name="uniprot-target-normalization",
                status="completed" if normalized_targets else "skipped",
                duration_ms=uniprot_result.duration_ms,
                external_request_count=uniprot_result.external_request_count,
                cache_hit_count=uniprot_result.cache_hit_count,
                warning="; ".join(uniprot_result.warnings) or None,
            )
        )

        merged_targets = _merge_targets(normalized_targets)
        ppi_result = StringConnector.resolve_ppi_edges(
            [target.symbol for target in merged_targets],
            self.external_client,
        )
        warnings.extend(ppi_result.warnings)
        data_sources.extend(ppi_result.data_sources)
        ppi_edges = _to_schema_ppi_edges(ppi_result.items)
        pipeline_steps.append(
            NetworkPipelineStep(
                name="string-ppi-resolution",
                status="completed" if ppi_edges else "degraded",
                duration_ms=ppi_result.duration_ms,
                external_request_count=ppi_result.external_request_count,
                cache_hit_count=ppi_result.cache_hit_count,
                warning="; ".join(ppi_result.warnings) or None,
            )
        )

        pathways, pathway_sources, pathway_warnings, pathway_metrics = self._load_kegg_pathways(
            merged_targets
        )
        data_sources.extend(pathway_sources)
        warnings.extend(pathway_warnings)
        pathway_label = pathways[0].name if pathways else "未匹配 KEGG 通路"
        pipeline_steps.append(
            NetworkPipelineStep(
                name="kegg-pathway-resolution",
                status="completed" if pathways else "degraded",
                duration_ms=pathway_metrics.duration_ms,
                external_request_count=pathway_metrics.external_request_count,
                cache_hit_count=pathway_metrics.cache_hit_count,
                warning="; ".join(pathway_warnings) or None,
            )
        )

        live_chains = [
            NetworkChain(
                herb=_compound_herb_for_target(target, compounds),
                formula=query if analysis_type == "formula" else None,
                compound=target.compound,
                target=target.symbol,
                pathway=pathway_label,
                disease="Atopic dermatitis",
                score=target.score,
                related_entity_ids=[],
                evidence_refs=_split_evidence_refs(target.source_record_id),
                target_evidence_type=target.evidence_type,
            )
            for target in merged_targets
        ]
        live_enrichment = _build_kegg_enrichment(merged_targets, pathways)
        pipeline_steps.append(
            NetworkPipelineStep(
                name="live-result-assembly",
                status="completed" if live_chains else "failed",
                warning=None if live_chains else "No live target chains could be assembled.",
            )
        )
        if not live_chains:
            warnings.append("No live target chains could be assembled.")

        return NetworkAnalysisResult(
            task_id=task_id,
            query=query,
            analysis_type=analysis_type,
            data_mode="live",
            chains=live_chains,
            enrichment=live_enrichment,
            pipeline_steps=pipeline_steps,
            data_sources=_dedupe_data_sources(data_sources),
            ppi_edges=ppi_edges,
            warnings=_dedupe_warnings(warnings),
            disclaimer=DISCLAIMER,
        )

    def _load_pubchem_identity(
        self,
        compound: CompoundCandidate,
        data_sources: list[NetworkDataSource],
        warnings: list[str],
    ) -> tuple[CompoundIdentity | None, _LoadMetrics]:
        params = {"compound": compound.name}
        cache_key = build_network_cache_key(provider="pubchem", query=compound.name, params=params)
        payload = self.cache_repo.read_json(cache_key)
        if isinstance(payload, dict):
            data_sources.append(
                NetworkDataSource(
                    name="pubchem",
                    source_record_id=compound.name,
                    url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{compound.name}",
                    license_note="PubChem PUG-REST cache/import.",
                    cache_key=cache_key,
                    from_cache=True,
                )
            )
            return (
                PubChemConnector.parse_compound_identity(compound.name, payload),
                _LoadMetrics(cache_hit_count=1),
            )

        result = PubChemConnector.resolve_compound_identity(compound, self.external_client)
        data_sources.extend(result.data_sources)
        warnings.extend(result.warnings)
        return (
            result.items[0] if result.items else None,
            _LoadMetrics(
                external_request_count=result.external_request_count,
                cache_hit_count=result.cache_hit_count,
                duration_ms=result.duration_ms,
            ),
        )

    def _load_chembl_targets(
        self,
        compound: CompoundCandidate,
        identity: CompoundIdentity | None,
        data_sources: list[NetworkDataSource],
        warnings: list[str],
    ) -> tuple[list[TargetCandidate], _LoadMetrics]:
        safe_identity = identity or CompoundIdentity(name=compound.name)
        params = {"compound": compound.name, "pubchem_cid": safe_identity.pubchem_cid or ""}
        cache_key = build_network_cache_key(provider="chembl", query=compound.name, params=params)
        payload = self.cache_repo.read_json(cache_key)
        if isinstance(payload, dict):
            data_sources.append(
                NetworkDataSource(
                    name="chembl",
                    source_record_id=safe_identity.source_record_id or compound.name,
                    url="https://www.ebi.ac.uk/chembl/",
                    license_note="ChEMBL activity cache/import.",
                    cache_key=cache_key,
                    from_cache=True,
                )
            )
            return (
                ChemblConnector.parse_activity_targets(compound, safe_identity, payload),
                _LoadMetrics(cache_hit_count=1),
            )

        result = ChemblConnector.resolve_activity_targets(
            compound, safe_identity, self.external_client
        )
        data_sources.extend(result.data_sources)
        warnings.extend(result.warnings)
        return (
            result.items,
            _LoadMetrics(
                external_request_count=result.external_request_count,
                cache_hit_count=result.cache_hit_count,
                duration_ms=result.duration_ms,
            ),
        )

    def _load_kegg_pathways(
        self,
        targets: list[TargetCandidate],
    ) -> tuple[list[Any], list[NetworkDataSource], list[str], _LoadMetrics]:
        symbols = sorted({target.symbol for target in targets})
        if not symbols:
            return [], [], ["No targets available for KEGG pathway lookup."], _LoadMetrics()
        joined = ",".join(symbols)
        params = {"genes": joined}
        cache_key = build_network_cache_key(provider="kegg", query=joined, params=params)
        payload = self.cache_repo.read_json(cache_key)
        if isinstance(payload, dict):
            pathways = KeggConnector.parse_pathways(
                str(payload.get("link_text", "")),
                str(payload.get("list_text", "")),
            )
            return (
                pathways,
                [
                    NetworkDataSource(
                        name="kegg",
                        source_record_id=joined,
                        url="https://www.kegg.jp/kegg/rest/keggapi.html",
                        license_note="KEGG REST cache/import.",
                        cache_key=cache_key,
                        from_cache=True,
                    )
                ],
                [],
                _LoadMetrics(cache_hit_count=1),
            )

        result = KeggConnector.resolve_pathways(symbols, self.external_client)
        return (
            result.items,
            result.data_sources,
            result.warnings,
            _LoadMetrics(
                external_request_count=result.external_request_count,
                cache_hit_count=result.cache_hit_count,
                duration_ms=result.duration_ms,
            ),
        )


def select_network_provider(data_mode: DataMode) -> NetworkProvider:
    if data_mode == "live":
        return LiveNetworkProvider()
    return MockNetworkProvider()


def _filter_predictions_for_compounds(
    targets: list[TargetCandidate],
    compounds: list[CompoundCandidate],
) -> list[TargetCandidate]:
    compound_names = {compound.name.lower() for compound in compounds}
    return [target for target in targets if target.compound.lower() in compound_names]


def _merge_targets(targets: list[TargetCandidate]) -> list[TargetCandidate]:
    by_key: dict[tuple[str, str], TargetCandidate] = {}
    for target in targets:
        key = (target.compound.lower(), target.symbol.upper())
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = target
            continue
        evidence_type: TargetEvidenceType = (
            "mixed" if existing.evidence_type != target.evidence_type else target.evidence_type
        )
        by_key[key] = TargetCandidate(
            compound=target.compound,
            symbol=target.symbol,
            evidence_type=evidence_type,
            score=max(existing.score, target.score),
            source=f"{existing.source}+{target.source}",
            source_record_id=";".join(
                ref for ref in [existing.source_record_id, target.source_record_id] if ref
            )
            or None,
            retrieved_at=target.retrieved_at or existing.retrieved_at,
        )
    return list(by_key.values())


def _compound_herb_for_target(
    target: TargetCandidate,
    compounds: list[CompoundCandidate],
) -> str:
    for compound in compounds:
        if compound.name == target.compound:
            return compound.herb
    return "未识别中药"


def _build_kegg_enrichment(
    targets: list[TargetCandidate],
    pathways: list[Any],
) -> EnrichmentResult | None:
    target_symbols = sorted({target.symbol for target in targets})
    kegg_terms = [
        {
            "id": pathway.term_id,
            "name": pathway.name,
            "name_zh": None,
            "genes": pathway.genes,
        }
        for pathway in pathways
    ]
    return build_enrichment_result(target_symbols, [], kegg_terms)


def _to_schema_ppi_edges(edges: list[PpiEdge]) -> list[NetworkPpiEdge]:
    return [
        NetworkPpiEdge(
            source=edge.source,
            target=edge.target,
            score=edge.score,
            source_record_id=edge.source_record_id,
        )
        for edge in edges
    ]


def _split_evidence_refs(value: str | None) -> list[str]:
    if not value:
        return []
    return [ref for ref in (part.strip() for part in value.split(";")) if ref]


def _dedupe_data_sources(sources: list[NetworkDataSource]) -> list[NetworkDataSource]:
    seen: set[tuple[str, str | None, str | None]] = set()
    result: list[NetworkDataSource] = []
    for source in sources:
        key = (source.name, source.source_record_id, source.cache_key)
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    return list(dict.fromkeys(warning for warning in warnings if warning))
