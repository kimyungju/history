# Data Ingestion, Integration Testing & Repository Setup — Strategic Plan

**Last Updated: 2026-03-01**

---

## Executive Summary

The Colonial Archives Graph-RAG system has Phases 1-3 code complete but only 1 of 28 available PDFs ingested, no git version control, and an empty document category mapping. This plan addresses all four gaps in a single coordinated push using multiple agent teams to maximize parallelism where possible.

**Deliverables:**
1. Git repository initialized with clean first commit
2. All 28 PDFs mapped to archive categories in `document_categories.json`
3. 10 additional PDFs ingested (total 11 of 28) with entities in Neo4j and vectors in Vertex AI
4. End-to-end frontend integration verified against live backend with real data

---

## Current State Analysis

| Area | Status | Gap |
|------|--------|-----|
| **Version Control** | No `.git/` directory | Cannot track changes, no deployment pipeline possible |
| **Category Mapping** | `document_categories.json` has only example entries | Ingested docs get empty categories, category-filtered queries broken |
| **Data Volume** | 1 PDF ingested (CO 273:550:18, 6 pages, 2 chunks, 19 entities) | Insufficient for meaningful queries — LLM returns "I cannot answer" |
| **Frontend Integration** | Builds and serves, proxy works, basic query tested | Not validated with sufficient data for graph viz, citations, category filter |

### Available PDFs in GCS Bucket (`aihistory-co273-nus`)

| Size Tier | Count | Files | Ingestion Risk |
|-----------|-------|-------|----------------|
| Small (< 12 MB) | 5 | :550:5, :550:11, :550:10, :534:11b, :550:21 | Low — fast OCR |
| Medium (12-30 MB) | 5 | :534:6, :534:7, :534:13, :534:5, :534:24 | Low — moderate OCR time |
| Large (30-100 MB) | 8 | :579:4, :550:13, :550:1, :550:3, :550:14, :550:19, :534:9, :534:15b | Medium — long OCR, potential timeouts |
| XL (100+ MB) | 9 | :534:2, :579:2b, :579:3, :550:8, :579:1, :534:15a, :534:3, :534:11a, :579:2a | High — may need manual monitoring |
| **Already ingested** | 1 | :550:18 (3.2 MB) | N/A |

**Strategy:** Ingest all Small + Medium tier (10 PDFs) this session. Large/XL deferred to a future session with monitoring.

---

## Proposed Future State

After execution:
- **Git**: Clean repo with 2-3 commits documenting Phases 1-3 and category setup
- **Categories**: All 28 PDFs mapped (refinable after content analysis)
- **Data**: 11 PDFs ingested → ~100+ chunks, ~200+ entities, rich graph for queries
- **Frontend**: Validated with real multi-document data, all components confirmed working

---

## Implementation Phases

### Phase A: Foundation (Sequential — Must Complete First)

**Rationale:** Git init and category config are prerequisites for everything else. Fast, no external dependencies beyond filesystem.

| Task | Effort | Depends On | Agent |
|------|--------|------------|-------|
| A1: Initialize git repo | S | None | setup-agent |
| A2: Update document_categories.json | S | None (can parallel with A1) | setup-agent |
| A3: Commit foundation changes | S | A1, A2 | setup-agent |

### Phase B: Data Ingestion (Long-Running — Backend Required)

**Rationale:** Ingestion is async and I/O-bound (GCS download, Document AI OCR, Gemini entity extraction). Multiple PDFs can be submitted concurrently since the backend processes them independently. However, submitting too many at once risks Gemini rate limits and Document AI quota exhaustion.

**Strategy:** Submit in 2 batches of 5, polling between batches.

| Task | Effort | Depends On | Agent |
|------|--------|------------|-------|
| B1: Start backend, verify health | S | A3 | ingestion-agent |
| B2: Ingest Batch 1 (5 small PDFs) | L | B1 | ingestion-agent |
| B3: Ingest Batch 2 (5 medium PDFs) | L | B2 | ingestion-agent |
| B4: Verify cumulative data volume | S | B3 | ingestion-agent |

### Phase C: Integration Testing (Depends on Data)

**Rationale:** Frontend testing requires ingested data to validate graph rendering, citations, and category filters. Can only start after Phase B provides sufficient entities.

| Task | Effort | Depends On | Agent |
|------|--------|------------|-------|
| C1: Start frontend, verify proxy | S | B2 (minimum) | testing-agent |
| C2: API smoke tests (query, graph search, subgraph) | M | C1 | testing-agent |
| C3: Browser integration test checklist | M | C2 | testing-agent (manual) |
| C4: Record results and final commit | S | C3 | testing-agent |

---

## Agent Team Structure

```
                    +-----------------+
                    |   Team Lead     |
                    | (orchestrator)  |
                    +--------+--------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v-------+  +---v----------+
     | setup-agent|  |ingestion-agent|  |testing-agent |
     | Phase A    |  | Phase B       |  | Phase C      |
     | (fast)     |  | (long-running)|  | (after data) |
     +------------+  +---------------+  +--------------+
```

### Agent Responsibilities

**setup-agent** (general-purpose, ~5 min)
- Initialize git repo
- Write `document_categories.json`
- Create initial commit
- **Completes before ingestion starts**

**ingestion-agent** (general-purpose, ~20-30 min)
- Start backend server (background process)
- Submit 10 ingestion jobs in 2 batches
- Poll job status until all complete
- Verify entity counts
- **Long-running — most time spent waiting for OCR/entity extraction**

**testing-agent** (general-purpose, ~10 min)
- Start frontend dev server
- Run API smoke tests via curl
- Document browser test checklist results
- Final commit
- **Can start after Batch 1 completes (doesn't need all 10 PDFs)**

### Parallelism Opportunities

| Parallel Window | Agents Active | What's Happening |
|-----------------|---------------|------------------|
| Phase A | setup-agent only | Git init + categories (fast, sequential) |
| Phase B start | ingestion-agent only | Backend startup + Batch 1 submission |
| Phase B mid → C start | ingestion-agent + testing-agent | Batch 2 ingesting while frontend tests run on Batch 1 data |
| Phase C | testing-agent only | Browser tests + final commit |

**Key constraint:** testing-agent can start after Batch 1 (5 PDFs) completes — it doesn't need all 10. This creates a ~10 minute parallelism window where Batch 2 ingestion runs alongside frontend testing.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Neo4j AuraDB paused (3-day inactivity) | High | Blocks ingestion steps 7-9 | Auto-resumes on connection; retry after 30s |
| Document AI quota exceeded | Low | Batch fails, need retry | Submit 5 at a time, not all 10 |
| Gemini rate limit (entity extraction) | Medium | Graph steps fail (vector ingestion still succeeds) | Non-blocking — graph failures logged, retry later |
| GCP auth expired | Low | All GCP calls fail | Run `gcloud auth application-default login` in PowerShell |
| Large PDF OCR timeout | Low (small/medium only) | Job hangs or fails | Only ingesting PDFs < 30 MB this session |
| Frontend proxy misconfigured | Low | API calls fail from browser | Already verified working (port 8090 in vite.config.ts) |

---

## Success Metrics

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Git repo initialized | 2-3 clean commits | `git log --oneline` |
| Categories mapped | 28 entries in JSON | `python -c "import json; print(len(...))"` |
| PDFs ingested | 11 total (1 existing + 10 new) | All job statuses = "done" |
| Entities in Neo4j | 100+ | `GET /graph/search?q=&limit=500` |
| Query returns answers | Non-empty answer with citations | `POST /query` with general question |
| Graph renders in frontend | Nodes + edges visible | Browser check |
| Category filter works | Different results per category | Filtered vs unfiltered query comparison |

---

## Required Resources & Dependencies

| Resource | Status | Notes |
|----------|--------|-------|
| GCP Project (`aihistory-488807`) | Active | All services provisioned |
| GCP Auth (ADC) | Required | `gcloud auth application-default login` (PowerShell) |
| Neo4j AuraDB | May be paused | Auto-resumes; URI: `neo4j+s://ae76ab7c.databases.neo4j.io` |
| Python 3.13 + backend deps | Installed | `C:\Users\yjkim\AppData\Local\Programs\Python\Python313\python.exe` |
| Node.js + frontend deps | Installed | `frontend/node_modules/` should exist |
| Port 8090 | Must be free | Backend server |
| Port 5173 | Must be free | Frontend dev server |

---

## Timeline Estimate

| Phase | Duration | Bottleneck |
|-------|----------|------------|
| A: Foundation | ~5 min | None — filesystem ops |
| B: Ingestion | ~20-30 min | Document AI OCR + Gemini entity extraction |
| C: Testing | ~10-15 min | Manual browser checks |
| **Total** | **~35-50 min** | Ingestion wait time dominates |

---

## Reference Documents

- **Detailed implementation plan:** `docs/plans/2026-03-01-data-ingestion-and-integration.md`
- **Architecture context:** `dev/active/colonial-archives-graph-rag/colonial-archives-graph-rag-context.md`
- **Master task tracker:** `dev/active/colonial-archives-graph-rag/colonial-archives-graph-rag-tasks.md`
- **Backend code:** `backend/app/` (21 Python modules)
- **Frontend code:** `frontend/src/` (23 TypeScript/TSX files)
