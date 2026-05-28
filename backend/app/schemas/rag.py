from typing import Literal

from pydantic import BaseModel, Field


class CitationCard(BaseModel):
    literature_id: str
    chunk_id: str | None = None
    title: str
    source: str
    snippet: str
    quote: str | None = None
    reason: str | None = None
    confidence: float
    source_type: str | None = None
    pdf_upload_id: str | None = None
    related_entity_ids: list[str] = Field(default_factory=list)


class RetrievalMetadata(BaseModel):
    applied_source: Literal["all", "cn_literature", "pubmed"]
    applied_top_k: int
    available_citation_count: int
    strategy: str = "keyword"


class GroundedClaim(BaseModel):
    text: str
    evidence_refs: list[str] = Field(default_factory=list)


class GroundingMetadata(BaseModel):
    status: Literal["skipped", "passed", "blocked"]
    policy: Literal["hard_block_v2_sentence_refs", "structured_claim_refs_v3"] = (
        "hard_block_v2_sentence_refs"
    )
    checked: bool
    blocked_reason: str | None = None
    allowed_evidence_refs: list[str] = Field(default_factory=list)
    matched_evidence_refs: list[str] = Field(default_factory=list)
    unsupported_evidence_refs: list[str] = Field(default_factory=list)
    claim_count: int = 0
    cited_claim_count: int = 0
    structured_claims: list[GroundedClaim] = Field(default_factory=list)


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    source: Literal["all", "cn_literature", "pubmed"] = "all"
    top_k: int = Field(default=2, ge=1)


class RagAnswerResponse(BaseModel):
    question: str
    answer: str
    disclaimer: str
    retrieval: RetrievalMetadata
    citations: list[CitationCard]
    answered_at: str
    provider_name: str
    grounding: GroundingMetadata
    input_tokens: int | None = None
    output_tokens: int | None = None
