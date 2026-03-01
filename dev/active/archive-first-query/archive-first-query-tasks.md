# Archive-First Query Pipeline — Task Tracker

**Last Updated: 2026-03-01**

---

## Agent Assignment

| Agent | Tasks | Mode | Files Owned |
|-------|-------|------|-------------|
| **scoring-fix** | A1-A4 | `bypassPermissions` | `hybrid_retrieval.py`, `test_hybrid_retrieval.py` |
| **prompt-fix** | B1-B3 | `bypassPermissions` | `llm.py`, `test_llm_mixed.py` |
| **verifier** | C1-C4 | read-only | None (curl + frontend testing) |

---

## Phase A: Scoring Fix + Archive-First Orchestration (scoring-fix agent)

- [ ] **A1: Fix distance-to-similarity conversion**
  - Change `vector_score = avg_distance` → `vector_score = max(1.0 - avg_distance, 0.0)`
  - Location: `hybrid_retrieval.py:112-117`
  - Acceptance: `vector_score` is ~0.59 for distance ~0.41
  - Effort: S | Depends: None

- [ ] **A2: Rewrite web fallback to archive-first approach**
  - Remove web context mixing from main flow (delete lines 136-157)
  - Generate archive-only LLM answer FIRST
  - If answer == `FALLBACK_ANSWER`: trigger web search → call `llm_service.generate_answer()` with `prompt_template=WEB_FALLBACK_PROMPT` → prepend disclaimer
  - Set `source_type` correctly: `"archive"` or `"web_fallback"`
  - Replace `merged_context` with web-only for web_fallback citations
  - Disclaimer text: `"The requested information was not found in the colonial archive documents. Below is an answer based on web sources:\n\n"`
  - Location: `hybrid_retrieval.py:136-164`
  - Acceptance: Archive answer generated first; web only triggers on fallback
  - Effort: M | Depends: B1 (needs `WEB_FALLBACK_PROMPT` + `prompt_template` param)

- [ ] **A3: Write tests for archive-first behavior**
  - `TestRelevanceScoring::test_vector_score_converts_distance_to_similarity`
  - `TestArchiveFirstBehavior::test_archive_answer_does_not_trigger_web`
  - `TestArchiveFirstBehavior::test_web_fallback_includes_disclaimer`
  - Add `from unittest.mock import AsyncMock` import
  - Acceptance: All new tests pass
  - Effort: M | Depends: A1, A2

- [ ] **A4: Run full test suite**
  - `"C:/Users/yjkim/AppData/Local/Programs/Python/Python313/python.exe" -m pytest tests/ -v`
  - Acceptance: All tests pass (31 existing + new)
  - Effort: S | Depends: A3, B3

---

## Phase B: LLM Prompt Updates (prompt-fix agent)

- [ ] **B1: Update archive prompt + add web fallback prompt**
  - Replace `ANSWER_GENERATION_PROMPT` with archive-focused version:
    - Mention colonial-era Straits Settlements archives
    - Instruct to handle OCR artifacts, financial tables, fragmented text
    - Only use `[archive:N]` markers
  - Add `WEB_FALLBACK_PROMPT` constant for web-only answers:
    - Use `[web:N]` markers only
    - Concise and factual
  - Location: `llm.py:13-31`
  - Acceptance: Two separate prompt constants exist
  - Effort: S | Depends: None

- [ ] **B2: Add `prompt_template` parameter to `generate_answer()`**
  - Add `prompt_template: str | None = None` parameter
  - If `prompt_template` is provided, use it instead of `ANSWER_GENERATION_PROMPT`
  - Keep all existing behavior when `prompt_template=None`
  - Location: `llm.py:55-137`
  - Acceptance: Method accepts optional template; existing callers unaffected
  - Effort: S | Depends: B1

- [ ] **B3: Update `test_llm_mixed.py` if prompt format changed**
  - The test checks citation prefix format — should still work
  - Verify test passes; update if assertion on prompt text changed
  - Acceptance: `pytest tests/test_llm_mixed.py -v` passes
  - Effort: S | Depends: B1, B2

---

## Phase C: End-to-End Verification (verifier — after A+B)

- [ ] **C1: Restart backend server**
  - Kill existing uvicorn, restart with `--port 8090`
  - Acceptance: `/health` returns ok
  - Effort: S | Depends: A4

- [ ] **C2: Test archive-answerable query**
  - `curl POST /query {"question":"What was the expenditure of the Straits Settlements in 1932?"}`
  - Acceptance: `source_type="archive"`, answer has `[archive:N]` citations, no web citations
  - Effort: S | Depends: C1

- [ ] **C3: Test web-fallback query**
  - `curl POST /query {"question":"What is the population of Singapore in 2025?"}`
  - Acceptance: `source_type="web_fallback"`, answer starts with disclaimer, has `[web:N]` citations
  - Effort: S | Depends: C1

- [ ] **C4: Test original failing query**
  - `curl POST /query {"question":"explain strait settlement"}`
  - Acceptance: Answer is from archive citations OR web with disclaimer (NOT silently web-dominated)
  - Effort: S | Depends: C1

---

## Summary

| Phase | Tasks | Status | Agent |
|-------|-------|--------|-------|
| A: Scoring + Orchestration | A1-A4 | NOT STARTED | scoring-fix |
| B: LLM Prompts | B1-B3 | NOT STARTED | prompt-fix |
| C: Verification | C1-C4 | NOT STARTED | verifier (lead) |

**Dependency chain:** B1 → A2 (scoring-fix needs `WEB_FALLBACK_PROMPT` from prompt-fix)

**Execution order:**
1. Launch `prompt-fix` and `scoring-fix` in parallel
2. `scoring-fix` does A1 first (independent), then waits for B1 before A2
3. After both complete, lead runs Phase C verification

**Total new tests**: ~3
**Estimated time**: ~15 min with parallel agents
