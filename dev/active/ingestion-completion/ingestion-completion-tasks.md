# Ingestion Completion Tasks

**Last Updated: 2026-03-01**

## Phase A: Verify Fixes

- [ ] **A1** Start backend server (`uvicorn app.main:app --reload --port 8090`) [S]
- [ ] **A2** Hit `GET /health` — confirm Neo4j connected (wake if needed, wait 60s) [S]
- [ ] **A3** Test signed URL: `GET /document/signed_url?doc_id=CO 273:550:18` — expect URL (not 500) [S]
- [ ] **A4** Test proxy: `GET /document/proxy/CO 273:550:18` — expect PDF bytes [S]
- [ ] **A5** Test entity retry: `POST /retry_entities {"doc_id": "CO 273:550:1"}` — expect entities > 0 [S]

## Phase B: Entity Retry for Vector-Only PDFs

_Prerequisite: A2, A5 pass_
_Run ONE AT A TIME, wait for completion_

- [ ] **B1** Retry entities: `CO 273:550:3` (39 chunks) [S]
- [ ] **B2** Retry entities: `CO 273:550:1` (57 chunks) [S]
- [ ] **B3** Retry entities: `CO 273:550:14` (~80 chunks) [M]
- [ ] **B4** Retry entities: `CO 273:579:2b` (94 chunks) [M]
- [ ] **B5** Retry entities: `CO 273:550:19` (101 chunks) [M]
- [ ] **B6** Retry entities: `CO 273:579:1` (170 chunks) [M]
- [ ] **B7** Retry entities: `CO 273:534:15b` (195 chunks) [L]
- [ ] **B8** Retry entities: `CO 273:534:6` (missing graph data) [S]

**Acceptance**: Each returns `entities_extracted > 0` and `relationships_extracted > 0`

## Phase C: Re-ingest Medium-Failed PDFs

_Prerequisite: Phase A passes_
_Run ONE AT A TIME_

- [ ] **C1** Re-ingest `CO 273:534:9` via `/ingest_pdf` (previously quota-failed) [M]
  - Poll `/ingest_status/{job_id}` until `status: "done"`
  - Accept: `pages_total > 0`, `entities_extracted > 0`
- [ ] **C2** Re-ingest `CO 273:550:8` via `/ingest_pdf` (~125 MB, unknown failure) [L]
  - Accept: `pages_total > 0`, `entities_extracted > 0`

## Phase D: Re-ingest XL PDFs

_Prerequisite: Phase A passes, Phase C ideally done_
_Run ONE AT A TIME with no other server load_
_Consider server restart between each for fresh memory_

- [ ] **D1** Re-ingest `CO 273:579:3` (~65 MB) [M]
- [ ] **D2** Re-ingest `CO 273:534:15a` (~130 MB, 201 pages) [L]
- [ ] **D3** Re-ingest `CO 273:534:2` (~140 MB) [XL]
- [ ] **D4** Re-ingest `CO 273:534:11a` (~170 MB) [XL]
- [ ] **D5** Re-ingest `CO 273:534:3` (~200 MB) [XL]
- [ ] **D6** Re-ingest `CO 273:579:2a` (~278 MB — largest) [XL]

**Acceptance per PDF**: `status: "done"`, `pages_total > 0`, `chunks_processed > 0`, `entities_extracted > 0`

**If failure**: Check logs → restart server → retry. If still fails: manual pypdf split as last resort.

## Phase E: Verification & Testing

_Prerequisite: B, C, D all complete (or max effort reached)_

- [ ] **E1** Query Neo4j entity count per document (28 docs should have entities) [M]
- [ ] **E2** Test query endpoint: "What were the trade regulations in the Straits Settlements?" [S]
- [ ] **E3** Test query with category filter: `filter_categories: ["Economic and Financial"]` [S]
- [ ] **E4** Test graph search: `GET /graph/search?q=Straits Settlements` [S]
- [ ] **E5** Test signed URL / proxy for 3 different doc_ids [S]
- [ ] **E6** Run backend tests: `pytest tests/ -v` (24 pass) [S]
- [ ] **E7** Run frontend tests: `npx vitest run` (29 pass) [S]
- [ ] **E8** Update MEMORY.md with final ingestion status [S]

## Progress Summary

| Phase | Tasks | Done | Status |
|-------|-------|------|--------|
| A: Verify | 5 | 0 | Not started |
| B: Entity Retry | 8 | 0 | Not started |
| C: Medium Re-ingest | 2 | 0 | Not started |
| D: XL Re-ingest | 6 | 0 | Not started |
| E: Verification | 8 | 0 | Not started |
| **Total** | **29** | **0** | |
