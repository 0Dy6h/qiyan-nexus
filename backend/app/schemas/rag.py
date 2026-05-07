from typing import Literal

from pydantic import BaseModel, Field


class CitationCard(BaseModel):
    literature_id: str
    title: str
    source: str
    snippet: str
    confidence: float


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    source: Literal["all", "cn_literature", "pubmed"] = "all"
    top_k: int = Field(default=2, ge=1)


class RagAnswerResponse(BaseModel):
    question: str
    answer: str
    disclaimer: str
    citations: list[CitationCard]
