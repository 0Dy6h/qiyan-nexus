from fastapi import APIRouter, Query

from app.schemas.literature import LiteratureSearchResponse

router = APIRouter(prefix="/api/literature", tags=["literature"])


@router.get("/search", response_model=LiteratureSearchResponse)
def search_literature(q: str = Query(min_length=1)) -> LiteratureSearchResponse:
    items = [
        {
            "id": "cn-ad-gbs-001",
            "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
            "language": "zh",
            "source": "中文本地样本文献库",
            "year": 2025,
            "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
        },
        {
            "id": "en-ad-barrier-001",
            "title": "Atopic dermatitis, skin barrier dysfunction, and immune pathways",
            "language": "en",
            "source": "PubMed sample",
            "year": 2024,
            "snippet": "A sample English literature record for AD barrier and immune pathway retrieval.",
        },
    ]
    return LiteratureSearchResponse(query=q, total=len(items), items=items)
