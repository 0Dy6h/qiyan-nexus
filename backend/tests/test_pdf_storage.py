"""Test pdf_storage path resolution security."""

from pathlib import Path

from app.services.pdf_storage import build_storage_path, resolve_stored_pdf_path


def test_resolve_stored_pdf_path_returns_none_for_missing_file(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings

    storage_dir = tmp_path.resolve()
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    result = resolve_stored_pdf_path("pdf-valid-id")
    assert result is None


def test_resolve_stored_pdf_path_returns_path_for_existing_file(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings

    storage_dir = tmp_path.resolve()
    storage_file = storage_dir / "pdf-valid-id.pdf"
    storage_file.write_bytes(b"%PDF-1.4")
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    result = resolve_stored_pdf_path("pdf-valid-id")
    assert result == storage_file


def test_resolve_stored_pdf_path_rejects_parent_traversal(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings

    storage_dir = tmp_path.resolve()
    (storage_dir / "escape.pdf").write_bytes(b"%PDF-1.4")
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    result = resolve_stored_pdf_path("pdf-../escape")
    assert result is None


def test_resolve_stored_pdf_path_rejects_absolute_path_injection(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings

    storage_dir = tmp_path.resolve()
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    result = resolve_stored_pdf_path("pdf-/etc/passwd")
    assert result is None


def test_resolve_stored_pdf_path_rejects_invalid_id_pattern(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings

    storage_dir = tmp_path.resolve()
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    result = resolve_stored_pdf_path("../etc/passwd")
    assert result is None


def test_build_storage_path_uses_pdf_upload_id_only(tmp_path: Path):
    result = build_storage_path(tmp_path, "pdf-id-123", "ignored.pdf")
    assert result == tmp_path / "pdf-id-123.pdf"
