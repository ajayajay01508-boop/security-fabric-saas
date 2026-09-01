"""
Structured logging utilities for all Python services.
Usage:
    from shared.python_utils.logging import get_logger
    logger = get_logger(__name__)
    logger.info("event", extra={"trace_id": "abc", "tenant_id": 1})
"""
import logging
import json
import time
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for log aggregators (Loki, CloudWatch)."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)

        # Merge any extra fields
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
            ):
                log_obj[key] = val

        return json.dumps(log_obj, default=str)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
