# Ingestion Completion Plan

**Last Updated: 2026-03-01**

## Executive Summary

Complete data ingestion for all 28 colonial archive PDFs and verify the three pipeline fixes (entity retry endpoint, XL PDF resilience, signed URL fallback). Currently 13 of 28 PDFs are fully ingested, 7 have vector data but no graph entities, and 8 remain unprocessed or failed. This plan executes the fixes built by the ingestion-fixes team and brings the corpus to 100% ingestion.

## Current State Analysis

### Ingestion Status (28 PDFs total)

| Status | Count | PDFs |
|--------|-------|------|
| Fully ingested (steps 1-9) | 13 | :550:18, :550:5, :550:11, :550:10, :550:21, :534:11b, :534:6*, :534:7, :534:13, :534:5, :534:24, :579:4, :550:13 |
| Vector-only (need entity retry) | 7 | :550:1, :550:3, :550:19, :579:1, :579:2b, :550:14, :534:15b |
| Failed - XL load (need re-ingest) | 5 | :534:2, :534:11a, :534:3, :579:2a, :579:3 |
| Failed - quota (retryable) | 1 | :534:9 |
| Failed - unknown | 1 | :550:8 |
| Missing graph only | 1 | :534:6 (vector data present, no entities) |

*:534:6 counted as "fully ingested" above but actually missing graph entities.

### Available Fixes (just implemented)

1. **`POST /retry_entities`** — Re-runs entity extraction (steps 7-9) from stored chunks in GCS
2. **Adaptive OCR concurrency** — Reduces concurrent Document AI batches for large PDFs (5→2→1)
3. **Document AI 429 retry** — Exponential backoff (3 retries: 2s/4s/8s) for quota errors
4. **Signed URL proxy fallback** — `GET /document/proxy/{doc_id}` streams PDF when signing fails

## Proposed Future State

All 28 PDFs fully ingested with both vector embeddings and graph entities in Neo4j. Signed URL/proxy endpoint working for frontend PDF viewer. Full query pipeline verified end-to-end across all documents.

## Implementation Phases

### Phase A: Verify Fixes (Prerequisites)

Before bulk processing, verify each fix works individually.

1. **A1**: Start the backend server on port 8090
2. **A2**: Test signed URL endpoint — `GET /document/signed_url?doc_id=CO 273:550:18` — should return proxy URL or signed URL (not 500)
3. **A3**: Test entity retry on a known vector-only PDF — `POST /retry_entities {"doc_id": "CO 273:550:1"}` — should return entity/relationship counts > 0
4. **A4**: Test health endpoint — confirm Neo4j is connected (may need to wake from sleep)

### Phase B: Entity Retry for Vector-Only PDFs (7 PDFs)

Use the new `/retry_entities` endpoint sequentially for each PDF. These already have chunks in GCS — no OCR needed.

**Order** (smallest chunk count first to verify quickly):
1. **B1**: `CO 273:550:3` (39 chunks)
2. **B2**: `CO 273:550:1` (57 chunks)
3. **B3**: `CO 273:550:14` (~80 chunks)
4. **B4**: `CO 273:579:2b` (94 chunks)
5. **B5**: `CO 273:550:19` (101 chunks)
6. **B6**: `CO 273:579:1` (170 chunks)
7. **B7**: `CO 273:534:15b` (195 chunks)
8. **B8**: `CO 273:534:6` (vector data present, no entities — retry)

**Expected duration**: ~2-5 min per PDF (entity extraction + normalization + Neo4j MERGE). Total ~20-40 min.

**Concurrency**: Run ONE AT A TIME to avoid Gemini rate limiting. Each has Semaphore(5) for concurrent Gemini calls per PDF.

### Phase C: Re-ingest Medium-Failed PDFs (2 PDFs)

These failed for transient reasons (quota, unknown). Try re-ingestion with the improved pipeline.

1. **C1**: `CO 273:534:9` — Previously failed with Document AI 429 RESOURCE_EXHAUSTED. The new retry logic should handle this.
2. **C2**: `CO 273:550:8` (~125 MB) — Unknown failure. May succeed with adaptive concurrency.

**Concurrency**: ONE AT A TIME, wait for completion before next.

### Phase D: Re-ingest XL PDFs (5 PDFs + 1 partial)

These are the largest PDFs (>95 MB, >100 pages). The adaptive concurrency fix should help, but process ONE AT A TIME with no other load.

**Order** (smallest first):
1. **D1**: `CO 273:579:3` (~65 MB) — May succeed now with adaptive concurrency
2. **D2**: `CO 273:534:15a` (~130 MB, 201 pages) — Previously succeeded under low load, should work with Semaphore(2)
3. **D3**: `CO 273:534:2` (~140 MB) — XL, sequential OCR (Semaphore(1))
4. **D4**: `CO 273:534:11a` (~170 MB) — XL
5. **D5**: `CO 273:534:3` (~200 MB) — XL
6. **D6**: `CO 273:579:2a` (~278 MB) — Largest PDF, most likely to fail

**Expected duration**: 15-45 min per PDF depending on page count. Total ~2-4 hours.

**Failure strategy**: If a PDF still fails:
- Check server logs for the specific error
- Try with server restart (fresh memory)
- As last resort: manually split PDF into smaller parts via pypdf and ingest individually

### Phase E: Verification & Testing

1. **E1**: Query Neo4j for entity counts per document — verify all 28 have entities
2. **E2**: Test the query endpoint with questions spanning multiple documents
3. **E3**: Test signed URL / proxy for each ingested document
4. **E4**: Test frontend citation clicks → PDF viewer
5. **E5**: Run full test suite (24 backend + 29 frontend = 53 tests)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gemini rate limiting during entity retry | Medium | Delays Phase B | Process one at a time, monitor for 429s |
| XL PDFs still OOM despite adaptive concurrency | Medium | Phase D failures | Server restart between XL PDFs, sequential OCR |
| Neo4j AuraDB paused (3-day inactivity) | High | Phase B blocked | Hit /health first to wake it, wait 60s |
| Document AI quota exhaustion | Low | Phase C-D delayed | Stagger submissions, retry logic handles 429 |
| GCS chunk files missing for some PDFs | Low | Phase B blocked | Fall back to full re-ingestion via /ingest_pdf |

## Success Metrics

| Metric | Target |
|--------|--------|
| PDFs fully ingested (vector + graph) | 28/28 (100%) |
| Total entities in Neo4j | 200+ (currently 100+) |
| Signed URL / proxy working | All documents accessible |
| Backend tests passing | 24/24 |
| Frontend tests passing | 29/29 |

## Required Resources

- **Backend server**: Running on localhost:8090
- **GCP services**: Document AI, Vertex AI (embeddings + Gemini), Cloud Storage, Vector Search
- **Neo4j AuraDB**: Must be awake (auto-resumes on connection)
- **Time**: ~3-5 hours for full execution (mostly waiting for OCR/entity extraction)
- **Monitoring**: Watch server logs for OOM, 429 errors, or connection timeouts

## Timeline Estimates

| Phase | Effort | Duration | Dependencies |
|-------|--------|----------|--------------|
| A: Verify fixes | S | 10 min | Server running |
| B: Entity retry (7+1 PDFs) | M | 30-45 min | A complete, Neo4j awake |
| C: Medium re-ingest (2 PDFs) | M | 20-40 min | A complete |
| D: XL re-ingest (5+1 PDFs) | XL | 2-4 hours | A complete, low server load |
| E: Verification | M | 30 min | B, C, D complete |
| **Total** | | **3-6 hours** | |
