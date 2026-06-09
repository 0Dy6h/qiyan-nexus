import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Qiyan Nexus API"
    environment: str = "dev"
    upload_storage_dir: Path = Path("uploads")
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = 1024
    opencode_go_api_key: str = ""
    opencode_go_base_url: str = "https://ai.router.team/v1"
    opencode_go_model: str = "gpt-5.5"
    opencode_go_max_tokens: int = 4096
    opencode_go_temperature: float = 0.2
    opencode_go_price_input_per_mtok: float = 0.0
    opencode_go_price_output_per_mtok: float = 0.0
    grounding_semantic_threshold: float = 0.40
    nli_backend: str = ""
    nli_threshold: float = 0.0
    network_data_provider: str = "mock"
    network_task_runner: str = "local"
    network_allow_tcmsp_scrape: bool = False
    network_target_prediction_file: Path = Path("")
    network_cache_dir: Path = Path("backend/data/runtime/network_cache")
    network_http_timeout_seconds: float = 15.0
    network_rate_limit_per_second: float = 1.0


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Qiyan Nexus API"),
        environment=os.getenv("ENVIRONMENT", "dev"),
        upload_storage_dir=Path(os.getenv("UPLOAD_STORAGE_DIR", "uploads")),
        # ANTHROPIC_API_KEY is intentionally unprefixed: the anthropic SDK reads
        # this exact name natively, so we mirror it instead of using QIYAN_*.
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("QIYAN_ANTHROPIC_MODEL", "claude-haiku-4-5"),
        anthropic_max_tokens=int(os.getenv("QIYAN_ANTHROPIC_MAX_TOKENS", "1024")),
        opencode_go_api_key=os.getenv("QIYAN_OPENCODE_GO_API_KEY", ""),
        opencode_go_base_url=os.getenv("QIYAN_OPENCODE_GO_BASE_URL", "https://ai.router.team/v1"),
        opencode_go_model=os.getenv("QIYAN_OPENCODE_GO_MODEL", "gpt-5.5"),
        opencode_go_max_tokens=int(os.getenv("QIYAN_OPENCODE_GO_MAX_TOKENS", "4096")),
        opencode_go_temperature=float(os.getenv("QIYAN_OPENCODE_GO_TEMPERATURE", "0.2")),
        # Prices are USD per million tokens; default 0.0 means "do not estimate cost"
        # so we never surface a guessed price the operator did not configure.
        opencode_go_price_input_per_mtok=float(
            os.getenv("QIYAN_OPENCODE_GO_PRICE_INPUT_PER_MTOK", "0.0")
        ),
        opencode_go_price_output_per_mtok=float(
            os.getenv("QIYAN_OPENCODE_GO_PRICE_OUTPUT_PER_MTOK", "0.0")
        ),
        grounding_semantic_threshold=float(os.getenv("QIYAN_GROUNDING_SEMANTIC_THRESHOLD", "0.40")),
        # Opt-in NLI entailment second-stage gate; default empty backend = disabled.
        # Threshold <=0 also disables it. See app/services/nli.py and
        # docs/evaluations/2026-06-01-nli-grounding-spike.md.
        nli_backend=os.getenv("QIYAN_NLI_BACKEND", ""),
        nli_threshold=float(os.getenv("QIYAN_NLI_THRESHOLD", "0.0")),
        network_data_provider=os.getenv("QIYAN_NETWORK_DATA_PROVIDER", "mock"),
        network_task_runner=os.getenv("QIYAN_NETWORK_TASK_RUNNER", "local"),
        network_allow_tcmsp_scrape=_bool_env("QIYAN_NETWORK_ALLOW_TCMSP_SCRAPE"),
        network_target_prediction_file=Path(os.getenv("QIYAN_NETWORK_TARGET_PREDICTION_FILE", "")),
        network_cache_dir=Path(
            os.getenv("QIYAN_NETWORK_CACHE_DIR", "backend/data/runtime/network_cache")
        ),
        network_http_timeout_seconds=float(os.getenv("QIYAN_NETWORK_HTTP_TIMEOUT_SECONDS", "15")),
        network_rate_limit_per_second=float(os.getenv("QIYAN_NETWORK_RATE_LIMIT_PER_SECOND", "1")),
    )
