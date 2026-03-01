# Phase 3 Frontend Team — Task Tracker

**Last Updated: 2026-03-01**

## Status Legend

- S = Small (< 5 min), M = Medium (5-15 min), L = Large (15-30 min)
- Owner: `lead` = team lead, `graph` = graph agent, `chat` = chat agent, `pdf-infra` = pdf-infra agent

---

## Phase A: Foundation (Sequential — Team Lead)

All tasks must complete before Phase B agents launch.

### A.1 — Project Scaffolding [M] [Owner: lead]

- [ ] Run `npm create vite@latest frontend -- --template react-ts`
- [ ] Install runtime deps: zustand, react-markdown, cytoscape, react-cytoscapejs, cytoscape-cose-bilkent, pdfjs-dist
- [ ] Install dev deps: tailwindcss, @tailwindcss/vite, @types/cytoscape, @types/react-cytoscapejs, vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, jsdom
- [ ] Configure Tailwind v4 (`@import "tailwindcss"` in index.css)
- [ ] Configure Vite (API proxy, vitest, tailwind plugin)
- [ ] Create test-setup.ts
- [ ] Write minimal App.tsx and main.tsx
- [ ] Clean up scaffolding files (App.css, assets/react.svg, public/vite.svg)
- [ ] Verify: `npm run dev` starts, page loads with Tailwind styling
- [ ] Verify: `npx vitest run` executes without errors

### A.2 — TypeScript Types [S] [Owner: lead]

- [ ] Create `src/types/index.ts` mirroring backend schemas
- [ ] Create `src/types/index.test.ts` with compile-time type tests
- [ ] Verify: `npx vitest run src/types/index.test.ts` — all 8 tests pass

### A.3 — API Client [S] [Owner: lead]

- [ ] Create `src/api/client.test.ts` (mock fetch, 6 tests)
- [ ] Create `src/api/client.ts` (postQuery, getSignedUrl, searchGraph)
- [ ] Verify: `npx vitest run src/api/client.test.ts` — all 6 tests pass

### A.4 — Zustand Store [M] [Owner: lead]

- [ ] Create `src/stores/useAppStore.test.ts` (8 tests)
- [ ] Create `src/stores/useAppStore.ts` (full state + actions)
- [ ] Verify: `npx vitest run src/stores/useAppStore.test.ts` — all 8 tests pass

### A.5 — App Layout Shell [S] [Owner: lead]

- [ ] Update App.tsx with CSS Grid layout (graph | splitter | chat placeholders)
- [ ] Verify: two panels visible at 65/35 split in browser

### A.6 — ResizableSplitter [S] [Owner: lead]

- [ ] Create `src/components/ResizableSplitter.tsx`
- [ ] Wire into App.tsx (replace placeholder divider)
- [ ] Verify: drag splitter resizes panels, min 30% / max 70%, persists in localStorage

---

## Phase B: Parallel Agent Streams

Launch all 3 agents after Phase A completes. Agents work in worktrees.

### Agent: graph

#### B.graph.1 — GraphCanvas [L] [Owner: graph]

- [ ] Create `src/components/GraphCanvas.tsx`
- [ ] Implement Cytoscape.js wrapper with cose-bilkent layout
- [ ] Implement node styling (rounded rect, color by category)
- [ ] Implement edge styling (curved, arrow, label = type)
- [ ] Implement highlighting (orange border on `highlighted: true`, dim others to 0.4 opacity)
- [ ] Implement camera fit animation (800ms to highlighted subgraph)
- [ ] Implement node click → `selectNode()` from store
- [ ] Implement background click → `selectNode(null)`
- [ ] Implement empty state placeholder text
- [ ] Verify: `npx tsc --noEmit` — no errors

#### B.graph.2 — GraphSearchBar + useGraphSearch [M] [Owner: graph]

- [ ] Create `src/hooks/useGraphSearch.ts` (debounced 300ms, calls searchGraph)
- [ ] Create `src/components/GraphSearchBar.tsx` (search icon input, spinner)
- [ ] Verify: `npx tsc --noEmit` — no errors

#### B.graph.3 — NodeSidebar [M] [Owner: graph]

- [ ] Create `src/components/NodeSidebar.tsx`
- [ ] Implement entity name, categories as tags, sub_category, aliases
- [ ] Implement attributes key-value table
- [ ] Implement "Ask about this entity" button → setChatInput + selectNode(null)
- [ ] Implement close button → selectNode(null)
- [ ] Verify: `npx tsc --noEmit` — no errors

---

### Agent: chat

#### B.chat.1 — Citation Parser (TDD) [S] [Owner: chat]

- [ ] Create `src/utils/parseCitations.test.ts` (5 tests)
- [ ] Verify: tests FAIL (module not found)
- [ ] Create `src/utils/parseCitations.ts`
- [ ] Verify: `npx vitest run src/utils/parseCitations.test.ts` — all 5 tests pass

#### B.chat.2 — CitationBadge [S] [Owner: chat]

- [ ] Create `src/components/CitationBadge.tsx`
- [ ] Archive badge: blue, click → openPdfModal, tooltip = text_span
- [ ] Web badge: green, click → window.open in new tab, tooltip = title
- [ ] Verify: `npx tsc --noEmit` — no errors

#### B.chat.3 — ChatMessage [S] [Owner: chat]

- [ ] Create `src/components/ChatMessage.tsx`
- [ ] User messages: blue bubble, right-aligned
- [ ] Assistant messages: gray bubble, left-aligned, markdown + citation badges inline
- [ ] Verify: `npx tsc --noEmit` — no errors

#### B.chat.4 — ChatPanel [M] [Owner: chat]

- [ ] Create `src/components/ChatPanel.tsx`
- [ ] Scrollable message list with auto-scroll on new messages
- [ ] Fixed input bar at bottom with Send button
- [ ] Loading state: bouncing dots animation
- [ ] Error state: red message + retry button
- [ ] Empty state: "Ask a question about the colonial archives"
- [ ] Verify: `npx tsc --noEmit` — no errors

#### B.chat.5 — CategoryFilter [S] [Owner: chat]

- [ ] Create `src/components/CategoryFilter.tsx`
- [ ] 5 category pills from MAIN_CATEGORIES
- [ ] Toggle active/inactive (blue/gray)
- [ ] Update store.filterCategories on toggle
- [ ] Verify: `npx tsc --noEmit` — no errors

---

### Agent: pdf-infra

#### B.pdf.1 — PdfModal [L] [Owner: pdf-infra]

- [ ] Create `src/components/PdfModal.tsx`
- [ ] React portal to document.body
- [ ] Fetch signed URL via apiClient.getSignedUrl on open
- [ ] Render PDF with pdfjs-dist worker (CDN)
- [ ] Jump to cited page on open
- [ ] Page navigation (prev/next), zoom controls, page number display
- [ ] Close via X button, Escape key, backdrop click
- [ ] Loading spinner and error state
- [ ] Verify: `npx tsc --noEmit` — no errors

#### B.pdf.2 — Dockerfile + nginx [S] [Owner: pdf-infra]

- [ ] Create `frontend/.dockerignore`
- [ ] Create `frontend/Dockerfile` (multi-stage: node:20-alpine build → nginx:alpine serve)
- [ ] Create `frontend/nginx.conf` (SPA routing + `/api/` proxy to backend:8080)

#### B.pdf.3 — Docker Compose Update [S] [Owner: pdf-infra]

- [ ] Update `infra/docker-compose.yml` — add frontend service (port 3000:80, depends_on backend)

---

## Phase C: Integration (Sequential — Team Lead)

After all Phase B agents report complete.

### C.1 — Merge Agent Output [M] [Owner: lead]

- [ ] Copy graph agent files into main frontend/src/
- [ ] Copy chat agent files into main frontend/src/
- [ ] Copy pdf-infra agent files into main frontend/src/ and infra/
- [ ] Resolve any file conflicts (should be none if agents followed rules)

### C.2 — Wire Components into App.tsx [S] [Owner: lead]

- [ ] Import all components into App.tsx
- [ ] Replace graph placeholder with GraphSearchBar + GraphCanvas + NodeSidebar
- [ ] Replace chat placeholder with ChatPanel
- [ ] Add PdfModal outside the grid
- [ ] Add CategoryFilter import in ChatPanel (if not done by chat agent)

### C.3 — Add CSS Animations [S] [Owner: lead]

- [ ] Add `@keyframes slide-in` and `.animate-slide-in` to `src/index.css`

### C.4 — Final Verification (Task 18) [M] [Owner: lead]

- [ ] `npx vitest run` — all tests pass
- [ ] `npx tsc --noEmit` — no type errors
- [ ] `npm run dev` — visual check: two panels, splitter, empty states
- [ ] `npm run build` — production build succeeds
- [ ] Docker build test: `cd frontend && docker build -t frontend .` (if Docker available)

---

## Summary

| Phase | Tasks | Agents | Parallel? |
|-------|-------|--------|-----------|
| A: Foundation | 6 tasks | lead (1) | No — sequential |
| B: Graph stream | 3 tasks | graph (1) | Yes — with chat + pdf-infra |
| B: Chat stream | 5 tasks | chat (1) | Yes — with graph + pdf-infra |
| B: PDF/Infra stream | 3 tasks | pdf-infra (1) | Yes — with graph + chat |
| C: Integration | 4 tasks | lead (1) | No — sequential |
| **Total** | **21 tasks** | **4 agents** | |
