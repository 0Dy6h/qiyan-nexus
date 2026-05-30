from pathlib import Path

from app.core.config import get_settings


def test_default_settings(monkeypatch):
    for env_var in [
        "APP_NAME",
        "ENVIRONMENT",
        "UPLOAD_STORAGE_DIR",
        "ANTHROPIC_API_KEY",
        "QIYAN_ANTHROPIC_MODEL",
        "QIYAN_ANTHROPIC_MAX_TOKENS",
        "QIYAN_OPENCODE_GO_API_KEY",
        "QIYAN_OPENCODE_GO_BASE_URL",
        "QIYAN_OPENCODE_GO_MODEL",
        "QIYAN_OPENCODE_GO_MAX_TOKENS",
        "QIYAN_OPENCODE_GO_TEMPERATURE",
    ]:
        monkeypatch.delenv(env_var, raising=False)
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "Qiyan Nexus API"
    assert settings.environment == "dev"
    assert settings.upload_storage_dir == Path("uploads")
    assert settings.anthropic_api_key == ""
    assert settings.opencode_go_api_key == ""
    assert settings.opencode_go_base_url == "https://opencode.ai/zen/go/v1"
    assert settings.opencode_go_model == "deepseek-v4-flash"
    assert settings.opencode_go_max_tokens == 1200
    assert settings.opencode_go_temperature == 0.2
    get_settings.cache_clear()


def test_upload_storage_dir_from_env(monkeypatch):
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", "/tmp/qiyan-uploads")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.upload_storage_dir == Path("/tmp/qiyan-uploads")
    get_settings.cache_clear()


def test_anthropic_api_key_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.anthropic_api_key == "test-anthropic-key"
    get_settings.cache_clear()


def test_opencode_go_settings_from_env(monkeypatch):
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-key")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_MODEL", "test-model")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_MAX_TOKENS", "128")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_TEMPERATURE", "0.4")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.opencode_go_api_key == "test-key"
    assert settings.opencode_go_base_url == "https://example.test/v1/"
    assert settings.opencode_go_model == "test-model"
    assert settings.opencode_go_max_tokens == 128
    assert settings.opencode_go_temperature == 0.4
    get_settings.cache_clear()
