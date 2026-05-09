import json
from pathlib import Path

from pydantic import BaseModel, Field


class RagEvalQuestion(BaseModel):
    id: str
    question: str = Field(min_length=1)
    source_preference: str
    difficulty: str
    expected_literature_ids: list[str]
    expected_chunk_ids: list[str]
    must_include: list[str]
    must_not_include: list[str]
    compliance_notes: str


class RagEvalDataset(BaseModel):
    items: list[RagEvalQuestion]


def load_rag_eval_dataset(data_path: Path) -> list[RagEvalQuestion]:
    raw_items = json.loads(data_path.read_text(encoding="utf-8"))
    return [RagEvalQuestion(**item) for item in raw_items]
