from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key


def test_network_cache_key_is_stable_for_sorted_params():
    first = build_network_cache_key(
        provider="pubchem",
        query="黄芪",
        params={"b": 2, "a": 1},
    )
    second = build_network_cache_key(
        provider="pubchem",
        query="黄芪",
        params={"a": 1, "b": 2},
    )

    assert first == second
    assert first.startswith("pubchem-v1-")


def test_network_cache_key_changes_when_query_changes():
    first = build_network_cache_key(provider="pubchem", query="黄芪", params={"a": 1})
    second = build_network_cache_key(provider="pubchem", query="黄芩", params={"a": 1})

    assert first != second


def test_network_cache_repository_round_trips_json(tmp_path):
    repo = NetworkCacheRepository(tmp_path)
    cache_key = build_network_cache_key(
        provider="chembl",
        query="baicalin",
        params={"limit": 10},
    )

    assert repo.read_json(cache_key) is None

    payload = {"records": [{"target": "IL6"}]}
    repo.write_json(cache_key, payload)

    assert repo.read_json(cache_key) == payload
    assert (tmp_path / f"{cache_key}.json").exists()


def test_network_cache_repository_rejects_path_traversal(tmp_path):
    repo = NetworkCacheRepository(tmp_path)

    assert repo.read_json("../escape") is None
