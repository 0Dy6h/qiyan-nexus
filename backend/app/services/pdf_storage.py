import re
from pathlib import Path

from app.core.config import get_settings

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
