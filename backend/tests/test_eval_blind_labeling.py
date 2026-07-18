"""Behaviour tests for the non-circular blind-labeling eval harness."""

import json
from pathlib import Path

import pytest

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from scripts.eval_blind_labeling import (
    _query_set_fingerprint,
    _review_payload_fingerprint,
    build_labeling_bundle,
    normalize_query_set,
    score_worksheet,
)


def _query_set(*questions: str) -> dict[str, object]:
    return {
        "dataset_id": "test-held-out-v1",
        "status": "frozen",
        "queries": [
            {
                "query_id": f"q-{index}",
                "question": question,
                "language": "zh"
                if any("\u4e00" <= char <= "\u9fff" for char in question)
                else "en",
                "topic": "test",
                "user_role": "clinician",
            }
            for index, question in enumerate(questions, start=1)
        ],
    }


def _seed_repositories(
    tmp_path: Path,
) -> tuple[InMemoryLiteratureRepository, InMemoryChunkRepository]:
    root = Path(__file__).resolve().parents[1]
    literature_path = tmp_path / "literature.json"
    chunk_path = tmp_path / "chunks.json"
    literature_path.write_bytes((root / "data/literature/sample_ad_literature.json").read_bytes())
    chunk_path.write_bytes((root / "data/literature/sample_ad_chunks.json").read_bytes())
    return InMemoryLiteratureRepository(literature_path), InMemoryChunkRepository(chunk_path)


def _seal_score_bundle(
    worksheet: dict[str, object], manifest: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    normalized_queries = []
    worksheet_queries = worksheet["queries"]
    manifest_queries = manifest["queries"]
    assert isinstance(worksheet_queries, list)
    assert isinstance(manifest_queries, list)
    for entry in worksheet_queries:
        assert isinstance(entry, dict)
        normalized_queries.append(
            {
                "query_id": str(entry.get("query_id", "")),
                "question": str(entry.get("question", "")),
                "language": str(entry.get("language", "unspecified")),
                "topic": str(entry.get("topic", "unspecified")),
                "user_role": str(entry.get("user_role", "unspecified")),
                "provenance": str(entry.get("provenance", "unspecified")),
            }
        )
    query_sha = _query_set_fingerprint(normalized_queries)
    worksheet["dataset_id"] = "test-score-dataset"
    worksheet["query_set_status"] = "frozen"
    worksheet["query_set_sha256"] = query_sha
    manifest["dataset_id"] = "test-score-dataset"
    manifest["query_set"] = {
        "status": "frozen",
        "query_count": len(normalized_queries),
        "sha256": query_sha,
    }
    visible_by_query = {
        entry["query_id"]: {
            candidate["candidate_id"]: candidate for candidate in entry["candidates"]
        }
        for entry in worksheet_queries
    }
    for entry in manifest_queries:
        for hidden in entry["candidates"]:
            visible = visible_by_query[entry["query_id"]][hidden["candidate_id"]]
            hidden["review_payload_sha256"] = _review_payload_fingerprint(visible)
    return worksheet, manifest


def test_normalize_query_set_accepts_versioned_objects_and_rejects_duplicates():
    metadata, queries = normalize_query_set(_query_set("特应性皮炎如何修复皮肤屏障？"))

    assert metadata["dataset_id"] == "test-held-out-v1"
    assert queries[0]["query_id"] == "q-1"

    duplicate = _query_set("q1", "q2")
    duplicate["queries"][1]["query_id"] = "q-1"  # type: ignore[index]
    with pytest.raises(ValueError, match="duplicate query_id"):
        normalize_query_set(duplicate)


def test_validation_v1_query_set_is_frozen_without_expected_ids():
    query_path = Path(__file__).resolve().parents[1] / "scripts/eval_queries.validation.v1.json"
    payload = json.loads(query_path.read_text(encoding="utf-8"))

    metadata, queries = normalize_query_set(payload)

    assert metadata["dataset_id"] == "ad-real-retrieval-held-out-v1"
    assert len(queries) == 30
    assert all("expected" not in key for entry in payload["queries"] for key in entry)


def test_build_bundle_fails_closed_when_seed_records_enter_real_only_eval(tmp_path: Path):
    literature_repo, chunk_repo = _seed_repositories(tmp_path)

    with pytest.raises(ValueError, match="real-only"):
        build_labeling_bundle(
            _query_set("What is the evidence for JAK inhibitors in atopic dermatitis?"),
            top_k=5,
            shuffle_seed=7,
            min_live_records=1,
            literature_repository=literature_repo,
            chunk_repository=chunk_repo,
        )


def test_build_bundle_fails_closed_when_runtime_chunks_are_not_live_pubmed(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    literature_payload = json.loads(
        (root / "data/literature/sample_ad_literature.json").read_text(encoding="utf-8")
    )[:1]
    literature_payload[0].update(
        {
            "id": "pmid-live-test",
            "record_origin": "pubmed_live",
            "source_type": "pubmed",
            "source": "PubMed live sync",
        }
    )
    chunk_payload = [
        {
            "chunk_id": "poisoned-uploaded-chunk",
            "literature_id": "pmid-live-test",
            "section": "uploaded",
            "text": "uploaded text that must not enter a PubMed-only baseline",
            "source_quote": "uploaded text",
            "source_type": "uploaded_pdf",
            "pdf_upload_id": "pdf-foreign",
        }
    ]
    literature_path = tmp_path / "literature.json"
    chunk_path = tmp_path / "chunks.json"
    literature_path.write_text(json.dumps(literature_payload), encoding="utf-8")
    chunk_path.write_text(json.dumps(chunk_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="chunk"):
        build_labeling_bundle(
            _query_set("What is atopic dermatitis?"),
            top_k=1,
            min_live_records=1,
            literature_repository=InMemoryLiteratureRepository(literature_path),
            chunk_repository=InMemoryChunkRepository(chunk_path),
        )


def test_build_bundle_uses_product_selection_and_blinds_rank_and_score(tmp_path: Path):
    literature_repo, chunk_repo = _seed_repositories(tmp_path)
    worksheet, manifest = build_labeling_bundle(
        _query_set(
            "特应性皮炎和皮肤屏障有什么关系？",
            "高血压一线降压药是什么？",
        ),
        top_k=3,
        shuffle_seed=19,
        require_real_only=False,
        min_live_records=0,
        literature_repository=literature_repo,
        chunk_repository=chunk_repo,
    )

    serialized = json.dumps(worksheet, ensure_ascii=False)
    assert "retrieval_rank" not in serialized
    assert "retrieval_score" not in serialized
    assert all(
        "rank" not in candidate and "score" not in candidate and "match_score" not in candidate
        for entry in worksheet["queries"]
        for candidate in entry["candidates"]
    )

    topical = worksheet["queries"][0]
    off_topic = worksheet["queries"][1]
    assert topical["candidates"]
    assert off_topic["candidates"] == []
    assert manifest["retrieval"]["selection_mode"] == "rag_answer_citations"
    assert manifest["queries"][0]["candidates"][0]["retrieval_rank"] == 1
    assert manifest["corpus"]["chunk_count"] > 0
    assert manifest["corpus"]["chunk_sha256"]
    assert manifest["retrieval"]["shuffle_secret"] == "19"
    assert "shuffle_secret" not in worksheet


def test_worksheet_identity_changes_when_query_text_changes(tmp_path: Path):
    literature_repo, chunk_repo = _seed_repositories(tmp_path)
    first, first_manifest = build_labeling_bundle(
        _query_set("特应性皮炎皮肤屏障证据有哪些？"),
        top_k=2,
        require_real_only=False,
        min_live_records=0,
        literature_repository=literature_repo,
        chunk_repository=chunk_repo,
    )
    second, second_manifest = build_labeling_bundle(
        _query_set("特应性皮炎瘙痒证据有哪些？"),
        top_k=2,
        require_real_only=False,
        min_live_records=0,
        literature_repository=literature_repo,
        chunk_repository=chunk_repo,
    )

    assert first["worksheet_id"] != second["worksheet_id"]
    assert first_manifest["query_set"]["sha256"] != second_manifest["query_set"]["sha256"]


def test_score_worksheet_uses_hidden_rank_and_reports_precision_and_mrr_at_k():
    worksheet = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 3,
        "queries": [
            {
                "query_id": "q1",
                "candidates": [
                    {"candidate_id": "c-rank-3", "relevant": True},
                    {"candidate_id": "c-rank-1", "relevant": False},
                    {"candidate_id": "c-rank-2", "relevant": True},
                ],
            },
            {"query_id": "q2", "candidates": []},
        ],
    }
    manifest = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 3,
        "queries": [
            {
                "query_id": "q1",
                "candidates": [
                    {"candidate_id": "c-rank-1", "retrieval_rank": 1},
                    {"candidate_id": "c-rank-2", "retrieval_rank": 2},
                    {"candidate_id": "c-rank-3", "retrieval_rank": 3},
                ],
            },
            {"query_id": "q2", "candidates": []},
        ],
    }

    worksheet, manifest = _seal_score_bundle(worksheet, manifest)
    result = score_worksheet(worksheet, manifest)

    assert result["labeled_queries"] == 2
    assert result["unlabeled_queries"] == 0
    assert result["mean_precision_at_k"] == round(((2 / 3) + 0) / 2, 3)
    assert result["mrr_at_k"] == round((0.5 + 0) / 2, 3)
    assert result["per_query"][0]["first_relevant_rank"] == 2
    assert result["per_query"][1]["returned_candidates"] == 0


def test_score_worksheet_rejects_non_boolean_labels():
    worksheet = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 1,
        "queries": [{"query_id": "q1", "candidates": [{"candidate_id": "c1", "relevant": "true"}]}],
    }
    manifest = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 1,
        "queries": [
            {"query_id": "q1", "candidates": [{"candidate_id": "c1", "retrieval_rank": 1}]}
        ],
    }

    worksheet, manifest = _seal_score_bundle(worksheet, manifest)
    with pytest.raises(ValueError, match="JSON boolean"):
        score_worksheet(worksheet, manifest)


def test_score_worksheet_skips_partially_labeled_query():
    worksheet = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 2,
        "queries": [
            {
                "query_id": "q1",
                "candidates": [
                    {"candidate_id": "c1", "relevant": None},
                    {"candidate_id": "c2", "relevant": True},
                ],
            }
        ],
    }
    manifest = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 2,
        "queries": [
            {
                "query_id": "q1",
                "candidates": [
                    {"candidate_id": "c1", "retrieval_rank": 1},
                    {"candidate_id": "c2", "retrieval_rank": 2},
                ],
            }
        ],
    }

    worksheet, manifest = _seal_score_bundle(worksheet, manifest)
    result = score_worksheet(worksheet, manifest)

    assert result["labeled_queries"] == 0
    assert result["unlabeled_queries"] == 1
    assert result["mrr_at_k"] is None
    assert result["mean_precision_at_k"] is None


def test_score_worksheet_does_not_publish_partial_metrics():
    worksheet = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 1,
        "queries": [
            {"query_id": "q1", "candidates": [{"candidate_id": "c1", "relevant": True}]},
            {"query_id": "q2", "candidates": [{"candidate_id": "c2", "relevant": None}]},
        ],
    }
    manifest = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 1,
        "queries": [
            {"query_id": "q1", "candidates": [{"candidate_id": "c1", "retrieval_rank": 1}]},
            {"query_id": "q2", "candidates": [{"candidate_id": "c2", "retrieval_rank": 1}]},
        ],
    }

    worksheet, manifest = _seal_score_bundle(worksheet, manifest)
    result = score_worksheet(worksheet, manifest)

    assert result["labeled_queries"] == 1
    assert result["unlabeled_queries"] == 1
    assert result["mean_precision_at_k"] is None
    assert result["mrr_at_k"] is None
    assert result["per_query"] == []


def test_score_worksheet_rejects_changed_query_or_candidate_text():
    worksheet = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 1,
        "queries": [
            {
                "query_id": "q1",
                "question": "atopic dermatitis barrier evidence",
                "candidates": [
                    {
                        "candidate_id": "c1",
                        "title": "Original PubMed title",
                        "abstract": "Original abstract",
                        "relevant": False,
                    }
                ],
            }
        ],
    }
    manifest = {
        "schema_version": 2,
        "worksheet_id": "ws-1",
        "top_k": 1,
        "queries": [
            {"query_id": "q1", "candidates": [{"candidate_id": "c1", "retrieval_rank": 1}]}
        ],
    }
    worksheet, manifest = _seal_score_bundle(worksheet, manifest)

    changed_query = json.loads(json.dumps(worksheet))
    changed_query["queries"][0]["question"] = "高血压一线治疗"
    with pytest.raises(ValueError, match="query-set fingerprint"):
        score_worksheet(changed_query, manifest)

    changed_candidate = json.loads(json.dumps(worksheet))
    changed_candidate["queries"][0]["candidates"][0]["title"] = "Fabricated title"
    with pytest.raises(ValueError, match="review payload"):
        score_worksheet(changed_candidate, manifest)
