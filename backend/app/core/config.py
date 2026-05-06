import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = "Qiyan Nexus API"
    environment: str = "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Qiyan Nexus API"),
        environment=os.getenv("ENVIRONMENT", "dev"),
    )
