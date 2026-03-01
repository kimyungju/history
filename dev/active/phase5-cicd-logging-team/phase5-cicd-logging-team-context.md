# Phase 5: Cloud Logging + CI/CD — Context Document

Last Updated: 2026-03-01

## Implementation Status: ✅ ALL CODE COMPLETE (T11 GCP infra remaining)

All application code, tests, and CI/CD config are committed to `main` (24 commits). Phases 5.1-5.3 and 5.5-5.7 are code complete. The only remaining work is provisioning GCP infrastructure (Artifact Registry, Secret Manager, IAM, build trigger).

---

## Commits (in order)

| SHA | Message | Task |
|-----|---------|------|
| `7bbceb8` | feat: Phases 1-3 complete | T1 |
| `7814b2e` | chore: add dev dependencies | T2 |
| `c73aed7` | chore: add frontend test script | T7 |
| `a85c0b3` | feat(5.1): structured JSON log formatter | T3 |
| `2fb9862` | test: backend health check test | T8 |
| `f1360c7` | feat(5.1): trace ID middleware | T4 |
| `5ec8f5d` | chore: Dockerfile hardening | T9 |
| `d6cf190` | feat(5.7): Cloud Build CI/CD pipeline | T10 |
| `ba284ac` | feat(5.1): pipeline stage timing | T5 |
| `ee160b7` | feat(5.1): log-based alerting | T6 |
| `533d53c` | fix: vector search region-safe index + correct restricts API | T12 |
| `b0dc7f5` | feat(5.2): Cloud Monitoring dashboard config | T15 |
| `80e0e70` | fix: resolve 4 ESLint errors in GraphCanvas and PdfModal | T12 |
| `6e02265` | perf: parallelize GCS chunk loading in hybrid retrieval | T13 |
| `a63ebc6` | feat(5.3): admin endpoints for OCR quality | T15 |
| `e7abe29` | feat(5.6): useIsMobile hook | T14 |
| `e940b51` | feat(5.6): responsive mobile layout — tab switching | T14 |
| `da8f427` | perf: parallelize graph entity search in hybrid retrieval | T13 |
| `8d2521a` | feat(5.6): touch support for ResizableSplitter | T14 |
| `45bdc6d` | perf: split query_search log_stage into vector_search + graph_search | T13 |
| `2572e52` | feat(5.3): OCR confidence flagging UI — admin panel | T15 |

---

## Files Created/Modified

### New Files (Phase 5)
| File | Purpose |
|------|---------|
| `backend/app/config/logging_config.py` | CloudJsonFormatter, trace_id_var, setup_logging(), log_stage() |
| `backend/app/middleware/__init__.py` | Package init |
| `backend/app/middleware/trace.py` | TraceMiddleware — X-Cloud-Trace-Context propagation |
| `backend/app/routers/admin.py` | GET /admin/documents, GET /admin/documents/{doc_id}/ocr |
| `backend/tests/conftest.py` | mock_gcp fixture (patches neo4j + vertexai.init) |
| `backend/tests/test_logging_config.py` | 6 tests for CloudJsonFormatter |
| `backend/tests/test_trace_middleware.py` | 3 tests for TraceMiddleware |
| `backend/tests/test_log_stage.py` | 2 tests for log_stage context manager |
| `backend/tests/test_health.py` | 1 test for /health endpoint |
| `backend/tests/test_hybrid_retrieval.py` | 3 tests for parallel GCS + graph search |
| `backend/tests/test_admin.py` | 2 tests for admin OCR quality endpoints |
| `backend/requirements-dev.txt` | ruff, pytest, pytest-asyncio |
| `backend/pyproject.toml` | ruff (py311, 120 chars) + pytest (asyncio auto) config |
| `cloudbuild.yaml` | 11-step Cloud Build pipeline |
| `infra/logging/alert-policy.json` | Cloud Monitoring error rate alert |
| `infra/monitoring/dashboard.json` | Cloud Monitoring dashboard (4 widgets) |
| `frontend/src/hooks/useIsMobile.ts` | Media query breakpoint detection (768px) |
| `frontend/src/hooks/__tests__/useIsMobile.test.ts` | 2 tests for useIsMobile |
| `frontend/src/components/AdminPanel.tsx` | OCR quality admin modal |

### Modified Files
| File | Change |
|------|--------|
| `backend/app/main.py` | Added setup_logging() in lifespan + TraceMiddleware + admin router |
| `backend/app/routers/ingest.py` | All 9 pipeline steps wrapped in log_stage() |
| `backend/app/services/hybrid_retrieval.py` | Parallel GCS, parallel graph, split log stages |
| `backend/app/services/vector_search.py` | Region-safe index, correct restricts API |
| `backend/Dockerfile` | Added appuser (non-root) |
| `frontend/package.json` | Added "test": "vitest run" |
| `frontend/src/App.tsx` | Mobile responsive layout + admin toggle |
| `frontend/src/stores/useAppStore.ts` | Added mobileTab, isAdminOpen state |
| `frontend/src/components/GraphCanvas.tsx` | ESLint disable comments (3) |
| `frontend/src/components/PdfModal.tsx` | ESLint disable comment (1) |
| `frontend/src/components/ResizableSplitter.tsx` | Touch support (onTouchStart/Move/End) |
| `frontend/src/api/client.ts` | Added listDocuments, getOcrQuality methods |
| `.gitignore` | Added GCP credentials, IDE, .claude/worktrees/ |

---

## Key Decisions Made This Session

1. **Structured JSON to stdout** — not google-cloud-logging lib. Cloud Run auto-captures stdout.
2. **contextvars for trace IDs** — async-safe (threading.local breaks with asyncio.gather)
3. **Cloud Build** — native GCP, no additional vendor (GitHub Actions would work too)
4. **ruff** — single tool replaces flake8+isort+black, 10-100x faster
5. **Worktrees didn't work** on Windows — fallback to shared directory with separate branches

## Issues Discovered
- `requirements-dev.txt` with `-r requirements.txt` fails pip resolution — install tools directly
- Python 3.14 (bash default) missing vertexai — must use Python 3.13 full path
- 4 pre-existing ESLint errors in frontend — FIXED in T12 with eslint-disable comments
- Docker Desktop not running — couldn't verify Dockerfile build locally
- Multi-agent teams work well with file-partitioned parallel agents (no worktrees needed)

## Remaining: T11 GCP Infrastructure (manual gcloud commands)

```bash
# 1. Enable APIs
gcloud services enable cloudbuild.googleapis.com --project=aihistory-488807
gcloud services enable secretmanager.googleapis.com --project=aihistory-488807

# 2. Create Artifact Registry
gcloud artifacts repositories create colonial-archives \
  --repository-format=docker --location=asia-southeast1 --project=aihistory-488807

# 3. Create secrets
echo -n "neo4j+s://ae76ab7c.databases.neo4j.io" | gcloud secrets create neo4j-uri --data-file=- --project=aihistory-488807
echo -n "ae76ab7c" | gcloud secrets create neo4j-user --data-file=- --project=aihistory-488807
echo -n "YOUR_PASSWORD" | gcloud secrets create neo4j-password --data-file=- --project=aihistory-488807

# 4. IAM for Cloud Build SA
PROJECT_NUMBER=$(gcloud projects describe aihistory-488807 --format='value(projectNumber)')
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding aihistory-488807 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 5. Test pipeline
gcloud builds submit . --config=cloudbuild.yaml --project=aihistory-488807
```
