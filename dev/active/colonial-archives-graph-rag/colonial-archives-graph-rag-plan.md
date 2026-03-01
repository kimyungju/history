# Colonial Archives Graph-RAG System — Implementation Plan

**Last Updated: 2026-03-01 (Phase 1 complete, Phase 2 next)**

---

## 1. Executive Summary

The Colonial Archives Graph-RAG system is an AI-powered research tool that enables academic researchers to query, explore, and cite colonial-era handwritten archive documents through a chatbot interface backed by an interactive knowledge graph. The system ingests 100+ large PDFs (300-500 pages each, totaling 30,000-50,000 pages) from Cloud Storage, performs OCR using Google Document AI, builds vector embeddings and a Neo4j knowledge graph, and generates source-grounded answers using Gemini 1.5 Flash. Every answer, every graph node, and every relationship must trace back to a specific document page and text snippet — the system is designed with zero tolerance for hallucination or inferred facts.

The technology stack is built entirely on Google Cloud Platform services with no LangChain dependency — all GCP SDK calls are made directly from a FastAPI backend deployed on Cloud Run. The stack includes Document AI for multilingual OCR, Vertex AI text-embedding-004 for embeddings, Vertex AI Vector Search for semantic retrieval, Neo4j AuraDB (GCP-hosted) for the knowledge graph, Gemini 1.5 Flash for answer generation with structured output, and Tavily API as a web search fallback. The frontend is a React 18 + TypeScript application using Cytoscape.js for interactive graph visualization, TailwindCSS for styling, and pdf.js for in-browser document viewing with signed Cloud Storage URLs.

The project follows a 5-phase build approach: Phase 1 establishes the backend foundation with a vector-only query pipeline (OCR, chunking, embedding, retrieval, and LLM answer generation). Phase 2 adds the graph layer with entity extraction, normalization, and Neo4j integration. Phase 3 delivers the full frontend with graph canvas, chat panel, and PDF viewer. Phase 4 introduces Tavily web fallback, Pub/Sub async ingestion, and category filtering. Phase 5 focuses on scale, monitoring, CI/CD, and production hardening. Each phase builds on the previous one, with Phase 2 requiring Neo4j AuraDB provisioning as its only external dependency gate.

---

## 2. Current State Analysis

### Project Status

- **Phase 1: COMPLETE**. All 12 Phase 1 tasks implemented. Full backend foundation: FastAPI app, all 7 services, all 3 routers, Docker Compose.
- **Phase 2: CODE COMPLETE**. All 6 Phase 2 tasks implemented. Neo4j AuraDB free tier provisioned (`neo4j+s://3d0eb007.databases.neo4j.io`). Three new services created (entity extraction, normalization, Neo4j). Hybrid retrieval upgraded to parallel vector+graph. Graph router stubs replaced with real endpoints. Ingestion pipeline extended with entity extraction → normalization → Neo4j MERGE. **Not yet tested end-to-end with real data.**
- **Phase 3: NOT STARTED**. Next phase — React frontend.
- **Documentation**: Design document (approved), Phase 1 implementation plan (executed), context reference document, and task tracker are all up to date.
- **Design Decisions**: All major architectural decisions have been finalized — tech stack, deployment model, chunking strategy, category taxonomy, citation format, and API contracts are documented and locked.

### Infrastructure Status

- **GCP Project**: Already set up and active. The GCP project exists with billing enabled.
- **Cloud Storage**: Documents (100+ colonial-era PDFs) are already uploaded and accessible in a Cloud Storage bucket.
- **Document AI**: Processor needs to be provisioned (multilingual handwritten processor). The processor ID is a placeholder in the settings.
- **Vertex AI**: Embedding model (text-embedding-004) and Gemini 1.5 Flash are available via Vertex AI. Vector Search index and endpoint need to be created and deployed.
- **Neo4j AuraDB**: **Not yet provisioned. BLOCKING for Phase 2.** Must be provisioned before Phase 2 begins. Free tier is sufficient (200k nodes, 400k relationships). Region/cloud provider is assigned by Neo4j — no impact on functionality.
- **Cloud Run**: Not yet configured. Two services will be deployed — one for the FastAPI backend, one for the React frontend (nginx container).

### Document Corpus

- **Volume**: 100+ PDF files, each 300-500 pages, totaling approximately 30,000-50,000 pages.
- **Language**: Mostly English with some Chinese content. Mixed-language pages are expected.
- **Format**: Handwritten and typed colonial-era archive documents. OCR quality will vary significantly across documents.
- **Categories**: Five predefined main categories — Internal Relations and Research, Economic and Financial, Social Services, Defence and Military, General and Establishment. Document-to-category mappings will be provided via `document_categories.json` before ingestion.

---

## 3. Proposed Future State

### System Overview

The completed system will be a full-stack AI research platform consisting of:

- **FastAPI Backend** (Cloud Run): Handles PDF ingestion (OCR, chunking, embedding, entity extraction, graph population), query processing (vector search, graph traversal, LLM answer generation), and document serving (signed URLs). Exposes RESTful API endpoints for all operations.
- **React Frontend** (Cloud Run, nginx container): Split-panel interface with an interactive Cytoscape.js graph canvas (60-70% width) and a chat panel (30-40% width) connected by a resizable splitter. Includes citation badges linking to source evidence, a node sidebar for entity details, and a pdf.js modal for in-browser document viewing at the cited page.
- **Document AI OCR Pipeline**: Processes handwritten/typed PDFs using Google Document AI's multilingual handwritten processor. Batches pages in groups of 15 with asyncio concurrency limits. Flags low-confidence pages (confidence < 0.5) for manual review.
- **Vertex AI Embeddings + Vector Search**: Embeds text chunks using text-embedding-004 (multilingual, 768-dimensional). Stores embeddings in Vertex AI Vector Search with category metadata for filtered retrieval. Returns top-10 nearest neighbors by cosine similarity.
- **Neo4j Knowledge Graph**: Stores entities (persons, organizations, locations, events, policies) and relationships extracted by Gemini Flash structured output. Uses MERGE operations exclusively to prevent duplicates. Supports 1-3 hop Cypher traversals from seed entities. All nodes and edges carry evidence metadata linking back to source documents.
- **Gemini 1.5 Flash Answer Generation**: Generates cited answers using strict grounding prompts. Every fact must be cited with `[archive:N]` or `[web:N]` markers. Temperature set to 0.1 for deterministic output. Responds with "I cannot answer this based on the available sources" when context is insufficient.
- **Tavily Web Fallback**: Triggered when average relevance score falls below 0.7. Web results are clearly separated with `source_type: "web"` and distinct citation badges. Supplements but never replaces archive evidence.

### User Experience

- **Open Access**: No authentication or login required. Academic researchers access the system via a public URL.
- **Query Workflow**: User types a natural language question in the chat panel. The system retrieves relevant chunks via vector search and graph traversal (in parallel), generates a cited answer, and highlights relevant entities/edges on the graph canvas with an animated camera fit (800ms).
- **Citation Verification**: Every `[archive:N]` badge in the answer is clickable, opening a pdf.js modal that renders the original PDF at the exact cited page. Users can zoom, scroll, and navigate pages. Every `[web:N]` badge opens the web source in a new tab.
- **Graph Exploration**: Users can click any node on the graph canvas to open a sidebar showing entity details, attributes, aliases, evidence links, and an "Ask about this entity" button that pre-fills the chat input.
- **Category Filtering**: Optional dropdown filter in the chat panel restricts retrieval to specific document categories.

---

## 4. Implementation Phases

### Phase 1: Backend Foundation + Vector-Only Query

**Goal**: Build a working FastAPI backend that ingests PDFs from Cloud Storage (OCR, chunk, embed, vector index) and answers questions via vector-only retrieval with Gemini-generated cited answers.

**Architecture**: FastAPI monolith on Cloud Run. Direct Google Cloud SDK calls. Sync ingestion. No Neo4j, no graph, no frontend.

**12 Tasks**:

| Task | Description | Key Deliverables |
|------|-------------|------------------|
| 1 | **Project Skeleton + Configuration** | Directory structure (`backend/app/`), `main.py` with FastAPI app + CORS + health endpoint, `config/settings.py` with all PLACEHOLDER values (GCP, Document AI, Vector Search, Neo4j, Tavily, thresholds), `models/schemas.py` with full Pydantic v2 schemas (IngestRequest/Response, QueryRequest/Response, Chunk, Evidence, Citation models, GraphNode/Edge/Payload stubs), `requirements.txt`, `Dockerfile`, `.env.example`, `document_categories.json` template |
| 2 | **Cloud Storage Service** | `services/storage.py` — read PDF bytes from `gs://` URLs, upload JSON to GCS, generate signed URLs (v4, 15-min expiry), extract doc_id from URL, build PDF URL from doc_id |
| 3 | **Document AI OCR Service** | `services/ocr.py` — OCR full PDFs using Document AI sync API, batch pages in groups of 15, asyncio.gather with Semaphore(5) for concurrency, extract page text via layout text anchors, return `OcrResult` with per-page text + confidence scores |
| 4 | **Text Cleaning + Chunking Service** | `services/chunking.py` — normalize whitespace/unicode, remove OCR artifacts, concatenate pages with `[PAGE:N]` markers, sliding window chunking (300-600 tokens, 100 overlap), sentence boundary detection, page span tracking, heuristic language detection (en/zh/mixed) |
| 5 | **Vertex AI Embeddings Service** | `services/embeddings.py` — embed chunks using text-embedding-004 with `RETRIEVAL_DOCUMENT` task type, embed queries with `RETRIEVAL_QUERY` task type, batch in groups of 250 (Vertex AI limit) |
| 6 | **Vertex AI Vector Search Service** | `services/vector_search.py` — upsert chunk embeddings with category metadata (Namespace restricts), batch upserts in groups of 100, search with top-K nearest neighbors and optional category filtering |
| 7 | **Gemini LLM Service** | `services/llm.py` — generate cited answers using Gemini 1.5 Flash, strict grounding prompt (cite every fact, never infer, explicit "I cannot answer" fallback), temperature 0.1, max 2048 output tokens |
| 8 | **Hybrid Retrieval Service (Vector-Only)** | `services/hybrid_retrieval.py` — full query pipeline: embed question, vector search, load chunk texts from GCS, compute relevance score (avg vector similarity), generate answer with citations, build QueryResponse. Graph retrieval placeholder for Phase 2 |
| 9 | **Ingestion Router** | `routers/ingest.py` — `POST /ingest_pdf` endpoint accepting `gs://` URL, background task execution, in-memory job tracking (`_jobs` dict), `GET /ingest_status/{job_id}` for polling, full pipeline: download PDF, OCR, category lookup, chunk, embed, vector upsert, GCS storage of OCR output and chunks |
| 10 | **Query Router** | `routers/query.py` — `POST /query` endpoint accepting question + optional category filter, `GET /document/signed_url` endpoint returning time-limited signed URL for pdf.js viewer |
| 11 | **Graph Router Placeholder** | `routers/graph.py` — stub endpoints `GET /graph/{entity_canonical_id}` and `GET /graph/search` returning HTTP 501 "available in Phase 2" |
| 12 | **Docker Compose + Vertex AI Init + Verification** | `infra/docker-compose.yml` for local development (mounts GCP credentials), add Vertex AI initialization to FastAPI lifespan handler, verify all endpoints visible in Swagger UI |

**Phase 1 Exit Criteria**:
- FastAPI app starts locally and renders Swagger docs at `/docs`
- All 7 endpoints visible: `/ingest_pdf`, `/ingest_status/{job_id}`, `/query`, `/document/signed_url`, `/graph/{id}`, `/graph/search`, `/health`
- Ingestion pipeline runs end-to-end: PDF download, OCR, chunking, embedding, vector upsert
- Query pipeline runs end-to-end: question embedding, vector search, chunk loading, LLM answer generation with citations
- Signed URL generation works for PDF viewer

### Phase 2: Graph Layer

**Goal**: Add entity extraction, normalization, and Neo4j knowledge graph to enable hybrid vector + graph retrieval.

**Prerequisites**: Neo4j AuraDB instance provisioned and accessible.

**Key Tasks**:

| Task | Description |
|------|-------------|
| 2.1 | **Neo4j Connection Service** — `services/neo4j_service.py` with connection pooling, Cypher query execution, health check. Use official `neo4j` Python driver. Connection URI, user, and password from settings. |
| 2.2 | **Entity Extraction Service** — `services/entity_extraction.py` using Gemini 1.5 Flash structured JSON output. Per-chunk extraction of entities (name, categories, sub_category, attributes, evidence) and relationships (from_entity, to_entity, type, attributes, evidence). Batch processing with rate limiting. |
| 2.3 | **Entity Normalization Service** — `services/entity_normalization.py` comparing new entities against existing Neo4j nodes. Three-stage matching: (a) exact name match, (b) embedding similarity (text-embedding-004 on entity names), (c) fuzzy string match (Levenshtein distance). Merge aliases (e.g., "J. Anderson" becomes alias of "John Anderson"). Confidence threshold for auto-merge vs. manual review flagging. |
| 2.4 | **Neo4j MERGE Pipeline** — Extend ingestion pipeline to MERGE entities and relationships into Neo4j after vector upsert. Always use MERGE (never CREATE) to prevent duplicates. Store full evidence metadata on every node and relationship. Handle concurrent ingestion safely. |
| 2.5 | **Hybrid Query Service** — Upgrade `hybrid_retrieval.py` to run vector search and Cypher graph traversal in parallel (asyncio.gather). Seed graph traversal from entity hints extracted via keyword matching. 1-3 hop traversals, filtered by categories, ordered by confidence, limited to 50 results. Merged relevance score: `avg(vector_similarity) * 0.6 + graph_hit_ratio * 0.4`. |
| 2.6 | **Graph API Endpoints** — Implement `GET /graph/{canonical_id}` returning subgraph (nodes + edges + evidence) around an entity. Implement `GET /graph/search?q={query}` for entity name search with fuzzy matching. Return `GraphPayload` with highlighted nodes/edges. |
| 2.7 | **Integration Testing** — End-to-end test: ingest PDF, verify entities appear in Neo4j, query with entity name, verify graph data in response, verify hybrid scoring improves relevance. |

### Phase 3: Frontend

**Goal**: Build the full React frontend with interactive graph visualization, chat interface, and PDF viewer.

**Key Tasks**:

| Task | Description |
|------|-------------|
| 3.1 | **React Project Setup** — Create React 18 + TypeScript project with TailwindCSS. Configure nginx Dockerfile for Cloud Run deployment. Set up API proxy configuration for local development. |
| 3.2 | **App Layout Shell** — `App.tsx` with global state management (React Context or Zustand). Split-panel layout: GraphCanvas (60-70%) + ChatPanel (30-40%). |
| 3.3 | **ResizableSplitter Component** — Draggable vertical divider between graph and chat panels. Minimum 30% width on each side. Smooth drag interaction with cursor feedback. |
| 3.4 | **ChatPanel Component** — Message history display (user questions + system answers). Input box fixed at bottom with send button. Loading state with skeleton/spinner during query execution. Error state display. |
| 3.5 | **useQuery Hook** — Custom React hook for `POST /query`. Manages loading, error, and response state. Parses citations and graph data from response. Triggers graph highlighting on successful response. |
| 3.6 | **GraphCanvas Component** — Cytoscape.js rendering of knowledge graph. Node styling by category (color-coded). Edge labels showing relationship types. Zoom, pan, and click interactions. Layout algorithm (e.g., CoSE or COSE-Bilkent for organic graph layout). |
| 3.7 | **useGraphHighlight Hook** — Clear previous highlights, apply orange border + pulse animation to relevant nodes/edges from query response. Animate camera to fit highlighted subgraph (800ms transition). |
| 3.8 | **CitationBadge Component** — Inline `[archive:N]` badges that open PDF modal on click. Inline `[web:N]` badges that open source URL in new tab. Styled distinctly (archive = blue, web = green). |
| 3.9 | **NodeSidebar Component** — Slides in from the right when a graph node is clicked. Shows entity name, canonical_id, categories, sub_category, aliases, attributes (key-value pairs), and evidence links. "Ask about this entity" button pre-fills chat input with entity name. Evidence links are clickable, opening PDF modal. |
| 3.10 | **PDF Modal** — Full-screen modal using pdf.js to render PDFs. Calls `GET /document/signed_url?doc_id=X&page=N` to get time-limited URL. Jumps to the cited page on open. Supports zoom, scroll, and page navigation. Close button and escape key dismiss. |
| 3.11 | **Category Filter Dropdown** — Optional multi-select dropdown in the chat panel. Passes `filter_categories` to `/query` endpoint. Displays the 5 MAIN_CATEGORIES. |
| 3.12 | **Frontend Docker + Cloud Run Config** — Nginx Dockerfile serving built React app. Cloud Run service configuration. Environment variable injection for API base URL. |

### Phase 4: Web Fallback + Polish

**Goal**: Add Tavily web search fallback, Pub/Sub async ingestion, and UI refinements.

**Key Tasks**:

| Task | Description |
|------|-------------|
| 4.1 | **Tavily Web Search Integration** — `services/web_search.py` using Tavily API. Triggered when average relevance score < 0.7 (configurable threshold). Returns results with `source_type: "web"` and `cite_type: "web"`. Basic search depth for speed. |
| 4.2 | **Mixed Source Response Handling** — Update `hybrid_retrieval.py` to append web results to archive results when fallback is triggered. Set `source_type` to "mixed" when both archive and web sources are present. Build WebCitation objects for web results. |
| 4.3 | **Web Citation Badges (Frontend)** — `[web:N]` badges in ChatPanel open source URL in new tab. Visually distinct from archive badges (different color/icon). |
| 4.4 | **Pub/Sub Async Ingestion** — Create Pub/Sub topic and subscription. Refactor `/ingest_pdf` to publish message to Pub/Sub instead of running background task. Create Pub/Sub push subscriber endpoint that executes the ingestion pipeline. Update `GET /ingest_status` to track jobs via Firestore or Cloud Storage metadata instead of in-memory dict. |
| 4.5 | **Auto-Classification for Unmapped Documents** — When `document_categories.json` has no entry for a PDF, use Gemini Flash to auto-classify into MAIN_CATEGORIES. Flag classifications with confidence < 0.8 for manual review. Store auto-classifications back to GCS. |
| 4.6 | **Category Filter UI Polish** — Improve category filter dropdown with clear selection, select all/none, and visual feedback on active filters. Show result counts per category if feasible. |

### Phase 5: Scale + Monitoring

**Goal**: Production-harden the system with monitoring, batch ingestion, CI/CD, and performance optimization.

**Key Tasks**:

| Task | Description |
|------|-------------|
| 5.1 | **Cloud Logging Integration** — Structured JSON logging throughout the backend. Log ingestion pipeline stages, query latency breakdown, OCR confidence warnings, entity extraction counts, and error traces. Integrate with Cloud Logging for centralized log management. |
| 5.2 | **Cloud Monitoring + Alerting** — Custom metrics for query latency (p50, p95, p99), ingestion throughput (pages/minute), OCR confidence distribution, vector search hit rate, and error rates. Set up alerting for latency spikes and error rate thresholds. |
| 5.3 | **OCR Confidence Flagging UI** — Admin-facing page in the frontend showing pages with OCR confidence < 0.5. Sortable by document and confidence. Link to PDF viewer for manual review. Allow marking pages as "reviewed" or "needs re-scan". |
| 5.4 | **Batch Ingestion** — Accept multiple PDF URLs in a single request. Queue ingestion jobs and process sequentially or with controlled parallelism. Progress tracking across the batch. Resume capability for partially failed batches. |
| 5.5 | **Query Latency Optimization** — Profile and optimize the query pipeline to meet <2s p95 target. Strategies: connection pooling for Neo4j, caching frequently accessed chunks, pre-warming Vector Search endpoint, optimizing Cypher queries with indexes, reducing Gemini prompt size. |
| 5.6 | **Mobile Responsive Layout** — Adapt the split-panel layout for mobile screens. Stack graph canvas and chat panel vertically on small screens. Touch-friendly graph interactions. Responsive PDF modal. |
| 5.7 | **CI/CD Pipeline** — `cloudbuild.yaml` for automated builds and deployments. Triggered on push to main branch. Build and push Docker images to Artifact Registry. Deploy to Cloud Run. Run basic health checks post-deployment. |
| 5.8 | **Vector Search Index Optimization** — Optimize shard configuration for the full corpus (30k-50k pages). Evaluate index rebuild frequency. Monitor query latency vs. index size. Consider approximate nearest neighbor tuning (tree depth, leaf size). |

---

## 5. Risk Assessment and Mitigation

### Risk 1: Document AI OCR Quality on Handwritten Text

- **Severity**: High
- **Likelihood**: High (colonial-era handwriting varies enormously in legibility)
- **Impact**: Poor OCR quality degrades chunking, embedding quality, entity extraction, and ultimately answer accuracy. Garbled text produces meaningless embeddings and false entity extractions.
- **Mitigation**:
  - Flag every page with OCR confidence < 0.5 in the ingestion response (`ocr_confidence_warnings`).
  - Store raw OCR output to GCS (`ocr/{doc_id}_ocr.json`) for inspection and re-processing.
  - Build an OCR confidence flagging UI in Phase 5 for manual review of low-confidence pages.
  - Use Document AI's multilingual handwritten processor (specifically designed for handwriting).
  - Consider re-processing low-confidence pages with alternative settings or manual transcription for critical documents.
  - Set a success metric: OCR confidence > 0.5 on 90%+ of pages.

### Risk 2: Entity Normalization Accuracy

- **Severity**: High
- **Likelihood**: Medium (colonial documents use inconsistent naming — abbreviations, titles, transliterations)
- **Impact**: Poor normalization creates duplicate entities in Neo4j, fragmenting the knowledge graph and reducing retrieval quality. "J. Anderson", "John Anderson", "Anderson, J." must all resolve to one canonical entity.
- **Mitigation**:
  - Three-stage matching pipeline: (1) exact name match, (2) embedding similarity using text-embedding-004 on entity names, (3) fuzzy string match (Levenshtein distance / Jaro-Winkler).
  - Confidence threshold for auto-merge (high confidence) vs. flagging for manual review (low confidence).
  - Always use Neo4j MERGE operations — never CREATE — to prevent duplicates at the database level.
  - Store all aliases on the entity node for future matching.
  - Set a success metric: entity normalization accuracy > 85%.

### Risk 3: Vector Search Index Size at Scale

- **Severity**: Medium
- **Likelihood**: Medium (30k-50k pages producing potentially 50k-100k+ chunks)
- **Impact**: Large index sizes can increase query latency, raise costs, and hit Vertex AI Vector Search quotas. Index rebuild times may become prohibitive.
- **Mitigation**:
  - Batch upserts in groups of 100 to avoid API rate limits.
  - Monitor index size and shard configuration as the corpus grows.
  - Optimize shard count and approximate nearest neighbor parameters (tree depth, leaf size) in Phase 5.
  - Use category metadata filtering (Namespace restricts) to reduce the search space per query.
  - Consider index partitioning by document category if latency degrades.

### Risk 4: Gemini Hallucination Risk

- **Severity**: Critical (for an academic research tool, hallucinated facts are unacceptable)
- **Likelihood**: Low-Medium (Gemini Flash is capable but not immune to hallucination)
- **Impact**: Fabricated facts with false citations would destroy researcher trust and produce incorrect scholarship. This is the highest-impact risk for the project.
- **Mitigation**:
  - Strict grounding prompt with explicit rules: "Answer ONLY using information from the context above", "Cite every fact using [archive:N] or [web:N]", "NEVER infer, guess, or use external knowledge".
  - Explicit fallback instruction: "If the context does not contain enough information to answer, respond exactly: I cannot answer this based on the available sources."
  - Low temperature (0.1) for deterministic, conservative output.
  - Citation-only answers: every claim must have a corresponding `[archive:N]` or `[web:N]` marker.
  - Structured output mode to enforce response schema.
  - All citations link directly to the source PDF page via the pdf.js viewer, enabling immediate human verification.
  - Set a success metric: zero hallucinated facts (every claim has a verifiable citation).

### Risk 5: Neo4j AuraDB Free Tier Limits

- **Severity**: Medium
- **Likelihood**: Medium (free tier has node/relationship/storage limits)
- **Impact**: If the knowledge graph exceeds free tier limits, ingestion will fail and the graph will be incomplete.
- **Mitigation**:
  - Monitor node count, relationship count, and storage usage during Phase 2 development.
  - Estimate graph size before full ingestion: if 100 entities per document with 200 relationships, the full corpus could produce 10k+ nodes and 20k+ relationships.
  - Plan upgrade path to AuraDB Professional if free tier is insufficient.
  - Optimize entity normalization to minimize duplicate nodes.
  - Consider pruning low-confidence entities (confidence < 0.5) to reduce graph size.

### Risk 6: API Quota Exhaustion with 30k-50k Pages

- **Severity**: Medium
- **Likelihood**: Medium-High (ingesting the full corpus requires thousands of API calls)
- **Impact**: Hitting Document AI, Vertex AI Embeddings, or Gemini Flash quotas will halt ingestion mid-pipeline, leaving the system in a partially indexed state.
- **Mitigation**:
  - Concurrency limits throughout the pipeline: Semaphore(5) for Document AI OCR, batch size 250 for embeddings, batch size 100 for vector upserts.
  - Retry with exponential backoff on transient API errors (429 Too Many Requests, 503 Service Unavailable).
  - Idempotent ingestion: re-ingesting the same PDF overwrites chunks/vectors (keyed by doc_id + chunk_id), so partial failures can be resumed.
  - Monitor API quota usage via Cloud Monitoring dashboards.
  - Request quota increases from Google Cloud before full corpus ingestion if needed.
  - Phase the full ingestion: process documents in batches of 10-20 with monitoring between batches.

---

## 6. Success Metrics

### Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Query latency (p95) | < 2 seconds | Cloud Monitoring custom metric on `/query` endpoint. Breakdown: vector search ~100ms, Gemini generation ~1-1.5s, overhead ~200ms. |
| Query latency (p50) | < 1.5 seconds | Cloud Monitoring custom metric. |
| Ingestion throughput | > 5 pages/minute sustained | Log-based metric on ingestion pipeline stages. |
| Vector search latency | < 200ms p95 | Measured at the Vector Search API call boundary. |

### Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| OCR confidence | > 0.5 on 90%+ of pages | Aggregated from `ocr_confidence_warnings` across all ingested documents. |
| Zero hallucinated facts | Every claim has a verifiable citation | Manual audit of sample queries. Every `[archive:N]` badge must link to source text that supports the claim. |
| Entity normalization accuracy | > 85% | Manual audit of merged entities in Neo4j. Sample 100 entities and verify alias groupings are correct. |
| Citation accuracy | 100% of citations point to correct source | Verify that clicking `[archive:N]` opens the correct document at the correct page with relevant text visible. |

### Completeness Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Corpus ingestion | All 100+ PDFs fully ingested and queryable | Verify every PDF has corresponding chunks in Vector Search and entities in Neo4j. |
| Page coverage | > 95% of pages successfully OCR'd | Compare ingested page count vs. expected page count per document. |
| Category coverage | Every document assigned to at least one MAIN_CATEGORY | Audit `document_categories.json` completeness plus auto-classification coverage. |

### User Experience Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| PDF viewer load time | < 3 seconds for signed URL generation + PDF render | Browser performance measurement. |
| Graph render time | < 500ms for subgraphs up to 50 nodes | Cytoscape.js render timing. |
| Frontend initial load | < 2 seconds (first contentful paint) | Lighthouse audit. |

---

## 7. Required Resources and Dependencies

### Google Cloud Platform Services

| Service | Purpose | SDK / API |
|---------|---------|-----------|
| Cloud Storage | Raw PDF storage, OCR output, chunk JSON | `google-cloud-storage` (Python SDK) |
| Document AI | OCR for handwritten/typed PDFs | `google-cloud-documentai` (Python SDK) |
| Vertex AI Embeddings | text-embedding-004 for chunk and query embeddings | `google-cloud-aiplatform`, `vertexai` (Python SDK) |
| Vertex AI Vector Search | Semantic similarity search over chunk embeddings | `google-cloud-aiplatform` (Matching Engine API) |
| Vertex AI Generative AI | Gemini 1.5 Flash for answer generation + entity extraction | `vertexai` (GenerativeModel API) |
| Cloud Run | Container deployment for backend and frontend | `gcloud` CLI for deployment |
| Pub/Sub (Phase 4) | Async ingestion message queue | `google-cloud-pubsub` (Python SDK) |
| Cloud Logging (Phase 5) | Centralized structured logging | `google-cloud-logging` (Python SDK) |
| Cloud Monitoring (Phase 5) | Custom metrics and alerting | `google-cloud-monitoring` (Python SDK) |
| Artifact Registry (Phase 5) | Docker image storage for CI/CD | `gcloud` CLI |
| Cloud Build (Phase 5) | CI/CD pipeline | `cloudbuild.yaml` |

### External Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| Neo4j AuraDB | Knowledge graph database (GCP-hosted) | `neo4j` Python driver |
| Tavily API (Phase 4) | Web search fallback when archive relevance < 0.7 | `tavily-python` SDK or REST API |

### Backend Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.6 | Web framework |
| `uvicorn[standard]` | 0.34.0 | ASGI server |
| `pydantic` | 2.10.4 | Data validation and schemas |
| `pydantic-settings` | 2.7.1 | Settings management with `.env` file support |
| `google-cloud-documentai` | 2.32.0 | Document AI OCR |
| `google-cloud-storage` | 2.19.0 | Cloud Storage operations |
| `google-cloud-aiplatform` | 1.74.0 | Vertex AI Vector Search |
| `vertexai` | 1.74.0 | Vertex AI Embeddings + Gemini |
| `python-multipart` | 0.0.20 | Form data parsing |
| `httpx` | 0.28.1 | Async HTTP client |
| `neo4j` | (Phase 2) | Neo4j Python driver |
| `tavily-python` | (Phase 4) | Tavily web search SDK |
| `google-cloud-pubsub` | (Phase 4) | Pub/Sub messaging |
| `google-cloud-logging` | (Phase 5) | Cloud Logging integration |

### Frontend npm Dependencies

| Package | Purpose |
|---------|---------|
| `react` (18.x) | UI framework |
| `react-dom` (18.x) | React DOM rendering |
| `typescript` | Type safety |
| `cytoscape` | Graph visualization library |
| `react-cytoscapejs` | React wrapper for Cytoscape.js |
| `tailwindcss` | Utility-first CSS framework |
| `pdfjs-dist` | PDF rendering in browser (pdf.js) |
| `axios` or `fetch` | HTTP client for API calls |
| `zustand` or React Context | State management |
| `vite` | Build tool and dev server |
| `@types/cytoscape` | TypeScript types for Cytoscape |

### Infrastructure

| Resource | Purpose |
|----------|---------|
| Docker | Containerization for Cloud Run deployment |
| nginx | Static file serving for React frontend container |
| GCP Service Account | Authentication for all GCP SDK calls |
| GCP IAM Roles | Document AI User, Storage Admin, Vertex AI User, Cloud Run Developer |

---

## 8. Timeline Estimates

### Phase 1: Backend Foundation + Vector-Only Query

| Task | Effort Estimate | Notes |
|------|----------------|-------|
| Task 1: Project Skeleton + Configuration | 1 day | Boilerplate, but extensive schemas |
| Task 2: Cloud Storage Service | 0.5 days | Straightforward SDK wrapper |
| Task 3: Document AI OCR Service | 2 days | Batch processing logic, concurrency, testing with real PDFs |
| Task 4: Text Cleaning + Chunking Service | 1.5 days | Sliding window, sentence boundary, language detection |
| Task 5: Vertex AI Embeddings Service | 1 day | Batch embedding, task type configuration |
| Task 6: Vertex AI Vector Search Service | 1.5 days | Upsert with metadata, category filtering, endpoint configuration |
| Task 7: Gemini LLM Service | 1 day | Prompt engineering, structured output |
| Task 8: Hybrid Retrieval Service | 1.5 days | Pipeline orchestration, chunk loading from GCS |
| Task 9: Ingestion Router | 1 day | Background task, job tracking, pipeline integration |
| Task 10: Query Router | 0.5 days | Thin wrapper over retrieval service |
| Task 11: Graph Router Placeholder | 0.5 days | Stub endpoints |
| Task 12: Docker Compose + Verification | 1 day | Docker config, Vertex AI init, end-to-end verification |
| **Phase 1 Total** | **~13 days (2.5 weeks)** | |

### Phase 2: Graph Layer

| Task | Effort Estimate | Notes |
|------|----------------|-------|
| Neo4j Connection Service | 1 day | Driver setup, connection pooling |
| Entity Extraction Service | 3 days | Gemini structured output, prompt iteration, testing |
| Entity Normalization Service | 3 days | Three-stage matching, threshold tuning, alias merging |
| Neo4j MERGE Pipeline | 2 days | Cypher queries, evidence metadata, idempotency |
| Hybrid Query Upgrade | 2 days | Parallel retrieval, score merging, Cypher traversals |
| Graph API Endpoints | 1.5 days | Subgraph retrieval, entity search |
| Integration Testing | 2 days | End-to-end validation |
| **Phase 2 Total** | **~14.5 days (3 weeks)** | Requires Neo4j AuraDB provisioned beforehand |

### Phase 3: Frontend

| Task | Effort Estimate | Notes |
|------|----------------|-------|
| React Project Setup | 1 day | Vite + TypeScript + TailwindCSS + Docker |
| App Layout Shell | 1 day | Global state, layout structure |
| ResizableSplitter | 1 day | Drag interaction, min-width constraints |
| ChatPanel | 2 days | Message rendering, input, loading/error states |
| useQuery Hook | 1 day | API integration, state management |
| GraphCanvas (Cytoscape.js) | 3 days | Node/edge rendering, layout, zoom/pan, styling |
| useGraphHighlight Hook | 1 day | Animation, camera fit |
| CitationBadge | 1 day | Inline badges, click handlers |
| NodeSidebar | 1.5 days | Entity details, evidence links, "Ask about" button |
| PDF Modal | 2 days | pdf.js integration, signed URLs, page navigation |
| Category Filter | 0.5 days | Multi-select dropdown |
| Frontend Docker + Cloud Run | 1 day | nginx config, env vars, deployment |
| **Phase 3 Total** | **~16 days (3 weeks)** | |

### Phase 4: Web Fallback + Polish

| Task | Effort Estimate | Notes |
|------|----------------|-------|
| Tavily Integration | 2 days | API integration, result formatting |
| Mixed Source Handling | 1 day | Backend logic update |
| Web Citation Badges | 0.5 days | Frontend update |
| Pub/Sub Async Ingestion | 3 days | Topic/subscription setup, refactor, job persistence |
| Auto-Classification | 1.5 days | Gemini classification, confidence flagging |
| Category Filter Polish | 1 day | UI improvements |
| **Phase 4 Total** | **~9 days (2 weeks)** | |

### Phase 5: Scale + Monitoring

| Task | Effort Estimate | Notes |
|------|----------------|-------|
| Cloud Logging | 1.5 days | Structured logging, log sink config |
| Cloud Monitoring + Alerting | 2 days | Custom metrics, dashboards, alert policies |
| OCR Confidence Flagging UI | 2 days | Admin page, review workflow |
| Batch Ingestion | 2 days | Multi-PDF queue, progress tracking, resume |
| Query Latency Optimization | 3 days | Profiling, caching, connection pooling, Cypher indexes |
| Mobile Responsive Layout | 2 days | CSS breakpoints, touch interactions |
| CI/CD Pipeline | 2 days | cloudbuild.yaml, Artifact Registry, auto-deploy |
| Vector Search Index Optimization | 1.5 days | Shard tuning, ANN parameter optimization |
| **Phase 5 Total** | **~16 days (3 weeks)** | |

### Overall Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Backend Foundation | 2.5 weeks | 2.5 weeks |
| Phase 2: Graph Layer | 3 weeks | 5.5 weeks |
| Phase 3: Frontend | 3 weeks | 8.5 weeks |
| Phase 4: Web Fallback + Polish | 2 weeks | 10.5 weeks |
| Phase 5: Scale + Monitoring | 3 weeks | 13.5 weeks |
| **Total Estimated Duration** | **~14 weeks** | Buffer included |

**Notes on Timeline**:
- Estimates assume a single developer working full-time.
- Buffer of ~0.5 weeks is included in the total for unexpected issues, GCP configuration delays, and API quota negotiations.
- Phase 2 has a hard dependency on Neo4j AuraDB provisioning — this should be initiated during Phase 1 to avoid delays.
- Phases are strictly sequential (Phase 1 -> 2 -> 3 -> 4 -> 5) due to dependencies.
- Full corpus ingestion (100+ PDFs) should be scheduled after Phase 2 completion, as it benefits from the complete pipeline (vector + graph). Test ingestion of 3-5 documents should occur during each phase for validation.

---

## Appendix A: Key Configuration Values

```python
# Thresholds (from settings.py)
RELEVANCE_THRESHOLD = 0.7      # Below this triggers Tavily fallback
OCR_CONFIDENCE_FLAG = 0.5      # Below this flags page for review
CHUNK_SIZE_TOKENS = 450        # Target chunk size (300-600 range)
CHUNK_OVERLAP_TOKENS = 100     # Sliding window overlap
GRAPH_HOP_DEPTH = 3            # Max hops for Cypher traversal
VECTOR_TOP_K = 10              # Number of nearest neighbors
SIGNED_URL_EXPIRY_MINUTES = 15 # Signed URL validity
```

## Appendix B: Document Category Taxonomy

```python
MAIN_CATEGORIES = [
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment",
]
```

All other fields (sub_category, entity attributes, relationship types) are AI-inferred by Gemini Flash during entity extraction. The five main categories above are predefined and immutable.

## Appendix C: API Endpoint Summary

| Method | Path | Phase | Purpose |
|--------|------|-------|---------|
| GET | `/health` | 1 | Health check |
| POST | `/ingest_pdf` | 1 | Ingest PDF from Cloud Storage |
| GET | `/ingest_status/{job_id}` | 1 | Poll ingestion progress |
| POST | `/query` | 1 | Ask question, get cited answer + graph |
| GET | `/document/signed_url` | 1 | Signed URL for PDF viewer |
| GET | `/graph/{canonical_id}` | 2 | Get subgraph around entity |
| GET | `/graph/search?q={query}` | 2 | Search entities by name |
