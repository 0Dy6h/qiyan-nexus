import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.schemas.literature import LiteratureSource


class RagEvalQuestion(BaseModel):
    id: str
    question: str = Field(min_length=1)
    source_preference: LiteratureSource
    difficulty: str
    expected_literature_ids: list[str]
    expected_chunk_ids: list[str]
    must_include: list[str]
    must_not_include: list[str]
    compliance_notes: str


class RagEvalDataset(BaseModel):
    items: list[RagEvalQuestion]


class RagEvalItemResult(BaseModel):
    id: str
    question: str
    source_preference: LiteratureSource
    difficulty: str
    expected_literature_ids: list[str]
    expected_literature_hits: list[str]
    expected_chunk_ids: list[str]
    expected_chunk_hits: list[str]
    missing_must_include: list[str]
    violated_must_not_include: list[str]
    disclaimer_present: bool
    citation_count: int
    passed: bool


class RagEvalSummary(BaseModel):
    total_questions: int
    passed_questions: int
    pass_rate: float
    citation_hit_count: int
    chunk_hit_count: int
    disclaimer_coverage_count: int
    must_not_violation_count: int


class RagEvalReport(BaseModel):
    summary: RagEvalSummary
    items: list[RagEvalItemResult]


def load_rag_eval_dataset(data_path: Path) -> list[RagEvalQuestion]:
    raw_items = json.loads(data_path.read_text(encoding="utf-8"))
    return [RagEvalQuestion(**item) for item in raw_items]
