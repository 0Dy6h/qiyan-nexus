from typing import Literal

from pydantic import BaseModel, Field

AnalysisType = Literal["formula", "herb"]
TaskStatus = Literal["queued", "running", "completed"]


class NetworkAnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    analysis_type: AnalysisType = "formula"


class NetworkAnalyzeAccepted(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)


class NetworkChain(BaseModel):
    herb: str
    formula: str | None = None
    compound: str
    target: str
    pathway: str
    disease: str
    score: float = Field(ge=0, le=1)
    related_entity_ids: list[str] = Field(default_factory=list)


class EnrichmentTerm(BaseModel):
    term_id: str
    term_name: str
    term_name_zh: str | None = None
    category: str
    gene_count: int
    overlap_count: int
    p_value: float
    adjusted_p_value: float
    genes: list[str]


class EnrichmentResult(BaseModel):
    analysis_type: str
    input_gene_count: int
    background_gene_count: int
    terms: list[EnrichmentTerm]
    timestamp: str


class NetworkAnalysisResult(BaseModel):
    task_id: str
    query: str
    analysis_type: AnalysisType
    chains: list[NetworkChain]
    enrichment: EnrichmentResult | None = None
    disclaimer: str


class NetworkResultResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    result: NetworkAnalysisResult | None = None


class NetworkTaskRecord(BaseModel):
    task_id: str
    query: str
    analysis_type: AnalysisType
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    poll_count: int = Field(ge=0)
    result: NetworkAnalysisResult | None = None
    created_at: str
