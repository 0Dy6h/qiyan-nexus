from fastapi import UploadFile

from app.core.config import get_settings
from app.schemas.upload import StoredUpload
from app.services.literature import attach_pdf_metadata, build_pdf_upload_id, get_literature_item
from app.services.pdf_storage import build_storage_path, resolve_stored_pdf_path



def store_pdf_upload(file: UploadFile, literature_id: str) -> StoredUpload:
    if file.content_type != "application/pdf":
        raise ValueError("Only PDF uploads are supported")
    if get_literature_item(literature_id) is None:
        raise LookupError("Literature item not found")

    contents = file.file.read()
    storage_dir = get_settings().upload_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_name = file.filename or "upload.pdf"
    pdf_upload_id = build_pdf_upload_id(literature_id, file_name)
    storage_path = build_storage_path(storage_dir, pdf_upload_id, file_name)
    storage_path.write_bytes(contents)

    item = attach_pdf_metadata(literature_id, file_name)
    if item is None:
        storage_path.unlink(missing_ok=True)
        raise LookupError("Literature item not found")

    return StoredUpload(
        literature_id=literature_id,
        pdf_upload_id=pdf_upload_id,
        file_name=file_name,
        content_type=file.content_type,
        file_size=len(contents),
        storage_path=str(storage_path),
        pdf_parse_status=item.pdf_parse_status or "pending",
    )
