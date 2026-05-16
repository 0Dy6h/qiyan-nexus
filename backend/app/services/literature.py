import re
from datetime import UTC, datetime
from pathlib import Path

from app.repositories.literature import InMemoryLiteratureRepository
from app.schemas.literature import (
    LiteratureItem,
    LiteratureSearchResponse,
    LiteratureSearchSort,
    LiteratureSource,
    PdfParseResult,
)
from app.services.pdf_storage import resolve_stored_pdf_path

_SAMPLE_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
)
_REPOSITORY = InMemoryLiteratureRepository(_SAMPLE_DATA_PATH)
DEFAULT_SEARCH_PAGE_SIZE = 10
MAX_SEARCH_PAGE_SIZE = 50

_SEARCH_ALIASES = {
    "disease": ["特应性皮炎", "atopic dermatitis", "atopic", "dermatitis", "ad"],
    "gut_skin_axis": [
        "肠",
        "肠道",
        "肠道菌群",
        "肠-脑-皮肤轴",
        "gut",
        "gut-skin",
        "microbiome",
        "菌群",
    ],
    "skin_barrier": ["屏障", "皮肤屏障", "barrier", "filaggrin", "ceramide"],
    "immune": ["免疫", "炎症", "inflammation", "immune", "th2", "jak", "cytokine"],
    "pruritus": ["瘙痒", "itch", "itching", "il-31", "pruritus"],
    "formula": ["复方", "方剂", "中药", "formula", "herbal", "消风散"],
    "network": ["网络药理学", "靶点", "通路", "network pharmacology", "target", "pathway"],
    "pediatric": ["儿童", "pediatric", "children"],
}
_DISEASE_TERMS = {term.lower() for term in _SEARCH_ALIASES["disease"]}


def _english_term_matches(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _keyword_in_text(text: str, keyword: str) -> bool:
    keyword = keyword.lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9\-]*", keyword):
        return _english_term_matches(text, keyword)
    return keyword in text


def tokenize_search_query(query: str) -> list[str]:
    normalized = query.lower().strip()
    terms = set(re.findall(r"[a-z0-9][a-z0-9\-]*", normalized))
    terms.update(re.findall(r"[\u4e00-\u9fff]+", normalized))

    for alias_terms in _SEARCH_ALIASES.values():
        if any(_keyword_in_text(normalized, keyword) for keyword in alias_terms):
            terms.update(alias_terms)

    return sorted((term for term in terms if term), key=lambda term: (-len(term), term))


def _is_broad_disease_query(query_terms: list[str]) -> bool:
    return bool(query_terms) and all(term.lower() in _DISEASE_TERMS for term in query_terms)


def _build_search_haystacks(item: LiteratureItem) -> list[tuple[str, int]]:
    evidence_tags = " ".join(
        item.evidence_tags + [tag.replace("_", " ") for tag in item.evidence_tags]
    )
    return [
        (item.title.lower(), 4),
        (" ".join(item.keywords).lower(), 3),
        (evidence_tags.lower(), 2),
        (item.snippet.lower(), 2),
        ((item.abstract or "").lower(), 1),
        (" ".join(item.authors).lower(), 1),
    ]


def score_literature_item(item: LiteratureItem, query_terms: list[str]) -> int:
    score = 0
    for haystack, weight in _build_search_haystacks(item):
        if not haystack:
            continue
        for term in query_terms:
            if _keyword_in_text(haystack, term):
                score += weight
    return score


def _sort_scored_items(
    scored_items: list[tuple[int, int, int, LiteratureItem]],
    sort: LiteratureSearchSort,
    is_broad_disease_query: bool,
) -> list[LiteratureItem]:
    if sort == "year_desc":
        scored_items.sort(key=lambda row: (row[3].year, row[0], row[1], -row[2]), reverse=True)
    elif sort == "year_asc":
        scored_items.sort(key=lambda row: (row[3].year, -row[0], -row[1], row[2]))
    elif is_broad_disease_query:
        scored_items.sort(key=lambda row: (row[1], -row[2]), reverse=True)
    else:
        scored_items.sort(key=lambda row: (row[1], row[0], row[3].year, -row[2]), reverse=True)
    return [item for _, _, _, item in scored_items]


def detect_query_language(query: str) -> str:
    for char in query:
        if "\u4e00" <= char <= "\u9fff":
            return "zh"
    return "en"


def search_literature(
    query: str,
    source: LiteratureSource = "all",
    page: int = 1,
    page_size: int = DEFAULT_SEARCH_PAGE_SIZE,
    sort: LiteratureSearchSort = "relevance",
) -> LiteratureSearchResponse:
    normalized_query = query.strip()
    query_language = detect_query_language(normalized_query)
    preferred_source_type = "cn_literature" if query_language == "zh" else "pubmed"
    query_terms = tokenize_search_query(normalized_query)
    items = _REPOSITORY.list_items()
    if source != "all":
        items = [item for item in items if item.source_type == source]
    scored_items = [
        (score, 1 if item.source_type == preferred_source_type else 0, index, item)
        for index, item in enumerate(items)
        if (score := score_literature_item(item, query_terms)) > 0
    ]
    items = _sort_scored_items(scored_items, sort, _is_broad_disease_query(query_terms))
    total = len(items)
    normalized_page = max(page, 1)
    normalized_page_size = min(max(page_size, 1), MAX_SEARCH_PAGE_SIZE)
    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    paged_items = items[start:end]
    total_pages = (total + normalized_page_size - 1) // normalized_page_size if total else 0
    return LiteratureSearchResponse(
        query=normalized_query,
        source=source,
        page=normalized_page,
        page_size=normalized_page_size,
        total=total,
        total_pages=total_pages,
        sort=sort,
        items=paged_items,
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


def build_parse_metadata(pdf_parse_status: str) -> tuple[str, str, str]:
    started_at = datetime.now(UTC).isoformat()
    finished_at = datetime.now(UTC).isoformat()
    if pdf_parse_status == "failed":
        return "Mock parser flagged file as failed", started_at, finished_at
    return "Mock parser completed successfully", started_at, finished_at


def build_pdf_parse_result(item: LiteratureItem) -> PdfParseResult | None:
    if item.pdf_parse_status != "parsed" or not item.pdf_upload_id or not item.pdf_file_name:
        return None
    storage_path = resolve_stored_pdf_path(item.pdf_upload_id)
    if storage_path is None:
        return None
    return PdfParseResult(
        file_name=item.pdf_file_name,
        storage_path=str(storage_path),
        file_size=storage_path.stat().st_size,
        preview_text="已读取上传 PDF 文件，当前提供文件级解析预览；正文抽取将在后续接入。",
        extraction_method="file-metadata-placeholder",
    )


def update_pdf_parse_status(
    literature_id: str,
    pdf_parse_status: str,
    trigger: str = "manual",
) -> tuple[str, LiteratureItem | None]:
    item = _REPOSITORY.get_item_by_id(literature_id)
    if item is None:
        return "not_found", None
    if not item.pdf_upload_id or not item.pdf_file_name:
        return "missing_metadata", None
    pdf_parse_message, pdf_parse_started_at, pdf_parse_finished_at = build_parse_metadata(
        pdf_parse_status
    )
    next_item = LiteratureItem(
        **{
            **item.model_dump(),
            "pdf_parse_status": pdf_parse_status,
        }
    )
    return "ok", _REPOSITORY.update_pdf_parse_status(
        literature_id,
        pdf_parse_status,
        pdf_parse_message=pdf_parse_message,
        pdf_parse_started_at=pdf_parse_started_at,
        pdf_parse_finished_at=pdf_parse_finished_at,
        pdf_parse_result=build_pdf_parse_result(next_item),
        last_parse_trigger=trigger,
    )
