from fastapi import APIRouter, Body, HTTPException, Query

from app.schemas.literature import (
    LiteratureItem,
    LiteratureSearchSort,
    LiteratureSearchResponse,
    LiteratureSource,
    PdfMetadataUploadRequest,
    PdfParseStatusUpdateRequest,
)
from app.services.literature import attach_pdf_metadata, get_literature_item, search_literature, update_pdf_parse_status

router = APIRouter(prefix="/api/literature", tags=["literature"])


@router.get("/search", response_model=LiteratureSearchResponse)
def search_literature_endpoint(
    q: str = Query(min_length=1),
    source: LiteratureSource = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    sort: LiteratureSearchSort = "relevance",
) -> LiteratureSearchResponse:
    return search_literature(q, source=source, page=page, page_size=page_size, sort=sort)


@router.post("/pdf-metadata", response_model=LiteratureItem)
def upload_pdf_metadata_endpoint(request: PdfMetadataUploadRequest = Body()) -> LiteratureItem:
    item = attach_pdf_metadata(request.literature_id, request.file_name)
    if item is None:
        raise HTTPException(status_code=404, detail="Literature item not found")
    return item


@router.post("/pdf-parse-status", response_model=LiteratureItem)
def update_pdf_parse_status_endpoint(request: PdfParseStatusUpdateRequest = Body()) -> LiteratureItem:
    status, item = update_pdf_parse_status(request.literature_id, request.pdf_parse_status)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Literature item not found")
    if status == "missing_metadata":
        raise HTTPException(status_code=409, detail="PDF metadata not attached")
    return item


@router.get("/{item_id}", response_model=LiteratureItem)
def get_literature_item_endpoint(item_id: str) -> LiteratureItem:
    item = get_literature_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Literature item not found")
    return item
