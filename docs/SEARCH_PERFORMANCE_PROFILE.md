# `aur mem search` Performance Profile

This document provides a detailed performance analysis of the `aur mem search` command, identifying bottlenecks and potential optimizations.

## Executive Summary

| Scenario | Total Time | Primary Bottleneck |
|----------|------------|-------------------|
| Cold start (first search) | ~15-19s | Embedding model load (9-12s) |
| Warm start (BM25-only mode) | ~4-5s | BM25 tokenization (3.5s) |
| With persisted BM25 index | ~2-3s (estimated) | Query embedding (0.4s) |

**Key Finding**: The "fast mode" with background model loading is already implemented and working effectively, reducing perceived latency from ~15s to ~5s.

## Detailed Profiling Results

### Phase-by-Phase Breakdown (Cold Start)

| Phase | Component | Time (ms) | % Total | Notes |
|-------|-----------|-----------|---------|-------|
| 1 | Import: aurora_cli.config | 290 | 1.5% | Rich, click, config loading |
| 1 | Import: aurora_core.store.sqlite | 15 | 0.1% | ✅ Fast |
| 1 | Import: aurora_cli.memory.retrieval | 11 | 0.1% | ✅ Fast |
| 1 | Import: aurora_context_code.model_cache | 2 | 0.0% | ✅ Lightweight module |
| 2 | Config loading | 1 | 0.0% | ✅ Fast |
| 3 | SQLiteStore initialization | 0.2 | 0.0% | ✅ Deferred schema init |
| 3 | Schema initialization (first query) | 5 | 0.0% | ✅ Fast |
| 4 | Model cache check (filesystem) | 0.4 | 0.0% | ✅ Fast |
| 5 | BM25 index load | N/A | - | ❌ Index not persisted |
| 6 | MemoryRetriever initialization | 0.02 | 0.0% | ✅ Fast |
| **7** | **Embedding model load (synchronous)** | **9,196-12,265** | **62-68%** | ❌ **Primary bottleneck** |
| **8** | **Query embedding generation** | **2,400-3,057** | **15-16%** | ⚠️ Includes model warmup |
| 9 | DB: retrieve_by_activation | 95-106 | 0.5-0.7% | ✅ Acceptable |
| **10** | **BM25: build index from chunks** | **139-188** | **0.8-1.1%** | ⚠️ Should be cached |
| 10 | BM25: score all chunks | 70-85 | 0.4-0.6% | ✅ Acceptable |
| 11 | Semantic: score all chunks | 4-6 | 0.0% | ✅ Very fast |
| **12** | **Full search (retrieve_fast)** | **2,086-2,863** | **11-15%** | ⚠️ End-to-end time |

### cProfile Function-Level Analysis

Top 10 time-consuming functions:

| Function | Total Time | Calls | Notes |
|----------|------------|-------|-------|
| `hybrid_retriever.retrieve()` | 4.7s | 1 | Entry point |
| **`bm25_scorer.tokenize()`** | **3.8s** | **36,924** | ❌ **Major bottleneck** |
| `hybrid_retriever._stage1_bm25_filter()` | 3.5s | 1 | BM25 filtering stage |
| `bm25_scorer.build_index()` | 2.3s | 1 | ⚠️ Should be cached |
| `bm25_scorer.score()` | 1.7s | 599 | Per-chunk scoring |
| `re.findall()` | 1.1s | 157,889 | Used by tokenizer |
| `re.split()` | 0.57s | 36,924 | Used by tokenizer |
| `embedding_provider.embed_query()` | 0.49s | 1 | After model loaded |
| `sqlite.retrieve_by_activation()` | 0.17s | 1 | Database query |
| `sqlite._deserialize_chunk()` | 0.13s | 500 | JSON deserialization |

## Identified Bottlenecks

### 1. Embedding Model Loading (~9-12s) - **Primary Bottleneck**

**Status**: Mitigated with background loading

The embedding model (`sentence-transformers/all-MiniLM-L6-v2`) takes 9-12 seconds to load. However, the current implementation already uses background loading:

```python
# From memory.py search_command()
_start_background_model_loading()  # Non-blocking
```

When model is loading, search falls back to "fast mode" (BM25+activation only), completing in ~5s instead of waiting for full hybrid search.

**Remaining Optimization**: The query embedding generation after model load still takes ~2.4s on first query due to model warmup. This could be reduced with:
- Model preloading during `aur init`
- Query embedding caching (already implemented)

### 2. BM25 Tokenization (~3.5s for 500 chunks)

**Status**: Major optimization opportunity

The `tokenize()` function in `bm25_scorer.py` is called 36,924 times with significant regex overhead:
- `re.findall()`: 1.1s
- `re.split()`: 0.57s

**Root Cause**: Tokenization happens on every search because BM25 index is rebuilt from scratch each time.

**Solution**: Persist BM25 index to disk (already supported but not being used):
```python
# In hybrid_retriever.py
bm25_index_path = Path(db_path).parent / "indexes" / "bm25_index.pkl"
```

The `build_and_save_bm25_index()` method exists but isn't being called during indexing.

### 3. BM25 Index Rebuilding (~2.3s)

**Status**: Should be cached

The BM25 index is being rebuilt on every search instead of loading from disk:

```
📑 Phase 5: BM25 index loading...
   BM25 index not found (will be built on-demand)
```

**Solution**: Ensure `_build_bm25_index()` is called during `aur mem index` (it's in the code but may not be executing).

### 4. Database Query Embeddings (~100ms)

**Status**: Acceptable, but can be optimized

The two-phase retrieval optimization is implemented but could be improved:
- Phase 1: Retrieve without embeddings (should be faster)
- Phase 2: Fetch embeddings only for BM25-filtered candidates

Current timings show both phases take similar time (~90-106ms), suggesting the two-phase optimization isn't providing full benefit.

## Performance Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       aur mem search "query"                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────────────────────────────────────┐  │
│  │ Background  │    │           Main Search Path                  │  │
│  │ Model Load  │    │                                             │  │
│  │   (9-12s)   │    │  1. Config Load        (~1ms)    ✅        │  │
│  │             │    │  2. Store Init         (~5ms)    ✅        │  │
│  │   ⬇ async   │    │  3. Model Cache Check  (~0.5ms)  ✅        │  │
│  │             │    │  4. BM25 Index Load    (~0ms)    ❌ MISSING │  │
│  │  Provides   │    │  5. DB Retrieval       (~100ms)  ✅        │  │
│  │  embeddings │───▶│  6. BM25 Filtering     (~3.5s)   ❌ SLOW    │  │
│  │  when ready │    │  7. Semantic Scoring   (~5ms)    ✅        │  │
│  │             │    │  8. Result Formatting  (~10ms)   ✅        │  │
│  └─────────────┘    │                                             │  │
│                     │  Total Fast Mode: ~4-5s                     │  │
│                     │  Total Full Hybrid: ~15-19s (first query)   │  │
│                     └─────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Recommended Optimizations

### Priority 1: Persist BM25 Index (Expected: -3s)

Ensure BM25 index is saved during `aur mem index`:

```python
# In memory_manager.py, after indexing completes:
if stats["chunks"] > 0:
    self._build_bm25_index()  # Already exists, just ensure it runs
```

**Expected Impact**: Eliminate 3.5s tokenization + 2.3s index building = ~5.8s saved

### Priority 2: Optimize Tokenization (Expected: -1-2s)

The `tokenize()` function uses multiple regex operations. Options:

1. **Pre-compile regex patterns** (moderate gain):
```python
_CAMEL_PATTERN = re.compile(r"([A-Z]+(?=[A-Z][a-z]|\b)|[A-Z][a-z]+|[a-z]+|[0-9]+)")
_SPLIT_PATTERN = re.compile(r"[^\w\.\-]+")
```

2. **Cache tokenization results** (high gain):
```python
@lru_cache(maxsize=10000)
def tokenize_cached(text: str) -> tuple[str, ...]:
    return tuple(tokenize(text))
```

3. **Batch tokenization during indexing** (best):
Store pre-tokenized content in database.

### Priority 3: Query Embedding Warmup (Expected: -2s on first query)

The first query embedding takes ~2.4s due to model warmup. Options:

1. **Warm up during `aur init`**:
```python
# After model download in aur init
provider.embed_query("warmup query")
```

2. **Cache warmup state** with model checkpoint

### Priority 4: Reduce Database I/O

Current: Fetching 500 chunks with embeddings (~100ms)

Options:
1. Reduce `activation_top_k` from 500 to 200 for faster searches
2. Ensure two-phase retrieval is working (embeddings only for top candidates)

## Benchmark Commands

```bash
# Full profiling
python scripts/profile_mem_search.py "authentication" --detailed

# cProfile analysis
python scripts/profile_mem_search.py "authentication" --cprofile

# Quick timing test
time aur mem search "authentication" --limit 5

# Profile with hyperfine (if installed)
hyperfine 'aur mem search "authentication" --limit 5' --warmup 1
```

## Metrics Summary

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Cold start (first search) | 15-19s | <5s | Medium |
| Warm start (BM25-only) | 4-5s | <1s | High |
| With persisted BM25 index | N/A | <500ms | **Critical** |
| Query embedding (warm model) | 400ms | <100ms | Low |
| Database retrieval | 100ms | <50ms | Low |

## Conclusion

The primary performance issues are:

1. **BM25 index not persisted** - Causes 5-6 second overhead on every search
2. **Tokenization overhead** - 3.5s spent on regex operations that should be cached
3. **Model loading** - Already mitigated with background loading

With BM25 index persistence enabled, expected search time should drop from ~5s to ~1s for the common case.
