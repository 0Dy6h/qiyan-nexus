"""Network pharmacology enrichment analysis service.

Provides GO/KEGG enrichment analysis using hypergeometric distribution
for statistical significance testing. Uses local JSON dictionaries to
simulate real enrichment databases.
"""

from datetime import UTC, datetime

from scipy.stats import hypergeom

from app.schemas.network import EnrichmentResult, EnrichmentTerm


def calculate_enrichment(
    input_genes: list[str], term_genes: list[str], background_size: int
) -> tuple[float, int]:
    """Calculate enrichment p-value using hypergeometric distribution.

    Args:
        input_genes: List of input gene symbols (e.g., targets from network chains)
        term_genes: List of genes associated with a GO term or KEGG pathway
        background_size: Total number of genes in the background set (default: 20000)

    Returns:
        Tuple of (p_value, overlap_count)
        - p_value: Probability of observing >= overlap_count by chance (P(X >= k))
        - overlap_count: Number of genes in both input_genes and term_genes
    """
    overlap = set(input_genes) & set(term_genes)
    overlap_count = len(overlap)

    M = background_size  # Total genes in background
    n = len(term_genes)  # Genes in this term
    N = len(input_genes)  # Input genes
    k = overlap_count  # Overlapping genes

    # P(X >= k) using survival function: sf(k-1) = 1 - cdf(k-1) = P(X >= k)
    p_value = hypergeom.sf(k - 1, M, n, N)
    return float(p_value), overlap_count


def run_go_enrichment(
    target_symbols: list[str],
    go_terms: list[dict],
    background_size: int = 20000,
    p_threshold: float = 0.05,
) -> list[EnrichmentTerm]:
    """Run GO enrichment analysis on target gene symbols.

    Args:
        target_symbols: List of target gene symbols from network analysis
        go_terms: List of GO term dictionaries (loaded from sample_go_terms.json)
        background_size: Total background gene count (default: 20000)
        p_threshold: P-value threshold for significance (default: 0.05)

    Returns:
        List of significant EnrichmentTerm objects, sorted by p-value (top 20)
    """
    results = []
    for term in go_terms:
        term_genes = term.get("genes", [])
        if not term_genes:
            continue

        p_value, overlap_count = calculate_enrichment(
            target_symbols, term_genes, background_size
        )

        # Filter: at least 2 overlapping genes and p-value < threshold
        if overlap_count >= 2 and p_value < p_threshold:
            # Bonferroni correction (simplified)
            adjusted_p_value = min(p_value * len(go_terms), 1.0)

            results.append(
                EnrichmentTerm(
                    term_id=term["id"],
                    term_name=term["name"],
                    term_name_zh=term.get("name_zh"),
                    category=term["category"],
                    gene_count=len(term_genes),
                    overlap_count=overlap_count,
                    p_value=p_value,
                    adjusted_p_value=adjusted_p_value,
                    genes=sorted(set(target_symbols) & set(term_genes)),
                )
            )

    # Sort by p-value (most significant first) and return top 20
    results.sort(key=lambda x: x.p_value)
    return results[:20]


def run_kegg_enrichment(
    target_symbols: list[str],
    kegg_pathways: list[dict],
    background_size: int = 20000,
    p_threshold: float = 0.05,
) -> list[EnrichmentTerm]:
    """Run KEGG pathway enrichment analysis on target gene symbols.

    Args:
        target_symbols: List of target gene symbols from network analysis
        kegg_pathways: List of KEGG pathway dictionaries (loaded from sample_kegg_pathways.json)
        background_size: Total background gene count (default: 20000)
        p_threshold: P-value threshold for significance (default: 0.05)

    Returns:
        List of significant EnrichmentTerm objects, sorted by p-value (top 20)
    """
    results = []
    for pathway in kegg_pathways:
        pathway_genes = pathway.get("genes", [])
        if not pathway_genes:
            continue

        p_value, overlap_count = calculate_enrichment(
            target_symbols, pathway_genes, background_size
        )

        # Filter: at least 2 overlapping genes and p-value < threshold
        if overlap_count >= 2 and p_value < p_threshold:
            # Bonferroni correction (simplified)
            adjusted_p_value = min(p_value * len(kegg_pathways), 1.0)

            results.append(
                EnrichmentTerm(
                    term_id=pathway["id"],
                    term_name=pathway["name"],
                    term_name_zh=pathway.get("name_zh"),
                    category="KEGG",
                    gene_count=len(pathway_genes),
                    overlap_count=overlap_count,
                    p_value=p_value,
                    adjusted_p_value=adjusted_p_value,
                    genes=sorted(set(target_symbols) & set(pathway_genes)),
                )
            )

    # Sort by p-value (most significant first) and return top 20
    results.sort(key=lambda x: x.p_value)
    return results[:20]


def build_enrichment_result(
    target_symbols: list[str],
    go_terms: list[dict],
    kegg_pathways: list[dict],
    background_size: int = 20000,
) -> EnrichmentResult | None:
    """Build combined GO + KEGG enrichment result.

    Args:
        target_symbols: List of target gene symbols from network chains
        go_terms: GO term dictionaries
        kegg_pathways: KEGG pathway dictionaries
        background_size: Total background gene count

    Returns:
        EnrichmentResult with combined GO and KEGG terms, or None if too few genes
    """
    if len(target_symbols) < 2:
        return None  # Need at least 2 genes for enrichment

    go_results = run_go_enrichment(target_symbols, go_terms, background_size)
    kegg_results = run_kegg_enrichment(target_symbols, kegg_pathways, background_size)

    # Combine and sort by p-value
    all_terms = go_results + kegg_results
    all_terms.sort(key=lambda x: x.p_value)

    return EnrichmentResult(
        analysis_type="combined",
        input_gene_count=len(target_symbols),
        background_gene_count=background_size,
        terms=all_terms[:20],  # Top 20 most significant
        timestamp=datetime.now(UTC).isoformat(),
    )
