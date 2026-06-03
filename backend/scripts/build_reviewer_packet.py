"""Build a markdown reviewer packet from a real-answer capture JSON.

This is intentionally a delta-only artifact for the post-2026-06-01 L2 line:
the prior §4c reviewer walkthrough already verified gate/rollback behavior.
This packet only prepares passed claims for explicit reviewer support checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


SECRET_PATTERNS = (
    re.compile(r"QIYAN_OPENCODE_GO_API_KEY\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"QIYAN_OPENCODE_GO_API_KEY", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
)


@dataclass(frozen=True)
class ReviewerPacketBuildResult:
    output_path: Path
    selected_question_ids: list[str]
    warning_count: int


def _sanitize(value: object) -> str:
    if value is None:
        return "null"
    text = str(value)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text.strip()


def _metric(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return _sanitize(value)


def _cell(value: object) -> str:
    return _sanitize(value).replace("\n", "<br>").replace("|", "\\|")


def _quote_block(text: object) -> list[str]:
    sanitized = _sanitize(text)
    if not sanitized:
        return [">"]
    return [f"> {line}" for line in sanitized.splitlines()]


def _load_capture(input_path: Path) -> dict[str, Any]:
    return json.loads(input_path.read_text(encoding="utf-8"))


def _select_questions(payload: dict[str, Any], question_ids: Sequence[str]) -> list[dict[str, Any]]:
    questions = payload.get("questions", [])
    questions_by_id = {question.get("question_id"): question for question in questions}

    if question_ids:
        missing_ids = [
            question_id for question_id in question_ids if question_id not in questions_by_id
        ]
        if missing_ids:
            raise ValueError(f"missing question ids: {', '.join(missing_ids)}")
        selected = [questions_by_id[question_id] for question_id in question_ids]
    else:
        selected = [
            question for question in questions if question.get("grounding_status") == "passed"
        ]

    non_passed = [
        _sanitize(question.get("question_id"))
        for question in selected
        if question.get("grounding_status") != "passed"
    ]
    if non_passed:
        raise ValueError(f"selected questions are not passed: {', '.join(non_passed)}")

    if not selected:
        raise ValueError("no passed questions found")
    return selected


def _append_capture_summary(lines: list[str], input_path: Path, meta: dict[str, Any]) -> None:
    lines.extend(
        [
            "## Capture Summary",
            "",
            f"- Source capture: `{_sanitize(input_path.name)}`",
            f"- Capture source: `{_sanitize(meta.get('source'))}`",
            f"- Captured at: `{_sanitize(meta.get('captured_at'))}`",
            f"- Provider: `{_sanitize(meta.get('llm_provider'))}`",
            f"- Embedding backend: `{_sanitize(meta.get('embedding_backend'))}`",
            f"- Semantic threshold: `{_sanitize(meta.get('semantic_threshold'))}`",
            f"- Max tokens: `{_sanitize(meta.get('max_tokens'))}`",
            f"- Questions captured: `{_sanitize(meta.get('questions_captured'))}`",
            f"- Total claims: `{_sanitize(meta.get('total_claims'))}`",
            "",
        ]
    )


def _append_question_summary(lines: list[str], questions: list[dict[str, Any]]) -> None:
    lines.extend(
        [
            "## Selected Questions",
            "",
            "| Question ID | Claims | Min semantic | Min entailment | Latency ms | Cost |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for question in questions:
        lines.append(
            "| "
            f"{_cell(question.get('question_id'))} | "
            f"{_cell(question.get('claim_count'))} | "
            f"{_cell(_metric(question.get('min_semantic_score')))} | "
            f"{_cell(_metric(question.get('min_entailment_score')))} | "
            f"{_cell(question.get('provider_latency_ms'))} | "
            f"{_cell(_metric(question.get('estimated_cost_usd')))} |"
        )
    lines.append("")


def _append_review_instructions(lines: list[str]) -> None:
    lines.extend(
        [
            "## Reviewer Instructions",
            "",
            "- This is a delta-only packet. The 2026-06-01 §4c reviewer walkthrough already verified gate, fallback, rollback, and UI metadata behavior.",
            "- Review only whether each passed claim is directly supported by its cited chunk.",
            "- Use one verdict per claim: `supported`, `unsupported`, or `unclear`.",
            "- Do not treat this packet as a default-provider flip. The default RAG path remains offline `deterministic` unless ADR-0012 is changed separately.",
            "",
        ]
    )


def _append_warnings(lines: list[str], warnings: list[str]) -> None:
    if not warnings:
        return
    lines.extend(["## Packet Warnings", ""])
    for warning in warnings:
        lines.append(f"- {warning}")
    lines.append("")


def _append_claim(
    lines: list[str],
    *,
    question_id: str,
    claim_index: int,
    claim: dict[str, Any],
    warnings: list[str],
) -> None:
    evidence_refs = claim.get("evidence_refs") or []
    if len(evidence_refs) != 1:
        warnings.append(
            f"{question_id} claim has {len(evidence_refs)} evidence refs "
            f"(claim {claim_index}); expected exactly 1."
        )

    lines.extend(
        [
            f"### Claim {claim_index}",
            "",
            "Claim:",
            "",
            *_quote_block(claim.get("text")),
            "",
            f"- Evidence refs: `{_sanitize(', '.join(evidence_refs) if evidence_refs else 'none')}`",
            f"- Semantic score: `{_metric(claim.get('semantic_score'))}`",
            f"- Entailment score: `{_metric(claim.get('entailment_score'))}`",
            "- Reviewer verdict: `[ ] supported` / `[ ] unsupported` / `[ ] unclear`",
            "- Reviewer notes:",
            "",
            "Cited evidence:",
            "",
        ]
    )

    cited_chunks = claim.get("cited_chunks") or []
    if not cited_chunks:
        warnings.append(f"{question_id} claim {claim_index} has no cited chunk text.")
        lines.extend(["_No cited chunk text captured._", ""])
        return

    for chunk in cited_chunks:
        lines.extend(
            [
                f"- Chunk: `{_sanitize(chunk.get('chunk_id'))}`",
                f"- Literature: `{_sanitize(chunk.get('literature_id'))}`",
                f"- Section: `{_sanitize(chunk.get('section'))}`",
                "",
                *_quote_block(chunk.get("text")),
                "",
            ]
        )


def _append_question(lines: list[str], question: dict[str, Any], warnings: list[str]) -> None:
    question_id = _sanitize(question.get("question_id"))
    lines.extend(
        [
            f"## {question_id}",
            "",
            f"- Question: {_sanitize(question.get('question'))}",
            f"- Provider: `{_sanitize(question.get('provider_name'))}`",
            f"- Retrieval strategy: `{_sanitize(question.get('retrieval_strategy'))}`",
            f"- Grounding status: `{_sanitize(question.get('grounding_status'))}`",
            f"- Semantic threshold: `{_sanitize(question.get('semantic_threshold'))}`",
            f"- NLI threshold: `{_sanitize(question.get('nli_threshold'))}`",
            f"- Input tokens: `{_sanitize(question.get('input_tokens'))}`",
            f"- Output tokens: `{_sanitize(question.get('output_tokens'))}`",
            f"- Provider latency ms: `{_sanitize(question.get('provider_latency_ms'))}`",
            f"- Estimated cost: `{_metric(question.get('estimated_cost_usd'))}`",
            "",
            "Answer shown after grounding:",
            "",
            *_quote_block(question.get("answer")),
            "",
        ]
    )

    for index, claim in enumerate(question.get("claims", []), 1):
        _append_claim(
            lines,
            question_id=question_id,
            claim_index=index,
            claim=claim,
            warnings=warnings,
        )


def _render_packet(
    *,
    input_path: Path,
    payload: dict[str, Any],
    selected_questions: list[dict[str, Any]],
    generated_at: str,
) -> tuple[str, int]:
    warnings: list[str] = []
    meta = payload.get("capture_meta", {})
    lines = [
        "# L2 Passed Claims Reviewer Packet",
        "",
        f"date: {generated_at}",
        "status: pending reviewer verdicts; default provider unchanged",
        "",
        "## Purpose",
        "",
        "This packet prepares the 2026-06-02 passed real-provider claims for formal reviewer sign-off.",
        "It is delta-only: it does not repeat the 2026-06-01 §4c reviewer walkthrough that already verified gate, fallback, rollback, and UI metadata behavior.",
        "",
    ]
    _append_capture_summary(lines, input_path, meta)
    _append_question_summary(lines, selected_questions)
    _append_review_instructions(lines)

    question_start_index = len(lines)
    for question in selected_questions:
        _append_question(lines, question, warnings)

    if warnings:
        question_lines = lines[question_start_index:]
        lines = lines[:question_start_index]
        _append_warnings(lines, warnings)
        lines.extend(question_lines)

    return "\n".join(lines).rstrip() + "\n", len(warnings)


def build_reviewer_packet(
    *,
    input_path: Path,
    output_path: Path,
    question_ids: Sequence[str] = (),
    generated_at: str | None = None,
) -> ReviewerPacketBuildResult:
    payload = _load_capture(input_path)
    selected_questions = _select_questions(payload, question_ids)
    selected_question_ids = [
        _sanitize(question.get("question_id")) for question in selected_questions
    ]
    rendered_at = generated_at or datetime.now(UTC).date().isoformat()
    markdown, warning_count = _render_packet(
        input_path=input_path,
        payload=payload,
        selected_questions=selected_questions,
        generated_at=rendered_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return ReviewerPacketBuildResult(
        output_path=output_path,
        selected_question_ids=selected_question_ids,
        warning_count=warning_count,
    )


def _parse_question_ids(raw_question_ids: str) -> list[str]:
    return [
        question_id.strip() for question_id in raw_question_ids.split(",") if question_id.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a markdown reviewer packet from a captured real-claims JSON file."
    )
    parser.add_argument("--input", required=True, type=Path, help="Capture JSON path.")
    parser.add_argument("--output", required=True, type=Path, help="Markdown output path.")
    parser.add_argument(
        "--question-ids",
        default="",
        help="Comma-separated question IDs. Defaults to all passed questions in the capture.",
    )
    args = parser.parse_args()

    result = build_reviewer_packet(
        input_path=args.input,
        output_path=args.output,
        question_ids=_parse_question_ids(args.question_ids),
    )
    print(
        f"wrote {result.output_path} with {len(result.selected_question_ids)} questions "
        f"and {result.warning_count} warnings"
    )


if __name__ == "__main__":
    main()
