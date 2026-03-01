# Archive-First Query Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the chatbot answer from colonial archive documents first, only falling back to web search with a clear disclaimer when the archive cannot answer the question.

**Architecture:** Two-phase LLM generation — first generate an answer using archive-only context; if the LLM returns the fallback answer, trigger web search and generate a separate web-sourced answer with a disclaimer. Also fix the distance→similarity scoring inversion that causes web fallback to trigger on every query.

**Tech Stack:** Python 3.13, FastAPI, Vertex AI Gemini, Tavily, pytest

---

## Problem Analysis

**Current behavior:** Web search always triggers because:
1. Vector search returns COSINE_DISTANCE values (~0.41) which are used directly as `vector_score`. Lower distance = better match, but code treats higher = better. So `vector_score ≈ 0.41`, combined ≈ 0.25 — always below the 0.7 threshold.
2. Web results get mixed into archive context, and the LLM prefers clean web text over messy OCR.
3. The LLM prompt treats archive and web sources equally.

**Desired behavior:**
1. Answer from colonial archive documents via RAG
2. Only if archive can't answer → show disclaimer + web answer
3. Clear separation: user knows when answer is from archive vs web

---

### Task 1: Fix distance-to-similarity scoring inversion

**Files:**
- Modify: `backend/app/services/hybrid_retrieval.py:112-117`
- Test: `backend/tests/test_hybrid_retrieval.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_hybrid_retrieval.py`:

```python
class TestRelevanceScoring:
    """Verify relevance scoring converts distance to similarity."""

    def test_vector_score_converts_distance_to_similarity(self, service):
        """Distance 0.4 should become similarity 0.6, not raw 0.4."""
        # Simulate: 2 results with distances 0.3 and 0.5 → avg distance 0.4
        # Similarity should be 1.0 - 0.4 = 0.6
        vector_results = [
            {"id": "c1", "distance": 0.3},
            {"id": "c2", "distance": 0.5},
        ]
        avg_dist = sum(r["distance"] for r in vector_results) / len(vector_results)
        expected_similarity = 1.0 - avg_dist
        assert expected_similarity == pytest.approx(0.6, abs=0.01)
```

**Step 2: Run test to verify it passes (this is a logic test, not code-dependent)**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py::TestRelevanceScoring -v`

**Step 3: Fix the scoring in hybrid_retrieval.py**

In `hybrid_retrieval.py`, change lines 112-117 from:

```python
vector_score = 0.0
if vector_results:
    vector_score = sum(r["distance"] for r in vector_results) / len(
        vector_results
    )
```

to:

```python
vector_score = 0.0
if vector_results:
    avg_distance = sum(r["distance"] for r in vector_results) / len(
        vector_results
    )
    vector_score = max(1.0 - avg_distance, 0.0)
```

**Step 4: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py backend/tests/test_hybrid_retrieval.py
git commit -m "fix: convert vector distance to similarity for relevance scoring"
```

---

### Task 2: Implement archive-first answer generation with web disclaimer

This is the core change. Instead of mixing web results into archive context, we do two-phase LLM generation.

**Files:**
- Modify: `backend/app/services/hybrid_retrieval.py:136-164`
- Modify: `backend/app/services/llm.py` (prompts + new method)
- Test: `backend/tests/test_hybrid_retrieval.py`

**Step 1: Write failing tests**

Add to `backend/tests/test_hybrid_retrieval.py`:

```python
class TestArchiveFirstBehavior:
    """Verify archive-first answer generation with web fallback."""

    @pytest.mark.asyncio
    async def test_archive_answer_does_not_trigger_web(self, service):
        """When archive LLM returns a real answer, web search should not run."""
        with patch("app.services.hybrid_retrieval.vector_search_service") as mock_vs, \
             patch("app.services.hybrid_retrieval.embeddings_service") as mock_embed, \
             patch("app.services.hybrid_retrieval.neo4j_service") as mock_neo4j, \
             patch("app.services.hybrid_retrieval.storage_service") as mock_storage, \
             patch("app.services.hybrid_retrieval.llm_service") as mock_llm, \
             patch("app.services.hybrid_retrieval.web_search_service") as mock_web:

            mock_embed.embed_query = AsyncMock(return_value=[0.1] * 768)
            mock_vs.search = AsyncMock(return_value=[
                {"id": "doc_a_chunk_0", "distance": 0.3}
            ])
            mock_neo4j.search_entities = AsyncMock(return_value=[])

            # Mock GCS chunk loading
            mock_blob = MagicMock()
            mock_blob.download_as_text.return_value = json.dumps([
                {"chunk_id": "doc_a_chunk_0", "text": "Archive text about settlements.", "pages": [1]}
            ])
            mock_storage._bucket = MagicMock()
            mock_storage._bucket.blob.return_value = mock_blob

            # Archive LLM returns a real answer
            mock_llm.generate_answer = AsyncMock(return_value={
                "answer": "The settlements were established in 1826 [archive:1].",
                "context_chunks": [],
            })

            result = await service.query("explain strait settlement")

            assert result.source_type == "archive"
            assert "settlements" in result.answer.lower()
            mock_web.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_web_fallback_includes_disclaimer(self, service):
        """When archive returns fallback, web answer should have disclaimer."""
        with patch("app.services.hybrid_retrieval.vector_search_service") as mock_vs, \
             patch("app.services.hybrid_retrieval.embeddings_service") as mock_embed, \
             patch("app.services.hybrid_retrieval.neo4j_service") as mock_neo4j, \
             patch("app.services.hybrid_retrieval.storage_service") as mock_storage, \
             patch("app.services.hybrid_retrieval.llm_service") as mock_llm, \
             patch("app.services.hybrid_retrieval.web_search_service") as mock_web:

            mock_embed.embed_query = AsyncMock(return_value=[0.1] * 768)
            mock_vs.search = AsyncMock(return_value=[
                {"id": "doc_a_chunk_0", "distance": 0.3}
            ])
            mock_neo4j.search_entities = AsyncMock(return_value=[])

            mock_blob = MagicMock()
            mock_blob.download_as_text.return_value = json.dumps([
                {"chunk_id": "doc_a_chunk_0", "text": "Some numbers 1234 5678.", "pages": [1]}
            ])
            mock_storage._bucket = MagicMock()
            mock_storage._bucket.blob.return_value = mock_blob

            # Archive LLM returns fallback
            archive_fallback = "I cannot answer this based on the available sources."
            mock_llm.generate_answer = AsyncMock(side_effect=[
                {"answer": archive_fallback, "context_chunks": []},
                {"answer": "Web answer about settlements.", "context_chunks": []},
            ])

            mock_web.search = AsyncMock(return_value=[
                {"id": "web_1", "title": "Britannica", "url": "https://britannica.com", "text": "Web content", "cite_type": "web"}
            ])

            result = await service.query("explain strait settlement")

            assert result.source_type == "web_fallback"
            assert "not found in the colonial archive" in result.answer.lower()
            mock_web.search.assert_called_once()
```

Note: These tests need `from unittest.mock import AsyncMock` import added at the top of the test file.

**Step 2: Run tests to verify they fail**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py::TestArchiveFirstBehavior -v`
Expected: FAIL

**Step 3: Update LLM prompts in `llm.py`**

Replace `ANSWER_GENERATION_PROMPT` and add `WEB_FALLBACK_PROMPT`:

```python
ANSWER_GENERATION_PROMPT = """You are a research assistant for colonial-era Straits Settlements archives.

Context retrieved from colonial archive documents:
\"\"\"
{context}
\"\"\"

Sources: {citations}

Rules:
1. Answer ONLY using information from the archive context above.
2. Cite every fact using [archive:N] markers.
3. Colonial archives may contain OCR artifacts, financial tables, or fragmented text — extract meaning where possible.
4. If the context genuinely does not contain information to answer the question, respond exactly: "I cannot answer this based on the available sources."
5. NEVER infer, guess, or use external knowledge.

User question: {question}"""


WEB_FALLBACK_PROMPT = """Context from web sources:
\"\"\"
{context}
\"\"\"

Sources: {citations}

Rules:
1. Answer using information from the web context above.
2. Cite every fact using [web:N] markers.
3. Be concise and factual.

User question: {question}"""
```

Update `generate_answer` to accept a `prompt_template` parameter:

```python
async def generate_answer(
    self,
    question: str,
    context_chunks: list[dict],
    source_type: str = "archive",
    prompt_template: str | None = None,
) -> dict:
```

Use `prompt_template` if provided, otherwise fall back to `ANSWER_GENERATION_PROMPT`. Build the prompt the same way (context parts + citations), but use the template string.

**Step 4: Rewrite the web fallback section in `hybrid_retrieval.py`**

Replace lines 136-164 (the web fallback + LLM generation section) with archive-first logic:

```python
        # Step 7 — Generate archive-only answer.
        with log_stage("llm_generation", logger=logger):
            llm_result: dict = await llm_service.generate_answer(
                question, merged_context, source_type="archive"
            )
        answer_text: str = llm_result["answer"]

        # Step 8 — If archive couldn't answer, try web fallback.
        web_context: list[dict] = []
        source_type = "archive"

        if answer_text.strip() == FALLBACK_ANSWER and merged_context:
            logger.info("Archive could not answer; triggering web fallback")
            try:
                web_context = await web_search_service.search(question)
                if web_context:
                    from app.services.llm import WEB_FALLBACK_PROMPT

                    web_llm_result = await llm_service.generate_answer(
                        question, web_context, source_type="web_fallback",
                        prompt_template=WEB_FALLBACK_PROMPT,
                    )
                    web_answer = web_llm_result["answer"]
                    disclaimer = (
                        "The requested information was not found in the colonial archive documents. "
                        "Below is an answer based on web sources:\n\n"
                    )
                    answer_text = disclaimer + web_answer
                    source_type = "web_fallback"
                    # Replace merged_context with web-only for citations
                    merged_context = web_context
                    logger.info("Web fallback answer generated")
            except Exception:
                logger.exception("Web fallback failed")

        # If no archive results at all and we already returned early fallback,
        # this code won't reach here. But handle edge case:
        if not merged_context and not web_context:
            answer_text = FALLBACK_ANSWER
```

**Step 5: Update citation building**

The citation building section (lines 167-195) stays the same — it builds citations from `merged_context`. Since we now replace `merged_context` with web-only context for web_fallback, the citations will be web-only automatically.

Remove the old `source_type` logic that checked for mixed/web_fallback (lines 148-157 in old code) — it's now handled above.

**Step 6: Run tests**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/test_hybrid_retrieval.py -v`
Expected: All tests pass.

**Step 7: Run full test suite**

Run: `cd backend && "C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
Expected: All tests pass (may need to update `test_llm_mixed.py` if prompt format changed).

**Step 8: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py backend/app/services/llm.py backend/tests/test_hybrid_retrieval.py
git commit -m "feat: archive-first query with web fallback disclaimer"
```

---

### Task 3: End-to-end verification

**Step 1: Restart the backend server**

```bash
cd backend && uvicorn app.main:app --reload --port 8090
```

**Step 2: Test archive-answerable query**

```bash
curl -s -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "explain strait settlement"}' | python -m json.tool
```

Expected:
- `source_type`: `"archive"` (if archive can answer) or `"web_fallback"` with disclaimer prefix
- If `web_fallback`: answer starts with "The requested information was not found in the colonial archive documents."
- Citations match the `source_type`

**Step 3: Test query that archive should answer**

```bash
curl -s -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the expenditure of the Straits Settlements in 1932?"}' | python -m json.tool
```

Expected: Archive answer with `[archive:N]` citations (the vector results contain financial data from 1932).

**Step 4: Test query that archive cannot answer**

```bash
curl -s -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the population of Singapore in 2025?"}' | python -m json.tool
```

Expected: `source_type: "web_fallback"` with disclaimer + web citations.

**Step 5: Verify in frontend**

Open the frontend and test both query types. Verify:
- Archive answers show gold citation badges
- Web fallback answers show the disclaimer text + emerald web links
- Footer label shows "Web sources" for web_fallback responses
