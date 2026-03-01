# Phase 4: Web Augmentation — Team Context

**Last Updated: 2026-03-01**

This is the reference document for all agents working on Phase 4. Read this BEFORE starting any task.

---

## Key Files Reference

| File | Purpose | Who Can Modify |
|------|---------|----------------|
| `docs/plans/2026-03-01-phase4-web-augmentation.md` | Detailed implementation plan with complete code | Read-only reference |
| `backend/app/config/settings.py` | All configuration settings | auto-classify agent |
| `backend/app/config/document_categories.json` | PDF → category manual mappings | Nobody (read-only) |
| `backend/app/models/schemas.py` | Pydantic models | Nobody (already complete) |
| `backend/app/services/llm.py` | Gemini LLM answer generation | web-search agent |
| `backend/app/services/hybrid_retrieval.py` | Query orchestration pipeline | web-search agent |
| `backend/app/routers/ingest.py` | PDF ingestion endpoint | auto-classify agent |
| `frontend/src/types/index.ts` | TypeScript interfaces | frontend agent |
| `frontend/src/stores/useAppStore.ts` | Zustand state store | frontend agent |
| `frontend/src/components/ChatMessage.tsx` | Chat message rendering | frontend agent |

---

## Agent Rules

### CRITICAL — What Agents CAN Do

- Create new files within their assigned scope
- Modify files explicitly listed in their task descriptions
- Import from existing modules (read-only)
- Run tests for their own code
- Read any file for reference

### CRITICAL — What Agents MUST NOT Do

- **web-search**: Do NOT modify `schemas.py`, `ingest.py`, `settings.py`, or any frontend files
- **auto-classify**: Do NOT modify `llm.py`, `hybrid_retrieval.py`, `schemas.py`, or any frontend files
- **frontend**: Do NOT modify any backend files, `App.tsx`, or `index.css`
- **All agents**: Do NOT modify `main.py`, `schemas.py`, `document_categories.json`

### What Each Agent Receives

- **web-search**: Tasks B.ws.1, B.ws.2, B.ws.3 — "Create Tavily service, update LLM citations, wire into hybrid retrieval"
- **auto-classify**: Tasks B.ac.1, B.ac.2 — "Create classification service, integrate into ingestion step 3"
- **frontend**: Task B.fe.1 — "Add source_type to ChatMessage type and render source label"

---

## Dependencies Between Tasks

```
A.1 (deps install) ─┬─→ B.ws.1 (Tavily service) → B.ws.2 (LLM update) → B.ws.3 (retrieval)
                     │
A.2 (test infra)  ──┤─→ B.ac.1 (classify service) → B.ac.2 (ingest integration)
                     │
                     └─→ B.fe.1 (frontend indicator) — no backend dependency
```

**Phase B agents are fully independent** — they modify different files. No merge conflicts expected.

---

## Backend Architecture (Read-Only Reference)

### Settings Already in Place (`config/settings.py`)

```python
TAVILY_API_KEY: str = "PLACEHOLDER_TAVILY_API_KEY"   # line 36
PUBSUB_TOPIC: str = "PLACEHOLDER_PUBSUB_TOPIC"       # line 33 (Phase 5)
RELEVANCE_THRESHOLD: float = 0.7                       # line 39
```

### Schemas Already in Place (`models/schemas.py`)

```python
class WebCitation(BaseModel):          # line 48
    type: str = "web"
    id: int
    title: str
    url: str

class QueryResponse(BaseModel):       # line 99
    answer: str
    source_type: str  # "archive" | "web_fallback" | "mixed"
    citations: list[ArchiveCitation | WebCitation]
    graph: GraphPayload | None = None

MAIN_CATEGORIES = [                    # line 4
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment",
]
```

### Hybrid Retrieval — Phase 4 Placeholder (`services/hybrid_retrieval.py:125-133`)

```python
# Web fallback placeholder (Phase 4)
if relevance_score < settings.RELEVANCE_THRESHOLD:
    logger.warning(
        "Relevance %.4f below threshold %.2f — web fallback not yet implemented",
        relevance_score,
        settings.RELEVANCE_THRESHOLD,
    )

source_type = "archive"
```

This block gets replaced by the web-search agent with actual Tavily integration.

### LLM Service — Citation Logic (`services/llm.py:70-80`)

```python
cite_type = "archive" if source_type == "archive" else "web"

context_parts: list[str] = []
citation_refs: list[str] = []

for idx, chunk in enumerate(context_chunks, start=1):
    cite_id = chunk.get("id", idx)
    prefix = f"[{cite_type}:{cite_id}]"
    context_parts.append(f"{prefix} {chunk.get('text', '')}")
    citation_refs.append(f"{prefix} chunk {cite_id}")
```

This block gets replaced by the web-search agent with per-chunk `cite_type` handling.

### Ingestion Pipeline — Step 3 (`routers/ingest.py:125-142`)

```python
categories_map = _load_document_categories()
blob_name = storage_service._parse_blob_name(pdf_url)
pdf_filename = PurePosixPath(blob_name).name
categories: list[str] = categories_map.get(
    pdf_filename, categories_map.get(doc_id, [])
)
if not categories:
    logger.warning(
        "[%s] No categories found for pdf_filename=%s or doc_id=%s",
        job_id, pdf_filename, doc_id,
    )
```

The auto-classify agent replaces the `if not categories:` block with an auto-classification fallback.

### Context Chunk Dict Shape

All services pass context chunks as `list[dict]`. Each dict MUST have:

```python
{
    "id": str,           # chunk_id or "web_1", "web_2", etc.
    "text": str,         # chunk text or web article content
    "doc_id": str,       # document ID (empty for web)
    "pages": list[int],  # page numbers (empty for web)
    "confidence": float, # vector distance or 0.0 for web
    "cite_type": str,    # "archive" or "web"  ← KEY FIELD for Phase 4
}
```

Web results from Tavily additionally carry:
```python
{
    "title": str,  # page title
    "url": str,    # source URL
}
```

---

## Frontend Architecture (Read-Only Reference)

### Current ChatMessage Type (`types/index.ts`)

```typescript
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  graph?: GraphPayload | null;
  // source_type NOT YET PRESENT — frontend agent adds this
}
```

### Current Store Action (`stores/useAppStore.ts:66-71`)

```typescript
const assistantMsg: ChatMessage = {
  role: "assistant",
  content: response.answer,
  citations: response.citations,
  graph: response.graph,
  // source_type NOT YET PASSED — frontend agent adds this
};
```

### Current CitationBadge (`components/CitationBadge.tsx`)

Already handles both archive (blue) and web (green/emerald) citations:
- Archive: `<button>` with `bg-blue-500/20 text-blue-400`, clicks open PDF modal
- Web: `<a>` with `bg-emerald-500/20 text-emerald-400`, opens URL in new tab

**No changes needed** to CitationBadge — it already works for both types.

---

## Service Singleton Pattern

All backend services follow the same pattern. New services MUST match:

```python
class MyService:
    def __init__(self) -> None:
        self._client = None  # or self._model = None

    @property
    def client(self):  # or model
        if self._client is None:
            # Lazy initialization here
            self._client = SomeClient(...)
            logger.info("MyService initialised")
        return self._client

    async def do_something(self, ...) -> ...:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self.client.method(...))
        return result

# Module-level singleton
my_service = MyService()
```

Key: `run_in_executor` wraps all blocking SDK calls. No `await` on sync clients.

---

## Environment / Runtime Notes

- **Python**: 3.13 at `C:\Users\yjkim\AppData\Local\Programs\Python\Python313` (bash may use 3.14 — use full path if needed)
- **Backend start**: `cd backend && uvicorn app.main:app --reload --port 8090`
- **Frontend start**: `cd frontend && npm run dev` (port 5173, proxies `/api` → `:8090`)
- **Tests**: `cd backend && python -m pytest tests/ -v`
- **TypeScript check**: `cd frontend && npx tsc --noEmit`
- **Port 8080 may be stuck** — always use 8090

---

## GCP Infrastructure (Read-Only)

| Service | Region | ID / Endpoint |
|---------|--------|---------------|
| Cloud Storage | asia-southeast1 | Bucket: `aihistory-co273-nus` |
| Document AI OCR | asia-southeast1 | Processor: `1a36b779b245dae0` |
| Vector Search | asia-southeast1 | Endpoint: `1005598664.asia-southeast1-58449340870.vdb.vertexai.goog` |
| Gemini LLM | us-central1 | Model: `gemini-2.0-flash` |
| Neo4j AuraDB | — | URI: `neo4j+s://ae76ab7c.databases.neo4j.io` |
