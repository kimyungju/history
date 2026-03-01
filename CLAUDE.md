# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Colonial Archives Graph-RAG: an AI-powered research tool for querying colonial-era handwritten archive documents (English + Chinese) via a chatbot backed by a knowledge graph. Every answer must trace back to specific document pages — zero tolerance for hallucination.

**Current state**: Phase 1 (backend foundation), Phase 2 (graph layer), and Phase 3 (React frontend) code complete. Backend **tested end-to-end with real data** — full 9-step ingestion pipeline works (OCR → chunk → embed → vector upsert → entity extraction → normalization → Neo4j MERGE). Query endpoint works (vector search + graph traversal + Gemini answer generation). Frontend not yet tested with live backend. Phases 4–5 (web augmentation, production hardening) planned but not yet implemented.

## Commands

```bash
# Run backend locally (use port 8090 if 8080 is stuck)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8090
# Swagger docs at http://localhost:8090/docs

# Run via Docker Compose
cd infra && docker-compose up --build
# Requires GCP credentials — see backend/.env.example

# gcloud auth (run in PowerShell, not bash)
gcloud auth application-default login
gcloud config set project aihistory-488807

# No test suite yet — testing is planned for Phase 5
```

## Architecture

**Stack**: FastAPI (Python 3.11) + Google Cloud services (Document AI, Vertex AI, Cloud Storage, Vector Search) + Neo4j AuraDB. No LangChain/LlamaIndex — direct SDK calls for traceability and control.

### Backend Layout (`backend/app/`)

- `main.py` — FastAPI app, CORS, Vertex AI init + Neo4j init/close in lifespan, router registration, health check with Neo4j status
- `config/settings.py` — Pydantic Settings reading from `.env`. Values with `PLACEHOLDER_*` defaults must be replaced. Tunable thresholds have working defaults.
- `config/document_categories.json` — Maps PDF filenames → 5 predefined archive categories
- `models/schemas.py` — All Pydantic v2 models (requests, responses, internal types like `Chunk`, `Evidence`, `EntityExtractionResult`, `GraphNode/Edge/Payload`)
- `routers/` — Thin HTTP layer: `ingest.py` (PDF ingestion + entity extraction + Neo4j), `query.py` (Q&A + signed URLs), `graph.py` (entity search + subgraph retrieval)
- `services/` — Business logic, one service per concern:
  - `storage.py` — Cloud Storage read/write/signed URLs
  - `ocr.py` — Document AI OCR with page batching (15/batch) and semaphore concurrency (5)
  - `chunking.py` — Text cleaning + sliding window (450 tokens, 100 overlap), page-span tracking, CJK language detection
  - `embeddings.py` — Vertex AI text-embedding-004, batch size 250
  - `vector_search.py` — Vertex AI Vector Search upsert (batch 100) and nearest-neighbor search
  - `llm.py` — Gemini 2.0 Flash with grounded citation prompt, temperature 0.1
  - `entity_extraction.py` — Gemini structured JSON output for entities + relationships per chunk
  - `entity_normalization.py` — Three-stage dedup (exact match, embedding similarity, fuzzy string via rapidfuzz)
  - `neo4j_service.py` — Async Neo4j driver, MERGE entities/relationships, subgraph traversal, entity search
  - `hybrid_retrieval.py` — Orchestrates parallel vector search + graph traversal, combined scoring, GraphPayload in response

### Data Flow

**Ingestion** (9 steps): PDF (GCS) → Document AI OCR → clean+chunk → embed → vector upsert → entity extraction (Gemini) → entity normalization → Neo4j MERGE. Steps 7-9 (graph) are non-blocking — vector ingestion succeeds even if graph fails.

**Query**: Question → embed + extract entity hints → parallel (vector search + graph traversal) → merge + score (vector*0.6 + graph*0.4) → Gemini generates grounded answer with `[archive:N]` citations → response includes GraphPayload.

### Key Design Decisions

- **Module-level singletons** for all services (imported directly, no DI framework)
- **Async throughout** with `asyncio.gather` for parallel I/O and `run_in_executor` for blocking SDK calls
- **MERGE not CREATE** in Neo4j for idempotent re-ingestion
- **No auth** — data is publicly digitized archives; researchers need friction-free access
- **Category filtering** via Vector Search namespace restricts, not separate indexes
- **Relationships stored as `RELATED_TO`** with `rel_type` property (Neo4j doesn't support parameterized relationship types without APOC)
- **Entity normalization thresholds**: `ENTITY_SIMILARITY_THRESHOLD=0.85` for auto-merge, `ENTITY_CONFIDENCE_MIN=0.5` to discard low-confidence extractions
- **Entity hint extraction** from queries uses regex (capitalized words/phrases), not LLM, to keep latency low
- **Dual-region architecture**: asia-southeast1 for storage/OCR/embeddings/vector search; us-central1 for Gemini LLM (not available in SEA). `VERTEX_LLM_REGION` setting controls LLM region.
- **Lazy initialization** for all GCP service clients (deferred to first use, not import time) — required because `vertexai.init()` runs in FastAPI lifespan, after imports

## Planning Documents

- `dev/active/colonial-archives-graph-rag/` — Context doc (architecture reference), plan, and task breakdown (5 phases, 39 tasks total)
- `docs/plans/` — Design document and Phase 1 implementation plan

## API Endpoints

| Method | Path | Status |
|--------|------|--------|
| POST | `/ingest_pdf` | Phase 1+2 ✓ (includes entity extraction) |
| GET | `/ingest_status/{job_id}` | Phase 1 ✓ |
| POST | `/query` | Phase 2 ✓ (parallel vector+graph) |
| GET | `/document/signed_url` | Phase 1 ✓ |
| GET | `/graph/search?q=&limit=&categories=` | Phase 2 ✓ |
| GET | `/graph/{canonical_id}?categories=` | Phase 2 ✓ |
| GET | `/health` | Phase 2 ✓ (includes Neo4j status) |

## Environment Setup

Copy `backend/.env.example` to `backend/.env` and fill in all `PLACEHOLDER_*` values. Required services: GCP (Document AI, Vertex AI Vector Search, Cloud Storage) + Neo4j AuraDB (free tier sufficient). Docker Compose mounts GCP credentials automatically.

## Neo4j AuraDB

- **URI**: configured in `.env` as `NEO4J_URI` (format: `neo4j+s://xxxxx.databases.neo4j.io`)
- **Free tier**: 200k nodes, 400k relationships — sufficient for ~100 docs
- **Pauses after 3 days of inactivity** — auto-resumes on connection
- **Node label**: `:Entity` with properties `canonical_id`, `name`, `main_categories`, `sub_category`, `aliases`, `attributes` (JSON string), `evidence_*` fields
- **Relationship label**: `:RELATED_TO` with `rel_type` property storing the semantic type (e.g. "ADMINISTERED")
