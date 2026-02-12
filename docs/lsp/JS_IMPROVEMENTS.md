# LSP JavaScript Improvements Plan

Based on testing on [terribic](https://github.com/hamr0/terribic) JS project.

## Test Results Summary

| Tool | Status | Issue |
|------|--------|-------|
| mem_search (exact) | Good | parsePDF, createMessageRouter found correctly |
| lsp imports | Good | All 6 importers of store.js found |
| lsp check | OK | Quick ref count works |
| mem_search (descriptive) | Broken | "DocumentStore search FTS5" → 0 results |
| lsp impact | Broken | createMessageRouter → 1 file (should be 5+) |
| lsp related | Broken | parsePDF → 0 calls (should be 5+) |
| lsp deadcode | Noisy | 4/4 "dead" symbols are callbacks (false positives) |
| name field | Bug | Truncated: "DF(fileP" instead of parsePDF |

## Phase 1: Quick Wins (this PR)

### 1. Expand JS callback skip list for deadcode
**File:** `packages/lsp/src/aurora_lsp/languages/javascript.py`
**Problem:** `setInterval()`, `setTimeout()`, `setImmediate()` callbacks flagged as dead code.
These are timer/scheduler callbacks — never directly called by user code.
**Fix:** Add timer functions and common Node.js patterns to `JS_CALLBACK_METHODS`.

### 2. Improve BM25 for multi-word descriptive queries
**File:** `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
**Problem:** "DocumentStore search FTS5" returns 0 because:
- BM25 stage 1 returns candidates sorted by score
- Code chunks only index name+signature+docstring (not body)
- A chunk about DocumentStore may not mention "FTS5" in its signature
- Chunk gets low BM25 score → filtered out in stage1_top_k
**Fix:** Include chunk body content in BM25 indexing for richer matching. Also,
add `_get_chunk_content_for_bm25` to include the full content when available.

### 3. Add error logging when JS/TS LSP server fails
**File:** `packages/lsp/src/aurora_lsp/client.py`
**Problem:** `request_references` swallows exceptions at `logger.debug` level.
When multilspy fails to start the JS language server (e.g. `typescript-language-server`
not installed), the user gets empty results with no indication of why.
**Fix:** Log at WARNING level when server startup fails, and at INFO level when
references return empty for a file type that should have LSP support.

## Phase 2: Full JS/TS Language Server (future)

### 4. Wire up typescript-language-server in multilspy
**Problem:** multilspy's JS/TS support needs `typescript-language-server` installed and
properly configured. The `impact`, `related`, and accurate `deadcode` actions all depend
on working LSP references which currently return empty for JS.
**Effort:** 3-4 days
**Scope:** Out of scope for this PR.

---

## Implementation Notes

### Callback skip list (Task 1)
Current `JS_CALLBACK_METHODS` has: map, filter, sort, reduce, forEach, find, findIndex,
some, every, flatMap, then, catch, finally, transaction, on, once, addEventListener,
removeEventListener, subscribe, pipe.

Missing patterns from terribic test:
- `setInterval`, `setTimeout`, `setImmediate` — timer callbacks
- `process.on`, `process.once` — Node.js process events
- `bot.on`, `bot.catch` — framework event handlers (already covered by `on`/`catch` in methods list)

Note: `setInterval`/`setTimeout` are in `JS_SKIP_NAMES` (callee skip) but NOT in
`JS_CALLBACK_METHODS` (deadcode skip). The deadcode detector sees a function passed to
`setInterval(fn, 1000)` and doesn't recognize `setInterval` as a callback-consuming method.

### BM25 content enrichment (Task 2)
Current `_get_chunk_content_for_bm25` returns: name + signature + docstring.
This misses function body content. For JS especially, where docstrings are less common,
the body content is where the meaningful keywords live.

Approach: Fall back to chunk content (from `to_json()`) when signature/docstring is sparse.

### LSP error visibility (Task 3)
Current log levels:
- `_ensure_server`: `logger.debug` on startup
- `request_references`: `logger.debug` on failure → should be WARNING for non-Python
- `request_definition`: `logger.warning` on failure (already good)
