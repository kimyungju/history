# Phase 5 Remaining Tasks — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete all remaining Phase 5 work: commit pending bugfix, fix ESLint errors, optimize query performance (5.5), add mobile responsive layout (5.6), create Cloud Monitoring dashboards (5.2), and build OCR confidence flagging UI (5.3).

**Architecture:** Backend performance via asyncio parallelization in hybrid_retrieval.py. Mobile layout via CSS breakpoints + tab switching. Monitoring via Cloud Monitoring JSON dashboard configs. OCR UI via new admin API endpoints + React component.

**Tech Stack:** Python 3.11/FastAPI, React 18/TypeScript/Tailwind CSS, Google Cloud Monitoring, Cytoscape.js, Vitest, pytest

**Test commands:**
- Backend: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
- Frontend: `cd frontend && npx vitest run`

---

## Phase A: Quick Wins

### Task 1: Commit vector_search.py bug fixes

**Files:**
- Already modified: `backend/app/services/vector_search.py`

These are 3 real bug fixes from a prior session: region-safe lazy `index` property, correct `Restriction` construction for upsert (single namespace with `allow_list`), and cached index reference in upsert loop.

**Step 1: Review the diff**

Run: `git diff backend/app/services/vector_search.py`
Verify: changes are region-safe index, correct restricts API, cached index ref.

**Step 2: Commit**

```bash
git add backend/app/services/vector_search.py
git commit -m "fix: vector search region-safe index + correct restricts API

- Lazy index property builds full resource name to avoid region override
- Single Restriction with allow_list instead of multiple Namespace objects
- Cache index reference before upsert loop"
```

---

### Task 2: Fix ESLint errors in GraphCanvas.tsx and PdfModal.tsx

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx` (3 errors)
- Modify: `frontend/src/components/PdfModal.tsx` (1 error)

**Step 1: Fix GraphCanvas.tsx — rules-of-hooks false positive (line 9)**

`Cytoscape.use(coseBilkent)` at module level triggers the hook linter. Add disable comment:

```tsx
// eslint-disable-next-line react-hooks/rules-of-hooks
Cytoscape.use(coseBilkent);
```

**Step 2: Fix GraphCanvas.tsx — no-explicit-any on stylesheet (line 112)**

Add disable comment above the `as any` cast:

```tsx
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ] as any,
```

**Step 3: Fix GraphCanvas.tsx — no-explicit-any on layout (line 188)**

Add disable comment above the `as any` cast:

```tsx
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any}
```

**Step 4: Fix PdfModal.tsx — no-explicit-any on render call (line 74)**

Add disable comment:

```tsx
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await page.render({ canvasContext: ctx, viewport, canvas } as any).promise;
```

**Step 5: Verify ESLint passes**

Run: `cd frontend && npx eslint src/components/GraphCanvas.tsx src/components/PdfModal.tsx`
Expected: 0 errors, 0 warnings

**Step 6: Verify all frontend tests still pass**

Run: `cd frontend && npx vitest run`
Expected: 27 tests pass

**Step 7: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx frontend/src/components/PdfModal.tsx
git commit -m "fix: resolve 4 ESLint errors in GraphCanvas and PdfModal

- Suppress rules-of-hooks false positive on Cytoscape.use (module-level)
- Suppress no-explicit-any on cytoscape stylesheet/layout casts (no types)
- Suppress no-explicit-any on pdfjs-dist render call (missing canvas type)"
```

---

## Phase B: Performance Optimization (5.5)

### Task 3: Parallelize GCS chunk loading in hybrid retrieval (TDD)

**Files:**
- Create: `backend/tests/test_hybrid_retrieval.py`
- Modify: `backend/app/services/hybrid_retrieval.py:351-410`

The `_load_chunk_contexts` method downloads one GCS blob per unique doc_id **sequentially** using a sync `download_as_text()` call. For queries hitting 5+ documents, this is a significant bottleneck. Fix: use `run_in_executor` + `asyncio.gather` to download all blobs in parallel.

**Step 1: Write the failing test**

```python
# backend/tests/test_hybrid_retrieval.py
"""Tests for hybrid retrieval performance optimizations."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.hybrid_retrieval import HybridRetrievalService


@pytest.fixture
def service():
    return HybridRetrievalService()


@pytest.fixture
def mock_storage():
    """Mock storage_service with multiple doc blobs."""
    chunks_by_doc = {
        "chunks/doc_a.json": json.dumps([
            {"chunk_id": "doc_a_chunk_0", "text": "Text A0", "pages": [1]},
        ]),
        "chunks/doc_b.json": json.dumps([
            {"chunk_id": "doc_b_chunk_0", "text": "Text B0", "pages": [1]},
        ]),
        "chunks/doc_c.json": json.dumps([
            {"chunk_id": "doc_c_chunk_0", "text": "Text C0", "pages": [2]},
        ]),
    }

    mock_bucket = MagicMock()

    def fake_blob(path):
        blob = MagicMock()
        blob.download_as_text.return_value = chunks_by_doc.get(path, "[]")
        return blob

    mock_bucket.blob.side_effect = fake_blob

    with patch("app.services.hybrid_retrieval.storage_service") as mock_svc:
        mock_svc._bucket = mock_bucket
        yield mock_svc, mock_bucket


class TestLoadChunkContextsParallel:
    """Verify _load_chunk_contexts downloads blobs concurrently."""

    @pytest.mark.asyncio
    async def test_loads_multiple_docs_concurrently(self, service, mock_storage):
        """All GCS downloads should run via asyncio.gather, not sequentially."""
        _mock_svc, mock_bucket = mock_storage

        vector_results = [
            {"id": "doc_a_chunk_0", "distance": 0.9},
            {"id": "doc_b_chunk_0", "distance": 0.85},
            {"id": "doc_c_chunk_0", "distance": 0.8},
        ]

        contexts = await service._load_chunk_contexts(vector_results)

        # All 3 docs loaded
        assert len(contexts) == 3
        # All 3 blobs were requested
        assert mock_bucket.blob.call_count == 3

    @pytest.mark.asyncio
    async def test_handles_gcs_failure_gracefully(self, service, mock_storage):
        """A single GCS failure should not block other downloads."""
        _mock_svc, mock_bucket = mock_storage

        def failing_blob(path):
            blob = MagicMock()
            if "doc_b" in path:
                blob.download_as_text.side_effect = Exception("GCS error")
            else:
                blob.download_as_text.return_value = json.dumps([
                    {"chunk_id": path.split("/")[1].replace(".json", "") + "_chunk_0",
                     "text": "OK", "pages": [1]}
                ])
            return blob

        mock_bucket.blob.side_effect = failing_blob

        vector_results = [
            {"id": "doc_a_chunk_0", "distance": 0.9},
            {"id": "doc_b_chunk_0", "distance": 0.85},
            {"id": "doc_c_chunk_0", "distance": 0.8},
        ]

        contexts = await service._load_chunk_contexts(vector_results)

        # 3 results returned (doc_b has empty text but entry still exists)
        assert len(contexts) == 3
        # doc_b chunk has empty text due to failure
        doc_b = next(c for c in contexts if c["id"] == "doc_b_chunk_0")
        assert doc_b["text"] == ""
```

**Step 2: Run test to verify it fails**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py -v`
Expected: Tests may pass or fail depending on current sync behavior. The key test is `test_loads_multiple_docs_concurrently` — it should pass functionally but we're refactoring for concurrency.

**Step 3: Implement parallel GCS loading**

Replace `_load_chunk_contexts` in `backend/app/services/hybrid_retrieval.py` (lines 351-410):

```python
    async def _load_chunk_contexts(
        self,
        vector_results: list[dict],
    ) -> list[dict]:
        """Load full chunk texts from GCS and merge with vector distances.

        Downloads are parallelized via asyncio.gather + run_in_executor.
        """

        distance_by_chunk: dict[str, float] = {
            r["id"]: r["distance"] for r in vector_results
        }

        doc_chunks: dict[str, list[str]] = defaultdict(list)
        for chunk_id in distance_by_chunk:
            parts = chunk_id.split("_chunk_", 1)
            doc_id = parts[0] if len(parts) == 2 else chunk_id
            doc_chunks[doc_id].append(chunk_id)

        # --- Parallel GCS downloads ---
        async def _download(doc_id: str) -> tuple[str, list[dict]]:
            blob_path = f"chunks/{doc_id}.json"
            try:
                blob = storage_service._bucket.blob(blob_path)
                loop = asyncio.get_event_loop()
                raw_text = await loop.run_in_executor(None, blob.download_as_text)
                return doc_id, json.loads(raw_text)
            except Exception:
                logger.warning(
                    "Failed to load chunk file from GCS: %s",
                    blob_path,
                    exc_info=True,
                )
                return doc_id, []

        results = await asyncio.gather(*[
            _download(doc_id) for doc_id in doc_chunks
        ])

        chunk_lookup: dict[str, dict] = {}
        for _doc_id, chunks_data in results:
            for chunk in chunks_data:
                cid = chunk.get("chunk_id", "")
                if cid in distance_by_chunk:
                    chunk_lookup[cid] = chunk

        # --- Build context list ---
        context_chunks: list[dict] = []
        for chunk_id, distance in distance_by_chunk.items():
            stored = chunk_lookup.get(chunk_id, {})
            parts = chunk_id.split("_chunk_", 1)
            doc_id = parts[0] if len(parts) == 2 else chunk_id

            context_chunks.append(
                {
                    "id": chunk_id,
                    "text": stored.get("text", ""),
                    "doc_id": doc_id,
                    "pages": stored.get("pages", []),
                    "confidence": distance,
                    "cite_type": "archive",
                }
            )

        context_chunks.sort(key=lambda c: c["confidence"], reverse=True)

        logger.info(
            "Loaded %d / %d chunk contexts from GCS",
            len(chunk_lookup),
            len(distance_by_chunk),
        )
        return context_chunks
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py -v`
Expected: 2 tests PASS

**Step 5: Run all backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All tests PASS (12 existing + 2 new = 14)

**Step 6: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py backend/tests/test_hybrid_retrieval.py
git commit -m "perf: parallelize GCS chunk loading in hybrid retrieval

- Replace sequential blob.download_as_text() loop with asyncio.gather
- Each GCS download runs via run_in_executor for true concurrency
- Individual download failures no longer block other documents
- Add 2 tests for concurrent loading and error resilience"
```

---

### Task 4: Parallelize graph entity search in hybrid retrieval (TDD)

**Files:**
- Modify: `backend/tests/test_hybrid_retrieval.py`
- Modify: `backend/app/services/hybrid_retrieval.py:241-317`

The `_graph_search` method calls `search_entities()` and `get_subgraph()` **sequentially** per entity hint. With 3+ entity hints, this is a bottleneck. Fix: gather all search calls in parallel, then gather all subgraph fetches in parallel.

**Step 1: Write the failing test**

Append to `backend/tests/test_hybrid_retrieval.py`:

```python
class TestGraphSearchParallel:
    """Verify _graph_search runs entity lookups concurrently."""

    @pytest.mark.asyncio
    async def test_searches_multiple_hints_concurrently(self, service):
        """All entity hint lookups should run via asyncio.gather."""
        mock_node_a = MagicMock()
        mock_node_a.canonical_id = "entity_alice_001"
        mock_node_a.name = "Alice"
        mock_node_a.main_categories = []
        mock_node_a.sub_category = None
        mock_node_a.attributes = {}
        mock_node_a.highlighted = True

        mock_node_b = MagicMock()
        mock_node_b.canonical_id = "entity_bob_001"
        mock_node_b.name = "Bob"
        mock_node_b.main_categories = []
        mock_node_b.sub_category = None
        mock_node_b.attributes = {}
        mock_node_b.highlighted = False

        mock_subgraph_a = MagicMock()
        mock_subgraph_a.nodes = [mock_node_a]
        mock_subgraph_a.edges = []

        mock_subgraph_b = MagicMock()
        mock_subgraph_b.nodes = [mock_node_b]
        mock_subgraph_b.edges = []

        async def fake_search(hint, limit=5, categories=None):
            if hint == "Alice":
                return [mock_node_a]
            elif hint == "Bob":
                return [mock_node_b]
            return []

        async def fake_subgraph(cid, categories=None):
            if cid == "entity_alice_001":
                return mock_subgraph_a
            elif cid == "entity_bob_001":
                return mock_subgraph_b
            return None

        with patch("app.services.hybrid_retrieval.neo4j_service") as mock_neo4j:
            mock_neo4j.search_entities.side_effect = fake_search
            mock_neo4j.get_subgraph.side_effect = fake_subgraph

            result = await service._graph_search(["Alice", "Bob"], None)

            assert result["payload"] is not None
            assert len(result["payload"].nodes) == 2
            # Both hints searched
            assert mock_neo4j.search_entities.call_count == 2
            assert mock_neo4j.get_subgraph.call_count == 2
```

**Step 2: Run test to verify it passes (functional baseline)**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py::TestGraphSearchParallel -v`
Expected: PASS (same results, just refactoring for concurrency)

**Step 3: Implement parallel graph search**

Replace `_graph_search` in `backend/app/services/hybrid_retrieval.py` (lines 241-317):

```python
    async def _graph_search(
        self,
        entity_hints: list[str],
        categories: list[str] | None,
    ) -> dict:
        """Search Neo4j for entities matching hints, return subgraph + context.

        Searches and subgraph fetches are parallelized via asyncio.gather.

        Returns a dict with ``payload`` (GraphPayload | None) and
        ``context_chunks`` (list of context dicts for LLM).
        """
        if not entity_hints:
            return {"payload": None, "context_chunks": []}

        # --- Phase 1: Search all entity hints in parallel ---
        search_results = await asyncio.gather(*[
            neo4j_service.search_entities(hint, limit=5, categories=categories)
            for hint in entity_hints
        ], return_exceptions=True)

        # Collect seeds for subgraph fetches
        seeds: list[GraphNode] = []
        for result in search_results:
            if isinstance(result, BaseException) or not result:
                continue
            seeds.append(result[0])

        if not seeds:
            return {"payload": None, "context_chunks": []}

        # --- Phase 2: Fetch all subgraphs in parallel ---
        subgraph_results = await asyncio.gather(*[
            neo4j_service.get_subgraph(seed.canonical_id, categories=categories)
            for seed in seeds
        ], return_exceptions=True)

        # --- Phase 3: Merge results ---
        all_nodes: dict[str, GraphNode] = {}
        all_edges: list[GraphEdge] = []
        context_chunks: list[dict] = []
        center_node: str | None = None

        for subgraph in subgraph_results:
            if isinstance(subgraph, BaseException) or subgraph is None:
                continue

            if center_node is None and subgraph.nodes:
                center_node = subgraph.nodes[0].canonical_id

            for node in subgraph.nodes:
                all_nodes[node.canonical_id] = node

            all_edges.extend(subgraph.edges)

            # Build context chunk from entity evidence for LLM grounding
            for node in subgraph.nodes:
                if node.highlighted:
                    context_chunks.append(
                        {
                            "id": node.canonical_id,
                            "text": f"Entity: {node.name}. "
                            + " ".join(
                                f"{k}: {v}" for k, v in node.attributes.items()
                            ),
                            "doc_id": "",
                            "pages": [],
                            "confidence": 0.8,
                            "cite_type": "archive",
                        }
                    )

        # Deduplicate edges
        seen_edges: set[str] = set()
        unique_edges: list[GraphEdge] = []
        for edge in all_edges:
            key = f"{edge.source}-{edge.type}-{edge.target}"
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(edge)

        payload = None
        if all_nodes:
            payload = GraphPayload(
                nodes=list(all_nodes.values()),
                edges=unique_edges,
                center_node=center_node or "",
            )

        return {"payload": payload, "context_chunks": context_chunks}
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py backend/tests/test_hybrid_retrieval.py
git commit -m "perf: parallelize graph entity search in hybrid retrieval

- Gather all search_entities calls in parallel instead of sequential loop
- Gather all get_subgraph calls in parallel after collecting seeds
- Reduces graph search latency from O(n) to O(1) for n entity hints"
```

---

### Task 5: Split query_search log_stage for observability

**Files:**
- Modify: `backend/app/services/hybrid_retrieval.py:68-77`

Currently, one `log_stage("query_search")` wraps both vector and graph tasks (which run in parallel via `asyncio.gather`). This makes it impossible to chart vector vs graph latency separately in Cloud Monitoring. Fix: wrap each branch individually.

**Step 1: Replace the combined log_stage with per-task timing**

Replace lines 68-77 in `hybrid_retrieval.py`:

```python
        # Step 2 — Parallel: vector search + graph traversal.
        async def _timed_vector():
            with log_stage("vector_search", logger=logger):
                return await vector_search_service.search(
                    query_embedding, filter_categories=filter_categories
                )

        async def _timed_graph():
            with log_stage("graph_search", logger=logger):
                return await self._graph_search(entity_hints, filter_categories)

        vector_results, graph_result = await asyncio.gather(
            _timed_vector(), _timed_graph(), return_exceptions=True
        )
```

**Step 2: Run all backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py
git commit -m "perf: split query_search log_stage into vector_search + graph_search

- Separate timing for vector search vs graph traversal
- Enables independent latency charts in Cloud Monitoring dashboards
- Both still run in parallel via asyncio.gather"
```

---

## Phase C: Mobile Responsive Layout (5.6)

### Task 6: Add useIsMobile hook (TDD)

**Files:**
- Create: `frontend/src/hooks/useIsMobile.ts`
- Create: `frontend/src/hooks/__tests__/useIsMobile.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/hooks/__tests__/useIsMobile.test.ts
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useIsMobile } from "../useIsMobile";

describe("useIsMobile", () => {
  let matchMediaMock: ReturnType<typeof vi.fn>;
  let listeners: Map<string, EventListener>;

  beforeEach(() => {
    listeners = new Map();
    matchMediaMock = vi.fn((query: string) => ({
      matches: false,
      media: query,
      addEventListener: (_event: string, listener: EventListener) => {
        listeners.set(query, listener);
      },
      removeEventListener: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    window.matchMedia = matchMediaMock;
  });

  it("returns false for desktop viewport", () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it("returns true when media query matches", () => {
    matchMediaMock.mockReturnValue({
      matches: true,
      media: "(max-width: 768px)",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });

    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/hooks/__tests__/useIsMobile.test.ts`
Expected: FAIL — module not found

**Step 3: Implement useIsMobile hook**

```typescript
// frontend/src/hooks/useIsMobile.ts
import { useState, useEffect } from "react";

const MOBILE_BREAKPOINT = "(max-width: 768px)";

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    window.matchMedia(MOBILE_BREAKPOINT).matches
  );

  useEffect(() => {
    const mql = window.matchMedia(MOBILE_BREAKPOINT);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isMobile;
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/__tests__/useIsMobile.test.ts`
Expected: 2 tests PASS

**Step 5: Commit**

```bash
git add frontend/src/hooks/useIsMobile.ts frontend/src/hooks/__tests__/useIsMobile.test.ts
git commit -m "feat(5.6): useIsMobile hook — media query breakpoint detection"
```

---

### Task 7: Responsive App layout with mobile tab switching

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/stores/useAppStore.ts`

On screens <= 768px, switch from side-by-side grid to a full-height single panel with a tab bar to toggle between Graph and Chat views.

**Step 1: Add mobileTab state to the Zustand store**

In `frontend/src/stores/useAppStore.ts`, add to `AppState` interface:

```typescript
  // UI
  mobileTab: "graph" | "chat";
  setMobileTab: (tab: "graph" | "chat") => void;
```

Add to initial state:

```typescript
  mobileTab: "chat",
```

Add action:

```typescript
  setMobileTab(tab: "graph" | "chat") {
    set({ mobileTab: tab });
  },
```

**Step 2: Update App.tsx with responsive layout**

Replace `frontend/src/App.tsx`:

```tsx
import { useAppStore } from "./stores/useAppStore";
import { useIsMobile } from "./hooks/useIsMobile";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";
import GraphSearchBar from "./components/GraphSearchBar";
import NodeSidebar from "./components/NodeSidebar";
import PdfModal from "./components/PdfModal";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);
  const mobileTab = useAppStore((s) => s.mobileTab);
  const setMobileTab = useAppStore((s) => s.setMobileTab);
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <div className="h-screen w-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-gray-700 shrink-0">
          <button
            onClick={() => setMobileTab("graph")}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              mobileTab === "graph"
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-gray-500"
            }`}
          >
            Knowledge Graph
          </button>
          <button
            onClick={() => setMobileTab("chat")}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              mobileTab === "chat"
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-gray-500"
            }`}
          >
            Chat
          </button>
        </div>

        {/* Active panel */}
        <div className="flex-1 overflow-hidden">
          {mobileTab === "graph" ? (
            <div className="relative h-full bg-gray-900">
              <GraphSearchBar />
              <GraphCanvas />
              <NodeSidebar />
            </div>
          ) : (
            <ChatPanel />
          )}
        </div>

        <PdfModal />
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 overflow-hidden">
      <div
        className="h-full grid"
        style={{
          gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
        }}
      >
        {/* Graph panel */}
        <div className="relative overflow-hidden bg-gray-900">
          <GraphSearchBar />
          <GraphCanvas />
          <NodeSidebar />
        </div>

        <ResizableSplitter />

        <ChatPanel />
      </div>

      <PdfModal />
    </div>
  );
}
```

**Step 3: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/stores/useAppStore.ts
git commit -m "feat(5.6): responsive mobile layout — tab switching for graph/chat

- Stacked single-panel layout on screens <= 768px
- Tab bar to toggle between Knowledge Graph and Chat views
- Desktop layout unchanged (side-by-side grid with splitter)"
```

---

### Task 8: Add touch support to ResizableSplitter

**Files:**
- Modify: `frontend/src/components/ResizableSplitter.tsx`

The splitter only handles mouse events. Add `onTouchStart`/`onTouchMove`/`onTouchEnd` for mobile/tablet drag interaction.

**Step 1: Add touch handlers to ResizableSplitter**

Replace `frontend/src/components/ResizableSplitter.tsx`:

```tsx
import { useCallback, useRef } from "react";
import { useAppStore } from "../stores/useAppStore";

export default function ResizableSplitter() {
  const setSplitRatio = useAppStore((s) => s.setSplitRatio);
  const isDragging = useRef(false);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;

      const onMouseMove = (moveEvent: MouseEvent) => {
        if (!isDragging.current) return;
        const ratio = moveEvent.clientX / window.innerWidth;
        setSplitRatio(ratio);
      };

      const onMouseUp = () => {
        isDragging.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [setSplitRatio]
  );

  const onTouchStart = useCallback(
    (e: React.TouchEvent) => {
      isDragging.current = true;

      const onTouchMove = (moveEvent: TouchEvent) => {
        if (!isDragging.current) return;
        const touch = moveEvent.touches[0];
        const ratio = touch.clientX / window.innerWidth;
        setSplitRatio(ratio);
      };

      const onTouchEnd = () => {
        isDragging.current = false;
        document.removeEventListener("touchmove", onTouchMove);
        document.removeEventListener("touchend", onTouchEnd);
      };

      document.addEventListener("touchmove", onTouchMove);
      document.addEventListener("touchend", onTouchEnd);
    },
    [setSplitRatio]
  );

  return (
    <div
      className="bg-gray-700 cursor-col-resize hover:bg-blue-500 active:bg-blue-400 transition-colors"
      onMouseDown={onMouseDown}
      onTouchStart={onTouchStart}
      role="separator"
      aria-orientation="vertical"
    />
  );
}
```

**Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add frontend/src/components/ResizableSplitter.tsx
git commit -m "feat(5.6): touch support for ResizableSplitter

- Add onTouchStart/onTouchMove/onTouchEnd handlers
- Enables drag-to-resize on tablets and touch devices"
```

---

## Phase D: Cloud Monitoring Dashboards (5.2)

### Task 9: Create Cloud Monitoring dashboard config

**Files:**
- Create: `infra/monitoring/dashboard.json`

Create a JSON dashboard config for Cloud Monitoring that visualizes backend service health using the structured log fields from Phase 5.1 (`stage`, `duration_ms`, `severity`).

**Step 1: Create the dashboard JSON**

```json
// infra/monitoring/dashboard.json
{
  "displayName": "Colonial Archives — Backend Health",
  "gridLayout": {
    "columns": "2",
    "widgets": [
      {
        "title": "Error Rate (severity >= ERROR)",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"colonial-archives-backend\" AND severity>=ERROR",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }]
        }
      },
      {
        "title": "Query Latency by Stage (ms)",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"colonial-archives-backend\" AND jsonPayload.stage=~\"query_embed|vector_search|graph_search|llm_generation\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_PERCENTILE_95",
                    "crossSeriesReducer": "REDUCE_NONE"
                  }
                }
              },
              "plotType": "LINE"
            }
          ]
        }
      },
      {
        "title": "Ingestion Stage Latency (ms)",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"colonial-archives-backend\" AND jsonPayload.stage=~\"ocr|chunking|embedding|vector_upsert|entity_extraction|entity_normalization|neo4j_merge\"",
                  "aggregation": {
                    "alignmentPeriod": "300s",
                    "perSeriesAligner": "ALIGN_PERCENTILE_95",
                    "crossSeriesReducer": "REDUCE_NONE"
                  }
                }
              },
              "plotType": "STACKED_BAR"
            }
          ]
        }
      },
      {
        "title": "Request Count",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"colonial-archives-backend\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }]
        }
      }
    ]
  },
  "_apply_command": "gcloud monitoring dashboards create --config-from-file=infra/monitoring/dashboard.json --project=aihistory-488807"
}
```

**Step 2: Commit**

```bash
git add infra/monitoring/dashboard.json
git commit -m "feat(5.2): Cloud Monitoring dashboard config

- Error rate, query latency by stage, ingestion latency, request count
- Uses structured log fields: stage, duration_ms, severity
- Deploy: gcloud monitoring dashboards create --config-from-file"
```

---

## Phase E: OCR Confidence Flagging UI (5.3)

### Task 10: Backend admin endpoints for OCR quality (TDD)

**Files:**
- Create: `backend/app/routers/admin.py`
- Create: `backend/tests/test_admin.py`
- Modify: `backend/app/main.py` (register router)

Add two endpoints:
- `GET /admin/documents` — list all ingested doc IDs from GCS `ocr/` prefix
- `GET /admin/documents/{doc_id}/ocr` — read OCR JSON, return per-page confidence + flagged pages

**Step 1: Write the failing tests**

```python
# backend/tests/test_admin.py
"""Tests for admin OCR quality endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_storage_blobs():
    """Mock storage_service for listing and reading OCR blobs."""
    ocr_data = [
        {"page_number": 1, "text": "Page 1 text", "confidence": 0.95},
        {"page_number": 2, "text": "Page 2 text", "confidence": 0.42},
        {"page_number": 3, "text": "Page 3 text", "confidence": 0.88},
    ]

    mock_bucket = MagicMock()

    # Mock list_blobs
    blob1 = MagicMock()
    blob1.name = "ocr/doc_alpha_ocr.json"
    blob2 = MagicMock()
    blob2.name = "ocr/doc_beta_ocr.json"
    mock_bucket.list_blobs.return_value = [blob1, blob2]

    # Mock blob download
    def fake_blob(path):
        blob = MagicMock()
        blob.download_as_text.return_value = json.dumps(ocr_data)
        return blob

    mock_bucket.blob.side_effect = fake_blob

    with patch("app.routers.admin.storage_service") as mock_svc:
        mock_svc._bucket = mock_bucket
        yield mock_svc, mock_bucket


@pytest.mark.asyncio
async def test_list_documents(mock_gcp, mock_storage_blobs):
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/admin/documents")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["documents"]) == 2
    assert "doc_alpha" in data["documents"]
    assert "doc_beta" in data["documents"]


@pytest.mark.asyncio
async def test_document_ocr_quality(mock_gcp, mock_storage_blobs):
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/admin/documents/doc_alpha/ocr")

    assert resp.status_code == 200
    data = resp.json()
    assert data["doc_id"] == "doc_alpha"
    assert data["total_pages"] == 3
    assert len(data["flagged_pages"]) == 1
    assert data["flagged_pages"][0]["page"] == 2
    assert data["flagged_pages"][0]["confidence"] == 0.42
```

**Step 2: Run test to verify it fails**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_admin.py -v`
Expected: FAIL — module `app.routers.admin` not found

**Step 3: Implement admin router**

```python
# backend/app/routers/admin.py
"""Admin endpoints for document and OCR quality management."""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, HTTPException

from app.config.settings import settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/documents")
async def list_documents() -> dict:
    """List all ingested document IDs from GCS ocr/ prefix."""
    try:
        blobs = storage_service._bucket.list_blobs(prefix="ocr/")
        doc_ids = []
        for blob in blobs:
            # Extract doc_id from "ocr/{doc_id}_ocr.json"
            match = re.match(r"ocr/(.+)_ocr\.json$", blob.name)
            if match:
                doc_ids.append(match.group(1))
        return {"documents": sorted(doc_ids)}
    except Exception:
        logger.exception("Failed to list documents from GCS")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/documents/{doc_id}/ocr")
async def document_ocr_quality(doc_id: str) -> dict:
    """Return OCR quality data for a specific document."""
    blob_path = f"ocr/{doc_id}_ocr.json"
    try:
        blob = storage_service._bucket.blob(blob_path)
        raw = blob.download_as_text()
        pages = json.loads(raw)
    except Exception:
        logger.exception("Failed to load OCR data for %s", doc_id)
        raise HTTPException(status_code=404, detail=f"OCR data not found for {doc_id}")

    flagged = [
        {"page": p["page_number"], "confidence": p["confidence"]}
        for p in pages
        if p.get("confidence", 1.0) < settings.OCR_CONFIDENCE_FLAG
    ]

    avg_confidence = (
        sum(p.get("confidence", 0) for p in pages) / len(pages) if pages else 0
    )

    return {
        "doc_id": doc_id,
        "total_pages": len(pages),
        "avg_confidence": round(avg_confidence, 3),
        "flagged_pages": flagged,
        "flagged_count": len(flagged),
    }
```

**Step 4: Register admin router in main.py**

In `backend/app/main.py`, add:

```python
from app.routers.admin import router as admin_router
app.include_router(admin_router)
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_admin.py -v`
Expected: 2 tests PASS

**Step 6: Run all backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_admin.py backend/app/main.py
git commit -m "feat(5.3): admin endpoints for OCR quality — list docs + flagged pages

- GET /admin/documents — list ingested doc IDs from GCS
- GET /admin/documents/{doc_id}/ocr — per-page confidence, flagged pages
- Flag threshold from settings.OCR_CONFIDENCE_FLAG"
```

---

### Task 11: Frontend OCR quality admin panel

**Files:**
- Create: `frontend/src/components/AdminPanel.tsx`
- Modify: `frontend/src/api/client.ts` (add admin API methods)
- Modify: `frontend/src/App.tsx` (add admin panel toggle)
- Modify: `frontend/src/stores/useAppStore.ts` (add admin state)

**Step 1: Add admin API methods to client**

In `frontend/src/api/client.ts`, add:

```typescript
  async listDocuments(): Promise<{ documents: string[] }> {
    const res = await this.http.get("/admin/documents");
    return res.data;
  },

  async getOcrQuality(docId: string): Promise<{
    doc_id: string;
    total_pages: number;
    avg_confidence: number;
    flagged_pages: { page: number; confidence: number }[];
    flagged_count: number;
  }> {
    const res = await this.http.get(`/admin/documents/${docId}/ocr`);
    return res.data;
  },
```

**Step 2: Add admin state to Zustand store**

In `frontend/src/stores/useAppStore.ts`, add to interface and initial state:

```typescript
  // UI
  isAdminOpen: boolean;
  toggleAdmin: () => void;
```

```typescript
  isAdminOpen: false,
  toggleAdmin() {
    set((s) => ({ isAdminOpen: !s.isAdminOpen }));
  },
```

**Step 3: Create AdminPanel component**

```tsx
// frontend/src/components/AdminPanel.tsx
import { useState, useEffect } from "react";
import { apiClient } from "../api/client";
import { useAppStore } from "../stores/useAppStore";

interface OcrQuality {
  doc_id: string;
  total_pages: number;
  avg_confidence: number;
  flagged_pages: { page: number; confidence: number }[];
  flagged_count: number;
}

export default function AdminPanel() {
  const isAdminOpen = useAppStore((s) => s.isAdminOpen);
  const toggleAdmin = useAppStore((s) => s.toggleAdmin);
  const openPdfModal = useAppStore((s) => s.openPdfModal);

  const [documents, setDocuments] = useState<string[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [ocrData, setOcrData] = useState<OcrQuality | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAdminOpen) return;
    setLoading(true);
    apiClient
      .listDocuments()
      .then((data) => setDocuments(data.documents))
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false));
  }, [isAdminOpen]);

  useEffect(() => {
    if (!selectedDoc) {
      setOcrData(null);
      return;
    }
    setLoading(true);
    apiClient
      .getOcrQuality(selectedDoc)
      .then(setOcrData)
      .catch(() => setOcrData(null))
      .finally(() => setLoading(false));
  }, [selectedDoc]);

  if (!isAdminOpen) return null;

  return (
    <div className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center">
      <div className="bg-gray-900 rounded-xl shadow-2xl w-[700px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h2 className="text-sm font-semibold text-gray-200">
            OCR Quality — Ingested Documents
          </h2>
          <button
            onClick={toggleAdmin}
            className="text-gray-400 hover:text-white p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading && (
            <div className="flex justify-center py-8">
              <div className="w-6 h-6 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {!loading && documents.length === 0 && (
            <p className="text-gray-500 text-sm text-center py-8">
              No ingested documents found.
            </p>
          )}

          {!loading && documents.length > 0 && (
            <div className="space-y-2">
              {documents.map((docId) => (
                <button
                  key={docId}
                  onClick={() =>
                    setSelectedDoc(selectedDoc === docId ? null : docId)
                  }
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedDoc === docId
                      ? "bg-gray-700 text-white"
                      : "text-gray-300 hover:bg-gray-800"
                  }`}
                >
                  {docId}
                </button>
              ))}
            </div>
          )}

          {/* OCR detail for selected doc */}
          {ocrData && (
            <div className="mt-4 border-t border-gray-700 pt-4">
              <div className="flex items-center gap-4 mb-3">
                <span className="text-sm text-gray-300">
                  Pages: {ocrData.total_pages}
                </span>
                <span className="text-sm text-gray-300">
                  Avg confidence:{" "}
                  <span
                    className={
                      ocrData.avg_confidence < 0.7
                        ? "text-red-400"
                        : "text-green-400"
                    }
                  >
                    {(ocrData.avg_confidence * 100).toFixed(1)}%
                  </span>
                </span>
                <span className="text-sm text-gray-300">
                  Flagged: {ocrData.flagged_count}
                </span>
              </div>

              {ocrData.flagged_pages.length > 0 ? (
                <div className="space-y-1">
                  <p className="text-xs text-gray-500 mb-2">
                    Flagged pages (click to view in PDF):
                  </p>
                  {ocrData.flagged_pages.map((fp) => (
                    <button
                      key={fp.page}
                      onClick={() => openPdfModal(ocrData.doc_id, fp.page)}
                      className="flex items-center gap-3 w-full px-3 py-1.5 rounded text-sm text-left hover:bg-gray-800 transition-colors"
                    >
                      <span className="text-gray-400">
                        Page {fp.page}
                      </span>
                      <span className="text-red-400 text-xs">
                        {(fp.confidence * 100).toFixed(1)}% confidence
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-green-400">
                  All pages above confidence threshold.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 4: Wire AdminPanel into App.tsx**

Add import and render `<AdminPanel />` alongside `<PdfModal />` in both mobile and desktop layouts. Add a small admin toggle button in the top-right corner:

In App.tsx, add import:
```tsx
import AdminPanel from "./components/AdminPanel";
```

Add the toggle button inside the graph panel `<div>` (both mobile and desktop):
```tsx
<button
  onClick={toggleAdmin}
  className="absolute top-2 right-2 z-10 text-gray-500 hover:text-gray-300 text-xs px-2 py-1 rounded bg-gray-800/80"
>
  Admin
</button>
```

Add `<AdminPanel />` next to `<PdfModal />`:
```tsx
<PdfModal />
<AdminPanel />
```

Add `toggleAdmin` to the destructured store calls:
```tsx
const toggleAdmin = useAppStore((s) => s.toggleAdmin);
```

**Step 5: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add frontend/src/components/AdminPanel.tsx frontend/src/api/client.ts frontend/src/App.tsx frontend/src/stores/useAppStore.ts
git commit -m "feat(5.3): OCR confidence flagging UI — admin panel

- AdminPanel modal listing ingested documents from /admin/documents
- Click document to see per-page OCR confidence scores
- Flagged pages (below threshold) highlighted in red
- Click flagged page to open in PDF modal for review
- Admin toggle button in graph panel corner"
```

---

## Phase F: GCP Infrastructure (T11) — Manual Commands

> These are `gcloud` commands to run in **PowerShell** (not bash). Not TDD tasks.

```powershell
# 1. Enable APIs
gcloud services enable cloudbuild.googleapis.com --project=aihistory-488807
gcloud services enable secretmanager.googleapis.com --project=aihistory-488807
gcloud services enable artifactregistry.googleapis.com --project=aihistory-488807

# 2. Create Artifact Registry repo
gcloud artifacts repositories create colonial-archives `
  --repository-format=docker --location=asia-southeast1 --project=aihistory-488807

# 3. Create Secret Manager secrets
echo -n "neo4j+s://ae76ab7c.databases.neo4j.io" | `
  gcloud secrets create neo4j-uri --data-file=- --project=aihistory-488807
echo -n "ae76ab7c" | `
  gcloud secrets create neo4j-user --data-file=- --project=aihistory-488807
# Replace YOUR_PASSWORD with actual Neo4j password:
echo -n "YOUR_PASSWORD" | `
  gcloud secrets create neo4j-password --data-file=- --project=aihistory-488807

# 4. IAM for Cloud Build SA
$PROJECT_NUMBER = (gcloud projects describe aihistory-488807 --format='value(projectNumber)')
foreach ($role in @("roles/run.admin", "roles/iam.serviceAccountUser", "roles/artifactregistry.writer", "roles/secretmanager.secretAccessor")) {
  gcloud projects add-iam-policy-binding aihistory-488807 `
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" `
    --role=$role
}

# 5. Deploy monitoring dashboard
gcloud monitoring dashboards create --config-from-file=infra/monitoring/dashboard.json --project=aihistory-488807

# 6. Deploy alert policy
gcloud alpha monitoring policies create --policy-from-file=infra/logging/alert-policy.json --project=aihistory-488807

# 7. Test pipeline
gcloud builds submit . --config=cloudbuild.yaml --project=aihistory-488807
```

---

## Summary

| Phase | Tasks | New Tests | Key Changes |
|-------|-------|-----------|-------------|
| A: Quick Wins | 1-2 | 0 | Commit bugfix, fix ESLint |
| B: Performance (5.5) | 3-5 | 3 | Parallel GCS + graph + split log stages |
| C: Mobile (5.6) | 6-8 | 2 | useIsMobile hook, tab layout, touch splitter |
| D: Dashboards (5.2) | 9 | 0 | JSON config for Cloud Monitoring |
| E: OCR UI (5.3) | 10-11 | 2 | Admin endpoints + AdminPanel component |
| F: GCP Infra (T11) | — | — | Manual gcloud commands |

**Total: 11 tasks, ~7 new tests, touches ~15 files.**

### Not in scope (deferred)
- **5.4 Batch Ingestion** — depends on Pub/Sub, deferred until corpus > 100 docs
- **3.8 Integration Testing** — needs live backend + frontend running together
- **Phase 4 task tracker updates** — code exists but checkboxes not updated
