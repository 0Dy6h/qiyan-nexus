"""Unit tests for build_network_report_markdown service function."""

from app.schemas.network import (
    EnrichmentResult,
    EnrichmentTerm,
    NetworkAnalysisResult,
    NetworkChain,
)
from app.services.network import build_network_report_markdown

DISCLAIMER = "非诊断结论、需结合临床。"

_SAMPLE_CHAIN = NetworkChain(
    herb="黄芩",
    compound="baicalin",
    target="IL6",
    pathway="inflammatory response",
    disease="AD",
    score=0.85,
    related_entity_ids=["herb-001", "compound-001"],
)

_SAMPLE_RESULT = NetworkAnalysisResult(
    task_id="test-task",
    query="黄芩",
    analysis_type="herb",
    chains=[_SAMPLE_CHAIN],
    disclaimer=DISCLAIMER,
)


def _make_result(**overrides: object) -> NetworkAnalysisResult:
    """Create a NetworkAnalysisResult with sensible defaults, allowing overrides."""
    defaults = {
        "task_id": "test-task",
        "query": "黄芩",
        "analysis_type": "herb",
        "chains": [_SAMPLE_CHAIN],
        "disclaimer": DISCLAIMER,
    }
    defaults.update(overrides)
    return NetworkAnalysisResult(**defaults)  # type: ignore[arg-type]


def test_build_report_includes_disclaimer():
    md = build_network_report_markdown(_SAMPLE_RESULT)
    assert DISCLAIMER in md


def test_build_report_chains_table():
    md = build_network_report_markdown(_SAMPLE_RESULT)
    # Header row
    assert (
        "| 序号 | 方剂 | 单味中药 | 成分 | 靶点 | 通路 | 疾病 | Mock 置信度 | 相关实体 ID |" in md
    )
    # Data row: herb=黄芩, compound=baicalin, target=IL6, score=85%
    assert "黄芩" in md
    assert "baicalin" in md
    assert "IL6" in md
    assert "85%" in md
    # formula is None → "无"
    assert "| 无 | 黄芩 |" in md or "无" in md


def test_build_report_empty_chains():
    result = _make_result(chains=[])
    md = build_network_report_markdown(result)
    assert "（当前报告没有可导出的 mock 链路。）" in md


def test_build_report_with_enrichment():
    enrichment = EnrichmentResult(
        analysis_type="combined",
        input_gene_count=5,
        background_gene_count=20000,
        terms=[
            EnrichmentTerm(
                term_id="GO:0006954",
                term_name="inflammatory response",
                term_name_zh="炎症反应",
                category="GO_BP",
                gene_count=200,
                overlap_count=3,
                p_value=1.23e-4,
                adjusted_p_value=2.46e-3,
                genes=["IL6", "TNF", "IL1B"],
            ),
        ],
        timestamp="2025-01-01T00:00:00+00:00",
    )
    result = _make_result(enrichment=enrichment)
    md = build_network_report_markdown(result)

    assert "## 富集分析结果" in md
    assert "输入基因数：5" in md
    assert "背景基因数：20000" in md
    assert "GO:0006954" in md
    assert "炎症反应" in md
    assert "3/200" in md
    assert "1.23e-04" in md
    assert "2.46e-03" in md
    assert "IL6, TNF, IL1B" in md
    assert "### 参数说明" in md


def test_build_report_without_enrichment():
    result = _make_result(enrichment=None)
    md = build_network_report_markdown(result)
    assert "## 富集分析结果" not in md


def test_build_report_enrichment_with_empty_terms_is_omitted():
    enrichment = EnrichmentResult(
        analysis_type="combined",
        input_gene_count=5,
        background_gene_count=20000,
        terms=[],
        timestamp="2025-01-01T00:00:00+00:00",
    )
    result = _make_result(enrichment=enrichment)
    md = build_network_report_markdown(result)
    assert "## 富集分析结果" not in md


def test_build_report_formula_type_label():
    result = _make_result(analysis_type="formula")
    md = build_network_report_markdown(result)
    assert "分析类型：复方" in md


def test_build_report_herb_type_label():
    result = _make_result(analysis_type="herb")
    md = build_network_report_markdown(result)
    assert "分析类型：单味中药" in md


def test_build_report_boundary_notes():
    md = build_network_report_markdown(_SAMPLE_RESULT)
    assert "## 边界说明" in md
    assert "不是正式网络药理学计算。" in md
    assert "富集分析基于本地 JSON 字典（mock），不代表真实 KEGG REST API 或 STRING 数据库。" in md
    assert "不构成诊断或治疗建议" in md


def test_build_report_network_graph_placeholder():
    md = build_network_report_markdown(_SAMPLE_RESULT)
    assert "## 网络图" in md
    assert "![成分-靶点-通路网络图](placeholder-network-graph.png)" in md
    assert "*注：图片占位符，实际图片生成功能待后续实现*" in md


def test_build_report_custom_exported_at():
    md = build_network_report_markdown(_SAMPLE_RESULT, exported_at="2025-06-01T12:00:00+00:00")
    assert "2025-06-01T12:00:00+00:00" in md


def test_build_report_pipe_escaping():
    chain = NetworkChain(
        herb="黄芩|苦参",
        compound="baicalin",
        target="IL6",
        pathway="inflammatory|response",
        disease="AD",
        score=0.85,
        related_entity_ids=[],
    )
    result = _make_result(chains=[chain])
    md = build_network_report_markdown(result)
    # Pipes inside cells should be escaped
    assert "黄芩\\|苦参" in md
    assert "inflammatory\\|response" in md


def test_build_report_formula_chain_shows_formula():
    chain = NetworkChain(
        herb="黄芩",
        formula="消风散",
        compound="baicalin",
        target="IL6",
        pathway="inflammatory response",
        disease="AD",
        score=0.85,
        related_entity_ids=["herb-001"],
    )
    result = _make_result(chains=[chain])
    md = build_network_report_markdown(result)
    assert "消风散" in md
