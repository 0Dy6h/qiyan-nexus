import httpx

from app.repositories.network_cache import NetworkCacheRepository
from app.services.network_external_client import NetworkExternalClient


def test_network_external_client_caches_successful_json_response(tmp_path):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.url.params["q"] == "baicalin"
        return httpx.Response(200, json={"PC_Compounds": [{"id": {"id": {"cid": 5281605}}}]})

    client = NetworkExternalClient(
        cache_repo=NetworkCacheRepository(tmp_path),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limit_per_second=0,
    )

    first = client.get_json(
        provider="pubchem",
        url="https://pubchem.example.test/rest/pug/compound/name/baicalin/JSON",
        query="baicalin",
        params={"q": "baicalin"},
        license_note="PubChem PUG-REST test fixture",
    )
    second = client.get_json(
        provider="pubchem",
        url="https://pubchem.example.test/rest/pug/compound/name/baicalin/JSON",
        query="baicalin",
        params={"q": "baicalin"},
        license_note="PubChem PUG-REST test fixture",
    )

    assert request_count == 1
    assert first.payload == second.payload
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.data_source.from_cache is True
    assert second.data_source.cache_key == first.data_source.cache_key


def test_network_external_client_retries_once_then_returns_warning(tmp_path):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(503, json={"detail": "temporarily unavailable"})

    client = NetworkExternalClient(
        cache_repo=NetworkCacheRepository(tmp_path),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limit_per_second=0,
    )

    result = client.get_json(
        provider="kegg",
        url="https://kegg.example.test/link/pathway/hsa:3569",
        query="IL6",
        params={},
        license_note="KEGG REST test fixture",
    )

    assert request_count == 2
    assert result.payload is None
    assert result.warning is not None
    assert "kegg request failed" in result.warning
    assert result.data_source.name == "kegg"


def test_network_external_client_caches_successful_text_response(tmp_path):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.url.params["identifiers"] == "IL6\rTNF"
        return httpx.Response(
            200,
            text="preferredName_A\tpreferredName_B\tscore\nIL6\tTNF\t0.982\n",
        )

    client = NetworkExternalClient(
        cache_repo=NetworkCacheRepository(tmp_path),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limit_per_second=0,
    )

    first = client.get_text(
        provider="string",
        url="https://string-db.org/api/tsv/network",
        query="IL6,TNF",
        params={"identifiers": "IL6\rTNF", "species": 9606},
        license_note="STRING API test fixture",
    )
    second = client.get_text(
        provider="string",
        url="https://string-db.org/api/tsv/network",
        query="IL6,TNF",
        params={"identifiers": "IL6\rTNF", "species": 9606},
        license_note="STRING API test fixture",
    )

    assert request_count == 1
    assert first.payload == second.payload
    assert first.payload.startswith("preferredName_A")
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.data_source.cache_key == first.data_source.cache_key
