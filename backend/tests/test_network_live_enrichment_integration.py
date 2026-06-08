import json

from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.services.network_connectors import UniProtConnector
from app.services.network_providers import LiveNetworkProvider


def test_live_network_provider_builds_kegg_derived_enrichment(tmp_path):
    cache_repo = NetworkCacheRepository(tmp_path / "cache")
    compound_name = "Astragaloside IV"
    cache_repo.write_json(
        build_network_cache_key(
            provider="tcmsp",
            query="黄芪",
            params={"herb": "黄芪", "analysis_type": "herb"},
        ),
        {"compounds": [{"name": compound_name, "herb": "黄芪"}]},
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="pubchem",
            query=compound_name,
            params={"compound": compound_name},
        ),
        {"IdentifierList": {}},
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="chembl",
            query=compound_name,
            params={"compound": compound_name, "pubchem_cid": ""},
        ),
        {"activities": []},
    )
    prediction_path = tmp_path / "predictions.json"
    prediction_path.write_text(
        json.dumps(
            [
                {
                    "compound": compound_name,
                    "target_symbol": "IL6",
                    "score": 0.81,
                    "source": "SwissTargetPrediction",
                    "source_record_id": "swiss-1",
                },
                {
                    "compound": compound_name,
                    "target_symbol": "TNF",
                    "score": 0.72,
                    "source": "SwissTargetPrediction",
                    "source_record_id": "swiss-2",
                },
            ]
        ),
        encoding="utf-8",
    )
    cache_repo.write_json(
        build_network_cache_key(
            provider="kegg",
            query="IL6,TNF",
            params={"genes": "IL6,TNF"},
        ),
        {
            "link_text": "hsa:IL6\tpath:hsa04668\nhsa:TNF\tpath:hsa04668\n",
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

    result = LiveNetworkProvider(
        cache_repo=cache_repo,
        prediction_file=prediction_path,
        allow_tcmsp_scrape=False,
    ).build_result(
        task_id="network-live-enrichment",
        query="黄芪",
        analysis_type="herb",
        chains=[],
        enrichment=None,
    )

    assert result.enrichment is not None
    assert result.enrichment.analysis_type == "combined"
    assert result.enrichment.terms[0].term_id == "hsa04668"
    assert result.enrichment.terms[0].overlap_count == 2
    assert result.enrichment.terms[0].genes == ["IL6", "TNF"]
