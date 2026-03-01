"""Structured JSON logging for Google Cloud Run.

Cloud Run auto-captures stdout to Cloud Logging. This module provides:
- CloudJsonFormatter: outputs JSON matching Cloud Logging's structured format
- trace_id_var: contextvars.ContextVar for request-scoped trace ID propagation
- setup_logging(): configures the root logger with JSON output
- log_stage(): context manager for timing pipeline stages
"""

from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

_SEVERITY_MAP = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}

_EXTRA_FIELDS = ("stage", "duration_ms", "job_id", "step", "doc_id", "entity_count")


class CloudJsonFormatter(logging.Formatter):
    """Outputs one JSON object per log line, compatible with Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "severity": _SEVERITY_MAP.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        trace_id = trace_id_var.get("")
        if trace_id:
            entry["logging.googleapis.com/trace"] = trace_id

        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value

        if record.exc_info and record.exc_info[0] is not None:
            entry["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(entry)


def setup_logging() -> None:
    """Configure root logger with CloudJsonFormatter on stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudJsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


@contextmanager
def log_stage(stage_name: str, logger: logging.Logger | None = None, **extra):
    """Context manager that logs stage start/end with elapsed time in ms.

    Usage::

        with log_stage("ocr", logger=logger, job_id=job_id):
            result = await ocr_service.process_pdf(pdf_bytes)
    """
    _logger = logger or logging.getLogger(__name__)
    _logger.info("Starting %s", stage_name, extra={"stage": stage_name, **extra})
    start = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        _logger.error(
            "Failed %s after %.1fms",
            stage_name,
            elapsed,
            extra={"stage": stage_name, "duration_ms": round(elapsed, 1), **extra},
        )
        raise
    else:
        elapsed = (time.perf_counter() - start) * 1000
        _logger.info(
            "Completed %s in %.1fms",
            stage_name,
            elapsed,
            extra={"stage": stage_name, "duration_ms": round(elapsed, 1), **extra},
        )
