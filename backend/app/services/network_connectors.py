from __future__ import annotations

import csv
import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar
from urllib.parse import quote

from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.repositories.network_entities import NetworkEntityRepository
from app.schemas.network import AnalysisType, NetworkDataSource, TargetEvidenceType
from app.services.network_external_client import NetworkExternalClient

T = TypeVar("T")


@dataclass(frozen=True)
class ConnectorResult(Generic[T]):
    items: list[T]
    data_sources: list[NetworkDataSource] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    external_request_count: int = 0
    cache_hit_count: int = 0
    duration_ms: int = 0


@dataclass(frozen=True)
class CompoundCandidate:
    name: str
    herb: str
    source_record_id: str | None = None
    source_url: str | None = None
    properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CompoundIdentity:
    name: str
    pubchem_cid: str | None = None
    source_record_id: str | None = None


@dataclass(frozen=True)
class TargetCandidate:
    compound: str
    symbol: str
    evidence_type: TargetEvidenceType
    score: float
    source: str
    source_record_id: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True)
class NormalizedTarget:
    query: str
    symbol: str
    accession: str | None = None
    protein_name: str | None = None


@dataclass(frozen=True)
class PpiEdge:
    source: str
    target: str
    score: float
    source_record_id: str


@dataclass(frozen=True)
class KeggPathway:
    term_id: str
    name: str
    genes: list[str]
    source_record_id: str


class TcmspConnector:
    def __init__(
        self,
        *,
        cache_repo: NetworkCacheRepository,
        allow_scrape: bool,
        fetch_html: Callable[[str], str] | None = None,
        external_client: NetworkExternalClient | None = None,
        entity_repo: NetworkEntityRepository | None = None,
    ) -> None:
        self.cache_repo = cache_repo
        self.allow_scrape = allow_scrape
        self.fetch_html = fetch_html
        self.external_client = external_client
        self.entity_repo = entity_repo or NetworkEntityRepository()

    @staticmethod
    def parse_compounds_from_html(raw_html: str, *, herb_name: str) -> list[CompoundCandidate]:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not rows:
            return []

        headers: list[str] = []
        compounds: list[CompoundCandidate] = []
        for row in rows:
            header_cells = re.findall(r"<th[^>]*>(.*?)</th>", row, flags=re.IGNORECASE | re.DOTALL)
            if header_cells:
                headers = [_clean_cell(cell) for cell in header_cells]
                continue
            cells = [
                _clean_cell(cell)
                for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
            ]
            if not cells:
                continue
            name_index = _find_name_column(headers)
            name = cells[name_index] if name_index < len(cells) else cells[0]
            if not name:
                continue
            properties = {
                headers[index]: value
                for index, value in enumerate(cells)
                if index < len(headers) and headers[index] and index != name_index
            }
            compounds.append(
                CompoundCandidate(
                    name=name,
                    herb=herb_name,
                    source_record_id=f"tcmsp:{herb_name}:{name}",
                    properties=properties,
                )
            )
        return compounds

    def resolve_compounds(
        self,
        *,
        query: str,
        analysis_type: AnalysisType,
    ) -> ConnectorResult[CompoundCandidate]:
        herb_names = self._resolve_herb_names(query=query, analysis_type=analysis_type)
        all_compounds: list[CompoundCandidate] = []
        data_sources: list[NetworkDataSource] = []
        warnings: list[str] = []
        external_request_count = 0
        cache_hit_count = 0
        duration_ms = 0

        for herb_name in herb_names:
            cache_key = build_network_cache_key(
                provider="tcmsp",
                query=herb_name,
                params={"herb": herb_name, "analysis_type": "herb"},
            )
            cached = self.cache_repo.read_json(cache_key)
            if isinstance(cached, dict) and isinstance(cached.get("compounds"), list):
                compounds = [
                    CompoundCandidate(
                        name=str(item.get("name", "")),
                        herb=str(item.get("herb") or herb_name),
                        source_record_id=item.get("source_record_id"),
                        source_url=item.get("source_url"),
                        properties={
                            str(key): str(value)
                            for key, value in dict(item.get("properties", {})).items()
                        },
                    )
                    for item in cached["compounds"]
                    if item.get("name")
                ]
                all_compounds.extend(compounds)
                data_sources.append(
                    NetworkDataSource(
                        name="TCMSP scraped/cache",
                        source_record_id=herb_name,
                        url=None,
                        license_note="TCMSP cache generated by explicit opt-in scraping/import.",
                        cache_key=cache_key,
                        from_cache=True,
                    )
                )
                continue

            if not self.allow_scrape:
                warnings.append("TCMSP scraping is disabled and no cached compounds were found.")
                continue

            if self.fetch_html is None and self.external_client is None:
                warnings.append("TCMSP scraping is enabled but no fetcher is configured.")
                continue

            if self.fetch_html is not None:
                raw_html = self.fetch_html(herb_name)
                source = NetworkDataSource(
                    name="TCMSP scraped/cache",
                    source_record_id=herb_name,
                    license_note="TCMSP scraped only after explicit operator opt-in.",
                    cache_key=cache_key,
                    from_cache=False,
                )
            else:
                assert self.external_client is not None
                html_result = self.external_client.get_text(
                    provider="tcmsp-html",
                    url="https://tcmsp-e.com/tcmspsearch.php",
                    query=herb_name,
                    params={"qr": herb_name, "qsr": "herb_cn_name"},
                    license_note="TCMSP HTML scraping entry; explicit opt-in only.",
                )
                external_request_count += html_result.request_count
                cache_hit_count += 1 if html_result.from_cache else 0
                duration_ms += html_result.latency_ms
                if html_result.warning:
                    warnings.append(html_result.warning)
                if html_result.payload is None:
                    continue
                raw_html = html_result.payload
                source = html_result.data_source.model_copy(update={"name": "TCMSP scraped/cache"})

            compounds = self.parse_compounds_from_html(raw_html, herb_name=herb_name)
            if not compounds:
                warnings.append("TCMSP compound parser returned no compounds.")
                continue
            self.cache_repo.write_json(
                cache_key,
                {
                    "compounds": [
                        {
                            "name": compound.name,
                            "herb": compound.herb,
                            "source_record_id": compound.source_record_id,
                            "source_url": compound.source_url,
                            "properties": compound.properties,
                        }
                        for compound in compounds
                    ]
                },
            )
            all_compounds.extend(compounds)
            data_sources.append(source)

        return ConnectorResult(
            items=_dedupe_compounds(all_compounds),
            data_sources=data_sources,
            warnings=warnings,
            external_request_count=external_request_count,
            cache_hit_count=cache_hit_count,
            duration_ms=duration_ms,
        )

    def _resolve_herb_names(self, *, query: str, analysis_type: AnalysisType) -> list[str]:
        if analysis_type == "herb":
            herb = self.entity_repo.find_herb_by_query(query)
            return [herb.name if herb else query]

        formula = self.entity_repo.find_formula_by_query(query)
        if formula is None:
            return [query]
        herbs_by_id = {herb.id: herb.name for herb in self.entity_repo.list_herbs()}
        return [herbs_by_id[herb_id] for herb_id in formula.herb_ids if herb_id in herbs_by_id]


class PubChemConnector:
    @staticmethod
    def resolve_compound_identity(
        compound: CompoundCandidate,
        external_client: NetworkExternalClient,
    ) -> ConnectorResult[CompoundIdentity]:
        encoded_name = quote(compound.name, safe="")
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON"
        result = external_client.get_json(
            provider="pubchem",
            url=url,
            query=compound.name,
            params={"compound": compound.name},
            license_note="PubChem PUG-REST name-to-CID lookup.",
        )
        data_sources = [result.data_source]
        warnings = [result.warning] if result.warning else []
        if not isinstance(result.payload, dict):
            warnings.append(f"PubChem lookup did not return JSON for compound {compound.name}.")
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=result.request_count,
                cache_hit_count=1 if result.from_cache else 0,
                duration_ms=result.latency_ms,
            )
        identity = PubChemConnector.parse_compound_identity(compound.name, result.payload)
        if identity is None:
            warnings.append(f"PubChem CID not found for compound {compound.name}.")
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=result.request_count,
                cache_hit_count=1 if result.from_cache else 0,
                duration_ms=result.latency_ms,
            )
        return ConnectorResult(
            items=[identity],
            data_sources=data_sources,
            warnings=warnings,
            external_request_count=result.request_count,
            cache_hit_count=1 if result.from_cache else 0,
            duration_ms=result.latency_ms,
        )

    @staticmethod
    def parse_compound_identity(name: str, payload: dict[str, Any]) -> CompoundIdentity | None:
        cid: Any | None = None
        identifier_list = payload.get("IdentifierList")
        if isinstance(identifier_list, dict):
            cids = identifier_list.get("CID")
            if isinstance(cids, list) and cids:
                cid = cids[0]
        if cid is None:
            return None
        return CompoundIdentity(name=name, pubchem_cid=str(cid), source_record_id=f"CID:{cid}")


class ChemblConnector:
    @staticmethod
    def resolve_activity_targets(
        compound: CompoundCandidate,
        identity: CompoundIdentity,
        external_client: NetworkExternalClient,
    ) -> ConnectorResult[TargetCandidate]:
        molecule_result = external_client.get_json(
            provider="chembl",
            url="https://www.ebi.ac.uk/chembl/api/data/molecule.json",
            query=compound.name,
            params={
                "molecule_synonyms__molecule_synonym__iexact": compound.name,
                "limit": 1,
            },
            license_note="ChEMBL molecule synonym lookup.",
        )
        data_sources = [molecule_result.data_source]
        warnings = [molecule_result.warning] if molecule_result.warning else []
        request_count = molecule_result.request_count
        cache_hit_count = 1 if molecule_result.from_cache else 0
        duration_ms = molecule_result.latency_ms

        molecule_id = ChemblConnector.parse_molecule_chembl_id(molecule_result.payload)
        if molecule_id is None:
            warnings.append(f"ChEMBL molecule not found for compound {compound.name}.")
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=request_count,
                cache_hit_count=cache_hit_count,
                duration_ms=duration_ms,
            )

        activity_result = external_client.get_json(
            provider="chembl",
            url="https://www.ebi.ac.uk/chembl/api/data/activity.json",
            query=molecule_id,
            params={
                "molecule_chembl_id": molecule_id,
                "target_organism": "Homo sapiens",
                "limit": 50,
            },
            license_note="ChEMBL human bioactivity records.",
        )
        data_sources.append(activity_result.data_source)
        if activity_result.warning:
            warnings.append(activity_result.warning)
        request_count += activity_result.request_count
        cache_hit_count += 1 if activity_result.from_cache else 0
        duration_ms += activity_result.latency_ms

        if not isinstance(activity_result.payload, dict):
            warnings.append(f"ChEMBL activity lookup did not return JSON for {compound.name}.")
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=request_count,
                cache_hit_count=cache_hit_count,
                duration_ms=duration_ms,
            )

        return ConnectorResult(
            items=ChemblConnector.parse_activity_targets(
                compound, identity, activity_result.payload
            ),
            data_sources=data_sources,
            warnings=warnings,
            external_request_count=request_count,
            cache_hit_count=cache_hit_count,
            duration_ms=duration_ms,
        )

    @staticmethod
    def parse_molecule_chembl_id(payload: Any | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        molecules = payload.get("molecules")
        if not isinstance(molecules, list) or not molecules:
            return None
        first = molecules[0]
        if not isinstance(first, dict):
            return None
        molecule_id = first.get("molecule_chembl_id")
        return str(molecule_id) if molecule_id else None

    @staticmethod
    def parse_activity_targets(
        compound: CompoundCandidate,
        identity: CompoundIdentity,
        payload: dict[str, Any],
    ) -> list[TargetCandidate]:
        activities = payload.get("activities", [])
        if not isinstance(activities, list):
            return []

        targets: list[TargetCandidate] = []
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            organism = str(activity.get("target_organism", ""))
            if organism and organism != "Homo sapiens":
                continue
            symbol = str(activity.get("target_pref_name") or activity.get("target_chembl_id") or "")
            if not symbol:
                continue
            score = _pchembl_to_score(activity.get("pchembl_value"))
            targets.append(
                TargetCandidate(
                    compound=compound.name,
                    symbol=symbol,
                    evidence_type="known_activity",
                    score=score,
                    source="ChEMBL",
                    source_record_id=activity.get("assay_chembl_id")
                    or activity.get("activity_id")
                    or identity.source_record_id,
                )
            )
        return targets


class TargetPredictionImporter:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ConnectorResult[TargetCandidate]:
        if str(self.path) in {"", "."} or not self.path.is_file():
            return ConnectorResult(
                items=[],
                warnings=["Prediction target file is not configured or does not exist."],
            )

        raw_items = self._read_items()
        targets: list[TargetCandidate] = []
        data_sources_by_name: dict[str, NetworkDataSource] = {}
        for item in raw_items:
            source = str(item.get("source") or "target-prediction-import")
            target = TargetCandidate(
                compound=str(item.get("compound", "")),
                symbol=str(item.get("target_symbol", "")),
                evidence_type="predicted",
                score=float(item.get("score") or 0.0),
                source=source,
                source_record_id=item.get("source_record_id"),
                retrieved_at=item.get("retrieved_at"),
            )
            if not target.compound or not target.symbol:
                continue
            targets.append(target)
            data_sources_by_name.setdefault(
                source,
                NetworkDataSource(
                    name=source,
                    source_record_id=item.get("source_record_id"),
                    retrieved_at=item.get("retrieved_at"),
                    license_note="Imported target prediction artifact; no automated SwissTargetPrediction crawling.",
                    cache_key=str(self.path),
                    from_cache=True,
                ),
            )
        return ConnectorResult(items=targets, data_sources=list(data_sources_by_name.values()))

    def _read_items(self) -> list[dict[str, Any]]:
        if self.path.suffix.lower() == ".json":
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [dict(item) for item in raw] if isinstance(raw, list) else []

        with self.path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]


class StringConnector:
    @staticmethod
    def resolve_ppi_edges(
        symbols: list[str],
        external_client: NetworkExternalClient,
    ) -> ConnectorResult[PpiEdge]:
        unique_symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        if not unique_symbols:
            return ConnectorResult(
                items=[], warnings=["No targets available for STRING PPI lookup."]
            )
        identifiers = "\r".join(unique_symbols)
        result = external_client.get_text(
            provider="string",
            url="https://string-db.org/api/tsv/network",
            query=",".join(unique_symbols),
            params={
                "identifiers": identifiers,
                "species": 9606,
                "required_score": 400,
            },
            license_note="STRING protein-protein interaction API.",
        )
        data_sources = [result.data_source]
        warnings = [result.warning] if result.warning else []
        if result.payload is None:
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=result.request_count,
                cache_hit_count=1 if result.from_cache else 0,
                duration_ms=result.latency_ms,
            )
        return ConnectorResult(
            items=StringConnector.parse_network_tsv(result.payload),
            data_sources=data_sources,
            warnings=warnings,
            external_request_count=result.request_count,
            cache_hit_count=1 if result.from_cache else 0,
            duration_ms=result.latency_ms,
        )

    @staticmethod
    def parse_network_tsv(text: str) -> list[PpiEdge]:
        reader = csv.DictReader(text.splitlines(), delimiter="\t")
        edges: list[PpiEdge] = []
        for row in reader:
            source = row.get("preferredName_A") or row.get("stringId_A") or ""
            target = row.get("preferredName_B") or row.get("stringId_B") or ""
            if not source or not target:
                continue
            score = float(row.get("score") or 0.0)
            edges.append(
                PpiEdge(
                    source=source,
                    target=target,
                    score=score,
                    source_record_id=f"STRING:{source}-{target}",
                )
            )
        return edges


class KeggConnector:
    @staticmethod
    def resolve_pathways(
        symbols: list[str],
        external_client: NetworkExternalClient,
    ) -> ConnectorResult[KeggPathway]:
        unique_symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        if not unique_symbols:
            return ConnectorResult(
                items=[], warnings=["No targets available for KEGG pathway lookup."]
            )

        data_sources: list[NetworkDataSource] = []
        warnings: list[str] = []
        request_count = 0
        cache_hit_count = 0
        duration_ms = 0
        gene_ids: list[str] = []
        gene_id_to_symbol: dict[str, str] = {}

        for symbol in unique_symbols:
            encoded_symbol = quote(symbol, safe="")
            find_result = external_client.get_text(
                provider="kegg",
                url=f"https://rest.kegg.jp/find/hsa/{encoded_symbol}",
                query=f"find:{symbol}",
                params={"database": "hsa", "symbol": symbol},
                license_note="KEGG REST gene lookup.",
            )
            data_sources.append(find_result.data_source)
            request_count += find_result.request_count
            cache_hit_count += 1 if find_result.from_cache else 0
            duration_ms += find_result.latency_ms
            if find_result.warning:
                warnings.append(find_result.warning)
            gene_id = KeggConnector.parse_first_hsa_gene_id(find_result.payload or "")
            if gene_id is None:
                warnings.append(f"KEGG gene id not found for target {symbol}.")
                continue
            gene_ids.append(gene_id)
            gene_id_to_symbol[gene_id.split(":", maxsplit=1)[-1]] = symbol

        if not gene_ids:
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=request_count,
                cache_hit_count=cache_hit_count,
                duration_ms=duration_ms,
            )

        joined_gene_ids = "+".join(gene_ids)
        link_result = external_client.get_text(
            provider="kegg",
            url=f"https://rest.kegg.jp/link/pathway/{joined_gene_ids}",
            query=f"link:{','.join(gene_ids)}",
            params={"target_db": "pathway", "genes": joined_gene_ids},
            license_note="KEGG REST gene-to-pathway links.",
        )
        data_sources.append(link_result.data_source)
        request_count += link_result.request_count
        cache_hit_count += 1 if link_result.from_cache else 0
        duration_ms += link_result.latency_ms
        if link_result.warning:
            warnings.append(link_result.warning)
        pathway_ids = KeggConnector.parse_pathway_ids(link_result.payload or "")
        if not pathway_ids:
            warnings.append("KEGG returned no pathways for live targets.")
            return ConnectorResult(
                items=[],
                data_sources=data_sources,
                warnings=warnings,
                external_request_count=request_count,
                cache_hit_count=cache_hit_count,
                duration_ms=duration_ms,
            )

        joined_pathways = "+".join(f"path:{pathway_id}" for pathway_id in pathway_ids)
        list_result = external_client.get_text(
            provider="kegg",
            url=f"https://rest.kegg.jp/list/{joined_pathways}",
            query=f"list:{','.join(pathway_ids)}",
            params={"pathways": joined_pathways},
            license_note="KEGG REST pathway metadata.",
        )
        data_sources.append(list_result.data_source)
        request_count += list_result.request_count
        cache_hit_count += 1 if list_result.from_cache else 0
        duration_ms += list_result.latency_ms
        if list_result.warning:
            warnings.append(list_result.warning)

        pathways = [
            KeggPathway(
                term_id=pathway.term_id,
                name=pathway.name,
                genes=[gene_id_to_symbol.get(gene, gene) for gene in pathway.genes],
                source_record_id=pathway.source_record_id,
            )
            for pathway in KeggConnector.parse_pathways(
                link_result.payload or "", list_result.payload or ""
            )
        ]
        return ConnectorResult(
            items=pathways,
            data_sources=data_sources,
            warnings=warnings,
            external_request_count=request_count,
            cache_hit_count=cache_hit_count,
            duration_ms=duration_ms,
        )

    @staticmethod
    def parse_first_hsa_gene_id(text: str) -> str | None:
        for raw_line in text.splitlines():
            if not raw_line.strip():
                continue
            gene_raw = raw_line.split("\t", maxsplit=1)[0]
            if gene_raw.startswith("hsa:"):
                return gene_raw
        return None

    @staticmethod
    def parse_pathway_ids(text: str) -> list[str]:
        pathway_ids: list[str] = []
        for raw_line in text.splitlines():
            if not raw_line.strip():
                continue
            _, pathway_raw = raw_line.split("\t", maxsplit=1)
            pathway_id = pathway_raw.split(":", maxsplit=1)[-1]
            if pathway_id not in pathway_ids:
                pathway_ids.append(pathway_id)
        return pathway_ids

    @staticmethod
    def parse_pathways(link_text: str, list_text: str) -> list[KeggPathway]:
        pathway_to_genes: dict[str, list[str]] = {}
        for raw_line in link_text.splitlines():
            if not raw_line.strip():
                continue
            left, right = raw_line.split("\t", maxsplit=1)
            gene = left.split(":", maxsplit=1)[-1]
            pathway = right.split(":", maxsplit=1)[-1]
            pathway_to_genes.setdefault(pathway, []).append(gene)

        names: dict[str, str] = {}
        for raw_line in list_text.splitlines():
            if not raw_line.strip():
                continue
            pathway_raw, name_raw = raw_line.split("\t", maxsplit=1)
            pathway = pathway_raw.split(":", maxsplit=1)[-1]
            names[pathway] = name_raw.split(" - ", maxsplit=1)[0].strip()

        return [
            KeggPathway(
                term_id=pathway,
                name=names.get(pathway, pathway),
                genes=genes,
                source_record_id=f"path:{pathway}",
            )
            for pathway, genes in sorted(pathway_to_genes.items())
        ]


def _clean_cell(cell: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", cell)
    return html.unescape(" ".join(without_tags.split())).strip()


def _find_name_column(headers: list[str]) -> int:
    for index, header in enumerate(headers):
        lowered = header.lower()
        if "molecule" in lowered or "compound" in lowered or "name" == lowered:
            return index
    return 0


def _dedupe_compounds(compounds: list[CompoundCandidate]) -> list[CompoundCandidate]:
    seen: set[tuple[str, str]] = set()
    result: list[CompoundCandidate] = []
    for compound in compounds:
        key = (compound.herb, compound.name.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(compound)
    return result


def _pchembl_to_score(value: Any) -> float:
    try:
        score = float(value) / 10
    except (TypeError, ValueError):
        score = 0.5
    return max(0.0, min(score, 1.0))


class UniProtConnector:
    @staticmethod
    def normalize_targets(
        targets: list[TargetCandidate],
        external_client: NetworkExternalClient,
    ) -> ConnectorResult[TargetCandidate]:
        normalized_targets: list[TargetCandidate] = []
        data_sources: list[NetworkDataSource] = []
        warnings: list[str] = []
        request_count = 0
        cache_hit_count = 0
        duration_ms = 0

        for target in targets:
            result = external_client.get_json(
                provider="uniprot",
                url="https://rest.uniprot.org/uniprotkb/search",
                query=target.symbol,
                params={
                    "query": UniProtConnector.build_query(target.symbol),
                    "fields": "accession,gene_names,protein_name",
                    "format": "json",
                    "size": 1,
                },
                license_note="UniProtKB human target normalization.",
            )
            data_sources.append(result.data_source)
            request_count += result.request_count
            cache_hit_count += 1 if result.from_cache else 0
            duration_ms += result.latency_ms
            if result.warning:
                warnings.append(result.warning)
            normalized = UniProtConnector.parse_normalized_target(target.symbol, result.payload)
            if normalized is None:
                warnings.append(f"UniProt normalization not found for target {target.symbol}.")
                normalized_targets.append(target)
                continue
            refs = [
                ref
                for ref in [
                    target.source_record_id,
                    f"UniProt:{normalized.accession}" if normalized.accession else None,
                ]
                if ref
            ]
            normalized_targets.append(
                TargetCandidate(
                    compound=target.compound,
                    symbol=normalized.symbol,
                    evidence_type=target.evidence_type,
                    score=target.score,
                    source=f"{target.source}+UniProt",
                    source_record_id=";".join(refs) or target.source_record_id,
                    retrieved_at=target.retrieved_at,
                )
            )

        return ConnectorResult(
            items=normalized_targets,
            data_sources=data_sources,
            warnings=warnings,
            external_request_count=request_count,
            cache_hit_count=cache_hit_count,
            duration_ms=duration_ms,
        )

    @staticmethod
    def parse_normalized_target(query: str, payload: Any | None) -> NormalizedTarget | None:
        if not isinstance(payload, dict):
            return None
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None
        first = UniProtConnector._select_best_record(query, results)
        if not isinstance(first, dict):
            return None
        accession = first.get("primaryAccession")
        symbol = UniProtConnector._extract_gene_symbol(first) or query
        protein_name = UniProtConnector._extract_protein_name(first)
        return NormalizedTarget(
            query=query,
            symbol=str(symbol),
            accession=str(accession) if accession else None,
            protein_name=protein_name,
        )

    @staticmethod
    def build_query(query: str) -> str:
        escaped = query.replace('"', '\\"')
        return f'((gene_exact:{escaped}) OR (protein_name:"{escaped}")) AND (organism_id:9606)'

    @staticmethod
    def _select_best_record(query: str, results: list[Any]) -> Any | None:
        expected = query.upper()
        for item in results:
            if not isinstance(item, dict):
                continue
            symbol = UniProtConnector._extract_gene_symbol(item)
            if symbol and symbol.upper() == expected:
                return item
        return results[0]

    @staticmethod
    def _extract_gene_symbol(record: dict[str, Any]) -> str | None:
        genes = record.get("genes")
        if not isinstance(genes, list) or not genes:
            return None
        first_gene = genes[0]
        if not isinstance(first_gene, dict):
            return None
        gene_name = first_gene.get("geneName")
        if not isinstance(gene_name, dict):
            return None
        value = gene_name.get("value")
        return str(value) if value else None

    @staticmethod
    def _extract_protein_name(record: dict[str, Any]) -> str | None:
        description = record.get("proteinDescription")
        if not isinstance(description, dict):
            return None
        recommended = description.get("recommendedName")
        if not isinstance(recommended, dict):
            return None
        full_name = recommended.get("fullName")
        if not isinstance(full_name, dict):
            return None
        value = full_name.get("value")
        return str(value) if value else None
