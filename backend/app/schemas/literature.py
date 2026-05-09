from pydantic import BaseModel, Field


class LiteratureItem(BaseModel):
    id: str
    title: str
    language: str
    source_type: str
    source: str
    year: int
    snippet: str
    authors: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    evidence_tags: list[str] = Field(default_factory=list)
    abstract: str | None = None
    citation_url: str | None = None
    pubmed_id: str | None = None
    doi: str | None = None
    pdf_upload_id: str | None = None
    pdf_file_name: str | None = None
    pdf_parse_status: str | None = None


class LiteratureSearchResponse(BaseModel):
    query: str
    total: int
    items: list[LiteratureItem]
