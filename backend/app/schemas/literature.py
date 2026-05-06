from pydantic import BaseModel


class LiteratureItem(BaseModel):
    id: str
    title: str
    language: str
    source_type: str
    source: str
    year: int
    snippet: str


class LiteratureSearchResponse(BaseModel):
    query: str
    total: int
    items: list[LiteratureItem]
