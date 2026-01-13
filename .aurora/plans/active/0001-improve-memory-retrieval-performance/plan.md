# Plan: Improve Memory Retrieval Performance

**ID:** 0001-improve-memory-retrieval-performance
**Status:** Draft
**Created:** 2026-01-12

## Problem Statement

Memory retrieval for natural language queries is slow on a repository with ~12,500 chunks (56MB database). The current bottlenecks are:

1. **No caching integration** - `CacheManager` and `QueryOptimizer` exist in `aurora_core.optimization` but are not used by `HybridRetriever`
2. **BM25 index rebuilt per query** - In `_stage1_bm25_filter()`, a new `BM25Scorer` is created and index rebuilt for every retrieval call
3. **Sequential embedding generation** - Query embeddings generated synchronously without caching
4. **Full candidate scan** - All 100+ activation candidates re-scored even for repeated/similar queries

## Current Architecture

```
Query → HybridRetriever
         ├── Stage 1: BM25 Filter (rebuild index each time)
         │   └── Retrieve top 100 by activation
         │   └── Build BM25 index from 100 docs
         │   └── Score all candidates
         ├── Stage 2: Tri-hybrid re-rank
         │   └── Generate query embedding (slow ~50-100ms)
         │   └── Calculate semantic similarity
         │   └── Normalize and combine scores
         └── Return top K
```

## Proposed Improvements

### Phase 1: Query Embedding Cache (Quick Win)
**Impact: ~50-100ms per repeated query**

Cache query embeddings using LRU cache with TTL. Natural language queries often repeat or have overlapping tokens.

- Add `@lru_cache` wrapper for `EmbeddingProvider.embed_query()`
- Use hash of normalized query as key
- TTL: 30 minutes (configurable)

### Phase 2: Persistent BM25 Index (Medium Impact)
**Impact: ~50-100ms per query**

Instead of rebuilding BM25 index per query, persist it and update incrementally.

- Save BM25 index to disk during `aur mem index`
- Load once at retriever initialization
- Invalidate only when chunks change

### Phase 3: Integrate CacheManager (High Impact)
**Impact: Cache hits avoid full retrieval path**

Wire up existing `CacheManager` from `aurora_core.optimization`:
- Hot cache for recent query results
- Activation score cache (10-min TTL already designed)
- Cache statistics for monitoring

### Phase 4: Pre-computed Activations (High Impact)
**Impact: Avoid activation calculation per query**

Store pre-computed base-level activations and only apply time-decay at query time.

- Batch update activations during indexing
- Store in SQLite with chunk embeddings
- Only calculate spreading activation dynamically

### Phase 5: Configuration Tuning
**Impact: Reduce candidate pool**

Add config options to tune performance vs recall tradeoff:

```json
"retrieval": {
  "stage1_candidates": 50,      // Default 100
  "activation_top_k": 50,       // Default 100
  "enable_bm25_cache": true,
  "enable_query_cache": true,
  "query_cache_ttl_seconds": 1800
}
```

## Non-Goals

- Switching embedding models (all-MiniLM-L6-v2 is already optimized)
- Async/parallel processing (adds complexity for marginal gains)
- External vector databases (keep local-first philosophy)

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Cold query (12K chunks) | ~2s | <500ms |
| Warm query (cached) | N/A | <100ms |
| Cache hit rate (after 100 queries) | 0% | >30% |

## Dependencies

- Existing `CacheManager` in `packages/core/src/aurora_core/optimization/cache_manager.py`
- Existing `BM25Scorer.save_index()`/`load_index()` methods
- Config system supports nested keys

## Risks

1. **Cache invalidation complexity** - Mitigated by TTL and explicit invalidation on index
2. **Memory growth** - Mitigated by LRU eviction and configurable limits
3. **Stale results** - Acceptable tradeoff; users can `--no-cache` if needed
