import json
from pathlib import Path

import pytest

from scripts.build_reviewer_packet import build_reviewer_packet


def _write_capture(path: Path, questions: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "capture_meta": {
                    "source": "live_opencode_go",
                    "captured_at": "2026-06-02T08:46:00+08:00",
                    "llm_provider": "opencode_go",
                    "embedding_backend": "bge",
                    "semantic_threshold": "0.3",
                    "max_tokens": "4000",
                    "questions_captured": len(questions),
                    "total_claims": sum(len(question.get("claims", [])) for question in questions),
                    "grounding_status_counts": {"passed": len(questions)},
                },
                "questions": questions,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _passed_question(question_id: str = "rag-eval-005") -> dict:
    return {
        "question_id": question_id,
        "question": "英文文献中如何解释特应性皮炎的皮肤屏障损伤？",
        "provider_name": "opencode_go",
        "retrieval_strategy": "keyword",
        "grounding_status": "passed",
        "claim_count": 1,
        "claims_with_zero_refs": 0,
        "claims_with_one_ref": 1,
        "claims_with_multi_refs": 0,
        "min_semantic_score": 0.3394,
        "semantic_threshold": 0.3,
        "min_entailment_score": 0.9985,
        "nli_threshold": 0.5,
        "input_tokens": 400,
        "output_tokens": 120,
        "provider_latency_ms": 5252,
        "estimated_cost_usd": None,
        "answer": "丝聚蛋白功能缺失变异导致经皮水分丢失增加。",
        "claims": [
            {
                "text": "丝聚蛋白功能缺失变异导致经皮水分丢失增加和表皮屏障减弱。",
                "evidence_refs": ["chunk-pmid-40100006-filaggrin"],
                "semantic_score": 0.339448511600494,
                "entailment_score": 0.99853515625,
                "cited_chunks": [
                    {
                        "chunk_id": "chunk-pmid-40100006-filaggrin",
                        "text": (
                            "Filaggrin loss-of-function variants drive transepidermal "
                            "water loss and weaken the epidermal barrier in atopic dermatitis."
                        ),
                        "literature_id": "pmid-40100006",
                        "section": "review",
                    }
                ],
            }
        ],
    }


def test_build_reviewer_packet_writes_passed_claim_review_template(tmp_path):
    input_path = tmp_path / "capture.json"
    output_path = tmp_path / "packet.md"
    _write_capture(input_path, [_passed_question()])

    result = build_reviewer_packet(
        input_path=input_path,
        output_path=output_path,
        question_ids=["rag-eval-005"],
        generated_at="2026-06-02",
    )

    output = output_path.read_text(encoding="utf-8")
    assert result.selected_question_ids == ["rag-eval-005"]
    assert result.warning_count == 0
    assert "# L2 Passed Claims Reviewer Packet" in output
    assert "delta-only" in output
    assert "rag-eval-005" in output
    assert "chunk-pmid-40100006-filaggrin" in output
    assert "Filaggrin loss-of-function variants" in output
    assert "Reviewer verdict: `[ ] supported` / `[ ] unsupported` / `[ ] unclear`" in output
    assert "Estimated cost: `null`" in output


def test_build_reviewer_packet_errors_for_missing_question_id(tmp_path):
    input_path = tmp_path / "capture.json"
    output_path = tmp_path / "packet.md"
    _write_capture(input_path, [_passed_question()])

    with pytest.raises(ValueError, match="missing question ids: rag-eval-999"):
        build_reviewer_packet(
            input_path=input_path,
            output_path=output_path,
            question_ids=["rag-eval-999"],
        )


def test_build_reviewer_packet_warns_about_multi_ref_claims(tmp_path):
    question = _passed_question()
    question["claims"][0]["evidence_refs"] = ["chunk-a", "chunk-b"]
    input_path = tmp_path / "capture.json"
    output_path = tmp_path / "packet.md"
    _write_capture(input_path, [question])

    result = build_reviewer_packet(
        input_path=input_path,
        output_path=output_path,
        question_ids=["rag-eval-005"],
    )

    output = output_path.read_text(encoding="utf-8")
    assert result.warning_count == 1
    assert "claim has 2 evidence refs" in output


def test_build_reviewer_packet_redacts_secret_like_values(tmp_path):
    question = _passed_question()
    env_name = "QIYAN_" + "OPENCODE_GO_API_KEY"
    secret_value = "sk-" + "dummy-value-1234567890"
    question["answer"] = f"do not leak {env_name}={secret_value}"
    input_path = tmp_path / "capture.json"
    output_path = tmp_path / "packet.md"
    _write_capture(input_path, [question])

    build_reviewer_packet(
        input_path=input_path,
        output_path=output_path,
        question_ids=["rag-eval-005"],
    )

    output = output_path.read_text(encoding="utf-8")
    assert secret_value not in output
    assert env_name not in output
    assert "[REDACTED]" in output
