from pydantic import BaseModel, Field


class CitationCard(BaseModel):
    literature_id: str
    title: str
    source: str
    snippet: str
    confidence: float


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1)


class RagAnswerResponse(BaseModel):
    question: str
    answer: str
    disclaimer: str
    citations: list[CitationCard]
