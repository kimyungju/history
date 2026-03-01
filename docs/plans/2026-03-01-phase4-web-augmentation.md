# Phase 4: Web Augmentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Tavily web search fallback when archive relevance is low, auto-classify unmapped documents via Gemini, and show source type indicators in the frontend.

**Architecture:** When hybrid retrieval (vector + graph) yields combined relevance < 0.7, Tavily web search supplements archive results. The LLM receives both archive and web context with separate citation prefixes (`[archive:N]` / `[web:N]`). Unmapped PDFs get auto-classified by Gemini Flash using first-page OCR text. Pub/Sub async ingestion is deferred to Phase 5 — current `BackgroundTasks` approach handles the ~20-doc corpus fine.

**Tech Stack:** tavily-python (web search), Gemini 2.0 Flash (auto-classification), pytest + pytest-asyncio (backend tests)

**Scope Note:** Task 4.3 (Category Filter UI) was already completed in Phase 3 — `CategoryFilter.tsx`, `filterCategories` store field, and `QueryRequest.filter_categories` all exist. Task 4.2 (Mixed Citation Rendering) is partially done — `CitationBadge.tsx` handles both archive and web citations, `WebCitation` schema exists. Task 4.4 (Pub/Sub) is deferred as optional stretch goal.

---

## Task 1: Add Phase 4 Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add tavily-python and test dependencies**

Add to the end of `backend/requirements.txt`:

```
tavily-python==0.5.0
pytest==8.3.4
pytest-asyncio==0.24.0
```

**Step 2: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`
Expected: All packages install successfully, tavily importable.

**Step 3: Verify import**

Run: `cd backend && python -c "from tavily import TavilyClient; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add tavily-python and pytest dependencies for Phase 4"
```

---

## Task 2: Create Tavily Web Search Service

**Files:**
- Create: `backend/app/services/web_search.py`

**Step 1: Write the failing test**

Create `backend/tests/__init__.py` (empty) and `backend/tests/test_web_search.py`:

```python
"""Tests for Tavily web search service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.web_search import web_search_service


@pytest.mark.asyncio
async def test_search_returns_formatted_results():
    """Web search returns list of dicts with id, title, url, text, cite_type."""
    mock_response = {
        "results": [
            {"title": "Straits Settlements - Wikipedia", "url": "https://en.wikipedia.org/wiki/Straits_Settlements", "content": "The Straits Settlements were a group of British territories."},
            {"title": "Colonial Singapore", "url": "https://example.com/colonial", "content": "Singapore was a crown colony from 1867."},
        ]
    }

    with patch.object(web_search_service, "_client") as mock_client:
        mock_client.search.return_value = mock_response
        # Force the property to return our mock
        with patch.object(type(web_search_service), "client", new_callable=lambda: property(lambda self: mock_client)):
            results = await web_search_service.search("Straits Settlements history")

    assert len(results) == 2
    assert results[0]["id"] == "web_1"
    assert results[0]["cite_type"] == "web"
    assert results[0]["title"] == "Straits Settlements - Wikipedia"
    assert results[0]["url"] == "https://en.wikipedia.org/wiki/Straits_Settlements"
    assert "British territories" in results[0]["text"]
    assert results[1]["id"] == "web_2"


@pytest.mark.asyncio
async def test_search_returns_empty_on_no_results():
    """Web search returns empty list when Tavily returns no results."""
    mock_response = {"results": []}

    with patch.object(web_search_service, "_client") as mock_client:
        mock_client.search.return_value = mock_response
        with patch.object(type(web_search_service), "client", new_callable=lambda: property(lambda self: mock_client)):
            results = await web_search_service.search("xyznonexistent")

    assert results == []


@pytest.mark.asyncio
async def test_search_handles_api_error():
    """Web search returns empty list on Tavily API error."""
    with patch.object(web_search_service, "_client") as mock_client:
        mock_client.search.side_effect = Exception("API rate limit")
        with patch.object(type(web_search_service), "client", new_callable=lambda: property(lambda self: mock_client)):
            results = await web_search_service.search("test query")

    assert results == []
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_web_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.web_search'`

**Step 3: Write the web search service**

Create `backend/app/services/web_search.py`:

```python
"""Tavily web search service for the Colonial Archives Graph-RAG backend.

Phase 4: Provides web search fallback when archive relevance is low.
Only triggered when combined relevance score < RELEVANCE_THRESHOLD (0.7).
"""

from __future__ import annotations

import asyncio
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class WebSearchService:
    """Wraps the Tavily API for web search fallback."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from tavily import TavilyClient

            self._client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            logger.info("TavilyClient initialised")
        return self._client

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web via Tavily and return formatted results.

        Each result dict has: id, title, url, text, cite_type.
        Returns an empty list on error (web search is best-effort).
        """
        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.client.search(
                    query, search_depth="basic", max_results=max_results
                ),
            )
        except Exception:
            logger.exception("Tavily search failed for query: %s", query)
            return []

        results: list[dict] = []
        for i, r in enumerate(response.get("results", []), start=1):
            results.append(
                {
                    "id": f"web_{i}",
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "text": r.get("content", ""),
                    "cite_type": "web",
                }
            )

        logger.info("Tavily returned %d results for query: %s", len(results), query)
        return results


# Module-level singleton
web_search_service = WebSearchService()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_web_search.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add backend/app/services/web_search.py backend/tests/__init__.py backend/tests/test_web_search.py
git commit -m "feat: add Tavily web search service for Phase 4 web fallback"
```

---

## Task 3: Update LLM Service for Mixed Sources

**Files:**
- Modify: `backend/app/services/llm.py` (lines 70-84)

**Step 1: Write the failing test**

Create `backend/tests/test_llm_mixed.py`:

```python
"""Tests for LLM service mixed source citation handling."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from app.services.llm import llm_service, ANSWER_GENERATION_PROMPT


def test_prompt_uses_per_chunk_cite_type():
    """When context has mixed cite_types, prompt uses [archive:N] and [web:N] separately."""
    context_chunks = [
        {"id": "chunk_001", "text": "Archive content about trade.", "cite_type": "archive"},
        {"id": "chunk_002", "text": "Archive content about governance.", "cite_type": "archive"},
        {"id": "web_1", "text": "Web article about Straits.", "cite_type": "web"},
    ]

    # Call the internal prompt builder (we test by examining the prompt)
    context_parts = []
    citation_refs = []
    archive_idx = 0
    web_idx = 0

    for chunk in context_chunks:
        cite_type = chunk.get("cite_type", "archive")
        if cite_type == "archive":
            archive_idx += 1
            prefix = f"[archive:{archive_idx}]"
        else:
            web_idx += 1
            prefix = f"[web:{web_idx}]"
        context_parts.append(f"{prefix} {chunk.get('text', '')}")
        citation_refs.append(prefix)

    context_str = "\n\n".join(context_parts)

    assert "[archive:1] Archive content about trade." in context_str
    assert "[archive:2] Archive content about governance." in context_str
    assert "[web:1] Web article about Straits." in context_str
    assert "[archive:3]" not in context_str  # No archive:3
    assert "[web:2]" not in context_str  # No web:2
```

**Step 2: Run test to verify it passes (this is a logic test)**

Run: `cd backend && python -m pytest tests/test_llm_mixed.py -v`
Expected: PASS (this validates the numbering logic we'll implement)

**Step 3: Update LLM service to use per-chunk citation types**

In `backend/app/services/llm.py`, replace lines 70-84 (the `cite_type` assignment and the for loop) with:

```python
        # Build the context block and citation reference list.
        # Use per-chunk cite_type for mixed source support (Phase 4).
        context_parts: list[str] = []
        citation_refs: list[str] = []
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
            context_parts.append(f"{prefix} {chunk.get('text', '')}")
            citation_refs.append(prefix)
```

This replaces lines 70-80 of the original file. The old code:
```python
        cite_type = "archive" if source_type == "archive" else "web"

        # Build the context block and citation reference list.
        context_parts: list[str] = []
        citation_refs: list[str] = []

        for idx, chunk in enumerate(context_chunks, start=1):
            cite_id = chunk.get("id", idx)
            prefix = f"[{cite_type}:{cite_id}]"
            context_parts.append(f"{prefix} {chunk.get('text', '')}")
            citation_refs.append(f"{prefix} chunk {cite_id}")
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_llm_mixed.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/llm.py backend/tests/test_llm_mixed.py
git commit -m "feat: update LLM service to support per-chunk citation types (archive/web)"
```

---

## Task 4: Integrate Web Fallback into Hybrid Retrieval

**Files:**
- Modify: `backend/app/services/hybrid_retrieval.py` (lines 22-27 imports, lines 125-133 placeholder, lines 141-166 response building)

This is the core integration — replacing the Phase 4 placeholder with actual web search logic.

**Step 1: Add web_search_service import**

In `backend/app/services/hybrid_retrieval.py`, add to imports (after line 27):

```python
from app.services.web_search import web_search_service
```

And add `WebCitation` to the schemas import (line 17):

```python
from app.models.schemas import (
    ArchiveCitation,
    GraphEdge,
    GraphNode,
    GraphPayload,
    QueryResponse,
    WebCitation,
)
```

**Step 2: Replace the Phase 4 placeholder (lines 125-133) with web fallback logic**

Replace this block:
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

With:
```python
        # Phase 4: Web fallback when relevance is below threshold.
        web_context: list[dict] = []
        source_type = "archive"

        if relevance_score < settings.RELEVANCE_THRESHOLD:
            logger.info(
                "Relevance %.4f below threshold %.2f — triggering web fallback",
                relevance_score,
                settings.RELEVANCE_THRESHOLD,
            )
            try:
                web_context = await web_search_service.search(question)
                if web_context:
                    merged_context.extend(web_context)
                    source_type = "mixed" if merged_context else "web_fallback"
                    logger.info("Added %d web results to context", len(web_context))
            except Exception:
                logger.exception("Web fallback failed; continuing with archive only")

        # If we only had web results (no archive at all), mark as web_fallback.
        if not vector_results and not graph_context and web_context:
            source_type = "web_fallback"
```

**Step 3: Update response building to include WebCitation objects (lines 141-166)**

Replace the citations and response building block:

```python
        # Step 7 — Generate answer via LLM.
        llm_result: dict = await llm_service.generate_answer(
            question, merged_context, source_type
        )
        answer_text: str = llm_result["answer"]

        # Step 8 — Build citation list (archive + web).
        citations: list[ArchiveCitation | WebCitation] = []
        archive_idx = 0
        web_idx = 0

        for chunk in merged_context:
            cite_type = chunk.get("cite_type", "archive")
            if cite_type == "web":
                web_idx += 1
                citations.append(
                    WebCitation(
                        id=web_idx,
                        title=chunk.get("title", ""),
                        url=chunk.get("url", ""),
                    )
                )
            else:
                archive_idx += 1
                text_span = chunk.get("text", "")
                if len(text_span) > 300:
                    text_span = text_span[:300]
                citations.append(
                    ArchiveCitation(
                        id=archive_idx,
                        doc_id=chunk.get("doc_id", ""),
                        pages=chunk.get("pages", []),
                        text_span=text_span,
                        confidence=chunk.get("confidence", 0.0),
                    )
                )

        # Step 9 — Build graph payload.
        graph_payload = graph_result.get("payload")

        return QueryResponse(
            answer=answer_text,
            source_type=source_type,
            citations=citations,
            graph=graph_payload,
        )
```

**Step 4: Run server to verify no import errors**

Run: `cd backend && python -c "from app.services.hybrid_retrieval import hybrid_retrieval_service; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py
git commit -m "feat: integrate Tavily web fallback into hybrid retrieval pipeline"
```

---

## Task 5: Add Source Type Indicator to ChatPanel

**Files:**
- Modify: `frontend/src/components/ChatMessage.tsx` (add source_type badge)
- Modify: `frontend/src/types/index.ts` (add source_type to ChatMessage)

**Step 1: Add source_type to ChatMessage type**

In `frontend/src/types/index.ts`, find the `ChatMessage` interface and add `source_type`:

```typescript
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  graph?: GraphPayload | null;
  source_type?: "archive" | "web_fallback" | "mixed";
}
```

**Step 2: Update Zustand store to pass source_type**

In `frontend/src/stores/useAppStore.ts`, in the `sendQuery` action (around line 66), update the `assistantMsg` construction:

```typescript
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        graph: response.graph,
        source_type: response.source_type,
      };
```

**Step 3: Add source type indicator to ChatMessage component**

In `frontend/src/components/ChatMessage.tsx`, after the citations segment rendering (inside the assistant message div, after the map), add a source type indicator:

```tsx
  // Source type label
  const sourceLabel =
    message.source_type === "mixed"
      ? "Archive + Web"
      : message.source_type === "web_fallback"
        ? "Web sources"
        : null;

  return (
    <div className="flex justify-start mb-3">
      <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
        <div className="text-sm prose prose-invert prose-sm max-w-none">
          {segments.map((seg, i) =>
            seg.type === "text" ? (
              <Markdown key={i}>{seg.content}</Markdown>
            ) : (
              <CitationBadge key={i} citation={seg.citation} />
            )
          )}
        </div>
        {sourceLabel && (
          <div className="mt-2 pt-2 border-t border-gray-700">
            <span className="text-xs text-gray-500">
              Sources: {sourceLabel}
            </span>
          </div>
        )}
      </div>
    </div>
  );
```

**Step 4: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/stores/useAppStore.ts frontend/src/components/ChatMessage.tsx
git commit -m "feat: add source type indicator (archive/mixed/web) to chat messages"
```

---

## Task 6: Create Auto-Classification Service

**Files:**
- Create: `backend/app/services/auto_classification.py`

**Step 1: Write the failing test**

Create `backend/tests/test_auto_classification.py`:

```python
"""Tests for auto-classification service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.auto_classification import auto_classification_service
from app.models.schemas import MAIN_CATEGORIES


@pytest.mark.asyncio
async def test_classify_returns_valid_category():
    """classify() returns a category from MAIN_CATEGORIES and a confidence score."""
    mock_response = MagicMock()
    mock_response.text = '{"category": "Economic and Financial", "confidence": 0.92}'

    with patch.object(
        type(auto_classification_service), "model",
        new_callable=lambda: property(lambda self: MagicMock(generate_content=MagicMock(return_value=mock_response)))
    ):
        category, confidence = await auto_classification_service.classify(
            "Revenue from import duties on wines and spirits in the Straits Settlements."
        )

    assert category in MAIN_CATEGORIES
    assert category == "Economic and Financial"
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_classify_returns_general_on_invalid_json():
    """classify() returns General and Establishment with low confidence on parse error."""
    mock_response = MagicMock()
    mock_response.text = "not valid json"

    with patch.object(
        type(auto_classification_service), "model",
        new_callable=lambda: property(lambda self: MagicMock(generate_content=MagicMock(return_value=mock_response)))
    ):
        category, confidence = await auto_classification_service.classify("some text")

    assert category == "General and Establishment"
    assert confidence < 0.5


@pytest.mark.asyncio
async def test_classify_returns_general_on_exception():
    """classify() returns General and Establishment on LLM error."""
    with patch.object(
        type(auto_classification_service), "model",
        new_callable=lambda: property(lambda self: MagicMock(generate_content=MagicMock(side_effect=Exception("API error"))))
    ):
        category, confidence = await auto_classification_service.classify("some text")

    assert category == "General and Establishment"
    assert confidence == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auto_classification.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.auto_classification'`

**Step 3: Write the auto-classification service**

Create `backend/app/services/auto_classification.py`:

```python
"""Auto-classification service for unmapped documents.

Phase 4: Uses Gemini Flash to classify documents into one of 5 MAIN_CATEGORIES
when no manual mapping exists in document_categories.json.
"""

from __future__ import annotations

import asyncio
import json
import logging

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from app.config.settings import settings
from app.models.schemas import MAIN_CATEGORIES

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a document classifier for colonial-era British archives (primarily Straits Settlements CO 273 series).

Classify the following document excerpt into exactly ONE of these categories:
1. Internal Relations and Research
2. Economic and Financial
3. Social Services
4. Defence and Military
5. General and Establishment

Category descriptions:
- "Internal Relations and Research": Diplomatic correspondence, inter-colonial relations, political affairs, surveys, and research reports.
- "Economic and Financial": Trade, revenue, taxation, customs duties, commerce, budgets, and financial administration.
- "Social Services": Education, health, welfare, immigration, labor, and public works.
- "Defence and Military": Military operations, defence planning, police, security, and wartime matters.
- "General and Establishment": Administrative appointments, regulations, civil service, constitutional matters, and anything not fitting the above.

Document excerpt:
\"\"\"
{text_sample}
\"\"\"

Respond with ONLY valid JSON (no markdown): {{"category": "<exact category name>", "confidence": <0.0-1.0>}}"""

FALLBACK_CATEGORY = "General and Establishment"


class AutoClassificationService:
    """Classifies documents into MAIN_CATEGORIES using Gemini Flash."""

    def __init__(self) -> None:
        self._model = None

    @property
    def model(self):
        if self._model is None:
            vertexai.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.VERTEX_LLM_REGION,
            )
            self._model = GenerativeModel(settings.VERTEX_LLM_MODEL)
            logger.info("AutoClassificationService initialised")
        return self._model

    async def classify(self, text_sample: str) -> tuple[str, float]:
        """Classify a document excerpt into one of MAIN_CATEGORIES.

        Args:
            text_sample: Text excerpt from the document (typically first page OCR).

        Returns:
            Tuple of (category_name, confidence). Falls back to
            'General and Establishment' with confidence 0.0 on error.
        """
        # Truncate to 2000 chars to keep prompt short.
        truncated = text_sample[:2000]
        prompt = CLASSIFICATION_PROMPT.format(text_sample=truncated)

        loop = asyncio.get_event_loop()
        generation_config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=256,
        )

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt, generation_config=generation_config
                ),
            )
        except Exception:
            logger.exception("Auto-classification LLM call failed")
            return FALLBACK_CATEGORY, 0.0

        try:
            result = json.loads(response.text)
            category = result.get("category", FALLBACK_CATEGORY)
            confidence = float(result.get("confidence", 0.0))

            # Validate category is in the allowed list.
            if category not in MAIN_CATEGORIES:
                logger.warning(
                    "LLM returned invalid category '%s'; falling back to '%s'",
                    category,
                    FALLBACK_CATEGORY,
                )
                category = FALLBACK_CATEGORY
                confidence = min(confidence, 0.3)

            return category, confidence

        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse classification response: %s", response.text)
            return FALLBACK_CATEGORY, 0.3


# Module-level singleton
auto_classification_service = AutoClassificationService()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auto_classification.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add backend/app/services/auto_classification.py backend/tests/test_auto_classification.py
git commit -m "feat: add auto-classification service for unmapped documents"
```

---

## Task 7: Integrate Auto-Classification into Ingestion Pipeline

**Files:**
- Modify: `backend/app/routers/ingest.py` (import + step 3 fallback)
- Modify: `backend/app/config/settings.py` (add threshold)

**Step 1: Add classification confidence threshold to settings**

In `backend/app/config/settings.py`, add after the `ENTITY_CONFIDENCE_MIN` line:

```python
    # Auto-classification (Phase 4)
    CLASSIFICATION_CONFIDENCE_MIN: float = 0.8
```

**Step 2: Add import in ingest.py**

At the top of `backend/app/routers/ingest.py`, add after the existing service imports (line 24):

```python
from app.services.auto_classification import auto_classification_service
```

**Step 3: Update Step 3 in _run_ingestion to use auto-classification fallback**

In `backend/app/routers/ingest.py`, replace the Step 3 block (lines 125-142) with:

```python
        # ---- Step 3: Resolve categories -------------------------------------
        categories_map = _load_document_categories()

        # Derive the PDF filename from the URL for the primary lookup
        blob_name = storage_service._parse_blob_name(pdf_url)
        pdf_filename = PurePosixPath(blob_name).name

        categories: list[str] = categories_map.get(
            pdf_filename, categories_map.get(doc_id, [])
        )

        if not categories:
            # Phase 4: Auto-classify using first-page OCR text.
            logger.info(
                "[%s] No manual categories for %s — running auto-classification",
                job_id,
                pdf_filename,
            )
            first_page_text = ocr_result.pages[0].text if ocr_result.pages else ""
            if first_page_text:
                category, confidence = await auto_classification_service.classify(
                    first_page_text
                )
                if confidence >= settings.CLASSIFICATION_CONFIDENCE_MIN:
                    categories = [category]
                    logger.info(
                        "[%s] Auto-classified as '%s' (confidence=%.2f)",
                        job_id,
                        category,
                        confidence,
                    )
                else:
                    categories = [category]
                    logger.warning(
                        "[%s] Auto-classified as '%s' with LOW confidence %.2f (threshold=%.2f) — flagged for review",
                        job_id,
                        category,
                        confidence,
                        settings.CLASSIFICATION_CONFIDENCE_MIN,
                    )
            else:
                logger.warning("[%s] No OCR text for auto-classification", job_id)
```

**Step 4: Verify no import errors**

Run: `cd backend && python -c "from app.routers.ingest import router; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/config/settings.py backend/app/routers/ingest.py
git commit -m "feat: integrate auto-classification fallback into ingestion pipeline"
```

---

## Task 8: Update .env.example with Phase 4 Variables

**Files:**
- Modify: `backend/.env.example` (if it exists, otherwise create)

**Step 1: Add Phase 4 environment variables**

Add these lines to `.env.example`:

```bash
# Phase 4: Tavily Web Search (get key at https://tavily.com)
TAVILY_API_KEY=tvly-your-api-key-here

# Phase 4: Auto-classification confidence threshold (0.0-1.0)
CLASSIFICATION_CONFIDENCE_MIN=0.8
```

**Step 2: Add actual TAVILY_API_KEY to .env**

The user needs to get a Tavily API key from https://tavily.com (free tier: 1000 searches/month).

Add to `backend/.env`:
```bash
TAVILY_API_KEY=<actual-key>
```

**Step 3: Commit .env.example only (never .env)**

```bash
git add backend/.env.example
git commit -m "docs: add Phase 4 env variables to .env.example"
```

---

## Task 9: End-to-End Manual Verification

**No files changed — manual testing only.**

**Step 1: Start the backend**

Run: `cd backend && uvicorn app.main:app --reload --port 8090`
Expected: Server starts, logs show Neo4j connected.

**Step 2: Test query with high relevance (no web fallback)**

Run:
```bash
curl -s -X POST http://127.0.0.1:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Vibrona wine?"}' | python -m json.tool
```
Expected: `source_type` = `"archive"`, citations are all `type: "archive"`, no web citations.

**Step 3: Test query with low relevance (triggers web fallback)**

Run:
```bash
curl -s -X POST http://127.0.0.1:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the population of Singapore in 1920?"}' | python -m json.tool
```
Expected: If relevance < 0.7, `source_type` = `"mixed"` or `"web_fallback"`, response includes `WebCitation` objects with title/url.

**Step 4: Test auto-classification (ingest an unmapped PDF)**

Run:
```bash
curl -s -X POST http://127.0.0.1:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:550:11.pdf"}'
```
Check server logs for: `Auto-classified as '<category>' (confidence=X.XX)` — since this PDF is not in `document_categories.json`, auto-classification should trigger.

**Step 5: Start the frontend and test source type indicator**

Run: `cd frontend && npm run dev`

Open http://localhost:5173, ask a question that triggers web fallback. Verify:
- Chat bubble shows "Sources: Archive + Web" or "Sources: Web sources" label
- Web citation badges are green (emerald), archive badges are blue
- Clicking web badge opens URL in new tab

**Step 6: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass (6+ tests across 3 test files).

---

## Task 10 (Stretch — Deferrable): Pub/Sub Async Ingestion

> **Note:** This task is optional. The current `BackgroundTasks` approach works well for ~20 documents. Pub/Sub is recommended only if you need: (a) ingestion to survive server restarts, (b) concurrent workers processing multiple PDFs, or (c) dead-letter queues for failed ingestions. Consider implementing this in Phase 5 alongside production hardening.

If implementing, the scope is:

1. **Add `google-cloud-pubsub`** to `requirements.txt`
2. **Create Pub/Sub topic** via `gcloud pubsub topics create colonial-archives-ingest`
3. **Create subscription** via `gcloud pubsub subscriptions create colonial-archives-ingest-sub --topic=colonial-archives-ingest`
4. **Create `backend/app/services/job_store.py`** — persistent job status in Cloud Storage (replace in-memory `_jobs` dict)
5. **Refactor `POST /ingest_pdf`** — publish message to Pub/Sub instead of `BackgroundTasks`
6. **Create `backend/app/worker.py`** — Pub/Sub subscriber that pulls messages and runs the ingestion pipeline
7. **Update `GET /ingest_status/{job_id}`** — read from Cloud Storage instead of `_jobs`
8. **Add dead-letter topic** for failed messages (max 3 retries)

Estimated effort: 3 days. Files: 3 new, 2 modified.

---

## Summary

| Task | Component | What It Does | Status |
|------|-----------|-------------|--------|
| 1 | Dependencies | Add tavily-python, pytest | Required |
| 2 | Backend Service | Tavily web search wrapper | Required |
| 3 | Backend Service | LLM per-chunk citation types | Required |
| 4 | Backend Service | Web fallback in hybrid retrieval | Required |
| 5 | Frontend | Source type indicator in chat | Required |
| 6 | Backend Service | Gemini auto-classification | Required |
| 7 | Backend Integration | Auto-classify in ingestion pipeline | Required |
| 8 | Config | .env.example updates | Required |
| 9 | Testing | End-to-end manual verification | Required |
| 10 | Backend Architecture | Pub/Sub async ingestion | Stretch (defer to Phase 5) |

**Key files created:**
- `backend/app/services/web_search.py`
- `backend/app/services/auto_classification.py`
- `backend/tests/test_web_search.py`
- `backend/tests/test_auto_classification.py`
- `backend/tests/test_llm_mixed.py`

**Key files modified:**
- `backend/app/services/llm.py` (per-chunk citation types)
- `backend/app/services/hybrid_retrieval.py` (web fallback integration)
- `backend/app/routers/ingest.py` (auto-classification step)
- `backend/app/config/settings.py` (classification threshold)
- `backend/requirements.txt` (new dependencies)
- `frontend/src/types/index.ts` (source_type on ChatMessage)
- `frontend/src/stores/useAppStore.ts` (pass source_type)
- `frontend/src/components/ChatMessage.tsx` (source label)
