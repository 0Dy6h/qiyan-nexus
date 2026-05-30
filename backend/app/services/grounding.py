import json
import re

import numpy as np

from app.schemas.rag import CitationCard, GroundedClaim, GroundingMetadata, GroundingPolicy
from app.services.retrieval.embedding import EmbeddingBackend

BLOCKED_ANSWER_TEXT = (
    "当前模型草稿未通过引用证据校验，系统已拦截展示。"
    "请核对下方引用卡片，或调整问题、来源与引用数量后重试。"
)

_EXTERNAL_PROVIDER_NAMES = {"anthropic", "opencode_go"}
_BRACKETED_REF_PATTERN = re.compile(r"[\[［]([A-Za-z0-9][A-Za-z0-9_.:-]*)[\]］]")
_CLAIM_SPLIT_PATTERN = re.compile(r"(?<=[。！？!?])|\n+")
_CLAIM_PREFIX_PATTERN = re.compile(r"^\s*(?:[-*•]|\d+[.、）)])\s*")
_MARKDOWN_MARKERS_PATTERN = re.compile(r"[*_`>#]")
_JSON_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_STRUCTURED_GROUNDING_POLICY: GroundingPolicy = "structured_claim_refs_v3"
_ANTHROPIC_TOOL_GROUNDING_POLICY: GroundingPolicy = "anthropic_tool_use_v1"
_OPENCODE_GO_TOOL_GROUNDING_POLICY: GroundingPolicy = "opencode_go_tool_use_v1"
_PROVIDER_NATIVE_TOOL_POLICIES = {
    _ANTHROPIC_TOOL_GROUNDING_POLICY,
    _OPENCODE_GO_TOOL_GROUNDING_POLICY,
}


def build_allowed_evidence_refs(citations: list[CitationCard]) -> list[str]:
    refs: list[str] = []
    for citation in citations:
        ref = citation.chunk_id or citation.literature_id
        if ref not in refs:
            refs.append(ref)
    return refs


def score_claim_support(claim_text: str, reference_text: str, backend: EmbeddingBackend) -> float:
    """Cosine similarity between a claim and its cited evidence text.

    The default ``HashingEmbeddingBackend`` makes this a lexical-overlap proxy,
    not true semantics; ``QIYAN_EMBEDDING_BACKEND=bge`` upgrades it in place.
    True cosine is computed (not a raw dot product) so the score stays in
    ``[0, 1]`` regardless of whether the backend L2-normalises its output.
    """

    vectors = backend.encode([claim_text, reference_text])
    claim_vec = vectors[0]
    reference_vec = vectors[1]
    denominator = float(np.linalg.norm(claim_vec) * np.linalg.norm(reference_vec))
    if denominator <= 1e-12:
        return 0.0
    cosine = float(np.dot(claim_vec, reference_vec) / denominator)
    return max(0.0, min(1.0, cosine))


def _reference_text_by_ref(citations: list[CitationCard]) -> dict[str, str]:
    """Map each evidence ref to the cited chunk text (``quote``) or abstract ``snippet``."""

    mapping: dict[str, str] = {}
    for citation in citations:
        ref = citation.chunk_id or citation.literature_id
        if ref not in mapping:
            mapping[ref] = citation.quote or citation.snippet
    return mapping


def extract_bracketed_refs(answer_text: str) -> list[str]:
    refs: list[str] = []
    for ref in _BRACKETED_REF_PATTERN.findall(answer_text):
        if ref not in refs:
            refs.append(ref)
    return refs


def extract_claim_sentences(answer_text: str) -> list[str]:
    claims: list[str] = []
    normalized = answer_text.replace("\r\n", "\n").replace("\r", "\n")
    for raw_part in _CLAIM_SPLIT_PATTERN.split(normalized):
        part = _CLAIM_PREFIX_PATTERN.sub("", raw_part.strip())
        claim_text = _BRACKETED_REF_PATTERN.sub("", part)
        claim_text = _MARKDOWN_MARKERS_PATTERN.sub("", claim_text).strip()
        if claim_text:
            claims.append(part)
    return claims


def _extract_json_payload(answer_text: str) -> str:
    match = _JSON_FENCE_PATTERN.match(answer_text)
    if match:
        return match.group(1)
    return answer_text


def _parse_structured_claims(answer_text: str) -> list[GroundedClaim] | None:
    try:
        data = json.loads(_extract_json_payload(answer_text))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    raw_claims = data.get("claims")
    if not isinstance(raw_claims, list):
        return None
    claims: list[GroundedClaim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            return None
        text = raw_claim.get("text")
        evidence_refs = raw_claim.get("evidence_refs")
        if not isinstance(text, str) or not isinstance(evidence_refs, list):
            return None
        text = text.strip()
        refs: list[str] = []
        for raw_ref in evidence_refs:
            if not isinstance(raw_ref, str):
                return None
            if raw_ref not in refs:
                refs.append(raw_ref)
        claims.append(GroundedClaim(text=text, evidence_refs=refs))
    return claims


def _blocked_structured_metadata(
    *,
    reason: str,
    allowed_refs: list[str],
    policy: GroundingPolicy = _STRUCTURED_GROUNDING_POLICY,
    structured_claims: list[GroundedClaim] | None = None,
    matched_refs: list[str] | None = None,
    unsupported_refs: list[str] | None = None,
    provider_native_grounding: bool = False,
    tool_name: str | None = None,
    tool_call_count: int = 0,
    semantic_threshold: float | None = None,
    min_semantic_score: float | None = None,
) -> GroundingMetadata:
    claims = structured_claims or []
    return GroundingMetadata(
        status="blocked",
        policy=policy,
        checked=True,
        blocked_reason=reason,
        allowed_evidence_refs=allowed_refs,
        matched_evidence_refs=matched_refs or [],
        unsupported_evidence_refs=unsupported_refs or [],
        claim_count=len(claims),
        cited_claim_count=sum(
            1 for claim in claims if any(ref in allowed_refs for ref in claim.evidence_refs)
        ),
        structured_claims=claims,
        provider_native_grounding=provider_native_grounding,
        tool_name=tool_name,
        tool_call_count=tool_call_count,
        semantic_threshold=semantic_threshold,
        min_semantic_score=min_semantic_score,
    )


def _build_structured_answer(claims: list[GroundedClaim]) -> str:
    sentences: list[str] = []
    for claim in claims:
        refs = " ".join(f"[{ref}]" for ref in claim.evidence_refs)
        text = claim.text.rstrip("。！？!? ")
        sentences.append(f"{text} {refs}。")
    return "".join(sentences)


def evaluate_answer_grounding(
    provider_name: str,
    answer_text: str,
    citations: list[CitationCard],
    *,
    structured_claims: list[GroundedClaim] | None = None,
    policy: GroundingPolicy = _STRUCTURED_GROUNDING_POLICY,
    provider_native_grounding: bool = False,
    tool_name: str | None = None,
    tool_call_count: int = 0,
    blocked_reason: str | None = None,
    semantic_backend: EmbeddingBackend | None = None,
    semantic_threshold: float | None = None,
) -> tuple[str, GroundingMetadata]:
    allowed_refs = build_allowed_evidence_refs(citations)
    if provider_name not in _EXTERNAL_PROVIDER_NAMES:
        return (
            answer_text,
            GroundingMetadata(
                status="skipped",
                policy=policy,
                checked=False,
                allowed_evidence_refs=allowed_refs,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    if policy in _PROVIDER_NATIVE_TOOL_POLICIES and structured_claims is None:
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason=blocked_reason or "missing_tool_use",
                allowed_refs=allowed_refs,
                policy=policy,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    if structured_claims is None:
        structured_claims = _parse_structured_claims(answer_text)
    if structured_claims is None:
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="structured_claims_parse_error",
                allowed_refs=allowed_refs,
                policy=policy,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    if not structured_claims:
        reason = (
            "empty_tool_claims"
            if policy in _PROVIDER_NATIVE_TOOL_POLICIES
            else "empty_structured_claims"
        )
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason=reason,
                allowed_refs=allowed_refs,
                policy=policy,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    matched_refs: list[str] = []
    unsupported_refs: list[str] = []
    for claim in structured_claims:
        for ref in claim.evidence_refs:
            if ref in allowed_refs:
                if ref not in matched_refs:
                    matched_refs.append(ref)
            elif ref not in unsupported_refs:
                unsupported_refs.append(ref)

    if any(not claim.text for claim in structured_claims):
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="blank_claim_text",
                allowed_refs=allowed_refs,
                policy=policy,
                structured_claims=structured_claims,
                matched_refs=matched_refs,
                unsupported_refs=unsupported_refs,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    if any(not claim.evidence_refs for claim in structured_claims):
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="claim_without_evidence_ref",
                allowed_refs=allowed_refs,
                policy=policy,
                structured_claims=structured_claims,
                matched_refs=matched_refs,
                unsupported_refs=unsupported_refs,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    if unsupported_refs:
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="unsupported_evidence_ref",
                allowed_refs=allowed_refs,
                policy=policy,
                structured_claims=structured_claims,
                matched_refs=matched_refs,
                unsupported_refs=unsupported_refs,
                provider_native_grounding=provider_native_grounding,
                tool_name=tool_name,
                tool_call_count=tool_call_count,
            ),
        )

    min_semantic_score: float | None = None
    if semantic_threshold is not None and semantic_backend is not None:
        reference_by_ref = _reference_text_by_ref(citations)
        for claim in structured_claims:
            claim_best = 0.0
            for ref in claim.evidence_refs:
                reference_text = reference_by_ref.get(ref)
                if not reference_text:
                    continue
                claim_best = max(
                    claim_best,
                    score_claim_support(claim.text, reference_text, semantic_backend),
                )
            claim.semantic_score = claim_best
            min_semantic_score = (
                claim_best if min_semantic_score is None else min(min_semantic_score, claim_best)
            )

        if min_semantic_score is not None and min_semantic_score < semantic_threshold:
            return (
                BLOCKED_ANSWER_TEXT,
                _blocked_structured_metadata(
                    reason="semantic_low_support",
                    allowed_refs=allowed_refs,
                    policy=policy,
                    structured_claims=structured_claims,
                    matched_refs=matched_refs,
                    unsupported_refs=unsupported_refs,
                    provider_native_grounding=provider_native_grounding,
                    tool_name=tool_name,
                    tool_call_count=tool_call_count,
                    semantic_threshold=semantic_threshold,
                    min_semantic_score=min_semantic_score,
                ),
            )

    return (
        _build_structured_answer(structured_claims),
        GroundingMetadata(
            status="passed",
            policy=policy,
            checked=True,
            allowed_evidence_refs=allowed_refs,
            matched_evidence_refs=matched_refs,
            claim_count=len(structured_claims),
            cited_claim_count=len(structured_claims),
            structured_claims=structured_claims,
            provider_native_grounding=provider_native_grounding,
            tool_name=tool_name,
            tool_call_count=tool_call_count,
            semantic_threshold=semantic_threshold,
            min_semantic_score=min_semantic_score,
        ),
    )
