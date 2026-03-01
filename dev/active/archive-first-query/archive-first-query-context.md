# Archive-First Query Pipeline — Context & Key Files

**Last Updated: 2026-03-01**

---

## Key Files

### Scoring + Orchestration (Agent: scoring-fix)

| File | Role | Lines of Interest |
|------|------|-------------------|
| `backend/app/services/hybrid_retrieval.py` | Query orchestration | L112-117: scoring (distance used as similarity — BUG), L136-164: web fallback + LLM generation (needs rewrite to archive-first), L34: `FALLBACK_ANSWER` constant |
| `backend/tests/test_hybrid_retrieval.py` | Existing tests | 3 parallel tests + 4 entity hint tests; add scoring + archive-first tests |

### LLM Prompts (Agent: prompt-fix)

| File | Role | Lines of Interest |
|------|------|-------------------|
| `backend/app/services/llm.py` | LLM answer generation | L13-29: `ANSWER_GENERATION_PROMPT` (treats archive/web equally — needs archive focus), L55-137: `generate_answer()` method (needs `prompt_template` param) |
| `backend/tests/test_llm_mixed.py` | Citation format test | Tests prompt construction — may need update if prompt changes |

### Frontend (No changes needed)

| File | Role | Already Handles |
|------|------|-----------------|
| `frontend/src/components/CitationBadge.tsx` | Citation rendering | Gold=archive, Emerald=web — already correct |
| `frontend/src/components/ChatMessage.tsx` | Message display | Shows "Web sources" label for `web_fallback` — already correct |
| `frontend/src/utils/parseCitations.ts` | Citation parser | Parses `[archive:N]` and `[web:N]` — already correct |
| `frontend/src/types/index.ts` | Type definitions | `source_type: "archive" \| "web_fallback" \| "mixed"` — already correct |

## Scoring Bug Details

Vertex AI Vector Search with `COSINE_DISTANCE`:
- Returns distance where **0 = identical**, **2 = opposite**
- Distance ~0.41 means cosine similarity ~0.59 (decent match)
- Code uses `distance` directly as `vector_score` (higher = better)
- Should be: `vector_score = 1.0 - avg_distance`

```
Current:  vector_score = avg_distance = 0.41 → combined = 0.25 → < 0.7 → web fallback
Fixed:    vector_score = 1 - 0.41 = 0.59   → combined = 0.35 → < 0.7 → still low without graph
```

Note: Even with the fix, without graph results the score may stay below 0.7. But that's OK because the archive-first approach doesn't depend on the threshold — it always tries archive first. The threshold only controls logging/monitoring.

## Interface Contract Between Agents

The `scoring-fix` agent calls `llm_service.generate_answer()`. The `prompt-fix` agent modifies this method.

**Current signature:**
```python
async def generate_answer(self, question: str, context_chunks: list[dict], source_type: str = "archive") -> dict
```

**New signature (prompt-fix agent adds `prompt_template`):**
```python
async def generate_answer(self, question: str, context_chunks: list[dict], source_type: str = "archive", prompt_template: str | None = None) -> dict
```

**Contract:**
- `prompt_template=None` → uses default `ANSWER_GENERATION_PROMPT` (archive-focused)
- `prompt_template=WEB_FALLBACK_PROMPT` → uses web-specific prompt
- Return value unchanged: `{"answer": str, "context_chunks": list}`

The `scoring-fix` agent imports `WEB_FALLBACK_PROMPT` from `llm.py` when calling the web fallback path.

## Disclaimer Text

```
The requested information was not found in the colonial archive documents. Below is an answer based on web sources:
```

This gets prepended to the web LLM answer in `hybrid_retrieval.py`.

## Test Commands

```bash
# Full backend suite
cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v

# Specific test files
cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py -v
cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_llm_mixed.py -v

# Manual query test
curl -s -X POST http://localhost:8090/query -H "Content-Type: application/json" -d '{"question":"explain strait settlement"}' | python -m json.tool
```

## Related Documents

- Implementation plan: `docs/plans/2026-03-01-archive-first-query.md`
- Previous fix (vector search config): `docs/plans/2026-03-01-query-pipeline-fix.md`
- Query pipeline architecture: `dev/active/query-pipeline-fix/query-pipeline-fix-context.md`
