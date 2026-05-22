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
    compound: str
    target: str
    pathway: str
    disease: str
    score: float = Field(ge=0, le=1)


class NetworkAnalysisResult(BaseModel):
    task_id: str
    query: str
    analysis_type: AnalysisType
    chains: list[NetworkChain]
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
