# Phase 5: Cloud Logging (5.1) + CI/CD Pipeline (5.7) — Multi-Team Execution Plan

Last Updated: 2026-03-01

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Implementation plan reference:** `docs/plans/2026-03-01-phase5-cicd-logging.md`

---

## Executive Summary

Add production observability and deployment automation to the Colonial Archives Graph-RAG system. Two workstreams execute in parallel after a shared foundation phase: **Cloud Logging** (structured JSON logs, trace IDs, pipeline timing) and **CI/CD** (Cloud Build pipeline with lint, test, Docker build, Cloud Run deploy, smoke test). A sequential Phase 0 initializes the git repo and dev dependencies before the teams split.

**Outcome:** Every request gets a trace ID in logs. Every ingestion/query stage is timed. Every push to main triggers an automated lint → test → build → deploy → smoke-test pipeline.

---

## Current State Analysis

| Component | State |
|---|---|
| Git repository | **Not initialized** — no commits exist |
| Backend logging | `logging.getLogger()` with default text formatter — no structure, no trace IDs, no timing |
| Backend tests | **None** — no pytest, no test directory |
| Backend linting | **None** — no ruff/flake8 |
| Frontend tests | 27 tests pass via `npx vitest run`, but no `"test"` script in `package.json` |
| Frontend linting | ESLint configured, `npm run lint` works |
| CI/CD pipeline | **None** — no `cloudbuild.yaml`, no GitHub Actions, no build triggers |
| Docker security | Backend Dockerfile runs as root, no `USER` directive |
| Artifact Registry | **Not created** — no Docker image repository |
| Cloud Run | **Not deployed** — local development only |
| Secret Manager | **Not configured** — secrets in `.env` file only |

---

## Proposed Future State

```
                    ┌─────────────────────────────┐
                    │     Phase 0 (Sequential)     │
                    │  Task 1: git init + commit   │
                    │  Task 2: dev deps + config   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │                              │
          ┌─────────▼──────────┐      ┌────────────▼─────────┐
          │  Team A: Logging   │      │   Team B: CI/CD      │
          │  (worktree)        │      │   (worktree)         │
          │                    │      │                      │
          │  T3: JSON formatter│      │  T7: Frontend test   │
          │  T4: Trace midware │      │  T8: Backend health  │
          │  T5: Stage timing  │      │  T9: Dockerfile      │
          │  T6: Alert policy  │      │  T10: cloudbuild.yaml│
          │                    │      │  T11: GCP infra      │
          └─────────┬──────────┘      └────────────┬─────────┘
                    │                              │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     Leader: Merge + Review    │
                    │  Resolve conflicts if any     │
                    │  Run full test suite           │
                    │  Final commit                  │
                    └─────────────────────────────┘
```

---

## Implementation Phases

### Phase 0: Foundation (Sequential — Leader executes)

Must complete before teams start. Creates the git repo and installs dev tooling that both teams need.

| Task | Description | Effort | Deps |
|------|-------------|--------|------|
| T1 | Git init + .gitignore + first commit | S | None |
| T2 | `requirements-dev.txt` + `pyproject.toml` (ruff, pytest) | S | T1 |

### Phase A: Cloud Logging (Team A — worktree `logging`)

All new files — no conflicts with Team B. Modifies `main.py`, `ingest.py`, `hybrid_retrieval.py`.

| Task | Description | Effort | Deps |
|------|-------------|--------|------|
| T3 | Structured JSON log formatter (TDD, 6 tests) | M | T2 |
| T4 | Trace ID middleware (TDD, 3 tests) + wire into `main.py` | M | T3 |
| T5 | Pipeline stage timing + wrap ingestion/query (2 tests) | M | T3 |
| T6 | Log-based alerting config (`alert-policy.json`) | S | None |

### Phase B: CI/CD Pipeline (Team B — worktree `cicd`)

Touches frontend config, backend Dockerfile, creates `cloudbuild.yaml`. No overlap with Team A files.

| Task | Description | Effort | Deps |
|------|-------------|--------|------|
| T7 | Frontend `"test"` script + vitest jsdom config | S | T2 |
| T8 | Backend health check test + `conftest.py` | M | T2 |
| T9 | Dockerfile hardening (non-root user) | S | None |
| T10 | `cloudbuild.yaml` (lint → test → build → deploy → smoke) | L | T7, T8, T9 |
| T11 | GCP infra setup (Artifact Registry, Secret Manager, IAM) | M | T10 |

### Phase C: Merge + Review (Leader)

| Task | Description | Effort |
|------|-------------|--------|
| Merge | Merge both worktree branches into main | S |
| Verify | Run full backend + frontend test suites | S |
| Review | Code review merged result | M |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Merge conflict on `backend/tests/__init__.py` | High | Low | Both teams create it — trivial auto-resolve (empty file) |
| `conftest.py` mock patching fails due to lazy init pattern | Medium | Medium | Team B tests with `mock_gcp` fixture; adjust patch paths if needed |
| Cloud Build step fails on first run | High | Low | Expected — iterate on `cloudbuild.yaml` locally with `gcloud builds submit` |
| Neo4j AuraDB paused (3-day inactivity) | Medium | Low | Health test mocks Neo4j; real connectivity not needed |
| `ruff check` finds many existing lint issues | High | Low | Don't fix all now — just verify ruff runs; can suppress with `# noqa` or per-file ignores |

---

## Success Metrics

- [ ] Git repo initialized with clean first commit
- [ ] `python -m pytest tests/ -v` passes all backend tests (11+ tests)
- [ ] `npm run test` passes all frontend tests (27 tests)
- [ ] `ruff check app/` runs without crashing (warnings OK)
- [ ] All log output is structured JSON when `setup_logging()` is called
- [ ] Every HTTP request gets a trace ID in response header and logs
- [ ] Ingestion pipeline logs timing for all 9 stages
- [ ] Query pipeline logs timing for embed, search, and LLM stages
- [ ] `cloudbuild.yaml` defines complete lint → test → build → deploy → smoke pipeline
- [ ] Backend Dockerfile runs as non-root user
- [ ] Alert policy JSON ready for `gcloud` deployment

---

## Required Resources

| Resource | Status | Notes |
|----------|--------|-------|
| GCP Project `aihistory-488807` | Active | Owner access required for IAM + Secret Manager |
| Artifact Registry | **Not created** | Task 11 creates it |
| Cloud Build API | **Must enable** | `gcloud services enable cloudbuild.googleapis.com` |
| Secret Manager API | **Must enable** | `gcloud services enable secretmanager.googleapis.com` |
| Neo4j AuraDB | Active (may be paused) | Only needed for live testing, not unit tests |
| Python 3.11+ | Installed (3.13 on host) | Dockerfile uses 3.11-slim |
| Node.js 20+ | Installed | Frontend tests use vitest |

---

## Timeline Estimate

| Phase | Duration | Parallelism |
|-------|----------|-------------|
| Phase 0 (Foundation) | ~15 min | Sequential |
| Phase A (Logging) | ~45 min | Parallel with B |
| Phase B (CI/CD) | ~45 min | Parallel with A |
| Phase C (Merge + Review) | ~15 min | Sequential |
| **Total** | **~1.5 hours** | With parallel teams |
| Without parallelism | ~2.5 hours | Sequential |
