# Query Pipeline Fix — Comprehensive Plan

**Last Updated: 2026-03-01**

---

## Executive Summary

The chatbot's query pipeline is fundamentally broken: **vector search silently fails on every query** due to two `.env` misconfigurations, and **entity hint extraction is case-sensitive**, preventing graph fallback for lowercase input. The combined effect is that the chatbot returns "I cannot answer this based on the available sources" for virtually all user queries. This is a **critical production bug** requiring immediate fix across 3 files.

## Current State Analysis

### Symptom
- User asks: `"explain strait settlement"` → chatbot responds with fallback "I cannot answer this based on the available sources."
- Queries with proper capitalization + matching entity names partially work via graph + web fallback, but vector search still fails.

### Diagnosed Root Causes

| # | Component | Bug | Impact |
|---|-----------|-----|--------|
| **RC-1** | `.env` config | `VECTOR_SEARCH_ENDPOINT` set to public domain name (`1005598664...vdb.vertexai.goog`) instead of endpoint resource ID (`7992877787885076480`) | SDK raises `ValueError` → caught silently → vector search always returns `[]` |
| **RC-2** | `.env` config | `VECTOR_SEARCH_DEPLOYED_INDEX_ID` set to `colonial-archives-deployed` instead of actual ID `colonial_archives_deployed_1772349960200` | SDK raises `404 NotFound` on `find_neighbors` even if RC-1 is fixed |
| **RC-3** | Code logic | `_extract_entity_hints()` regex only matches `[A-Z][a-z.]+` patterns | Lowercase queries produce zero entity hints → graph search never triggers |

### Evidence

```
# RC-1 + RC-2: Vector search fails
>>> vector_search_service.search(embedding)
ValueError: Resource 1005598664...vdb.vertexai.goog is not a valid resource id.

# With correct endpoint ID but wrong deployed index ID:
>>> ep.find_neighbors(deployed_index_id='colonial-archives-deployed', ...)
404 Index 'colonial-archives-deployed' is not found.

# With BOTH correct values:
>>> ep.find_neighbors(deployed_index_id='colonial_archives_deployed_1772349960200', ...)
Results: 5 chunks with distance ~0.41 ✓

# RC-3: Entity hints
>>> _extract_entity_hints("explain strait settlement")
[]  # Zero hints — all lowercase
>>> _extract_entity_hints("What is the Straits Settlements colonial administration?")
["Straits Settlements"]  # Works only with proper capitalization
```

### Data Flow (Current — Broken)

```
User query (lowercase)
  │
  ├─ Embed query ─────────────────── OK (768-dim vector produced)
  │
  ├─ Extract entity hints ──────── FAIL (RC-3: returns [])
  │   └─ Graph search ──────────── SKIP (no hints → early return)
  │
  ├─ Vector search ─────────────── FAIL (RC-1+2: ValueError/404)
  │   └─ Exception caught ──────── vector_results = []
  │
  └─ Early exit check ──────────── TRIGGERED (both empty)
      └─ Return FALLBACK_ANSWER ── "I cannot answer this..."
```

### Data Flow (Fixed)

```
User query (any case)
  │
  ├─ Embed query ─────────────────── OK
  │
  ├─ Extract entity hints ──────── OK (title-case fallback finds phrases)
  │   └─ Graph search ──────────── OK (Neo4j returns matching entities)
  │
  ├─ Vector search ─────────────── OK (correct endpoint + deployed ID)
  │   └─ Returns top-K chunks ──── 5-10 results with distances
  │
  ├─ Merge contexts ────────────── vector + graph contexts combined
  ├─ Score relevance ───────────── vector*0.6 + graph*0.4
  ├─ (Optional web fallback) ──── if relevance < 0.7
  └─ LLM generates answer ──────── grounded in archive citations
```

## Multi-Agent Team Strategy

### Agent Partitioning

The fix involves 3 independent code areas with no file overlap, making it ideal for parallel agents:

| Agent | Scope | Files | Depends On |
|-------|-------|-------|------------|
| **config-fix** | Fix .env + add resilient endpoint parsing | `backend/.env`, `backend/app/services/vector_search.py`, `backend/tests/test_vector_search_config.py` | None |
| **entity-hints** | Fix case-insensitive entity extraction | `backend/app/services/hybrid_retrieval.py`, `backend/tests/test_hybrid_retrieval.py` | None |
| **verifier** (sequential, after both) | End-to-end verification | Read-only queries | config-fix, entity-hints |

### Why This Partitioning Works

- **Zero file overlap**: config-fix touches `vector_search.py` + `.env`; entity-hints touches `hybrid_retrieval.py` + its test file
- **Independent test suites**: Each agent runs only its own tests
- **Clear boundaries**: Config fix is infra-level; entity hints is business logic
- **Simple merge**: No conflicts possible

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| `.env` committed with secrets | Medium | High — credential leak | Check `.gitignore`; update `.env.example` instead if `.env` is ignored |
| Entity hints over-extract (false positives) | Low | Low — extra graph lookups, slightly slower | Stop-word filtering + test coverage |
| Vector Search endpoint ID changes on redeployment | Low | Critical — search breaks again | Resilient `_parse_endpoint_name()` handles domain format too |
| Existing tests break from refactor | Very Low | Medium | Run full test suite before commit |

## Success Metrics

1. `curl -X POST /query -d '{"question":"explain strait settlement"}'` returns substantive answer with `citations.length > 0`
2. Vector search returns 5+ results with distances > 0.3
3. Entity hints extracted from lowercase query: `len(hints) > 0`
4. All existing 24 backend tests continue to pass
5. New tests: 3 config + 4 entity hints = 7 new tests pass
6. No regression on capitalized queries

## Timeline

| Phase | Effort | Time |
|-------|--------|------|
| Config fix (.env + vector_search.py) | S | ~5 min |
| Entity hints fix + tests | M | ~10 min |
| End-to-end verification | S | ~5 min |
| **Total** | | **~20 min** |
