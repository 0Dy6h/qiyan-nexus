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
    opencode_go_base_url: str = "https://opencode.ai/zen/go/v1"
    opencode_go_model: str = "deepseek-v4-flash"
    opencode_go_max_tokens: int = 1200
    opencode_go_temperature: float = 0.2
    opencode_go_price_input_per_mtok: float = 0.0
    opencode_go_price_output_per_mtok: float = 0.0
    grounding_semantic_threshold: float = 0.40


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
        opencode_go_base_url=os.getenv(
            "QIYAN_OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1"
        ),
        opencode_go_model=os.getenv("QIYAN_OPENCODE_GO_MODEL", "deepseek-v4-flash"),
        opencode_go_max_tokens=int(os.getenv("QIYAN_OPENCODE_GO_MAX_TOKENS", "1200")),
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
    )
