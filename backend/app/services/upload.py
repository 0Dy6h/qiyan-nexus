from pathlib import Path
import re

from fastapi import UploadFile

from app.core.config import get_settings
from app.schemas.upload import StoredUpload
from app.services.literature import attach_pdf_metadata, build_pdf_upload_id, get_literature_item


_PDF_UPLOAD_ID_PATTERN = re.compile(r"^pdf-[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def build_storage_path(storage_dir: Path, pdf_upload_id: str, file_name: str) -> Path:
    return storage_dir / f"{pdf_upload_id}.pdf"


def resolve_stored_pdf_path(pdf_upload_id: str) -> Path | None:
    if not _PDF_UPLOAD_ID_PATTERN.fullmatch(pdf_upload_id):
        return None

    storage_dir = get_settings().upload_storage_dir.resolve()
    storage_path = (storage_dir / f"{pdf_upload_id}.pdf").resolve()
    if storage_path.parent != storage_dir:
        return None
    if not storage_path.is_file():
        return None
    return storage_path


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
