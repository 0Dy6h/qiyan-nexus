from app.core.config import get_settings


def test_default_settings():
    settings = get_settings()

    assert settings.app_name == "Qiyan Nexus API"
    assert settings.environment == "dev"
