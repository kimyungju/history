# Phase 4: Web Augmentation — Task Tracker

**Last Updated: 2026-03-01**

**Status Legend**: S (< 5 min) | M (5-15 min) | L (15-30 min)

---

## Phase A: Foundation (Team Lead) — Sequential

### A.1: Install Phase 4 Dependencies [S] — Owner: lead

- [ ] Add `tavily-python==0.5.0` to `backend/requirements.txt`
- [ ] Add `pytest==8.3.4` to `backend/requirements.txt`
- [ ] Add `pytest-asyncio==0.24.0` to `backend/requirements.txt`
- [ ] Run `cd backend && pip install -r requirements.txt`
- [ ] Verify: `python -c "from tavily import TavilyClient; print('OK')"`

### A.2: Create Test Infrastructure [S] — Owner: lead

- [ ] Create `backend/tests/__init__.py` (empty file)
- [ ] Verify: `cd backend && python -m pytest tests/ -v` (should report "no tests ran" or 0 collected)

### A.3: Commit Foundation [S] — Owner: lead

- [ ] `git add backend/requirements.txt backend/tests/__init__.py`
- [ ] `git commit -m "chore: add Phase 4 dependencies and test infrastructure"`

---

## Phase B: Parallel Agent Streams

### Agent: web-search

#### B.ws.1: Create Tavily Web Search Service [M] — Owner: web-search

- [ ] Create `backend/app/services/web_search.py`
  - [ ] `WebSearchService` class with lazy `TavilyClient` init
  - [ ] `async search(query, max_results=5)` method
  - [ ] Returns `list[dict]` with keys: id, title, url, text, cite_type
  - [ ] `run_in_executor` for blocking Tavily API call
  - [ ] Returns empty list on exception (best-effort fallback)
  - [ ] Module-level singleton: `web_search_service = WebSearchService()`
- [ ] Create `backend/tests/test_web_search.py`
  - [ ] Test: success returns formatted results with correct keys
  - [ ] Test: empty results returns empty list
  - [ ] Test: API error returns empty list
- [ ] Run: `python -m pytest tests/test_web_search.py -v` → 3 passed
- [ ] Commit: `feat: add Tavily web search service`

#### B.ws.2: Update LLM for Mixed Citation Types [M] — Owner: web-search

- [ ] Modify `backend/app/services/llm.py` (lines 70-80)
  - [ ] Remove single `cite_type = "archive" if source_type == "archive" else "web"`
  - [ ] Add `archive_idx = 0`, `web_idx = 0` counters
  - [ ] Read `cite_type` from `chunk.get("cite_type", "archive")`
  - [ ] Number `[archive:N]` and `[web:N]` independently
- [ ] Create `backend/tests/test_llm_mixed.py`
  - [ ] Test: mixed context produces correct citation prefixes
- [ ] Run: `python -m pytest tests/test_llm_mixed.py -v` → 1 passed
- [ ] Commit: `feat: LLM service supports per-chunk citation types`

#### B.ws.3: Integrate Web Fallback into Hybrid Retrieval [L] — Owner: web-search

- [ ] Modify `backend/app/services/hybrid_retrieval.py`
  - [ ] Add import: `from app.services.web_search import web_search_service`
  - [ ] Add `WebCitation` to schemas import
  - [ ] Replace Phase 4 placeholder (lines 125-133) with:
    - [ ] `web_context: list[dict] = []`
    - [ ] If `relevance_score < RELEVANCE_THRESHOLD`: call `web_search_service.search(question)`
    - [ ] Extend `merged_context` with web results
    - [ ] Set `source_type` to `"mixed"` or `"web_fallback"`
  - [ ] Update citation building (lines 141-156):
    - [ ] Iterate merged_context with per-chunk `cite_type` check
    - [ ] Build `ArchiveCitation` for archive chunks
    - [ ] Build `WebCitation` for web chunks
    - [ ] Number archive and web citations independently
- [ ] Verify: `python -c "from app.services.hybrid_retrieval import hybrid_retrieval_service; print('OK')"`
- [ ] Commit: `feat: integrate Tavily web fallback into hybrid retrieval`

---

### Agent: auto-classify

#### B.ac.1: Create Auto-Classification Service [M] — Owner: auto-classify

- [ ] Create `backend/app/services/auto_classification.py`
  - [ ] `AutoClassificationService` class with lazy `GenerativeModel` init
  - [ ] `async classify(text_sample) -> tuple[str, float]`
  - [ ] Classification prompt with 5 MAIN_CATEGORIES and descriptions
  - [ ] Truncate input to 2000 chars
  - [ ] Parse JSON response: `{"category": "...", "confidence": 0.0-1.0}`
  - [ ] Validate category against `MAIN_CATEGORIES`
  - [ ] Fallback: "General and Establishment" with confidence 0.0 on error
  - [ ] `temperature=0.1`, `max_output_tokens=256`
  - [ ] Module-level singleton: `auto_classification_service = AutoClassificationService()`
- [ ] Create `backend/tests/test_auto_classification.py`
  - [ ] Test: valid category returned from mock LLM
  - [ ] Test: invalid JSON → fallback category with low confidence
  - [ ] Test: LLM exception → fallback with confidence 0.0
- [ ] Run: `python -m pytest tests/test_auto_classification.py -v` → 3 passed
- [ ] Commit: `feat: add auto-classification service for unmapped documents`

#### B.ac.2: Integrate into Ingestion Pipeline [M] — Owner: auto-classify

- [ ] Modify `backend/app/config/settings.py`
  - [ ] Add `CLASSIFICATION_CONFIDENCE_MIN: float = 0.8` after `ENTITY_CONFIDENCE_MIN`
- [ ] Modify `backend/app/routers/ingest.py`
  - [ ] Add import: `from app.services.auto_classification import auto_classification_service`
  - [ ] Replace Step 3 `if not categories:` block (lines 136-142) with:
    - [ ] Log: "No manual categories — running auto-classification"
    - [ ] Get `first_page_text = ocr_result.pages[0].text`
    - [ ] Call `auto_classification_service.classify(first_page_text)`
    - [ ] If confidence >= threshold: use category, log success
    - [ ] If confidence < threshold: use category, log warning "flagged for review"
    - [ ] If no OCR text: log warning
- [ ] Verify: `python -c "from app.routers.ingest import router; print('OK')"`
- [ ] Commit: `feat: auto-classification fallback in ingestion pipeline`

---

### Agent: frontend

#### B.fe.1: Add Source Type Indicator [S] — Owner: frontend

- [ ] Modify `frontend/src/types/index.ts`
  - [ ] Add `source_type?: "archive" | "web_fallback" | "mixed"` to `ChatMessage` interface
- [ ] Modify `frontend/src/stores/useAppStore.ts`
  - [ ] Add `source_type: response.source_type` to `assistantMsg` construction (line 66-71)
- [ ] Modify `frontend/src/components/ChatMessage.tsx`
  - [ ] Compute `sourceLabel` from `message.source_type`:
    - `"mixed"` → `"Archive + Web"`
    - `"web_fallback"` → `"Web sources"`
    - otherwise → `null` (no label)
  - [ ] Render label below assistant message content:
    ```tsx
    {sourceLabel && (
      <div className="mt-2 pt-2 border-t border-gray-700">
        <span className="text-xs text-gray-500">Sources: {sourceLabel}</span>
      </div>
    )}
    ```
- [ ] Run: `npx tsc --noEmit` → no errors
- [ ] Commit: `feat: source type indicator in chat messages`

---

## Phase C: Integration (Team Lead) — Sequential

### C.1: Merge Agent Output [M] — Owner: lead

- [ ] Merge web-search branch into main working branch
- [ ] Merge auto-classify branch into main working branch
- [ ] Merge frontend branch into main working branch
- [ ] Resolve any conflicts (none expected — agents touch different files)
- [ ] Verify backend imports: `python -c "from app.services.hybrid_retrieval import hybrid_retrieval_service; print('OK')"`
- [ ] Verify frontend types: `cd frontend && npx tsc --noEmit`

### C.2: Update .env.example [S] — Owner: lead

- [ ] Add to `backend/.env.example`:
  ```
  TAVILY_API_KEY=tvly-your-api-key-here
  CLASSIFICATION_CONFIDENCE_MIN=0.8
  ```
- [ ] Verify user has actual `TAVILY_API_KEY` in `backend/.env`

### C.3: Run All Backend Tests [S] — Owner: lead

- [ ] Run: `cd backend && python -m pytest tests/ -v`
- [ ] Expected: 7+ tests pass across test_web_search, test_llm_mixed, test_auto_classification
- [ ] Fix any failures before proceeding

### C.4: End-to-End Manual Verification [M] — Owner: lead

- [ ] Start backend: `cd backend && uvicorn app.main:app --reload --port 8090`
- [ ] Test archive-only query: `POST /query {"question": "What is Vibrona wine?"}`
  - [ ] Verify: `source_type: "archive"`, no web citations
- [ ] Test web fallback query: `POST /query {"question": "What was the population of Singapore in 1920?"}`
  - [ ] Verify: `source_type: "mixed"` or `"web_fallback"`, WebCitation objects present
- [ ] Test auto-classification: `POST /ingest_pdf {"pdf_url": "gs://aihistory-co273-nus/CO 273:550:11.pdf"}`
  - [ ] Check logs for "Auto-classified as '<category>'"
- [ ] Start frontend: `cd frontend && npm run dev`
  - [ ] Verify: source label appears for mixed/web responses
  - [ ] Verify: web citation badges are green, archive badges are blue
  - [ ] Verify: clicking web badge opens URL in new tab

### C.5: Final Commit [S] — Owner: lead

- [ ] `git add .`
- [ ] `git commit -m "feat: Phase 4 Web Augmentation complete — Tavily fallback + auto-classification"`

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| A: Foundation | 3 | 0/3 | Not Started |
| B.ws: Web Search | 3 | 0/3 | Not Started |
| B.ac: Auto-Classify | 2 | 0/2 | Not Started |
| B.fe: Frontend | 1 | 0/1 | Not Started |
| C: Integration | 5 | 0/5 | Not Started |
| **Total** | **14** | **0/14** | **Not Started** |
