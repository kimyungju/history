# Ingestion Completion Context

**Last Updated: 2026-03-01**

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/routers/ingest.py` | Ingestion pipeline (9 steps) + retry_entities endpoint |
| `backend/app/services/ocr.py` | Document AI OCR with adaptive concurrency + 429 retry |
| `backend/app/services/storage.py` | GCS I/O + download_json + signed URL with fallback |
| `backend/app/routers/query.py` | Query + signed URL + proxy endpoint |
| `backend/app/services/entity_extraction.py` | Gemini entity extraction (Semaphore 5) |
| `backend/app/services/entity_normalization.py` | 3-stage entity dedup |
| `backend/app/services/neo4j_service.py` | Neo4j MERGE for entities/relationships |
| `backend/app/config/document_categories.json` | PDF → category mapping (28 PDFs) |
| `backend/app/config/settings.py` | All tunable thresholds |

## API Endpoints Used

### Entity Retry (NEW)
```bash
# Retry entity extraction for a vector-only PDF
curl -X POST http://localhost:8090/retry_entities \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "CO 273:550:1"}'

# Response: {"doc_id": "CO 273:550:1", "entities_extracted": 15, "relationships_extracted": 8}
```

### Full Ingestion
```bash
# Submit PDF for full 9-step ingestion
curl -X POST http://localhost:8090/ingest_pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf_url": "gs://aihistory-co273-nus/CO 273:534:9.pdf"}'

# Response: {"job_id": "uuid", "status": "processing", ...}

# Poll for completion
curl http://localhost:8090/ingest_status/{job_id}
```

### Signed URL / Proxy
```bash
# Get signed URL (falls back to proxy)
curl "http://localhost:8090/document/signed_url?doc_id=CO%20273:550:18"

# Direct proxy (always works with GCS access)
curl "http://localhost:8090/document/proxy/CO%20273:550:18" --output test.pdf
```

### Health / Neo4j Wake
```bash
curl http://localhost:8090/health
# {"status": "ok", "neo4j": "connected"}
```

### Entity Count Verification
```bash
# Search for entities from a specific document
curl "http://localhost:8090/graph/search?q=&limit=100"
```

## GCS Data Paths

| Path Pattern | Content | Used By |
|-------------|---------|---------|
| `gs://aihistory-co273-nus/CO 273:*.pdf` | Source PDFs | ingest_pdf |
| `gs://aihistory-co273-nus/ocr/{doc_id}_ocr.json` | OCR results (page text + confidence) | ingest pipeline step 2 |
| `gs://aihistory-co273-nus/chunks/{doc_id}.json` | Processed chunks (text, pages, categories) | retry_entities |

## OCR Adaptive Concurrency Tiers

| Pages | Semaphore | Concurrent Batches | Use Case |
|-------|-----------|-------------------|----------|
| ≤100 | 5 | 5 × 15 = 75 pages in flight | Normal PDFs |
| 101-200 | 2 | 2 × 15 = 30 pages in flight | Large PDFs |
| >200 | 1 | 1 × 15 = 15 pages in flight | XL PDFs (sequential) |

## Document AI 429 Retry Logic

- Max retries: 3
- Backoff: 2s → 4s → 8s (exponential)
- Catches: `google.api_core.exceptions.ResourceExhausted`
- Total max wait: 14s before giving up on a single batch

## PDF Size Estimates

| Doc ID | Est. Size | Est. Pages | Tier | OCR Concurrency |
|--------|----------|-----------|------|-----------------|
| CO 273:550:3 | ~60 MB | ~40 | Medium | Semaphore(5) |
| CO 273:550:1 | 50.9 MB | 43 | Medium | Semaphore(5) |
| CO 273:550:14 | ~62 MB | ~80 | Medium | Semaphore(5) |
| CO 273:579:2b | ~82 MB | ~94 | Large | Semaphore(5) |
| CO 273:550:19 | ~70 MB | ~101 | Large | Semaphore(2) |
| CO 273:579:1 | ~95 MB | ~170 | Large | Semaphore(2) |
| CO 273:534:15b | ~78 MB | ~195 | Large | Semaphore(2) |
| CO 273:534:9 | ~75 MB | ~100 | Medium | Semaphore(5) |
| CO 273:550:8 | ~110 MB | ~125 | XL | Semaphore(2) |
| CO 273:579:3 | ~65 MB | ~65 | Medium | Semaphore(5) |
| CO 273:534:15a | ~130 MB | 201 | XL | Semaphore(1) |
| CO 273:534:2 | ~140 MB | ~200+ | XL | Semaphore(1) |
| CO 273:534:11a | ~170 MB | ~200+ | XL | Semaphore(1) |
| CO 273:534:3 | ~200 MB | ~300+ | XL | Semaphore(1) |
| CO 273:579:2a | ~278 MB | ~400+ | XL | Semaphore(1) |

## Key Decisions

1. **Sequential processing** — One PDF at a time to avoid memory pressure and Gemini rate limiting
2. **Entity retry before re-ingest** — For vector-only PDFs, retry entities (minutes) rather than full re-ingest (tens of minutes)
3. **Smallest first** — Process smaller/faster PDFs first to validate fixes before committing to XL PDFs
4. **Server restart between XL PDFs** — Fresh memory for each large PDF to avoid cumulative memory buildup
5. **No parallel agents for ingestion** — Previous experience showed >3 concurrent large PDFs crash the backend

## Known Bugs Fixed (This Session)

| Fix | File | Description |
|-----|------|-------------|
| Entity retry endpoint | `ingest.py`, `schemas.py`, `storage.py` | `POST /retry_entities` re-runs steps 7-9 from stored chunks |
| Adaptive OCR concurrency | `ocr.py` | Semaphore(5/2/1) based on page count |
| Document AI 429 retry | `ocr.py` | 3 retries with exponential backoff |
| Signed URL proxy fallback | `storage.py`, `query.py` | `GET /document/proxy/{doc_id}` streams PDF bytes |

## Open Issues

- **:534:6 missing entities**: Has vector data, needs entity retry (included in Phase B)
- **XL PDF memory**: Even with adaptive concurrency, >200 MB PDFs may still OOM — last resort is manual PDF splitting
- **Neo4j pause**: Free tier pauses after 3 days idle — hit /health to wake before Phase B
