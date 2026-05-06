from fastapi import APIRouter, Query

from app.schemas.literature import LiteratureSearchResponse
from app.services.literature import search_literature

router = APIRouter(prefix="/api/literature", tags=["literature"])


@router.get("/search", response_model=LiteratureSearchResponse)
def search_literature_endpoint(q: str = Query(min_length=1)) -> LiteratureSearchResponse:
    return search_literature(q)
