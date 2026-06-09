"""Tests for structured logging configuration."""

import json
import logging

from app.core.logging_config import (
    JSONFormatter,
    configure_logging,
    get_log_config_from_env,
)


def test_json_formatter_basic_message():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    data = json.loads(output)

    assert data["level"] == "INFO"
    assert data["logger"] == "test.logger"
    assert data["message"] == "Test message"
    assert "timestamp" in data


def test_json_formatter_with_extra_fields():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    # Add extra fields
    record.request_id = "abc-123"
    record.elapsed_ms = 42.5
    record.status_code = 200

    output = formatter.format(record)
    data = json.loads(output)

    assert data["request_id"] == "abc-123"
    assert data["elapsed_ms"] == 42.5
    assert data["status_code"] == 200


def test_json_formatter_excludes_standard_attrs():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    data = json.loads(output)

    # Standard attrs should not appear as extra fields
    assert "pathname" not in data
    assert "lineno" not in data
    assert "funcName" not in data
    assert "thread" not in data


def test_json_formatter_with_exception():
    formatter = JSONFormatter()

    try:
        raise ValueError("Test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )

    output = formatter.format(record)
    data = json.loads(output)

    assert "exception" in data
    assert "ValueError: Test error" in data["exception"]
    assert "Traceback" in data["exception"]


def test_configure_logging_text_format():
    configure_logging(level="DEBUG", format_type="text")

    logger = logging.getLogger("test_text")
    # Verify logger is configured at DEBUG level
    assert logger.isEnabledFor(logging.DEBUG)

    # Verify root logger has a handler
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0


def test_configure_logging_json_format():
    configure_logging(level="INFO", format_type="json")

    logger = logging.getLogger("test_json")
    # Verify logger is configured at INFO level
    assert logger.isEnabledFor(logging.INFO)

    # Verify the handler uses JSONFormatter
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0
    handler = root_logger.handlers[0]
    assert isinstance(handler.formatter, JSONFormatter)


def test_configure_logging_sets_level():
    configure_logging(level="WARNING", format_type="text")

    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING


def test_get_log_config_from_env_defaults(monkeypatch):
    monkeypatch.delenv("QIYAN_LOG_LEVEL", raising=False)
    monkeypatch.delenv("QIYAN_LOG_FORMAT", raising=False)

    level, format_type = get_log_config_from_env()

    assert level == "INFO"
    assert format_type == "text"


def test_get_log_config_from_env_custom(monkeypatch):
    monkeypatch.setenv("QIYAN_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("QIYAN_LOG_FORMAT", "json")

    level, format_type = get_log_config_from_env()

    assert level == "DEBUG"
    assert format_type == "json"


def test_configure_logging_removes_existing_handlers():
    # Add a dummy handler
    root_logger = logging.getLogger()

    dummy_handler = logging.StreamHandler()
    root_logger.addHandler(dummy_handler)

    # Configure logging should remove existing handlers
    configure_logging(level="INFO", format_type="text")

    # Should have exactly 1 handler (the new one)
    assert len(root_logger.handlers) == 1


def test_json_formatter_handles_unicode():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="中文日志消息",
        args=(),
        exc_info=None,
    )
    record.user_name = "张三"

    output = formatter.format(record)
    data = json.loads(output)

    assert data["message"] == "中文日志消息"
    assert data["user_name"] == "张三"
    # ensure_ascii=False means Chinese characters are preserved
    assert "中文" in output
    assert "张三" in output
