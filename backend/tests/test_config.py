import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings, get_settings


def test_default_settings(monkeypatch):
    for env_var in [
        "APP_NAME",
        "ENVIRONMENT",
        "QIYAN_LLM_PROVIDER",
        "QIYAN_ACCESS_TOKENS",
        "UPLOAD_STORAGE_DIR",
        "ANTHROPIC_API_KEY",
        "QIYAN_ANTHROPIC_MODEL",
        "QIYAN_ANTHROPIC_MAX_TOKENS",
        "QIYAN_OPENCODE_GO_API_KEY",
        "QIYAN_OPENCODE_GO_BASE_URL",
        "QIYAN_OPENCODE_GO_MODEL",
        "QIYAN_OPENCODE_GO_MAX_TOKENS",
        "QIYAN_OPENCODE_GO_TEMPERATURE",
        "QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK",
        "QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK",
        "QIYAN_NETWORK_DATA_PROVIDER",
        "QIYAN_NETWORK_TASK_RUNNER",
        "QIYAN_NETWORK_ALLOW_TCMSP_SCRAPE",
        "QIYAN_NETWORK_TARGET_PREDICTION_FILE",
        "QIYAN_NETWORK_CACHE_DIR",
        "QIYAN_NETWORK_HTTP_TIMEOUT_SECONDS",
        "QIYAN_NETWORK_RATE_LIMIT_PER_SECOND",
    ]:
        monkeypatch.delenv(env_var, raising=False)
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "Qiyan Nexus API"
    assert settings.environment == "dev"
    assert settings.llm_provider == "deterministic"
    assert settings.access_control_enabled is False
    assert settings.upload_storage_dir == Path("uploads")
    assert settings.anthropic_api_key == ""
    assert settings.opencode_go_api_key == ""
    assert settings.opencode_go_base_url == "https://ai.router.team/v1"
    assert settings.opencode_go_model == "gpt-5.5"
    assert settings.opencode_go_max_tokens == 4096
    assert settings.opencode_go_temperature == 0.2
    assert settings.opencode_go_price_input_per_mtok == 0.0
    assert settings.opencode_go_price_output_per_mtok == 0.0
    assert settings.network_data_provider == "mock"
    assert settings.network_task_runner == "local"
    assert settings.network_allow_tcmsp_scrape is False
    assert settings.network_target_prediction_file == Path("")
    assert settings.network_cache_dir == Path("backend/data/runtime/network_cache")
    assert settings.network_http_timeout_seconds == 15.0
    assert settings.network_rate_limit_per_second == 1.0
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


def test_opencode_go_price_settings_from_env(monkeypatch):
    monkeypatch.setenv("QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK", "0.27")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK", "1.1")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.opencode_go_price_input_per_mtok == 0.27
    assert settings.opencode_go_price_output_per_mtok == 1.1
    get_settings.cache_clear()


def test_network_live_settings_from_env(monkeypatch):
    monkeypatch.setenv("QIYAN_NETWORK_DATA_PROVIDER", "live")
    monkeypatch.setenv("QIYAN_NETWORK_TASK_RUNNER", "celery")
    monkeypatch.setenv("QIYAN_NETWORK_ALLOW_TCMSP_SCRAPE", "true")
    monkeypatch.setenv("QIYAN_NETWORK_TARGET_PREDICTION_FILE", "/tmp/predictions.csv")
    monkeypatch.setenv("QIYAN_NETWORK_CACHE_DIR", "/tmp/qiyan-network-cache")
    monkeypatch.setenv("QIYAN_NETWORK_HTTP_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("QIYAN_NETWORK_RATE_LIMIT_PER_SECOND", "0.5")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.network_data_provider == "live"
    assert settings.network_task_runner == "celery"
    assert settings.network_allow_tcmsp_scrape is True
    assert settings.network_target_prediction_file == Path("/tmp/predictions.csv")
    assert settings.network_cache_dir == Path("/tmp/qiyan-network-cache")
    assert settings.network_http_timeout_seconds == 3.5
    assert settings.network_rate_limit_per_second == 0.5
    get_settings.cache_clear()


def test_production_requires_access_control(tmp_path):
    with pytest.raises(ValueError, match="access control"):
        Settings(environment="production", upload_storage_dir=tmp_path)


def test_production_accepts_deterministic_without_placeholder_llm_key(tmp_path):
    settings = Settings(
        environment="production",
        access_control_enabled=True,
        upload_storage_dir=tmp_path,
    )

    assert settings.environment == "production"


def test_production_live_provider_requires_its_api_key(tmp_path):
    with pytest.raises(ValueError, match="QIYAN_OPENCODE_GO_API_KEY"):
        Settings(
            environment="production",
            access_control_enabled=True,
            llm_provider="opencode_go",
            upload_storage_dir=tmp_path,
        )


def test_production_alias_is_normalized_and_still_runs_validation(tmp_path):
    settings = Settings(
        environment=" PROD ",
        access_control_enabled=True,
        upload_storage_dir=tmp_path,
    )

    assert settings.environment == "production"


def test_unknown_environment_fails_closed():
    with pytest.raises(ValueError, match="ENVIRONMENT"):
        Settings(environment="staging-ish")


def test_production_rejects_out_of_range_grounding_threshold(tmp_path):
    with pytest.raises(ValueError, match="GROUNDING_SEMANTIC_THRESHOLD"):
        Settings(
            environment="production",
            access_control_enabled=True,
            upload_storage_dir=tmp_path,
            grounding_semantic_threshold=1.5,
        )


def test_dev_environment_skips_production_validation():
    # Default dev path must not raise even with no provider keys configured.
    settings = Settings(environment="dev")

    assert settings.environment == "dev"


def test_app_import_runs_production_validation_before_serving_requests(tmp_path):
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "prod",
            "QIYAN_ACCESS_TOKENS": "",
            "QIYAN_LLM_PROVIDER": "deterministic",
            "UPLOAD_STORAGE_DIR": str(tmp_path),
        }
    )

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "requires access control" in result.stderr
