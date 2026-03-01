import json
import logging
import sys

from app.config.logging_config import CloudJsonFormatter, log_stage


def test_log_stage_logs_start_and_completion(capfd):
    test_logger = logging.getLogger("test_stage")
    test_logger.handlers.clear()
    test_logger.propagate = False
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudJsonFormatter())
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    with log_stage("test_step", logger=test_logger, job_id="j1"):
        pass  # simulate work

    captured = capfd.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().split("\n") if line]
    assert len(lines) == 2

    assert "Starting test_step" in lines[0]["message"]
    assert lines[0]["stage"] == "test_step"
    assert lines[0]["job_id"] == "j1"

    assert "Completed test_step" in lines[1]["message"]
    assert lines[1]["stage"] == "test_step"
    assert "duration_ms" in lines[1]
    assert lines[1]["duration_ms"] >= 0


def test_log_stage_logs_failure_on_exception(capfd):
    test_logger = logging.getLogger("test_stage_fail")
    test_logger.handlers.clear()
    test_logger.propagate = False
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudJsonFormatter())
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    try:
        with log_stage("failing_step", logger=test_logger):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    captured = capfd.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().split("\n") if line]
    assert len(lines) == 2

    assert lines[0]["stage"] == "failing_step"
    assert "Failed failing_step" in lines[1]["message"]
    assert lines[1]["severity"] == "ERROR"
    assert lines[1]["duration_ms"] >= 0
