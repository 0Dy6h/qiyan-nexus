from app.services.network import _build_chains_from_seed


def test_formula_query_expands_to_constituent_herbs():
    chains = _build_chains_from_seed("消风散", "formula")

    assert len(chains) >= 1
    assert all(chain.formula == "消风散" for chain in chains)
    # 消风散 = 荆芥 + 防风 + 牛蒡子 in seed; chains must come from this set.
    constituent_herbs = {"荆芥", "防风", "牛蒡子"}
    assert {chain.herb for chain in chains} <= constituent_herbs
    # Chains are scored 0-1 and sorted desc; top should match the curated seed.
    scores = [chain.score for chain in chains]
    assert scores == sorted(scores, reverse=True)
    assert chains[0].disease == "Atopic dermatitis"


def test_herb_query_restricts_chains_to_that_herb_only():
    chains = _build_chains_from_seed("黄芪", "herb")

    assert len(chains) >= 1
    assert all(chain.herb == "黄芪" for chain in chains)
    assert all(chain.formula is None for chain in chains)


def test_unknown_query_returns_echo_fallback_chains():
    chains = _build_chains_from_seed("不存在的方剂", "formula")

    assert len(chains) >= 1
    # All fallback chains echo the query as herb/formula label.
    assert all(chain.herb == "不存在的方剂" for chain in chains)
    assert all(chain.formula == "不存在的方剂" for chain in chains)


def test_chain_count_capped_to_max_five():
    chains = _build_chains_from_seed("消风散", "formula")
    assert len(chains) <= 5


def test_network_chains_include_entity_ids_for_frontend_chips():
    chains = _build_chains_from_seed("消风散", "formula")

    assert len(chains) >= 1
    first = chains[0]
    assert "herb-" in first.related_entity_ids[0]
    assert first.related_entity_ids[1].startswith("compound-")
    assert first.related_entity_ids[2].startswith("target-")
    assert first.related_entity_ids[3].startswith("pathway-")
