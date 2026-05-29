import json
import re
from typing import Literal

from app.schemas.rag import CitationCard, GroundedClaim, GroundingMetadata

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
_STRUCTURED_GROUNDING_POLICY: Literal["structured_claim_refs_v3"] = "structured_claim_refs_v3"


def build_allowed_evidence_refs(citations: list[CitationCard]) -> list[str]:
    refs: list[str] = []
    for citation in citations:
        ref = citation.chunk_id or citation.literature_id
        if ref not in refs:
            refs.append(ref)
    return refs


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
    structured_claims: list[GroundedClaim] | None = None,
    matched_refs: list[str] | None = None,
    unsupported_refs: list[str] | None = None,
) -> GroundingMetadata:
    claims = structured_claims or []
    return GroundingMetadata(
        status="blocked",
        policy=_STRUCTURED_GROUNDING_POLICY,
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
) -> tuple[str, GroundingMetadata]:
    allowed_refs = build_allowed_evidence_refs(citations)
    if provider_name not in _EXTERNAL_PROVIDER_NAMES:
        return (
            answer_text,
            GroundingMetadata(
                status="skipped",
                policy=_STRUCTURED_GROUNDING_POLICY,
                checked=False,
                allowed_evidence_refs=allowed_refs,
            ),
        )

    structured_claims = _parse_structured_claims(answer_text)
    if structured_claims is None:
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="structured_claims_parse_error",
                allowed_refs=allowed_refs,
            ),
        )

    if not structured_claims:
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="empty_structured_claims",
                allowed_refs=allowed_refs,
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
                structured_claims=structured_claims,
                matched_refs=matched_refs,
                unsupported_refs=unsupported_refs,
            ),
        )

    if any(not claim.evidence_refs for claim in structured_claims):
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="claim_without_evidence_ref",
                allowed_refs=allowed_refs,
                structured_claims=structured_claims,
                matched_refs=matched_refs,
                unsupported_refs=unsupported_refs,
            ),
        )

    if unsupported_refs:
        return (
            BLOCKED_ANSWER_TEXT,
            _blocked_structured_metadata(
                reason="unsupported_evidence_ref",
                allowed_refs=allowed_refs,
                structured_claims=structured_claims,
                matched_refs=matched_refs,
                unsupported_refs=unsupported_refs,
            ),
        )

    return (
        _build_structured_answer(structured_claims),
        GroundingMetadata(
            status="passed",
            policy=_STRUCTURED_GROUNDING_POLICY,
            checked=True,
            allowed_evidence_refs=allowed_refs,
            matched_evidence_refs=matched_refs,
            claim_count=len(structured_claims),
            cited_claim_count=len(structured_claims),
            structured_claims=structured_claims,
        ),
    )
