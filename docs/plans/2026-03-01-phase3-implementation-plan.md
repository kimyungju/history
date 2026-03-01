# Phase 3: React Frontend — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the React frontend for Colonial Archives Graph-RAG — a two-panel SPA with Cytoscape.js knowledge graph visualization and a chat interface for archive queries.

**Architecture:** Monolithic SPA with CSS Grid layout (graph left 65%, chat right 35%). Zustand store manages all shared state. Components communicate through the store — no prop drilling. API calls go through a single fetch wrapper proxied via Vite dev server or nginx in production.

**Tech Stack:** React 18, TypeScript, Vite, TailwindCSS, Zustand, Cytoscape.js (react-cytoscapejs + cytoscape-cose-bilkent), pdfjs-dist, react-markdown, Vitest + @testing-library/react.

**Design doc:** `docs/plans/2026-03-01-phase3-react-frontend-design.md`

**Backend schemas:** `backend/app/models/schemas.py` — all TypeScript types must mirror these Pydantic models exactly.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `frontend/` — entire Vite project
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

**Step 1: Scaffold Vite project**

```bash
cd C:/NUS/Projects/history
npm create vite@latest frontend -- --template react-ts
```

**Step 2: Install dependencies**

```bash
cd C:/NUS/Projects/history/frontend
npm install zustand react-markdown cytoscape react-cytoscapejs cytoscape-cose-bilkent pdfjs-dist
npm install -D tailwindcss @tailwindcss/vite @types/cytoscape @types/react-cytoscapejs vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

**Step 3: Configure Tailwind**

Replace `frontend/src/index.css` with:

```css
@import "tailwindcss";
```

**Step 4: Configure Vite**

Replace `frontend/vite.config.ts` with:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
```

**Step 5: Create test setup file**

Create `frontend/src/test-setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

**Step 6: Create minimal App.tsx**

Replace `frontend/src/App.tsx` with:

```tsx
export default function App() {
  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 flex items-center justify-center">
      <p className="text-lg">Colonial Archives Graph-RAG</p>
    </div>
  );
}
```

**Step 7: Update main.tsx**

Replace `frontend/src/main.tsx` with:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

**Step 8: Verify dev server starts**

```bash
cd C:/NUS/Projects/history/frontend && npm run dev
```

Expected: Vite starts on http://localhost:5173, page shows "Colonial Archives Graph-RAG" on dark background with Tailwind styling applied.

**Step 9: Verify tests run**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run
```

Expected: Test suite runs (may have 0 tests, no errors).

**Step 10: Clean up scaffolding files**

Delete these Vite-generated files that we don't need:
- `frontend/src/App.css`
- `frontend/src/assets/react.svg`
- `frontend/public/vite.svg`

**Step 11: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold React 18 + Vite + Tailwind + Zustand + Cytoscape.js"
```

---

## Task 2: TypeScript Types

**Files:**
- Create: `frontend/src/types/index.ts`
- Test: `frontend/src/types/index.test.ts`

**Reference:** `backend/app/models/schemas.py` — mirror every Pydantic model used in API responses.

**Step 1: Write type definitions**

Create `frontend/src/types/index.ts`:

```typescript
// --- Request types ---

export interface QueryRequest {
  question: string;
  filter_categories?: string[] | null;
}

// --- Citation types (discriminated union on `type`) ---

export interface ArchiveCitation {
  type: "archive";
  id: number;
  doc_id: string;
  pages: number[];
  text_span: string;
  confidence: number;
}

export interface WebCitation {
  type: "web";
  id: number;
  title: string;
  url: string;
}

export type Citation = ArchiveCitation | WebCitation;

// --- Graph types ---

export interface GraphNode {
  canonical_id: string;
  name: string;
  main_categories: string[];
  sub_category: string | null;
  attributes: Record<string, unknown>;
  highlighted: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  attributes: Record<string, unknown>;
  highlighted: boolean;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
  center_node: string;
}

// --- Response types ---

export interface QueryResponse {
  answer: string;
  source_type: "archive" | "web_fallback" | "mixed";
  citations: Citation[];
  graph: GraphPayload | null;
}

export interface SignedUrlResponse {
  url: string;
  expires_in: number;
}

export interface OcrConfidenceWarning {
  page: number;
  confidence: number;
}

export interface IngestResponse {
  job_id: string;
  status: "processing" | "done" | "failed";
  pages_total: number;
  chunks_processed: number;
  entities_extracted: number;
  ocr_confidence_warnings: OcrConfidenceWarning[];
}

// --- Frontend-only types ---

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  graph?: GraphPayload | null;
}

// --- Constants ---

export const MAIN_CATEGORIES = [
  "Internal Relations and Research",
  "Economic and Financial",
  "Social Services",
  "Defence and Military",
  "General and Establishment",
] as const;

export type MainCategory = (typeof MAIN_CATEGORIES)[number];
```

**Step 2: Write compile-time type test**

Create `frontend/src/types/index.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import type {
  ArchiveCitation,
  WebCitation,
  Citation,
  GraphNode,
  GraphPayload,
  QueryResponse,
  ChatMessage,
} from "./index";
import { MAIN_CATEGORIES } from "./index";

describe("TypeScript types", () => {
  it("ArchiveCitation has correct shape", () => {
    const citation: ArchiveCitation = {
      type: "archive",
      id: 1,
      doc_id: "doc_042",
      pages: [3, 4],
      text_span: "The colonial administration...",
      confidence: 0.92,
    };
    expect(citation.type).toBe("archive");
    expect(citation.pages).toHaveLength(2);
  });

  it("WebCitation has correct shape", () => {
    const citation: WebCitation = {
      type: "web",
      id: 2,
      title: "Wikipedia: Straits Settlements",
      url: "https://en.wikipedia.org/wiki/Straits_Settlements",
    };
    expect(citation.type).toBe("web");
  });

  it("Citation discriminated union narrows on type", () => {
    const citation: Citation = {
      type: "archive",
      id: 1,
      doc_id: "doc_001",
      pages: [1],
      text_span: "...",
      confidence: 0.9,
    };
    if (citation.type === "archive") {
      expect(citation.doc_id).toBe("doc_001");
    }
  });

  it("GraphNode has all required fields", () => {
    const node: GraphNode = {
      canonical_id: "entity_123",
      name: "Straits Settlements",
      main_categories: ["General and Establishment"],
      sub_category: null,
      attributes: { founded: "1826" },
      highlighted: true,
    };
    expect(node.highlighted).toBe(true);
  });

  it("GraphPayload contains nodes, edges, center_node", () => {
    const payload: GraphPayload = {
      nodes: [],
      edges: [],
      center_node: "entity_123",
    };
    expect(payload.center_node).toBe("entity_123");
  });

  it("QueryResponse allows null graph", () => {
    const response: QueryResponse = {
      answer: "The answer is...",
      source_type: "archive",
      citations: [],
      graph: null,
    };
    expect(response.graph).toBeNull();
  });

  it("ChatMessage stores role and content", () => {
    const msg: ChatMessage = {
      role: "assistant",
      content: "Based on the archives...",
      citations: [],
      graph: null,
    };
    expect(msg.role).toBe("assistant");
  });

  it("MAIN_CATEGORIES has 5 entries", () => {
    expect(MAIN_CATEGORIES).toHaveLength(5);
  });
});
```

**Step 3: Run tests**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/types/index.test.ts
```

Expected: All 8 tests pass.

**Step 4: Commit**

```bash
git add frontend/src/types/
git commit -m "feat(frontend): add TypeScript types mirroring backend Pydantic schemas"
```

---

## Task 3: API Client

**Files:**
- Create: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

**Step 1: Write the API client test**

Create `frontend/src/api/client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "./client";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("apiClient", () => {
  it("postQuery sends POST with correct body", async () => {
    const mockResponse = {
      answer: "Test answer",
      source_type: "archive",
      citations: [],
      graph: null,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await apiClient.postQuery({
      question: "Who governed the Straits?",
    });

    expect(mockFetch).toHaveBeenCalledWith("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "Who governed the Straits?" }),
    });
    expect(result.answer).toBe("Test answer");
  });

  it("postQuery includes filter_categories when provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          answer: "",
          source_type: "archive",
          citations: [],
          graph: null,
        }),
    });

    await apiClient.postQuery({
      question: "Trade routes?",
      filter_categories: ["Economic and Financial"],
    });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.filter_categories).toEqual(["Economic and Financial"]);
  });

  it("getSignedUrl sends GET with query params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ url: "https://signed.url", expires_in: 900 }),
    });

    const result = await apiClient.getSignedUrl("doc_042", 5);

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/document/signed_url?doc_id=doc_042&page=5",
      expect.objectContaining({ method: "GET" })
    );
    expect(result.url).toBe("https://signed.url");
  });

  it("searchGraph sends GET with query params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await apiClient.searchGraph("Raffles", 10);

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/graph/search?q=Raffles&limit=10",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("searchGraph includes categories when provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await apiClient.searchGraph("Raffles", 20, ["Defence and Military"]);

    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("categories=Defence+and+Military");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Internal error" }),
    });

    await expect(apiClient.postQuery({ question: "test" })).rejects.toThrow(
      "API error 500"
    );
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/api/client.test.ts
```

Expected: FAIL — module `./client` not found.

**Step 3: Write the API client**

Create `frontend/src/api/client.ts`:

```typescript
import type {
  QueryRequest,
  QueryResponse,
  SignedUrlResponse,
  GraphNode,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      `API error ${res.status}: ${body.detail ?? res.statusText}`
    );
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  postQuery(req: QueryRequest): Promise<QueryResponse> {
    return request<QueryResponse>(`${BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  },

  getSignedUrl(docId: string, page: number): Promise<SignedUrlResponse> {
    return request<SignedUrlResponse>(
      `${BASE}/document/signed_url?doc_id=${encodeURIComponent(docId)}&page=${page}`,
      { method: "GET" }
    );
  },

  searchGraph(
    query: string,
    limit = 20,
    categories?: string[]
  ): Promise<GraphNode[]> {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    if (categories?.length) {
      categories.forEach((c) => params.append("categories", c));
    }
    return request<GraphNode[]>(`${BASE}/graph/search?${params}`, {
      method: "GET",
    });
  },
};
```

**Step 4: Run tests**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/api/client.test.ts
```

Expected: All 6 tests pass.

**Step 5: Commit**

```bash
git add frontend/src/api/
git commit -m "feat(frontend): add API client with fetch wrapper for query, signed URL, graph search"
```

---

## Task 4: Zustand Store

**Files:**
- Create: `frontend/src/stores/useAppStore.ts`
- Test: `frontend/src/stores/useAppStore.test.ts`

**Step 1: Write store tests**

Create `frontend/src/stores/useAppStore.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAppStore } from "./useAppStore";

// Reset store between tests
beforeEach(() => {
  useAppStore.setState({
    messages: [],
    isQuerying: false,
    queryError: null,
    filterCategories: [],
    graphData: null,
    selectedNode: null,
    splitRatio: 0.65,
    isSidebarOpen: false,
    isPdfModalOpen: false,
    pdfModalProps: null,
    chatInput: "",
  });
});

describe("useAppStore", () => {
  it("has correct initial state", () => {
    const state = useAppStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.isQuerying).toBe(false);
    expect(state.splitRatio).toBe(0.65);
    expect(state.graphData).toBeNull();
    expect(state.filterCategories).toEqual([]);
  });

  it("selectNode opens sidebar", () => {
    const node = {
      canonical_id: "e1",
      name: "Raffles",
      main_categories: ["General and Establishment"],
      sub_category: null,
      attributes: {},
      highlighted: false,
    };
    useAppStore.getState().selectNode(node);
    const state = useAppStore.getState();
    expect(state.selectedNode).toEqual(node);
    expect(state.isSidebarOpen).toBe(true);
  });

  it("selectNode(null) closes sidebar", () => {
    useAppStore.getState().selectNode(null);
    const state = useAppStore.getState();
    expect(state.selectedNode).toBeNull();
    expect(state.isSidebarOpen).toBe(false);
  });

  it("openPdfModal sets modal props", () => {
    useAppStore.getState().openPdfModal("doc_042", 5);
    const state = useAppStore.getState();
    expect(state.isPdfModalOpen).toBe(true);
    expect(state.pdfModalProps).toEqual({ docId: "doc_042", page: 5 });
  });

  it("closePdfModal clears modal", () => {
    useAppStore.getState().openPdfModal("doc_042", 5);
    useAppStore.getState().closePdfModal();
    const state = useAppStore.getState();
    expect(state.isPdfModalOpen).toBe(false);
    expect(state.pdfModalProps).toBeNull();
  });

  it("setSplitRatio clamps between 0.3 and 0.7", () => {
    useAppStore.getState().setSplitRatio(0.1);
    expect(useAppStore.getState().splitRatio).toBe(0.3);

    useAppStore.getState().setSplitRatio(0.9);
    expect(useAppStore.getState().splitRatio).toBe(0.7);

    useAppStore.getState().setSplitRatio(0.5);
    expect(useAppStore.getState().splitRatio).toBe(0.5);
  });

  it("setFilterCategories replaces categories", () => {
    useAppStore
      .getState()
      .setFilterCategories(["Economic and Financial", "Social Services"]);
    expect(useAppStore.getState().filterCategories).toEqual([
      "Economic and Financial",
      "Social Services",
    ]);
  });

  it("setChatInput updates input text", () => {
    useAppStore.getState().setChatInput("Tell me about Raffles");
    expect(useAppStore.getState().chatInput).toBe("Tell me about Raffles");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/stores/useAppStore.test.ts
```

Expected: FAIL — module `./useAppStore` not found.

**Step 3: Write the store**

Create `frontend/src/stores/useAppStore.ts`:

```typescript
import { create } from "zustand";
import type {
  ChatMessage,
  GraphPayload,
  GraphNode,
  Citation,
} from "../types";
import { apiClient } from "../api/client";

interface AppState {
  // Chat
  messages: ChatMessage[];
  isQuerying: boolean;
  queryError: string | null;
  filterCategories: string[];
  chatInput: string;

  // Graph
  graphData: GraphPayload | null;
  selectedNode: GraphNode | null;

  // UI
  splitRatio: number;
  isSidebarOpen: boolean;
  isPdfModalOpen: boolean;
  pdfModalProps: { docId: string; page: number } | null;

  // Actions
  sendQuery: (question: string) => Promise<void>;
  selectNode: (node: GraphNode | null) => void;
  openPdfModal: (docId: string, page: number) => void;
  closePdfModal: () => void;
  setSplitRatio: (ratio: number) => void;
  setFilterCategories: (cats: string[]) => void;
  setChatInput: (text: string) => void;
  setGraphData: (data: GraphPayload | null) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  messages: [],
  isQuerying: false,
  queryError: null,
  filterCategories: [],
  chatInput: "",
  graphData: null,
  selectedNode: null,
  splitRatio: 0.65,
  isSidebarOpen: false,
  isPdfModalOpen: false,
  pdfModalProps: null,

  // Actions
  async sendQuery(question: string) {
    const { filterCategories } = get();
    const userMsg: ChatMessage = { role: "user", content: question };

    set({ isQuerying: true, queryError: null, messages: [...get().messages, userMsg] });

    try {
      const response = await apiClient.postQuery({
        question,
        filter_categories: filterCategories.length > 0 ? filterCategories : null,
      });

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        graph: response.graph,
      };

      set({
        messages: [...get().messages, assistantMsg],
        graphData: response.graph ?? get().graphData,
        isQuerying: false,
      });
    } catch (err) {
      set({
        queryError: err instanceof Error ? err.message : "Query failed",
        isQuerying: false,
      });
    }
  },

  selectNode(node: GraphNode | null) {
    set({
      selectedNode: node,
      isSidebarOpen: node !== null,
    });
  },

  openPdfModal(docId: string, page: number) {
    set({ isPdfModalOpen: true, pdfModalProps: { docId, page } });
  },

  closePdfModal() {
    set({ isPdfModalOpen: false, pdfModalProps: null });
  },

  setSplitRatio(ratio: number) {
    const clamped = Math.min(0.7, Math.max(0.3, ratio));
    set({ splitRatio: clamped });
    try {
      localStorage.setItem("splitRatio", String(clamped));
    } catch {
      // localStorage may be unavailable
    }
  },

  setFilterCategories(cats: string[]) {
    set({ filterCategories: cats });
  },

  setChatInput(text: string) {
    set({ chatInput: text });
  },

  setGraphData(data: GraphPayload | null) {
    set({ graphData: data });
  },
}));

// Restore split ratio from localStorage on load
try {
  const stored = localStorage.getItem("splitRatio");
  if (stored) {
    const ratio = parseFloat(stored);
    if (!isNaN(ratio)) {
      useAppStore.setState({ splitRatio: Math.min(0.7, Math.max(0.3, ratio)) });
    }
  }
} catch {
  // ignore
}
```

**Step 4: Run tests**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/stores/useAppStore.test.ts
```

Expected: All 8 tests pass.

**Step 5: Commit**

```bash
git add frontend/src/stores/
git commit -m "feat(frontend): add Zustand store with chat, graph, and UI state management"
```

---

## Task 5: App Layout Shell

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Write the layout shell**

Replace `frontend/src/App.tsx` with:

```tsx
import { useAppStore } from "./stores/useAppStore";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 overflow-hidden">
      <div
        className="h-full grid"
        style={{
          gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
        }}
      >
        {/* Graph panel — placeholder */}
        <div className="relative overflow-hidden bg-gray-900 flex items-center justify-center">
          <p className="text-gray-500">Graph Canvas</p>
        </div>

        {/* Splitter — placeholder */}
        <div className="bg-gray-700 cursor-col-resize hover:bg-blue-500 transition-colors" />

        {/* Chat panel — placeholder */}
        <div className="flex flex-col bg-gray-950">
          <p className="text-gray-500 m-auto">Chat Panel</p>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Verify in browser**

```bash
cd C:/NUS/Projects/history/frontend && npm run dev
```

Expected: Two panels visible — "Graph Canvas" on left (65%), "Chat Panel" on right (35%), with a thin gray divider between them.

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): add App layout shell with CSS Grid two-panel split"
```

---

## Task 6: ResizableSplitter

**Files:**
- Create: `frontend/src/components/ResizableSplitter.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write the ResizableSplitter component**

Create `frontend/src/components/ResizableSplitter.tsx`:

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

  return (
    <div
      className="bg-gray-700 cursor-col-resize hover:bg-blue-500 active:bg-blue-400 transition-colors"
      onMouseDown={onMouseDown}
      role="separator"
      aria-orientation="vertical"
    />
  );
}
```

**Step 2: Wire into App.tsx**

Replace the splitter placeholder in `frontend/src/App.tsx`:

```tsx
import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 overflow-hidden">
      <div
        className="h-full grid"
        style={{
          gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
        }}
      >
        {/* Graph panel — placeholder */}
        <div className="relative overflow-hidden bg-gray-900 flex items-center justify-center">
          <p className="text-gray-500">Graph Canvas</p>
        </div>

        <ResizableSplitter />

        {/* Chat panel — placeholder */}
        <div className="flex flex-col bg-gray-950">
          <p className="text-gray-500 m-auto">Chat Panel</p>
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Verify in browser**

```bash
cd C:/NUS/Projects/history/frontend && npm run dev
```

Expected: Drag the divider bar left/right — panels resize. Min 30%, max 70%. Ratio persists on page reload (check localStorage for `splitRatio` key).

**Step 4: Commit**

```bash
git add frontend/src/components/ResizableSplitter.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add ResizableSplitter with drag, min/max constraints, localStorage persistence"
```

---

## Task 7: Citation Parsing Utility

**Files:**
- Create: `frontend/src/utils/parseCitations.ts`
- Test: `frontend/src/utils/parseCitations.test.ts`

This is a pure function that parses `[archive:N]` and `[web:N]` markers from answer text into structured segments. The CitationBadge component will use these segments to render inline badges.

**Step 1: Write the test**

Create `frontend/src/utils/parseCitations.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { parseCitations } from "./parseCitations";
import type { Citation } from "../types";

const citations: Citation[] = [
  {
    type: "archive",
    id: 1,
    doc_id: "doc_042",
    pages: [3],
    text_span: "The colonial government...",
    confidence: 0.92,
  },
  {
    type: "web",
    id: 2,
    title: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Straits",
  },
];

describe("parseCitations", () => {
  it("returns plain text when no markers present", () => {
    const result = parseCitations("Hello world", []);
    expect(result).toEqual([{ type: "text", content: "Hello world" }]);
  });

  it("parses a single archive marker", () => {
    const result = parseCitations(
      "The governor arrived [archive:1] in 1819.",
      citations
    );
    expect(result).toEqual([
      { type: "text", content: "The governor arrived " },
      { type: "citation", citation: citations[0] },
      { type: "text", content: " in 1819." },
    ]);
  });

  it("parses a web marker", () => {
    const result = parseCitations("See also [web:2].", citations);
    expect(result).toEqual([
      { type: "text", content: "See also " },
      { type: "citation", citation: citations[1] },
      { type: "text", content: "." },
    ]);
  });

  it("parses multiple markers", () => {
    const result = parseCitations(
      "Fact [archive:1] and source [web:2].",
      citations
    );
    expect(result).toHaveLength(5);
    expect(result[1]).toEqual({ type: "citation", citation: citations[0] });
    expect(result[3]).toEqual({ type: "citation", citation: citations[1] });
  });

  it("leaves unmatched markers as plain text", () => {
    const result = parseCitations("Unknown [archive:99] ref.", citations);
    expect(result).toEqual([
      { type: "text", content: "Unknown [archive:99] ref." },
    ]);
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/utils/parseCitations.test.ts
```

Expected: FAIL — module not found.

**Step 3: Write the parser**

Create `frontend/src/utils/parseCitations.ts`:

```typescript
import type { Citation } from "../types";

export type TextSegment = { type: "text"; content: string };
export type CitationSegment = { type: "citation"; citation: Citation };
export type ParsedSegment = TextSegment | CitationSegment;

const CITATION_RE = /\[(archive|web):(\d+)\]/g;

export function parseCitations(
  text: string,
  citations: Citation[]
): ParsedSegment[] {
  const citationMap = new Map<string, Citation>();
  for (const c of citations) {
    citationMap.set(`${c.type}:${c.id}`, c);
  }

  const segments: ParsedSegment[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(CITATION_RE)) {
    const key = `${match[1]}:${match[2]}`;
    const citation = citationMap.get(key);

    if (!citation) continue; // unmatched marker — skip

    if (match.index > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    segments.push({ type: "citation", citation });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }

  if (segments.length === 0) {
    return [{ type: "text", content: text }];
  }

  return segments;
}
```

**Step 4: Run tests**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run src/utils/parseCitations.test.ts
```

Expected: All 5 tests pass.

**Step 5: Commit**

```bash
git add frontend/src/utils/
git commit -m "feat(frontend): add citation parser for [archive:N] and [web:N] inline markers"
```

---

## Task 8: CitationBadge Component

**Files:**
- Create: `frontend/src/components/CitationBadge.tsx`

**Step 1: Write the component**

Create `frontend/src/components/CitationBadge.tsx`:

```tsx
import type { Citation } from "../types";
import { useAppStore } from "../stores/useAppStore";

interface Props {
  citation: Citation;
}

export default function CitationBadge({ citation }: Props) {
  const openPdfModal = useAppStore((s) => s.openPdfModal);

  if (citation.type === "archive") {
    return (
      <button
        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors cursor-pointer"
        title={citation.text_span}
        onClick={() => openPdfModal(citation.doc_id, citation.pages[0])}
      >
        {citation.doc_id}:p{citation.pages.join(",")}
      </button>
    );
  }

  // Web citation
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
      title={citation.title}
    >
      {citation.title}
    </a>
  );
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd C:/NUS/Projects/history/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add frontend/src/components/CitationBadge.tsx
git commit -m "feat(frontend): add CitationBadge component (archive=blue, web=green)"
```

---

## Task 9: ChatMessage Component

**Files:**
- Create: `frontend/src/components/ChatMessage.tsx`

**Step 1: Write the component**

Create `frontend/src/components/ChatMessage.tsx`:

```tsx
import Markdown from "react-markdown";
import type { ChatMessage as ChatMessageType } from "../types";
import { parseCitations } from "../utils/parseCitations";
import CitationBadge from "./CitationBadge";

interface Props {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="bg-blue-600 rounded-2xl rounded-br-sm px-4 py-2 max-w-[85%]">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant message — parse citation markers
  const segments = parseCitations(message.content, message.citations ?? []);

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
      </div>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd C:/NUS/Projects/history/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add frontend/src/components/ChatMessage.tsx
git commit -m "feat(frontend): add ChatMessage component with markdown and inline citation badges"
```

---

## Task 10: ChatPanel Component

**Files:**
- Create: `frontend/src/components/ChatPanel.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write ChatPanel**

Create `frontend/src/components/ChatPanel.tsx`:

```tsx
import { useRef, useEffect } from "react";
import { useAppStore } from "../stores/useAppStore";
import ChatMessage from "./ChatMessage";

export default function ChatPanel() {
  const messages = useAppStore((s) => s.messages);
  const isQuerying = useAppStore((s) => s.isQuerying);
  const queryError = useAppStore((s) => s.queryError);
  const chatInput = useAppStore((s) => s.chatInput);
  const setChatInput = useAppStore((s) => s.setChatInput);
  const sendQuery = useAppStore((s) => s.sendQuery);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, isQuerying]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = chatInput.trim();
    if (!trimmed || isQuerying) return;
    setChatInput("");
    sendQuery(trimmed);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm text-center">
              Ask a question about the colonial archives
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isQuerying && (
          <div className="flex justify-start mb-3">
            <div className="bg-gray-800 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        {queryError && (
          <div className="mb-3 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm">{queryError}</p>
            <button
              className="text-red-400 text-xs underline mt-1"
              onClick={() => {
                const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
                if (lastUserMsg) sendQuery(lastUserMsg.content);
              }}
            >
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="border-t border-gray-800 px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask about the archives..."
            className="flex-1 bg-gray-800 text-gray-100 rounded-lg px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-gray-500"
            disabled={isQuerying}
          />
          <button
            type="submit"
            disabled={isQuerying || !chatInput.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
```

**Step 2: Wire ChatPanel into App.tsx**

Replace the chat placeholder in `frontend/src/App.tsx`:

```tsx
import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 overflow-hidden">
      <div
        className="h-full grid"
        style={{
          gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
        }}
      >
        {/* Graph panel — placeholder */}
        <div className="relative overflow-hidden bg-gray-900 flex items-center justify-center">
          <p className="text-gray-500">Graph Canvas</p>
        </div>

        <ResizableSplitter />

        <ChatPanel />
      </div>
    </div>
  );
}
```

**Step 3: Verify in browser**

```bash
cd C:/NUS/Projects/history/frontend && npm run dev
```

Expected: Right panel shows empty state message "Ask a question about the colonial archives", input bar at bottom with "Send" button. Typing in the input and pressing Send appends a user message bubble (blue, right-aligned). The query will fail (no backend) but the error state should appear with a red error message and retry button.

**Step 4: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add ChatPanel with messages, loading dots, error state, and input bar"
```

---

## Task 11: CategoryFilter Component

**Files:**
- Create: `frontend/src/components/CategoryFilter.tsx`
- Modify: `frontend/src/components/ChatPanel.tsx`

**Step 1: Write CategoryFilter**

Create `frontend/src/components/CategoryFilter.tsx`:

```tsx
import { useAppStore } from "../stores/useAppStore";
import { MAIN_CATEGORIES } from "../types";

export default function CategoryFilter() {
  const filterCategories = useAppStore((s) => s.filterCategories);
  const setFilterCategories = useAppStore((s) => s.setFilterCategories);

  const toggle = (cat: string) => {
    if (filterCategories.includes(cat)) {
      setFilterCategories(filterCategories.filter((c) => c !== cat));
    } else {
      setFilterCategories([...filterCategories, cat]);
    }
  };

  return (
    <div className="flex flex-wrap gap-1.5 px-4 py-2 border-b border-gray-800">
      {MAIN_CATEGORIES.map((cat) => {
        const active = filterCategories.includes(cat);
        return (
          <button
            key={cat}
            onClick={() => toggle(cat)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              active
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
}
```

**Step 2: Add CategoryFilter above the chat input in ChatPanel**

In `frontend/src/components/ChatPanel.tsx`, add the import and render CategoryFilter above the form:

Add import at top:
```typescript
import CategoryFilter from "./CategoryFilter";
```

Render it just above the `<form>` tag:
```tsx
      <CategoryFilter />

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="border-t border-gray-800 px-4 py-3">
```

**Step 3: Verify in browser**

Expected: 5 category pills appear above the input bar. Clicking toggles them blue (active) / gray (inactive). Multiple can be selected.

**Step 4: Commit**

```bash
git add frontend/src/components/CategoryFilter.tsx frontend/src/components/ChatPanel.tsx
git commit -m "feat(frontend): add CategoryFilter pill bar for filtering queries by archive category"
```

---

## Task 12: GraphCanvas Component

**Files:**
- Create: `frontend/src/components/GraphCanvas.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write GraphCanvas**

Create `frontend/src/components/GraphCanvas.tsx`:

```tsx
import { useRef, useCallback, useMemo, useEffect } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import Cytoscape from "cytoscape";
import { useAppStore } from "../stores/useAppStore";

// Register layout extension once
Cytoscape.use(coseBilkent);

const CATEGORY_COLORS: Record<string, string> = {
  "Internal Relations and Research": "#8B5CF6", // violet
  "Economic and Financial": "#F59E0B",          // amber
  "Social Services": "#10B981",                  // emerald
  "Defence and Military": "#EF4444",             // red
  "General and Establishment": "#3B82F6",        // blue
};

const DEFAULT_COLOR = "#6B7280"; // gray

function getCategoryColor(categories: string[]): string {
  if (categories.length === 0) return DEFAULT_COLOR;
  return CATEGORY_COLORS[categories[0]] ?? DEFAULT_COLOR;
}

export default function GraphCanvas() {
  const graphData = useAppStore((s) => s.graphData);
  const selectNode = useAppStore((s) => s.selectNode);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const elements = useMemo(() => {
    if (!graphData) return [];

    const nodes = graphData.nodes.map((n) => ({
      data: {
        id: n.canonical_id,
        label: n.name.length > 20 ? n.name.slice(0, 18) + "..." : n.name,
        fullName: n.name,
        ...n,
        color: getCategoryColor(n.main_categories),
      },
    }));

    const edges = graphData.edges.map((e) => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.type.replace(/_/g, " "),
        ...e,
      },
    }));

    return [...nodes, ...edges];
  }, [graphData]);

  const stylesheet: cytoscape.Stylesheet[] = useMemo(
    () => [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "background-color": "data(color)",
          "text-valign": "bottom",
          "text-halign": "center",
          "font-size": "10px",
          color: "#E5E7EB",
          "text-margin-y": 6,
          width: 40,
          height: 40,
          shape: "round-rectangle",
          "border-width": 2,
          "border-color": "data(color)",
        } as cytoscape.Css.Node,
      },
      {
        selector: "node[?highlighted]",
        style: {
          "border-color": "#F97316",
          "border-width": 4,
          "background-color": "data(color)",
        } as cytoscape.Css.Node,
      },
      {
        selector: "node:active",
        style: {
          "overlay-opacity": 0.1,
        } as cytoscape.Css.Node,
      },
      {
        selector: "edge",
        style: {
          label: "data(label)",
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.8,
          "line-color": "#4B5563",
          "target-arrow-color": "#4B5563",
          "font-size": "8px",
          color: "#9CA3AF",
          "text-rotation": "autorotate",
          width: 1.5,
        } as cytoscape.Css.Edge,
      },
      {
        selector: "edge[?highlighted]",
        style: {
          "line-color": "#F97316",
          "target-arrow-color": "#F97316",
          width: 3,
        } as cytoscape.Css.Edge,
      },
    ],
    []
  );

  const handleCyInit = useCallback(
    (cy: cytoscape.Core) => {
      cyRef.current = cy;

      cy.on("tap", "node", (evt) => {
        const nodeData = evt.target.data();
        selectNode({
          canonical_id: nodeData.canonical_id,
          name: nodeData.fullName ?? nodeData.name,
          main_categories: nodeData.main_categories ?? [],
          sub_category: nodeData.sub_category ?? null,
          attributes: nodeData.attributes ?? {},
          highlighted: nodeData.highlighted ?? false,
        });
      });

      cy.on("tap", (evt) => {
        if (evt.target === cy) {
          selectNode(null);
        }
      });
    },
    [selectNode]
  );

  // Animate camera to highlighted nodes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !graphData) return;

    const highlighted = cy.nodes("[?highlighted]");
    if (highlighted.length > 0) {
      // Dim non-highlighted elements
      cy.elements().style("opacity", 0.4);
      highlighted.style("opacity", 1);
      highlighted.connectedEdges().style("opacity", 1);
      highlighted.connectedEdges().targets().style("opacity", 1);
      highlighted.connectedEdges().sources().style("opacity", 1);

      cy.animate({
        fit: { eles: highlighted, padding: 60 },
        duration: 800,
        easing: "ease-out-cubic",
      });
    } else {
      cy.elements().style("opacity", 1);
      cy.fit(undefined, 40);
    }
  }, [graphData]);

  if (!graphData) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500 text-sm text-center px-8">
          Ask a question or search for an entity to see the knowledge graph
        </p>
      </div>
    );
  }

  return (
    <CytoscapeComponent
      elements={elements}
      stylesheet={stylesheet}
      layout={{
        name: "cose-bilkent",
        animate: true,
        animationDuration: 600,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 120,
        nodeRepulsion: 6000,
        gravity: 0.25,
      } as any}
      cy={handleCyInit}
      className="w-full h-full"
      style={{ width: "100%", height: "100%" }}
    />
  );
}
```

**Step 2: Wire into App.tsx**

Replace the graph placeholder in `frontend/src/App.tsx`:

```tsx
import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

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
          <GraphCanvas />
        </div>

        <ResizableSplitter />

        <ChatPanel />
      </div>
    </div>
  );
}
```

**Step 3: Verify in browser**

Expected: Left panel shows empty state text "Ask a question or search for an entity...". When graphData is set (can test via browser console: `useAppStore.getState().setGraphData(...)`) nodes render with Cytoscape.js.

**Step 4: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add GraphCanvas with Cytoscape.js, cose-bilkent layout, highlight animation"
```

---

## Task 13: GraphSearchBar + useGraphSearch Hook

**Files:**
- Create: `frontend/src/hooks/useGraphSearch.ts`
- Create: `frontend/src/components/GraphSearchBar.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write the useGraphSearch hook**

Create `frontend/src/hooks/useGraphSearch.ts`:

```typescript
import { useState, useRef, useCallback } from "react";
import { apiClient } from "../api/client";
import { useAppStore } from "../stores/useAppStore";

export function useGraphSearch() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const filterCategories = useAppStore((s) => s.filterCategories);
  const setGraphData = useAppStore((s) => s.setGraphData);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(
    (searchQuery: string) => {
      setQuery(searchQuery);

      if (timerRef.current) clearTimeout(timerRef.current);

      const trimmed = searchQuery.trim();
      if (!trimmed) {
        return;
      }

      timerRef.current = setTimeout(async () => {
        setIsSearching(true);
        try {
          const nodes = await apiClient.searchGraph(
            trimmed,
            20,
            filterCategories.length > 0 ? filterCategories : undefined
          );
          // Convert search results to GraphPayload (no edges, no highlights)
          if (nodes.length > 0) {
            setGraphData({
              nodes: nodes.map((n) => ({ ...n, highlighted: false })),
              edges: [],
              center_node: nodes[0].canonical_id,
            });
          }
        } catch {
          // Silently fail — search is not critical
        } finally {
          setIsSearching(false);
        }
      }, 300);
    },
    [filterCategories, setGraphData]
  );

  return { query, search, isSearching };
}
```

**Step 2: Write GraphSearchBar**

Create `frontend/src/components/GraphSearchBar.tsx`:

```tsx
import { useGraphSearch } from "../hooks/useGraphSearch";

export default function GraphSearchBar() {
  const { query, search, isSearching } = useGraphSearch();

  return (
    <div className="absolute top-3 left-3 right-3 z-10">
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => search(e.target.value)}
          placeholder="Search entities..."
          className="w-full bg-gray-800/90 backdrop-blur text-gray-100 rounded-lg pl-10 pr-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-gray-500"
        />
        {isSearching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 3: Add GraphSearchBar to App.tsx graph panel**

In `frontend/src/App.tsx`, add the import and render GraphSearchBar inside the graph panel:

```tsx
import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";
import GraphSearchBar from "./components/GraphSearchBar";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

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
        </div>

        <ResizableSplitter />

        <ChatPanel />
      </div>
    </div>
  );
}
```

**Step 4: Verify in browser**

Expected: Search input appears over the top of the graph panel with a search icon. Typing triggers a debounced API call (will fail without backend, but the spinner should appear and disappear).

**Step 5: Commit**

```bash
git add frontend/src/hooks/useGraphSearch.ts frontend/src/components/GraphSearchBar.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add GraphSearchBar with debounced entity search over graph panel"
```

---

## Task 14: NodeSidebar Component

**Files:**
- Create: `frontend/src/components/NodeSidebar.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write NodeSidebar**

Create `frontend/src/components/NodeSidebar.tsx`:

```tsx
import { useAppStore } from "../stores/useAppStore";

export default function NodeSidebar() {
  const selectedNode = useAppStore((s) => s.selectedNode);
  const isSidebarOpen = useAppStore((s) => s.isSidebarOpen);
  const selectNode = useAppStore((s) => s.selectNode);
  const setChatInput = useAppStore((s) => s.setChatInput);

  if (!isSidebarOpen || !selectedNode) return null;

  const attrs = selectedNode.attributes ?? {};

  return (
    <div className="absolute top-0 right-0 h-full w-[300px] bg-gray-900 border-l border-gray-700 z-20 flex flex-col shadow-xl animate-slide-in">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-gray-800">
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-semibold text-gray-100 truncate">
            {selectedNode.name}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5 truncate">
            {selectedNode.canonical_id}
          </p>
        </div>
        <button
          onClick={() => selectNode(null)}
          className="text-gray-400 hover:text-gray-200 ml-2 p-1"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Categories */}
        {selectedNode.main_categories.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-gray-400 uppercase mb-1.5">Categories</h3>
            <div className="flex flex-wrap gap-1">
              {selectedNode.main_categories.map((cat) => (
                <span
                  key={cat}
                  className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-xs"
                >
                  {cat}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Sub-category */}
        {selectedNode.sub_category && (
          <div>
            <h3 className="text-xs font-medium text-gray-400 uppercase mb-1">Sub-category</h3>
            <p className="text-sm text-gray-300">{selectedNode.sub_category}</p>
          </div>
        )}

        {/* Attributes */}
        {Object.keys(attrs).length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-gray-400 uppercase mb-1.5">Attributes</h3>
            <table className="w-full text-xs">
              <tbody>
                {Object.entries(attrs).map(([key, val]) => (
                  <tr key={key} className="border-b border-gray-800">
                    <td className="py-1.5 pr-2 text-gray-400 font-medium align-top whitespace-nowrap">
                      {key}
                    </td>
                    <td className="py-1.5 text-gray-300 break-words">
                      {String(val)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={() => {
            setChatInput(`Tell me about ${selectedNode.name}`);
            selectNode(null);
          }}
          className="w-full bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium py-2 rounded-lg transition-colors"
        >
          Ask about this entity
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Add slide-in animation to global CSS**

Add to `frontend/src/index.css`:

```css
@import "tailwindcss";

@keyframes slide-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.animate-slide-in {
  animation: slide-in 200ms ease-out;
}
```

**Step 3: Wire NodeSidebar into App.tsx graph panel**

In `frontend/src/App.tsx`, add the import and render NodeSidebar inside the graph panel:

```tsx
import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";
import GraphSearchBar from "./components/GraphSearchBar";
import NodeSidebar from "./components/NodeSidebar";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

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
    </div>
  );
}
```

**Step 4: Verify in browser**

Expected: When `selectedNode` is set in the store (test via console), the sidebar slides in from the right showing entity details. "Ask about this entity" button sets the chat input. Close button dismisses the sidebar.

**Step 5: Commit**

```bash
git add frontend/src/components/NodeSidebar.tsx frontend/src/index.css frontend/src/App.tsx
git commit -m "feat(frontend): add NodeSidebar with entity details, attributes table, ask-about-entity action"
```

---

## Task 15: PdfModal Component

**Files:**
- Create: `frontend/src/components/PdfModal.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write PdfModal**

Create `frontend/src/components/PdfModal.tsx`:

```tsx
import { useEffect, useState, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import * as pdfjsLib from "pdfjs-dist";
import { useAppStore } from "../stores/useAppStore";
import { apiClient } from "../api/client";

// Configure pdf.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

export default function PdfModal() {
  const isPdfModalOpen = useAppStore((s) => s.isPdfModalOpen);
  const pdfModalProps = useAppStore((s) => s.pdfModalProps);
  const closePdfModal = useAppStore((s) => s.closePdfModal);

  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Fetch signed URL and load PDF
  useEffect(() => {
    if (!isPdfModalOpen || !pdfModalProps) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setPdfDoc(null);

    (async () => {
      try {
        const { url } = await apiClient.getSignedUrl(
          pdfModalProps.docId,
          pdfModalProps.page
        );
        const doc = await pdfjsLib.getDocument(url).promise;
        if (cancelled) return;
        setPdfDoc(doc);
        setTotalPages(doc.numPages);
        setCurrentPage(
          Math.min(pdfModalProps.page, doc.numPages)
        );
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load PDF");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isPdfModalOpen, pdfModalProps]);

  // Render current page
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;

    let cancelled = false;

    (async () => {
      const page = await pdfDoc.getPage(currentPage);
      if (cancelled) return;

      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current!;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      const ctx = canvas.getContext("2d")!;
      await page.render({ canvasContext: ctx, viewport }).promise;
    })();

    return () => {
      cancelled = true;
    };
  }, [pdfDoc, currentPage, scale]);

  // Escape key to close
  useEffect(() => {
    if (!isPdfModalOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") closePdfModal();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isPdfModalOpen, closePdfModal]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) closePdfModal();
    },
    [closePdfModal]
  );

  if (!isPdfModalOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center"
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-900 rounded-xl shadow-2xl flex flex-col max-w-[90vw] max-h-[90vh] w-[800px]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-300 font-medium">
              {pdfModalProps?.docId}
            </span>
            {totalPages > 0 && (
              <span className="text-xs text-gray-500">
                Page {currentPage} / {totalPages}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Zoom controls */}
            <button
              onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
              className="text-gray-400 hover:text-white px-2 py-1 text-sm"
            >
              -
            </button>
            <span className="text-xs text-gray-500 w-12 text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={() => setScale((s) => Math.min(3, s + 0.2))}
              className="text-gray-400 hover:text-white px-2 py-1 text-sm"
            >
              +
            </button>

            {/* Page navigation */}
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="text-gray-400 hover:text-white disabled:text-gray-600 px-2 py-1 text-sm"
            >
              Prev
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="text-gray-400 hover:text-white disabled:text-gray-600 px-2 py-1 text-sm"
            >
              Next
            </button>

            {/* Close */}
            <button
              onClick={closePdfModal}
              className="text-gray-400 hover:text-white ml-2 p-1"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Canvas area */}
        <div className="flex-1 overflow-auto p-4 flex justify-center">
          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center py-20">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}
          {!loading && !error && (
            <canvas ref={canvasRef} className="max-w-full" />
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
```

**Step 2: Add PdfModal to App.tsx**

In `frontend/src/App.tsx`, add import and render PdfModal outside the grid (it's a portal, but needs to be in the React tree):

```tsx
import { useAppStore } from "./stores/useAppStore";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";
import GraphSearchBar from "./components/GraphSearchBar";
import NodeSidebar from "./components/NodeSidebar";
import PdfModal from "./components/PdfModal";

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);

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

**Step 3: Verify TypeScript compiles**

```bash
cd C:/NUS/Projects/history/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 4: Commit**

```bash
git add frontend/src/components/PdfModal.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add PdfModal with pdf.js rendering, page nav, zoom, Escape to close"
```

---

## Task 16: Dockerfile + nginx.conf

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `frontend/.dockerignore`

**Step 1: Write .dockerignore**

Create `frontend/.dockerignore`:

```
node_modules
dist
.git
```

**Step 2: Write Dockerfile**

Create `frontend/Dockerfile`:

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Step 3: Write nginx.conf**

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;

    # SPA routing — serve index.html for all non-file paths
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to backend
    location /api/ {
        proxy_pass http://backend:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf frontend/.dockerignore
git commit -m "feat(frontend): add multi-stage Dockerfile + nginx.conf with SPA routing and API proxy"
```

---

## Task 17: Update Docker Compose

**Files:**
- Modify: `infra/docker-compose.yml`

**Step 1: Add frontend service**

Update `infra/docker-compose.yml` to add the frontend service:

```yaml
version: "3.8"

services:
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    env_file:
      - ../backend/.env
    volumes:
      - ${GOOGLE_APPLICATION_CREDENTIALS:-~/.config/gcloud/application_default_credentials.json}:/app/credentials.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
```

**Step 2: Commit**

```bash
git add infra/docker-compose.yml
git commit -m "feat(infra): add frontend service to Docker Compose"
```

---

## Task 18: Final Integration Verification

**Files:** None (verification only)

**Step 1: Run all tests**

```bash
cd C:/NUS/Projects/history/frontend && npx vitest run
```

Expected: All tests pass (types, API client, store, citation parser).

**Step 2: Verify TypeScript compiles cleanly**

```bash
cd C:/NUS/Projects/history/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Verify dev server runs**

```bash
cd C:/NUS/Projects/history/frontend && npm run dev
```

Expected: App loads at http://localhost:5173 showing:
- Left panel: empty graph with search bar
- Right panel: empty chat with category pills and input bar
- Splitter: draggable
- All visual components render without console errors

**Step 4: Verify production build**

```bash
cd C:/NUS/Projects/history/frontend && npm run build
```

Expected: Build completes successfully, output in `frontend/dist/`.

**Step 5: Commit any final fixes, then tag**

```bash
git add -A
git commit -m "feat(frontend): Phase 3 complete — React frontend with graph visualization, chat, PDF viewer"
```

---

## Summary

| Task | Component | Type |
|------|-----------|------|
| 1 | Project scaffolding | Setup |
| 2 | TypeScript types | Types + TDD |
| 3 | API client | Logic + TDD |
| 4 | Zustand store | Logic + TDD |
| 5 | App layout shell | UI |
| 6 | ResizableSplitter | UI |
| 7 | Citation parser | Logic + TDD |
| 8 | CitationBadge | UI |
| 9 | ChatMessage | UI |
| 10 | ChatPanel | UI |
| 11 | CategoryFilter | UI |
| 12 | GraphCanvas | UI |
| 13 | GraphSearchBar + hook | UI + Logic |
| 14 | NodeSidebar | UI |
| 15 | PdfModal | UI |
| 16 | Dockerfile + nginx | Infra |
| 17 | Docker Compose update | Infra |
| 18 | Integration verification | QA |
