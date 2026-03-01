# Phase 3 Frontend — Multi-Agent Team Execution Plan

**Last Updated: 2026-03-01**

---

## Executive Summary

Execute the Phase 3 React frontend implementation (18 tasks from `docs/plans/2026-03-01-phase3-implementation-plan.md`) using a coordinated multi-agent team. The plan splits work into a sequential foundation phase followed by three parallel agent work streams, then a final integration phase.

**Total scope**: 10 components, 2 hooks, 1 utility, TypeScript types, API client, Zustand store, Docker/nginx, integration verification.

**Team size**: 1 leader + 3 parallel agents (after foundation).

---

## Current State Analysis

- **Phase 1 (Backend Foundation)**: COMPLETE
- **Phase 2 (Graph Layer)**: CODE COMPLETE (untested end-to-end)
- **Phase 3 (Frontend)**: NOT STARTED — design doc and implementation plan approved
- **No git repo initialized** — commits in the plan are aspirational; agents should write files, leader handles commits
- Backend API endpoints are ready: `POST /query`, `GET /document/signed_url`, `GET /graph/search`, `GET /graph/{id}`
- All Pydantic schemas defined in `backend/app/models/schemas.py`

---

## Team Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    TEAM LEAD (main session)                   │
│  Coordinates phases, reviews output, merges, resolves conflicts│
└──────────┬──────────────┬──────────────┬─────────────────────┘
           │              │              │
     Phase B (parallel after Phase A completes)
           │              │              │
    ┌──────┴──────┐ ┌────┴─────┐ ┌─────┴──────┐
    │  Agent:     │ │ Agent:   │ │ Agent:     │
    │  graph      │ │ chat     │ │ pdf-infra  │
    │  (worktree) │ │(worktree)│ │ (worktree) │
    └─────────────┘ └──────────┘ └────────────┘
```

---

## Phase A: Foundation (Sequential, Team Lead)

Must complete before any parallel agents launch. These tasks create shared infrastructure that all agents depend on.

| Order | Plan Task | What | Effort |
|-------|-----------|------|--------|
| A.1 | Task 1 | Project scaffolding (Vite + React + TS + Tailwind + deps) | M |
| A.2 | Task 2 | TypeScript types (`src/types/index.ts`) | S |
| A.3 | Task 3 | API client (`src/api/client.ts`) | S |
| A.4 | Task 4 | Zustand store (`src/stores/useAppStore.ts`) | M |
| A.5 | Task 5 | App.tsx layout shell (placeholder panels) | S |
| A.6 | Task 6 | ResizableSplitter component | S |

**Why sequential**: Every component imports from types, api/client, and stores. The App.tsx layout shell defines the mounting points for all other components. These must exist before parallel agents can work.

**Deliverable**: A working `frontend/` directory with dev server running, showing two placeholder panels with a draggable splitter.

---

## Phase B: Parallel Agent Streams

After Phase A commits, launch 3 agents in isolated worktrees. Each agent works on self-contained component clusters that don't share files.

### Agent: graph (worktree)

**Scope**: Graph visualization panel (left side of the app)

| Order | Plan Task | Component | Effort |
|-------|-----------|-----------|--------|
| B.1 | Task 12 | GraphCanvas.tsx (Cytoscape.js + cose-bilkent) | L |
| B.2 | Task 13 | GraphSearchBar.tsx + hooks/useGraphSearch.ts | M |
| B.3 | Task 14 | NodeSidebar.tsx | M |

**Imports from foundation**: `types/index`, `stores/useAppStore`, `api/client`
**Creates**: 3 component files + 1 hook file
**Does NOT modify**: App.tsx (leader wires these in during Phase C)

**Agent instructions**: Implement each component as a standalone module. Export default from each. Do NOT modify App.tsx — the team lead will wire components into the layout during integration. Run `npx tsc --noEmit` after each component to verify types.

### Agent: chat (worktree)

**Scope**: Chat panel (right side of the app) + citation parsing

| Order | Plan Task | Component | Effort |
|-------|-----------|-----------|--------|
| B.1 | Task 7 | parseCitations utility (TDD) | S |
| B.2 | Task 8 | CitationBadge.tsx | S |
| B.3 | Task 9 | ChatMessage.tsx | S |
| B.4 | Task 10 | ChatPanel.tsx | M |
| B.5 | Task 11 | CategoryFilter.tsx | S |

**Imports from foundation**: `types/index`, `stores/useAppStore`
**Creates**: 4 component files + 1 utility file + 2 test files
**Does NOT modify**: App.tsx

**Agent instructions**: Start with the citation parser (pure function, TDD with Vitest). Then build components bottom-up: CitationBadge → ChatMessage → ChatPanel → CategoryFilter. Run tests after writing the parser. Run `npx tsc --noEmit` after each component.

### Agent: pdf-infra (worktree)

**Scope**: PDF modal + Docker/nginx deployment

| Order | Plan Task | Component | Effort |
|-------|-----------|-----------|--------|
| B.1 | Task 15 | PdfModal.tsx | L |
| B.2 | Task 16 | Dockerfile + nginx.conf + .dockerignore | S |
| B.3 | Task 17 | docker-compose.yml update | S |

**Imports from foundation**: `types/index`, `stores/useAppStore`, `api/client`
**Creates**: 1 component file + 3 infra files
**Modifies**: `infra/docker-compose.yml`
**Does NOT modify**: App.tsx

**Agent instructions**: Build PdfModal first (uses React portal, pdfjs-dist). Then write the Dockerfile, nginx.conf, and update docker-compose.yml. PdfModal is fully self-contained (portal renders outside the component tree). Run `npx tsc --noEmit` after PdfModal.

---

## Phase C: Integration (Sequential, Team Lead)

After all 3 agents complete, the team lead:

1. **Merges worktree output** into main branch — resolve any conflicts
2. **Wires components into App.tsx** — replace placeholder panels with real components
3. **Adds slide-in CSS animation** to `index.css` (for NodeSidebar)
4. **Runs full verification** (Task 18):
   - `npx vitest run` — all tests pass
   - `npx tsc --noEmit` — no type errors
   - `npm run dev` — visual verification
   - `npm run build` — production build succeeds
5. **Final commit**

### App.tsx Integration (Phase C target state)

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
      <div className="h-full grid" style={{
        gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
      }}>
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

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Worktree merge conflicts on shared files | Medium | Low | Only App.tsx and index.css are shared; agents are instructed NOT to modify them |
| Cytoscape.js type issues with react-cytoscapejs | Medium | Medium | GraphCanvas agent should cast layout config as `any` where needed |
| pdfjs-dist worker loading in Vite dev mode | Medium | Medium | Use CDN worker URL (`cdnjs.cloudflare.com`) as fallback |
| Agent installs different npm package versions | Low | Medium | All agents work from the same package-lock.json created in Phase A |
| Store shape mismatch between agents | High | Low | Types and store are frozen in Phase A; agents import but don't modify |

---

## Success Metrics

- [ ] All Vitest tests pass (`npx vitest run`)
- [ ] TypeScript compiles cleanly (`npx tsc --noEmit`)
- [ ] Dev server starts without errors (`npm run dev`)
- [ ] Production build succeeds (`npm run build`)
- [ ] Two-panel layout renders with draggable splitter
- [ ] Graph empty state shows placeholder text
- [ ] Chat empty state shows placeholder text
- [ ] Category filter pills toggle correctly
- [ ] Docker build succeeds (`docker build -t frontend .`)

---

## Timeline

| Phase | Duration | Blocking? |
|-------|----------|-----------|
| Phase A: Foundation | ~15 min | Yes — must complete before Phase B |
| Phase B: Parallel agents (3x) | ~15-20 min each | No — all 3 run concurrently |
| Phase C: Integration | ~10 min | Yes — after all Phase B agents complete |
| **Total** | **~40-45 min** | |

Sequential execution (no agents) would take ~50-60 min. Team execution saves ~20 min and reduces context window pressure by distributing work across 3 separate sessions.
