import httpx

from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.services.network_connectors import TcmspConnector
from app.services.network_external_client import NetworkExternalClient


def test_tcmsp_connector_parses_compounds_from_fixture_html():
    html = """
    <table>
      <tr><th>Molecule Name</th><th>OB</th><th>DL</th></tr>
      <tr><td>Astragaloside IV</td><td>36.7</td><td>0.15</td></tr>
      <tr><td>Formononetin</td><td>69.7</td><td>0.21</td></tr>
    </table>
    """

    compounds = TcmspConnector.parse_compounds_from_html(html, herb_name="黄芪")

    assert [compound.name for compound in compounds] == ["Astragaloside IV", "Formononetin"]
    assert compounds[0].herb == "黄芪"
    assert compounds[0].properties["OB"] == "36.7"
    assert compounds[0].properties["DL"] == "0.15"


def test_tcmsp_connector_reads_cached_compounds_when_scraping_is_disabled(tmp_path):
    cache_repo = NetworkCacheRepository(tmp_path)
    cache_key = build_network_cache_key(
        provider="tcmsp",
        query="黄芪",
        params={"herb": "黄芪", "analysis_type": "herb"},
    )
    cache_repo.write_json(
        cache_key,
        {
            "compounds": [
                {
                    "name": "Astragaloside IV",
                    "herb": "黄芪",
                    "source_record_id": "tcmsp-huangqi-astragaloside-iv",
                    "properties": {"OB": "36.7"},
                }
            ]
        },
    )
    connector = TcmspConnector(cache_repo=cache_repo, allow_scrape=False)

    result = connector.resolve_compounds(query="黄芪", analysis_type="herb")

    assert len(result.items) == 1
    assert result.items[0].name == "Astragaloside IV"
    assert result.data_sources[0].from_cache is True
    assert result.warnings == []


def test_tcmsp_connector_returns_warning_without_cache_or_scrape(tmp_path):
    connector = TcmspConnector(cache_repo=NetworkCacheRepository(tmp_path), allow_scrape=False)

    result = connector.resolve_compounds(query="黄芪", analysis_type="herb")

    assert result.items == []
    assert result.warnings == ["TCMSP scraping is disabled and no cached compounds were found."]


def test_tcmsp_connector_fetches_html_with_external_client_when_scraping_is_enabled(tmp_path):
    request_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_urls.append(str(request.url))
        assert request.url.params["qr"] == "黄芪"
        assert request.url.params["qsr"] == "herb_cn_name"
        return httpx.Response(
            200,
            text="""
            <table>
              <tr><th>Molecule Name</th><th>OB</th></tr>
              <tr><td>Astragaloside IV</td><td>36.7</td></tr>
            </table>
            """,
        )

    cache_repo = NetworkCacheRepository(tmp_path)
    external_client = NetworkExternalClient(
        cache_repo=cache_repo,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limit_per_second=0,
    )
    connector = TcmspConnector(
        cache_repo=cache_repo,
        allow_scrape=True,
        external_client=external_client,
    )

    result = connector.resolve_compounds(query="黄芪", analysis_type="herb")

    assert [compound.name for compound in result.items] == ["Astragaloside IV"]
    assert result.data_sources[0].name == "TCMSP scraped/cache"
    assert result.data_sources[0].from_cache is False
    assert result.external_request_count == 1
    assert result.cache_hit_count == 0
    assert any("tcmspsearch.php" in url for url in request_urls)
