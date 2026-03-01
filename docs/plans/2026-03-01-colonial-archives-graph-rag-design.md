# Colonial Archives Graph-RAG System — Design Document

**Date**: 2026-03-01
**Status**: Approved

---

## 1. Project Goal

Build a chatbot + interactive knowledge graph UI that answers questions about colonial-era handwritten archive documents (English/Chinese PDFs) with source-grounded responses only.

**Strict rule**: Every answer, every graph node, every relationship must trace back to a specific document page + text snippet. No hallucinations. No inferred facts. If information is not present in source documents, the system must say so.

**Primary users**: Academic researchers who need rigorous citations and evidence traceability.

---

## 2. Constraints & Decisions

| Decision | Choice |
|---|---|
| Scale | 100+ PDFs, 300-500 pages each (~30k-50k pages) |
| Languages | Mostly English, some Chinese |
| Users | Academic researchers |
| PDF citations | Full in-browser PDF viewer (pdf.js) via signed Cloud Storage URLs |
| Ingestion | Sync REST in Phase 1, Pub/Sub in Phase 4 |
| GCP | Already set up, documents in Cloud Storage |
| Neo4j | Will provision AuraDB before Phase 2 |
| Deployment | Cloud Run for both backend and frontend |
| Auth | Open access, no login |
| SDKs | Official Google Cloud Python SDKs (no LangChain) |
| Chunking | Page-level OCR + sliding window (300-600 tokens, 100 overlap, may span 2 adjacent pages) |

---

## 3. Tech Stack

- **Storage**: Cloud Storage (raw PDFs, OCR output, chunks)
- **OCR**: Document AI (multilingual handwritten processor)
- **Embeddings**: Vertex AI text-embedding-004 (multilingual)
- **Vector DB**: Vertex AI Vector Search
- **Graph DB**: Neo4j AuraDB (GCP-hosted)
- **Backend**: FastAPI on Cloud Run
- **LLM**: Vertex AI Gemini 1.5 Flash (structured output mode)
- **Messaging**: Pub/Sub (async ingestion, Phase 4)
- **Web Search**: Tavily API (fallback only)
- **Frontend**: React 18 + TypeScript + Cytoscape.js + TailwindCSS
- **PDF Viewer**: pdf.js

---

## 4. Architecture

```
                         CLOUD RUN
  ┌──────────────────────┐    ┌──────────────────────────┐
  │ React Frontend       │    │ FastAPI Backend           │
  │ (nginx container)    │───>│ /ingest_pdf              │
  │ Cytoscape.js         │    │ /query                   │
  │ pdf.js viewer        │    │ /graph/*                 │
  └──────────────────────┘    │ /document/signed_url     │
                              └──────────┬───────────────┘
                                         │
              ┌──────────────────────────┼──────────────────┐
              │                          │                  │
              v                          v                  v
     Cloud Storage            Vertex AI             Neo4j AuraDB
     - Raw PDFs               - Document AI OCR     - Entities
     - OCR output             - Embeddings          - Relationships
     - Chunks JSON            - Vector Search       - Evidence
                              - Gemini Flash
                                         │
                                         v (fallback)
                              Tavily Web Search
```

- Two Cloud Run services: React (nginx) + FastAPI
- Backend makes direct SDK calls to all GCP services
- Cloud Storage serves original PDFs via signed URLs for the pdf.js viewer
- Tavily triggered only when relevance score < 0.7

---

## 5. Ingestion Pipeline

```
PDF in Cloud Storage
  │
  v
POST /ingest_pdf { "pdf_url": "gs://bucket/file.pdf" }
  │
  v
1. DOWNLOAD & OCR
   - Document AI OCR per page (batched, parallelized)
   - Store raw OCR JSON to gs://bucket/ocr/
   - Flag pages with confidence < 0.5
  │
  v
2. TEXT CLEANING & CHUNKING
   - Normalize whitespace, remove headers/footers
   - Concatenate pages with [PAGE:N] markers
   - Sliding window: 300-600 tokens, 100 overlap
   - Chunks may span 2 adjacent pages
   - Each chunk: { chunk_id, doc_id, pages[], language_tag, categories[] }
   - Store chunks JSON to gs://bucket/chunks/
  │
  v
3. EMBEDDING & VECTOR UPSERT
   - Vertex AI text-embedding-004 (batch embed)
   - Upsert to Vertex AI Vector Search with metadata
  │
  v
4. ENTITY EXTRACTION (Phase 2)
   - Gemini Flash structured JSON per chunk
   - Returns: entities[] + relationships[] with evidence
  │
  v
5. ENTITY NORMALIZATION (Phase 2)
   - Compare new entities vs existing Neo4j nodes
   - Embedding similarity + fuzzy string match
   - Merge aliases (e.g. "J. Anderson" → "John Anderson")
  │
  v
6. NEO4J MERGE (Phase 2)
   - MERGE nodes + relationships with evidence metadata
   - Never CREATE, always MERGE to prevent duplicates
  │
  v
Return: { status, chunks_processed, pages_total,
          ocr_confidence_warnings[], entities_extracted }
```

**Document AI batching**: Up to 15 pages per sync request. A 400-page PDF = ~27 batch requests, parallelized with asyncio.gather and concurrency limits.

**Category assignment**: Looks up doc_id in document_categories.json. If not found, Gemini auto-classifies and flags confidence < 0.8 for manual review.

**Idempotency**: Re-ingesting the same PDF overwrites chunks/vectors (keyed by doc_id + chunk_id). Neo4j MERGE prevents duplicate entities.

---

## 6. Query Pipeline

```
POST /query { "question": "...", "filter_categories": [...] | null }
  │
  v
1. QUERY ANALYSIS
   - Embed question via text-embedding-004
   - Extract entity hints (keyword extraction, no LLM call)
  │
  v
2. PARALLEL RETRIEVAL
   2a. Vector Search: top-10 chunks by cosine similarity
       Filter by categories if provided
   2b. Graph Traversal (Phase 2): 1-3 hop Cypher from seed entities
       Filter by categories, order by confidence, limit 50
  │
  v
3. MERGE & SCORE
   - Combine vector chunks + graph evidence
   - Deduplicate overlapping text spans
   - Relevance score:
     Phase 1: avg(vector_similarity)
     Phase 2: avg(vector_similarity) * 0.6 + graph_hit_ratio * 0.4
  │
  v
4. WEB FALLBACK (if relevance < 0.7)
   - Tavily.search(question, search_depth="basic")
   - Append as separate source_type: "web"
  │
  v
5. LLM GENERATION
   - Gemini 1.5 Flash structured output
   - Strict grounding: cite every fact [archive:N] or [web:N]
   - Insufficient context → "I cannot answer this based on the available sources."
  │
  v
6. RESPONSE
   { answer, source_type, citations[], graph{} }
```

**Latency target**: <2s p95. Vector search ~100ms, Gemini generation ~1-1.5s. Vector + graph run in parallel.

---

## 7. Frontend

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  GRAPH CANVAS (60-70%)    │ SPLITTER │  CHAT PANEL (30-40%)  │
│  Cytoscape.js             │ ◀──────▶ │  Message history      │
│                           │          │  Input box (bottom)   │
│  Highlighted: orange      │          │  Citation badges      │
│  border + pulse animation │          │  [archive:N] [web:N]  │
│  Click node → sidebar     │          │                       │
└──────────────────────────────────────────────────────────────┘
```

### Components

| Component | Responsibility |
|---|---|
| App.tsx | Layout shell, global state |
| GraphCanvas.tsx | Cytoscape.js rendering, highlight animation |
| ChatPanel.tsx | Messages, input, loading state |
| ResizableSplitter.tsx | Draggable divider (min 30% each side) |
| CitationBadge.tsx | [archive:N] → PDF modal, [web:N] → new tab |
| NodeSidebar.tsx | Entity details, attributes, evidence, "Ask about this" button |
| useGraphHighlight.ts | Clear/apply highlights, camera animation |
| useQuery.ts | POST /query, loading/error state |

### PDF Modal

Triggered by clicking [archive:N] badges in chat OR source evidence links in NodeSidebar.

1. Frontend calls GET /document/signed_url?doc_id=X&page=N
2. Backend returns time-limited signed URL (15 min)
3. pdf.js renders PDF, jumps to cited page
4. Zoomable, scrollable, page navigation

### Interaction Flow

1. User types question → useQuery calls POST /query
2. Response: { answer, citations, graph }
3. ChatPanel renders answer with CitationBadge components
4. useGraphHighlight highlights relevant nodes/edges, animates camera fit (800ms)
5. Click node → NodeSidebar slides in
6. Click [archive:N] → PDF modal opens at cited page
7. "Ask about this entity" → pre-fills chat input

---

## 8. Data Models

### Neo4j Node Schema

```
(Entity {
  canonical_id: string,
  name: string,
  main_categories: string[],     // from MAIN_CATEGORIES only
  sub_category: string | null,   // AI-inferred
  aliases: string[],
  attributes: map,               // AI-inferred key-value pairs
  evidence: {
    doc_id: string,
    page: int,
    text_span: string,
    chunk_id: string,
    confidence: float
  }
})
```

### Neo4j Relationship Schema

```
(a)-[:RELATIONSHIP_TYPE {
  type: string,                  // AI-inferred verb
  attributes: map,               // AI-inferred details
  evidence: { doc_id, page, text_span, chunk_id, confidence }
}]->(b)
```

### Document Categories (predefined, immutable)

```python
MAIN_CATEGORIES = [
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment"
]
```

All other fields (sub_category, attributes, relationship types) are AI-inferred.

### API Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /ingest_pdf | Ingest PDF from Cloud Storage |
| GET | /ingest_status/{job_id} | Poll ingestion progress |
| POST | /query | Ask question, get cited answer + graph |
| GET | /graph/{canonical_id} | Get subgraph around entity |
| GET | /graph/search?q={query} | Search entities by name |
| GET | /document/signed_url | Signed URL for PDF viewer |

---

## 9. Build Phases

### Phase 1: Backend Foundation + Vector-Only Query

- FastAPI skeleton + Docker + Cloud Run config
- POST /ingest_pdf (sync): Cloud Storage → Document AI → chunk → embed → Vector Search
- POST /query: vector-only retrieval → Gemini answer with citations
- GET /document/signed_url
- All Pydantic schemas, settings with PLACEHOLDER values

### Phase 2: Graph Layer

- LLM entity extraction (Gemini structured JSON)
- Entity normalization (embedding similarity + fuzzy match)
- Neo4j MERGE pipeline
- Hybrid /query (vector + Cypher in parallel)
- GET /graph/* endpoints

### Phase 3: Frontend

- React 18 + TypeScript + TailwindCSS
- GraphCanvas (Cytoscape.js) + ChatPanel + ResizableSplitter
- CitationBadge + NodeSidebar
- PDF modal (pdf.js + signed URLs)
- Live graph highlight on every query

### Phase 4: Web Fallback + Polish

- Tavily integration (relevance < 0.7 triggers fallback)
- Web citation badges
- Category filter dropdown
- Pub/Sub async ingestion
- Auto-classification for unmapped documents

### Phase 5: Scale + Monitoring

- Cloud Logging + Cloud Monitoring
- OCR confidence flagging UI
- Batch ingestion
- Query latency optimization (<2s p95)
- Mobile responsive layout
- cloudbuild.yaml CI/CD

### Phase Dependencies

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
                │
                └── requires Neo4j AuraDB provisioned
```

---

## 10. Operational Notes

- **Admin ingests documents before launch**. Users only access the app after indexing is complete.
- **New documents can be added post-launch** via /ingest_pdf. Existing queries unaffected until ingestion completes.
- **All secrets use PLACEHOLDER values** until user provides real credentials.
- **No LangChain** — all GCP SDK calls are direct.
- **document_categories.json** provided by user before ingestion.
