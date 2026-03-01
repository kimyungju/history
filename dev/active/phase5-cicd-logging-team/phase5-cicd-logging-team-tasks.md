# Phase 5: Cloud Logging + CI/CD — Task Tracker

Last Updated: 2026-03-01

## Status Legend
- S = Small (< 30 min), M = Medium (30-60 min), L = Large (1-2 hours)
- Dependencies listed as [Depends: TX]
- **Implementation plan**: `docs/plans/2026-03-01-phase5-cicd-logging.md` (full code for every task)

---

## Phase 0: Foundation (Sequential — Leader)

### T1: Git Init + .gitignore + First Commit [S]

- [ ] Enhance `.gitignore` with GCP credential patterns, IDE dirs, `.claude/worktrees/`
- [ ] Run `git init`
- [ ] Verify `.env` and `node_modules/` are excluded from `git status`
- [ ] Stage all files and create first commit (Phases 1-3 complete)
- [ ] Verify commit succeeded

### T2: Backend Dev Dependencies + Config [S] [Depends: T1]

- [ ] Create `backend/requirements-dev.txt` (ruff, pytest, pytest-asyncio)
- [ ] Create `backend/pyproject.toml` (ruff + pytest config)
- [ ] Install dev dependencies: `pip install -r requirements-dev.txt`
- [ ] Verify ruff runs: `ruff check app/ --statistics`
- [ ] Create `backend/tests/__init__.py` (empty — needed by both teams)
- [ ] Commit: "chore: add dev dependencies — ruff, pytest, pytest-asyncio"

---

## Phase A: Cloud Logging — Team A (Worktree: `logging`)

### T3: Structured JSON Log Formatter (TDD) [M] [Depends: T2]

- [ ] Write 6 failing tests in `backend/tests/test_logging_config.py`
  - [ ] `test_json_formatter_outputs_valid_json_with_severity`
  - [ ] `test_json_formatter_includes_source_location`
  - [ ] `test_json_formatter_includes_trace_id_when_set`
  - [ ] `test_json_formatter_omits_trace_when_not_set`
  - [ ] `test_json_formatter_includes_extra_fields`
  - [ ] `test_json_formatter_includes_exception_traceback`
- [ ] Run tests — verify FAIL (ModuleNotFoundError)
- [ ] Implement `backend/app/config/logging_config.py` (CloudJsonFormatter, trace_id_var, setup_logging, log_stage)
- [ ] Run tests — verify all 6 PASS
- [ ] Commit: "feat(5.1): structured JSON log formatter with trace ID support"

### T4: Trace ID Middleware (TDD) [M] [Depends: T3]

- [ ] Write 3 failing tests in `backend/tests/test_trace_middleware.py`
  - [ ] `test_middleware_generates_trace_id`
  - [ ] `test_middleware_propagates_cloud_trace_header`
  - [ ] `test_middleware_sets_trace_in_contextvar`
- [ ] Run tests — verify FAIL (ModuleNotFoundError)
- [ ] Create `backend/app/middleware/__init__.py`
- [ ] Implement `backend/app/middleware/trace.py` (TraceMiddleware)
- [ ] Run tests — verify all 3 PASS
- [ ] Wire into `backend/app/main.py`:
  - [ ] Import `setup_logging` and `TraceMiddleware`
  - [ ] Call `setup_logging()` at start of lifespan
  - [ ] Add `app.add_middleware(TraceMiddleware)` after CORS
- [ ] Run full backend test suite — verify all 9 PASS
- [ ] Commit: "feat(5.1): trace ID middleware — Cloud Trace header propagation"

### T5: Pipeline Stage Timing [M] [Depends: T3]

- [ ] Write 2 tests in `backend/tests/test_log_stage.py`
  - [ ] `test_log_stage_logs_start_and_completion`
  - [ ] `test_log_stage_logs_failure_on_exception`
- [ ] Run tests — verify PASS (log_stage already implemented in T3)
- [ ] Modify `backend/app/routers/ingest.py`:
  - [ ] Import `log_stage`
  - [ ] Wrap Step 1 (pdf_download) in `log_stage`
  - [ ] Wrap Step 2 (ocr) in `log_stage`
  - [ ] Wrap Step 3 (category_resolution) in `log_stage`
  - [ ] Wrap Step 4 (chunking) in `log_stage`
  - [ ] Wrap Step 5 (embedding) in `log_stage`
  - [ ] Wrap Step 6 (vector_upsert) in `log_stage`
  - [ ] Wrap Step 7 (entity_extraction) in `log_stage`
  - [ ] Wrap Step 8 (entity_normalization) in `log_stage`
  - [ ] Wrap Step 9 (neo4j_merge) in `log_stage`
- [ ] Modify `backend/app/services/hybrid_retrieval.py`:
  - [ ] Import `log_stage`
  - [ ] Wrap query_embed stage
  - [ ] Wrap query_search stage
  - [ ] Wrap llm_generation stage
- [ ] Run full test suite — verify all 11 PASS
- [ ] Commit: "feat(5.1): pipeline stage timing — log_stage wraps ingestion + query steps"

### T6: Log-Based Alerting Config [S]

- [ ] Create `infra/logging/alert-policy.json` (error rate > 5/min alert)
- [ ] Add gcloud apply command as comment in file
- [ ] Commit: "feat(5.1): log-based alerting — error rate alert policy"

---

## Phase B: CI/CD Pipeline — Team B (Worktree: `cicd`)

### T7: Frontend Test Script + Vitest Config [S] [Depends: T2]

- [ ] Add `"test": "vitest run"` to `frontend/package.json` scripts
- [ ] Add `test: { environment: "jsdom", globals: true }` to `frontend/vite.config.ts`
- [ ] Run `npm run test` — verify 27 tests PASS
- [ ] Run `npm run lint` — verify passes
- [ ] Commit: "chore: add frontend test script and vitest jsdom config"

### T8: Backend Health Check Test [M] [Depends: T2]

- [ ] Create `backend/tests/conftest.py` with `mock_gcp` fixture
- [ ] Create `backend/tests/test_health.py`
  - [ ] `test_health_returns_ok_with_neo4j_connected`
- [ ] Run test — verify 1 PASS
- [ ] Run full backend test suite — verify all PASS
- [ ] Commit: "test: add backend health check test with GCP mocks"

### T9: Dockerfile Hardening [S]

- [ ] Add `appuser` group and user to `backend/Dockerfile`
- [ ] Add `chown` and `USER appuser` directives
- [ ] Run `docker build -t colonial-archives-backend:test ./backend` — verify build succeeds
- [ ] Commit: "chore: Dockerfile hardening — non-root user for Cloud Run"

### T10: Cloud Build Pipeline [L] [Depends: T7, T8, T9]

- [ ] Create `cloudbuild.yaml` at project root with steps:
  - [ ] `backend-lint` — ruff check
  - [ ] `backend-test` — pytest
  - [ ] `frontend-checks` — npm ci + lint + tsc + vitest
  - [ ] `build-backend` — Docker build (waitFor lint + test)
  - [ ] `build-frontend` — Docker build (waitFor frontend-checks)
  - [ ] `push-backend` — push to Artifact Registry
  - [ ] `push-frontend` — push to Artifact Registry
  - [ ] `deploy-backend` — Cloud Run deploy with Secret Manager refs
  - [ ] `deploy-frontend` — Cloud Run deploy
  - [ ] `smoke-test` — curl /health + assert status OK
- [ ] Add substitutions (_REGION, _REPO) and images list
- [ ] Commit: "feat(5.7): Cloud Build CI/CD pipeline"

### T11: GCP Infrastructure Setup [M] [Depends: T10]

- [ ] Enable Cloud Build API: `gcloud services enable cloudbuild.googleapis.com`
- [ ] Enable Secret Manager API: `gcloud services enable secretmanager.googleapis.com`
- [ ] Create Artifact Registry repo: `colonial-archives` in `asia-southeast1`
- [ ] Create Secret Manager secrets: `neo4j-uri`, `neo4j-user`, `neo4j-password`
- [ ] Grant Cloud Build SA roles: `run.admin`, `iam.serviceAccountUser`, `artifactregistry.writer`, `secretmanager.secretAccessor`
- [ ] Test pipeline: `gcloud builds submit . --config=cloudbuild.yaml`
- [ ] (Optional) Create GitHub build trigger for `main` branch

---

## Phase C: Merge + Review (Leader)

### Merge Worktrees [S]

- [ ] Merge `logging` worktree branch into main
- [ ] Merge `cicd` worktree branch into main
- [ ] Resolve any conflicts (expected: `backend/tests/__init__.py` — trivial)
- [ ] Run full backend test suite: `python -m pytest tests/ -v` (expect 12+ tests PASS)
- [ ] Run full frontend test suite: `npm run test` (expect 27 tests PASS)
- [ ] Run ruff: `ruff check app/` (expect clean or known warnings only)

### Code Review [M]

- [ ] Review: JSON log output format matches Cloud Logging spec
- [ ] Review: Trace middleware correctly resets contextvar
- [ ] Review: log_stage doesn't swallow exceptions
- [ ] Review: ingest.py pipeline steps correctly wrapped (no logic change)
- [ ] Review: hybrid_retrieval.py timing doesn't change query behavior
- [ ] Review: cloudbuild.yaml step dependencies form correct DAG
- [ ] Review: Dockerfile non-root user doesn't break uvicorn
- [ ] Review: No secrets committed to git

---

## Summary

| Phase | Tasks | Tests | Team | Estimated |
|-------|-------|-------|------|-----------|
| Phase 0 | T1-T2 | 0 | Leader | 15 min |
| Phase A | T3-T6 | 11 | logging-agent | 45 min |
| Phase B | T7-T11 | 28 | cicd-agent | 45 min |
| Phase C | Merge | All | Leader | 15 min |
| **Total** | **11** | **39** | **3 agents** | **~1.5 hours** |
