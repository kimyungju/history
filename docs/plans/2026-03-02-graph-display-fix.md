# Graph Display Fix — Overview on Load + Node Spacing

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two bugs: (1) the full knowledge graph must display immediately when the site loads, and (2) nodes must not overlap — categories should form distinct spatial clusters with generous spacing.

**Architecture:** The GraphCanvas component already fetches overview data on mount and renders with cytoscape + fcose layout. The fix targets three areas: reliability of the initial load (error handling, container sizing race condition), dramatically better fcose layout parameters for proper node separation, and visual polish for a clear, readable graph.

**Tech Stack:** Cytoscape.js, cytoscape-fcose, React, Zustand, Tailwind CSS

---

### Task 1: Fix overview graph not appearing on initial page load

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx:54-68` (overview fetch)
- Modify: `frontend/src/components/GraphCanvas.tsx:131-207` (cytoscape init)

**Root cause analysis:** Two potential issues: (a) the overview API call may silently fail (network, CORS, Neo4j cold-start) with no retry, and (b) Cytoscape may initialize before the container has nonzero dimensions (race between React paint and effect).

**Step 1: Add retry logic and logging to overview fetch**

Replace the overview fetch useEffect (lines 55-68) with:

```tsx
// ---- Fetch overview on mount (with retry) ----
useEffect(() => {
  let cancelled = false;
  let retries = 0;
  const maxRetries = 2;

  const fetchOverview = () => {
    apiClient
      .getOverview()
      .then((data) => {
        if (!cancelled) {
          setOverviewData(data);
          setOverviewError(false);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn(`[GraphCanvas] Overview fetch failed (attempt ${retries + 1}):`, err);
        if (retries < maxRetries) {
          retries++;
          setTimeout(fetchOverview, 1500);
        } else {
          setOverviewError(true);
        }
      });
  };

  fetchOverview();
  return () => { cancelled = true; };
}, []); // eslint-disable-line react-hooks/exhaustive-deps
```

**Step 2: Guard Cytoscape init against zero-size container**

Before creating the cytoscape instance (line 135), add a dimension check and defer if needed:

```tsx
useEffect(() => {
  if (!containerRef.current || elements.length === 0) return;

  // Defer init if container has no dimensions yet (pre-paint)
  const rect = containerRef.current.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    const raf = requestAnimationFrame(() => {
      // Force a re-check by triggering a state update
      setForceRender((n) => n + 1);
    });
    return () => cancelAnimationFrame(raf);
  }

  const cy = cytoscape({ /* ... */ });
  // ...
```

Add `forceRender` state to the component:

```tsx
const [forceRender, setForceRender] = useState(0);
```

And add `forceRender` to the dependency array of the Cytoscape init useEffect.

**Step 3: Run and verify**

Run: `cd frontend && npm run dev`
Expected: Open browser → graph loads and displays within 2-3 seconds. Check browser console for any fetch errors.

**Step 4: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "fix: overview graph not appearing on initial page load"
```

---

### Task 2: Fix node overlap — dramatically improve fcose layout spacing

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx:186-203` (layout config)

**Problem:** Current fcose settings are too tight: `nodeSeparation: 80`, `nodeRepulsion: 4500-8000`, `idealEdgeLength: 80-250`. With hundreds of entities, nodes pile on top of each other. Categories don't form visible clusters.

**Step 1: Create separate layout configs for overview vs query mode**

Replace the single `layout` object with a function that returns different settings based on mode. The overview graph needs aggressive spacing while the query subgraph (10-30 nodes) can be tighter.

Replace the layout config in the cytoscape init (approximately lines 186-203) with:

```tsx
layout: {
  name: "fcose",
  quality: "proof",
  randomize: true,
  animate: true,
  animationDuration: isOverviewMode ? 1200 : 600,
  animationEasing: "ease-out-cubic",
  fit: true,
  padding: isOverviewMode ? 80 : 40,

  // --- Spacing (overview: galaxy spread / query: compact) ---
  nodeSeparation: isOverviewMode ? 250 : 100,
  idealEdgeLength: isOverviewMode
    ? ((edge: cytoscape.EdgeSingular) => {
        const src = edge.source().data("main_categories");
        const tgt = edge.target().data("main_categories");
        return src === tgt ? 180 : 450;
      }) as unknown as number
    : ((edge: cytoscape.EdgeSingular) => {
        const src = edge.source().data("main_categories");
        const tgt = edge.target().data("main_categories");
        return src === tgt ? 100 : 200;
      }) as unknown as number,
  nodeRepulsion: isOverviewMode
    ? ((node: cytoscape.NodeSingular) => {
        const cc = node.data("connection_count") ?? 0;
        return cc > 10 ? 80000 : cc > 3 ? 40000 : 20000;
      }) as unknown as number
    : ((node: cytoscape.NodeSingular) => {
        return node.data("connection_count") > 3 ? 10000 : 5000;
      }) as unknown as number,

  // --- Force simulation tuning ---
  gravity: isOverviewMode ? 0.08 : 0.25,
  gravityRange: isOverviewMode ? 8.0 : 3.8,
  nestingFactor: 0.1,
  edgeElasticity: isOverviewMode ? 0.1 : 0.45,
  numIter: isOverviewMode ? 5000 : 2500,
  tile: true,
  packComponents: true,
  samplingType: true,
} as cytoscape.LayoutOptions,
```

Key changes for overview mode:
- **nodeRepulsion: 20K–80K** (was 4.5K–8K) — pushes nodes far apart
- **idealEdgeLength: 180 same-cat / 450 cross-cat** (was 80/250) — stretches edges to create cluster spacing
- **gravity: 0.08** (was default ~0.25) — prevents nodes from collapsing to center
- **gravityRange: 8.0** — extends gravitational range for better clustering
- **edgeElasticity: 0.1** — weaker springs let repulsion dominate
- **numIter: 5000** — more iterations for better convergence
- **nodeSeparation: 250** (was 80) — minimum gap between nodes
- **padding: 80** — more breathing room at edges

**Step 2: Add isOverviewMode to Cytoscape init dependency**

Since layout config now depends on `isOverviewMode`, add it to the useEffect dependencies:

```tsx
}, [elements, threshold, selectNode, isOverviewMode]);
```

**Step 3: Run and verify**

Run: `cd frontend && npm run dev`
Expected: Overview graph has clear category clusters with no overlapping nodes. Cross-category edges stretch across visible gaps. Zooming out shows a "galaxy" of distinct clusters.

**Step 4: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "fix: dramatically increase node spacing to prevent overlap in overview graph"
```

---

### Task 3: Improve node sizing and label visibility for overview

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx:22-33` (nodeSize + labelThreshold)
- Modify: `frontend/src/components/GraphCanvas.tsx:138-165` (node style)

**Problem:** With hundreds of nodes, the current sizing (12–50px) makes most nodes tiny dots. Labels only show for top 20% — meaning 80% of nodes are anonymous colored dots with no identity.

**Step 1: Scale node sizes based on mode**

Update the `nodeSize` function and the elements mapping to use larger sizes in overview:

```tsx
function nodeSize(connectionCount: number, isOverview: boolean): number {
  if (isOverview) {
    // Overview: bigger nodes, more differentiation
    return Math.max(20, Math.min(70, 14 + Math.sqrt(connectionCount) * 8));
  }
  // Query mode: tighter range
  return Math.max(16, Math.min(50, 10 + Math.sqrt(connectionCount) * 6));
}
```

Update the elements builder to pass `isOverviewMode`:

```tsx
size: nodeSize(n.connection_count, isOverviewMode),
```

**Step 2: Show more labels in overview — top 40% instead of top 20%**

Add an overview-specific threshold calculation:

```tsx
const threshold = useMemo(() => {
  if (!activeData) return 0;
  const sorted = [...activeData.nodes]
    .map((n) => n.connection_count)
    .sort((a, b) => a - b);
  // Overview: show top 40% labels; query: top 60%
  const pct = isOverviewMode ? 0.6 : 0.4;
  const idx = Math.floor(sorted.length * pct);
  return sorted[Math.min(idx, sorted.length - 1)];
}, [activeData, isOverviewMode]);
```

**Step 3: Improve node border and glow for hub nodes**

Update the node style to give high-connection nodes a subtle glow ring:

```tsx
{
  selector: "node",
  style: {
    "background-color": ((ele: cytoscape.NodeSingular) => {
      const cat = ele.data("main_categories") as string;
      return CATEGORY_COLORS[cat] ?? DEFAULT_NODE_COLOR;
    }) as unknown as string,
    "background-opacity": 0.9,
    width: "data(size)",
    height: "data(size)",
    label: ((ele: cytoscape.NodeSingular) =>
      ele.data("connection_count") >= threshold
        ? ele.data("label")
        : "") as unknown as string,
    color: "#E5E7EB",
    "font-size": ((ele: cytoscape.NodeSingular) => {
      const cc = ele.data("connection_count") ?? 0;
      return cc > 10 ? 13 : cc > 3 ? 11 : 9;
    }) as unknown as string,
    "font-family": "Plus Jakarta Sans, system-ui, sans-serif",
    "text-valign": "bottom",
    "text-margin-y": 6,
    "text-background-color": "#1C1917",
    "text-background-opacity": 0.75,
    "text-background-padding": "3px",
    "text-max-width": "120px",
    "text-wrap": "ellipsis",
    "border-width": ((ele: cytoscape.NodeSingular) => {
      const cc = ele.data("connection_count") ?? 0;
      return cc > 8 ? 3 : cc > 3 ? 2 : 0;
    }) as unknown as number,
    "border-color": ((ele: cytoscape.NodeSingular) => {
      const cat = ele.data("main_categories") as string;
      return CATEGORY_COLORS[cat] ?? DEFAULT_NODE_COLOR;
    }) as unknown as string,
    "border-opacity": 0.3,
  },
},
```

**Step 4: Improve edge styling — thinner for overview, relationship-type opacity**

```tsx
{
  selector: "edge",
  style: {
    width: isOverviewMode ? 0.5 : 1.5,
    "line-color": "#4B5563",
    opacity: isOverviewMode ? 0.15 : 0.4,
    "curve-style": "bezier",
    "target-arrow-shape": "triangle",
    "target-arrow-color": "#4B5563",
    "arrow-scale": isOverviewMode ? 0.3 : 0.5,
  },
},
```

**Step 5: Run and verify**

Run: `cd frontend && npm run dev`
Expected: Overview graph has clearly visible nodes with proportional sizing. Hub entities have visible borders (glow effect). More labels visible. Edges are subtle in overview, more prominent in query view.

**Step 6: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "feat: improve node sizing, labels, and edge styling for graph readability"
```

---

### Task 4: Add smooth zoom-to-fit and initial viewport centering

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx` (cytoscape init, after layout)

**Problem:** After fcose layout completes, the viewport may not be optimally fitted — nodes may be partially offscreen or too small.

**Step 1: Add layout-done callback to fit viewport**

After creating the Cytoscape instance, add a layout event listener:

```tsx
const cy = cytoscape({ /* ... */ });

// After layout animation completes, smoothly fit to viewport
cy.one("layoutstop", () => {
  cy.animate({
    fit: { eles: cy.elements(), padding: isOverviewMode ? 60 : 30 },
    duration: 400,
    easing: "ease-in-out-cubic",
  });
});
```

**Step 2: Run and verify**

Run: `cd frontend && npm run dev`
Expected: After layout animation, graph smoothly fits to the viewport with appropriate padding. No nodes cut off at edges.

**Step 3: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "feat: smooth zoom-to-fit after graph layout completes"
```

---

### Task 5: Add loading skeleton and error retry UI

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx:259-288` (empty states)

**Problem:** The current loading state is a tiny diamond icon. The error state doesn't offer a retry button. For an archival research tool, these states should feel intentional and polished.

**Step 1: Replace loading state with an animated skeleton**

```tsx
if (!activeData && !overviewError) {
  return (
    <div className="flex h-full items-center justify-center bg-stone-900">
      <div className="text-center animate-fade-in">
        <div className="relative w-24 h-24 mx-auto mb-6">
          {/* Animated rings representing graph connections */}
          <div className="absolute inset-0 rounded-full border border-stone-700/40 animate-ping" style={{ animationDuration: "3s" }} />
          <div className="absolute inset-3 rounded-full border border-stone-600/30 animate-ping" style={{ animationDuration: "2.5s", animationDelay: "0.5s" }} />
          <div className="absolute inset-6 rounded-full border border-stone-500/20 animate-ping" style={{ animationDuration: "2s", animationDelay: "1s" }} />
          <div className="absolute inset-[2.25rem] rounded-full bg-ink-500/20" />
        </div>
        <p className="text-sm text-stone-400 font-display">Loading knowledge graph&hellip;</p>
        <p className="text-xs text-stone-600 mt-1">Connecting to archive database</p>
      </div>
    </div>
  );
}
```

**Step 2: Replace error state with retry button**

```tsx
if (overviewError && !activeData) {
  return (
    <div className="flex h-full items-center justify-center bg-stone-900">
      <div className="text-center animate-fade-in">
        <div className="text-3xl mb-3 text-stone-600">&#x26A0;</div>
        <p className="font-display text-base text-stone-300 mb-1">
          Could not load knowledge graph
        </p>
        <p className="text-xs text-stone-500 mb-4">
          The archive database may be waking up from sleep.
        </p>
        <button
          onClick={() => {
            setOverviewError(false);
            apiClient.getOverview().then(setOverviewData).catch(() => setOverviewError(true));
          }}
          className="px-4 py-2 text-sm rounded-md bg-stone-800 border border-stone-700 text-stone-300 hover:bg-stone-700 hover:text-stone-100 transition-colors"
        >
          Retry Connection
        </button>
      </div>
    </div>
  );
}
```

**Step 3: Run and verify**

Run: `cd frontend && npm run dev`
Expected: Loading shows animated concentric rings. Error shows warning with "Retry" button. Retry button re-fetches overview.

**Step 4: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "feat: polished loading skeleton and error retry for graph panel"
```

---

### Task 6: Final integration test — full flow verification

**Files:**
- Test: `frontend/src/stores/useAppStore.test.ts`

**Step 1: Run existing frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All 33 tests pass (existing tests should not break).

**Step 2: Manually verify the full flow**

1. Open site → overview graph loads with clear clusters, no overlap
2. Hover node → label appears, gold border highlight
3. Click legend category → those nodes hide/show
4. Ask a question in chat → graph switches to filtered query view
5. Click "Show Full Graph" → returns to overview with good spacing
6. Resize browser → graph re-fits

**Step 3: Commit all remaining changes**

```bash
git add frontend/
git commit -m "test: verify graph display fixes pass all existing tests"
```
