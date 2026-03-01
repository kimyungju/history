# Phase 5: Git Init + Cloud Logging (5.1) + CI/CD Pipeline (5.7)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Initialize git repository with first commit, add structured Cloud Logging with request trace IDs and pipeline stage timing, and set up a Cloud Build CI/CD pipeline with lint, test, Docker build, Artifact Registry push, Cloud Run deploy, and smoke test.

**Architecture:**
- **Cloud Logging**: Structured JSON to stdout (Cloud Run auto-captures to Cloud Logging). Custom `CloudJsonFormatter` replaces Python's default formatter. FastAPI middleware injects `X-Cloud-Trace-Context` trace IDs via `contextvars`. A `log_stage()` context manager adds timing to ingestion and query pipeline steps.
- **CI/CD**: Google Cloud Build multi-step pipeline. Backend: `ruff check` + `pytest`. Frontend: `eslint` + `tsc --noEmit` + `vitest run`. Docker images built and pushed to Artifact Registry (`asia-southeast1-docker.pkg.dev/aihistory-488807/colonial-archives/`). Deployed to Cloud Run with secrets from Secret Manager. Post-deploy smoke test hits `/health`.

**Tech Stack:** Google Cloud Build, Cloud Run, Artifact Registry, Secret Manager, ruff, pytest, pytest-asyncio, Vitest, ESLint

---

## Task 1: Git Init + .gitignore + First Commit

**Files:**
- Modify: `.gitignore`

**Step 1: Enhance .gitignore with GCP credential patterns**

Add these lines to the existing `.gitignore` at `C:/NUS/Projects/history/.gitignore`:

```
# GCP credentials
*-service-account.json
credentials*.json
*-key.json

# IDE
.idea/
.vscode/
*.swp

# Claude Code
.claude/worktrees/

# Build artifacts
frontend/dist/
backend/__pycache__/
```

**Step 2: Initialize git repository**

```bash
cd C:/NUS/Projects/history
git init
```

Expected: `Initialized empty Git repository in ...`

**Step 3: Stage all files and verify sensitive files are excluded**

```bash
git status
```

Verify: `.env` is NOT listed. `node_modules/` is NOT listed. No `*-service-account.json` files listed.

**Step 4: Create first commit**

```bash
git add -A
git commit -m "feat: Phases 1-3 complete — backend, graph layer, React frontend

- FastAPI backend with 9-step ingestion pipeline
  (OCR → chunk → embed → vector → entity extraction → normalization → Neo4j)
- Hybrid query: parallel vector search + graph traversal + Gemini answer
- React 18 frontend: graph visualization, chat panel, PDF modal
- Docker Compose for local development
- Tested end-to-end with real colonial archive documents"
```

Expected: large commit with all Phase 1-3 files.

---

## Task 2: Backend Dev Dependencies + Lint/Test Config

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/pyproject.toml`

**Step 1: Create `backend/requirements-dev.txt`**

```
-r requirements.txt
ruff>=0.9.0
pytest>=8.0
pytest-asyncio>=0.25
```

**Step 2: Create `backend/pyproject.toml` with ruff + pytest config**

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: Install dev dependencies**

```bash
cd C:/NUS/Projects/history/backend
pip install -r requirements-dev.txt
```

Expected: ruff, pytest, pytest-asyncio installed successfully.

**Step 4: Verify ruff runs (expect lint issues — that's OK, we just want it to not crash)**

```bash
cd C:/NUS/Projects/history/backend
ruff check app/ --statistics
```

Expected: runs and reports findings. We will NOT fix all lint issues now — just verify the tool works.

**Step 5: Commit**

```bash
cd C:/NUS/Projects/history
git add backend/requirements-dev.txt backend/pyproject.toml
git commit -m "chore: add dev dependencies — ruff, pytest, pytest-asyncio"
```

---

## Task 3: Structured Cloud Logging — JSON Formatter (TDD)

**Files:**
- Create: `backend/app/config/logging_config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_logging_config.py`

**Step 1: Write the failing tests**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/test_logging_config.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/test_logging_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.config.logging_config'`

**Step 3: Implement `backend/app/config/logging_config.py`**

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/test_logging_config.py -v
```

Expected: all 6 tests PASS.

**Step 5: Commit**

```bash
cd C:/NUS/Projects/history
git add backend/app/config/logging_config.py backend/tests/
git commit -m "feat(5.1): structured JSON log formatter with trace ID support

- CloudJsonFormatter outputs Cloud Logging compatible JSON to stdout
- trace_id_var ContextVar for request-scoped trace propagation
- log_stage() context manager for pipeline timing
- 6 unit tests covering all formatter behaviors"
```

---

## Task 4: Trace ID Middleware (TDD)

**Files:**
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/middleware/trace.py`
- Create: `backend/tests/test_trace_middleware.py`
- Modify: `backend/app/main.py` (wire middleware + setup_logging)

**Step 1: Write the failing tests**

Create `backend/tests/test_trace_middleware.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.config.logging_config import trace_id_var
from app.middleware.trace import TraceMiddleware


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with TraceMiddleware for testing."""
    app = FastAPI()
    app.add_middleware(TraceMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"trace_id": trace_id_var.get("")}

    return app


@pytest.mark.asyncio
async def test_middleware_generates_trace_id():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test")
    assert response.status_code == 200
    assert "X-Trace-Id" in response.headers
    trace_id = response.headers["X-Trace-Id"]
    assert len(trace_id) == 32  # UUID hex without dashes


@pytest.mark.asyncio
async def test_middleware_propagates_cloud_trace_header():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/test",
            headers={"X-Cloud-Trace-Context": "abcdef1234567890/123;o=1"},
        )
    assert response.headers["X-Trace-Id"] == "abcdef1234567890"
    body = response.json()
    assert body["trace_id"] == "abcdef1234567890"


@pytest.mark.asyncio
async def test_middleware_sets_trace_in_contextvar():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test")
    body = response.json()
    # The endpoint returns the trace_id from the contextvar
    assert body["trace_id"] == response.headers["X-Trace-Id"]
```

**Step 2: Run tests to verify they fail**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/test_trace_middleware.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.middleware'`

**Step 3: Implement the middleware**

Create `backend/app/middleware/__init__.py` (empty file).

Create `backend/app/middleware/trace.py`:

```python
"""Trace ID middleware for request-scoped logging correlation.

Extracts trace ID from the ``X-Cloud-Trace-Context`` header (set by Cloud Run)
or generates a UUID. Stores it in ``trace_id_var`` for the request lifetime
and returns it in the ``X-Trace-Id`` response header.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config.logging_config import trace_id_var


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_header = request.headers.get("X-Cloud-Trace-Context", "")
        if trace_header:
            trace_id = trace_header.split("/")[0]
        else:
            trace_id = uuid.uuid4().hex

        token = trace_id_var.set(trace_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            trace_id_var.reset(token)
```

**Step 4: Run tests to verify they pass**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/test_trace_middleware.py -v
```

Expected: all 3 tests PASS.

**Step 5: Wire into `backend/app/main.py`**

Add these changes to `main.py`:

1. Add import at top:
```python
from app.config.logging_config import setup_logging
from app.middleware.trace import TraceMiddleware
```

2. Call `setup_logging()` at the very start of the `lifespan` function (before `vertexai.init`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    vertexai.init(
        ...
```

3. Add TraceMiddleware AFTER the CORSMiddleware block:
```python
app.add_middleware(TraceMiddleware)
```

**Step 6: Run all tests**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/ -v
```

Expected: all 9 tests PASS (6 formatter + 3 middleware).

**Step 7: Commit**

```bash
cd C:/NUS/Projects/history
git add backend/app/middleware/ backend/tests/test_trace_middleware.py backend/app/main.py
git commit -m "feat(5.1): trace ID middleware — Cloud Trace header propagation

- TraceMiddleware extracts X-Cloud-Trace-Context or generates UUID
- Stores in contextvars for automatic inclusion in all JSON logs
- setup_logging() wired into FastAPI lifespan
- 3 unit tests for trace propagation"
```

---

## Task 5: Pipeline Stage Timing

**Files:**
- Modify: `backend/app/routers/ingest.py` (wrap 9 steps in `log_stage`)
- Modify: `backend/app/services/hybrid_retrieval.py` (wrap query pipeline in `log_stage`)
- Create: `backend/tests/test_log_stage.py`

**Step 1: Write the failing test for `log_stage`**

Create `backend/tests/test_log_stage.py`:

```python
import json
import logging

from app.config.logging_config import CloudJsonFormatter, log_stage


def test_log_stage_logs_start_and_completion(capfd):
    test_logger = logging.getLogger("test_stage")
    test_logger.handlers.clear()
    handler = logging.StreamHandler()
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
    handler = logging.StreamHandler()
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
```

**Step 2: Run tests to verify they pass (log_stage already implemented)**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/test_log_stage.py -v
```

Expected: 2 tests PASS (the implementation is in Task 3).

**Step 3: Add `log_stage` to ingestion pipeline in `backend/app/routers/ingest.py`**

Add import at top of `ingest.py`:
```python
from app.config.logging_config import log_stage
```

Replace the 9 pipeline steps in `_run_ingestion()` to wrap each in `log_stage`. Each step's existing `logger.info` call at the start becomes the `log_stage` context manager. Example transformation for Step 1:

Before:
```python
        # ---- Step 1: Download PDF -------------------------------------------
        logger.info("[%s] Downloading PDF from %s", job_id, pdf_url)
        pdf_bytes = storage_service.read_pdf_bytes(pdf_url)
```

After:
```python
        # ---- Step 1: Download PDF -------------------------------------------
        with log_stage("pdf_download", logger=logger, job_id=job_id, doc_id=doc_id):
            pdf_bytes = storage_service.read_pdf_bytes(pdf_url)
```

Apply the same pattern to all steps:
- Step 1 → `log_stage("pdf_download", ...)`
- Step 2 → `log_stage("ocr", ...)`
- Step 3 → `log_stage("category_resolution", ...)`
- Step 4 → `log_stage("chunking", ...)`
- Step 5 → `log_stage("embedding", ...)`
- Step 6 → `log_stage("vector_upsert", ...)`
- Step 7 → `log_stage("entity_extraction", ...)`
- Step 8 → `log_stage("entity_normalization", ...)`
- Step 9 → `log_stage("neo4j_merge", ...)`

Keep the OCR JSON storage, confidence warnings, and chunk storage logic inside the relevant `log_stage` blocks. Steps 7-9 remain inside the existing `try/except` for graph failure isolation.

**Step 4: Add `log_stage` to query pipeline in `backend/app/services/hybrid_retrieval.py`**

Add import at top:
```python
from app.config.logging_config import log_stage
```

Wrap the major query stages in the `query()` method:

```python
    async def query(self, question, filter_categories=None):
        with log_stage("query_embed", logger=logger):
            query_embedding = await embeddings_service.embed_query(question)

        entity_hints = self._extract_entity_hints(question)

        with log_stage("query_search", logger=logger):
            vector_results, graph_result = await asyncio.gather(
                vector_search_service.search(query_embedding, filter_categories=filter_categories),
                self._graph_search(entity_hints, filter_categories),
                return_exceptions=True,
            )

        # ... (handle exceptions, merge, score — no timing needed for in-memory ops)

        with log_stage("llm_generation", logger=logger):
            llm_result = await llm_service.generate_answer(question, merged_context, source_type)

        # ... (build citations, return response)
```

**Step 5: Run all tests**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/ -v
```

Expected: all 11 tests PASS.

**Step 6: Commit**

```bash
cd C:/NUS/Projects/history
git add backend/app/routers/ingest.py backend/app/services/hybrid_retrieval.py backend/tests/test_log_stage.py
git commit -m "feat(5.1): pipeline stage timing — log_stage wraps ingestion + query steps

- 9 ingestion stages timed (pdf_download through neo4j_merge)
- 3 query stages timed (embed, search, llm_generation)
- Each stage logs start/completion/failure with duration_ms
- 2 unit tests for log_stage context manager"
```

---

## Task 6: Log-Based Alerting

**Files:**
- Create: `infra/logging/alert-policy.json`

This task sets up a Cloud Monitoring alert that fires when the error rate exceeds a threshold. This is a GCP resource, not application code.

**Step 1: Create the alert policy definition**

Create `infra/logging/alert-policy.json`:

```json
{
  "displayName": "Colonial Archives — High Error Rate",
  "documentation": {
    "content": "Error rate exceeded 5 errors/min for the colonial-archives-backend Cloud Run service. Check Cloud Logging for stack traces.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Error log entries > 5/min",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"colonial-archives-backend\" AND severity>=ERROR",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 5,
        "duration": "60s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ]
      }
    }
  ],
  "alertStrategy": {
    "autoClose": "604800s"
  }
}
```

**Step 2: Document the gcloud command to create the alert (run manually when deploying)**

Add a comment at the top of the file:

```
// Apply with:
// gcloud alpha monitoring policies create --policy-from-file=infra/logging/alert-policy.json --project=aihistory-488807
//
// Prerequisites:
// - Cloud Run service "colonial-archives-backend" must exist
// - Notification channel must be configured separately (email/Slack)
```

**Step 3: Commit**

```bash
cd C:/NUS/Projects/history
git add infra/logging/
git commit -m "feat(5.1): log-based alerting — error rate alert policy for Cloud Monitoring"
```

---

## Task 7: Frontend Test Script + Vitest Config

**Files:**
- Modify: `frontend/package.json` (add `test` script)
- Modify: `frontend/vite.config.ts` (add `test` config block)

**Step 1: Add `test` script to `frontend/package.json`**

Add to the `"scripts"` section:

```json
"test": "vitest run"
```

So scripts becomes:
```json
"scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "test": "vitest run",
    "preview": "vite preview"
}
```

**Step 2: Add test config to `frontend/vite.config.ts`**

The vitest config needs `environment: "jsdom"` for React component tests. Add a `test` block:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8090",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
});
```

Note: the `/// <reference types="vitest" />` directive may be needed at the top if TypeScript complains about the `test` property. Check if `vitest/config` types are already resolved.

**Step 3: Verify frontend tests pass**

```bash
cd C:/NUS/Projects/history/frontend
npm run test
```

Expected: 27 tests PASS (same tests that were passing before, now accessible via `npm run test`).

**Step 4: Verify frontend lint passes**

```bash
cd C:/NUS/Projects/history/frontend
npm run lint
```

Expected: passes (or reports warnings — note any issues).

**Step 5: Commit**

```bash
cd C:/NUS/Projects/history
git add frontend/package.json frontend/vite.config.ts
git commit -m "chore: add frontend test script and vitest jsdom config"
```

---

## Task 8: Backend Health Check Test

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Step 1: Write `backend/tests/conftest.py` — shared test fixtures**

The main challenge is that `app.main` imports services that call `vertexai.init()` at startup via the lifespan. For unit tests, we need to bypass the lifespan and mock GCP services.

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def mock_gcp():
    """Patch GCP services so FastAPI app can be imported without real credentials."""
    with (
        patch("app.services.neo4j_service.neo4j_service") as mock_neo4j,
        patch("vertexai.init"),
    ):
        mock_neo4j.verify_connectivity = AsyncMock(return_value=True)
        mock_neo4j.close = AsyncMock()
        yield {"neo4j": mock_neo4j}
```

**Step 2: Write `backend/tests/test_health.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_returns_ok_with_neo4j_connected(mock_gcp):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
```

**Step 3: Run to verify**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/test_health.py -v
```

Expected: 1 test PASS. If mocking issues occur (e.g. neo4j_service is imported before mock is applied), adjust the conftest fixture to patch at the correct import path.

**Step 4: Run full test suite**

```bash
cd C:/NUS/Projects/history/backend
python -m pytest tests/ -v
```

Expected: all tests PASS (logging + middleware + stage + health).

**Step 5: Commit**

```bash
cd C:/NUS/Projects/history
git add backend/tests/
git commit -m "test: add backend health check test with GCP mocks"
```

---

## Task 9: Dockerfile Hardening

**Files:**
- Modify: `backend/Dockerfile`

**Step 1: Update `backend/Dockerfile` with non-root user and better caching**

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 2: Verify Docker build succeeds**

```bash
cd C:/NUS/Projects/history/backend
docker build -t colonial-archives-backend:test .
```

Expected: builds successfully.

**Step 3: Commit**

```bash
cd C:/NUS/Projects/history
git add backend/Dockerfile
git commit -m "chore: Dockerfile hardening — non-root user for Cloud Run"
```

---

## Task 10: Cloud Build Pipeline (cloudbuild.yaml)

**Files:**
- Create: `cloudbuild.yaml` (at project root)

**Step 1: Create `cloudbuild.yaml`**

```yaml
# Cloud Build pipeline for Colonial Archives Graph-RAG
# Triggers: push to main branch
# Steps: lint → test → build → push → deploy → smoke test

steps:
  # ---- Backend Lint ----
  - name: "python:3.11-slim"
    id: "backend-lint"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        pip install --quiet ruff
        cd backend
        ruff check app/

  # ---- Backend Test ----
  - name: "python:3.11-slim"
    id: "backend-test"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        cd backend
        pip install --quiet -r requirements-dev.txt
        python -m pytest tests/ -v

  # ---- Frontend Lint + Type Check + Test ----
  - name: "node:20-slim"
    id: "frontend-checks"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        cd frontend
        npm ci --silent
        npm run lint
        npx tsc --noEmit
        npm run test

  # ---- Build Backend Docker Image ----
  - name: "gcr.io/cloud-builders/docker"
    id: "build-backend"
    waitFor: ["backend-lint", "backend-test"]
    args:
      - "build"
      - "-t"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}"
      - "./backend"

  # ---- Build Frontend Docker Image ----
  - name: "gcr.io/cloud-builders/docker"
    id: "build-frontend"
    waitFor: ["frontend-checks"]
    args:
      - "build"
      - "-t"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/frontend:${SHORT_SHA}"
      - "./frontend"

  # ---- Push Backend Image ----
  - name: "gcr.io/cloud-builders/docker"
    id: "push-backend"
    waitFor: ["build-backend"]
    args:
      - "push"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}"

  # ---- Push Frontend Image ----
  - name: "gcr.io/cloud-builders/docker"
    id: "push-frontend"
    waitFor: ["build-frontend"]
    args:
      - "push"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/frontend:${SHORT_SHA}"

  # ---- Deploy Backend to Cloud Run ----
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: "deploy-backend"
    waitFor: ["push-backend"]
    entrypoint: "gcloud"
    args:
      - "run"
      - "deploy"
      - "colonial-archives-backend"
      - "--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}"
      - "--region=${_REGION}"
      - "--platform=managed"
      - "--allow-unauthenticated"
      - "--port=8080"
      - "--memory=1Gi"
      - "--cpu=1"
      - "--min-instances=0"
      - "--max-instances=3"
      - "--set-secrets=NEO4J_URI=neo4j-uri:latest,NEO4J_USER=neo4j-user:latest,NEO4J_PASSWORD=neo4j-password:latest"

  # ---- Deploy Frontend to Cloud Run ----
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: "deploy-frontend"
    waitFor: ["push-frontend", "deploy-backend"]
    entrypoint: "gcloud"
    args:
      - "run"
      - "deploy"
      - "colonial-archives-frontend"
      - "--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/frontend:${SHORT_SHA}"
      - "--region=${_REGION}"
      - "--platform=managed"
      - "--allow-unauthenticated"
      - "--port=80"
      - "--memory=256Mi"
      - "--cpu=1"
      - "--min-instances=0"
      - "--max-instances=2"

  # ---- Smoke Test ----
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: "smoke-test"
    waitFor: ["deploy-backend"]
    entrypoint: "bash"
    args:
      - "-c"
      - |
        BACKEND_URL=$(gcloud run services describe colonial-archives-backend \
          --region=${_REGION} --format='value(status.url)')
        echo "Smoke testing $BACKEND_URL/health ..."
        curl -sf "$BACKEND_URL/health" | python3 -c "
        import json, sys
        data = json.load(sys.stdin)
        assert data['status'] == 'ok', f'Health check failed: {data}'
        print('Smoke test PASSED')
        "

substitutions:
  _REGION: asia-southeast1
  _REPO: colonial-archives

images:
  - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}"
  - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/frontend:${SHORT_SHA}"

options:
  logging: CLOUD_LOGGING_ONLY
```

**Step 2: Commit**

```bash
cd C:/NUS/Projects/history
git add cloudbuild.yaml
git commit -m "feat(5.7): Cloud Build CI/CD pipeline

- Backend: ruff lint + pytest
- Frontend: ESLint + tsc + vitest
- Docker build + push to Artifact Registry
- Cloud Run deploy (backend + frontend)
- Post-deploy smoke test on /health
- Parallel lint/test steps for speed"
```

---

## Task 11: GCP Infrastructure Setup

This task provisions the GCP resources needed for the CI/CD pipeline. These are **manual gcloud commands** run once, not application code.

**Step 1: Create Artifact Registry repository**

```bash
gcloud artifacts repositories create colonial-archives \
  --repository-format=docker \
  --location=asia-southeast1 \
  --description="Colonial Archives Graph-RAG Docker images" \
  --project=aihistory-488807
```

**Step 2: Create Secret Manager secrets for Cloud Run**

```bash
# Neo4j credentials (replace values from backend/.env)
echo -n "neo4j+s://ae76ab7c.databases.neo4j.io" | \
  gcloud secrets create neo4j-uri --data-file=- --project=aihistory-488807

echo -n "ae76ab7c" | \
  gcloud secrets create neo4j-user --data-file=- --project=aihistory-488807

echo -n "YOUR_NEO4J_PASSWORD" | \
  gcloud secrets create neo4j-password --data-file=- --project=aihistory-488807
```

**Step 3: Grant Cloud Build service account permissions**

```bash
PROJECT_NUMBER=$(gcloud projects describe aihistory-488807 --format='value(projectNumber)')

# Cloud Run deployer
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# Service account user (to act as Cloud Run service account)
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Artifact Registry writer
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Secret Manager accessor (for --set-secrets in deploy step)
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Step 4: Create Cloud Build trigger (connect GitHub repo first)**

```bash
# Option A: If using GitHub — connect repo in Cloud Console first, then:
gcloud builds triggers create github \
  --name="colonial-archives-main" \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --repo-name=history \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --project=aihistory-488807

# Option B: Manual trigger (no GitHub — submit builds manually):
gcloud builds submit . --config=cloudbuild.yaml --project=aihistory-488807
```

**Step 5: Test the pipeline manually**

```bash
cd C:/NUS/Projects/history
gcloud builds submit . --config=cloudbuild.yaml --project=aihistory-488807
```

This uploads the source and runs the full pipeline. Watch the output for each step.

---

## Summary

| Task | What | Commit |
|------|------|--------|
| 1 | Git init + first commit | `feat: Phases 1-3 complete` |
| 2 | Dev deps + ruff/pytest config | `chore: add dev dependencies` |
| 3 | JSON log formatter (TDD, 6 tests) | `feat(5.1): structured JSON log formatter` |
| 4 | Trace ID middleware (TDD, 3 tests) | `feat(5.1): trace ID middleware` |
| 5 | Pipeline stage timing (2 tests) | `feat(5.1): pipeline stage timing` |
| 6 | Log-based alerting config | `feat(5.1): log-based alerting` |
| 7 | Frontend test script + vitest config | `chore: frontend test script` |
| 8 | Backend health check test | `test: backend health check` |
| 9 | Dockerfile hardening | `chore: Dockerfile hardening` |
| 10 | cloudbuild.yaml | `feat(5.7): Cloud Build CI/CD pipeline` |
| 11 | GCP infra setup (manual gcloud) | No commit — infrastructure |

**Total: 11 tasks, ~12 tests, 10 commits**
