# Knowledge Graph Visualization Overhaul — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the graph panel from a search-only view into a two-state visualization — a full overview of all entities on page load (clustered by category), transitioning to a filtered subgraph when the user asks a question.

**Architecture:** Add a `GET /graph/overview` backend endpoint that returns all entities with connection counts. Frontend switches from `cose-bilkent` to `fcose` layout with category-aware edge lengths to create spatial clusters. A new `GraphLegend` component provides color-coded category legend with toggle filtering. State transitions animate between overview and query-filtered views.

**Tech Stack:** FastAPI, Neo4j (Cypher), Cytoscape.js with `cytoscape-fcose`, React/TypeScript, Zustand

---

## Existing Code Reference

| File | Role |
|------|------|
| `backend/app/routers/graph.py` | Graph API router — `GET /graph/search`, `GET /graph/{canonical_id}` |
| `backend/app/services/neo4j_service.py` | Neo4j service — `search_entities()`, `get_subgraph()`, `_record_to_graph_node()` |
| `backend/app/models/schemas.py` | Pydantic models — `GraphNode`, `GraphEdge`, `GraphPayload` |
| `frontend/src/components/GraphCanvas.tsx` | Cytoscape.js renderer — cose-bilkent layout, node tap, empty states |
| `frontend/src/components/GraphSearchBar.tsx` | Entity search input with 300ms debounce |
| `frontend/src/components/NodeSidebar.tsx` | Selected node detail panel |
| `frontend/src/stores/useAppStore.ts` | Zustand store — `graphData`, `selectedNode`, `setGraphData()` |
| `frontend/src/api/client.ts` | API client — `searchGraph()`, `postQuery()` |
| `frontend/src/types/index.ts` | TypeScript types — `GraphNode`, `GraphPayload`, `MAIN_CATEGORIES` |
| `frontend/src/hooks/useGraphSearch.ts` | Graph search hook with debounce |

**Current Cytoscape deps** (in `package.json`): `cytoscape ^3.33.1`, `cytoscape-cose-bilkent ^4.1.0`, `react-cytoscapejs ^2.0.0`, `@types/cytoscape ^3.21.9`

**Current `GraphNode` schema** (backend + frontend): `canonical_id`, `name`, `main_categories: list[str]`, `sub_category`, `attributes`, `highlighted`

**Current `GraphPayload`**: `nodes: GraphNode[]`, `edges: GraphEdge[]`, `center_node: str`

---

## Task 1: Backend — Add `get_overview_graph()` to Neo4j service

**Files:**
- Modify: `backend/app/services/neo4j_service.py`
- Test: `backend/tests/test_graph_overview.py`

**Step 1: Write the failing test**

Create `backend/tests/test_graph_overview.py`:

```python
"""Tests for the graph overview endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import GraphEdge, GraphNode, GraphOverviewPayload


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j async driver."""
    driver = AsyncMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__ = AsyncMock(return_value=session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return driver, session


@pytest.mark.asyncio
async def test_get_overview_graph_returns_nodes_with_connection_count(
    mock_neo4j_driver,
):
    """Overview should return nodes with connection_count field."""
    driver, session = mock_neo4j_driver

    # Mock node query result
    node_record = MagicMock()
    node_record.__getitem__ = lambda self, key: {
        "canonical_id": "entity_raffles",
        "name": "Stamford Raffles",
        "main_categories": ["General and Establishment"],
        "sub_category": "Colonial Administrator",
        "attributes": "{}",
        "connection_count": 5,
    }[key]
    node_record.get = lambda key, default=None: {
        "canonical_id": "entity_raffles",
        "name": "Stamford Raffles",
        "main_categories": ["General and Establishment"],
        "sub_category": "Colonial Administrator",
        "attributes": "{}",
        "connection_count": 5,
    }.get(key, default)

    # Mock edge query result
    edge_record = MagicMock()
    edge_record.__getitem__ = lambda self, key: {
        "source_id": "entity_raffles",
        "target_id": "entity_singapore",
        "rel_type": "GOVERNED",
    }[key]

    # First call returns nodes, second call returns edges
    node_result = MagicMock()
    node_result.__aiter__ = lambda self: aiter_records([node_record])

    edge_result = MagicMock()
    edge_result.__aiter__ = lambda self: aiter_records([edge_record])

    call_count = 0

    async def mock_run(query, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return node_result
        return edge_result

    session.run = mock_run

    from app.services.neo4j_service import Neo4jService

    service = Neo4jService()
    service._driver = driver

    result = await service.get_overview_graph()

    assert isinstance(result, GraphOverviewPayload)
    assert len(result.nodes) >= 1
    assert result.nodes[0].connection_count == 5
    assert result.nodes[0].name == "Stamford Raffles"


async def aiter_records(records):
    for r in records:
        yield r
```

**Step 2: Run test to verify it fails**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_graph_overview.py -v`
Expected: FAIL — `GraphOverviewPayload` not found, `get_overview_graph` not found

**Step 3: Add `GraphOverviewPayload` schema**

In `backend/app/models/schemas.py`, add after the existing `GraphPayload` class:

```python
class OverviewNode(BaseModel):
    """Node with connection count for overview visualization."""

    canonical_id: str
    name: str
    main_categories: list[str]
    sub_category: str | None = None
    connection_count: int = 0


class GraphOverviewPayload(BaseModel):
    """Full graph overview with connection counts for node sizing."""

    nodes: list[OverviewNode]
    edges: list[GraphEdge]
```

Update the import in `__init__` or wherever schemas are exported. Also add `GraphOverviewPayload` and `OverviewNode` to the test import.

**Step 4: Implement `get_overview_graph()` in `neo4j_service.py`**

Add this method to the `Neo4jService` class:

```python
async def get_overview_graph(self) -> GraphOverviewPayload:
    """Return all entities and relationships for the overview visualization.

    Each node includes a connection_count (number of relationships) so the
    frontend can size nodes proportionally.
    """
    from app.models.schemas import GraphOverviewPayload, OverviewNode

    nodes: list[OverviewNode] = []
    edges: list[GraphEdge] = []

    async with self.driver.session() as session:
        # Fetch all entities with their connection counts
        node_result = await session.run(
            """
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r:RELATED_TO]-()
            WITH e, count(r) AS connection_count
            RETURN e.canonical_id AS canonical_id,
                   e.name AS name,
                   coalesce(e.main_categories, []) AS main_categories,
                   e.sub_category AS sub_category,
                   connection_count
            ORDER BY connection_count DESC
            """
        )
        async for record in node_result:
            nodes.append(
                OverviewNode(
                    canonical_id=record["canonical_id"],
                    name=record["name"],
                    main_categories=list(record["main_categories"]),
                    sub_category=record.get("sub_category"),
                    connection_count=record["connection_count"],
                )
            )

        # Fetch all relationships
        edge_result = await session.run(
            """
            MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity)
            RETURN a.canonical_id AS source_id,
                   b.canonical_id AS target_id,
                   r.rel_type AS rel_type
            """
        )
        edge_idx = 0
        async for record in edge_result:
            edges.append(
                GraphEdge(
                    id=f"overview_edge_{edge_idx}",
                    source=record["source_id"],
                    target=record["target_id"],
                    type=record["rel_type"] or "RELATED_TO",
                    attributes={},
                    highlighted=False,
                )
            )
            edge_idx += 1

    logger.info(
        "Overview graph: %d nodes, %d edges", len(nodes), len(edges)
    )
    return GraphOverviewPayload(nodes=nodes, edges=edges)
```

**Step 5: Run test to verify it passes**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_graph_overview.py -v`
Expected: PASS

**Step 6: Run all backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All pass

**Step 7: Commit**

```bash
git add backend/app/models/schemas.py backend/app/services/neo4j_service.py backend/tests/test_graph_overview.py
git commit -m "feat: add get_overview_graph() Neo4j method with connection counts"
```

---

## Task 2: Backend — Add `GET /graph/overview` endpoint with caching

**Files:**
- Modify: `backend/app/routers/graph.py`
- Test: `backend/tests/test_graph_overview.py` (extend)

**Step 1: Add test for the endpoint**

Append to `backend/tests/test_graph_overview.py`:

```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_graph_overview_endpoint_returns_200():
    """GET /graph/overview should return 200 with nodes and edges."""
    mock_payload = GraphOverviewPayload(
        nodes=[
            OverviewNode(
                canonical_id="e1",
                name="Test Entity",
                main_categories=["General and Establishment"],
                connection_count=3,
            )
        ],
        edges=[],
    )
    with patch(
        "app.routers.graph.neo4j_service.get_overview_graph",
        new_callable=AsyncMock,
        return_value=mock_payload,
    ):
        response = client.get("/graph/overview")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["nodes"][0]["connection_count"] == 3
```

**Step 2: Run test to verify it fails**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_graph_overview.py::test_graph_overview_endpoint_returns_200 -v`
Expected: FAIL — 404 (endpoint doesn't exist yet)

**Step 3: Add the endpoint to `graph.py`**

In `backend/app/routers/graph.py`, add:

```python
import time

from app.models.schemas import GraphOverviewPayload

# In-memory cache for overview graph (changes infrequently)
_overview_cache: dict[str, tuple[float, GraphOverviewPayload]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


@router.get("/overview", response_model=GraphOverviewPayload)
async def graph_overview() -> GraphOverviewPayload:
    """Return all entities and relationships for the overview visualization.

    Cached in-memory for 5 minutes since the full graph changes infrequently.
    """
    cache_key = "overview"
    now = time.time()

    if cache_key in _overview_cache:
        cached_at, payload = _overview_cache[cache_key]
        if now - cached_at < _CACHE_TTL_SECONDS:
            return payload

    payload = await neo4j_service.get_overview_graph()
    _overview_cache[cache_key] = (now, payload)
    return payload
```

**Important:** Place this endpoint **BEFORE** the `/{entity_canonical_id}` endpoint in the file. Otherwise FastAPI will try to match `"overview"` as a `canonical_id` path parameter.

**Step 4: Run test to verify it passes**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_graph_overview.py -v`
Expected: PASS

**Step 5: Run all backend tests + lint**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v && ruff check app/`
Expected: All pass, lint clean

**Step 6: Commit**

```bash
git add backend/app/routers/graph.py backend/tests/test_graph_overview.py
git commit -m "feat: add GET /graph/overview endpoint with 5-minute cache"
```

---

## Task 3: Frontend — Install `cytoscape-fcose` and add category color constants

**Files:**
- Modify: `frontend/package.json` (via npm)
- Create: `frontend/src/constants/graphColors.ts`

**Step 1: Install fcose**

```bash
cd frontend && npm install cytoscape-fcose
```

**Step 2: Create the color constants file**

Create `frontend/src/constants/graphColors.ts`:

```typescript
/**
 * Category color map for the knowledge graph visualization.
 * Colors match the 5 MAIN_CATEGORIES from the Colonial Archives schema.
 */
export const CATEGORY_COLORS: Record<string, string> = {
  "General and Establishment": "#3B82F6",
  "Defence and Military": "#EF4444",
  "Economic and Financial": "#10B981",
  "Internal Relations and Research": "#8B5CF6",
  "Social Services": "#F59E0B",
};

/** Fallback color for nodes with unknown or multiple categories. */
export const DEFAULT_NODE_COLOR = "#6B7280";

/**
 * Get the display color for a node based on its first main_categories entry.
 */
export function getNodeColor(mainCategories: string[]): string {
  if (!mainCategories || mainCategories.length === 0) return DEFAULT_NODE_COLOR;
  return CATEGORY_COLORS[mainCategories[0]] ?? DEFAULT_NODE_COLOR;
}

/**
 * Threshold: only nodes with connection_count above this show labels by default.
 * Set dynamically in GraphCanvas based on the dataset.
 */
export const LABEL_VISIBILITY_PERCENTILE = 0.8; // top 20% show labels
```

**Step 3: Run frontend tests to ensure nothing breaks**

Run: `cd frontend && npx vitest run`
Expected: All 29 tests pass

**Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/constants/graphColors.ts
git commit -m "feat: install cytoscape-fcose, add category color constants"
```

---

## Task 4: Frontend — Add `getOverview()` to API client and types

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`

**Step 1: Add `OverviewNode` and `GraphOverviewPayload` types**

In `frontend/src/types/index.ts`, add after the existing `GraphPayload` interface:

```typescript
export interface OverviewNode {
  canonical_id: string;
  name: string;
  main_categories: string[];
  sub_category: string | null;
  connection_count: number;
}

export interface GraphOverviewPayload {
  nodes: OverviewNode[];
  edges: GraphEdge[];
}
```

**Step 2: Add `getOverview()` to the API client**

In `frontend/src/api/client.ts`, add to the `apiClient` object:

```typescript
getOverview(): Promise<GraphOverviewPayload> {
  return request<GraphOverviewPayload>(`${API_BASE}/graph/overview`, {
    method: "GET",
  });
},
```

Add `GraphOverviewPayload` to the imports from `../types`.

**Step 3: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

**Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add overview API types and client method"
```

---

## Task 5: Frontend — Add overview state to Zustand store

**Files:**
- Modify: `frontend/src/stores/useAppStore.ts`
- Modify: `frontend/src/stores/useAppStore.test.ts` (extend)

**Step 1: Add overview state and actions**

In `frontend/src/stores/useAppStore.ts`, add to the state interface and implementation:

```typescript
// New state fields:
overviewData: GraphOverviewPayload | null;
isOverviewMode: boolean;
hiddenCategories: Set<string>;

// New actions:
setOverviewData: (data: GraphOverviewPayload | null) => void;
setOverviewMode: (mode: boolean) => void;
toggleCategory: (category: string) => void;
```

Implementation in the `create` call:

```typescript
overviewData: null,
isOverviewMode: true,
hiddenCategories: new Set<string>(),

setOverviewData: (data) => set({ overviewData: data }),
setOverviewMode: (mode) => set({ isOverviewMode: mode }),
toggleCategory: (category) =>
  set((state) => {
    const next = new Set(state.hiddenCategories);
    if (next.has(category)) {
      next.delete(category);
    } else {
      next.add(category);
    }
    return { hiddenCategories: next };
  }),
```

Also update the query response handler: when a query returns graph data, switch out of overview mode:

```typescript
// In the sendMessage action, after setting graphData:
isOverviewMode: false,
```

**Step 2: Add a test for overview mode toggle**

In `frontend/src/stores/useAppStore.test.ts`, add:

```typescript
it("toggleCategory adds and removes categories", () => {
  const { toggleCategory } = useAppStore.getState();
  toggleCategory("Defence and Military");
  expect(useAppStore.getState().hiddenCategories.has("Defence and Military")).toBe(true);
  toggleCategory("Defence and Military");
  expect(useAppStore.getState().hiddenCategories.has("Defence and Military")).toBe(false);
});

it("setOverviewMode switches between overview and query mode", () => {
  const { setOverviewMode } = useAppStore.getState();
  setOverviewMode(true);
  expect(useAppStore.getState().isOverviewMode).toBe(true);
  setOverviewMode(false);
  expect(useAppStore.getState().isOverviewMode).toBe(false);
});
```

**Step 3: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

**Step 4: Commit**

```bash
git add frontend/src/stores/useAppStore.ts frontend/src/stores/useAppStore.test.ts
git commit -m "feat: add overview state, hiddenCategories, and mode toggle to store"
```

---

## Task 6: Frontend — Create `GraphLegend.tsx` component

**Files:**
- Create: `frontend/src/components/GraphLegend.tsx`

**Step 1: Create the legend component**

Create `frontend/src/components/GraphLegend.tsx`:

```tsx
import { CATEGORY_COLORS } from "../constants/graphColors";
import useAppStore from "../stores/useAppStore";

const categories = Object.entries(CATEGORY_COLORS);

export default function GraphLegend() {
  const hiddenCategories = useAppStore((s) => s.hiddenCategories);
  const toggleCategory = useAppStore((s) => s.toggleCategory);

  return (
    <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-stone-900/85 backdrop-blur-sm border border-stone-700/50 p-3 select-none">
      <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">
        Categories
      </h4>
      <ul className="space-y-1.5">
        {categories.map(([name, color]) => {
          const isHidden = hiddenCategories.has(name);
          return (
            <li key={name}>
              <button
                onClick={() => toggleCategory(name)}
                className={`flex items-center gap-2 text-xs transition-opacity w-full text-left ${
                  isHidden ? "opacity-30" : "opacity-100"
                } hover:opacity-80`}
              >
                <span
                  className="inline-block w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="text-stone-300 truncate">{name}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

**Step 2: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass (no tests for this pure UI component — tested via integration)

**Step 3: Commit**

```bash
git add frontend/src/components/GraphLegend.tsx
git commit -m "feat: add GraphLegend component with category color toggles"
```

---

## Task 7: Frontend — Rewrite `GraphCanvas.tsx` with fcose layout and two-state logic

This is the largest task. The component must:
1. Fetch overview on mount → render State 1 (clustered by category)
2. Listen for query `graphData` → animate to State 2 (filtered subgraph)
3. Support "Show Full Graph" reset
4. Apply category colors, node sizing, label threshold, hover tooltips
5. Respect `hiddenCategories` from the store

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx` (major rewrite)

**Step 1: Rewrite GraphCanvas.tsx**

Replace the contents of `frontend/src/components/GraphCanvas.tsx` with:

```tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { Core, EventObject } from "cytoscape";
// @ts-expect-error — cytoscape-fcose has no type definitions
import fcose from "cytoscape-fcose";

import { apiClient } from "../api/client";
import {
  CATEGORY_COLORS,
  DEFAULT_NODE_COLOR,
  LABEL_VISIBILITY_PERCENTILE,
} from "../constants/graphColors";
import useAppStore from "../stores/useAppStore";
import type { GraphOverviewPayload, OverviewNode } from "../types";

cytoscape.use(fcose);

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function nodeSize(connectionCount: number): number {
  return Math.max(12, Math.min(50, 8 + Math.sqrt(connectionCount) * 6));
}

function labelThreshold(nodes: OverviewNode[]): number {
  if (nodes.length === 0) return 0;
  const sorted = [...nodes]
    .map((n) => n.connection_count)
    .sort((a, b) => a - b);
  const idx = Math.floor(sorted.length * LABEL_VISIBILITY_PERCENTILE);
  return sorted[Math.min(idx, sorted.length - 1)];
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function GraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [overviewError, setOverviewError] = useState(false);

  // Store state
  const graphData = useAppStore((s) => s.graphData);
  const overviewData = useAppStore((s) => s.overviewData);
  const isOverviewMode = useAppStore((s) => s.isOverviewMode);
  const hiddenCategories = useAppStore((s) => s.hiddenCategories);
  const selectNode = useAppStore((s) => s.selectNode);
  const setOverviewData = useAppStore((s) => s.setOverviewData);
  const setOverviewMode = useAppStore((s) => s.setOverviewMode);
  const hasMessages = useAppStore((s) => s.messages.length > 0);

  // ---- Fetch overview on mount ----
  useEffect(() => {
    let cancelled = false;
    apiClient
      .getOverview()
      .then((data) => {
        if (!cancelled) setOverviewData(data);
      })
      .catch(() => {
        if (!cancelled) setOverviewError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- Determine which data to display ----
  const activeData = useMemo(() => {
    if (!isOverviewMode && graphData) {
      // Query mode — convert GraphPayload nodes to OverviewNode shape
      return {
        nodes: graphData.nodes.map((n) => ({
          canonical_id: n.canonical_id,
          name: n.name,
          main_categories: n.main_categories,
          sub_category: n.sub_category,
          connection_count: 1, // no connection_count in query data
        })),
        edges: graphData.edges,
      } satisfies GraphOverviewPayload;
    }
    return overviewData;
  }, [isOverviewMode, graphData, overviewData]);

  // ---- Compute label threshold ----
  const threshold = useMemo(
    () => (activeData ? labelThreshold(activeData.nodes) : 0),
    [activeData],
  );

  // ---- Build Cytoscape elements ----
  const elements = useMemo(() => {
    if (!activeData) return [];

    const nodeEls = activeData.nodes
      .filter(
        (n) =>
          !n.main_categories.length ||
          !n.main_categories.every((c) => hiddenCategories.has(c)),
      )
      .map((n) => ({
        data: {
          id: n.canonical_id,
          label: n.name,
          main_categories: n.main_categories[0] ?? "",
          sub_category: n.sub_category ?? "",
          connection_count: n.connection_count,
          size: nodeSize(n.connection_count),
        },
      }));

    const visibleIds = new Set(nodeEls.map((n) => n.data.id));

    const edgeEls = activeData.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
        },
      }));

    return [...nodeEls, ...edgeEls];
  }, [activeData, hiddenCategories]);

  // ---- Initialize Cytoscape ----
  useEffect(() => {
    if (!containerRef.current || elements.length === 0) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": ((ele: cytoscape.NodeSingular) => {
              const cat = ele.data("main_categories") as string;
              return CATEGORY_COLORS[cat] ?? DEFAULT_NODE_COLOR;
            }) as unknown as string,
            width: ((ele: cytoscape.NodeSingular) =>
              ele.data("size")) as unknown as number,
            height: ((ele: cytoscape.NodeSingular) =>
              ele.data("size")) as unknown as number,
            label: ((ele: cytoscape.NodeSingular) =>
              ele.data("connection_count") >= threshold
                ? ele.data("label")
                : "") as unknown as string,
            color: "#E5E7EB",
            "font-size": "10px",
            "font-family": "Plus Jakarta Sans, system-ui, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 5,
            "text-background-color": "#1C1917",
            "text-background-opacity": 0.7,
            "text-background-padding": "2px",
            "text-max-width": "100px",
            "text-wrap": "ellipsis",
            "border-width": 0,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#4B5563",
            opacity: 0.3,
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#4B5563",
            "arrow-scale": 0.5,
          },
        },
        {
          selector: "node:active",
          style: {
            "overlay-opacity": 0,
          },
        },
      ],
      layout: {
        name: "fcose",
        quality: elements.length > 300 ? "default" : "proof",
        randomize: true,
        animate: true,
        animationDuration: 800,
        fit: true,
        padding: 50,
        nodeSeparation: 80,
        idealEdgeLength: ((edge: cytoscape.EdgeSingular) => {
          const src = edge.source().data("main_categories");
          const tgt = edge.target().data("main_categories");
          return src === tgt ? 80 : 250;
        }) as unknown as number,
        nodeRepulsion: ((node: cytoscape.NodeSingular) => {
          return node.data("connection_count") > 5 ? 8000 : 4500;
        }) as unknown as number,
      } as cytoscape.LayoutOptions,
      minZoom: 0.2,
      maxZoom: 4,
      wheelSensitivity: 0.3,
    });

    // ---- Events ----
    cy.on("tap", "node", (evt: EventObject) => {
      const nodeData = evt.target.data();
      selectNode({
        canonical_id: nodeData.id,
        name: nodeData.label,
        main_categories: nodeData.main_categories
          ? [nodeData.main_categories]
          : [],
        sub_category: nodeData.sub_category || null,
        attributes: {},
        highlighted: true,
      });
    });

    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) selectNode(null);
    });

    // Hover: show label on mouseover
    cy.on("mouseover", "node", (evt: EventObject) => {
      const node = evt.target;
      node.style("label", node.data("label"));
      node.style("border-width", 2);
      node.style("border-color", "#d4ad6a");
      containerRef.current!.style.cursor = "pointer";
    });

    cy.on("mouseout", "node", (evt: EventObject) => {
      const node = evt.target;
      if (node.data("connection_count") < threshold) {
        node.style("label", "");
      }
      node.style("border-width", 0);
      containerRef.current!.style.cursor = "default";
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, threshold, selectNode]);

  // ---- Reset to overview ----
  const handleResetToOverview = useCallback(() => {
    setOverviewMode(true);
  }, [setOverviewMode]);

  // ---- Empty states ----
  if (!activeData && !overviewError) {
    return (
      <div className="flex h-full items-center justify-center bg-stone-900 text-stone-500">
        <div className="text-center animate-fade-in">
          <div className="text-4xl mb-3 text-ink-400 animate-subtle-pulse">
            &#9671;
          </div>
          <p className="text-sm">Loading knowledge graph...</p>
        </div>
      </div>
    );
  }

  if (overviewError && !activeData) {
    return (
      <div className="flex h-full items-center justify-center bg-stone-900 text-stone-500">
        <div className="text-center animate-fade-in">
          <p className="font-display text-lg text-stone-400 mb-2">
            Knowledge Graph
          </p>
          <p className="text-sm">
            {hasMessages
              ? "No entities found for this query."
              : "Ask a question or search for an entity to explore."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full bg-stone-900">
      {/* Cytoscape container */}
      <div ref={containerRef} className="h-full w-full" />

      {/* Reset button (visible in query mode) */}
      {!isOverviewMode && (
        <button
          onClick={handleResetToOverview}
          className="absolute top-3 right-3 z-10 rounded-md bg-stone-800/90 backdrop-blur-sm border border-stone-700/50 px-3 py-1.5 text-xs text-stone-300 hover:bg-stone-700 hover:text-stone-100 transition-colors"
        >
          Show Full Graph
        </button>
      )}
    </div>
  );
}
```

**Step 2: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

**Step 3: Run lint**

Run: `cd frontend && npx eslint src/`
Expected: Clean

**Step 4: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "feat: rewrite GraphCanvas with fcose layout, two-state view, category clusters"
```

---

## Task 8: Frontend — Wire GraphLegend into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Add GraphLegend to the graph panel**

In `frontend/src/App.tsx`, import and place `GraphLegend` in the graph container, alongside `GraphSearchBar` and `NodeSidebar`:

```tsx
import GraphLegend from "./components/GraphLegend";
```

Then in the graph panel `<div className="relative ...">`, add:

```tsx
<GraphSearchBar />
<GraphCanvas />
<GraphLegend />
<NodeSidebar />
```

Do the same in the mobile tab view for the graph panel.

**Step 2: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

**Step 3: Run lint**

Run: `cd frontend && npx eslint src/`
Expected: Clean

**Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire GraphLegend into App layout"
```

---

## Task 9: Integration testing and final polish

**Files:**
- All modified files (manual testing)

**Step 1: Run all backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All pass

**Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

**Step 3: Run all linters**

Run: `cd backend && ruff check app/ && cd ../frontend && npx eslint src/ && npx tsc -b`
Expected: All clean

**Step 4: Manual smoke test**

1. Start backend: `cd backend && uvicorn app.main:app --port 8090`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser → graph panel should show **full overview** with clustered categories
4. Hover over a node → label appears, gold border
5. Click a node → NodeSidebar opens with details
6. Click a category in the legend → that category's nodes toggle visibility
7. Type a question in chat → graph transitions to **filtered subgraph**
8. Click "Show Full Graph" → returns to overview
9. Search via GraphSearchBar → graph updates

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: knowledge graph visualization overhaul — overview + query states"
```

---

## Summary of All File Changes

| File | Action | Task |
|------|--------|------|
| `backend/app/models/schemas.py` | Add `OverviewNode`, `GraphOverviewPayload` | 1 |
| `backend/app/services/neo4j_service.py` | Add `get_overview_graph()` method | 1 |
| `backend/tests/test_graph_overview.py` | Create — tests for overview | 1, 2 |
| `backend/app/routers/graph.py` | Add `GET /graph/overview` with caching | 2 |
| `frontend/package.json` | Add `cytoscape-fcose` dependency | 3 |
| `frontend/src/constants/graphColors.ts` | Create — category colors + helpers | 3 |
| `frontend/src/types/index.ts` | Add `OverviewNode`, `GraphOverviewPayload` | 4 |
| `frontend/src/api/client.ts` | Add `getOverview()` method | 4 |
| `frontend/src/stores/useAppStore.ts` | Add `overviewData`, `isOverviewMode`, `hiddenCategories` | 5 |
| `frontend/src/stores/useAppStore.test.ts` | Add tests for new state | 5 |
| `frontend/src/components/GraphLegend.tsx` | Create — category legend with toggle | 6 |
| `frontend/src/components/GraphCanvas.tsx` | Major rewrite — fcose, two states, sizing | 7 |
| `frontend/src/App.tsx` | Wire in `GraphLegend` | 8 |

## Parallelism Guide

Tasks can be parallelized as follows:
- **Tasks 1–2** (backend) can run in **parallel** with **Tasks 3–4** (frontend types/deps)
- **Task 5** (store) depends on Task 4
- **Task 6** (legend) depends on Task 3 + 5
- **Task 7** (GraphCanvas rewrite) depends on Tasks 3, 4, 5
- **Task 8** (App wiring) depends on Tasks 6, 7
- **Task 9** (integration) depends on all

Suggested parallel groups:
1. **Group A** (backend agent): Tasks 1 → 2
2. **Group B** (frontend agent): Tasks 3 → 4 → 5 → 6
3. **Group C** (GraphCanvas agent): Task 7 (after Group B completes Tasks 3–5)
4. **Sequential**: Task 8 → 9
