from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile, status

from app.schemas.literature import LiteratureItem
from app.schemas.upload import FakePdfAutoParseRequest, StoredUpload
from app.services.fake_parser import auto_parse_uploaded_pdf
from app.services.upload import store_pdf_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/pdf", response_model=StoredUpload, status_code=status.HTTP_201_CREATED)
def upload_pdf_endpoint(
    literature_id: str = Form(),
    file: UploadFile = File(),
) -> StoredUpload:
    try:
        return store_pdf_upload(file, literature_id)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/pdf/auto-parse", response_model=LiteratureItem)
def auto_parse_pdf_endpoint(request: FakePdfAutoParseRequest = Body()) -> LiteratureItem:
    try:
        return auto_parse_uploaded_pdf(request.literature_id, request.file_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
