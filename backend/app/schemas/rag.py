from typing import Literal

from pydantic import BaseModel, Field

GroundingPolicy = Literal[
    "structured_claim_refs_v3", "anthropic_tool_use_v1", "opencode_go_tool_use_v1"
]


class CitationCard(BaseModel):
    literature_id: str
    chunk_id: str | None = None
    title: str
    source: str
    snippet: str
    quote: str | None = None
    reason: str | None = None
    confidence: float
    match_score: float | None = None
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
    semantic_score: float | None = None
    entailment_score: float | None = None


class GroundingMetadata(BaseModel):
    status: Literal["skipped", "passed", "blocked"]
    policy: GroundingPolicy = "structured_claim_refs_v3"
    checked: bool
    blocked_reason: str | None = None
    allowed_evidence_refs: list[str] = Field(default_factory=list)
    matched_evidence_refs: list[str] = Field(default_factory=list)
    unsupported_evidence_refs: list[str] = Field(default_factory=list)
    claim_count: int = 0
    cited_claim_count: int = 0
    structured_claims: list[GroundedClaim] = Field(default_factory=list)
    provider_native_grounding: bool = False
    tool_name: str | None = None
    tool_call_count: int = 0
    semantic_threshold: float | None = None
    min_semantic_score: float | None = None
    nli_threshold: float | None = None
    min_entailment_score: float | None = None


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    source: Literal["all", "cn_literature", "pubmed"] = "all"
    top_k: int = Field(default=2, ge=1)


class ProviderSli(BaseModel):
    """Service-level indicators for the LLM provider call.

    ``provider_latency_ms`` wraps only the ``generate_answer`` call (retrieval and
    grounding are local and cheap). ``estimated_cost_usd`` is derived from token
    usage and operator-configured per-million-token prices; it stays ``None`` when
    token usage is missing (deterministic / fallback) or prices are unset, so we
    never surface a guessed price.
    """

    provider_latency_ms: int | None = None
    estimated_cost_usd: float | None = None


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
    sli: ProviderSli | None = None
    integrity_token: str | None = None
