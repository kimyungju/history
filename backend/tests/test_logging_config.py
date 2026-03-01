import json
import logging

from app.config.logging_config import CloudJsonFormatter, trace_id_var


def test_json_formatter_outputs_valid_json_with_severity():
    formatter = CloudJsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="hello world", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["severity"] == "INFO"
    assert parsed["message"] == "hello world"


def test_json_formatter_includes_source_location():
    formatter = CloudJsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="/app/services/ocr.py",
        lineno=42, msg="low confidence", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    loc = parsed["logging.googleapis.com/sourceLocation"]
    assert loc["file"] == "/app/services/ocr.py"
    assert loc["line"] == 42


def test_json_formatter_includes_trace_id_when_set():
    formatter = CloudJsonFormatter()
    token = trace_id_var.set("abc123def456")
    try:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="traced", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["logging.googleapis.com/trace"] == "abc123def456"
    finally:
        trace_id_var.reset(token)


def test_json_formatter_omits_trace_when_not_set():
    formatter = CloudJsonFormatter()
    # Ensure trace_id_var is at default (empty string)
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="no trace", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "logging.googleapis.com/trace" not in parsed


def test_json_formatter_includes_extra_fields():
    formatter = CloudJsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py",
        lineno=1, msg="stage done", args=(), exc_info=None,
    )
    record.stage = "ocr"
    record.duration_ms = 1234.5
    record.job_id = "job-001"
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["stage"] == "ocr"
    assert parsed["duration_ms"] == 1234.5
    assert parsed["job_id"] == "job-001"


def test_json_formatter_includes_exception_traceback():
    formatter = CloudJsonFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="error occurred", args=(), exc_info=sys.exc_info(),
        )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "ValueError: test error" in parsed["stack_trace"]
