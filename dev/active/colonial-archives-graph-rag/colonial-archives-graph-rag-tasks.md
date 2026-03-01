# Colonial Archives Graph-RAG -- Task Tracker

Last Updated: 2026-03-01 (Phase 1 complete, Phase 2 tested E2E, Phase 3 code complete + tested with backend, Phase 4 planned — multi-agent team ready)

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

## Phase 4: Web Augmentation ⏳ IN PROGRESS

**Team execution plan**: `dev/active/phase4-web-augmentation-team/`
**Detailed implementation plan**: `docs/plans/2026-03-01-phase4-web-augmentation.md`

### 4.1 Tavily Web Search Integration [M] [Depends: 1.8]

- [ ] Write `services/web_search.py` with `WebSearchService` class (lazy TavilyClient init)
- [ ] `async search(query, max_results=5)` → list of dicts with id, title, url, text, cite_type
- [ ] Update `services/llm.py` for per-chunk citation types (archive_idx / web_idx counters)
- [ ] Replace Phase 4 placeholder in `services/hybrid_retrieval.py:125-133` with Tavily call
- [ ] Build both `ArchiveCitation` and `WebCitation` in response when source_type is "mixed"
- [ ] Write 4 tests: test_web_search.py (3) + test_llm_mixed.py (1)
- [ ] Commit: "feat: Tavily web search fallback -- trigger on low relevance"

### 4.2 Mixed Citation Rendering [S] ✅ MOSTLY DONE IN PHASE 3

- [x] `CitationBadge.tsx` handles both `[archive:N]` (blue) and `[web:N]` (green) badges
- [x] Web badges open source URL in new tab
- [x] Archive badges open PDF modal
- [ ] Add source type indicator to `ChatMessage.tsx` (archive only / mixed / web)
- [ ] Pass `source_type` from `QueryResponse` through Zustand store to `ChatMessage`
- [ ] Commit: "feat: source type indicator in chat messages"

### 4.3 Category Filter UI [S] ✅ DONE IN PHASE 3

- [x] `CategoryFilter.tsx` with 5 MAIN_CATEGORIES toggle buttons
- [x] Active filter state stored in Zustand (`filterCategories`)
- [x] Categories passed as `filter_categories` in POST /query request
- [x] Visual styling: blue active, gray inactive

### 4.4 Pub/Sub Async Ingestion [XL] — DEFERRED TO PHASE 5

> Current `BackgroundTasks` approach works fine for ~20 docs. Pub/Sub adds operational
> complexity (new GCP resources, IAM, subscriber deployment) without proportional benefit
> at this scale. Revisit when corpus grows beyond 100 documents.

- [ ] Write `services/pubsub.py` with `PubSubService` class
- [ ] Create Pub/Sub topic and subscription configuration
- [ ] Refactor `/ingest_pdf` to publish message to Pub/Sub
- [ ] Write subscriber/worker for ingestion pipeline
- [ ] Persistent job tracking (replace in-memory _jobs dict)
- [ ] Retry logic and dead-letter queue

### 4.5 Auto-Classification [M] [Depends: 1.7, 1.9]

- [ ] Write `services/auto_classification.py` with `AutoClassificationService` class
- [ ] Classification prompt with 5 MAIN_CATEGORIES and descriptions
- [ ] Parse JSON response, validate category against MAIN_CATEGORIES
- [ ] Fallback to "General and Establishment" on error
- [ ] Add `CLASSIFICATION_CONFIDENCE_MIN=0.8` to settings.py
- [ ] Integrate into `routers/ingest.py` Step 3 as fallback when doc not in document_categories.json
- [ ] Flag low-confidence classifications (< 0.8) with log warning
- [ ] Write 3 tests: test_auto_classification.py
- [ ] Commit: "feat: auto-classification -- Gemini classifies unmapped documents"

---

## Phase 5: Scale + Monitoring

### 5.1 Cloud Logging Integration [M] [Depends: 1.1]

- [ ] Configure structured logging with Google Cloud Logging client
- [ ] Add request-scoped trace IDs for end-to-end query tracing
- [ ] Log ingestion pipeline stages with timing (OCR, chunking, embedding, upsert)
- [ ] Log query pipeline stages with timing (embed, vector search, graph, LLM generation)
- [ ] Set up log-based alerting for error rates
- [ ] Commit: "feat: Cloud Logging -- structured logs with trace IDs and stage timing"

### 5.2 Cloud Monitoring Dashboards [M] [Depends: 5.1]

- [ ] Create Cloud Monitoring dashboard for backend service health
- [ ] Add custom metrics: query latency (p50/p95/p99), ingestion throughput, OCR page rate
- [ ] Add vector search latency and hit-rate metrics
- [ ] Add graph query latency metrics (Phase 2+)
- [ ] Set up uptime checks and alerting policies
- [ ] Commit: "feat: Cloud Monitoring dashboards -- latency, throughput, alerting"

### 5.3 OCR Confidence Flagging UI [M] [Depends: 3.3, 1.9]

- [ ] Add admin/status page showing ingested documents and their OCR warnings
- [ ] Display per-page confidence scores for flagged pages (confidence < 0.5)
- [ ] Allow viewing flagged pages in PDF modal for manual review
- [ ] Show aggregated OCR quality stats per document
- [ ] Commit: "feat: OCR confidence UI -- flagged page review for low-quality OCR"

### 5.4 Batch Ingestion [L] [Depends: 4.4]

- [ ] Implement batch ingestion endpoint: accept list of gs:// URLs
- [ ] Publish individual ingestion messages to Pub/Sub for each PDF
- [ ] Build batch progress tracking (aggregate status across all jobs)
- [ ] Add concurrency limits to prevent overwhelming Document AI quotas
- [ ] Implement resumable batch ingestion (skip already-ingested documents)
- [ ] Commit: "feat: batch ingestion -- multi-PDF ingestion with progress tracking"

### 5.5 Performance Optimization [L] [Depends: 2.4]

- [ ] Profile and optimize query pipeline to meet < 2s p95 target
- [ ] Add caching layer for frequent queries (in-memory LRU or Redis)
- [ ] Optimize vector search parameters (num_neighbors, pruning)
- [ ] Optimize Cypher queries with index hints and query planning
- [ ] Add connection pooling for Neo4j and GCS clients
- [ ] Benchmark with realistic workload (concurrent users, large corpus)
- [ ] Commit: "feat: performance optimization -- caching, query tuning, connection pooling"

### 5.6 Mobile Responsive Layout [M] [Depends: 3.8]

- [ ] Add responsive breakpoints to App.tsx layout (stack vertically on small screens)
- [ ] Convert ResizableSplitter to tabs on mobile (toggle graph / chat)
- [ ] Optimize GraphCanvas touch interactions for mobile devices
- [ ] Ensure PDF modal is usable on mobile (pinch-to-zoom, swipe navigation)
- [ ] Test on common mobile viewports (375px, 390px, 414px width)
- [ ] Commit: "feat: mobile responsive layout -- stacked panels, touch support"

### 5.7 CI/CD Pipeline [L]

- [ ] Write `cloudbuild.yaml` for Google Cloud Build
- [ ] Configure build triggers for main branch pushes and pull requests
- [ ] Add lint step (ruff/flake8 for backend, ESLint for frontend)
- [ ] Add unit test step (pytest for backend, vitest/jest for frontend)
- [ ] Add Docker image build and push to Artifact Registry
- [ ] Add Cloud Run deployment step (rolling update, traffic migration)
- [ ] Add smoke test after deployment (health check + sample query)
- [ ] Commit: "feat: CI/CD pipeline -- Cloud Build with lint, test, deploy, smoke test"
