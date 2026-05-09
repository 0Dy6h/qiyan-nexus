from pathlib import Path

from app.core.config import get_settings


def test_default_settings():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "Qiyan Nexus API"
    assert settings.environment == "dev"
    assert settings.upload_storage_dir == Path("uploads")


def test_upload_storage_dir_from_env(monkeypatch):
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", "/tmp/qiyan-uploads")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.upload_storage_dir == Path("/tmp/qiyan-uploads")
    get_settings.cache_clear()
