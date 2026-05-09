import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def reset_sample_data(original_path: Path, temp_path: Path) -> None:
    temp_path.write_text(original_path.read_text(encoding="utf-8"), encoding="utf-8")


def test_pdf_metadata_upload_endpoint_updates_literature_record(monkeypatch, tmp_path: Path):
    from app import services as services_pkg
    from app.services import literature as literature_service

    original_path = Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
    temp_path = tmp_path / "sample_ad_literature.json"
    reset_sample_data(original_path, temp_path)

    monkeypatch.setattr(literature_service, "_SAMPLE_DATA_PATH", temp_path)
    monkeypatch.setattr(literature_service, "_REPOSITORY", literature_service.InMemoryLiteratureRepository(temp_path))

    client = TestClient(app)

    response = client.post(
        "/api/literature/pdf-metadata",
        json={
            "literature_id": "cn-ad-gbs-001",
            "file_name": "ad-evidence.pdf",
            "source_type": "uploaded_pdf",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "cn-ad-gbs-001"
    assert payload["pdf_upload_id"] == "pdf-cn-ad-gbs-001-ad-evidence-pdf"
    assert payload["pdf_file_name"] == "ad-evidence.pdf"
    assert payload["pdf_parse_status"] == "pending"

    persisted = json.loads(temp_path.read_text(encoding="utf-8"))
    first = next(item for item in persisted if item["id"] == "cn-ad-gbs-001")
    assert first["pdf_upload_id"] == "pdf-cn-ad-gbs-001-ad-evidence-pdf"
    assert first["pdf_file_name"] == "ad-evidence.pdf"
    assert first["pdf_parse_status"] == "pending"


def test_pdf_metadata_upload_endpoint_returns_404_for_unknown_literature_id(monkeypatch, tmp_path: Path):
    from app.services import literature as literature_service

    original_path = Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
    temp_path = tmp_path / "sample_ad_literature.json"
    reset_sample_data(original_path, temp_path)

    monkeypatch.setattr(literature_service, "_SAMPLE_DATA_PATH", temp_path)
    monkeypatch.setattr(literature_service, "_REPOSITORY", literature_service.InMemoryLiteratureRepository(temp_path))

    client = TestClient(app)

    response = client.post(
        "/api/literature/pdf-metadata",
        json={
            "literature_id": "unknown",
            "file_name": "ad-evidence.pdf",
            "source_type": "uploaded_pdf",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Literature item not found"}


def test_pdf_metadata_upload_endpoint_rejects_invalid_source_type():
    client = TestClient(app)

    response = client.post(
        "/api/literature/pdf-metadata",
        json={
            "literature_id": "cn-ad-gbs-001",
            "file_name": "ad-evidence.pdf",
            "source_type": "unknown",
        },
    )

    assert response.status_code == 422
