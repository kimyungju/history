# Colonial Archives Graph-RAG -- Task Tracker

Last Updated: 2026-03-01 (Phases 1-4 code complete, Phase 5.1-5.3 + 5.5-5.7 complete, 24 commits on main)

## Status Legend

- S = Small (< 1 hour), M = Medium (1-4 hours), L = Large (4-8 hours), XL = Extra Large (8+ hours)
- Dependencies listed as [Depends: Task X.Y]

---

## Phase 1: Backend Foundation + Vector-Only Query ✅ COMPLETE

### 1.1 Project Skeleton + Configuration [L] ✅

- [x] Create directory structure (backend/app/config, models, routers, services) with `__init__.py` files
- [x] Write `requirements.txt` (FastAPI, uvicorn, pydantic, google-cloud-documentai, google-cloud-storage, google-cloud-aiplatform, vertexai, httpx)
- [x] Write `config/settings.py` with all PLACEHOLDER values (GCP, Doc AI, Vector Search, LLM, Neo4j, Pub/Sub, Tavily, thresholds)
- [x] Write `config/document_categories.json` placeholder with example mappings
- [x] Write `models/schemas.py` (all Pydantic models: request/response, Evidence, Citations, Graph, Chunk, EntityExtractionResult)
- [x] Write `main.py` (FastAPI app with CORS middleware and /health endpoint)
- [x] Write `Dockerfile` (python:3.11-slim, pip install, uvicorn CMD on port 8080)
- [x] Write `.env.example` with all required environment variable names
- [x] Verify app starts locally and GET /health returns `{"status": "ok"}`
- [x] Commit: "feat: Phase 1 skeleton -- FastAPI app, config, schemas, Dockerfile"

### 1.2 Cloud Storage Service [M] ✅

- [x] Write `services/storage.py` with `StorageService` class
- [x] Implement `read_pdf_bytes()` -- download PDF bytes from gs:// URL
- [x] Implement `upload_json()` -- upload dict/list as JSON to GCS, return gs:// URL
- [x] Implement `generate_signed_url()` -- v4 signed URL with configurable expiry (default 15 min)
- [x] Implement `get_doc_id_from_url()` and `get_pdf_url()` helper methods
- [x] Implement `_parse_blob_name()` -- parse gs://bucket/path to blob path
- [x] Commit: "feat: Cloud Storage service -- read PDFs, upload JSON, signed URLs"

### 1.3 Document AI OCR Service [L] ✅

- [x] Write `services/ocr.py` with `OcrService` class and dataclasses (`OcrPageResult`, `OcrResult`)
- [x] Implement `process_pdf()` -- route to single-batch or multi-batch based on page count
- [x] Implement `_process_batch()` -- single Document AI sync request for PDFs <= 15 pages
- [x] Implement `_process_page_range()` -- process specific page range with `IndividualPageSelector`
- [x] Implement batched processing with `asyncio.gather` and `Semaphore(5)` concurrency limit
- [x] Implement `_extract_page_text()` -- extract text using layout text anchors
- [x] Implement `_count_pages()` -- heuristic PDF page count without full parsing
- [x] Commit: "feat: Document AI OCR service -- batched page processing with concurrency"

### 1.4 Text Cleaning + Chunking Service [M] ✅

- [x] Write `services/chunking.py` with `ChunkingService` class
- [x] Implement `clean_and_chunk()` -- clean OCR text, insert `[PAGE:N]` markers, sliding window chunking
- [x] Implement `_clean_text()` -- normalize whitespace, collapse newlines, remove OCR artifacts
- [x] Implement `_find_sentence_boundary()` -- break chunks at sentence boundaries (200-char lookback)
- [x] Implement `_get_pages_for_range()` -- determine which pages a chunk spans
- [x] Implement `_detect_language()` -- CJK ratio heuristic (en/zh/mixed)
- [x] Commit: "feat: chunking service -- page markers, sliding window, language detection"

### 1.5 Vertex AI Embeddings Service [M] ✅

- [x] Write `services/embeddings.py` with `EmbeddingsService` class
- [x] Implement `embed_chunks()` -- batch embed chunk texts with task_type RETRIEVAL_DOCUMENT
- [x] Implement `embed_query()` -- single query embedding with task_type RETRIEVAL_QUERY
- [x] Implement `embed_texts()` -- batch loop (250 per batch), run_in_executor for sync SDK call
- [x] Commit: "feat: Vertex AI embeddings service -- batch embed with text-embedding-004"

### 1.6 Vertex AI Vector Search Service [L] ✅

- [x] Write `services/vector_search.py` with `VectorSearchService` class
- [x] Implement lazy `endpoint` property -- initialize `MatchingEngineIndexEndpoint` on first use
- [x] Implement `upsert()` -- batch upsert (100 per batch) with category restrict metadata
- [x] Implement `search()` -- find_neighbors with top-k and optional category filtering
- [x] Store truncated text (500 chars) as metadata on each datapoint
- [x] Commit: "feat: Vertex AI Vector Search service -- upsert and search with category filtering"

### 1.7 Gemini LLM Service [M] ✅

- [x] Write `services/llm.py` with `LlmService` class
- [x] Write `ANSWER_GENERATION_PROMPT` with strict grounding rules (cite every fact, no inference)
- [x] Implement `generate_answer()` -- build context string with [archive:N]/[web:N] markers
- [x] Configure `GenerationConfig` (temperature=0.1, max_output_tokens=2048)
- [x] Handle empty/failed responses with fallback "I cannot answer" message
- [x] Commit: "feat: Gemini LLM service -- grounded answer generation with citation prompting"

### 1.8 Hybrid Retrieval Service (Vector-Only for Phase 1) [L] ✅

- [x] Write `services/hybrid_retrieval.py` with `HybridRetrievalService` class
- [x] Implement `query()` pipeline: embed question -> vector search -> load chunks -> generate answer
- [x] Implement `_load_chunk_contexts()` -- group results by doc_id, load chunk JSON from GCS, match by chunk_id
- [x] Compute relevance score as avg(vector_similarity) for Phase 1
- [x] Build `ArchiveCitation` list from context chunks (truncated text_span at 300 chars)
- [x] Return `QueryResponse` with graph=None placeholder for Phase 2
- [x] Handle empty vector results gracefully with "I cannot answer" response
- [x] Commit: "feat: hybrid retrieval service -- vector-only query pipeline for Phase 1"

### 1.9 Ingestion Router [M] ✅

- [x] Write `routers/ingest.py` with APIRouter
- [x] Implement POST `/ingest_pdf` -- generate job_id, launch background task
- [x] Implement GET `/ingest_status/{job_id}` -- return job status from in-memory dict
- [x] Implement `_run_ingestion()` background task: download -> OCR -> chunk -> embed -> upsert
- [x] Store OCR output to `gs://bucket/ocr/{doc_id}_ocr.json`
- [x] Store chunk data to `gs://bucket/chunks/{doc_id}.json`
- [x] Flag low-confidence OCR pages (< 0.5) in response warnings
- [x] Load and apply document categories from `document_categories.json`
- [x] Register router in `main.py` via `app.include_router()`
- [x] Commit: "feat: /ingest_pdf endpoint -- full OCR -> chunk -> embed -> vector pipeline"

### 1.10 Query Router [M] ✅

- [x] Write `routers/query.py` with APIRouter
- [x] Implement POST `/query` -- delegate to `hybrid_retrieval_service.query()`
- [x] Implement GET `/document/signed_url` -- accept doc_id and page params, return signed URL
- [x] Register router in `main.py`
- [x] Commit: "feat: /query and /document/signed_url endpoints"

### 1.11 Graph Router Placeholder [S] ✅

- [x] Write `routers/graph.py` with APIRouter (prefix="/graph")
- [x] Implement GET `/graph/{entity_canonical_id}` stub -- return HTTP 501 "Phase 2"
- [x] Implement GET `/graph/search` stub -- return HTTP 501 "Phase 2"
- [x] Register router in `main.py`
- [x] Commit: "feat: graph router stubs (Phase 2 placeholder)"

### 1.12 Docker Compose + Vertex AI Init + Final Verification [M] ✅

- [x] Write `infra/docker-compose.yml` -- backend service with env_file, GCP credentials volume mount
- [x] Add Vertex AI initialization in `main.py` lifespan context manager (vertexai.init on startup)
- [x] Verify app starts locally via `uvicorn app.main:app --reload --port 8080`
- [x] Verify Swagger docs at /docs show all 7 endpoints (ingest_pdf, ingest_status, query, signed_url, graph entity, graph search, health)
- [x] Commit: "feat: docker-compose for local dev, Vertex AI startup init"

---

## Phase 2: Graph Layer ✅ TESTED END-TO-END (all 9 ingestion steps + query + graph search working)

### 2.1 Entity Extraction Service [L] ✅

- [x] Write `services/entity_extraction.py` with `EntityExtractionService` class
- [x] Design Gemini structured output prompt for extracting entities and relationships from OCR text
- [x] Implement `extract_from_chunk()` -- call Gemini with structured JSON output mode (`response_mime_type="application/json"`)
- [x] Parse LLM response into `EntityExtractionResult` schema (entities + relationships with evidence)
- [x] Implement per-chunk extraction loop for integration into ingestion pipeline
- [x] Add confidence threshold filtering (discard low-confidence extractions via `ENTITY_CONFIDENCE_MIN`)
- [ ] Test with sample OCR output from colonial archive documents
- [ ] Commit: "feat: entity extraction service -- Gemini structured output for entities and relationships"

### 2.2 Entity Normalization Service [XL] ✅

- [x] Write `services/entity_normalization.py` with `EntityNormalizationService` class
- [x] Implement embedding-based similarity comparison (embed new entity name, compare to existing via cosine similarity)
- [x] Implement fuzzy string matching as secondary signal (rapidfuzz `token_sort_ratio`)
- [x] Implement alias merging logic (e.g., "J. Anderson" -> "John Anderson")
- [x] Define similarity thresholds for auto-merge (`ENTITY_SIMILARITY_THRESHOLD=0.85`)
- [x] Build canonical_id generation strategy (`entity_{slug}_{counter:03d}`)
- [ ] Test normalization with known colonial-era name variants
- [ ] Commit: "feat: entity normalization -- embedding similarity + fuzzy matching + alias merge"

### 2.3 Neo4j Service [L] ✅

- [x] Write `services/neo4j_service.py` with `Neo4jService` class
- [x] Implement Neo4j AuraDB async connection management (`AsyncGraphDatabase.driver`)
- [x] Implement `merge_entity()` -- MERGE node with canonical_id, update attributes, append aliases and evidence
- [x] Implement `merge_relationship()` -- MERGE edge via `RELATED_TO` label with `rel_type` property, evidence metadata
- [x] Implement `get_subgraph()` -- variable-depth Cypher traversal (1-3 hops) around a seed entity
- [x] Implement `search_entities()` -- CONTAINS search on entity name/aliases
- [x] Add category-based filtering to graph queries
- [x] Add `get_all_entity_names()` and `get_entity_ids_with_prefix()` helpers for normalization
- [x] Wire Neo4j init/close into `main.py` lifespan, add connectivity check to `/health`
- [ ] Commit: "feat: Neo4j service -- MERGE entities/relationships, subgraph traversal, entity search"

### 2.4 Hybrid Query Update [L] ✅

- [x] Update `hybrid_retrieval.py` to run vector search and graph traversal in parallel (asyncio.gather)
- [x] Implement entity hint extraction from query (regex-based capitalized word/phrase extraction, no LLM call)
- [x] Implement graph search seeded from entity hints via `neo4j_service.search_entities()` + `get_subgraph()`
- [x] Merge and deduplicate overlapping text spans from vector + graph results
- [x] Update relevance scoring: avg(vector_similarity) * 0.6 + graph_hit_ratio * 0.4
- [x] Wire web fallback placeholder: logs warning when combined relevance < 0.7 (actual Tavily in Phase 4)
- [x] Include `GraphPayload` (nodes, edges, center_node) in `QueryResponse`
- [ ] Commit: "feat: hybrid retrieval -- parallel vector + graph query, combined scoring"

### 2.5 Graph API Endpoints [M] ✅

- [x] Replace GET `/graph/{entity_canonical_id}` stub with real Neo4j subgraph query
- [x] Replace GET `/graph/search` stub with real entity name search
- [x] Add optional `categories` query param for filtering
- [x] Add `limit` param with validation (1-100, default 20) for search results
- [x] Return `GraphPayload` schema from subgraph endpoint, 404 if entity not found
- [ ] Commit: "feat: graph endpoints -- live entity subgraph and search via Neo4j"

### 2.6 Ingestion Pipeline Graph Integration [L] ✅

- [x] Update `_run_ingestion()` in `routers/ingest.py` to call entity extraction after vector upsert
- [x] Wire entity normalization step after extraction
- [x] Wire Neo4j MERGE step after normalization (entities first, then relationships via `name_to_canonical` mapping)
- [x] Update `IngestResponse` to populate `entities_extracted` count
- [x] Add error handling: graph failures wrapped in try/except, do NOT block vector ingestion
- [ ] Commit: "feat: ingestion pipeline -- entity extraction + normalization + Neo4j merge"

---

## Phase 3: Frontend ✅ CODE COMPLETE (not yet tested with live backend)

> **Execution plan**: `dev/active/phase3-frontend-team/` — multi-agent team (3 parallel agents after foundation)
> **Design doc**: `docs/plans/2026-03-01-phase3-react-frontend-design.md`
> **Implementation plan**: `docs/plans/2026-03-01-phase3-implementation-plan.md` (18 tasks with complete code)

### 3.1 React Project Setup [M] ✅
### 3.2 GraphCanvas Component [L] ✅
### 3.3 ChatPanel Component [L] ✅
### 3.4 ResizableSplitter [S] ✅
### 3.5 CitationBadge + PDF Modal [L] ✅
### 3.6 NodeSidebar [M] ✅
### 3.7 Hooks (useQuery, useGraphHighlight) [M] ✅
### 3.8 Frontend Docker + Integration Testing [L] ⏳ PENDING (needs live backend)

- [x] Write `frontend/Dockerfile` -- multi-stage build (node build -> nginx serve)
- [x] Write `frontend/nginx.conf` -- serve SPA with API proxy to backend
- [ ] Update `infra/docker-compose.yml` to include frontend service
- [ ] Test full flow: type question -> see answer with citations -> click citation -> PDF opens
- [ ] Test graph interaction: query returns graph -> nodes render -> click node -> sidebar opens
- [ ] Test ResizableSplitter drag behavior
- [ ] Commit: "feat: frontend Docker + integration testing"

---

## Phase 4: Web Augmentation ✅ CODE COMPLETE

**Team execution plan**: `dev/active/phase4-web-augmentation-team/`
**Detailed implementation plan**: `docs/plans/2026-03-01-phase4-web-augmentation.md`

### 4.1 Tavily Web Search Integration [M] ✅

- [x] Write `services/web_search.py` with `WebSearchService` class (lazy TavilyClient init)
- [x] `async search(query, max_results=5)` → list of dicts with id, title, url, text, cite_type
- [x] Update `services/llm.py` for per-chunk citation types (archive_idx / web_idx counters)
- [x] Wire web fallback in `services/hybrid_retrieval.py` — triggered when relevance < 0.7
- [x] Build both `ArchiveCitation` and `WebCitation` in response when source_type is "mixed"
- [x] 3 tests in test_web_search.py — all PASS

### 4.2 Mixed Citation Rendering [S] ✅

- [x] `CitationBadge.tsx` handles both `[archive:N]` (blue) and `[web:N]` (green) badges
- [x] Web badges open source URL in new tab
- [x] Archive badges open PDF modal
- [x] Source type indicator in `ChatMessage.tsx` (archive only / mixed / web)
- [x] `source_type` from `QueryResponse` passed through Zustand store to `ChatMessage`

### 4.3 Category Filter UI [S] ✅ DONE IN PHASE 3

- [x] `CategoryFilter.tsx` with 5 MAIN_CATEGORIES toggle buttons
- [x] Active filter state stored in Zustand (`filterCategories`)
- [x] Categories passed as `filter_categories` in POST /query request
- [x] Visual styling: blue active, gray inactive

### 4.4 Pub/Sub Async Ingestion [XL] — DEFERRED

> Current `BackgroundTasks` approach works fine for ~20 docs. Pub/Sub adds operational
> complexity (new GCP resources, IAM, subscriber deployment) without proportional benefit
> at this scale. Revisit when corpus grows beyond 100 documents.

### 4.5 Auto-Classification [M] ✅

- [x] Write `services/auto_classification.py` with `AutoClassificationService` class
- [x] Classification prompt with 5 MAIN_CATEGORIES and descriptions
- [x] Parse JSON response, validate category against MAIN_CATEGORIES
- [x] Fallback to "General and Establishment" on error
- [x] `CLASSIFICATION_CONFIDENCE_MIN=0.8` in settings.py
- [x] Integrated into `routers/ingest.py` Step 3 as fallback when doc not in document_categories.json
- [x] Flag low-confidence classifications (< 0.8) with log warning
- [x] 3 tests in test_auto_classification.py — all PASS

---

## Phase 5: Scale + Monitoring

> **Team execution**: `dev/active/phase5-cicd-logging-team/`
> **Implementation plan**: `docs/plans/2026-03-01-phase5-cicd-logging.md`

### 5.1 Cloud Logging Integration [M] ✅ COMPLETE

- [x] Structured JSON logging via CloudJsonFormatter to stdout (Cloud Run auto-captures)
- [x] Request-scoped trace IDs via contextvars + TraceMiddleware (X-Cloud-Trace-Context)
- [x] 9 ingestion stages timed with log_stage() context manager
- [x] 3 query stages timed (embed, search, llm_generation)
- [x] Log-based alerting config (infra/logging/alert-policy.json)
- [x] 11 unit tests (6 formatter + 3 middleware + 2 log_stage)
- [x] Commits: a85c0b3, f1360c7, ba284ac, ee160b7

### 5.2 Cloud Monitoring Dashboards [M] ✅ COMPLETE

- [x] Cloud Monitoring dashboard config (`infra/monitoring/dashboard.json`) with 4 widgets:
  - Error rate (severity >= ERROR)
  - Query latency by stage (vector_search, graph_search, llm_generation)
  - Ingestion stage latency (ocr, chunking, embedding, vector_upsert, entity_extraction, etc.)
  - Request count
- [x] Deploy command: `gcloud monitoring dashboards create --config-from-file=infra/monitoring/dashboard.json`
- [x] Commit `b0dc7f5`

### 5.3 OCR Confidence Flagging UI [M] ✅ COMPLETE

- [x] Backend: `GET /admin/documents` — list all ingested doc IDs from GCS `ocr/` prefix
- [x] Backend: `GET /admin/documents/{doc_id}/ocr` — per-page confidence, flagged pages, avg confidence
- [x] Frontend: `AdminPanel.tsx` modal — lists documents, shows OCR quality per doc
- [x] Flagged pages highlighted in red, click to open in PDF modal for review
- [x] Admin toggle button in graph panel corner
- [x] 2 backend tests (test_admin.py) — PASS
- [x] Commits: `a63ebc6` (backend), `2572e52` (frontend)

### 5.4 Batch Ingestion [L] — DEFERRED [Depends: 4.4]

> Depends on Pub/Sub (4.4), which is deferred. Not needed at current scale (~20 docs).

### 5.5 Performance Optimization [L] ✅ COMPLETE

- [x] Parallelize GCS chunk loading: `asyncio.gather` + `run_in_executor` replaces sequential loop
- [x] Parallelize graph entity search: 2-phase gather (search_entities, then get_subgraph)
- [x] Split `query_search` log_stage into separate `vector_search` + `graph_search` for observability
- [x] 3 tests in test_hybrid_retrieval.py — PASS
- [x] Commits: `6e02265`, `da8f427`, `45bdc6d`

### 5.6 Mobile Responsive Layout [M] ✅ COMPLETE

- [x] `useIsMobile` hook — media query breakpoint detection at 768px
- [x] App.tsx: stacked single-panel layout on mobile with tab bar (Knowledge Graph / Chat)
- [x] Desktop layout unchanged (side-by-side grid with splitter)
- [x] Touch support for ResizableSplitter (onTouchStart/Move/End)
- [x] 2 tests for useIsMobile hook — PASS
- [x] Commits: `e7abe29`, `e940b51`, `8d2521a`

### 5.7 CI/CD Pipeline [L] ✅ CODE COMPLETE (GCP infra not yet provisioned)

- [x] `cloudbuild.yaml` — 11-step Cloud Build pipeline (lint→test→build→push→deploy→smoke)
- [x] Backend lint (ruff) + test (pytest) run in parallel with frontend checks
- [x] Frontend: npm ci + ESLint + tsc --noEmit + vitest
- [x] Docker build + push to Artifact Registry (asia-southeast1)
- [x] Cloud Run deploy with Secret Manager refs for Neo4j creds
- [x] Post-deploy smoke test (curl /health + assert)
- [x] Dockerfile hardened with non-root appuser
- [x] Frontend `"test": "vitest run"` script added to package.json
- [x] Backend health check test with mock_gcp fixture (conftest.py)
- [x] Commits: c73aed7, 2fb9862, 5ec8f5d, d6cf190
- [ ] **T11 remaining**: Create Artifact Registry repo, Secret Manager secrets, IAM roles, build trigger
- [ ] Test pipeline: `gcloud builds submit . --config=cloudbuild.yaml`
