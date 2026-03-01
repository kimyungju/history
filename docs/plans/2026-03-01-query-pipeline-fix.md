# Query Pipeline Fix — Vector Search & Entity Hints

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the chatbot returning "I cannot answer this" for valid queries by resolving three root-cause bugs in the retrieval pipeline.

**Architecture:** Two `.env` misconfigurations silently break vector search (the primary retrieval path), and a case-sensitive regex in entity hint extraction prevents graph fallback for lowercase queries. All three must be fixed for the query pipeline to function.

**Tech Stack:** Python 3.13, FastAPI, Vertex AI Vector Search SDK, Neo4j, pytest

---

## Root Cause Analysis

| # | Bug | Impact | Severity |
|---|-----|--------|----------|
| 1 | `VECTOR_SEARCH_ENDPOINT` in `.env` is the public domain name (`1005598664...vdb.vertexai.goog`) but SDK expects endpoint resource ID (`7992877787885076480`) | `ValueError` on every vector search → silently caught → 0 results | CRITICAL |
| 2 | `VECTOR_SEARCH_DEPLOYED_INDEX_ID` in `.env` is `colonial-archives-deployed` but actual ID is `colonial_archives_deployed_1772349960200` | `404 NotFound` on every `find_neighbors` call even if #1 is fixed | CRITICAL |
| 3 | `_extract_entity_hints()` only matches `[A-Z][a-z.]+` — lowercase queries produce zero entity hints | Graph search never triggers for lowercase input → no graph fallback | MODERATE |

**Combined effect:** Vector search broken (bugs 1+2) + graph search skipped (bug 3) → early exit at `hybrid_retrieval.py:94` → fallback answer for every lowercase query.

---

### Task 1: Fix vector search .env configuration

**Files:**
- Modify: `backend/.env` (lines 5, 7)

**Step 1: Update VECTOR_SEARCH_ENDPOINT**

Change line 5 from:
```
VECTOR_SEARCH_ENDPOINT=1005598664.asia-southeast1-58449340870.vdb.vertexai.goog
```
to:
```
VECTOR_SEARCH_ENDPOINT=7992877787885076480
```

**Step 2: Update VECTOR_SEARCH_DEPLOYED_INDEX_ID**

Change line 7 from:
```
VECTOR_SEARCH_DEPLOYED_INDEX_ID=colonial-archives-deployed
```
to:
```
VECTOR_SEARCH_DEPLOYED_INDEX_ID=colonial_archives_deployed_1772349960200
```

**Step 3: Verify vector search works**

Run:
```bash
cd backend && python -c "
import asyncio, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from app.services.embeddings import embeddings_service
from app.services.vector_search import vector_search_service
async def t():
    e = await embeddings_service.embed_query('strait settlement')
    r = await vector_search_service.search(e, top_k=3)
    print(f'{len(r)} results'); [print(f'  {x[\"id\"]} dist={x[\"distance\"]:.4f}') for x in r]
asyncio.run(t())
"
```
Expected: 3 results with chunk IDs and distances > 0.3.

---

### Task 2: Make vector_search.py resilient to endpoint format

**Files:**
- Modify: `backend/app/services/vector_search.py:40-48`

The endpoint property currently passes `settings.VECTOR_SEARCH_ENDPOINT` directly. Add a guard that extracts the numeric ID if a full domain name is provided, so future misconfiguration doesn't silently break search.

**Step 1: Write the failing test**

Add to `backend/tests/test_vector_search_config.py`:

```python
"""Tests for VectorSearchService endpoint configuration."""

from app.services.vector_search import VectorSearchService


def test_extract_endpoint_id_from_domain():
    """Domain-style endpoint should be parsed to numeric prefix."""
    svc = VectorSearchService()
    domain = "1005598664.asia-southeast1-58449340870.vdb.vertexai.goog"
    assert svc._parse_endpoint_name(domain) == "1005598664"


def test_extract_endpoint_id_from_numeric():
    """Pure numeric endpoint ID should pass through unchanged."""
    svc = VectorSearchService()
    assert svc._parse_endpoint_name("7992877787885076480") == "7992877787885076480"


def test_extract_endpoint_id_from_resource_name():
    """Full resource name should pass through unchanged."""
    svc = VectorSearchService()
    full = "projects/123/locations/us-central1/indexEndpoints/456"
    assert svc._parse_endpoint_name(full) == full
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_vector_search_config.py -v`
Expected: FAIL — `_parse_endpoint_name` does not exist.

**Step 3: Implement `_parse_endpoint_name` and use it in the endpoint property**

In `backend/app/services/vector_search.py`, add the method and update `endpoint`:

```python
@staticmethod
def _parse_endpoint_name(raw: str) -> str:
    """Normalise endpoint config to a value the SDK accepts.

    Accepts:
      - Numeric endpoint ID (pass-through)
      - Full resource name (pass-through)
      - Public domain name → extract numeric prefix
    """
    if raw.endswith(".vdb.vertexai.goog"):
        return raw.split(".")[0]
    return raw

@property
def endpoint(self) -> MatchingEngineIndexEndpoint:
    if self._endpoint is None:
        self._ensure_init()
        endpoint_name = self._parse_endpoint_name(settings.VECTOR_SEARCH_ENDPOINT)
        self._endpoint = MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_name,
        )
    return self._endpoint
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_vector_search_config.py -v`
Expected: 3 passed.

**Step 5: Run all existing backend tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: 27 passed (24 existing + 3 new).

**Step 6: Commit**

```bash
git add backend/app/services/vector_search.py backend/tests/test_vector_search_config.py
git commit -m "fix: parse vector search endpoint domain name to resource ID"
```

---

### Task 3: Fix case-insensitive entity hint extraction

**Files:**
- Modify: `backend/app/services/hybrid_retrieval.py:211-241`
- Test: `backend/tests/test_hybrid_retrieval.py`

**Step 1: Write the failing tests**

Add to `backend/tests/test_hybrid_retrieval.py`:

```python
class TestExtractEntityHints:
    """Verify entity hint extraction handles various casing."""

    def test_lowercase_query_extracts_hints(self, service):
        """Lowercase queries should still produce entity hints."""
        hints = service._extract_entity_hints("explain strait settlement")
        assert len(hints) > 0
        # Should find "strait settlement" or similar
        combined = " ".join(hints).lower()
        assert "strait" in combined

    def test_mixed_case_query(self, service):
        """Mixed case queries should extract entities."""
        hints = service._extract_entity_hints("tell me about the straits Settlements")
        assert len(hints) > 0

    def test_stop_words_excluded(self, service):
        """Common stop words should not appear as hints."""
        hints = service._extract_entity_hints("What is the colonial office?")
        assert "What" not in hints
        assert "colonial office" in [h.lower() for h in hints] or len(hints) > 0

    def test_already_capitalized(self, service):
        """Capitalized queries should still work as before."""
        hints = service._extract_entity_hints("Who is J. Anderson?")
        assert any("Anderson" in h for h in hints)
```

**Step 2: Run test to verify the new tests fail**

Run: `cd backend && python -m pytest tests/test_hybrid_retrieval.py::TestExtractEntityHints -v`
Expected: `test_lowercase_query_extracts_hints` and `test_mixed_case_query` FAIL.

**Step 3: Fix `_extract_entity_hints` to handle lowercase input**

Replace the method in `backend/app/services/hybrid_retrieval.py`:

```python
@staticmethod
def _extract_entity_hints(question: str) -> list[str]:
    """Extract likely entity names from the question.

    Uses simple heuristics — capitalized multi-word phrases, proper
    nouns, and title-cased versions of multi-word sequences.
    No LLM call to keep latency low.
    """
    # Work on a title-cased version so lowercase input produces matches.
    # Original casing is tried first to preserve exact user input.
    stop_words = {
        "what", "who", "where", "when", "how", "why", "which",
        "does", "did", "was", "were", "are", "is", "the", "and",
        "for", "with", "from", "about", "into", "that", "this",
        "have", "has", "had", "can", "could", "would", "should",
        "tell", "describe", "explain", "me", "about", "please",
        "a", "an", "of", "in", "on", "to", "by",
    }

    # Find sequences of capitalized words (2+ words = likely entity)
    pattern = r"\b(?:[A-Z][a-z.]+(?:\s+[A-Z][a-z.]+)+)\b"

    # Try on original text first
    multi_word = re.findall(pattern, question)

    # Also try on title-cased text to catch lowercase queries
    title_q = question.title()
    title_multi = re.findall(pattern, title_q)

    # Merge, filtering out stop-word-only matches
    all_multi: list[str] = []
    for phrase in multi_word + title_multi:
        words = phrase.split()
        non_stop = [w for w in words if w.lower() not in stop_words]
        if non_stop and phrase not in all_multi:
            # Keep only the non-stop-word portion as the hint
            cleaned = " ".join(non_stop)
            if cleaned not in all_multi:
                all_multi.append(cleaned)

    # Single capitalized words from original
    single_caps = re.findall(r"\b([A-Z][a-z]{2,})\b", question)
    single_caps = [w for w in single_caps if w.lower() not in stop_words]

    # Also from title-cased version
    title_singles = re.findall(r"\b([A-Z][a-z]{2,})\b", title_q)
    title_singles = [w for w in title_singles if w.lower() not in stop_words]

    all_singles = list(dict.fromkeys(single_caps + title_singles))

    # Combine: multi-word first, then singles not already covered
    hints: list[str] = list(all_multi)
    for word in all_singles:
        if not any(word.lower() in mw.lower() for mw in all_multi):
            hints.append(word)

    return hints
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_hybrid_retrieval.py -v`
Expected: All tests pass (existing + new).

**Step 5: Run full backend test suite**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All 31 tests pass (24 original + 3 config + 4 hints).

**Step 6: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py backend/tests/test_hybrid_retrieval.py
git commit -m "fix: case-insensitive entity hint extraction for lowercase queries"
```

---

### Task 4: End-to-end verification

**Step 1: Restart the backend server** (to pick up .env changes)

Kill existing uvicorn and restart:
```bash
cd backend && uvicorn app.main:app --reload --port 8090
```

**Step 2: Test the original failing query**

```bash
curl -s -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "explain strait settlement"}' | python -m json.tool
```

Expected: An answer with archive citations (not the fallback message). The response should contain:
- `answer`: A substantive answer about the Straits Settlements
- `source_type`: `"archive"` or `"mixed"`
- `citations`: Non-empty list with archive citations containing `doc_id` and `pages`

**Step 3: Test a capitalized query still works**

```bash
curl -s -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is J. Anderson?"}' | python -m json.tool
```

Expected: Answer with citations (may include graph data).

**Step 4: Test from the frontend**

Open the frontend (`npm run dev`) and type "explain strait settlement" in the chat. Verify the response displays properly with citations.

**Step 5: Commit .env fix**

```bash
git add backend/.env
git commit -m "fix: correct vector search endpoint ID and deployed index ID"
```

Note: `.env` should NOT be committed if it contains secrets. Check `.gitignore` first. If `.env` is gitignored, document the correct values in `.env.example` instead.
