from app.schemas.literature import LiteratureSearchResponse

_SAMPLE_ITEMS = [
    {
        "id": "cn-ad-gbs-001",
        "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
        "language": "zh",
        "source_type": "cn_literature",
        "source": "中文本地样本文献库",
        "year": 2025,
        "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
    },
    {
        "id": "en-ad-barrier-001",
        "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
        "language": "en",
        "source_type": "pubmed",
        "source": "PubMed sample",
        "year": 2024,
        "snippet": "A sample English literature record for AD barrier and immune pathway retrieval.",
    },
]


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
        _SAMPLE_ITEMS,
        key=lambda item: item["source_type"] != preferred_source_type,
    )
    if source != "all":
        items = [item for item in items if item["source_type"] == source]
    return LiteratureSearchResponse(
        query=normalized_query,
        total=len(items),
        items=items,
    )
