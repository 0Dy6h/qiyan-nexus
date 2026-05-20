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


class RetrievalMetadata(BaseModel):
    applied_source: Literal["all", "cn_literature", "pubmed"]
    applied_top_k: int
    available_citation_count: int


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
