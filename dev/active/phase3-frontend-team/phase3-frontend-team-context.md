# Phase 3 Frontend Team — Context Reference

**Last Updated: 2026-03-01**

---

## Key Files

### Planning Documents

| Document | Path | Purpose |
|----------|------|---------|
| Design doc | `docs/plans/2026-03-01-phase3-react-frontend-design.md` | Approved design — all component specs, data flows, store shape |
| Implementation plan | `docs/plans/2026-03-01-phase3-implementation-plan.md` | 18 tasks with complete code, TDD, exact file paths |
| Master task tracker | `dev/active/colonial-archives-graph-rag/colonial-archives-graph-rag-tasks.md` | Full project task list (Phases 1-5) |
| Master context | `dev/active/colonial-archives-graph-rag/colonial-archives-graph-rag-context.md` | Architecture decisions, API contracts, data flows |

### Backend Files (Read-Only Reference)

| File | What agents need from it |
|------|--------------------------|
| `backend/app/models/schemas.py` | Pydantic models to mirror as TypeScript types |
| `backend/app/routers/query.py` | POST /query, GET /document/signed_url contracts |
| `backend/app/routers/graph.py` | GET /graph/search, GET /graph/{id} contracts |
| `backend/app/main.py` | CORS config (allow_origins=["*"]), health endpoint |
| `infra/docker-compose.yml` | Existing docker-compose to extend with frontend service |

### Frontend Files (Created During Execution)

```
frontend/
├── index.html                     # Phase A
├── package.json                   # Phase A
├── package-lock.json              # Phase A
├── tsconfig.json                  # Phase A
├── vite.config.ts                 # Phase A (includes test config + API proxy)
├── tailwind.config.js             # Phase A
├── postcss.config.js              # Phase A
├── Dockerfile                     # Agent: pdf-infra
├── nginx.conf                     # Agent: pdf-infra
├── .dockerignore                  # Agent: pdf-infra
└── src/
    ├── main.tsx                   # Phase A
    ├── App.tsx                    # Phase A (placeholders) → Phase C (wired)
    ├── index.css                  # Phase A → Phase C (add animation)
    ├── test-setup.ts              # Phase A
    ├── api/
    │   ├── client.ts              # Phase A
    │   └── client.test.ts         # Phase A
    ├── types/
    │   ├── index.ts               # Phase A
    │   └── index.test.ts          # Phase A
    ├── stores/
    │   ├── useAppStore.ts         # Phase A
    │   └── useAppStore.test.ts    # Phase A
    ├── utils/
    │   ├── parseCitations.ts      # Agent: chat
    │   └── parseCitations.test.ts # Agent: chat
    ├── components/
    │   ├── ResizableSplitter.tsx   # Phase A
    │   ├── GraphCanvas.tsx        # Agent: graph
    │   ├── GraphSearchBar.tsx     # Agent: graph
    │   ├── NodeSidebar.tsx        # Agent: graph
    │   ├── CitationBadge.tsx      # Agent: chat
    │   ├── ChatMessage.tsx        # Agent: chat
    │   ├── ChatPanel.tsx          # Agent: chat
    │   ├── CategoryFilter.tsx     # Agent: chat
    │   └── PdfModal.tsx           # Agent: pdf-infra
    └── hooks/
        └── useGraphSearch.ts      # Agent: graph
```

---

## Key Decisions

| Decision | Choice | Reference |
|----------|--------|-----------|
| Tech stack | React 18 + Vite + TypeScript + TailwindCSS | Design doc §Decisions |
| State management | Zustand (single store) | Design doc §Zustand Store |
| Graph library | Cytoscape.js + react-cytoscapejs + cose-bilkent | Design doc §Components |
| PDF viewer | pdfjs-dist (CDN worker) | Design doc §Components |
| Architecture | Monolithic SPA (no router) | Design doc §Decisions |
| App layout | CSS Grid: `[graph] [splitter] [chat]` | Design doc §App Layout |
| Default split | 65% graph / 35% chat, min 30%, max 70% | Design doc §App Layout |
| Node click behavior | Sidebar only (no auto-query) | Design doc §Decisions |
| Graph search | Included in Phase 3 | Design doc §Decisions |
| Agent isolation | Worktrees — agents don't modify App.tsx | This doc §Agent Rules |

---

## Agent Rules (Critical)

### What agents CAN do:
- Create new files in their assigned paths (see task assignments below)
- Import from `types/`, `stores/`, `api/` (frozen after Phase A)
- Run `npx tsc --noEmit` and `npx vitest run` for verification
- Install NO additional npm packages (all deps installed in Phase A)

### What agents MUST NOT do:
- Modify `App.tsx` — only the team lead does this in Phase C
- Modify `index.css` — only the team lead adds animations in Phase C
- Modify any file in `types/`, `stores/`, `api/` — these are frozen
- Modify `package.json` or install new packages
- Modify any backend files
- Create commits (no git repo yet — team lead handles this)

### Each agent receives:
1. The implementation plan path (`docs/plans/2026-03-01-phase3-implementation-plan.md`)
2. Their specific task numbers (e.g., "Tasks 12, 13, 14")
3. These rules
4. Working directory: `C:/NUS/Projects/history/frontend`

---

## Dependencies Between Tasks

```
Phase A (sequential):
  Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

Phase B (parallel after Phase A):
  Agent graph:     Task 12 → Task 13 → Task 14
  Agent chat:      Task 7  → Task 8  → Task 9 → Task 10 → Task 11
  Agent pdf-infra: Task 15 → Task 16 → Task 17

Phase C (sequential after all Phase B):
  Wire App.tsx → Add CSS animations → Run verification (Task 18)
```

### Cross-agent dependencies: NONE
Each agent's components are self-contained. No agent creates a file that another agent imports. The only shared dependencies (types, store, api client) are frozen in Phase A.

---

## API Endpoints (Frontend Consumes)

| Method | Path | Used By | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/query` | ChatPanel via store.sendQuery | `{question, filter_categories?}` | `QueryResponse` |
| GET | `/document/signed_url?doc_id=X&page=N` | PdfModal via apiClient | query params | `SignedUrlResponse` |
| GET | `/graph/search?q=X&limit=N&categories=` | GraphSearchBar via useGraphSearch | query params | `GraphNode[]` |

### Vite Dev Proxy

```
/api/* → http://localhost:8080/*  (strips /api prefix)
```

Frontend code always prefixes API calls with `/api` (via `VITE_API_BASE_URL`). In dev mode, Vite proxies to the backend. In production, nginx proxies.

---

## Store Shape (Frozen in Phase A)

```typescript
interface AppState {
  messages: ChatMessage[];         // Chat history
  isQuerying: boolean;             // Loading state for POST /query
  queryError: string | null;       // Error message from failed query
  filterCategories: string[];      // Selected category filters
  chatInput: string;               // Current chat input text

  graphData: GraphPayload | null;  // Nodes + edges for Cytoscape
  selectedNode: GraphNode | null;  // Currently clicked graph node

  splitRatio: number;              // Panel split (0.3-0.7, default 0.65)
  isSidebarOpen: boolean;          // NodeSidebar visibility
  isPdfModalOpen: boolean;         // PdfModal visibility
  pdfModalProps: { docId: string; page: number } | null;

  // Actions
  sendQuery(question: string): Promise<void>;
  selectNode(node: GraphNode | null): void;
  openPdfModal(docId: string, page: number): void;
  closePdfModal(): void;
  setSplitRatio(ratio: number): void;
  setFilterCategories(cats: string[]): void;
  setChatInput(text: string): void;
  setGraphData(data: GraphPayload | null): void;
}
```

---

## Category Constants

```typescript
const MAIN_CATEGORIES = [
  "Internal Relations and Research",
  "Economic and Financial",
  "Social Services",
  "Defence and Military",
  "General and Establishment",
] as const;
```

Hardcoded in `types/index.ts`. No API call needed. Used by CategoryFilter and passed as `filter_categories` in query/search requests.

---

## Color Palette

| Element | Color | Hex |
|---------|-------|-----|
| Background (app) | gray-950 | #030712 |
| Background (graph panel) | gray-900 | #111827 |
| Background (chat messages) | gray-800 | #1F2937 |
| User message bubble | blue-600 | #2563EB |
| Archive citation badge | blue-500/20 text blue-400 | #3B82F6 |
| Web citation badge | emerald-500/20 text emerald-400 | #10B981 |
| Highlighted node/edge | orange-500 | #F97316 |
| Error text | red-400 | #F87171 |
| Category: Internal Relations | violet-500 | #8B5CF6 |
| Category: Economic | amber-500 | #F59E0B |
| Category: Social Services | emerald-500 | #10B981 |
| Category: Defence | red-500 | #EF4444 |
| Category: General | blue-500 | #3B82F6 |
