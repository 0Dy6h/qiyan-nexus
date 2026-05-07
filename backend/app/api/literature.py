from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.schemas.literature import LiteratureItem, LiteratureSearchResponse
from app.services.literature import get_literature_item, search_literature

router = APIRouter(prefix="/api/literature", tags=["literature"])


@router.get("/search", response_model=LiteratureSearchResponse)
def search_literature_endpoint(
    q: str = Query(min_length=1),
    source: Literal["all", "cn_literature", "pubmed"] = "all",
) -> LiteratureSearchResponse:
    return search_literature(q, source=source)


@router.get("/{item_id}", response_model=LiteratureItem)
def get_literature_item_endpoint(item_id: str) -> LiteratureItem:
    item = get_literature_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Literature item not found")
    return item
