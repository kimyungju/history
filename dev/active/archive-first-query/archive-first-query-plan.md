# Archive-First Query Pipeline — Comprehensive Plan

**Last Updated: 2026-03-01**

---

## Executive Summary

The chatbot currently answers most queries using web sources instead of colonial archive documents, defeating the purpose of the RAG system. Two bugs cause this: an inverted distance-to-similarity scoring makes the relevance threshold always fail, and web results get mixed into archive context where the LLM prefers clean web text over messy OCR. The fix implements an archive-first approach: generate from archive context alone, only falling back to web search with a clear disclaimer when the archive genuinely cannot answer.

## Current State Analysis

### The Problem

```
User: "explain strait settlement"
Bot:  "The Straits Settlements was a former British crown colony..." [web:1] [web:2] [web:3]
      ↑ All citations are web sources — archive documents are ignored
```

### Root Causes

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 1 | **Scoring inversion** — cosine distance (~0.41) used directly as similarity score | `hybrid_retrieval.py:114-117` | `vector_score ≈ 0.41` → combined always < 0.7 → web fallback ALWAYS triggers |
| 2 | **Mixed context** — web results appended to archive context before LLM call | `hybrid_retrieval.py:148-149` | LLM sees both, prefers clean web text over OCR artifacts |
| 3 | **Equal-weight prompt** — LLM prompt treats archive and web identically | `llm.py:13-29` | No instruction to prefer archive sources |

### Current Data Flow (Broken)

```
query → embed → vector search (returns results, distance ~0.41)
     → score = 0.41 (raw distance, NOT similarity)
     → 0.41 < 0.7 threshold → ALWAYS triggers web fallback
     → web results MIXED into archive context
     → LLM generates from mixed context → prefers clean web text
     → Answer dominated by [web:N] citations
```

## Proposed Future State

### New Data Flow (Archive-First)

```
query → embed → parallel(vector search, graph search)
     → merge archive context
     → score = 1.0 - 0.41 = 0.59 (corrected similarity)
     → LLM generates answer from ARCHIVE-ONLY context
     ├─ If real answer → return with source_type="archive" ✓
     └─ If FALLBACK_ANSWER → web search → LLM with web context
                           → prepend disclaimer → source_type="web_fallback"
```

### User Experience

**Archive can answer:**
```
User: "What was the expenditure in 1932?"
Bot:  "The expenditure for 1932 was $13,695,633 [archive:1]..."
      Source: Archive  ← gold citation badges
```

**Archive cannot answer:**
```
User: "What is the population of Singapore in 2025?"
Bot:  "The requested information was not found in the colonial archive
       documents. Below is an answer based on web sources:

       The population of Singapore in 2025 is approximately 5.9 million [web:1]..."
      Source: Web sources  ← emerald badges + footer label
```

## Multi-Agent Team Strategy

### Agent Partitioning

| Agent | Scope | Files Owned | Parallel? |
|-------|-------|-------------|-----------|
| **scoring-fix** | Fix distance→similarity + archive-first orchestration | `hybrid_retrieval.py`, `test_hybrid_retrieval.py` | Yes |
| **prompt-fix** | Update LLM prompts for archive-priority + web fallback | `llm.py`, `test_llm_mixed.py` | Yes |
| **verifier** (lead) | End-to-end verification, restart server, test queries | Read-only | After both |

### Why This Partitioning

- **Zero file overlap**: scoring-fix owns `hybrid_retrieval.py`; prompt-fix owns `llm.py`
- **Independent concerns**: Scoring logic vs prompt engineering
- **Clean interface**: `hybrid_retrieval.py` calls `llm_service.generate_answer()` — the method signature is the only contract between the two agents

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Archive OCR text too noisy for LLM to extract meaning | Medium | Medium | Update archive prompt to handle OCR artifacts, tables, fragmented text |
| Two LLM calls for web fallback adds latency | Low | Low | Only triggers when archive can't answer; most queries archive-answerable |
| `test_llm_mixed.py` breaks from prompt change | High | Low | prompt-fix agent updates the test |
| Scoring fix changes threshold behavior for edge cases | Low | Medium | Log both raw distance and converted similarity for monitoring |

## Success Metrics

1. "explain strait settlement" → answer uses `[archive:N]` citations OR clear web disclaimer
2. No web citations appear when archive has relevant content
3. Web fallback responses start with disclaimer text
4. `source_type` is `"archive"` for archive-answerable queries
5. All 31 existing tests continue to pass
6. New tests cover scoring conversion + archive-first behavior
