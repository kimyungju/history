# Query Pipeline Fix — Context & Key Files

**Last Updated: 2026-03-01**

---

## Key Files

### Config (Agent: config-fix)

| File | Role | Lines of Interest |
|------|------|-------------------|
| `backend/.env` | Environment config | L5: `VECTOR_SEARCH_ENDPOINT`, L7: `VECTOR_SEARCH_DEPLOYED_INDEX_ID` |
| `backend/app/services/vector_search.py` | Vector search singleton | L40-48: `endpoint` property (needs `_parse_endpoint_name`), L136-194: `search()` method |
| `backend/app/config/settings.py` | Pydantic Settings | L16-18: Vector search setting definitions |

### Entity Hints (Agent: entity-hints)

| File | Role | Lines of Interest |
|------|------|-------------------|
| `backend/app/services/hybrid_retrieval.py` | Query orchestration | L211-241: `_extract_entity_hints()` — case-sensitive regex; L86-101: silent exception catch + early exit |
| `backend/tests/test_hybrid_retrieval.py` | Existing tests | 3 tests for parallel behavior; need 4 new tests for case handling |

### Verification (Agent: verifier)

| File | Role |
|------|------|
| `backend/app/services/hybrid_retrieval.py:53-205` | Full `query()` method — traces through embed → search → merge → LLM |
| `backend/app/routers/query.py:20-26` | POST `/query` route |
| `backend/app/services/llm.py` | LLM answer generation + prompt template |

## Correct GCP Resource IDs

Discovered via `gcloud ai index-endpoints list`:

| Setting | Wrong Value (current .env) | Correct Value |
|---------|---------------------------|---------------|
| `VECTOR_SEARCH_ENDPOINT` | `1005598664.asia-southeast1-58449340870.vdb.vertexai.goog` | `7992877787885076480` |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID` | `colonial-archives-deployed` | `colonial_archives_deployed_1772349960200` |
| `VECTOR_SEARCH_INDEX_ID` | `5700013413925650432` | `5700013413925650432` (correct, no change) |

Full endpoint resource name: `projects/58449340870/locations/asia-southeast1/indexEndpoints/7992877787885076480`

## Key Decisions

1. **Resilient parsing over strict validation**: `_parse_endpoint_name()` accepts domain name format and extracts numeric prefix, rather than just erroring. Prevents silent breakage if someone pastes the domain name from GCP console.

2. **Title-case fallback for entity hints**: Apply `question.title()` and run the same regex, then filter out stop words from multi-word matches. This preserves exact behavior for already-capitalized input while enabling lowercase queries.

3. **Stop-word list expansion**: Added common query words (`"me"`, `"about"`, `"please"`, `"a"`, `"an"`, `"of"`, `"in"`, `"on"`, `"to"`, `"by"`) to prevent false multi-word entity matches like `"Explain Strait Settlement"` where `"Explain"` is not an entity.

4. **.env vs .env.example**: The `.env` file contains secrets (Neo4j password, Tavily key). If `.gitignore` excludes `.env`, update `.env.example` with the correct non-secret values. The endpoint ID and deployed index ID are not secrets — they're infrastructure identifiers.

## Dependencies

- **No new packages** required
- **No schema changes** — existing `QueryResponse` model is unchanged
- **No frontend changes** — the fix is entirely backend
- **Backend server restart** required after `.env` changes (uvicorn `--reload` won't pick up `.env` changes automatically)

## Test Infrastructure

```bash
# Backend tests (use Python 3.13 explicitly)
cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v

# Run specific test file
cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_vector_search_config.py -v
cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py -v

# Manual end-to-end test
curl -s -X POST http://localhost:8090/query -H "Content-Type: application/json" -d '{"question": "explain strait settlement"}' | python -m json.tool
```

## Related Planning Documents

- Implementation plan: `docs/plans/2026-03-01-query-pipeline-fix.md`
- Master task tracker: `dev/active/colonial-archives-graph-rag/colonial-archives-graph-rag-tasks.md`
- Data ingestion context: `dev/active/data-ingestion-integration/data-ingestion-integration-context.md`
