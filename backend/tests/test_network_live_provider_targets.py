import json

import httpx

from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.services.network_connectors import UniProtConnector
from app.services.network_external_client import NetworkExternalClient
from app.services.network_providers import LiveNetworkProvider


def test_live_network_provider_builds_known_and_predicted_target_chains(tmp_path):
    cache_repo = NetworkCacheRepository(tmp_path / "cache")
    compound_name = "Astragaloside IV"

    cache_repo.write_json(
        build_network_cache_key(
            provider="tcmsp",
            query="黄芪",
            params={"herb": "黄芪", "analysis_type": "herb"},
        ),
        {
            "compounds": [
                {
                    "name": compound_name,
                    "herb": "黄芪",
                    "source_record_id": "tcmsp-huangqi-astragaloside-iv",
                    "properties": {"OB": "36.7"},
                }
            ]
        },
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="pubchem",
            query=compound_name,
            params={"compound": compound_name},
        ),
        {"IdentifierList": {"CID": [13943297]}},
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="chembl",
            query=compound_name,
            params={"compound": compound_name, "pubchem_cid": "13943297"},
        ),
        {
            "activities": [
                {
                    "target_pref_name": "IL6",
                    "target_organism": "Homo sapiens",
                    "pchembl_value": "8.0",
                    "assay_chembl_id": "CHEMBLASSAY-HQ-1",
                }
            ]
        },
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="kegg",
            query="IL6,TNF",
            params={"genes": "IL6,TNF"},
        ),
        {
            "link_text": "hsa:3569\tpath:hsa04668\nhsa:7124\tpath:hsa04668\n",
            "list_text": "path:hsa04668\tTNF signaling pathway - Homo sapiens (human)\n",
        },
    )
    for symbol, accession, name in [
        ("IL6", "P05231", "Interleukin-6"),
        ("TNF", "P01375", "Tumor necrosis factor"),
    ]:
        cache_repo.write_json(
            build_network_cache_key(
                provider="uniprot",
                query=symbol,
                params={
                    "query": UniProtConnector.build_query(symbol),
                    "fields": "accession,gene_names,protein_name",
                    "format": "json",
                    "size": 1,
                },
            ),
            {
                "results": [
                    {
                        "primaryAccession": accession,
                        "genes": [{"geneName": {"value": symbol}}],
                        "proteinDescription": {"recommendedName": {"fullName": {"value": name}}},
                    }
                ]
            },
        )
    cache_repo.write_json(
        build_network_cache_key(
            provider="string",
            query="IL6,TNF",
            params={"identifiers": "IL6\rTNF", "species": 9606, "required_score": 400},
        ),
        "preferredName_A\tpreferredName_B\tscore\nIL6\tTNF\t0.982\n",
    )
    prediction_path = tmp_path / "predictions.json"
    prediction_path.write_text(
        json.dumps(
            [
                {
                    "compound": compound_name,
                    "target_symbol": "TNF",
                    "score": 0.72,
                    "source": "SwissTargetPrediction",
                    "source_record_id": "swiss-hq-1",
                    "retrieved_at": "2026-06-08T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )

    provider = LiveNetworkProvider(
        cache_repo=cache_repo,
        prediction_file=prediction_path,
        allow_tcmsp_scrape=False,
    )

    result = provider.build_result(
        task_id="network-live-test",
        query="黄芪",
        analysis_type="herb",
        chains=[],
        enrichment=None,
    )

    assert result.data_mode == "live"
    assert {chain.target for chain in result.chains} == {"IL6", "TNF"}
    by_target = {chain.target: chain for chain in result.chains}
    assert by_target["IL6"].target_evidence_type == "known_activity"
    assert by_target["TNF"].target_evidence_type == "predicted"
    assert all(chain.pathway == "TNF signaling pathway" for chain in result.chains)
    assert {source.name for source in result.data_sources} >= {
        "TCMSP scraped/cache",
        "pubchem",
        "chembl",
        "SwissTargetPrediction",
        "kegg",
    }
    assert result.pipeline_steps[-1].name == "live-result-assembly"


def test_live_network_provider_fetches_external_sources_when_cache_is_missing(tmp_path):
    cache_repo = NetworkCacheRepository(tmp_path / "cache")
    compound_name = "Astragaloside IV"
    requested_paths: list[str] = []

    cache_repo.write_json(
        build_network_cache_key(
            provider="tcmsp",
            query="黄芪",
            params={"herb": "黄芪", "analysis_type": "herb"},
        ),
        {"compounds": [{"name": compound_name, "herb": "黄芪"}]},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        path = request.url.path
        if path.endswith("/compound/name/Astragaloside%20IV/cids/JSON"):
            return httpx.Response(200, json={"IdentifierList": {"CID": [13943297]}})
        if path.endswith("/chembl/api/data/molecule.json"):
            return httpx.Response(
                200,
                json={"molecules": [{"molecule_chembl_id": "CHEMBL-AS-IV"}]},
            )
        if path.endswith("/chembl/api/data/activity.json"):
            return httpx.Response(
                200,
                json={
                    "activities": [
                        {
                            "target_pref_name": "Interleukin-6",
                            "target_organism": "Homo sapiens",
                            "pchembl_value": "8.0",
                            "assay_chembl_id": "CHEMBLASSAY-HQ-1",
                        }
                    ]
                },
            )
        if path.endswith("/uniprotkb/search"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "primaryAccession": "P05231",
                            "genes": [{"geneName": {"value": "IL6"}}],
                            "proteinDescription": {
                                "recommendedName": {"fullName": {"value": "Interleukin-6"}}
                            },
                        }
                    ]
                },
            )
        if path.endswith("/api/tsv/network"):
            return httpx.Response(
                200,
                text="preferredName_A\tpreferredName_B\tscore\nIL6\tTNF\t0.982\n",
            )
        if path.endswith("/find/hsa/IL6"):
            return httpx.Response(200, text="hsa:3569\tinterleukin 6; IL6\n")
        if path.endswith("/link/pathway/hsa:3569"):
            return httpx.Response(200, text="hsa:3569\tpath:hsa04668\n")
        if path.endswith("/list/path:hsa04668"):
            return httpx.Response(
                200,
                text="path:hsa04668\tTNF signaling pathway - Homo sapiens (human)\n",
            )
        return httpx.Response(404, json={"unexpected": str(request.url)})

    external_client = NetworkExternalClient(
        cache_repo=cache_repo,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limit_per_second=0,
    )

    result = LiveNetworkProvider(
        cache_repo=cache_repo,
        prediction_file=tmp_path / "missing-predictions.json",
        allow_tcmsp_scrape=False,
        external_client=external_client,
    ).build_result(
        task_id="network-live-http-test",
        query="黄芪",
        analysis_type="herb",
        chains=[],
        enrichment=None,
    )

    assert [chain.target for chain in result.chains] == ["IL6"]
    assert result.chains[0].target_evidence_type == "known_activity"
    assert result.chains[0].pathway == "TNF signaling pathway"
    assert result.ppi_edges[0].source == "IL6"
    assert result.ppi_edges[0].target == "TNF"
    assert {source.name for source in result.data_sources} >= {
        "pubchem",
        "chembl",
        "uniprot",
        "string",
        "kegg",
    }
    assert any(step.name == "string-ppi-resolution" for step in result.pipeline_steps)
    assert any(step.name == "uniprot-target-normalization" for step in result.pipeline_steps)
    assert any("/compound/name/" in path for path in requested_paths)
