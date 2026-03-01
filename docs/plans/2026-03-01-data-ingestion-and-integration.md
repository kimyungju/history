# Data Ingestion, Integration Testing & Repository Setup

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ingest 10 colonial archive PDFs into the system, verify end-to-end frontend integration, initialize git version control, and populate document category mappings.

**Architecture:** The backend runs on localhost:8090 (FastAPI + Uvicorn). Ingestion is async — POST `/ingest_pdf` returns a `job_id` immediately and processes 9 pipeline steps in background (GCS download → Document AI OCR → chunk → embed → vector upsert → entity extraction → normalization → Neo4j MERGE). Frontend on localhost:5173 proxies `/api` to backend. Doc IDs are derived from PDF filenames without extension (e.g., `CO 273:550:11.pdf` → `CO 273:550:11`).

**Tech Stack:** FastAPI, Google Cloud (Document AI, Vertex AI, Cloud Storage, Vector Search), Neo4j AuraDB, React 18 + Vite

---

## Task 1: Initialize Git Repository

**Files:**
- Create: (git internals — `.git/`)
- Verify: `C:\NUS\Projects\history\.gitignore` (already exists)

**Step 1: Verify .gitignore covers sensitive files**

Read `.gitignore` and confirm it includes:
```
.env
__pycache__/
node_modules/
```

Expected: All three present (already confirmed — file has 13 lines covering Python, Node, .env).

**Step 2: Initialize git repo**

```bash
cd /c/NUS/Projects/history && git init
```

Expected output: `Initialized empty Git repository in C:/NUS/Projects/history/.git/`

**Step 3: Verify no secrets will be staged**

```bash
cd /c/NUS/Projects/history && git status -u | grep -E "\.env$|credentials|secret" || echo "No secrets found"
```

Expected: "No secrets found" — `.env` is gitignored. If any secrets appear, do NOT proceed — add them to `.gitignore` first.

**Step 4: Stage all files**

```bash
cd /c/NUS/Projects/history && git add -A && git status --short | head -30
```

Expected: ~50-80 files staged (backend .py, frontend .tsx/.ts, config, docs, infra). No `.env`, no `node_modules/`, no `__pycache__/`.

**Step 5: Create initial commit**

```bash
cd /c/NUS/Projects/history && git commit -m "feat: Colonial Archives Graph-RAG — Phases 1-3 complete

Phase 1: Backend foundation (FastAPI, Document AI OCR, chunking,
embeddings, Vector Search, Gemini LLM, hybrid retrieval)

Phase 2: Graph layer (entity extraction, normalization, Neo4j AuraDB,
subgraph traversal, graph endpoints)

Phase 3: React frontend (Cytoscape.js graph viz, chat panel,
PDF viewer, citation badges, category filter, Zustand store)

All GCP services provisioned. First ingestion test passed (9 steps).
Query endpoint returns grounded answers with graph context."
```

Expected: Commit succeeds. Run `git log --oneline` to verify.

---

## Task 2: Update document_categories.json

**Files:**
- Modify: `backend/app/config/document_categories.json`

**Context:** The 5 valid categories are defined in `backend/app/models/schemas.py:4-10`:
```python
MAIN_CATEGORIES = [
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment",
]
```

CO 273 is "Original Correspondence, Straits Settlements" from the British Colonial Office. All documents are colonial administrative correspondence, so "General and Establishment" applies universally. Sub-series hints:
- **CO 273:534** — Earlier volume, general colonial administration
- **CO 273:550** — Later volume, includes economic/trade correspondence (Vibrona wine, import duties found in :550:18)
- **CO 273:579** — Supplementary correspondence

Without reading each document, assign "General and Establishment" to all, plus "Economic and Financial" to CO 273:550 (confirmed by entity extraction of :550:18). Categories can be refined after ingestion reveals document content.

**Step 1: Replace document_categories.json with real mappings**

Write this content to `backend/app/config/document_categories.json`:

```json
{
  "_comment": "Map PDF filenames to 1-2 categories from MAIN_CATEGORIES. CO 273 = Original Correspondence, Straits Settlements.",
  "CO 273:534:2.pdf": ["General and Establishment"],
  "CO 273:534:3.pdf": ["General and Establishment"],
  "CO 273:534:5.pdf": ["General and Establishment"],
  "CO 273:534:6.pdf": ["General and Establishment"],
  "CO 273:534:7.pdf": ["General and Establishment"],
  "CO 273:534:9.pdf": ["General and Establishment"],
  "CO 273:534:11a.pdf": ["General and Establishment"],
  "CO 273:534:11b.pdf": ["General and Establishment"],
  "CO 273:534:13.pdf": ["General and Establishment"],
  "CO 273:534:15a.pdf": ["General and Establishment"],
  "CO 273:534:15b.pdf": ["General and Establishment"],
  "CO 273:534:24.pdf": ["General and Establishment"],
  "CO 273:550:1.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:3.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:5.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:8.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:10.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:11.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:13.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:14.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:18.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:19.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:550:21.pdf": ["General and Establishment", "Economic and Financial"],
  "CO 273:579:1.pdf": ["General and Establishment"],
  "CO 273:579:2a.pdf": ["General and Establishment"],
  "CO 273:579:2b.pdf": ["General and Establishment"],
  "CO 273:579:3.pdf": ["General and Establishment"],
  "CO 273:579:4.pdf": ["General and Establishment"]
}
```

**Step 2: Validate JSON syntax**

```bash
cd /c/NUS/Projects/history && python -c "import json; json.load(open('backend/app/config/document_categories.json')); print('Valid JSON')"
```

Expected: `Valid JSON`

**Step 3: Verify category values match MAIN_CATEGORIES**

```bash
cd /c/NUS/Projects/history && python -c "
import json
cats = json.load(open('backend/app/config/document_categories.json'))
valid = {'Internal Relations and Research','Economic and Financial','Social Services','Defence and Military','General and Establishment'}
for k, v in cats.items():
    if k.startswith('_'): continue
    for c in v:
        assert c in valid, f'Invalid category \"{c}\" for {k}'
print(f'All {len([k for k in cats if not k.startswith(\"_\")])} entries valid')
"
```

Expected: `All 28 entries valid`

**Step 4: Commit**

```bash
cd /c/NUS/Projects/history && git add backend/app/config/document_categories.json && git commit -m "feat: populate document_categories.json with all 28 CO 273 PDFs

Maps all PDFs in aihistory-co273-nus bucket to archive categories.
CO 273:550 series gets Economic and Financial (confirmed by entity
extraction). All get General and Establishment (colonial correspondence).
Categories can be refined after more ingestion reveals content."
```

---

## Task 3: Start Backend and Ingest PDFs (Batch 1 — Small Files)

**Files:**
- Read: `backend/app/routers/ingest.py` (understand job tracking)
- No code changes — operational task

**Context:** 28 PDFs available, 1 already ingested (CO 273:550:18.pdf). Start with the 5 smallest unprocessed PDFs (5.8-11.3 MB). Ingestion is async — POST returns job_id immediately. Each job processes all 9 pipeline steps in the background. Poll `/ingest_status/{job_id}` until `status: "done"` or `"failed"`.

**Step 1: Start the backend server**

```bash
cd /c/NUS/Projects/history/backend && uvicorn app.main:app --port 8090
```

Expected: Server starts, logs show:
```
INFO:     Uvicorn running on http://127.0.0.1:8090
INFO:     Neo4j connection verified
```

If Neo4j says "not reachable" — the AuraDB instance may be paused (3-day inactivity). It auto-resumes on connection, retry after 30 seconds.

**Step 2: Verify health endpoint**

```bash
curl -s http://127.0.0.1:8090/health | python -m json.tool
```

Expected:
```json
{
    "status": "ok",
    "neo4j": "connected"
}
```

If `neo4j: "disconnected"` — wait 30s and retry. AuraDB free tier pauses after 3 days of inactivity and auto-resumes.

**Step 3: Ingest PDF #1 — CO 273:550:5.pdf (5.8 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:550:5.pdf"}' | python -m json.tool
```

Expected: Returns `{"job_id": "<uuid>", "status": "processing", ...}`. Save the job_id.

**Step 4: Ingest PDF #2 — CO 273:550:11.pdf (6.2 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:550:11.pdf"}' | python -m json.tool
```

**Step 5: Ingest PDF #3 — CO 273:550:10.pdf (7.9 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:550:10.pdf"}' | python -m json.tool
```

**Step 6: Ingest PDF #4 — CO 273:534:11b.pdf (9.5 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:11b.pdf"}' | python -m json.tool
```

**Step 7: Ingest PDF #5 — CO 273:550:21.pdf (11.3 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:550:21.pdf"}' | python -m json.tool
```

**Step 8: Poll all jobs until complete**

For each job_id returned in Steps 3-7:

```bash
curl -s http://127.0.0.1:8090/ingest_status/<JOB_ID> | python -m json.tool
```

Expected for each completed job:
```json
{
    "job_id": "<uuid>",
    "status": "done",
    "pages_total": <N>,
    "chunks_processed": <N>,
    "entities_extracted": <N>,
    "ocr_confidence_warnings": [...]
}
```

Wait and re-poll every 30 seconds for jobs still `"processing"`. OCR on larger docs can take 1-3 minutes. If any job shows `"failed"`, check server logs for the error.

**Step 9: Verify data volume**

After all 5 jobs complete, verify the system now has meaningful data:

```bash
# Check total entities in Neo4j via graph search
curl -s "http://127.0.0.1:8090/graph/search?q=&limit=50" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total entities in Neo4j: {len(data)}')
for e in data[:10]:
    print(f'  - {e[\"name\"]} ({e.get(\"main_categories\", [])})')
"
```

Expected: 50+ entities (vs 19 from the single-document test). If significantly fewer, check server logs for entity extraction failures.

---

## Task 4: Ingest PDFs (Batch 2 — Medium Files)

**Step 1: Ingest PDF #6 — CO 273:534:6.pdf (14.6 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:6.pdf"}' | python -m json.tool
```

**Step 2: Ingest PDF #7 — CO 273:534:7.pdf (17.3 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:7.pdf"}' | python -m json.tool
```

**Step 3: Ingest PDF #8 — CO 273:534:13.pdf (23.1 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:13.pdf"}' | python -m json.tool
```

**Step 4: Ingest PDF #9 — CO 273:534:5.pdf (27.9 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:5.pdf"}' | python -m json.tool
```

**Step 5: Ingest PDF #10 — CO 273:534:24.pdf (29.5 MB)**

```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:24.pdf"}' | python -m json.tool
```

**Step 6: Poll all batch 2 jobs until complete**

Same polling approach as Task 3, Step 8. These larger PDFs will take longer (2-5 minutes each). Watch server logs for Document AI batching (15 pages per request).

**Step 7: Verify cumulative data volume**

```bash
# Entity count
curl -s "http://127.0.0.1:8090/graph/search?q=&limit=200" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total entities: {len(data)}')
cats = {}
for e in data:
    for c in e.get('main_categories', []):
        cats[c] = cats.get(c, 0) + 1
print('By category:')
for c, n in sorted(cats.items()):
    print(f'  {c}: {n}')
"
```

Expected: 100+ entities across multiple categories. The graph should now be rich enough for meaningful queries.

**Step 8: Commit ingestion results note**

No code files changed, but update the context doc with results:

```bash
cd /c/NUS/Projects/history && git add -A && git status
```

If no files changed (ingestion only writes to GCS/Vector Search/Neo4j, not local files), skip this step.

---

## Task 5: End-to-End Frontend Smoke Test

**Files:**
- Read (no modify): `frontend/src/api/client.ts`, `frontend/vite.config.ts`
- The backend must be running on port 8090 (from Task 3)

**Context:** Frontend proxies `/api` to `http://localhost:8090` via Vite dev server. All 10 PDFs should now be ingested, giving the system enough data for meaningful query results.

**Step 1: Start the frontend dev server**

In a separate terminal:

```bash
cd /c/NUS/Projects/history/frontend && npm run dev
```

Expected:
```
VITE v7.x.x  ready in XXXms
➜  Local:   http://localhost:5173/
```

If `node_modules/` missing, run `npm install` first.

**Step 2: Verify API proxy works**

```bash
curl -s http://localhost:5173/api/health | python -m json.tool
```

Expected:
```json
{
    "status": "ok",
    "neo4j": "connected"
}
```

This confirms the Vite proxy is forwarding `/api` → `http://localhost:8090`.

**Step 3: Test a query via the API proxy**

```bash
curl -s -X POST http://localhost:5173/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the main economic activities in the Straits Settlements?"}' | python -c "
import sys, json
r = json.load(sys.stdin)
print(f'Answer length: {len(r[\"answer\"])} chars')
print(f'Source type: {r[\"source_type\"]}')
print(f'Citations: {len(r[\"citations\"])}')
if r.get('graph'):
    print(f'Graph nodes: {len(r[\"graph\"][\"nodes\"])}')
    print(f'Graph edges: {len(r[\"graph\"][\"edges\"])}')
print()
print(r['answer'][:500])
"
```

Expected: A substantive answer with citations and graph data (not "I cannot answer" — we now have 10+ documents). If still getting "I cannot answer", try more specific queries based on known entities (e.g., "What is Vibrona wine?").

**Step 4: Test graph search endpoint**

```bash
curl -s "http://localhost:5173/api/graph/search?q=Straits&limit=10" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'Entities found: {len(data)}')
for e in data:
    print(f'  - {e[\"name\"]} (categories: {e.get(\"main_categories\", [])})')
"
```

Expected: Multiple entities matching "Straits" — Straits Settlements should appear with its relationships.

**Step 5: Test subgraph retrieval**

Use a canonical_id from Step 4:

```bash
# Replace CANONICAL_ID with an actual ID from Step 4
curl -s "http://localhost:5173/api/graph/CANONICAL_ID" | python -c "
import sys, json
r = json.load(sys.stdin)
print(f'Nodes: {len(r[\"nodes\"])}')
print(f'Edges: {len(r[\"edges\"])}')
print(f'Center: {r[\"center_node\"]}')
for n in r['nodes'][:5]:
    print(f'  Node: {n[\"name\"]}')
for e in r['edges'][:5]:
    print(f'  Edge: {e[\"source\"]} --[{e[\"type\"]}]--> {e[\"target\"]}')
"
```

Expected: A subgraph with the requested entity at center, connected nodes, and typed edges.

**Step 6: Test category-filtered query**

```bash
curl -s -X POST http://localhost:5173/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What economic policies affected trade?", "filter_categories": ["Economic and Financial"]}' | python -c "
import sys, json
r = json.load(sys.stdin)
print(f'Answer: {r[\"answer\"][:300]}')
print(f'Citations: {len(r[\"citations\"])}')
"
```

Expected: Answer draws from CO 273:550 documents (which have "Economic and Financial" category). Results should be more focused than unfiltered query.

**Step 7: Manual browser test checklist**

Open `http://localhost:5173` in a browser and verify:

1. **Chat panel**: Type a question → answer appears with `[archive:N]` citation badges
2. **Graph canvas**: Nodes and edges render after a query returns graph data
3. **Node click**: Clicking a graph node opens the NodeSidebar with entity details
4. **Citation badge**: Clicking a citation badge opens the PdfModal
5. **PDF viewer**: PdfModal loads the document page (uses signed URLs from backend)
6. **Graph search bar**: Type an entity name → results appear in the graph
7. **Category filter**: Toggle categories → filtered queries return different results
8. **Resizable splitter**: Drag the divider between graph and chat panels

Document any failures for follow-up fixes.

---

## Task 6: Verify and Record Results

**Step 1: Record final system state**

```bash
# Total entities
curl -s "http://127.0.0.1:8090/graph/search?q=&limit=500" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total entities in Neo4j: {len(data)}')
"

# Check ingested docs count
curl -s "http://127.0.0.1:8090/graph/search?q=&limit=500" | python -c "
import sys, json
data = json.load(sys.stdin)
docs = set()
for e in data:
    # entities don't directly track source doc, but we can count unique categories
    pass
print(f'Entities: {len(data)}')
"
```

**Step 2: Commit any remaining changes**

```bash
cd /c/NUS/Projects/history && git status
```

If there are uncommitted changes (documentation updates, config tweaks):

```bash
cd /c/NUS/Projects/history && git add -A && git commit -m "chore: record ingestion results and integration test notes"
```

**Step 3: Verify git log**

```bash
cd /c/NUS/Projects/history && git log --oneline
```

Expected: 2-3 commits:
```
<hash> chore: record ingestion results and integration test notes
<hash> feat: populate document_categories.json with all 28 CO 273 PDFs
<hash> feat: Colonial Archives Graph-RAG — Phases 1-3 complete
```

---

## Failure Recovery

### Neo4j AuraDB paused
- **Symptom**: Health endpoint returns `neo4j: "disconnected"`
- **Fix**: Wait 30-60 seconds — AuraDB auto-resumes on connection attempt. Retry health check.

### Ingestion job fails
- **Symptom**: `ingest_status` returns `status: "failed"`
- **Fix**: Check server logs (uvicorn console output). Common causes:
  - Document AI quota exceeded → wait and retry
  - Gemini rate limit → entity extraction failed (vector ingestion still succeeds)
  - GCS permission error → verify `gcloud auth application-default login`

### Frontend proxy 502
- **Symptom**: `/api/health` returns 502 Bad Gateway
- **Fix**: Backend not running or wrong port. Verify `vite.config.ts` targets port 8090, restart backend.

### PDF viewer fails to load
- **Symptom**: PdfModal shows blank or error
- **Fix**: Signed URL may have expired (15 min TTL). The frontend should re-request. If persistent, check that `generate_signed_url` works: `curl http://127.0.0.1:8090/document/signed_url?doc_id=CO%20273:550:18&page=1`

### "I cannot answer" for all queries
- **Symptom**: LLM refuses to answer despite ingested data
- **Fix**: Vector Search may not have propagated (STREAM_UPDATE). Wait 1-2 minutes after ingestion, then retry. Also try queries using exact entity names found via `/graph/search?q=&limit=10`.
