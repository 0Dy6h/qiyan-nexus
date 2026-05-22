import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def reset_sample_data(original_path: Path, temp_path: Path) -> None:
    temp_path.write_text(original_path.read_text(encoding="utf-8"), encoding="utf-8")


def test_pdf_parse_status_endpoint_updates_existing_pending_record(monkeypatch, tmp_path: Path):
    from app.services import literature as literature_service

    original_path = (
        Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
    )
    temp_path = tmp_path / "sample_ad_literature.json"
    reset_sample_data(original_path, temp_path)

    repository = literature_service.InMemoryLiteratureRepository(temp_path)
    repository.update_pdf_metadata(
        literature_id="cn-ad-gbs-001",
        pdf_upload_id="pdf-cn-ad-gbs-001-ad-evidence-pdf",
        pdf_file_name="ad-evidence.pdf",
        pdf_parse_status="pending",
    )

    monkeypatch.setattr(literature_service, "_REPOSITORY", repository)

    client = TestClient(app)

    response = client.post(
        "/api/literature/pdf-parse-status",
        json={
            "literature_id": "cn-ad-gbs-001",
            "pdf_parse_status": "parsed",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pdf_upload_id"] == "pdf-cn-ad-gbs-001-ad-evidence-pdf"
    assert payload["pdf_file_name"] == "ad-evidence.pdf"
    assert payload["pdf_parse_status"] == "parsed"

    persisted = json.loads(temp_path.read_text(encoding="utf-8"))
    first = next(item for item in persisted if item["id"] == "cn-ad-gbs-001")
    assert first["pdf_parse_status"] == "parsed"


def test_pdf_parse_status_endpoint_returns_real_file_parse_result_fields(
    monkeypatch, tmp_path: Path
):
    from app.services import literature as literature_service

    original_path = (
        Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
    )
    temp_path = tmp_path / "sample_ad_literature.json"
    reset_sample_data(original_path, temp_path)

    storage_dir = tmp_path / "uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / "pdf-cn-ad-gbs-001-ad-evidence-pdf.pdf"
    storage_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n")

    repository = literature_service.InMemoryLiteratureRepository(temp_path)
    repository.update_pdf_metadata(
        literature_id="cn-ad-gbs-001",
        pdf_upload_id="pdf-cn-ad-gbs-001-ad-evidence-pdf",
        pdf_file_name="ad-evidence.pdf",
        pdf_parse_status="pending",
    )

    monkeypatch.setattr(literature_service, "_REPOSITORY", repository)
    monkeypatch.setattr(
        literature_service, "resolve_stored_pdf_path", lambda pdf_upload_id: storage_path
    )

    client = TestClient(app)

    response = client.post(
        "/api/literature/pdf-parse-status",
        json={
            "literature_id": "cn-ad-gbs-001",
            "pdf_parse_status": "parsed",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pdf_parse_result"] == {
        "file_name": "ad-evidence.pdf",
        "storage_path": str(storage_path),
        "file_size": storage_path.stat().st_size,
        "preview_text": "已读取上传 PDF 文件，当前提供文件级解析预览；正文抽取将在后续接入。",
        "extraction_method": "file-metadata-placeholder",
    }

    persisted = json.loads(temp_path.read_text(encoding="utf-8"))
    first = next(item for item in persisted if item["id"] == "cn-ad-gbs-001")
    assert first["pdf_parse_result"] == {
        "file_name": "ad-evidence.pdf",
        "storage_path": str(storage_path),
        "file_size": storage_path.stat().st_size,
        "preview_text": "已读取上传 PDF 文件，当前提供文件级解析预览；正文抽取将在后续接入。",
        "extraction_method": "file-metadata-placeholder",
    }


def test_pdf_parse_status_endpoint_rejects_record_without_pending_upload(
    monkeypatch, tmp_path: Path
):
    from app.services import literature as literature_service

    original_path = (
        Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
    )
    temp_path = tmp_path / "sample_ad_literature.json"
    reset_sample_data(original_path, temp_path)

    monkeypatch.setattr(
        literature_service,
        "_REPOSITORY",
        literature_service.InMemoryLiteratureRepository(temp_path),
    )

    client = TestClient(app)

    response = client.post(
        "/api/literature/pdf-parse-status",
        json={
            "literature_id": "cn-ad-gbs-001",
            "pdf_parse_status": "failed",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "PDF metadata not attached"}
