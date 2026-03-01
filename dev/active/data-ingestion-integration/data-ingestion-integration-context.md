# Data Ingestion & Integration — Context Reference

**Last Updated: 2026-03-01 (Session 2 — post-ingestion)**

---

## Key Files

### Must Read Before Starting

| File | Purpose | Agent |
|------|---------|-------|
| `backend/app/config/document_categories.json` | Category mappings — edit this | setup-agent |
| `backend/app/models/schemas.py:4-10` | `MAIN_CATEGORIES` list — source of truth for valid categories | setup-agent |
| `backend/app/routers/ingest.py` | Ingestion endpoint + background pipeline + job tracking | ingestion-agent |
| `backend/app/services/storage.py:97-106` | `get_doc_id_from_url()` — how doc IDs derived from filenames | ingestion-agent |
| `backend/app/main.py` | Server startup, lifespan, Neo4j init | ingestion-agent |
| `frontend/vite.config.ts` | Proxy config (`/api` → `localhost:8090`) | testing-agent |
| `frontend/src/api/client.ts` | API client methods (postQuery, searchGraph, getSignedUrl) | testing-agent |
| `.gitignore` | Must cover `.env`, `__pycache__/`, `node_modules/` | setup-agent |

### Modified This Session

| File | Change | Commit |
|------|--------|--------|
| `backend/app/config/document_categories.json` | Populated 28 PDF-to-category mappings | setup-agent commit |
| `backend/app/services/vector_search.py` | Fixed Restriction class, namespace, region contamination | `74e34c6` |
| `backend/app/services/ocr.py` | Added pypdf splitting for > 40MB PDFs | `74e34c6` |
| `backend/app/services/embeddings.py` | Reduced batch size from 250 to 40 | `f55a956` |
| `backend/app/routers/ingest.py` | Wrapped GCS calls in run_in_executor | `f55a956` |
| `backend/app/services/storage.py` | Added timeout=300 for large downloads | `f55a956` |
| `backend/app/services/entity_extraction.py` | Concurrent extraction with Semaphore(5) | `f55a956` |
| `backend/requirements.txt` | Added pypdf==6.7.4 | `74e34c6` |

### Read-Only References

| File | Contains |
|------|----------|
| `backend/.env` | Real GCP + Neo4j credentials (gitignored) |
| `backend/.env.example` | Template showing required env vars |
| `backend/requirements.txt` | 13 Python packages |
| `frontend/package.json` | React 18, Cytoscape.js, Zustand, pdfjs-dist |
| `infra/docker-compose.yml` | Production Docker setup (not used this session) |

---

## Key Decisions

### Already Made (Do Not Change)

1. **Port 8090** for backend (8080 was stuck in earlier session)
2. **Vite proxy** `/api` → `http://localhost:8090` (already configured)
3. **No auth** — publicly digitized archives, friction-free researcher access
4. **MERGE not CREATE** in Neo4j — idempotent re-ingestion safe
5. **Graph failures non-blocking** — steps 7-9 wrapped in try/except
6. **Entity normalization threshold** — 0.85 for both embedding and fuzzy match
7. **Doc ID = filename stem** — e.g., `CO 273:550:11.pdf` → `CO 273:550:11`

### Decisions Made This Session

1. **Ingested 13+ PDFs** — Batch 1 (5 small), Batch 2 (5 medium), plus 3 large PDFs that fit under limits
2. **Categories assigned by sub-series:**
   - CO 273:534 → `["General and Establishment"]`
   - CO 273:550 → `["General and Establishment", "Economic and Financial"]`
   - CO 273:579 → `["General and Establishment"]`
3. **pypdf splitting for > 40 MB PDFs** — sub-PDFs of 15 pages each sent to Document AI
4. **Embedding batch size reduced to 40** — prevents 20K token limit errors
5. **All blocking I/O wrapped in run_in_executor** — GCS download/upload, prevents event loop starvation
6. **Entity extraction made concurrent** — `asyncio.gather()` with `Semaphore(5)` instead of sequential loop
7. **Max 2-3 concurrent large PDF ingestions** — more causes backend OOM/crashes
8. **PDFs > 95 MB still unsolved** — consistently return 0 pages, deferred to future investigation

---

## Dependencies Between Tasks

```
A1 (git init) ──────┐
                     ├──> A3 (commit) ──> B1 (start backend)
A2 (categories) ────┘                         │
                                               v
                                    B2 (ingest batch 1)
                                         │          │
                                         v          v
                              B3 (ingest batch 2)  C1 (start frontend)
                                    │                    │
                                    v                    v
                              B4 (verify data)     C2 (API smoke tests)
                                                         │
                                                         v
                                                   C3 (browser tests)
                                                         │
                                                         v
                                                   C4 (final commit)
```

---

## GCS Bucket Contents (Complete Inventory)

**Bucket:** `gs://aihistory-co273-nus/`

| # | Filename | Size | Tier | Status |
|---|----------|------|------|--------|
| 1 | CO 273:550:18.pdf | 3.2 MB | Small | ✅ Ingested (session 1) |
| 2 | CO 273:550:5.pdf | 5.8 MB | Small | ✅ Ingested (Batch 1) |
| 3 | CO 273:550:11.pdf | 6.2 MB | Small | ✅ Ingested (Batch 1) |
| 4 | CO 273:550:10.pdf | 7.9 MB | Small | ✅ Ingested (Batch 1) |
| 5 | CO 273:534:11b.pdf | 9.5 MB | Small | ✅ Ingested (Batch 1) |
| 6 | CO 273:550:21.pdf | 11.3 MB | Small | ✅ Ingested (Batch 1) |
| 7 | CO 273:534:6.pdf | 14.6 MB | Medium | ⚠️ Vector only (no graph — re-ingest needed) |
| 8 | CO 273:534:7.pdf | 17.3 MB | Medium | ✅ Ingested (Batch 2) |
| 9 | CO 273:534:13.pdf | 23.1 MB | Medium | ✅ Ingested (Batch 2) |
| 10 | CO 273:534:5.pdf | 27.9 MB | Medium | ✅ Ingested (Batch 2) |
| 11 | CO 273:534:24.pdf | 29.5 MB | Medium | ✅ Ingested (Batch 2) |
| 12 | CO 273:579:4.pdf | ~50 MB | Large | ✅ Ingested |
| 13 | CO 273:550:1.pdf | 50.9 MB | Large | ✅ Ingested (43 pages, 57 chunks) |
| 14 | CO 273:579:3.pdf | ~65 MB | Large | ✅ Likely ingested (agent completed) |
| 15 | CO 273:550:13.pdf | ~55 MB | Large | ❓ Unknown |
| 16 | CO 273:550:3.pdf | ~60 MB | Large | ❓ Unknown |
| 17 | CO 273:550:14.pdf | ~62 MB | Large | ❓ Unknown (agent task completed) |
| 18 | CO 273:550:19.pdf | ~70 MB | Large | ❓ Unknown |
| 19 | CO 273:534:9.pdf | ~75 MB | Large | ❓ Unknown |
| 20 | CO 273:534:15b.pdf | ~78 MB | Large | ❓ Unknown |
| 21 | CO 273:579:2b.pdf | ~82 MB | Large | ❓ Unknown |
| 22 | CO 273:579:1.pdf | ~95 MB | XL | ❓ Unknown |
| 23 | CO 273:550:8.pdf | ~110 MB | XL | ❓ Unknown |
| 24 | CO 273:534:15a.pdf | ~130 MB | XL | ❌ FAILED (0 pages) |
| 25 | CO 273:534:2.pdf | ~140 MB | XL | ❌ FAILED (0 pages) |
| 26 | CO 273:534:11a.pdf | ~170 MB | XL | ❌ FAILED (0 pages) |
| 27 | CO 273:534:3.pdf | ~200 MB | XL | ❌ FAILED (0 pages) |
| 28 | CO 273:579:2a.pdf | ~278 MB | XL | ❌ FAILED (0 pages) |

---

## API Endpoints Used

### Ingestion (ingestion-agent)

```bash
# Submit PDF for ingestion
POST http://127.0.0.1:8090/ingest_pdf
Body: {"pdf_url": "gs://aihistory-co273-nus/CO 273:550:5.pdf"}
Returns: {"job_id": "<uuid>", "status": "processing", ...}

# Poll job status
GET http://127.0.0.1:8090/ingest_status/{job_id}
Returns: {"job_id": "...", "status": "done"|"processing"|"failed",
          "pages_total": N, "chunks_processed": N, "entities_extracted": N}
```

### Health Check (all agents)

```bash
GET http://127.0.0.1:8090/health
Returns: {"status": "ok", "neo4j": "connected"|"disconnected"}
```

### Graph Search (testing-agent)

```bash
# Search entities by name
GET http://127.0.0.1:8090/graph/search?q=Straits&limit=10
Returns: [{"canonical_id": "...", "name": "...", "main_categories": [...]}]

# Get subgraph around entity
GET http://127.0.0.1:8090/graph/{canonical_id}
Returns: {"nodes": [...], "edges": [...], "center_node": "..."}
```

### Query (testing-agent)

```bash
POST http://127.0.0.1:8090/query
Body: {"question": "...", "filter_categories": ["Economic and Financial"]}
Returns: {"answer": "...", "source_type": "archive", "citations": [...], "graph": {...}}
```

---

## Runtime Environment

| Component | Path / Port | Notes |
|-----------|-------------|-------|
| Python 3.13 | `C:\Users\yjkim\AppData\Local\Programs\Python\Python313\python.exe` | Backend runtime |
| Backend server | `http://127.0.0.1:8090` | `cd backend && uvicorn app.main:app --port 8090` |
| Frontend dev | `http://localhost:5173` | `cd frontend && npm run dev` |
| Backend .env | `backend/.env` | Contains all GCP + Neo4j credentials |
| GCP credentials | Application Default Credentials | `gcloud auth application-default login` (PowerShell) |

---

## Common Failure Modes

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Neo4j paused | `neo4j: "disconnected"` in health | Wait 30-60s, auto-resumes |
| Gemini rate limit | Entity extraction fails (server logs) | Vector ingestion still succeeds; retry graph steps later |
| Doc AI quota | OCR step fails | Wait and retry individual PDF |
| Doc AI 40MB limit | `INVALID_ARGUMENT` on large PDFs | Fixed: pypdf splits into sub-PDFs of 15 pages |
| Embedding token limit | `exceeds the limit of 20000` | Fixed: batch size reduced from 250 to 40 |
| GCP auth expired | All GCP calls return 403 | Run `gcloud auth application-default login` in PowerShell |
| Port conflict | `Address already in use` | Use `netstat -aon \| findstr 8090` to find PID, or use different port |
| Signed URL expired | PdfModal blank in browser | URLs expire after 15 min; re-request |
| Signed URL 500 | `GET /document/signed_url` returns HTTP 500 | **NOT YET FIXED** — needs investigation |
| Very large PDF (> 95 MB) | Ingestion returns 0 pages | **NOT YET FIXED** — suspected memory/timeout |
| Backend OOM from concurrency | Multiple large PDFs → crash | Submit max 2-3 large PDFs at once, stagger |
| Region contamination | Vector upsert looks in wrong region | Fixed: cached `MatchingEngineIndex` with full resource name |

---

## Valid Categories (Source of Truth)

From `backend/app/models/schemas.py`:

```python
MAIN_CATEGORIES = [
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment",
]
```

Every value in `document_categories.json` must be from this list exactly (case-sensitive).
