import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Qiyan Nexus API"
    environment: str = "dev"
    upload_storage_dir: Path = Path("uploads")
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Qiyan Nexus API"),
        environment=os.getenv("ENVIRONMENT", "dev"),
        upload_storage_dir=Path(os.getenv("UPLOAD_STORAGE_DIR", "uploads")),
        anthropic_model=os.getenv("QIYAN_ANTHROPIC_MODEL", "claude-haiku-4-5"),
        anthropic_max_tokens=int(os.getenv("QIYAN_ANTHROPIC_MAX_TOKENS", "1024")),
    )
