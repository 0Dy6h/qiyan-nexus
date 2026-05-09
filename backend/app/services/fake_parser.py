from app.schemas.literature import LiteratureItem
from app.services.literature import update_pdf_parse_status


def resolve_fake_parse_status(file_name: str) -> str:
    return "failed" if "fail" in file_name.lower() else "parsed"


def auto_parse_uploaded_pdf(literature_id: str, file_name: str) -> LiteratureItem:
    status, item = update_pdf_parse_status(literature_id, resolve_fake_parse_status(file_name), trigger="auto")
    if status == "not_found":
        raise LookupError("Literature item not found")
    if status == "missing_metadata":
        raise ValueError("PDF metadata not attached")
    if item is None:
        raise LookupError("Literature item not found")
    return item
