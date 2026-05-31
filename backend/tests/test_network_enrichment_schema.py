"""Tests for network enrichment schema definitions."""

from app.schemas.network import EnrichmentResult, EnrichmentTerm, NetworkAnalysisResult


def test_enrichment_term_schema_validates():
    """EnrichmentTerm schema accepts valid fields."""
    term = EnrichmentTerm(
        term_id="GO:0006954",
        term_name="inflammatory response",
        term_name_zh="炎症反应",
        category="GO_BP",
        gene_count=450,
        overlap_count=12,
        p_value=0.0001,
        adjusted_p_value=0.005,
        genes=["IL6", "TNF", "IL1B"],
    )
    assert term.term_id == "GO:0006954"
    assert term.overlap_count == 12
    assert term.p_value == 0.0001
    assert len(term.genes) == 3


def test_enrichment_term_optional_zh_name():
    """EnrichmentTerm allows None for term_name_zh."""
    term = EnrichmentTerm(
        term_id="GO:0006954",
        term_name="inflammatory response",
        term_name_zh=None,
        category="GO_BP",
        gene_count=450,
        overlap_count=12,
        p_value=0.0001,
        adjusted_p_value=0.005,
        genes=["IL6", "TNF"],
    )
    assert term.term_name_zh is None


def test_enrichment_result_schema_validates():
    """EnrichmentResult schema accepts valid nested structure."""
    result = EnrichmentResult(
        analysis_type="combined",
        input_gene_count=10,
        background_gene_count=20000,
        terms=[
            EnrichmentTerm(
                term_id="GO:0006954",
                term_name="inflammatory response",
                term_name_zh="炎症反应",
                category="GO_BP",
                gene_count=450,
                overlap_count=5,
                p_value=0.0001,
                adjusted_p_value=0.005,
                genes=["IL6", "TNF"],
            )
        ],
        timestamp="2026-06-01T10:00:00Z",
    )
    assert result.input_gene_count == 10
    assert result.background_gene_count == 20000
    assert len(result.terms) == 1
    assert result.terms[0].term_id == "GO:0006954"


def test_network_analysis_result_enrichment_optional():
    """NetworkAnalysisResult allows enrichment to be None (backward compatible)."""
    result = NetworkAnalysisResult(
        task_id="task-001",
        query="黄芩",
        analysis_type="herb",
        chains=[],
        enrichment=None,
        disclaimer="非诊断结论、需结合临床。",
    )
    assert result.enrichment is None
    assert result.task_id == "task-001"


def test_network_analysis_result_with_enrichment():
    """NetworkAnalysisResult accepts enrichment field."""
    enrichment = EnrichmentResult(
        analysis_type="combined",
        input_gene_count=5,
        background_gene_count=20000,
        terms=[],
        timestamp="2026-06-01T10:00:00Z",
    )
    result = NetworkAnalysisResult(
        task_id="task-001",
        query="黄芩",
        analysis_type="herb",
        chains=[],
        enrichment=enrichment,
        disclaimer="非诊断结论、需结合临床。",
    )
    assert result.enrichment is not None
    assert result.enrichment.input_gene_count == 5
