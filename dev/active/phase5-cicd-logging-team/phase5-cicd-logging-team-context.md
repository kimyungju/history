# Phase 5: Cloud Logging + CI/CD — Context Document

Last Updated: 2026-03-01

---

## Key Files — Team A (Cloud Logging)

### Files to CREATE

| File | Purpose |
|------|---------|
| `backend/app/config/logging_config.py` | `CloudJsonFormatter`, `trace_id_var` ContextVar, `setup_logging()`, `log_stage()` |
| `backend/app/middleware/__init__.py` | Package init (empty) |
| `backend/app/middleware/trace.py` | `TraceMiddleware` — extracts `X-Cloud-Trace-Context` or generates UUID |
| `backend/tests/__init__.py` | Package init (empty) |
| `backend/tests/test_logging_config.py` | 6 tests for CloudJsonFormatter |
| `backend/tests/test_trace_middleware.py` | 3 tests for TraceMiddleware |
| `backend/tests/test_log_stage.py` | 2 tests for log_stage context manager |
| `infra/logging/alert-policy.json` | Cloud Monitoring error rate alert policy |

### Files to MODIFY

| File | Lines | Change |
|------|-------|--------|
| `backend/app/main.py` | 1-57 | Add `setup_logging()` import + call in lifespan; add `TraceMiddleware` after CORS |
| `backend/app/routers/ingest.py` | 68-246 | Wrap 9 pipeline steps in `log_stage()` context managers |
| `backend/app/services/hybrid_retrieval.py` | 50-166 | Wrap query embed, search, LLM generation in `log_stage()` |

### Conflict Risk with Team B

**LOW.** Team A touches `main.py`, `ingest.py`, `hybrid_retrieval.py`. Team B does NOT touch any of these. Only shared file is `backend/tests/__init__.py` (trivial merge — empty file).

---

## Key Files — Team B (CI/CD)

### Files to CREATE

| File | Purpose |
|------|---------|
| `backend/requirements-dev.txt` | Dev dependencies: ruff, pytest, pytest-asyncio |
| `backend/pyproject.toml` | ruff + pytest configuration |
| `backend/tests/conftest.py` | `mock_gcp` fixture (patches Neo4j + vertexai.init) |
| `backend/tests/test_health.py` | Health endpoint test with mocked GCP |
| `cloudbuild.yaml` | Full CI/CD pipeline (11 steps) |

### Files to MODIFY

| File | Lines | Change |
|------|-------|--------|
| `frontend/package.json:7-11` | Add `"test": "vitest run"` to scripts |
| `frontend/vite.config.ts` | Add `test: { environment: "jsdom", globals: true }` block |
| `backend/Dockerfile` | Add non-root user (`appuser`), `USER` directive |

### Conflict Risk with Team A

**LOW.** Team B touches `package.json`, `vite.config.ts`, `Dockerfile`, `cloudbuild.yaml`. Team A does NOT touch any of these.

---

## Architectural Decisions

### D1: Structured JSON to stdout (NOT google-cloud-logging library)

**Decision:** Output Cloud Logging-compatible JSON to stdout. Cloud Run's log agent auto-captures and sends to Cloud Logging.

**Rationale:**
- Simpler — no extra dependency
- Works identically in dev (readable JSON) and prod (auto-parsed by Cloud Logging)
- Cloud Run documentation recommends this approach
- Avoids background transport complexity

### D2: Trace IDs via contextvars (NOT threading.local)

**Decision:** Use Python `contextvars.ContextVar` for request-scoped trace ID propagation.

**Rationale:**
- Native async support — works with `asyncio.gather` and concurrent tasks
- `threading.local` breaks in async context (multiple coroutines share one thread)
- FastAPI + Starlette recommend contextvars for request-scoped state

### D3: Cloud Build (NOT GitHub Actions)

**Decision:** Use Google Cloud Build for CI/CD.

**Rationale:**
- Already on GCP — no additional vendor
- Native Artifact Registry + Cloud Run integration
- Can run without GitHub (manual `gcloud builds submit`)
- Build triggers can be added later when GitHub is connected

### D4: ruff (NOT flake8 + isort + black)

**Decision:** Use ruff as the sole Python linting tool.

**Rationale:**
- Single tool replaces flake8 + isort + black + pyflakes
- 10-100x faster than alternatives
- Drop-in compatible rule sets
- Active maintenance, modern Python support

### D5: Non-root Dockerfile (NOT root user)

**Decision:** Add `appuser` to backend Dockerfile.

**Rationale:**
- Cloud Run best practice — principle of least privilege
- Required for some security scanning tools
- No functionality impact (app doesn't need root)

---

## Environment & Dependencies

### Backend (Python 3.11)

```
# requirements.txt (existing)
fastapi==0.115.6, uvicorn[standard]==0.34.0, pydantic==2.10.4,
pydantic-settings==2.7.1, google-cloud-documentai==2.32.0,
google-cloud-storage==2.19.0, google-cloud-aiplatform==1.71.1,
vertexai==1.71.1, python-multipart==0.0.20, httpx==0.28.1,
neo4j==5.27.0, rapidfuzz==3.10.1

# requirements-dev.txt (NEW — includes all of above plus:)
ruff>=0.9.0, pytest>=8.0, pytest-asyncio>=0.25
```

### Frontend (Node 20)

```json
// Existing dev deps relevant to CI:
"vitest": "^4.0.18",
"eslint": "^9.39.1",
"typescript": "~5.9.3",
"jsdom": "^28.1.0",
"@testing-library/react": "^16.3.2"
```

### GCP Project

| Setting | Value |
|---------|-------|
| Project ID | `aihistory-488807` |
| Region | `asia-southeast1` |
| LLM Region | `us-central1` (Gemini not in SEA) |
| Artifact Registry repo | `colonial-archives` (to be created) |
| Cloud Run backend service | `colonial-archives-backend` |
| Cloud Run frontend service | `colonial-archives-frontend` |

---

## Testing Strategy

### Backend Tests (NEW — created by this phase)

| Test File | Tests | What |
|-----------|-------|------|
| `test_logging_config.py` | 6 | CloudJsonFormatter: severity, source location, trace ID, extras, exception |
| `test_trace_middleware.py` | 3 | TraceMiddleware: generates ID, propagates Cloud Trace header, sets contextvar |
| `test_log_stage.py` | 2 | log_stage: logs start+completion with timing, logs failure on exception |
| `test_health.py` | 1 | `/health` returns 200 with `{"status": "ok"}` (mocked GCP) |

All backend tests run without GCP credentials (mocked via `conftest.py`).

### Frontend Tests (EXISTING — 27 tests)

Run via `npm run test` (new script) / `npx vitest run`. No changes to test files.

---

## Reference: Implementation Plan Location

Full step-by-step implementation with exact code: `docs/plans/2026-03-01-phase5-cicd-logging.md`

Each task in that plan has:
- Exact file paths
- Complete code (copy-paste ready)
- Exact commands with expected output
- TDD flow (test first → verify fail → implement → verify pass → commit)
