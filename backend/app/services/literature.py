import re
from pathlib import Path

from app.repositories.literature import InMemoryLiteratureRepository
from app.schemas.literature import LiteratureItem, LiteratureSearchResponse

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


def get_literature_item(item_id: str) -> LiteratureItem | None:
    return _REPOSITORY.get_item_by_id(item_id)


def build_pdf_upload_id(literature_id: str, file_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", file_name.lower()).strip("-")
    return f"pdf-{literature_id}-{slug}"


def attach_pdf_metadata(literature_id: str, file_name: str) -> LiteratureItem | None:
    return _REPOSITORY.update_pdf_metadata(
        literature_id=literature_id,
        pdf_upload_id=build_pdf_upload_id(literature_id, file_name),
        pdf_file_name=file_name,
        pdf_parse_status="pending",
    )


def update_pdf_parse_status(literature_id: str, pdf_parse_status: str) -> tuple[str, LiteratureItem | None]:
    item = _REPOSITORY.get_item_by_id(literature_id)
    if item is None:
        return "not_found", None
    if not item.pdf_upload_id or not item.pdf_file_name:
        return "missing_metadata", None
    return "ok", _REPOSITORY.update_pdf_parse_status(literature_id, pdf_parse_status)
