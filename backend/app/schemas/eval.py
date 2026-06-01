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
    provider_name: str
    grounding_status: str
    passed: bool


class RagEvalSummary(BaseModel):
    total_questions: int
    passed_questions: int
    pass_rate: float
    citation_hit_count: int
    chunk_hit_count: int
    disclaimer_coverage_count: int
    must_not_violation_count: int
    grounding_blocked_count: int = 0
    provider_name: str
    retrieval_strategy: str = "keyword"


class RagEvalReport(BaseModel):
    summary: RagEvalSummary
    items: list[RagEvalItemResult]


class GroundingSemanticPair(BaseModel):
    id: str
    claim: str = Field(min_length=1)
    chunk_text: str = Field(min_length=1)
    supported: bool
    note: str = ""


def load_rag_eval_dataset(data_path: Path) -> list[RagEvalQuestion]:
    raw_items = json.loads(data_path.read_text(encoding="utf-8"))
    return [RagEvalQuestion(**item) for item in raw_items]


def load_grounding_semantic_pairs(data_path: Path) -> list[GroundingSemanticPair]:
    raw_items = json.loads(data_path.read_text(encoding="utf-8"))
    return [GroundingSemanticPair(**item) for item in raw_items]


class RealAnswerPair(BaseModel):
    """A labeled claim-premise pair from the real-answer validation set (Slice 2)."""

    claim: str = Field(min_length=1)
    premise: str = Field(min_length=1)
    premise_chunk_id: str = ""
    premise_literature_id: str = ""
    support_label: str = Field(default="unsupported")  # supported | partial | unsupported
    source: str = ""
    semantic_score_bge: float | None = None
    label_note: str = ""


def load_real_answer_pairs(data_path: Path) -> list[RealAnswerPair]:
    raw_items = json.loads(data_path.read_text(encoding="utf-8"))
    return [RealAnswerPair(**item) for item in raw_items]


class CrossLingualRetrievalItem(BaseModel):
    """Per-question cross-lingual retrieval metrics."""

    id: str
    question: str
    source_preference: str
    question_language: str  # "zh" | "en"
    expected_cn_ids: list[str]  # expected cn-* literature IDs
    expected_pubmed_ids: list[str]  # expected pmid-* literature IDs
    top_k: int
    retrieved_ids: list[str]  # top-k unique literature IDs from rank()
    cn_hit_count: int  # cn-* hits in retrieved
    pubmed_hit_count: int  # pmid-* hits in retrieved
    monolingual_recall: float  # same-language recall
    cross_lingual_recall: float  # cross-language recall
    language_diversity: float  # min(cn,pubmed) / max(cn,pubmed,1)
    mean_reciprocal_rank: float  # MRR of first expected hit
    precision_at_k: float  # expected hits / top_k


class CrossLingualRetrievalSummary(BaseModel):
    """Aggregated cross-lingual retrieval metrics."""

    total_questions: int
    top_k: int
    retrieval_strategy: str
    avg_monolingual_recall: float
    avg_cross_lingual_recall: float
    avg_language_diversity: float
    avg_precision_at_k: float
    avg_mrr: float


class CrossLingualRetrievalReport(BaseModel):
    """Full cross-lingual retrieval evaluation report."""

    summary: CrossLingualRetrievalSummary
    items: list[CrossLingualRetrievalItem]
