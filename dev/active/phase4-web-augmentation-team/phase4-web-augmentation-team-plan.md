# Phase 4: Web Augmentation — Multi-Agent Team Plan

**Last Updated: 2026-03-01**

---

## Executive Summary

Phase 4 adds three capabilities to the Colonial Archives Graph-RAG system:

1. **Tavily Web Search Fallback** — When archive retrieval relevance is low (< 0.7), supplement answers with web search results
2. **Auto-Classification** — Unmapped PDFs get classified by Gemini Flash into one of 5 categories, replacing manual `document_categories.json` lookups
3. **Source Type Indicators** — Frontend shows whether answers came from archives only, web only, or mixed sources

Phase 4.3 (Category Filter UI) was already built in Phase 3. Phase 4.4 (Pub/Sub Async Ingestion) is deferred to Phase 5 — current `BackgroundTasks` handles the ~20-doc corpus fine.

---

## Current State Analysis

| Component | Status | Notes |
|-----------|--------|-------|
| Backend (Phase 1+2) | Tested E2E | All 9 ingestion steps working, query returns GraphPayload |
| Frontend (Phase 3) | Code Complete | Chat, graph viz, PDF modal, citation badges all built |
| Frontend ↔ Backend | Tested | Vite proxy to :8090 works, queries return through UI |
| Category Filter UI (4.3) | Already Done | `CategoryFilter.tsx` + `filterCategories` in store |
| Citation Rendering (4.2) | Partially Done | `CitationBadge.tsx` handles both `archive` and `web` types |
| Web Fallback Placeholder | Exists | `hybrid_retrieval.py:125-131` has Phase 4 TODO comment |
| Settings Scaffolding | Ready | `TAVILY_API_KEY` and `PUBSUB_TOPIC` already in settings.py |
| WebCitation Schema | Ready | `schemas.py:48-52` already defines the model |

**Key insight**: Much of the scaffolding is already in place. The work is wiring real services into existing placeholders.

---

## Team Architecture

```
Team Lead (main session)
├── Phase A: Foundation — install deps, create test infra
├── Agent: web-search (worktree) — Tavily service + LLM update + hybrid retrieval
├── Agent: auto-classify (worktree) — classification service + ingestion integration
├── Agent: frontend (worktree) — source type indicator in ChatMessage
└── Phase C: Integration — merge agents, e2e verification
```

### Agent Assignments

| Agent | Scope | Files Created | Files Modified | Effort |
|-------|-------|---------------|----------------|--------|
| **web-search** | Tavily service, LLM mixed citations, hybrid retrieval integration | `services/web_search.py`, `tests/test_web_search.py`, `tests/test_llm_mixed.py` | `services/llm.py`, `services/hybrid_retrieval.py` | L |
| **auto-classify** | Classification service, ingestion fallback | `services/auto_classification.py`, `tests/test_auto_classification.py` | `routers/ingest.py`, `config/settings.py` | M |
| **frontend** | Source type badge in chat messages | — | `types/index.ts`, `stores/useAppStore.ts`, `components/ChatMessage.tsx` | S |

### Execution Timeline

```
Phase A: Foundation (Team Lead, ~5 min)
    │
    ├── Agent: web-search ──────────────── (~20 min)
    │   ├── B.ws.1: Tavily service
    │   ├── B.ws.2: LLM mixed citations
    │   └── B.ws.3: Hybrid retrieval integration
    │
    ├── Agent: auto-classify ───────────── (~15 min)
    │   ├── B.ac.1: Classification service
    │   └── B.ac.2: Ingestion integration
    │
    └── Agent: frontend ────────────────── (~10 min)
        └── B.fe.1: Source type indicator
    │
Phase C: Integration (Team Lead, ~10 min)
    ├── C.1: Merge agent output
    ├── C.2: Update .env.example
    └── C.3: End-to-end verification
```

**Estimated total: ~30-35 minutes** (Phase A 5 min → Phase B 20 min parallel → Phase C 10 min)

---

## Phase A: Foundation (Team Lead — Sequential)

### A.1: Install Phase 4 Dependencies [S]

**Files:** `backend/requirements.txt`

Add to `requirements.txt`:
```
tavily-python==0.5.0
pytest==8.3.4
pytest-asyncio==0.24.0
```

Run: `cd backend && pip install -r requirements.txt`

Verify: `python -c "from tavily import TavilyClient; print('OK')"`

### A.2: Create Test Infrastructure [S]

**Files:** Create `backend/tests/__init__.py` (empty file)

This enables `python -m pytest tests/` to discover test modules.

### A.3: Commit Foundation

```bash
git add backend/requirements.txt backend/tests/__init__.py
git commit -m "chore: add Phase 4 dependencies and test infrastructure"
```

---

## Phase B: Parallel Agent Streams

### Agent: web-search

Works in `backend/` only. Creates the Tavily web search service, updates LLM for mixed citation types, and wires the web fallback into hybrid retrieval.

#### B.ws.1: Create Tavily Web Search Service [M]

**Create:** `backend/app/services/web_search.py`
**Create:** `backend/tests/test_web_search.py`

Service wraps `TavilyClient` with lazy init (same pattern as all other services). Returns `list[dict]` where each dict has `{id, title, url, text, cite_type}`. Returns empty list on error (web search is best-effort fallback).

Key design:
- `search_depth="basic"` (speed over depth)
- `max_results=5` default
- `run_in_executor` for blocking API call
- `cite_type: "web"` on every result dict

Tests: 3 tests mocking TavilyClient (success, empty, error cases).

Commit: `feat: add Tavily web search service`

#### B.ws.2: Update LLM for Mixed Citation Types [M]

**Modify:** `backend/app/services/llm.py` (lines 70-80)
**Create:** `backend/tests/test_llm_mixed.py`

Current code assigns a single `cite_type` based on `source_type` param. For mixed responses, each chunk carries its own `cite_type`. Change the for-loop to read `chunk.get("cite_type", "archive")` and number `[archive:N]` and `[web:N]` independently.

Before:
```python
cite_type = "archive" if source_type == "archive" else "web"
for idx, chunk in enumerate(context_chunks, start=1):
    prefix = f"[{cite_type}:{cite_id}]"
```

After:
```python
archive_idx = 0
web_idx = 0
for chunk in context_chunks:
    cite_type = chunk.get("cite_type", "archive")
    if cite_type == "web":
        web_idx += 1
        prefix = f"[web:{web_idx}]"
    else:
        archive_idx += 1
        prefix = f"[archive:{archive_idx}]"
```

Commit: `feat: LLM service supports per-chunk citation types`

#### B.ws.3: Integrate Web Fallback into Hybrid Retrieval [L]

**Modify:** `backend/app/services/hybrid_retrieval.py`
- Add import: `from app.services.web_search import web_search_service`
- Add `WebCitation` to schemas import
- Replace Phase 4 placeholder (lines 125-133) with actual web search call
- Update citation building (lines 141-156) to emit both `ArchiveCitation` and `WebCitation`

Logic:
```python
if relevance_score < settings.RELEVANCE_THRESHOLD:
    web_context = await web_search_service.search(question)
    merged_context.extend(web_context)
    source_type = "mixed" if vector_results or graph_context else "web_fallback"
```

Commit: `feat: integrate Tavily web fallback into hybrid retrieval`

---

### Agent: auto-classify

Works in `backend/` only. Creates the Gemini-powered classification service and integrates it as a fallback in the ingestion pipeline's Step 3.

#### B.ac.1: Create Auto-Classification Service [M]

**Create:** `backend/app/services/auto_classification.py`
**Create:** `backend/tests/test_auto_classification.py`

Service uses Gemini Flash to classify document excerpts (first-page OCR text, truncated to 2000 chars) into one of the 5 `MAIN_CATEGORIES`. Returns `(category, confidence)` tuple. Falls back to "General and Establishment" with confidence 0.0 on error.

Key design:
- Lazy model init (same as `LlmService`)
- JSON output parsing with validation against `MAIN_CATEGORIES`
- `temperature=0.1`, `max_output_tokens=256`
- Invalid category → fallback to "General and Establishment"
- Parse error → fallback with confidence 0.3

Tests: 3 tests mocking GenerativeModel (valid category, invalid JSON, exception).

Commit: `feat: add auto-classification service for unmapped documents`

#### B.ac.2: Integrate into Ingestion Pipeline [M]

**Modify:** `backend/app/config/settings.py` — Add `CLASSIFICATION_CONFIDENCE_MIN: float = 0.8`
**Modify:** `backend/app/routers/ingest.py` — Import service, update Step 3

In `_run_ingestion()`, when `categories` is empty after the `document_categories.json` lookup:
1. Get first page OCR text
2. Call `auto_classification_service.classify(first_page_text)`
3. If confidence >= threshold: use the category
4. If confidence < threshold: use the category but log a warning for manual review
5. If no OCR text: log warning, proceed with empty categories

Commit: `feat: auto-classification fallback in ingestion pipeline`

---

### Agent: frontend

Works in `frontend/src/` only. Adds source type indicator to assistant chat messages.

#### B.fe.1: Add Source Type Indicator [S]

**Modify:** `frontend/src/types/index.ts` — Add `source_type?` to `ChatMessage` interface
**Modify:** `frontend/src/stores/useAppStore.ts` — Pass `source_type` from response to `ChatMessage`
**Modify:** `frontend/src/components/ChatMessage.tsx` — Render source label below assistant messages

Source label logic:
- `source_type === "mixed"` → "Sources: Archive + Web"
- `source_type === "web_fallback"` → "Sources: Web sources"
- `source_type === "archive"` or undefined → no label (archive is the default)

Styled as: `text-xs text-gray-500` below the message, with a `border-t border-gray-700` separator.

Verify: `npx tsc --noEmit` passes with no errors.

Commit: `feat: source type indicator in chat messages`

---

## Phase C: Integration (Team Lead — Sequential)

### C.1: Merge Agent Output [M]

Merge all three agent worktree branches into the working branch. Order doesn't matter — the agents touch different files.

Expected merge conflicts: **None** (agents modify different files).

Verify after merge:
```bash
cd backend && python -c "from app.services.hybrid_retrieval import hybrid_retrieval_service; print('OK')"
cd frontend && npx tsc --noEmit
```

### C.2: Update .env.example [S]

Add Phase 4 variables to `backend/.env.example`:
```bash
# Phase 4: Tavily Web Search
TAVILY_API_KEY=tvly-your-api-key-here
# Phase 4: Auto-classification threshold
CLASSIFICATION_CONFIDENCE_MIN=0.8
```

Remind user to add actual `TAVILY_API_KEY` to `backend/.env` (get from https://tavily.com, free tier: 1000 searches/month).

### C.3: Run All Backend Tests [S]

```bash
cd backend && python -m pytest tests/ -v
```

Expected: 9 tests pass (3 web search + 1 LLM mixed + 3 auto-classification + 2 integration).

### C.4: End-to-End Manual Verification [M]

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8090`
2. Test high-relevance query (no web fallback): `POST /query {"question": "What is Vibrona wine?"}`
   - Expected: `source_type: "archive"`, no web citations
3. Test low-relevance query (web fallback triggers): `POST /query {"question": "What was the population of Singapore in 1920?"}`
   - Expected: `source_type: "mixed"` or `"web_fallback"`, WebCitation objects in response
4. Start frontend: `cd frontend && npm run dev`
5. Verify source type label appears in chat bubbles for mixed/web responses

Commit: `docs: update .env.example with Phase 4 variables`

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Tavily API key not set | Web fallback silently fails | Medium | Service returns empty list on error; logged as warning |
| Tavily rate limit (free: 1000/mo) | Web fallback stops working | Low | `search_depth="basic"` minimizes tokens; only triggers when relevance < 0.7 |
| LLM citation numbering mismatch | Frontend renders wrong citations | Medium | Per-chunk `cite_type` ensures consistent numbering between LLM prompt and citation list |
| Auto-classification hallucination | Wrong category assigned | Low | Confidence threshold (0.8) + validation against `MAIN_CATEGORIES` + fallback to General |
| Merge conflicts between agents | Integration blocked | Very Low | Agents touch entirely different files |
| Neo4j AuraDB paused (3-day inactivity) | Graph search fails | Medium | Auto-resumes on connection; graph failures are already non-blocking |

---

## Success Metrics

1. **Web fallback triggers** when `combined_relevance < 0.7` and returns `source_type: "mixed"`
2. **Citation types are correct**: archive chunks get `[archive:N]`, web chunks get `[web:N]`
3. **Frontend shows source indicator** for mixed/web responses
4. **Auto-classification assigns valid category** from `MAIN_CATEGORIES` for unmapped PDFs
5. **All 9+ backend tests pass** (`python -m pytest tests/ -v`)
6. **Frontend TypeScript compiles** with no errors (`npx tsc --noEmit`)
7. **Existing functionality unbroken**: archive-only queries still work identically to Phase 2

---

## Required Resources

| Resource | Purpose | Status |
|----------|---------|--------|
| Tavily API Key | Web search fallback | User must sign up at https://tavily.com |
| Gemini 2.0 Flash (us-central1) | Auto-classification | Already provisioned |
| Python 3.11+ | Backend runtime | Installed |
| Node.js 18+ | Frontend build | Installed |
| Neo4j AuraDB | Graph queries | Already provisioned (may need resume) |
| GCP credentials | All cloud services | Already configured in `.env` |
