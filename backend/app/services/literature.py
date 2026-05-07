from pathlib import Path

from app.repositories.literature import InMemoryLiteratureRepository
from app.schemas.literature import LiteratureSearchResponse

_SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
_REPOSITORY = InMemoryLiteratureRepository(_SAMPLE_DATA_PATH)


def detect_query_language(query: str) -> str:
    for char in query:
        if "\u4e00" <= char <= "\u9fff":
            return "zh"
    return "en"


def search_literature(query: str, source: str = "all") -> LiteratureSearchResponse:
    normalized_query = query.strip()
    query_language = detect_query_language(normalized_query)
    preferred_source_type = "cn_literature" if query_language == "zh" else "pubmed"
    items = sorted(
        _REPOSITORY.list_items(),
        key=lambda item: item.source_type != preferred_source_type,
    )
    if source != "all":
        items = [item for item in items if item.source_type == source]
    return LiteratureSearchResponse(
        query=normalized_query,
        total=len(items),
        items=items,
    )
