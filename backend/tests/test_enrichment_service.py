"""Tests for enrichment analysis service."""

import pytest

from app.services.enrichment import (
    build_enrichment_result,
    calculate_enrichment,
    run_go_enrichment,
    run_kegg_enrichment,
)


def test_calculate_enrichment_returns_low_p_value_for_significant_overlap():
    """Significant overlap produces low p-value."""
    input_genes = ["IL6", "TNF", "IL1B", "CXCL8"]
    term_genes = ["IL6", "TNF", "IL1B", "IL10", "IL4", "IFNG", "CD4", "CD8A"]
    p_value, overlap = calculate_enrichment(input_genes, term_genes, 20000)

    assert overlap == 3
    assert p_value < 0.05  # Significant


def test_calculate_enrichment_returns_high_p_value_for_random_overlap():
    """Random overlap produces high p-value."""
    input_genes = ["IL6", "TNF"]
    term_genes = ["GENE1", "GENE2", "GENE3", "GENE4", "GENE5"]
    p_value, overlap = calculate_enrichment(input_genes, term_genes, 20000)

    assert overlap == 0
    assert p_value > 0.05  # Not significant


def test_calculate_enrichment_handles_perfect_overlap():
    """Perfect overlap produces very low p-value."""
    input_genes = ["IL6", "TNF", "IL1B"]
    term_genes = ["IL6", "TNF", "IL1B"]
    p_value, overlap = calculate_enrichment(input_genes, term_genes, 20000)

    assert overlap == 3
    assert p_value < 0.001  # Highly significant


def test_run_go_enrichment_filters_by_p_threshold():
    """GO enrichment filters terms by p-value threshold."""
    targets = ["IL6", "TNF", "IL1B", "CXCL8", "IL10"]
    go_terms = [
        {
            "id": "GO:0006954",
            "name": "inflammatory response",
            "name_zh": "炎症反应",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL1B", "CXCL8", "IL10", "CCL2", "PTGS2"],
        },
        {
            "id": "GO:9999999",
            "name": "unrelated process",
            "category": "biological_process",
            "genes": ["GENE1", "GENE2", "GENE3"],
        },
    ]

    results = run_go_enrichment(targets, go_terms, p_threshold=0.05)

    # Should only include inflammatory response (high overlap)
    assert len(results) >= 1
    assert all(term.p_value < 0.05 for term in results)
    assert results[0].term_id == "GO:0006954"
    assert results[0].overlap_count == 5


def test_run_go_enrichment_filters_by_minimum_overlap():
    """GO enrichment requires at least 2 overlapping genes."""
    targets = ["IL6"]
    go_terms = [
        {
            "id": "GO:0006954",
            "name": "inflammatory response",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL1B"],
        }
    ]

    results = run_go_enrichment(targets, go_terms)

    # Should be empty because overlap_count = 1 < 2
    assert len(results) == 0


def test_run_go_enrichment_sorts_by_p_value():
    """GO enrichment results are sorted by p-value (ascending)."""
    targets = ["IL6", "TNF", "IL1B", "CXCL8", "IL10", "CCL2"]
    go_terms = [
        {
            "id": "GO:0006954",
            "name": "inflammatory response",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL1B", "CXCL8", "IL10", "CCL2", "PTGS2", "ICAM1"],
        },
        {
            "id": "GO:0006955",
            "name": "immune response",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL10"],
        },
    ]

    results = run_go_enrichment(targets, go_terms)

    assert len(results) >= 2
    # First result should have lower p-value than second
    assert results[0].p_value <= results[1].p_value


def test_run_go_enrichment_applies_bonferroni_correction():
    """GO enrichment applies Bonferroni correction to p-values."""
    targets = ["IL6", "TNF", "IL1B"]
    go_terms = [
        {
            "id": "GO:0006954",
            "name": "inflammatory response",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL1B", "CXCL8"],
        }
    ]

    results = run_go_enrichment(targets, go_terms)

    assert len(results) >= 1
    # Adjusted p-value should be p_value * number_of_terms
    assert results[0].adjusted_p_value == pytest.approx(
        results[0].p_value * len(go_terms), abs=0.01
    )


def test_run_kegg_enrichment_returns_pathway_results():
    """KEGG enrichment returns pathway enrichment results."""
    targets = ["IL6", "TNF", "NFKB1", "MAPK1", "JUN"]
    kegg_pathways = [
        {
            "id": "hsa04668",
            "name": "TNF signaling pathway",
            "name_zh": "TNF 信号通路",
            "genes": ["TNF", "NFKB1", "JUN", "MAPK1", "MAPK14", "IL6"],
        }
    ]

    results = run_kegg_enrichment(targets, kegg_pathways)

    assert len(results) >= 1
    assert results[0].term_id == "hsa04668"
    assert results[0].category == "KEGG"
    assert results[0].overlap_count == 5
    assert "TNF" in results[0].genes
    assert "IL6" in results[0].genes


def test_build_enrichment_result_returns_none_for_too_few_genes():
    """Enrichment requires at least 2 genes."""
    result = build_enrichment_result(["IL6"], [], [])
    assert result is None


def test_build_enrichment_result_combines_go_and_kegg():
    """Enrichment result combines GO and KEGG terms."""
    targets = ["IL6", "TNF", "IL1B", "NFKB1"]
    go_terms = [
        {
            "id": "GO:0006954",
            "name": "inflammatory response",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL1B", "CXCL8"],
        }
    ]
    kegg_pathways = [
        {
            "id": "hsa04668",
            "name": "TNF signaling pathway",
            "genes": ["TNF", "NFKB1", "JUN", "IL6"],
        }
    ]

    result = build_enrichment_result(targets, go_terms, kegg_pathways)

    assert result is not None
    assert result.input_gene_count == 4
    assert result.background_gene_count == 20000
    assert len(result.terms) >= 2

    # Should contain both GO and KEGG terms
    term_ids = [term.term_id for term in result.terms]
    assert "GO:0006954" in term_ids
    assert "hsa04668" in term_ids


def test_build_enrichment_result_limits_to_top_20():
    """Enrichment result returns at most 20 terms."""
    targets = ["IL6", "TNF", "IL1B", "CXCL8", "IL10", "NFKB1", "MAPK1", "JUN"]

    # Create 30 GO terms with varying overlap
    go_terms = []
    for i in range(30):
        go_terms.append(
            {
                "id": f"GO:{i:07d}",
                "name": f"process {i}",
                "category": "biological_process",
                "genes": targets[:3] + [f"GENE{j}" for j in range(5)],
            }
        )

    result = build_enrichment_result(targets, go_terms, [])

    assert result is not None
    assert len(result.terms) <= 20


def test_enrichment_genes_are_sorted():
    """Enrichment term genes are sorted alphabetically."""
    targets = ["TNF", "IL6", "IL1B"]
    go_terms = [
        {
            "id": "GO:0006954",
            "name": "inflammatory response",
            "category": "biological_process",
            "genes": ["IL6", "TNF", "IL1B", "CXCL8"],
        }
    ]

    results = run_go_enrichment(targets, go_terms)

    assert len(results) >= 1
    # Genes should be sorted
    assert results[0].genes == ["IL1B", "IL6", "TNF"]
