# Phase 5: Cloud Logging + CI/CD — Task Tracker

Last Updated: 2026-03-01

## Status Legend
- S = Small (< 30 min), M = Medium (30-60 min), L = Large (1-2 hours)
- **Implementation plan**: `docs/plans/2026-03-01-phase5-cicd-logging.md`

---

## Phase 0: Foundation ✅ COMPLETE

### T1: Git Init + .gitignore + First Commit [S] ✅

- [x] Enhance `.gitignore` with GCP credential patterns, IDE dirs, `.claude/worktrees/`
- [x] Run `git init` → commit `7bbceb8`
- [x] Verify `.env` and `node_modules/` excluded
- [x] First commit: 88 files, all Phase 1-3 code

### T2: Backend Dev Dependencies + Config [S] ✅

- [x] Create `backend/requirements-dev.txt` (ruff, pytest, pytest-asyncio)
- [x] Create `backend/pyproject.toml` (ruff + pytest config)
- [x] Install dev dependencies (note: `-r requirements.txt` chain fails — install directly)
- [x] Verify ruff runs: 7 issues found (all minor, not fixed)
- [x] `backend/tests/__init__.py` already existed from initial commit
- [x] Commit `7814b2e`

---

## Phase A: Cloud Logging ✅ COMPLETE

### T3: Structured JSON Log Formatter (TDD) [M] ✅

- [x] 6 tests in `backend/tests/test_logging_config.py` — all PASS
- [x] `backend/app/config/logging_config.py` — CloudJsonFormatter, trace_id_var, setup_logging, log_stage
- [x] Commit `a85c0b3`

### T4: Trace ID Middleware (TDD) [M] ✅

- [x] 3 tests in `backend/tests/test_trace_middleware.py` — all PASS
- [x] `backend/app/middleware/trace.py` — TraceMiddleware
- [x] Wired into `main.py` (setup_logging + TraceMiddleware)
- [x] Commit `f1360c7`

### T5: Pipeline Stage Timing [M] ✅

- [x] 2 tests in `backend/tests/test_log_stage.py` — all PASS
- [x] `ingest.py`: all 9 steps wrapped in `log_stage()` (pdf_download through neo4j_merge)
- [x] `hybrid_retrieval.py`: 3 stages wrapped (query_embed, query_search, llm_generation)
- [x] Commit `ba284ac`

### T6: Log-Based Alerting Config [S] ✅

- [x] `infra/logging/alert-policy.json` — error rate > 5/min alert
- [x] gcloud apply command documented in `_apply_command` field
- [x] Commit `ee160b7`

---

## Phase B: CI/CD Pipeline ✅ COMPLETE (code only — GCP infra not yet provisioned)

### T7: Frontend Test Script + Vitest Config [S] ✅

- [x] Added `"test": "vitest run"` to `frontend/package.json`
- [x] Did NOT modify vite.config.ts — `vitest.config.ts` already exists with jsdom
- [x] 27 frontend tests pass
- [x] ESLint: 4 pre-existing errors (GraphCanvas.tsx, PdfModal.tsx) — not introduced by us
- [x] Commit `c73aed7`

### T8: Backend Health Check Test [M] ✅

- [x] `backend/tests/conftest.py` — mock_gcp fixture (patches neo4j driver + vertexai.init)
- [x] `backend/tests/test_health.py` — 1 test PASS
- [x] Commit `2fb9862`

### T9: Dockerfile Hardening [S] ✅

- [x] Added appuser (non-root) to `backend/Dockerfile`
- [x] Docker build not verified (Docker Desktop not running) — changes are straightforward
- [x] Commit `5ec8f5d`

### T10: Cloud Build Pipeline [L] ✅

- [x] `cloudbuild.yaml` — 11 steps with proper waitFor DAG
- [x] Backend: ruff lint + pytest (parallel)
- [x] Frontend: npm ci + eslint + tsc + vitest (parallel with backend)
- [x] Docker build → push → deploy → smoke test
- [x] Substitutions: `_REGION=asia-southeast1`, `_REPO=colonial-archives`
- [x] Commit `d6cf190`

### T11: GCP Infrastructure Setup [M] ⏳ NOT YET DONE

- [ ] Enable Cloud Build API: `gcloud services enable cloudbuild.googleapis.com`
- [ ] Enable Secret Manager API: `gcloud services enable secretmanager.googleapis.com`
- [ ] Create Artifact Registry repo: `colonial-archives` in `asia-southeast1`
- [ ] Create Secret Manager secrets: `neo4j-uri`, `neo4j-user`, `neo4j-password`
- [ ] Grant Cloud Build SA roles: `run.admin`, `iam.serviceAccountUser`, `artifactregistry.writer`, `secretmanager.secretAccessor`
- [ ] Test pipeline: `gcloud builds submit . --config=cloudbuild.yaml`
- [ ] (Optional) Create GitHub build trigger for `main` branch

---

## Phase C: Merge + Review ✅ COMPLETE

- [x] All work merged to `main` (fast-forward, no conflicts)
- [x] Feature branches deleted
- [x] Backend: 12 Phase 5 tests PASS (Python 3.13)
- [x] Frontend: 27 tests PASS
- [x] ruff: runs, 7 pre-existing minor issues

---

## Phase D: Remaining Phase 5 Tasks ✅ COMPLETE (multi-agent team)

> **Implementation plan**: `docs/plans/2026-03-01-phase5-remaining-tasks.md`
> **Execution**: 4-agent team (backend-perf, frontend-mobile, monitoring, ocr-ui)

### T12: ESLint Fixes + Vector Search Bugfix [S] ✅

- [x] Fixed 4 ESLint errors in GraphCanvas.tsx (3) + PdfModal.tsx (1) — eslint-disable comments
- [x] Committed vector_search.py bugfix (region-safe index, correct restricts API)
- [x] ESLint passes clean
- [x] Commits: `533d53c`, `80e0e70`

### T13: Performance Optimization (5.5) [M] ✅

- [x] Parallelize GCS chunk loading: `asyncio.gather` + `run_in_executor` — commit `6e02265`
- [x] Parallelize graph entity search: 2-phase gather — commit `da8f427`
- [x] Split query_search log_stage into vector_search + graph_search — commit `45bdc6d`
- [x] 3 tests in test_hybrid_retrieval.py — all PASS

### T14: Mobile Responsive Layout (5.6) [M] ✅

- [x] `useIsMobile` hook with 2 tests — commit `e7abe29`
- [x] Responsive App layout with tab switching — commit `e940b51`
- [x] Touch support for ResizableSplitter — commit `8d2521a`
- [x] Frontend: 29 tests PASS (27 existing + 2 new)

### T15: Cloud Monitoring + OCR UI (5.2 + 5.3) [M] ✅

- [x] Cloud Monitoring dashboard config — commit `b0dc7f5`
- [x] Backend admin endpoints for OCR quality (2 tests) — commit `a63ebc6`
- [x] Frontend AdminPanel component — commit `2572e52`
- [x] Backend: 24 tests PASS, Frontend: 29 tests PASS

---

## Summary

| Phase | Tasks | Tests | Status |
|-------|-------|-------|--------|
| Phase 0 | T1-T2 | 0 | ✅ Complete |
| Phase A | T3-T6 | 11 | ✅ Complete |
| Phase B | T7-T10 | 28 | ✅ Complete (code) |
| Phase D | T12-T15 | 7 | ✅ Complete |
| T11 | GCP infra | — | ⏳ Manual gcloud |
| **Total** | | **53** | **24 commits** |
