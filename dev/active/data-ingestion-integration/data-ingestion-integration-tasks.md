# Data Ingestion & Integration — Task Tracker

**Last Updated: 2026-03-01**

---

## Phase A: Foundation (setup-agent)

- [ ] **A1: Initialize git repository**
  - Verify `.gitignore` covers `.env`, `__pycache__/`, `node_modules/`
  - Run `git init` in project root
  - Verify no secrets in staged files
  - Effort: S | Depends: None

- [ ] **A2: Populate document_categories.json**
  - Replace example entries with all 28 PDF-to-category mappings
  - CO 273:534 → `["General and Establishment"]`
  - CO 273:550 → `["General and Establishment", "Economic and Financial"]`
  - CO 273:579 → `["General and Establishment"]`
  - Validate JSON syntax
  - Verify all category values match `MAIN_CATEGORIES`
  - Effort: S | Depends: None

- [ ] **A3: Create initial commit**
  - Stage all files (`git add -A`)
  - Commit with descriptive message covering Phases 1-3
  - Verify with `git log --oneline`
  - Effort: S | Depends: A1, A2

---

## Phase B: Data Ingestion (ingestion-agent)

- [ ] **B1: Start backend and verify health**
  - `cd backend && uvicorn app.main:app --port 8090`
  - `GET /health` → `{"status": "ok", "neo4j": "connected"}`
  - If Neo4j disconnected, wait 30-60s for AuraDB auto-resume
  - Effort: S | Depends: A3

- [ ] **B2: Ingest Batch 1 — 5 small PDFs (5.8-11.3 MB)**
  - Submit: CO 273:550:5.pdf (5.8 MB)
  - Submit: CO 273:550:11.pdf (6.2 MB)
  - Submit: CO 273:550:10.pdf (7.9 MB)
  - Submit: CO 273:534:11b.pdf (9.5 MB)
  - Submit: CO 273:550:21.pdf (11.3 MB)
  - Poll all 5 job_ids until status = "done"
  - Verify entity count via `/graph/search?q=&limit=50`
  - Target: 50+ total entities (was 19 from single doc)
  - Effort: L | Depends: B1

- [ ] **B3: Ingest Batch 2 — 5 medium PDFs (14.6-29.5 MB)**
  - Submit: CO 273:534:6.pdf (14.6 MB)
  - Submit: CO 273:534:7.pdf (17.3 MB)
  - Submit: CO 273:534:13.pdf (23.1 MB)
  - Submit: CO 273:534:5.pdf (27.9 MB)
  - Submit: CO 273:534:24.pdf (29.5 MB)
  - Poll all 5 job_ids until status = "done"
  - Effort: L | Depends: B2

- [ ] **B4: Verify cumulative data volume**
  - `/graph/search?q=&limit=500` → count total entities
  - Target: 100+ entities across categories
  - List entity counts by category
  - Effort: S | Depends: B3

---

## Phase C: Integration Testing (testing-agent)

- [ ] **C1: Start frontend and verify proxy**
  - `cd frontend && npm run dev` (install deps if needed)
  - `GET http://localhost:5173/api/health` → must return backend health response
  - Effort: S | Depends: B2 (at minimum)

- [ ] **C2: API smoke tests via curl**
  - Test query: `POST /query` with "What were the main economic activities in the Straits Settlements?"
  - Verify: non-empty answer, citations array, graph payload with nodes/edges
  - Test graph search: `GET /graph/search?q=Straits&limit=10`
  - Verify: entities returned with categories
  - Test subgraph: `GET /graph/{canonical_id}` using ID from search
  - Verify: nodes, edges, center_node populated
  - Test filtered query: `POST /query` with `filter_categories: ["Economic and Financial"]`
  - Verify: results differ from unfiltered query
  - Effort: M | Depends: C1

- [ ] **C3: Manual browser test checklist**
  - Open `http://localhost:5173` in browser
  - [ ] Chat panel: type question → answer with `[archive:N]` badges
  - [ ] Graph canvas: nodes and edges render after query
  - [ ] Node click: opens NodeSidebar with entity details
  - [ ] Citation badge click: opens PdfModal
  - [ ] PDF viewer: document page loads via signed URL
  - [ ] Graph search bar: type entity name → results in graph
  - [ ] Category filter: toggle category → changes query results
  - [ ] Resizable splitter: drag between graph and chat panels
  - Document any failures for follow-up
  - Effort: M | Depends: C2

- [ ] **C4: Record results and final commit**
  - Record: total entities, ingested doc count, test pass/fail summary
  - Commit any changed files (context doc updates, etc.)
  - Verify git log shows clean history
  - Effort: S | Depends: C3

---

## Summary

| Phase | Tasks | Total Effort | Agent | Status |
|-------|-------|-------------|-------|--------|
| A: Foundation | A1-A3 | S | setup-agent | Not started |
| B: Ingestion | B1-B4 | L | ingestion-agent | Not started |
| C: Testing | C1-C4 | M | testing-agent | Not started |

**Critical Path:** A1 → A3 → B1 → B2 → C1 → C2 → C3 → C4

**Parallelism:** B3 (Batch 2 ingestion) can run while C1-C2 (frontend testing) execute.

**Estimated Total Time:** 35-50 minutes (dominated by ingestion wait time).
