from pydantic import BaseModel


class LiteratureItem(BaseModel):
    id: str
    title: str
    language: str
    source_type: str
    source: str
    year: int
    snippet: str
    authors: list[str] = []
    keywords: list[str] = []
    evidence_tags: list[str] = []
    abstract: str | None = None
    citation_url: str | None = None
    pubmed_id: str | None = None
    doi: str | None = None


class LiteratureSearchResponse(BaseModel):
    query: str
    total: int
    items: list[LiteratureItem]
