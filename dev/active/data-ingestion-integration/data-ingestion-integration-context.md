# Data Ingestion & Integration — Context Reference

**Last Updated: 2026-03-01**

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

### Will Be Modified

| File | Change | By |
|------|--------|-----|
| `backend/app/config/document_categories.json` | Replace example entries with 28 real PDF mappings | setup-agent |
| `.git/` (new) | Initialize git repository | setup-agent |

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

### Decisions for This Session

1. **Ingest 10 PDFs** (small + medium tier only, < 30 MB each) — defers large files to avoid timeouts
2. **Categories assigned by sub-series:**
   - CO 273:534 → `["General and Establishment"]`
   - CO 273:550 → `["General and Establishment", "Economic and Financial"]`
   - CO 273:579 → `["General and Establishment"]`
3. **Batch size: 5 PDFs per batch** — avoids overwhelming Document AI / Gemini quotas
4. **Frontend testing starts after Batch 1** — doesn't need all 10 PDFs

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

| # | Filename | Size | Tier | Ingest This Session? |
|---|----------|------|------|---------------------|
| 1 | CO 273:550:18.pdf | 3.2 MB | Small | Already done |
| 2 | CO 273:550:5.pdf | 5.8 MB | Small | Yes (Batch 1) |
| 3 | CO 273:550:11.pdf | 6.2 MB | Small | Yes (Batch 1) |
| 4 | CO 273:550:10.pdf | 7.9 MB | Small | Yes (Batch 1) |
| 5 | CO 273:534:11b.pdf | 9.5 MB | Small | Yes (Batch 1) |
| 6 | CO 273:550:21.pdf | 11.3 MB | Small | Yes (Batch 1) |
| 7 | CO 273:534:6.pdf | 14.6 MB | Medium | Yes (Batch 2) |
| 8 | CO 273:534:7.pdf | 17.3 MB | Medium | Yes (Batch 2) |
| 9 | CO 273:534:13.pdf | 23.1 MB | Medium | Yes (Batch 2) |
| 10 | CO 273:534:5.pdf | 27.9 MB | Medium | Yes (Batch 2) |
| 11 | CO 273:534:24.pdf | 29.5 MB | Medium | Yes (Batch 2) |
| 12-28 | Large/XL files (50-278 MB) | — | Large/XL | No — future session |

**Other objects in bucket:**
- `chunks/CO 273:550:18.json` — chunk data from first ingestion
- `ocr/CO 273:550:18_ocr.json` — OCR output from first ingestion

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
| GCP auth expired | All GCP calls return 403 | Run `gcloud auth application-default login` in PowerShell |
| Port conflict | `Address already in use` | Use `netstat -aon \| findstr 8090` to find PID, or use different port |
| Signed URL expired | PdfModal blank in browser | URLs expire after 15 min; re-request |

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
