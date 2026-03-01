# Frontend Design Refinement — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Elevate the frontend from a generic dark chatbot UI to a distinctive scholarly research terminal — custom typography, warm archival color palette, refined animations, and visual polish — without changing layout structure or functionality.

**Architecture:** CSS-first approach using Tailwind v4 `@theme` for custom colors and fonts, Google Fonts for distinctive typography (Crimson Pro, Plus Jakarta Sans, IBM Plex Mono), CSS keyframe animations. All changes are visual — no logic, state, or API modifications. Existing 29 tests must pass unchanged.

**Tech Stack:** Tailwind CSS 4 (`@theme`), Google Fonts, CSS animations

**Test commands:**
- Frontend: `cd frontend && npx vitest run`
- Lint: `cd frontend && npx eslint src/`

**Design Direction — "The Archivist's Terminal":**
- **Palette:** `stone-*` warm grays (replacing cold `gray-*`), custom `ink-*` warm gold accents (replacing generic `blue-*`)
- **Typography:** Crimson Pro (serif display), Plus Jakarta Sans (body), IBM Plex Mono (IDs/citations)
- **Animations:** fade-in for messages, subtle-pulse for loading, slide-in refinement
- **Identity:** Thin header bar with app branding, evocative empty states, warm scrollbars

---

## Task 1: Theme Foundation — Fonts, Colors, Animations

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`

**Step 1: Add Google Fonts to index.html**

Replace `frontend/index.html` with:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Colonial Archives Graph-RAG</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=IBM+Plex+Mono&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Step 2: Replace index.css with theme + animations**

Replace `frontend/src/index.css` with:

```css
@import "tailwindcss";

@theme {
  /* Typography */
  --font-display: 'Crimson Pro', Georgia, serif;
  --font-body: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, monospace;

  /* Ink — warm gold accent palette */
  --color-ink-700: #8a6832;
  --color-ink-600: #a37c3c;
  --color-ink-500: #bf9650;
  --color-ink-400: #d4ad6a;
  --color-ink-300: #e3c48c;
  --color-ink-200: #eddbb4;
}

body {
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Animations */
@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes subtle-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.animate-slide-in {
  animation: slide-in 250ms cubic-bezier(0.16, 1, 0.3, 1);
}

.animate-fade-in {
  animation: fade-in 300ms ease-out both;
}

.animate-fade-in-up {
  animation: fade-in-up 400ms cubic-bezier(0.16, 1, 0.3, 1) both;
}

.animate-subtle-pulse {
  animation: subtle-pulse 1.5s ease-in-out infinite;
}

/* Warm scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #44403c; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #57534e; }
```

**Step 3: Verify dev server starts**

Run: `cd frontend && npx vite --port 5173 &` — verify no CSS compilation errors.

---

## Task 2: App Shell — Header Bar + Warm Palette

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Replace App.tsx**

Add `AppHeader` component, move admin button to header, swap `gray-*` → `stone-*`, `blue-*` → `ink-*` for tab indicators. Wrap desktop layout in flex column to accommodate header.

Replace `frontend/src/App.tsx` with:

```tsx
import { useAppStore } from "./stores/useAppStore";
import { useIsMobile } from "./hooks/useIsMobile";
import ResizableSplitter from "./components/ResizableSplitter";
import ChatPanel from "./components/ChatPanel";
import GraphCanvas from "./components/GraphCanvas";
import GraphSearchBar from "./components/GraphSearchBar";
import NodeSidebar from "./components/NodeSidebar";
import PdfModal from "./components/PdfModal";
import AdminPanel from "./components/AdminPanel";

function AppHeader() {
  const toggleAdmin = useAppStore((s) => s.toggleAdmin);

  return (
    <div className="h-10 flex items-center justify-between px-4 border-b border-stone-800/60 bg-stone-950 shrink-0">
      <div className="flex items-center gap-2.5">
        <span className="text-ink-500 text-lg leading-none select-none">&#9670;</span>
        <h1 className="font-display text-[15px] font-semibold text-stone-200 tracking-wide">
          Colonial Archives
        </h1>
      </div>
      <button
        onClick={toggleAdmin}
        className="text-stone-500 hover:text-stone-300 text-xs font-medium tracking-wide uppercase transition-colors"
      >
        Admin
      </button>
    </div>
  );
}

export default function App() {
  const splitRatio = useAppStore((s) => s.splitRatio);
  const mobileTab = useAppStore((s) => s.mobileTab);
  const setMobileTab = useAppStore((s) => s.setMobileTab);
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <div className="h-screen w-screen bg-stone-950 text-stone-100 flex flex-col overflow-hidden">
        <AppHeader />

        {/* Tab bar */}
        <div className="flex border-b border-stone-800/60 shrink-0">
          <button
            onClick={() => setMobileTab("graph")}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              mobileTab === "graph"
                ? "text-ink-400 border-b-2 border-ink-400"
                : "text-stone-500"
            }`}
          >
            Knowledge Graph
          </button>
          <button
            onClick={() => setMobileTab("chat")}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              mobileTab === "chat"
                ? "text-ink-400 border-b-2 border-ink-400"
                : "text-stone-500"
            }`}
          >
            Chat
          </button>
        </div>

        {/* Active panel */}
        <div className="flex-1 overflow-hidden">
          {mobileTab === "graph" ? (
            <div className="relative h-full bg-stone-900">
              <GraphSearchBar />
              <GraphCanvas />
              <NodeSidebar />
            </div>
          ) : (
            <ChatPanel />
          )}
        </div>

        <PdfModal />
        <AdminPanel />
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-stone-950 text-stone-100 flex flex-col overflow-hidden">
      <AppHeader />

      <div
        className="flex-1 grid min-h-0"
        style={{
          gridTemplateColumns: `${splitRatio * 100}% 4px 1fr`,
        }}
      >
        {/* Graph panel */}
        <div className="relative overflow-hidden bg-stone-900">
          <GraphSearchBar />
          <GraphCanvas />
          <NodeSidebar />
        </div>

        <ResizableSplitter />

        <ChatPanel />
      </div>

      <PdfModal />
      <AdminPanel />
    </div>
  );
}
```

**Step 2: Run tests**

Run: `cd frontend && npx vitest run`
Expected: 29 tests PASS (no logic changes).

**Step 3: Commit**

```bash
git add frontend/index.html frontend/src/index.css frontend/src/App.tsx
git commit -m "style: theme foundation + app header — warm palette, custom fonts, animations"
```

---

## Task 3: Chat Panel Polish

**Files:**
- Modify: `frontend/src/components/ChatPanel.tsx`

**Step 1: Replace ChatPanel.tsx**

Refined empty state with display font, warm loading dots, amber-accented input bar.

Replace `frontend/src/components/ChatPanel.tsx` with:

```tsx
import { useRef, useEffect } from "react";
import { useAppStore } from "../stores/useAppStore";
import ChatMessage from "./ChatMessage";
import CategoryFilter from "./CategoryFilter";

export default function ChatPanel() {
  const messages = useAppStore((s) => s.messages);
  const isQuerying = useAppStore((s) => s.isQuerying);
  const queryError = useAppStore((s) => s.queryError);
  const chatInput = useAppStore((s) => s.chatInput);
  const setChatInput = useAppStore((s) => s.setChatInput);
  const sendQuery = useAppStore((s) => s.sendQuery);

  const scrollRef = useRef<HTMLDivElement>(null);

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
    <div className="flex flex-col h-full bg-stone-950">
      {/* Message area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-xs animate-fade-in">
              <span className="text-ink-500/60 text-3xl select-none">&#9670;</span>
              <h2 className="font-display text-xl font-semibold text-stone-300 mt-3">
                Research Assistant
              </h2>
              <p className="text-stone-500 text-sm mt-2 leading-relaxed">
                Ask questions about colonial-era documents. Every answer traces back to specific archive pages.
              </p>
              <p className="text-stone-600 text-xs mt-4 italic font-display">
                Try: &ldquo;Who was the Resident of Singapore in 1830?&rdquo;
              </p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isQuerying && (
          <div className="flex justify-start mb-3 animate-fade-in">
            <div className="bg-stone-800/80 rounded-2xl px-4 py-3">
              <div className="flex gap-1.5">
                <span className="w-1.5 h-1.5 bg-ink-500 rounded-full animate-subtle-pulse" />
                <span className="w-1.5 h-1.5 bg-ink-500 rounded-full animate-subtle-pulse [animation-delay:200ms]" />
                <span className="w-1.5 h-1.5 bg-ink-500 rounded-full animate-subtle-pulse [animation-delay:400ms]" />
              </div>
            </div>
          </div>
        )}
        {queryError && (
          <div className="mb-3 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg animate-fade-in">
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

      <CategoryFilter />

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="border-t border-stone-800/60 px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask about the archives..."
            className="flex-1 bg-stone-800/60 text-stone-100 rounded-lg px-4 py-2.5 text-sm outline-none border border-stone-700/50 focus:border-ink-500/50 focus:ring-1 focus:ring-ink-500/30 placeholder:text-stone-500 transition-colors"
            disabled={isQuerying}
          />
          <button
            type="submit"
            disabled={isQuerying || !chatInput.trim()}
            className="bg-ink-600 hover:bg-ink-500 disabled:bg-stone-800 disabled:text-stone-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
```

---

## Task 4: Chat Messages + Citations + Category Filter

**Files:**
- Modify: `frontend/src/components/ChatMessage.tsx`
- Modify: `frontend/src/components/CitationBadge.tsx`
- Modify: `frontend/src/components/CategoryFilter.tsx`

**Step 1: Replace ChatMessage.tsx**

User bubbles → warm `ink-600`, assistant bubbles → `stone-800/80`, fade-in animation, warmer prose styling.

Replace `frontend/src/components/ChatMessage.tsx` with:

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
      <div className="flex justify-end mb-3 animate-fade-in">
        <div className="bg-ink-600 rounded-2xl rounded-br-sm px-4 py-2 max-w-[85%]">
          <p className="text-sm whitespace-pre-wrap text-white">{message.content}</p>
        </div>
      </div>
    );
  }

  const segments = parseCitations(message.content, message.citations ?? []);

  const sourceLabel =
    message.source_type === "mixed"
      ? "Archive + Web"
      : message.source_type === "web_fallback"
        ? "Web sources"
        : null;

  return (
    <div className="flex justify-start mb-3 animate-fade-in">
      <div className="bg-stone-800/80 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
        <div className="text-sm prose prose-invert prose-sm max-w-none prose-p:text-stone-200 prose-strong:text-stone-100">
          {segments.map((seg, i) =>
            seg.type === "text" ? (
              <Markdown key={i}>{seg.content}</Markdown>
            ) : (
              <CitationBadge key={i} citation={seg.citation} />
            )
          )}
        </div>
        {sourceLabel && (
          <div className="mt-2 pt-2 border-t border-stone-700/50">
            <span className="text-xs text-stone-500 font-medium tracking-wide">{sourceLabel}</span>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Replace CitationBadge.tsx**

Archive badges → warm `ink` palette with mono font, web badges → keep emerald.

Replace `frontend/src/components/CitationBadge.tsx` with:

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
        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-medium bg-ink-500/20 text-ink-400 hover:bg-ink-500/30 transition-colors cursor-pointer font-mono"
        title={citation.text_span}
        onClick={() => openPdfModal(citation.doc_id, citation.pages[0])}
      >
        {citation.doc_id}:p{citation.pages.join(",")}
      </button>
    );
  }

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

**Step 3: Replace CategoryFilter.tsx**

Active pills → `ink-600`, inactive → `stone-800`.

Replace `frontend/src/components/CategoryFilter.tsx` with:

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
    <div className="flex flex-wrap gap-1.5 px-4 py-2 border-b border-stone-800/60">
      {MAIN_CATEGORIES.map((cat) => {
        const active = filterCategories.includes(cat);
        return (
          <button
            key={cat}
            onClick={() => toggle(cat)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              active
                ? "bg-ink-600 text-white"
                : "bg-stone-800 text-stone-400 hover:bg-stone-700 hover:text-stone-300"
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

**Step 4: Run tests + commit**

Run: `cd frontend && npx vitest run`
Expected: 29 tests PASS.

```bash
git add frontend/src/components/ChatPanel.tsx frontend/src/components/ChatMessage.tsx frontend/src/components/CitationBadge.tsx frontend/src/components/CategoryFilter.tsx
git commit -m "style: chat panel polish — warm bubbles, ink citations, refined empty state"
```

---

## Task 5: Graph Panel Polish

**Files:**
- Modify: `frontend/src/components/GraphCanvas.tsx`
- Modify: `frontend/src/components/GraphSearchBar.tsx`

**Step 1: Update GraphCanvas.tsx**

Warmer Cytoscape stylesheet colors, refined empty state with display font.

In `frontend/src/components/GraphCanvas.tsx`, make these changes:

**Change 1 — Empty state** (replace the `if (!graphData)` block):

```tsx
  if (!graphData) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-xs animate-fade-in">
          <div className="flex justify-center gap-3 text-stone-700 text-lg mb-3 select-none">
            <span>&#9671;</span><span>&#9671;</span><span>&#9671;</span>
          </div>
          <h3 className="font-display text-base font-medium text-stone-400">
            Knowledge Graph
          </h3>
          <p className="text-stone-600 text-sm mt-1.5">
            Ask a question or search for an entity to explore the document network.
          </p>
        </div>
      </div>
    );
  }
```

**Change 2 — Cytoscape stylesheet** (update colors in the `stylesheet` useMemo):

```tsx
  const stylesheet = useMemo(
    () => [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "background-color": "data(color)",
          "text-valign": "bottom",
          "text-halign": "center",
          "font-size": "10px",
          "font-family": "'Plus Jakarta Sans', system-ui, sans-serif",
          color: "#d6d3d1",
          "text-margin-y": 6,
          width: 40,
          height: 40,
          shape: "round-rectangle",
          "border-width": 2,
          "border-color": "data(color)",
        },
      },
      {
        selector: "node[?highlighted]",
        style: {
          "border-color": "#d4ad6a",
          "border-width": 4,
          "background-color": "data(color)",
        },
      },
      {
        selector: "node:active",
        style: {
          "overlay-opacity": 0.1,
        },
      },
      {
        selector: "edge",
        style: {
          label: "data(label)",
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.8,
          "line-color": "#57534e",
          "target-arrow-color": "#57534e",
          "font-size": "8px",
          "font-family": "'Plus Jakarta Sans', system-ui, sans-serif",
          color: "#a8a29e",
          "text-rotation": "autorotate",
          width: 1.5,
        },
      },
      {
        selector: "edge[?highlighted]",
        style: {
          "line-color": "#d4ad6a",
          "target-arrow-color": "#d4ad6a",
          width: 3,
        },
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ] as any,
    []
  );
```

Key color changes:
- Node labels: `#E5E7EB` (gray-200) → `#d6d3d1` (stone-300)
- Highlight border: `#F97316` (orange) → `#d4ad6a` (ink-400, warm gold)
- Edge lines: `#4B5563` (gray-600) → `#57534e` (stone-600)
- Edge labels: `#9CA3AF` (gray-400) → `#a8a29e` (stone-400)
- Highlight edges: `#F97316` → `#d4ad6a` (ink-400)

**Step 2: Replace GraphSearchBar.tsx**

Warm tones, ink focus ring, refined border.

Replace `frontend/src/components/GraphSearchBar.tsx` with:

```tsx
import { useGraphSearch } from "../hooks/useGraphSearch";

export default function GraphSearchBar() {
  const { query, search, isSearching } = useGraphSearch();

  return (
    <div className="absolute top-3 left-3 right-3 z-10">
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500"
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
          className="w-full bg-stone-800/90 backdrop-blur-sm text-stone-100 rounded-lg pl-10 pr-4 py-2 text-sm outline-none border border-stone-700/50 focus:border-ink-500/50 focus:ring-1 focus:ring-ink-500/30 placeholder:text-stone-500 transition-colors"
        />
        {isSearching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-ink-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx frontend/src/components/GraphSearchBar.tsx
git commit -m "style: graph panel polish — warm Cytoscape theme, refined empty state + search"
```

---

## Task 6: Node Sidebar + Splitter

**Files:**
- Modify: `frontend/src/components/NodeSidebar.tsx`
- Modify: `frontend/src/components/ResizableSplitter.tsx`

**Step 1: Replace NodeSidebar.tsx**

Display font for entity name, mono font for canonical ID, warm palette, ink-accented CTA button.

Replace `frontend/src/components/NodeSidebar.tsx` with:

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
    <div className="absolute top-0 right-0 h-full w-[300px] bg-stone-900 border-l border-stone-700/60 z-20 flex flex-col shadow-2xl animate-slide-in">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-stone-800/60">
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-display font-semibold text-stone-100 truncate">
            {selectedNode.name}
          </h2>
          <p className="text-xs text-stone-500 mt-0.5 truncate font-mono">
            {selectedNode.canonical_id}
          </p>
        </div>
        <button
          onClick={() => selectNode(null)}
          className="text-stone-400 hover:text-stone-200 ml-2 p-1 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {selectedNode.main_categories.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1.5">Categories</h3>
            <div className="flex flex-wrap gap-1">
              {selectedNode.main_categories.map((cat) => (
                <span
                  key={cat}
                  className="px-2 py-0.5 bg-stone-800 text-stone-300 rounded text-xs"
                >
                  {cat}
                </span>
              ))}
            </div>
          </div>
        )}

        {selectedNode.sub_category && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1">Sub-category</h3>
            <p className="text-sm text-stone-300">{selectedNode.sub_category}</p>
          </div>
        )}

        {Object.keys(attrs).length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-1.5">Attributes</h3>
            <table className="w-full text-xs">
              <tbody>
                {Object.entries(attrs).map(([key, val]) => (
                  <tr key={key} className="border-b border-stone-800/60">
                    <td className="py-1.5 pr-2 text-stone-500 font-medium align-top whitespace-nowrap">
                      {key}
                    </td>
                    <td className="py-1.5 text-stone-300 break-words">
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
      <div className="p-4 border-t border-stone-800/60">
        <button
          onClick={() => {
            setChatInput(`Tell me about ${selectedNode.name}`);
            selectNode(null);
          }}
          className="w-full bg-ink-600 hover:bg-ink-500 text-white text-sm font-medium py-2 rounded-lg transition-colors"
        >
          Ask about this entity
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Update ResizableSplitter.tsx**

In `frontend/src/components/ResizableSplitter.tsx`, change the JSX className:

Old:
```
className="bg-gray-700 cursor-col-resize hover:bg-blue-500 active:bg-blue-400 transition-colors"
```

New:
```
className="bg-stone-700 cursor-col-resize hover:bg-ink-500 active:bg-ink-400 transition-colors"
```

**Step 3: Commit**

```bash
git add frontend/src/components/NodeSidebar.tsx frontend/src/components/ResizableSplitter.tsx
git commit -m "style: sidebar + splitter — display font entity names, warm accents"
```

---

## Task 7: Modal Polish

**Files:**
- Modify: `frontend/src/components/PdfModal.tsx`
- Modify: `frontend/src/components/AdminPanel.tsx`

**Step 1: Update PdfModal.tsx colors**

In `frontend/src/components/PdfModal.tsx`, apply these class replacements throughout the file:

| Old | New |
|-----|-----|
| `bg-gray-900` | `bg-stone-900` |
| `border-gray-700` | `border-stone-700/60` |
| `text-gray-300` | `text-stone-300` |
| `text-gray-500` | `text-stone-500` |
| `text-gray-400 hover:text-white` | `text-stone-400 hover:text-stone-100` |
| `text-gray-600` | `text-stone-600` |
| `border-gray-400` | `border-ink-400` |

Also add `animate-fade-in-up` to the modal container:

```
<div className="bg-stone-900 rounded-xl shadow-2xl flex flex-col max-w-[90vw] max-h-[90vh] w-[800px] animate-fade-in-up">
```

And update the loading spinner border color:

```
<div className="w-8 h-8 border-2 border-ink-400 border-t-transparent rounded-full animate-spin" />
```

**Step 2: Update AdminPanel.tsx colors**

In `frontend/src/components/AdminPanel.tsx`, apply these class replacements:

| Old | New |
|-----|-----|
| `bg-gray-900` | `bg-stone-900` |
| `border-gray-700` | `border-stone-700/60` |
| `text-gray-200` | `text-stone-200` |
| `text-gray-400 hover:text-white` | `text-stone-400 hover:text-stone-100` |
| `text-gray-500` | `text-stone-500` |
| `text-gray-300` | `text-stone-300` |
| `bg-gray-700` | `bg-stone-700` |
| `text-gray-300 hover:bg-gray-800` | `text-stone-300 hover:bg-stone-800` |
| `border-gray-400` | `border-ink-400` |

Also add to the header:

```tsx
<h2 className="text-sm font-display font-semibold text-stone-200">
```

And the modal container:

```
<div className="bg-stone-900 rounded-xl shadow-2xl w-[700px] max-h-[80vh] flex flex-col animate-fade-in-up">
```

And the loading spinner:

```
<div className="w-6 h-6 border-2 border-ink-400 border-t-transparent rounded-full animate-spin" />
```

**Step 3: Run all tests + lint**

Run: `cd frontend && npx vitest run`
Expected: 29 tests PASS.

Run: `cd frontend && npx eslint src/`
Expected: No errors.

**Step 4: Commit**

```bash
git add frontend/src/components/PdfModal.tsx frontend/src/components/AdminPanel.tsx
git commit -m "style: modal polish — warm palette, fade-in animation, refined borders"
```

---

## Task 8: Final Verification

**Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: 29 tests PASS — no logic was changed, only CSS classes.

**Step 2: Run ESLint**

Run: `cd frontend && npx eslint src/`
Expected: Clean (0 errors, 0 warnings).

**Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc -b`
Expected: No type errors (no type signatures changed).

**Step 4: Visual verification**

Start dev server: `cd frontend && npx vite`

Verify:
- [ ] Header bar shows "Colonial Archives" in serif font with diamond icon
- [ ] Graph panel has warm empty state with display font
- [ ] Chat panel has refined welcome screen with serif heading
- [ ] User messages appear as warm gold bubbles (ink-600)
- [ ] Assistant messages appear in warm dark stone bubbles
- [ ] Citation badges use warm gold (archive) and green (web)
- [ ] Loading dots pulse in warm gold
- [ ] Input field has ink-gold focus ring
- [ ] Send button is warm gold
- [ ] Category filter pills use warm gold active state
- [ ] Graph nodes render with warm highlight color (gold, not orange)
- [ ] Node sidebar shows entity name in serif display font
- [ ] PDF modal appears with fade-in-up animation
- [ ] Mobile layout works with tabs and header
- [ ] Scrollbars are warm-toned
- [ ] All text uses Plus Jakarta Sans body font

---

## Design Summary

| Element | Before | After |
|---------|--------|-------|
| **Background** | Cold `gray-950/900/800` | Warm `stone-950/900/800` |
| **Primary Accent** | Generic `blue-600` | Warm gold `ink-600` |
| **Focus Rings** | `blue-500` | `ink-500/30` with border |
| **User Bubbles** | `blue-600` | `ink-600` (warm amber) |
| **Display Font** | System default | Crimson Pro (serif) |
| **Body Font** | System default | Plus Jakarta Sans |
| **Mono Font** | System default | IBM Plex Mono |
| **Loading Dots** | Gray bouncing | Gold subtle-pulse |
| **Graph Highlights** | `orange-500` | `ink-400` (warm gold) |
| **Animations** | Only slide-in | fade-in, fade-in-up, subtle-pulse |
| **Scrollbars** | Default | Custom warm-toned |
| **Empty States** | Plain text | Display font + icon + suggestion |
| **Input Borders** | None | Subtle border + ink focus glow |
| **Category Pills** | Blue active | Gold active |
| **App Identity** | None | Header bar with serif branding |
