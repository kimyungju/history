# Node Source Document Link — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a user clicks a graph node, the sidebar shows the source document reference (doc_id + page) as a clickable link that opens the PDF viewer.

**Architecture:** Evidence data (doc_id, page, text_span, confidence) is already stored on every Neo4j Entity node but is dropped by `_record_to_graph_node()` before reaching the frontend. The fix threads evidence through: Neo4j → backend schemas → API responses → Cytoscape element data → NodeSidebar UI → existing PdfModal. No new endpoints needed — just plumbing existing data to the UI.

**Tech Stack:** FastAPI/Pydantic (backend schemas), Cytoscape.js (node data), React/Zustand (sidebar + PDF modal)

---

### Task 1: Add evidence fields to backend `GraphNode` schema

**Files:**
- Modify: `backend/app/models/schemas.py:61-67`

**Step 1: Add optional evidence fields to GraphNode**

In `backend/app/models/schemas.py`, add evidence fields to the `GraphNode` class:

```python
class GraphNode(BaseModel):
    canonical_id: str
    name: str
    main_categories: list[str]
    sub_category: str | None = None
    attributes: dict = {}
    highlighted: bool = False
    evidence_doc_id: str | None = None
    evidence_page: int | None = None
    evidence_text_span: str | None = None
    evidence_confidence: float | None = None
```

All fields are optional (`None` default) so existing callers that don't provide them still work.

**Step 2: Add evidence fields to OverviewNode**

In the same file, find `OverviewNode` and add:

```python
class OverviewNode(BaseModel):
    """Node with connection count for overview visualization."""
    canonical_id: str
    name: str
    main_categories: list[str]
    sub_category: str | None = None
    connection_count: int
    evidence_doc_id: str | None = None
    evidence_page: int | None = None
```

Overview nodes only need `doc_id` and `page` (not text_span/confidence — that's detail for the sidebar).

**Step 3: Run backend tests to verify nothing breaks**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All 54 tests pass. The new fields are optional so existing test fixtures work unchanged.

**Step 4: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: add evidence fields to GraphNode and OverviewNode schemas"
```

---

### Task 2: Thread evidence data through `_record_to_graph_node()` and Cypher queries

**Files:**
- Modify: `backend/app/services/neo4j_service.py:456-477` (`_record_to_graph_node`)
- Modify: `backend/app/services/neo4j_service.py:186-193` (`get_subgraph` center-node query)
- Modify: `backend/app/services/neo4j_service.py:400-411` (`get_overview_graph` node query)

**Step 1: Update `_record_to_graph_node` to extract evidence fields**

In `neo4j_service.py`, update the `_record_to_graph_node` static method (around line 456):

```python
@staticmethod
def _record_to_graph_node(
    node_record,
    highlighted: bool = False,
) -> GraphNode:
    """Convert a Neo4j node record to a GraphNode Pydantic model."""
    attrs = {}
    raw_attrs = node_record.get("attributes")
    if raw_attrs:
        try:
            attrs = json.loads(raw_attrs)
        except (json.JSONDecodeError, TypeError):
            pass

    return GraphNode(
        canonical_id=node_record.get("canonical_id", ""),
        name=node_record.get("name", ""),
        main_categories=list(node_record.get("main_categories", [])),
        sub_category=node_record.get("sub_category"),
        attributes=attrs,
        highlighted=highlighted,
        evidence_doc_id=node_record.get("evidence_doc_id"),
        evidence_page=node_record.get("evidence_page"),
        evidence_text_span=node_record.get("evidence_text_span"),
        evidence_confidence=node_record.get("evidence_confidence"),
    )
```

This works because the center-node query in `get_subgraph` already returns all node properties via `MATCH (center:Entity {...})` — the `center` record returned is the full Neo4j node object which contains `evidence_*` properties. When `_record_to_graph_node` calls `node_record.get("evidence_doc_id")`, it reads directly from the Neo4j node properties.

**Important**: The `get_subgraph` Cypher query on line 186 returns `center` as a raw Neo4j node (not individual fields), and the `neighbors` are also raw Neo4j nodes collected via `collect(DISTINCT neighbor)`. When `_record_to_graph_node` is called with these, accessing `node_record.get("evidence_doc_id")` reads the property directly from the Neo4j Node object. This already works — no query changes needed for subgraph.

**Step 2: Update `get_overview_graph` Cypher to return evidence fields**

The overview query returns individual fields (not raw nodes), so we need to add evidence columns. Update the Cypher in `get_overview_graph` (around line 400):

```python
node_result = await session.run(
    """
    MATCH (e:Entity)
    OPTIONAL MATCH (e)-[r:RELATED_TO]-()
    WITH e, count(r) AS connection_count
    RETURN e.canonical_id AS canonical_id,
           e.name AS name,
           coalesce(e.main_categories, []) AS main_categories,
           e.sub_category AS sub_category,
           connection_count,
           e.evidence_doc_id AS evidence_doc_id,
           e.evidence_page AS evidence_page
    ORDER BY connection_count DESC
    """
)
```

Then update the OverviewNode construction (around line 413):

```python
async for record in node_result:
    nodes.append(
        OverviewNode(
            canonical_id=record["canonical_id"],
            name=record["name"],
            main_categories=list(record["main_categories"]),
            sub_category=record.get("sub_category"),
            connection_count=record["connection_count"],
            evidence_doc_id=record.get("evidence_doc_id"),
            evidence_page=record.get("evidence_page"),
        )
    )
```

**Step 3: Run backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All 54 tests pass.

**Step 4: Commit**

```bash
git add backend/app/services/neo4j_service.py
git commit -m "feat: include evidence data in GraphNode and OverviewNode API responses"
```

---

### Task 3: Update frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts:30-65`

**Step 1: Add evidence fields to GraphNode TypeScript interface**

```typescript
export interface GraphNode {
  canonical_id: string;
  name: string;
  main_categories: string[];
  sub_category: string | null;
  attributes: Record<string, unknown>;
  highlighted: boolean;
  evidence_doc_id: string | null;
  evidence_page: number | null;
  evidence_text_span: string | null;
  evidence_confidence: number | null;
}
```

**Step 2: Add evidence fields to OverviewNode**

```typescript
export interface OverviewNode {
  canonical_id: string;
  name: string;
  main_categories: string[];
  sub_category: string | null;
  connection_count: number;
  evidence_doc_id: string | null;
  evidence_page: number | null;
}
```

**Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: Compiles cleanly. New fields are nullable so existing code that doesn't use them is fine.

**Step 4: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add evidence fields to GraphNode and OverviewNode types"
```

---

### Task 4: Pass evidence data through Cytoscape elements and selectNode handler

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx` (elements builder ~line 95-129, activeData mapping ~line 71-86, selectNode handler ~line 302-314)

**Step 1: Add evidence to Cytoscape element data**

In the `elements` useMemo (around line 95), add evidence fields to each node's `data`:

```tsx
.map((n) => ({
  data: {
    id: n.canonical_id,
    label: n.name,
    main_categories: n.main_categories[0] ?? "",
    sub_category: n.sub_category ?? "",
    connection_count: n.connection_count,
    size: nodeSize(n.connection_count, isOverviewMode),
    evidence_doc_id: n.evidence_doc_id ?? null,
    evidence_page: n.evidence_page ?? null,
  },
}));
```

**Step 2: Thread evidence through the activeData mapping for query mode**

In the `activeData` useMemo (around line 71), the query-mode branch maps `GraphNode` to `OverviewNode` shape. Add evidence fields:

```tsx
if (!isOverviewMode && graphData) {
  return {
    nodes: graphData.nodes.map((n) => ({
      canonical_id: n.canonical_id,
      name: n.name,
      main_categories: n.main_categories,
      sub_category: n.sub_category,
      connection_count: 1,
      evidence_doc_id: n.evidence_doc_id ?? null,
      evidence_page: n.evidence_page ?? null,
    })),
    edges: graphData.edges,
  } satisfies GraphOverviewPayload;
}
```

**Step 3: Update selectNode handler to include evidence**

In the `cy.on("tap", "node", ...)` handler (around line 302), pass evidence data:

```tsx
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
    evidence_doc_id: nodeData.evidence_doc_id ?? null,
    evidence_page: nodeData.evidence_page ?? null,
    evidence_text_span: null,
    evidence_confidence: null,
  });
});
```

Note: `evidence_text_span` and `evidence_confidence` are not stored on Cytoscape elements (they'd bloat the graph), but the type requires them — set to `null`. The sidebar will show doc_id + page which is sufficient for the link.

**Step 4: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: Compiles cleanly.

**Step 5: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "feat: thread evidence data through Cytoscape elements to selectNode"
```

---

### Task 5: Add source document link to NodeSidebar

**Files:**
- Modify: `frontend/src/components/NodeSidebar.tsx`

This is the core user-facing change. Add a "Source Document" section to the sidebar with a clickable link that opens the PDF viewer.

**Step 1: Wire up `openPdfModal` in the sidebar**

Add `openPdfModal` to the store selectors at the top of the component:

```tsx
const openPdfModal = useAppStore((s) => s.openPdfModal);
```

**Step 2: Add Source Document section to the sidebar body**

After the Attributes section (after the closing `)}` at line 78) and before the closing `</div>` of the body section at line 79, add:

```tsx
{selectedNode.evidence_doc_id && (
  <div>
    <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1.5">
      Source Document
    </h3>
    <button
      onClick={() =>
        openPdfModal(
          selectedNode.evidence_doc_id!,
          selectedNode.evidence_page ?? 1,
        )
      }
      className="flex items-center gap-2 w-full text-left group"
    >
      <div className="flex-shrink-0 w-8 h-8 bg-stone-800 rounded flex items-center justify-center">
        <svg
          className="w-4 h-4 text-ink-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
          />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-ink-400 group-hover:text-ink-300 transition-colors truncate">
          {selectedNode.evidence_doc_id}
        </p>
        {selectedNode.evidence_page != null && (
          <p className="text-xs text-stone-500">
            Page {selectedNode.evidence_page}
          </p>
        )}
      </div>
      <svg
        className="w-4 h-4 text-stone-600 group-hover:text-stone-400 transition-colors flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
    </button>
  </div>
)}
```

This renders:
- A document icon + doc_id text + page number + external-link arrow icon
- The whole row is a button — clicking opens the PdfModal at the exact page
- Uses existing ink-400 accent color + hover states
- Only shown when `evidence_doc_id` exists (won't show for nodes without source data)

**Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: Compiles cleanly.

**Step 4: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests pass.

**Step 5: Commit**

```bash
git add frontend/src/components/NodeSidebar.tsx
git commit -m "feat: show source document link in node sidebar with PDF viewer"
```

---

### Task 6: Final verification

**Step 1: Run all backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All 54 tests pass.

**Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests pass.

**Step 3: Manual flow verification**

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8090`
2. Start frontend: `cd frontend && npm run dev`
3. Wait for overview graph to load (may need to wake Neo4j first)
4. Click any node in the graph → sidebar opens
5. Verify "Source Document" section appears with doc_id and page
6. Click the source document link → PDF modal opens at correct page
7. Ask a question in chat → graph switches to query view
8. Click a query-result node → sidebar shows source document link
9. Click source link → PDF modal opens correctly
