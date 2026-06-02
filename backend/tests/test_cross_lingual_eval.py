"""Tests for cross-lingual retrieval eval harness (Slice 1: RED baseline)."""

from pathlib import Path

import pytest

from app.schemas.eval import (
    CrossLingualRetrievalItem,
    CrossLingualRetrievalReport,
)
from app.services.retrieval_eval import (
    _classify_id,
    _compute_item_metrics,
    _identify_question_language,
    run_cross_lingual_retrieval_eval,
)

# ---------------------------------------------------------------------------
# Unit tests: _identify_question_language
# ---------------------------------------------------------------------------


def test_identify_question_language_zh():
    """纯中文问题应识别为 zh"""
    assert _identify_question_language("特应性皮炎和肠-脑-皮肤轴之间有什么关系？") == "zh"


def test_identify_question_language_en():
    """纯英文问题应识别为 en"""
    assert (
        _identify_question_language("What is the relationship between AD and gut-brain-skin axis?")
        == "en"
    )


def test_identify_question_language_mixed():
    """中英混合问题应识别为 zh（含 CJK 字符即视为中文）"""
    assert _identify_question_language("IL-31 在特应性皮炎中的作用") == "zh"


def test_identify_question_language_pure_numbers():
    """纯数字/符号应识别为 en"""
    assert _identify_question_language("12345") == "en"


# ---------------------------------------------------------------------------
# Unit tests: _classify_id
# ---------------------------------------------------------------------------


def test_classify_id_cn():
    assert _classify_id("cn-ad-gbs-001") == "cn"


def test_classify_id_pubmed():
    assert _classify_id("pmid-40100002") == "pubmed"


def test_classify_id_unknown():
    assert _classify_id("other-123") == "unknown"


# ---------------------------------------------------------------------------
# Unit tests: _compute_item_metrics
# ---------------------------------------------------------------------------


def test_compute_item_metrics_monolingual():
    """中文问题，仅 cn-* 期望，全命中"""
    item = _compute_item_metrics(
        id="test-001",
        question="测试问题",
        source_preference="cn_literature",
        question_language="zh",
        expected_cn_ids=["cn-a", "cn-b"],
        expected_pubmed_ids=[],
        top_k=5,
        retrieved_ids=["cn-a", "cn-b", "cn-c", "pmid-x", "pmid-y"],
    )
    assert item.monolingual_recall == 1.0  # 2/2
    assert item.cross_lingual_recall == 0.0  # 0 个英文期望
    assert item.cn_hit_count == 3
    assert item.pubmed_hit_count == 2


def test_compute_item_metrics_cross_lingual():
    """中文问题，期望同时有 cn 和 pmid，但只命中 cn"""
    item = _compute_item_metrics(
        id="test-002",
        question="关于肠脑皮肤轴的研究",
        source_preference="all",
        question_language="zh",
        expected_cn_ids=["cn-a"],
        expected_pubmed_ids=["pmid-x", "pmid-y"],
        top_k=5,
        retrieved_ids=["cn-a", "cn-b", "cn-c", "cn-d", "cn-e"],
    )
    assert item.monolingual_recall == 1.0
    assert item.cross_lingual_recall == 0.0  # 应该暴露跨语言弱点
    assert item.cn_hit_count == 5
    assert item.pubmed_hit_count == 0


def test_compute_item_metrics_mrr():
    """MRR = 1/rank of first expected hit"""
    item = _compute_item_metrics(
        id="test-mrr",
        question="test",
        source_preference="all",
        question_language="en",
        expected_cn_ids=[],
        expected_pubmed_ids=["pmid-x"],
        top_k=5,
        retrieved_ids=["pmid-a", "pmid-b", "pmid-x", "pmid-c", "pmid-d"],
    )
    assert item.mean_reciprocal_rank == round(1.0 / 3, 4)  # rank 3


def test_compute_item_metrics_mrr_first_position():
    """MRR = 1.0 when expected hit is at rank 1"""
    item = _compute_item_metrics(
        id="test-mrr-first",
        question="test",
        source_preference="all",
        question_language="zh",
        expected_cn_ids=["cn-a"],
        expected_pubmed_ids=[],
        top_k=5,
        retrieved_ids=["cn-a", "cn-b", "cn-c"],
    )
    assert item.mean_reciprocal_rank == 1.0


def test_compute_item_metrics_no_expected_ids():
    """没有期望 ID 时不除零"""
    item = _compute_item_metrics(
        id="test-no-expected",
        question="test",
        source_preference="all",
        question_language="zh",
        expected_cn_ids=[],
        expected_pubmed_ids=[],
        top_k=5,
        retrieved_ids=["cn-a"],
    )
    assert item.monolingual_recall == 0.0
    assert item.cross_lingual_recall == 0.0


def test_compute_item_metrics_precision_at_k():
    """precision_at_k = expected hits / top_k"""
    item = _compute_item_metrics(
        id="test-prec",
        question="test",
        source_preference="all",
        question_language="zh",
        expected_cn_ids=["cn-a", "cn-b"],
        expected_pubmed_ids=["pmid-x"],
        top_k=10,
        retrieved_ids=[
            "cn-a",
            "cn-c",
            "pmid-y",
            "cn-d",
            "cn-e",
            "pmid-z",
            "cn-f",
            "cn-g",
            "pmid-w",
            "cn-h",
        ],
    )
    # cn-a is expected, cn-b not in retrieved, pmid-x not in retrieved
    # expected hits = 1 (cn-a), top_k = 10
    assert item.precision_at_k == 1.0 / 10


def test_compute_item_metrics_language_diversity():
    """language_diversity = min(cn_hits, pubmed_hits) / max(cn_hits, pubmed_hits, 1)"""
    item = _compute_item_metrics(
        id="test-div",
        question="test",
        source_preference="all",
        question_language="zh",
        expected_cn_ids=["cn-a"],
        expected_pubmed_ids=["pmid-x"],
        top_k=5,
        retrieved_ids=["cn-a", "cn-b", "cn-c", "pmid-x", "pmid-y"],
    )
    # cn_hits=3, pubmed_hits=2 → diversity = 2/3
    assert item.language_diversity == round(2 / 3, 4)


def test_compute_item_metrics_english_question():
    """英文问题：monolingual recall 对 pubmed，cross-lingual recall 对 cn"""
    item = _compute_item_metrics(
        id="test-en",
        question="barrier dysfunction in AD",
        source_preference="pubmed",
        question_language="en",
        expected_cn_ids=["cn-a"],
        expected_pubmed_ids=["pmid-x", "pmid-y"],
        top_k=5,
        retrieved_ids=["pmid-x", "cn-a", "pmid-z", "cn-b", "pmid-y"],
    )
    # monolingual: en → pubmed expected, hits = pmid-x + pmid-y = 2/2 = 1.0
    assert item.monolingual_recall == 1.0
    # cross-lingual: en → cn expected, hits = cn-a = 1/1 = 1.0
    assert item.cross_lingual_recall == 1.0


# ---------------------------------------------------------------------------
# Integration tests: run_cross_lingual_retrieval_eval
# ---------------------------------------------------------------------------

_EVAL_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "evals" / "rag_ad_eval_questions.json"
)


def test_run_cross_lingual_retrieval_eval_returns_report():
    """端到端：调用 eval 函数返回 CrossLingualRetrievalReport"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    assert isinstance(report, CrossLingualRetrievalReport)
    assert report.summary.total_questions > 0
    assert report.summary.retrieval_strategy == "keyword"
    assert len(report.items) == report.summary.total_questions


def test_run_cross_lingual_retrieval_eval_baseline_not_zero():
    """基线不应全为零——至少同语言召回应该合理"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    # 同语言召回应该合理（中文问题找中文文献）
    assert report.summary.avg_monolingual_recall > 0.0


def test_run_cross_lingual_retrieval_eval_items_have_correct_fields():
    """每个 item 应包含正确的字段类型"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    for item in report.items:
        assert isinstance(item, CrossLingualRetrievalItem)
        assert item.question_language in ("zh", "en")
        assert item.top_k == 10
        assert 0.0 <= item.monolingual_recall <= 1.0
        assert 0.0 <= item.cross_lingual_recall <= 1.0
        assert 0.0 <= item.language_diversity <= 1.0
        assert 0.0 <= item.mean_reciprocal_rank <= 1.0
        assert 0.0 <= item.precision_at_k <= 1.0


def test_run_cross_lingual_retrieval_eval_only_bilingual_questions():
    """只评估双语题目（expected_literature_ids 同时含 cn-* 和 pmid-*）"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    # Every item should have both cn and pubmed expected IDs
    for item in report.items:
        assert len(item.expected_cn_ids) > 0, f"Item {item.id} has no cn expected IDs"
        assert len(item.expected_pubmed_ids) > 0, f"Item {item.id} has no pubmed expected IDs"


# ---------------------------------------------------------------------------
# Slice 2: cross-lingual retrieval fix — regression + improvement tests
# ---------------------------------------------------------------------------


def test_cross_lingual_recall_improves_above_zero_after_fix():
    """Slice 2 核心断言：修复后 cross_lingual_recall > 0"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    assert report.summary.avg_cross_lingual_recall > 0.0, (
        f"Expected cross-lingual recall > 0.0, got {report.summary.avg_cross_lingual_recall}"
    )
    # 同语言召回不应退化到 0.9 以下
    assert report.summary.avg_monolingual_recall >= 0.9, (
        f"Monolingual recall regressed: {report.summary.avg_monolingual_recall}"
    )


# ---------------------------------------------------------------------------
# Slice 6: 跨语言术语桥扩展（"微生态" → gut，闭合 rag-eval-011）
# ---------------------------------------------------------------------------

# 扩展前基线 avg_cross_lingual_recall（17 双语题中 13 题完美）。术语桥扩展只能升不能降。
_CROSS_LINGUAL_RECALL_BASELINE = 0.7647


def _item_by_id(report: CrossLingualRetrievalReport, qid: str) -> CrossLingualRetrievalItem:
    for item in report.items:
        if item.id == qid:
            return item
    raise AssertionError(f"question {qid} not found in cross-lingual report")


def test_rag_eval_011_cross_lingual_recall_above_zero():
    """rag-eval-011（中英文献 AD 微生态研究对比）此前 cross_lingual_recall=0：
    查询词「微生态」触发不了任何 microbiome/gut 桥，期望英文文献拿不到主题性跨语 token。
    扩展术语桥后应 > 0——至少召回 pmid-40100002（带 gut_skin_axis 标签，吃到 +7 tag-bonus）；
    pmid-40100009 缺 gut_skin_axis 标签，纯数据无法拉进 top-10，属已知结构性上限。"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    item = _item_by_id(report, "rag-eval-011")
    assert item.cross_lingual_recall > 0.0, (
        f"rag-eval-011 cross-lingual recall should improve above 0, got {item.cross_lingual_recall}"
    )
    assert "pmid-40100002" in item.retrieved_ids


def test_cross_lingual_term_bridge_no_aggregate_regression():
    """术语桥扩展不得让聚合 cross/mono recall 回归。"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    assert report.summary.avg_cross_lingual_recall >= _CROSS_LINGUAL_RECALL_BASELINE, (
        f"cross-lingual recall regressed below baseline {_CROSS_LINGUAL_RECALL_BASELINE}: "
        f"{report.summary.avg_cross_lingual_recall}"
    )
    assert report.summary.avg_monolingual_recall == 1.0, (
        f"monolingual recall regressed: {report.summary.avg_monolingual_recall}"
    )
