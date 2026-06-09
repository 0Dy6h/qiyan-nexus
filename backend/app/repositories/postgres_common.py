"""Shared helpers for the opt-in PostgreSQL spike repositories."""

import os
from pathlib import Path
from typing import Any

from psycopg_pool import ConnectionPool

_SCHEMA_PATH = Path(__file__).resolve().parent / "postgres_schema.sql"
_DEFAULT_POOL_TIMEOUT_SECONDS = 5.0
_DEFAULT_CONNECT_TIMEOUT_SECONDS = 5


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def create_postgres_pool(dsn: str, *, min_size: int = 0, max_size: int = 5) -> ConnectionPool[Any]:
    """Create a small, fast-failing pool for the PostgreSQL spike backend."""
    pool_timeout = _float_env("QIYAN_POSTGRES_POOL_TIMEOUT", _DEFAULT_POOL_TIMEOUT_SECONDS)
    connect_timeout = _int_env(
        "QIYAN_POSTGRES_CONNECT_TIMEOUT",
        _DEFAULT_CONNECT_TIMEOUT_SECONDS,
    )
    return ConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        open=True,
        timeout=pool_timeout,
        reconnect_timeout=pool_timeout,
        kwargs={"connect_timeout": connect_timeout},
        num_workers=1,
    )


def ensure_postgres_schema(pool: ConnectionPool[Any]) -> None:
    """Apply the idempotent spike schema to a PostgreSQL connection pool."""
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    with pool.connection() as conn:
        conn.execute(schema_sql)
        conn.commit()
