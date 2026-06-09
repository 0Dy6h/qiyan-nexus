"""Tests for cross-lingual retrieval eval harness (Slice 1: RED baseline)."""

from pathlib import Path

import pytest

from app.schemas.eval import (
    CrossLingualRetrievalItem,
    CrossLingualRetrievalReport,
    load_rag_eval_dataset,
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
_SEED_LITERATURE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
)
_SEED_CHUNK_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_chunks.json"
)


def _write_polluted_runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Create a runtime-like corpus with uploaded chunks that distort retrieval ranking."""
    literature_path = tmp_path / "literature_state.json"
    chunk_path = tmp_path / "chunk_state.json"
    literature_path.write_text(_SEED_LITERATURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    raw_chunks = load_json_chunks(_SEED_CHUNK_PATH)
    for index, literature_id in enumerate(
        [
            "pmid-40100001",
            "cn-ad-barrier-006",
            "cn-ad-pruritus-005",
            "cn-ad-external-008",
            "cn-ad-gbs-001",
            "cn-ad-child-009",
        ]
    ):
        raw_chunks.append(
            {
                "chunk_id": f"chunk-uploaded-runtime-noise-{index}",
                "literature_id": literature_id,
                "section": "uploaded_pdf",
                "text": (
                    "分子对接 分子模拟 靶点 通路 后续 线索 molecular docking "
                    "molecular simulation target pathway targeted therapy "
                )
                * 5,
                "source_quote": "分子对接 分子模拟 靶点 通路",
                "evidence_tags": [
                    "uploaded_pdf",
                    "network_pharmacology",
                    "pathway",
                    "targeted_therapy",
                ],
                "related_entity_ids": [],
                "source_type": "uploaded_pdf",
                "pdf_upload_id": f"pdf-{literature_id}-polluted",
            }
        )
    chunk_path.write_text(json_dumps(raw_chunks), encoding="utf-8")
    return literature_path, chunk_path


def load_json_chunks(path: Path) -> list[dict[str, object]]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def json_dumps(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


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


def test_cross_lingual_eval_default_uses_seed_corpus_even_when_runtime_is_polluted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Benchmark eval must not silently consume local uploaded-PDF runtime chunks."""
    literature_path, chunk_path = _write_polluted_runtime_fixture(tmp_path)
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(literature_path))
    monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(chunk_path))

    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )

    assert report.summary.corpus == "seed"
    assert report.summary.avg_cross_lingual_recall >= _CROSS_LINGUAL_RECALL_BASELINE


def test_cross_lingual_eval_runtime_corpus_is_explicit_and_can_reflect_local_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Runtime eval is still available, but it must be opt-in and labeled."""
    literature_path, chunk_path = _write_polluted_runtime_fixture(tmp_path)
    monkeypatch.setenv("LITERATURE_RUNTIME_STATE_PATH", str(literature_path))
    monkeypatch.setenv("CHUNK_RUNTIME_STATE_PATH", str(chunk_path))

    report = run_cross_lingual_retrieval_eval(
        strategy="keyword",
        top_k=10,
        eval_data_path=_EVAL_DATA_PATH,
        corpus="runtime",
    )

    assert report.summary.corpus == "runtime"
    assert report.summary.avg_cross_lingual_recall < _CROSS_LINGUAL_RECALL_BASELINE


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
# Slice 7: alias_tag_bonus 识别 cross-lingual canonical（闭合 rag-eval-035/047）
# ---------------------------------------------------------------------------

# 基线 avg_cross_lingual_recall。Slice 6 把 0.7647 抬到 0.7941；Slice 7 让 035/047 各自
# 从 0 → 1.0（两题都只期望一个 cross-lingual id：pmid-40100002），聚合升至 0.9118；
# Slice 8 expected-label 审计把 pmid-40100004 从 rag-eval-020 移除，rag-eval-020 失去
# pubmed 期望被 bilingual 过滤剔除（17→16 题），剩余 15 题完美 + rag-eval-011 单题
# 0.5，聚合 (15+0.5)/16 = 0.9688。Slice 9 把「微生态」同时桥接到 microbiome，
# 闭合 q011 的皮肤微生态英文期望，16 道 bilingual 题全部达到 cross recall=1.0。
_CROSS_LINGUAL_RECALL_BASELINE = 1.0


def _item_by_id(report: CrossLingualRetrievalReport, qid: str) -> CrossLingualRetrievalItem:
    for item in report.items:
        if item.id == qid:
            return item
    raise AssertionError(f"question {qid} not found in cross-lingual report")


def test_rag_eval_011_cross_lingual_recall_equals_one():
    """rag-eval-011（中英文献 AD 微生态研究对比）应同时召回中文肠道微生态、
    英文 microbiome 及英文 skin microbiome / S. aureus 视角。2026-06-04 审计确认
    「微生态」不是纯 gut 术语，也应桥接到 microbiome，从而闭合 pmid-40100009。"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    item = _item_by_id(report, "rag-eval-011")
    assert item.cross_lingual_recall == 1.0, (
        f"rag-eval-011 cross-lingual recall should be 1.0, got {item.cross_lingual_recall}"
    )
    assert "pmid-40100002" in item.retrieved_ids
    assert "pmid-40100009" in item.retrieved_ids


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


def test_rag_eval_035_cross_lingual_recall_equals_one():
    """rag-eval-035（中文查询，期望 cn-ad-microbiome-003 + pmid-40100002）：
    Slice 7 前 pmid-40100002 卡在 rank 11，cross_lingual_recall=0。
    扩展 alias_tag_bonus 识别 cross-lingual canonical 后，``microbiome`` 标签也吃到 +7
    桥接奖励，pmid-40100002 进入 top-10，单题召回应达 1.0。"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    item = _item_by_id(report, "rag-eval-035")
    assert item.cross_lingual_recall == 1.0, (
        f"rag-eval-035 cross-lingual recall should be 1.0, got {item.cross_lingual_recall}"
    )
    assert "pmid-40100002" in item.retrieved_ids


def test_rag_eval_047_cross_lingual_recall_equals_one():
    """rag-eval-047（中文查询，期望 cn-ad-review-010 + pmid-40100002）：症状与根因
    同 035，扩展 alias_tag_bonus 后 pmid-40100002 进入 top-10，单题召回应达 1.0。"""
    if not _EVAL_DATA_PATH.exists():
        pytest.skip("eval dataset not found")
    report = run_cross_lingual_retrieval_eval(
        strategy="keyword", top_k=10, eval_data_path=_EVAL_DATA_PATH
    )
    item = _item_by_id(report, "rag-eval-047")
    assert item.cross_lingual_recall == 1.0, (
        f"rag-eval-047 cross-lingual recall should be 1.0, got {item.cross_lingual_recall}"
    )
    assert "pmid-40100002" in item.retrieved_ids


# ---------------------------------------------------------------------------
# Slice 8: expected-label 审计（2026-06-02）
# - rag-eval-020：pmid-40100004（草药系统综述）与「合规要求」主题不重叠，
#   expected_chunk_ids 也未收录其 chunk，从 expected_literature_ids 移除。
# - rag-eval-011：pmid-40100009（皮肤微生态 + S. aureus）作为 EN 视角合法保留；
#   2026-06-04 审计将「微生态」补桥到 microbiome，retrieval miss 不再接受为 ceiling。
# 详见 docs/evaluations/2026-06-02-expected-label-audit.md。
# ---------------------------------------------------------------------------


def test_rag_eval_020_expected_literature_locks_audit_verdict():
    """2026-06-02 expected-label audit 结论：pmid-40100004（herbal systematic
    review）与 rag-eval-020 合规题主题不重叠，且 expected_chunk_ids 也未收录其
    chunk，故从 expected_literature_ids 移除；cn-ad-guideline-004 作为
    consensus/guideline 文献保留。移除后 rag-eval-020 失去 pubmed 期望，被
    run_cross_lingual_retrieval_eval 的 bilingual 过滤剔除（17→16 题）。"""
    questions = load_rag_eval_dataset(_EVAL_DATA_PATH)
    q = next(q for q in questions if q.id == "rag-eval-020")
    assert q.expected_literature_ids == ["cn-ad-guideline-004"]
    assert q.expected_chunk_ids == ["chunk-cn-ad-guideline-004-management"]
