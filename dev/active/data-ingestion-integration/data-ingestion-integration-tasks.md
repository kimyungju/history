# Data Ingestion & Integration — Task Tracker

**Last Updated: 2026-03-01**

---

## Phase A: Foundation (setup-agent) — COMPLETE ✅

- [x] **A1: Initialize git repository**
  - `.gitignore` verified, `git init` done
  - Effort: S | Depends: None

- [x] **A2: Populate document_categories.json**
  - All 28 PDF-to-category mappings populated
  - CO 273:534 → `["General and Establishment"]`
  - CO 273:550 → `["General and Establishment", "Economic and Financial"]`
  - CO 273:579 → `["General and Establishment"]`
  - Effort: S | Depends: None

- [x] **A3: Create initial commit**
  - Committed with all Phase 1-3 code
  - Effort: S | Depends: A1, A2

---

## Phase B: Data Ingestion (ingestion-agent) — MOSTLY COMPLETE

- [x] **B1: Start backend and verify health**
  - Backend on port 8090, Neo4j connected
  - Effort: S | Depends: A3

- [x] **B2: Ingest Batch 1 — 5 small PDFs (5.8-11.3 MB)** ✅
  - CO 273:550:5.pdf ✅
  - CO 273:550:11.pdf ✅
  - CO 273:550:10.pdf ✅
  - CO 273:534:11b.pdf ✅
  - CO 273:550:21.pdf ✅
  - 3 bugs found and fixed during this batch (vector search restriction class, duplicate namespace, region contamination)
  - Effort: L | Depends: B1

- [x] **B3: Ingest Batch 2 — 5 medium PDFs (14.6-29.5 MB)** ✅
  - CO 273:534:6.pdf ✅ (vector only, no graph entities — Gemini rate-limited)
  - CO 273:534:7.pdf ✅
  - CO 273:534:13.pdf ✅
  - CO 273:534:5.pdf ✅
  - CO 273:534:24.pdf ✅
  - Effort: L | Depends: B2

- [x] **B4: Verify cumulative data volume** ✅
  - 100+ entities across categories
  - Effort: S | Depends: B3

- [x] **B5: Ingest large PDFs (50-78 MB)** — ADDED
  - CO 273:579:4.pdf ✅ (confirmed)
  - CO 273:550:1.pdf ✅ (43 pages, 57 chunks — confirmed)
  - CO 273:579:3.pdf ✅ (agent task completed)
  - Required 5 more bug fixes: Document AI 40MB limit (pypdf splitting), embedding batch size, blocking GCS download, sequential entity extraction, blocking GCS uploads
  - Effort: XL | Depends: B4

- [ ] **B6: Ingest remaining PDFs** — BLOCKED
  - CO 273:550:3.pdf — unknown status
  - CO 273:550:14.pdf — unknown status
  - CO 273:550:19.pdf — unknown status
  - CO 273:550:13.pdf — unknown status
  - CO 273:534:9.pdf — unknown status
  - CO 273:534:15b.pdf — unknown status
  - CO 273:579:2b.pdf — unknown status
  - CO 273:579:1.pdf — unknown status
  - CO 273:550:8.pdf — unknown status
  - Effort: XL | Depends: B5

- [ ] **B7: Investigate very large PDF failures (> 95 MB)** — NEW
  - CO 273:534:15a.pdf — FAILED (0 pages)
  - CO 273:534:2.pdf — FAILED (0 pages)
  - CO 273:534:11a.pdf — FAILED (0 pages)
  - CO 273:534:3.pdf — FAILED (0 pages)
  - CO 273:579:2a.pdf — FAILED (0 pages)
  - Root cause: suspected memory pressure or GCS download timeout for files > 95 MB
  - Effort: L | Depends: None

- [ ] **B8: Re-ingest CO 273:534:6 for graph entities** — NEW
  - Has vector data but no entities in Neo4j (Gemini was rate-limited during concurrent processing)
  - Effort: S | Depends: None

---

## Phase C: Integration Testing (testing-agent) — MOSTLY COMPLETE

- [x] **C1: Start frontend and verify proxy** ✅
  - Frontend on port 5173, proxy to backend 8090 works
  - Effort: S | Depends: B2

- [x] **C2: API smoke tests via curl** — 6/7 PASS
  - ✅ POST /query — returns answer + citations + graph
  - ✅ GET /graph/search — returns entities with categories
  - ✅ GET /graph/{canonical_id} — returns subgraph
  - ✅ POST /query with filter_categories — different results
  - ✅ GET /health — returns ok + neo4j connected
  - ✅ GET /ingest_status — returns job status
  - ❌ GET /document/signed_url — returns HTTP 500
  - Effort: M | Depends: C1

- [ ] **C3: Fix signed URL endpoint** — NEW
  - `GET /document/signed_url` returns 500
  - Need to investigate root cause
  - Effort: M | Depends: C2

- [ ] **C4: Manual browser test checklist** — PARTIALLY DONE
  - [x] Chat panel: questions return answers with citation badges
  - [x] Graph canvas: nodes and edges render after query
  - [ ] Citation badge → PdfModal (blocked by signed URL 500)
  - [ ] PDF viewer (blocked by signed URL 500)
  - [ ] Node click → NodeSidebar
  - [ ] Graph search bar
  - [ ] Category filter toggle
  - [ ] Resizable splitter
  - Effort: M | Depends: C3

- [ ] **C5: Record results and final commit**
  - Effort: S | Depends: C4

---

## Bugs Fixed This Session (8 total)

| # | Bug | File | Commit |
|---|-----|------|--------|
| 1 | Vector Search Restriction class mismatch | `vector_search.py` | `74e34c6` |
| 2 | Duplicate namespace in restricts | `vector_search.py` | `74e34c6` |
| 3 | Region contamination from vertexai.init | `vector_search.py` | `74e34c6` |
| 4 | Document AI 40MB inline limit | `ocr.py`, `requirements.txt` | `74e34c6` |
| 5 | Embedding 20K token batch limit | `embeddings.py` | `f55a956` |
| 6 | Blocking GCS download | `ingest.py`, `storage.py` | `f55a956` |
| 7 | Sequential entity extraction | `entity_extraction.py` | `f55a956` |
| 8 | Blocking GCS uploads | `ingest.py` | `f55a956` |

---

## Summary

| Phase | Tasks | Status | Completion |
|-------|-------|--------|------------|
| A: Foundation | A1-A3 | COMPLETE ✅ | 3/3 |
| B: Ingestion | B1-B8 | In Progress | 5/8 (B1-B5 done) |
| C: Testing | C1-C5 | In Progress | 2/5 (C1-C2 done) |

**Blocking Issues:**
1. Signed URL 500 error blocks PDF viewer testing (C3-C4)
2. Very large PDFs (> 95 MB) fail with 0 pages (B7)
3. CO 273:534:6 missing graph entities (B8)
4. Several PDFs with unknown ingestion status (B6)

**Next Session Priority:**
1. Check status of unknown PDFs (start backend, query Neo4j)
2. Fix signed URL endpoint
3. Complete browser test checklist
4. Investigate large PDF failures
