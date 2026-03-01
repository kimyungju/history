# Phase 3: React Frontend — Design Document

**Date**: 2026-03-01
**Status**: Approved
**Phase**: 3 of 5

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | React 18 + Vite + TypeScript | Lightweight SPA, no SSR needed |
| Styling | TailwindCSS | Utility-first, fast iteration |
| State management | Zustand | Minimal boilerplate, no provider wrappers |
| Graph rendering | Cytoscape.js + react-cytoscapejs | De facto standard for knowledge graphs in the browser |
| Graph layout | cose-bilkent | Best for compound/clustered knowledge graphs |
| PDF viewer | pdfjs-dist | Industry standard, no server-side rendering needed |
| Architecture | Monolithic SPA (no router) | Single-view app, ~10 components, no multi-page needs |
| Directory | `frontend/` at repo root | Alongside `backend/`, matches Docker Compose pattern |
| Node click behavior | Sidebar only (no auto-query) | User stays in control, less API noise |
| Graph search | Included in Phase 3 | Researchers can browse entities independently of chat |

## Project Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── Dockerfile              # multi-stage: node build -> nginx serve
├── nginx.conf              # SPA routing + API proxy
├── public/
│   └── favicon.ico
└── src/
    ├── main.tsx
    ├── App.tsx             # CSS Grid layout shell
    ├── api/
    │   └── client.ts       # fetch wrapper, base URL from env
    ├── types/
    │   └── index.ts        # TS interfaces mirroring Pydantic schemas
    ├── stores/
    │   └── useAppStore.ts  # Zustand store (chat, graph, UI state)
    ├── components/
    │   ├── GraphCanvas.tsx
    │   ├── GraphSearchBar.tsx
    │   ├── ChatPanel.tsx
    │   ├── ChatMessage.tsx
    │   ├── CitationBadge.tsx
    │   ├── PdfModal.tsx
    │   ├── NodeSidebar.tsx
    │   ├── CategoryFilter.tsx
    │   └── ResizableSplitter.tsx
    └── hooks/
        ├── useQuery.ts
        └── useGraphSearch.ts
```

## App Layout

CSS Grid with three columns: `[graph] [splitter] [chat]`.

- Default split: 65% graph / 35% chat
- Splitter: 4px draggable bar, min 30% / max 70% each side
- Split ratio persisted in localStorage
- NodeSidebar: absolute positioned over graph panel, slides from right (300px)
- PdfModal: full-screen overlay via React portal

## Zustand Store

```typescript
interface AppState {
  // Chat
  messages: ChatMessage[];
  isQuerying: boolean;
  queryError: string | null;
  filterCategories: string[];

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
}
```

## Data Flows

### Query Flow
1. User types question -> `sendQuery(question)`
2. Store sets `isQuerying: true`, appends user message
3. `POST /query` with `{ question, filter_categories }`
4. On success: append assistant message (with parsed citations), update `graphData`
5. GraphCanvas re-renders, highlights applied to nodes/edges where `highlighted: true`
6. Camera animates to fit highlighted subgraph (800ms ease-out)
7. On error: set `queryError`, show inline error with retry button

### Graph Search Flow
1. User types in GraphSearchBar -> debounced (300ms) `GET /graph/search?q=...&limit=20`
2. Results replace `graphData` (no highlighted nodes, all full opacity)
3. No chat message generated

### Node Click Flow
1. User clicks node -> `selectNode(node)`
2. NodeSidebar opens with entity details (from `graphData`, no extra API call)
3. "Ask about this entity" -> pre-fills chat input with `"Tell me about {name}"`

### Citation Click Flow
1. Archive badge clicked -> `openPdfModal(doc_id, pages[0])`
2. PdfModal fetches `GET /document/signed_url?doc_id=X&page=N`
3. PDF rendered with pdfjs-dist, jumps to cited page
4. Web badge clicked -> `window.open(url, '_blank')`

## Components

### GraphCanvas
- Wraps `react-cytoscapejs` with `cose-bilkent` layout
- Node style: rounded rectangles, color-coded by `main_categories[0]` (5 colors)
- Edge style: curved lines with arrow, label = `type`
- Highlighting: orange border (#F97316) + CSS pulse on `highlighted: true` nodes/edges; non-highlighted desaturated (opacity 0.4)
- Camera fit: animate to highlighted subgraph (800ms ease-out)
- Empty state: centered placeholder text

### GraphSearchBar
- Text input with search icon above graph
- Debounced 300ms, calls `GET /graph/search?q=...&limit=20`
- Passes `filterCategories` if set

### ChatPanel
- Scrollable message list + fixed input bar at bottom
- Markdown rendering via react-markdown
- Loading: pulsing dot animation
- Error: red inline message + retry button
- Auto-scroll to latest message

### ChatMessage + CitationBadge
- Parses `[archive:N]` / `[web:N]` markers into CitationBadge components
- Archive badges: blue (#3B82F6), click opens PdfModal
- Web badges: green (#10B981), click opens new tab
- Hover tooltip: shows `text_span` (300-char context snippet)

### PdfModal
- Full-screen overlay (React portal)
- Fetches signed URL on open
- pdfjs-dist worker renders PDF
- Controls: prev/next page, zoom, page input, close (X + Escape)
- Dark backdrop, click-outside to close

### NodeSidebar
- Slides from right (300px), overlays graph
- Shows: entity name, category tags, sub_category, aliases, attributes (key-value table), evidence links
- "Ask about this entity" button pre-fills chat input
- Close via X or click-outside

### CategoryFilter
- Multi-select pill bar above chat input
- 5 hardcoded categories: Internal Relations and Research, Economic and Financial, Social Services, Defence and Military, General and Establishment
- Filters both `/query` and `/graph/search`
- "All categories" when nothing selected

### ResizableSplitter
- 4px vertical bar, `cursor: col-resize`
- Mouse/touch drag updates `splitRatio`
- Min 30%, max 70%
- Persisted to localStorage

## TypeScript Types

Mirror backend Pydantic schemas exactly:
- `QueryRequest`, `QueryResponse`
- `ArchiveCitation`, `WebCitation` (discriminated union on `type`)
- `GraphPayload`, `GraphNode`, `GraphEdge`
- `SignedUrlResponse`
- `IngestResponse`, `OcrConfidenceWarning`
- `ChatMessage` (frontend-only: `{ role, content, citations? }`)

## Deployment

### Dockerfile (multi-stage)
- Stage 1: `node:20-alpine` — `npm ci && npm run build` -> `dist/`
- Stage 2: `nginx:alpine` — copy `dist/` + `nginx.conf`, expose port 80

### nginx.conf
- Serve static files from `/usr/share/nginx/html`
- `try_files $uri $uri/ /index.html` for SPA routing
- Proxy `/api/` to `http://backend:8080/`
- Gzip compression

### docker-compose.yml
- Add `frontend` service (build `../frontend/`, port `3000:80`, depends on `backend`)
- Environment: `VITE_API_BASE_URL=/api`

### Local development
- `npm run dev` (Vite on port 5173)
- Vite proxy: `/api` -> `http://localhost:8080`

### Environment variables
- `VITE_API_BASE_URL` — defaults to `/api`
- Injected at build time via `import.meta.env`

## Performance Targets
- Graph render: < 500ms for subgraphs up to 50 nodes
- PDF viewer load: < 3 seconds
- Frontend initial load (FCP): < 2 seconds

## API Endpoints Consumed

| Method | Path | Used By |
|--------|------|---------|
| POST | `/query` | useQuery hook (ChatPanel) |
| GET | `/document/signed_url` | PdfModal |
| GET | `/graph/search` | useGraphSearch hook (GraphSearchBar) |
| GET | `/graph/{canonical_id}` | Not in Phase 3 (future: node expansion) |
| GET | `/health` | Not in Phase 3 (future: status indicator) |
