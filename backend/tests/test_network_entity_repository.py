from app.repositories.network_entities import NetworkEntityRepository


def test_list_herbs_returns_seed_records():
    repo = NetworkEntityRepository()
    herbs = repo.list_herbs()
    ids = {herb.id for herb in herbs}
    assert {
        "herb-jingjie",
        "herb-fangfeng",
        "herb-niubangzi",
        "herb-baixianpi",
        "herb-huangqi",
    } <= ids


def test_list_formulas_returns_seed_records():
    repo = NetworkEntityRepository()
    formulas = repo.list_formulas()
    by_id = {f.id: f for f in formulas}
    assert "formula-xiaofengsan" in by_id
    assert "herb-jingjie" in by_id["formula-xiaofengsan"].herb_ids


def test_list_compounds_resolves_herb_links():
    repo = NetworkEntityRepository()
    compounds = repo.list_compounds()
    by_id = {c.id: c for c in compounds}
    assert "herb-huangqi" in by_id["compound-astragaloside-iv"].herb_ids


def test_list_targets_and_pathways_carry_disease_and_target_links():
    repo = NetworkEntityRepository()
    targets = {t.id: t for t in repo.list_targets()}
    pathways = {p.id: p for p in repo.list_pathways()}
    assert "disease-ad" in targets["target-il6"].disease_ids
    assert "target-il6" in pathways["pathway-pi3k-akt"].target_ids


def test_list_chains_returns_curated_seed_edges():
    repo = NetworkEntityRepository()
    chains = repo.list_chains()
    assert len(chains) >= 5
    for edge in chains:
        assert edge.compound_id
        assert edge.target_id
        assert edge.pathway_id
        assert edge.disease == "Atopic dermatitis"
        assert 0 <= edge.score <= 1


def test_find_formula_by_query_matches_name_and_pinyin():
    repo = NetworkEntityRepository()
    assert repo.find_formula_by_query("消风散") is not None
    assert repo.find_formula_by_query("xiaofengsan") is not None
    assert repo.find_formula_by_query("不存在的方") is None


def test_find_herb_by_query_matches_name_and_pinyin():
    repo = NetworkEntityRepository()
    assert repo.find_herb_by_query("黄芪") is not None
    assert repo.find_herb_by_query("HUANGQI") is not None
    assert repo.find_herb_by_query("not-an-herb") is None
