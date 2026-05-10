from pydantic import BaseModel, Field


class LiteratureChunk(BaseModel):
    chunk_id: str
    literature_id: str
    section: str
    text: str
    source_quote: str
    evidence_tags: list[str] = Field(default_factory=list)
    related_entity_ids: list[str] = Field(default_factory=list)
    source_type: str = "sample"
    pdf_upload_id: str | None = None
