"""Structured logging configuration for Qiyan Nexus API.

Provides JSON formatter for structured log output, controlled by environment variable.
"""

import json
import logging
import os
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines.

    Extracts structured fields from record.extra and outputs them as JSON.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON line.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log line
        """
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Extract any extra fields added via logger.info(..., extra={...})
        # These are fields not in the standard LogRecord attributes
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "taskName",
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def configure_logging(
    level: str = "INFO",
    format_type: str = "text",
) -> None:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format ("text" or "json")
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Remove existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    formatter: logging.Formatter
    if format_type.lower() == "json":
        formatter = JSONFormatter()
    else:
        # Text format with timestamp and structured fields
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def get_log_config_from_env() -> tuple[str, str]:
    """Get logging configuration from environment variables.

    Returns:
        Tuple of (level, format_type)

    Environment variables:
        QIYAN_LOG_LEVEL: Log level (default: INFO)
        QIYAN_LOG_FORMAT: Output format, "text" or "json" (default: text)
    """
    level = os.getenv("QIYAN_LOG_LEVEL", "INFO")
    format_type = os.getenv("QIYAN_LOG_FORMAT", "text")
    return level, format_type


def init_logging() -> None:
    """Initialize logging from environment variables.

    Should be called once at application startup.
    """
    level, format_type = get_log_config_from_env()
    configure_logging(level=level, format_type=format_type)
