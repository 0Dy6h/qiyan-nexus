from typing import Literal

from pydantic import BaseModel, Field

AnalysisType = Literal["formula", "herb"]
TaskStatus = Literal["queued", "running", "completed", "failed"]
DataMode = Literal["mock", "live"]
PipelineStepStatus = Literal["completed", "failed", "skipped", "degraded"]
TargetEvidenceType = Literal["mock", "known_activity", "predicted", "mixed"]
EvidenceLevel = Literal[
    "mock_inferred",
    "predicted",
    "literature_supported",
    "experimental",
]


class NetworkAnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    analysis_type: AnalysisType = "formula"


class NetworkAnalyzeAccepted(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    data_mode: DataMode = "mock"


class NetworkDataSource(BaseModel):
    name: str
    source_record_id: str | None = None
    url: str | None = None
    retrieved_at: str | None = None
    license_note: str | None = None
    cache_key: str | None = None
    from_cache: bool = False


class NetworkPipelineStep(BaseModel):
    name: str
    status: PipelineStepStatus
    duration_ms: int = Field(default=0, ge=0)
    external_request_count: int = Field(default=0, ge=0)
    cache_hit_count: int = Field(default=0, ge=0)
    warning: str | None = None


class NetworkChain(BaseModel):
    herb: str
    formula: str | None = None
    compound: str
    target: str
    pathway: str
    disease: str
    score: float = Field(ge=0, le=1)
    related_entity_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    target_evidence_type: TargetEvidenceType = "mock"
    evidence_level: EvidenceLevel | None = None


class NetworkPpiEdge(BaseModel):
    source: str
    target: str
    score: float = Field(ge=0, le=1)
    source_record_id: str


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
    data_mode: DataMode = "mock"
    chains: list[NetworkChain]
    enrichment: EnrichmentResult | None = None
    pipeline_steps: list[NetworkPipelineStep] = Field(default_factory=list)
    data_sources: list[NetworkDataSource] = Field(default_factory=list)
    ppi_edges: list[NetworkPpiEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str


class NetworkResultResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    data_mode: DataMode = "mock"
    result: NetworkAnalysisResult | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


class NetworkTaskRecord(BaseModel):
    task_id: str
    query: str
    analysis_type: AnalysisType
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    poll_count: int = Field(ge=0)
    data_mode: DataMode = "mock"
    result: NetworkAnalysisResult | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: str
