# Colonial Archives Graph-RAG -- Context Reference Document

**Last Updated: 2026-03-01 (Session 3 — Infrastructure provisioned, full pipeline tested end-to-end)**

**Purpose**: This document contains all key reference information needed to work on the Colonial Archives Graph-RAG system. It consolidates architecture decisions, data flows, API contracts, configuration values, dependencies, schemas, and component maps from the design document and Phase 1 implementation plan.

---

## 0. Infrastructure Status & Testing (Session 3)

### GCP Resources Provisioned
| Resource | Region | Status | ID/Endpoint |
|----------|--------|--------|-------------|
| Cloud Storage | asia-southeast1 | ✅ Working | `aihistory-co273-nus` (~20 PDFs, CO 273 series) |
| Document AI OCR | asia-southeast1 | ✅ Working | `projects/58449340870/locations/asia-southeast1/processors/1a36b779b245dae0` |
| Vector Search Index | asia-southeast1 | ✅ Working | ID: `5700013413925650432` (768 dims, COSINE_DISTANCE, UNIT_L2_NORM, STREAM_UPDATE) |
| Vector Search Endpoint | asia-southeast1 | ✅ Working | `1005598664.asia-southeast1-58449340870.vdb.vertexai.goog` (deployed: `colonial-archives-deployed`) |
| Vertex AI Embeddings | asia-southeast1 | ✅ Working | `text-embedding-004` |
| Gemini LLM | us-central1 | ✅ Working | `gemini-2.0-flash` (1.5-flash returned 404, switched to 2.0) |
| Neo4j AuraDB | cloud | ✅ Connected | `neo4j+s://ae76ab7c.databases.neo4j.io` (user: `ae76ab7c`) |

### First Ingestion Test (CO 273:550:18.pdf — 3.3MB, 6 pages) — ALL STEPS PASSED ✅
| Pipeline Step | Status | Details |
|---------------|--------|---------|
| 1. PDF Download (GCS) | ✅ | 3.3MB downloaded |
| 2. OCR (Document AI) | ✅ | 6 pages, all confidence=0.0 (handwritten colonial docs) |
| 3. Category Lookup | ⚠️ | No mapping found (file not in document_categories.json) |
| 4. Chunking | ✅ | 2 chunks produced |
| 5. Embedding | ✅ | 2 vectors (768-dim) |
| 6. Vector Upsert | ✅ | Upserted to index successfully |
| 7. Entity Extraction | ✅ | 19 entities extracted (gemini-2.0-flash) |
| 8. Normalization | ✅ | Entities normalized |
| 9. Neo4j MERGE | ✅ | Entities + relationships written to Neo4j |

### Query Endpoint Test — PASSED ✅
- `POST /query {"question": "What is Vibrona wine and its connection to the Straits Settlements?"}`
- **Graph returned**: Straits Settlements → HAS_IMPORT_DUTY_ON → Vibrona (both highlighted)
- **Answer**: LLM correctly refused to hallucinate when context insufficient (grounding rules work)
- **Citations**: 2 archive citations referencing matched entities
- **GraphPayload**: nodes, edges, center_node all populated correctly

### Graph Search Endpoint Test — PASSED ✅
- `GET /graph/search?q=&limit=10` returns entities from Neo4j
- Entities found: Straits Settlements, British Colonial Office, Government House, L.C.M.S. Amery, Vibrona wine, Government Monopolies Department, Messrs. Fletcher Fletcher and Company

### Bugs Fixed During Setup
1. **Wrong imports** in `ocr.py`, `vector_search.py`: `from backend.app.` → `from app.`
2. **Eager GCP client init**: All services created clients at import time (before `vertexai.init()`). Fixed with lazy `@property` pattern in `embeddings.py`, `llm.py`, `entity_extraction.py`, `ocr.py`, `vector_search.py`.
3. **Document AI region**: Client defaulted to US. Fixed: `api_endpoint=f"{settings.GCP_REGION}-documentai.googleapis.com"`.
4. **Gemini region**: Not available in asia-southeast1. Added `VERTEX_LLM_REGION=us-central1` in settings.py. LLM/entity services call `vertexai.init()` with this region.
5. **requirements.txt**: `vertexai==1.74.0` doesn't exist. Downgraded to `1.71.1`.
6. **Gemini model name**: `gemini-1.5-flash` returned 404 even in us-central1. Switched to `gemini-2.0-flash` in `settings.py`.

### Files Modified This Session
| File | Change |
|------|--------|
| `backend/app/services/ocr.py` | Fixed import (`backend.app.` → `app.`), lazy client init with region-specific endpoint |
| `backend/app/services/vector_search.py` | Fixed imports, lazy `aiplatform.init()` |
| `backend/app/services/embeddings.py` | Lazy model init via `@property` |
| `backend/app/services/llm.py` | Lazy model init, `vertexai.init()` with `VERTEX_LLM_REGION` |
| `backend/app/services/entity_extraction.py` | Lazy model init, `vertexai.init()` with `VERTEX_LLM_REGION` |
| `backend/app/config/settings.py` | Added `VERTEX_LLM_REGION=us-central1`, changed model to `gemini-2.0-flash` |
| `backend/requirements.txt` | Downgraded `vertexai` and `google-cloud-aiplatform` to `1.71.1` |
| `backend/.env` | All real values filled in (GCP, Neo4j, Vector Search) |

### Resolved Blocker
**Gemini model**: `gemini-1.5-flash` returned 404. Fixed by switching to `gemini-2.0-flash` in `settings.py`.

### Frontend Test Results
- Frontend on port 5173, Vite proxy → backend 8090 (changed from 8080 in `vite.config.ts`)
- `/api/health` through proxy returns `{"status":"ok","neo4j":"connected"}`
- Queries work end-to-end through UI, but most return "I cannot answer" — only 1 doc (2 chunks) ingested
- "Vibrona" query returns entity + graph node through frontend

### Resume Steps (Next Session)
1. ✅ ~~Fix Gemini access~~ — resolved (gemini-2.0-flash)
2. ✅ ~~Re-run ingestion~~ — all 9 steps pass, 19 entities extracted
3. ✅ ~~Test POST /query~~ — works, returns answer + graph + citations
4. ✅ ~~Test /graph/search~~ — works, returns entities from Neo4j
5. ✅ ~~Test frontend with live backend~~ — works, queries go through, graph renders
6. **Ingest more PDFs** — CRITICAL, only 1 doc in system. Small ones to start:
   - `CO 273:550:11.pdf` (6.5 MB), `CO 273:550:10.pdf` (8.3 MB), `CO 273:534:11b.pdf` (9.9 MB)
   - `curl -X POST http://127.0.0.1:8090/ingest_pdf -H "Content-Type: application/json" -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:550:11.pdf"}'`
7. **Initialize git repo** and make first commit (nothing is version controlled yet!)
8. **Update document_categories.json** with real PDF→category mappings
9. **Startup commands**: `cd backend && uvicorn app.main:app --port 8090` then `cd frontend && npm run dev`

---

## 1. Key Files and Locations

### Monorepo Structure

```
history/                          # Project root
  backend/                        # FastAPI backend service
    app/
      __init__.py
      main.py                     # FastAPI app entry point, lifespan, CORS, router registration
      config/
        __init__.py
        settings.py               # Pydantic Settings with all PLACEHOLDER values
        document_categories.json  # PDF filename -> MAIN_CATEGORIES mapping (user-provided)
      models/
        __init__.py
        schemas.py                # All Pydantic request/response/internal models
      routers/
        __init__.py
        ingest.py                 # POST /ingest_pdf, GET /ingest_status/{job_id}
        query.py                  # POST /query, GET /document/signed_url
        graph.py                  # GET /graph/{canonical_id}, GET /graph/search (Phase 2 stub)
      services/
        __init__.py
        storage.py                # Cloud Storage: read PDFs, upload JSON, signed URLs
        ocr.py                    # Document AI OCR with batched page processing
        chunking.py               # Text cleaning + sliding window chunking
        embeddings.py             # Vertex AI text-embedding-004 batch embeddings
        vector_search.py          # Vertex AI Vector Search upsert + search
        llm.py                    # Gemini 1.5 Flash answer generation with citation prompting
        hybrid_retrieval.py       # Full query pipeline: embed -> search -> generate
    requirements.txt              # Python dependencies (pinned versions)
    Dockerfile                    # Python 3.11-slim, uvicorn on port 8080
    .env                          # Real credentials (NOT committed, gitignored)
    .env.example                  # Template with placeholder values
  frontend/                       # React 18 + TypeScript frontend (Phase 3)
  infra/
    docker-compose.yml            # Local dev: backend service with GCP credentials mount
  docs/
    plans/
      2026-03-01-colonial-archives-graph-rag-design.md   # Master design document
      2026-03-01-phase1-backend-foundation.md             # Phase 1 implementation plan (12 tasks)
  dev/
    active/
      colonial-archives-graph-rag/
        colonial-archives-graph-rag-context.md            # THIS FILE
```

### Config Files

| File | Location | Purpose |
|------|----------|---------|
| `settings.py` | `backend/app/config/settings.py` | All environment variables with PLACEHOLDER defaults. Reads from `.env` file. |
| `document_categories.json` | `backend/app/config/document_categories.json` | Maps PDF filenames to 1-2 MAIN_CATEGORIES. Provided by user before ingestion. Keys starting with `_` are treated as comments. |
| `.env` | `backend/.env` | Real GCP credentials and configuration values. Must be created from `.env.example`. |
| `.env.example` | `backend/.env.example` | Template showing all required environment variables. |
| `docker-compose.yml` | `infra/docker-compose.yml` | Local dev orchestration. Mounts GCP credentials into container. |

### Design & Plan Locations

| Document | Absolute Path |
|----------|---------------|
| Design Document | `docs/plans/2026-03-01-colonial-archives-graph-rag-design.md` |
| Phase 1 Plan | `docs/plans/2026-03-01-phase1-backend-foundation.md` |
| Phase 3 Frontend Design | `docs/plans/2026-03-01-phase3-react-frontend-design.md` |
| Phase 3 Implementation Plan | `docs/plans/2026-03-01-phase3-implementation-plan.md` |
| Phase 3 Team Execution | `dev/active/phase3-frontend-team/` (plan, context, tasks) |

---

## 2. Architecture Decisions

Each decision below is documented with the choice made and the reasoning behind it.

### No LangChain -- Direct SDK Calls

- **Choice**: Use official Google Cloud Python SDKs directly (google-cloud-documentai, google-cloud-aiplatform, vertexai, google-cloud-storage). No LangChain, no LlamaIndex, no abstraction frameworks.
- **Why**: Transparency and control. Direct SDK calls make it clear exactly what API is being called, with what parameters, and what response is expected. This is critical for an academic research tool where every answer must be traceable. Abstraction layers obscure behavior, make debugging harder, and introduce unnecessary dependencies with their own update cycles.

### Page-Level OCR + Sliding Window Chunking

- **Choice**: OCR each page individually via Document AI, then concatenate pages with `[PAGE:N]` markers, then apply a sliding window (300-600 tokens, 100 token overlap) that may span 2 adjacent pages.
- **Why**: Two goals that are in tension -- (1) clean per-page citations so researchers can find the exact source page, and (2) cross-page context so that sentences or ideas spanning page breaks are not lost. The page markers solve (1) by letting chunks carry a `pages[]` array. The sliding window with overlap solves (2) by allowing a single chunk to contain text from two adjacent pages. The 300-600 token size (configurable via `CHUNK_SIZE_TOKENS` defaulting to 450) balances embedding quality with context window utilization. This matters especially for 300-500 page colonial-era documents where information density varies widely.

### Sync REST Ingestion First -- Pub/Sub in Phase 4

- **Choice**: Phase 1 uses synchronous REST (`POST /ingest_pdf` triggers a `BackgroundTasks` job). Pub/Sub async ingestion deferred to Phase 4.
- **Why**: Simpler to debug. Ingestion is an admin-only operation (documents are ingested before researchers access the system), so it does not need to handle concurrent user load. A sync pipeline with in-memory job tracking (`_jobs` dict) lets developers step through the full OCR -> chunk -> embed -> upsert flow with standard logging. Pub/Sub adds message acknowledgment, retry logic, dead-letter queues, and ordering concerns that are premature at this stage.

### Vertex AI text-embedding-004

- **Choice**: `text-embedding-004` from Vertex AI for all embeddings (document chunks and queries).
- **Why**: Multilingual capability is non-negotiable -- the archive documents are mostly English but contain Chinese text as well. text-embedding-004 handles both languages in the same embedding space, enabling cross-lingual retrieval. It also supports task-type hints (`RETRIEVAL_DOCUMENT` for chunks, `RETRIEVAL_QUERY` for questions) which improve relevance. As a Vertex AI native model, it integrates seamlessly with the rest of the GCP stack without additional API keys or services.

### Gemini 1.5 Flash

- **Choice**: Vertex AI Gemini 1.5 Flash for answer generation.
- **Why**: Fast inference (targeting <2s p95 total query latency, with LLM generation being 1-1.5s of that budget). Supports structured output mode, which is needed for reliable citation formatting. Low temperature (0.1) ensures consistent, factual responses. Cost-effective for a research tool that may handle many queries. The strict grounding prompt forces every fact to be cited with `[archive:N]` or `[web:N]` markers, and insufficient context triggers a refusal response rather than hallucination.

### Cloud Run for Both Services

- **Choice**: Deploy both the FastAPI backend and React frontend (nginx) as Cloud Run services.
- **Why**: Consistent deployment model. Both services use Docker containers, scale to zero when idle (cost-effective for an academic tool that may have sporadic usage), and are GCP-native. Cloud Run handles HTTPS termination, custom domains, and IAM integration without requiring Kubernetes knowledge. The frontend is a static nginx container serving built React assets.

### No Auth -- Open Access

- **Choice**: No authentication, no login, no user accounts.
- **Why**: The primary users are academic researchers who need friction-free access to the tool. The data (colonial-era archive documents) is not sensitive -- it is being digitized precisely to make it accessible. Adding auth would create a barrier to adoption without protecting anything that needs protection. CORS is configured with `allow_origins=["*"]` to support any frontend deployment.

### MERGE Not CREATE in Neo4j

- **Choice**: Always use Cypher `MERGE` operations, never `CREATE`, when writing to Neo4j (Phase 2).
- **Why**: Idempotency. Re-ingesting the same PDF must not create duplicate entities or relationships. `MERGE` finds existing nodes/relationships by their matching properties and updates them, or creates them only if they do not exist. This is essential because the ingestion pipeline will be run multiple times during development and may be re-run on corrected OCR output. `CREATE` would produce duplicates that corrupt the graph and mislead researchers.

### Categories as Metadata Labels, Not Graph Silos

- **Choice**: Attach `main_categories[]` as metadata on entities and as filter tokens on vector search, rather than creating separate graph partitions per category.
- **Why**: Free cross-category traversal. Colonial-era governance documents frequently reference entities across categories -- a person in "Defence and Military" may appear in "Economic and Financial" correspondence. If the graph were siloed by category, these cross-references would be invisible. Metadata labels allow filtering by category when desired (e.g., `filter_categories` on the query endpoint) while preserving the ability to traverse the full graph.

### All Entity Types/Relationships AI-Inferred

- **Choice**: Only 5 MAIN_CATEGORIES are predefined. Everything else -- entity types (person, organization, location, event, etc.), sub_category, relationship types (verb phrases), attributes (key-value pairs) -- is inferred by Gemini Flash during entity extraction (Phase 2).
- **Why**: The colonial archive documents span diverse topics and time periods. Pre-defining a fixed ontology would either be too restrictive (missing entity types that appear in the documents) or too broad (creating unused categories). Letting the LLM infer entity types and relationship types from the actual text produces a schema that reflects the documents' content. The evidence metadata (`doc_id`, `page`, `text_span`, `confidence`) on every node and relationship ensures that every AI-inferred classification is traceable back to its source.

---

## 3. Data Flow Diagrams (ASCII)

### Ingestion Pipeline

```
PDF in Cloud Storage (gs://bucket/document_042.pdf)
  |
  v
POST /ingest_pdf { "pdf_url": "gs://bucket/document_042.pdf" }
  |
  v
+-----------------------------------------------------------+
| 1. DOWNLOAD PDF                                           |
|    storage_service.read_pdf_bytes(gcs_url) -> bytes       |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 2. OCR (Document AI)                                      |
|    - Batch pages in groups of 15 (API limit)              |
|    - Parallelize with asyncio.gather, semaphore(5)        |
|    - Store raw OCR JSON -> gs://bucket/ocr/{doc_id}.json  |
|    - Flag pages with confidence < 0.5                     |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 3. CATEGORY LOOKUP                                        |
|    - Check document_categories.json for pdf filename      |
|    - If not found: empty list (auto-classify in Phase 4)  |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 4. TEXT CLEANING + CHUNKING                               |
|    - Normalize whitespace, remove artifacts               |
|    - Concatenate pages with [PAGE:N] markers              |
|    - Sliding window: ~450 tokens, 100 overlap             |
|    - Break at sentence boundaries when possible           |
|    - Each chunk: {chunk_id, doc_id, pages[], text,        |
|                   language_tag, categories[]}              |
|    - Store chunks -> gs://bucket/chunks/{doc_id}.json     |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 5. EMBEDDING (Vertex AI text-embedding-004)               |
|    - Batch embed: 250 texts per API call                  |
|    - Task type: RETRIEVAL_DOCUMENT                        |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 6. VECTOR UPSERT (Vertex AI Vector Search)                |
|    - Upsert in batches of 100                             |
|    - Metadata: doc_id, pages, language_tag, text[:500]    |
|    - Filter tokens: category names                        |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 7. ENTITY EXTRACTION (Phase 2 -- not in Phase 1)         |
|    - Gemini Flash structured JSON per chunk               |
|    - Returns: entities[] + relationships[] with evidence  |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 8. ENTITY NORMALIZATION (Phase 2)                         |
|    - Embedding similarity + fuzzy string match            |
|    - Merge aliases (e.g. "J. Anderson" -> "John Anderson")|
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 9. NEO4J MERGE (Phase 2)                                  |
|    - MERGE nodes + relationships with evidence metadata   |
|    - Never CREATE, always MERGE                           |
+-----------------------------------------------------------+
  |
  v
Return: { job_id, status, pages_total, chunks_processed,
          ocr_confidence_warnings[], entities_extracted }
```

### Query Pipeline

```
POST /query { "question": "...", "filter_categories": [...] | null }
  |
  v
+-----------------------------------------------------------+
| 1. QUERY ANALYSIS                                         |
|    - Embed question: text-embedding-004 (RETRIEVAL_QUERY) |
|    - Extract entity hints (keyword extraction, no LLM)    |
+-----------------------------------------------------------+
  |
  +---------------------------+---------------------------+
  |                           |                           |
  v                           v                           |
+------------------+  +------------------+                |
| 2a. VECTOR       |  | 2b. GRAPH        |                |
|     SEARCH       |  |     TRAVERSAL    |                |
| Top-10 chunks    |  | 1-3 hop Cypher   |                |
| by cosine sim    |  | from seed entities|               |
| Filter by cats   |  | Limit 50 results |                |
| (Vertex AI)      |  | (Neo4j, Phase 2) |                |
+------------------+  +------------------+                |
  |                           |                           |
  +---------------------------+                           |
  |                                                       |
  v                                                       |
+-----------------------------------------------------------+
| 3. MERGE + SCORE                                          |
|    - Combine vector chunks + graph evidence               |
|    - Deduplicate overlapping text spans                   |
|    - Relevance score:                                     |
|      Phase 1: avg(vector_similarity)                      |
|      Phase 2: avg(vector_sim)*0.6 + graph_hit_ratio*0.4  |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 4. WEB FALLBACK (Phase 4 -- not in Phase 1)              |
|    - Triggered if relevance < 0.7                         |
|    - Tavily.search(question, search_depth="basic")        |
|    - Appended as source_type: "web"                       |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 5. LLM GENERATION (Gemini 1.5 Flash)                     |
|    - Strict grounding: cite every fact [archive:N]/[web:N]|
|    - Temperature: 0.1, max_output_tokens: 2048            |
|    - Insufficient context -> refusal message              |
+-----------------------------------------------------------+
  |
  v
+-----------------------------------------------------------+
| 6. RESPONSE                                               |
|    { answer, source_type, citations[], graph{} }          |
+-----------------------------------------------------------+
```

### PDF Citation Viewer Flow

```
User clicks [archive:N] badge in chat
  |
  v
Frontend: GET /document/signed_url?doc_id=X&page=N
  |
  v
Backend: storage_service.generate_signed_url(pdf_url, 15 min)
  |
  v
Frontend: pdf.js renders PDF at signed URL, jumps to cited page
  |
  v
User: zoom, scroll, navigate pages in modal
```

---

## 4. API Contract Summary

### POST /ingest_pdf

Ingest a PDF from Cloud Storage through the full pipeline.

**Request:**
```json
{
  "pdf_url": "gs://bucket/document_042.pdf"
}
```

**Response (IngestResponse):**
```json
{
  "job_id": "uuid-string",
  "status": "processing",
  "pages_total": 0,
  "chunks_processed": 0,
  "entities_extracted": 0,
  "ocr_confidence_warnings": []
}
```

**Notes:**
- Returns immediately with `status: "processing"`. Actual ingestion runs as a BackgroundTask.
- Poll `/ingest_status/{job_id}` for progress.
- `status` values: `"processing"` | `"done"` | `"failed"`

---

### GET /ingest_status/{job_id}

Poll the progress of an ingestion job.

**Path parameter:** `job_id` (string, UUID)

**Response (IngestResponse):**
```json
{
  "job_id": "uuid-string",
  "status": "done",
  "pages_total": 412,
  "chunks_processed": 287,
  "entities_extracted": 0,
  "ocr_confidence_warnings": [
    { "page": 34, "confidence": 0.42 },
    { "page": 198, "confidence": 0.38 }
  ]
}
```

**Error:** 404 if `job_id` not found.

---

### POST /query

Ask a question about the archive documents and receive a cited answer.

**Request:**
```json
{
  "question": "What was the role of J. Anderson in colonial trade policy?",
  "filter_categories": ["Economic and Financial"]
}
```

`filter_categories` is optional (null = search all categories).

**Response (QueryResponse):**
```json
{
  "answer": "According to the archives, J. Anderson served as... [archive:1] ... [archive:3]",
  "source_type": "archive",
  "citations": [
    {
      "type": "archive",
      "id": 1,
      "doc_id": "document_042",
      "pages": [12, 13],
      "text_span": "First 300 chars of the chunk text...",
      "confidence": 0.87
    },
    {
      "type": "web",
      "id": 2,
      "title": "Colonial Trade Routes - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/..."
    }
  ],
  "graph": {
    "nodes": [
      {
        "canonical_id": "entity_j_anderson_001",
        "name": "J. Anderson",
        "main_categories": ["Economic and Financial"],
        "sub_category": "Trade Official",
        "attributes": { "role": "Senior Trade Commissioner" },
        "highlighted": true
      }
    ],
    "edges": [
      {
        "id": "edge_001",
        "source": "entity_j_anderson_001",
        "target": "entity_trade_commission_001",
        "type": "MEMBER_OF",
        "attributes": {},
        "highlighted": true
      }
    ],
    "center_node": "entity_j_anderson_001"
  }
}
```

**Notes:**
- `source_type` values: `"archive"` | `"web_fallback"` | `"mixed"`
- `graph` is `null` in Phase 1 (vector-only retrieval)
- Citations are either `ArchiveCitation` or `WebCitation` (discriminated by `type` field)

---

### GET /document/signed_url

Get a time-limited signed URL for viewing a PDF document in the browser.

**Query parameters:**
- `doc_id` (string, required) -- Document identifier (filename without extension)
- `page` (int, optional, default=1) -- Page to navigate to (used by frontend, not by URL generation)

**Response (SignedUrlResponse):**
```json
{
  "url": "https://storage.googleapis.com/bucket/document_042.pdf?X-Goog-Signature=...",
  "expires_in": 900
}
```

**Notes:** Signed URL expires in 15 minutes (configurable via `SIGNED_URL_EXPIRY_MINUTES`).

---

### GET /graph/{entity_canonical_id}

Get subgraph around an entity (Phase 2).

**Response:** GraphPayload (nodes + edges + center_node)

**Status:** Returns HTTP 501 until Phase 2 is implemented.

---

### GET /graph/search?q={query}

Search entities by name (Phase 2).

**Query parameter:** `q` (string) -- Entity name search query

**Status:** Returns HTTP 501 until Phase 2 is implemented.

---

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

---

## 5. Key Configuration Values

All configuration is managed through `backend/app/config/settings.py` using Pydantic Settings, which reads from `.env` file or environment variables.

### PLACEHOLDER Values That Must Be Replaced

| Setting | Default (PLACEHOLDER) | What It Needs To Be |
|---------|-----------------------|---------------------|
| `GCP_PROJECT_ID` | `PLACEHOLDER_GCP_PROJECT_ID` | Your GCP project ID (e.g., `my-colonial-archives-123`) |
| `GCP_REGION` | `PLACEHOLDER_GCP_REGION` | GCP region (e.g., `asia-southeast1` for Singapore) |
| `DOC_AI_PROCESSOR_ID` | `PLACEHOLDER_DOC_AI_PROCESSOR_ID` | Full Document AI processor resource name: `projects/PROJECT/locations/LOCATION/processors/PROCESSOR_ID` |
| `VECTOR_SEARCH_ENDPOINT` | `PLACEHOLDER_VECTOR_SEARCH_ENDPOINT` | Vertex AI Vector Search index endpoint resource name |
| `VECTOR_SEARCH_INDEX_ID` | `PLACEHOLDER_VECTOR_SEARCH_INDEX_ID` | Vertex AI Vector Search index ID |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID` | `PLACEHOLDER_DEPLOYED_INDEX_ID` | Deployed index ID within the Vector Search endpoint |
| `NEO4J_URI` | `PLACEHOLDER_NEO4J_URI` | Neo4j AuraDB connection URI (e.g., `neo4j+s://xxxx.databases.neo4j.io`) |
| `NEO4J_PASSWORD` | `PLACEHOLDER_NEO4J_PASSWORD` | Neo4j AuraDB password |
| `CLOUD_STORAGE_BUCKET` | `PLACEHOLDER_GCS_BUCKET_NAME` | GCS bucket name containing the PDF documents |
| `PUBSUB_TOPIC` | `PLACEHOLDER_PUBSUB_TOPIC` | Pub/Sub topic name for async ingestion (Phase 4) |
| `TAVILY_API_KEY` | `PLACEHOLDER_TAVILY_API_KEY` | Tavily API key for web search fallback (Phase 4) |

### Pre-Configured Defaults (Tunable)

| Setting | Default | Purpose |
|---------|---------|---------|
| `VERTEX_EMBED_MODEL` | `text-embedding-004` | Embedding model name |
| `VERTEX_LLM_MODEL` | `gemini-1.5-flash` | LLM model name |
| `NEO4J_USER` | `neo4j` | Neo4j default username |
| `RELEVANCE_THRESHOLD` | `0.7` | Below this, trigger web fallback (Phase 4) |
| `OCR_CONFIDENCE_FLAG` | `0.5` | Pages below this confidence are flagged |
| `CHUNK_SIZE_TOKENS` | `450` | Target chunk size in tokens (multiplied by 4 for char estimate) |
| `CHUNK_OVERLAP_TOKENS` | `100` | Overlap between adjacent chunks in tokens |
| `GRAPH_HOP_DEPTH` | `3` | Max hops for Cypher graph traversal (Phase 2) |
| `VECTOR_TOP_K` | `10` | Number of chunks returned by vector search |
| `SIGNED_URL_EXPIRY_MINUTES` | `15` | Signed URL lifetime |

### .env.example Template

```
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=asia-southeast1
DOC_AI_PROCESSOR_ID=projects/PROJECT/locations/LOCATION/processors/PROCESSOR_ID
CLOUD_STORAGE_BUCKET=your-bucket-name
VECTOR_SEARCH_ENDPOINT=your-vector-search-endpoint
VECTOR_SEARCH_INDEX_ID=your-index-id
VECTOR_SEARCH_DEPLOYED_INDEX_ID=your-deployed-index-id
```

---

## 6. Dependencies Between Components

### Service Dependency Graph

```
routers/ingest.py
  |-- services/storage.py              (download PDF, upload OCR JSON, upload chunks JSON)
  |-- services/ocr.py                  (Document AI OCR)
  |-- services/chunking.py             (text cleaning + sliding window)
  |-- services/embeddings.py           (Vertex AI text-embedding-004)
  |-- services/vector_search.py        (upsert to Vertex AI Vector Search)
  |-- services/entity_extraction.py    (Phase 2: Gemini entity/relationship extraction)
  |-- services/entity_normalization.py (Phase 2: dedup via embedding+fuzzy matching)
  |-- services/neo4j_service.py        (Phase 2: MERGE entities/relationships into Neo4j)
  |-- models/schemas.py
  |-- config/settings.py
  |-- config/document_categories.json

routers/query.py
  |-- services/hybrid_retrieval.py  (full query pipeline)
  |     |-- services/embeddings.py     (embed query)
  |     |-- services/vector_search.py  (search similar chunks)
  |     |-- services/neo4j_service.py  (Phase 2: graph traversal)
  |     |-- services/storage.py        (load chunk texts from GCS)
  |     |-- services/llm.py            (Gemini answer generation)
  |-- services/storage.py             (signed URL generation)
  |-- models/schemas.py

routers/graph.py
  |-- services/neo4j_service.py    (Phase 2: search_entities, get_subgraph)

main.py
  |-- routers/ingest.py
  |-- routers/query.py
  |-- routers/graph.py
  |-- services/neo4j_service.py    (Phase 2: init/close in lifespan, health check)
  |-- config/settings.py           (Vertex AI init on startup)
```

### Build Order (Phase 1 Tasks)

Tasks must be implemented in order because each builds on the previous:

```
Task 1: Project skeleton + config + schemas
  |
  v
Task 2: Cloud Storage service
  |
  v
Task 3: Document AI OCR service      (depends on: storage for GCS upload)
  |
  v
Task 4: Chunking service             (depends on: OCR output types)
  |
  v
Task 5: Embeddings service           (depends on: chunk model)
  |
  v
Task 6: Vector Search service        (depends on: embeddings, chunk model)
  |
  v
Task 7: LLM service                  (standalone, but needed by query)
  |
  v
Task 8: Hybrid Retrieval service     (depends on: embeddings, vector_search, llm, storage)
  |
  v
Task 9: Ingest router                (depends on: storage, ocr, chunking, embeddings, vector_search)
  |
  v
Task 10: Query router                (depends on: hybrid_retrieval, storage)
  |
  v
Task 11: Graph router stub           (standalone placeholder)
  |
  v
Task 12: Docker Compose + init       (depends on: all of the above)
```

### Phase Dependencies

```
Phase 1 (Backend Foundation)
  |
  v
Phase 2 (Graph Layer)              <-- Requires Neo4j AuraDB provisioned
  |
  v
Phase 3 (Frontend)
  |
  v
Phase 4 (Web Fallback + Polish)
  |
  v
Phase 5 (Scale + Monitoring)
```

---

## 7. External Service Dependencies

### Google Cloud Document AI

- **Purpose**: OCR of handwritten colonial-era PDFs (English + Chinese)
- **Processor type**: Multilingual handwritten processor
- **API limit**: 15 pages per sync request (large PDFs are batched)
- **Concurrency**: Semaphore of 5 concurrent batch requests
- **Config key**: `DOC_AI_PROCESSOR_ID` (full resource name)
- **SDK**: `google-cloud-documentai==2.32.0`
- **GCP Console**: `https://console.cloud.google.com/ai/document-ai/processors?project=YOUR_PROJECT`

### Vertex AI Embeddings

- **Purpose**: Embed document chunks and user queries into vector space
- **Model**: `text-embedding-004` (multilingual, supports English + Chinese)
- **Task types used**: `RETRIEVAL_DOCUMENT` (chunks), `RETRIEVAL_QUERY` (questions)
- **Batch limit**: 250 texts per API call
- **SDK**: `vertexai==1.74.0`
- **GCP Console**: `https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/text-embedding-004?project=YOUR_PROJECT`

### Vertex AI Vector Search

- **Purpose**: Store and retrieve chunk embeddings by cosine similarity
- **Features used**: Upsert datapoints, find_neighbors, namespace-based category filtering
- **Batch upsert**: 100 datapoints per call
- **Default top-K**: 10
- **SDK**: `google-cloud-aiplatform==1.74.0`
- **GCP Console**: `https://console.cloud.google.com/vertex-ai/matching-engine/indexes?project=YOUR_PROJECT`
- **Note**: Requires creating an Index, an Index Endpoint, and deploying the index to the endpoint before use

### Vertex AI Gemini 1.5 Flash

- **Purpose**: Generate cited answers from retrieved context chunks
- **Model**: `gemini-1.5-flash`
- **Config**: Temperature 0.1, max_output_tokens 2048
- **Structured output**: Used for strict citation grounding
- **SDK**: `vertexai==1.74.0`
- **GCP Console**: `https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-1.5-flash?project=YOUR_PROJECT`

### Google Cloud Storage

- **Purpose**: Store raw PDFs, OCR output JSON, chunk JSON, and serve PDFs via signed URLs
- **Bucket structure**:
  - `gs://bucket/*.pdf` -- Raw PDF documents (top level)
  - `gs://bucket/ocr/{doc_id}_ocr.json` -- Raw OCR output per document
  - `gs://bucket/chunks/{doc_id}.json` -- Chunk arrays per document
- **Signed URLs**: V4 signed URLs, 15 minute expiry, GET method only
- **SDK**: `google-cloud-storage==2.19.0`
- **GCP Console**: `https://console.cloud.google.com/storage/browser?project=YOUR_PROJECT`

### Neo4j AuraDB (Phase 2)

- **Purpose**: Knowledge graph storage for entities, relationships, and evidence metadata
- **Hosting**: GCP-hosted AuraDB instance
- **Config keys**: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- **Requirement**: Must be provisioned before Phase 2 begins
- **Console**: `https://console.neo4j.io/`

### Tavily API (Phase 4)

- **Purpose**: Web search fallback when archive relevance score < 0.7
- **Usage**: `Tavily.search(question, search_depth="basic")`
- **Config key**: `TAVILY_API_KEY`
- **Note**: Results appended as `source_type: "web"` with separate citation format
- **API docs**: `https://docs.tavily.com/`

---

## 8. Document Categories

### The 5 MAIN_CATEGORIES (Predefined, Immutable)

```python
MAIN_CATEGORIES = [
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment",
]
```

### Assignment Rules

1. **Before ingestion**: The user provides `document_categories.json` mapping each PDF filename to 1-2 categories from MAIN_CATEGORIES.
2. **Format**: JSON object where keys are PDF filenames (e.g., `"document_042.pdf"`) and values are arrays of category strings (e.g., `["Economic and Financial"]`).
3. **Keys starting with `_`** are treated as comments and ignored during lookup.
4. **Lookup order**: The ingestion router tries the full PDF filename first, then falls back to `doc_id` (filename without extension).
5. **If not found**: Empty category list is assigned. In Phase 4, Gemini auto-classifies the document and flags classifications with confidence < 0.8 for manual review.
6. **Storage**: Categories are stored as metadata on each chunk and as filter tokens (namespaces) in Vertex AI Vector Search.
7. **Query filtering**: The `/query` endpoint accepts optional `filter_categories` to restrict vector search to specific categories.

### Example document_categories.json

```json
{
  "_comment": "Map PDF filenames to 1-2 categories from MAIN_CATEGORIES. Provided by user before ingestion.",
  "_example_document_001.pdf": ["Economic and Financial"],
  "_example_document_002.pdf": ["Defence and Military", "General and Establishment"]
}
```

---

## 9. Neo4j Schema

### Node Schema (Entity)

Every node in the graph represents an entity extracted from the archive documents. All entity types are AI-inferred -- there is no fixed type taxonomy.

```
(Entity {
  canonical_id: string,          // Unique identifier (generated during normalization)
  name: string,                  // Display name (canonical form after alias resolution)
  main_categories: string[],     // 1-2 values from MAIN_CATEGORIES only
  sub_category: string | null,   // AI-inferred (e.g., "Trade Official", "Military Fort")
  aliases: string[],             // All name variants found in documents
  attributes: map,               // AI-inferred key-value pairs (e.g., {role: "Commissioner"})
  evidence: {                    // Source provenance (one primary evidence record)
    doc_id: string,              //   Document identifier
    page: int,                   //   Page number (1-indexed)
    text_span: string,           //   Exact text from document supporting this entity
    chunk_id: string,            //   Chunk containing this text
    confidence: float            //   LLM confidence in extraction (0.0-1.0)
  }
})
```

### Relationship Schema

All relationship types are AI-inferred verb phrases. There is no predefined relationship taxonomy.

```
(a)-[:RELATIONSHIP_TYPE {
  type: string,                  // AI-inferred verb (e.g., "ADMINISTERED", "TRADED_WITH")
  attributes: map,               // AI-inferred details (e.g., {period: "1820-1835"})
  evidence: {                    // Source provenance
    doc_id: string,
    page: int,
    text_span: string,
    chunk_id: string,
    confidence: float
  }
}]->(b)
```

### Evidence Structure

The `evidence` object appears on both nodes and relationships. It is the core mechanism for source grounding -- every fact in the graph can be traced back to a specific document, page, and text span.

```json
{
  "doc_id": "document_042",
  "page": 156,
  "text_span": "The Committee, under the chairmanship of J. Anderson, resolved to...",
  "chunk_id": "document_042_chunk_0087",
  "confidence": 0.92
}
```

### Entity Normalization (Phase 2)

When a new entity is extracted, it is compared against existing Neo4j nodes using:
1. **Embedding similarity**: Embed the new entity name and compare against existing node names
2. **Fuzzy string matching**: Handle spelling variations in historical documents

If a match is found above threshold, the new entity is merged with the existing node (aliases array updated, evidence added). If no match, a new node is created via MERGE.

---

## 10. Frontend Component Map

The frontend is a React 18 + TypeScript application built in Phase 3. It uses Cytoscape.js for graph rendering, pdf.js for document viewing, and TailwindCSS for styling.

### Layout

```
+--------------------------------------------------------------+
|  GRAPH CANVAS (60-70%)    | SPLITTER |  CHAT PANEL (30-40%)   |
|  Cytoscape.js             | <------> |  Message history       |
|                           |          |  Input box (bottom)    |
|  Highlighted: orange      |          |  Citation badges       |
|  border + pulse animation |          |  [archive:N] [web:N]   |
|  Click node -> sidebar    |          |                        |
+--------------------------------------------------------------+
```

### Component Inventory

| Component | File | Responsibility | Data Flow |
|-----------|------|----------------|-----------|
| **App.tsx** | `frontend/src/App.tsx` | Layout shell, global state management | Top-level container. Orchestrates GraphCanvas and ChatPanel via ResizableSplitter. |
| **GraphCanvas.tsx** | `frontend/src/components/GraphCanvas.tsx` | Cytoscape.js graph rendering and highlight animation | Receives `GraphPayload` from query responses. Renders nodes and edges. Applies orange border + pulse animation to highlighted entities. Click on node triggers NodeSidebar. |
| **ChatPanel.tsx** | `frontend/src/components/ChatPanel.tsx` | Chat message history, text input, loading state | Displays conversation history. Input box at bottom sends question via `useQuery` hook. Renders answer text with embedded `CitationBadge` components. |
| **ResizableSplitter.tsx** | `frontend/src/components/ResizableSplitter.tsx` | Draggable divider between graph and chat | Minimum 30% width on each side. Allows user to resize the two panels. |
| **CitationBadge.tsx** | `frontend/src/components/CitationBadge.tsx` | Clickable citation markers in chat text | `[archive:N]` badges open PDF modal at cited page. `[web:N]` badges open external URL in new tab. |
| **NodeSidebar.tsx** | `frontend/src/components/NodeSidebar.tsx` | Entity detail panel | Slides in when a graph node is clicked. Shows entity name, attributes, evidence, source links. "Ask about this entity" button pre-fills chat input. |

### Custom Hooks

| Hook | File | Responsibility |
|------|------|----------------|
| **useGraphHighlight.ts** | `frontend/src/hooks/useGraphHighlight.ts` | Clear previous highlights, apply new highlights to nodes/edges, animate camera to fit highlighted elements (800ms animation). |
| **useQuery.ts** | `frontend/src/hooks/useQuery.ts` | Manages POST /query calls. Handles loading state, error state, and response parsing. Returns QueryResponse to ChatPanel. |

### PDF Modal

- **Trigger**: Clicking `[archive:N]` badges in chat OR source evidence links in NodeSidebar
- **Flow**:
  1. Frontend calls `GET /document/signed_url?doc_id=X&page=N`
  2. Backend returns time-limited signed URL (15 min expiry)
  3. pdf.js renders PDF at the signed URL
  4. Viewer jumps to the cited page number
  5. User can zoom, scroll, and navigate pages within the modal

### Interaction Flow (End-to-End)

```
1. User types question in ChatPanel input box
   |
   v
2. useQuery hook calls POST /query { question, filter_categories }
   |
   v
3. Backend returns { answer, citations[], graph{} }
   |
   v
4. ChatPanel renders answer text with embedded CitationBadge components
   |
   v
5. useGraphHighlight applies orange highlights to relevant nodes/edges
   |  - Camera animates to fit highlighted region (800ms)
   |
   v
6. User clicks a graph node
   |  -> NodeSidebar slides in with entity details + evidence
   |  -> "Ask about this entity" button pre-fills chat input
   |
   v
7. User clicks [archive:N] badge
   |  -> GET /document/signed_url -> signed URL
   |  -> pdf.js modal opens at cited page
   |
   v
8. User clicks [web:N] badge
      -> New browser tab opens to external URL
```

---

## Appendix: Python Dependencies (Phase 1)

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1
google-cloud-documentai==2.32.0
google-cloud-storage==2.19.0
google-cloud-aiplatform==1.74.0
vertexai==1.74.0
python-multipart==0.0.20
httpx==0.28.1
```

## Appendix: Docker Setup

### Dockerfile (backend)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### docker-compose.yml (infra)

```yaml
version: "3.8"
services:
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    env_file:
      - ../backend/.env
    volumes:
      - ${GOOGLE_APPLICATION_CREDENTIALS:-~/.config/gcloud/application_default_credentials.json}:/app/credentials.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

### Local Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
# http://localhost:8080/health   -> {"status": "ok"}
# http://localhost:8080/docs     -> Swagger UI
```

## Appendix: LLM Prompt Template

The following prompt is used by Gemini 1.5 Flash for answer generation. It enforces strict grounding and citation.

```
Context retrieved from archives and/or web:
"""
{context}
"""

Sources: {citations}
Source type: {source_type}

Rules:
1. Answer ONLY using information from the context above.
2. Cite every fact using [archive:N] or [web:N].
3. If the context does not contain enough information to answer:
   respond exactly: "I cannot answer this based on the available sources."
4. NEVER infer, guess, or use external knowledge.
5. DO NOT merge facts from different sources without citing each.

User question: {question}
```
