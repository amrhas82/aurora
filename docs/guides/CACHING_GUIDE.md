# AURORA Memory Search Caching Guide

This guide documents the memory search caching infrastructure implemented in Epic 1 (PRD 0031).

## Overview

AURORA implements a three-layer caching strategy to optimize memory search performance:

1. **HybridRetriever Instance Caching** - Reuse retriever instances across searches
2. **ActivationEngine Singleton** - Share activation engine per database
3. **Shared QueryEmbeddingCache** - Cache query embeddings across all retrievers

## Performance Improvements

**Cold Search:** 15-19s → 10-12s (30-40% improvement)
**Warm Search:** 4-5s → 2-3s (40-50% improvement)
**Cache Overhead:** <10ms per lookup
**Memory Overhead:** <50MB total

## Environment Variables

### HybridRetriever Cache

```bash
# Maximum number of cached retriever instances (default: 10)
export AURORA_RETRIEVER_CACHE_SIZE=10

# Time-to-live for cached retrievers in seconds (default: 1800 = 30 min)
export AURORA_RETRIEVER_CACHE_TTL=1800
```

**Cache Key:** `(db_path, config_hash)`

Cached retrievers are invalidated when:
- Different database path is used
- Configuration changes (weights, top_k, etc.)
- TTL expires (default 30 minutes)
- Cache reaches size limit (LRU eviction)

### ActivationEngine Cache

ActivationEngine uses a **singleton pattern per database** (no configuration needed).

**Cache Key:** `db_path`

Benefits:
- Single engine per database reduces memory usage
- Thread-safe concurrent access
- Lazy initialization (no eager creation)

### QueryEmbeddingCache

QueryEmbeddingCache is **shared across all HybridRetriever instances** (singleton).

Configuration is set via HybridConfig:

```python
from aurora_context_code.semantic.hybrid_retriever import HybridConfig

config = HybridConfig(
    enable_query_cache=True,        # Enable query cache (default: True)
    query_cache_size=100,            # Max cached queries (default: 100)
    query_cache_ttl_seconds=1800,   # TTL in seconds (default: 1800 = 30 min)
)
```

**Note:** First retriever to create the shared cache sets its capacity and TTL. Subsequent retrievers reuse the same cache with original settings.

## Usage Examples

### Basic Usage (Automatic Caching)

```python
from aurora_cli.memory.retrieval import MemoryRetriever
from aurora_core.store import SQLiteStore

# Create store
store = SQLiteStore(".aurora/memory.db")

# Create retriever (uses caching automatically)
retriever = MemoryRetriever(store=store)

# First search (cache miss)
results1 = retriever.retrieve("authentication", limit=10)

# Second search (cache hit - reuses cached retriever and engine)
results2 = retriever.retrieve("database query", limit=10)
```

### Advanced: Direct Cache Access

```python
from aurora_context_code.semantic.hybrid_retriever import (
    get_cached_retriever,
    get_cache_stats,
    clear_retriever_cache,
)
from aurora_core.activation.engine import get_cached_engine
from aurora_core.store import SQLiteStore

store = SQLiteStore(".aurora/memory.db")

# Get cached engine (singleton per db_path)
engine = get_cached_engine(store)

# Get cached retriever
config = HybridConfig(bm25_weight=0.3, activation_weight=0.3, semantic_weight=0.4)
retriever = get_cached_retriever(store, engine, None, config)

# Check cache statistics
stats = get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Cache size: {stats['cache_size']}")

# Clear cache (for testing/debugging)
clear_retriever_cache()
```

### BM25 Index Persistence

BM25 indexes are automatically persisted to disk and loaded on subsequent runs:

**Location:** `.aurora/indexes/bm25_index.pkl` (relative to database)

**Configuration:**

```python
config = HybridConfig(
    enable_bm25_persistence=True,  # Enable persistence (default: True)
)
```

**Logging:**

- ✓ Success: `"✓ Loaded BM25 index from {path} ({corpus_size} documents, {size_mb} MB)"`
- ✗ Missing: `"No persistent BM25 index found at {path}"`
- ✗ Corrupted: `"✗ Failed to load BM25 index from {path} ({error_type}): {error}"`

### Cache Statistics

Monitor cache performance:

```python
from aurora_context_code.semantic.hybrid_retriever import get_cache_stats

stats = get_cache_stats()
print(f"Total hits: {stats['total_hits']}")
print(f"Total misses: {stats['total_misses']}")
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Current cache size: {stats['cache_size']}")
```

## Thread Safety

All caching components are thread-safe:
- `threading.Lock()` used for all cache operations
- No race conditions in concurrent access
- Verified with 5-thread concurrency tests

## Testing

### Unit Tests

```bash
# HybridRetriever caching
pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py -v

# ActivationEngine caching
pytest tests/unit/core/activation/test_engine_cache.py -v

# BM25 persistence
pytest tests/unit/context_code/semantic/test_bm25_persistence.py -v

# Query cache sharing
pytest tests/unit/context_code/semantic/test_query_cache_sharing.py -v
```

### Integration Tests

```bash
pytest tests/integration/test_memory_search_caching.py -v
```

### Performance Tests

```bash
pytest tests/performance/test_search_caching_performance.py -v
```

## Troubleshooting

### Cache not hitting

**Check cache statistics:**
```python
stats = get_cache_stats()
if stats['hit_rate'] < 0.5:
    print("Low hit rate - check if config is changing between searches")
```

**Common causes:**
- Configuration changing between searches (creates new retriever)
- Different database paths
- TTL expired (default 30 minutes)
- Cache cleared or size limit reached

### BM25 index not loading

**Check logs for:**
- `"No persistent BM25 index found"` - Index hasn't been built yet
- `"✗ Failed to load BM25 index"` - Corrupted or incompatible index

**Fix:**
```python
# Rebuild index
retriever.build_and_save_bm25_index()
```

### Memory concerns

**Monitor cache sizes:**
```python
stats = get_cache_stats()
print(f"Cached retrievers: {stats['cache_size']}")

if retriever._query_cache:
    print(f"Cached queries: {retriever._query_cache.size()}")
```

**Adjust cache limits:**
```bash
export AURORA_RETRIEVER_CACHE_SIZE=5  # Reduce retriever cache
```

```python
config = HybridConfig(query_cache_size=50)  # Reduce query cache
```

## Architecture

### Cache Layers

```
┌─────────────────────────────────────┐
│  MemoryRetriever (CLI layer)        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  get_cached_retriever()              │  Cache key: (db_path, config_hash)
│  - LRU eviction (size=10)            │  TTL: 1800s
│  - Thread-safe with Lock             │  Stats: hits, misses, hit_rate
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  HybridRetriever instance            │
│  ├─ get_cached_engine()              │  Cache key: db_path
│  │  (Singleton per db)               │  Lazy initialization
│  └─ get_shared_query_cache()         │  Cache key: query_hash
│     (Singleton, shared)              │  LRU + TTL eviction
└─────────────────────────────────────┘
```

### Cache Invalidation

**HybridRetriever cache invalidates on:**
- Config change (weights, top_k, etc.)
- Different db_path
- TTL expiration
- LRU eviction (when size limit reached)

**ActivationEngine never invalidates** (singleton per db_path for lifetime)

**QueryEmbeddingCache invalidates on:**
- TTL expiration (per query)
- LRU eviction (when size limit reached)

## Best Practices

1. **Use consistent configurations** - Changing config creates new retriever instances
2. **Monitor cache hit rates** - Target >70% hit rate for optimal performance
3. **Tune cache sizes** - Adjust based on workload and memory constraints
4. **Enable BM25 persistence** - Saves ~2-3s on cold searches
5. **Let caches warm up** - First few searches populate caches

## API Reference

### HybridRetriever Caching

```python
get_cached_retriever(
    store: Any,
    activation_engine: Any,
    embedding_provider: Any,
    config: HybridConfig | None = None,
    aurora_config: Any | None = None,
) -> HybridRetriever
```

Returns cached retriever or creates new one. Thread-safe.

```python
get_cache_stats() -> dict[str, Any]
```

Returns: `{"total_hits": int, "total_misses": int, "hit_rate": float, "cache_size": int}`

```python
clear_retriever_cache() -> None
```

Clears all cached retrievers and resets statistics.

### ActivationEngine Caching

```python
get_cached_engine(
    store: Any,
    config: ActivationConfig | None = None
) -> ActivationEngine
```

Returns singleton engine for db_path. Thread-safe.

### QueryEmbeddingCache

```python
get_shared_query_cache(
    capacity: int = 100,
    ttl_seconds: int = 1800
) -> QueryEmbeddingCache
```

Returns shared singleton cache. First call sets capacity/TTL.

```python
clear_shared_query_cache() -> None
```

Clears shared query cache (primarily for testing).

## See Also

- [PRD 0031: Epic 1 Foundation Caching](../../tasks/aur-mem-search/0031-prd-epic1-foundation-caching.md)
- [Performance Testing Guide](../PERFORMANCE_TESTING.md)
- [Commands Guide](./COMMANDS.md)
