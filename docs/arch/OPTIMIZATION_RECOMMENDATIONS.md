# Concrete Optimization Recommendations

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Status** | Actionable |
| **Date** | 2025-01-14 |
| **Based On** | HLD_CACHING_STRATEGY.md Analysis |

---

## Executive Summary

Based on analysis of the caching strategy HLD and current implementation, here are **concrete, actionable optimizations** with expected performance improvements.

### Current Performance Baseline

| Metric | Current Value | Source |
|--------|---------------|--------|
| Cold search | 15-19s | Profile report |
| Warm search | 4-5s | Profile report |
| Re-index (no changes) | ~100s | Estimate |
| BM25 rebuild | ~51% of search time | Profiling |
| Embedding generation | ~88% of index time | Profiling |

### Expected Improvements After All Optimizations

| Metric | Current | After Phase 1 | After Phase 2 | Final Target |
|--------|---------|---------------|---------------|--------------|
| Cold search | 15-19s | 8-10s | 3-5s | <3s |
| Warm search | 4-5s | 1-2s | 400-600ms | <500ms |
| Re-index (no changes) | 100s | 80s | 15-25s | <20s |

---

## Phase 1: Quick Wins (Week 1)

### 1.1 Share ActivationEngine Instance Across Searches

**Problem Identified:**
```python
# Current: memory_manager.py:1068
def search(self, query: str, ...):
    activation_engine = ActivationEngine()  # ← NEW instance every search
    retriever = HybridRetriever(self.memory_store, activation_engine, ...)
```

**Root Cause:** `ActivationEngine` is instantiated on every search call, wasting initialization time.

**Fix:**
```python
# memory_manager.py - Add class-level caching

class MemoryManager:
    def __init__(self, ...):
        ...
        self._activation_engine: ActivationEngine | None = None

    @property
    def activation_engine(self) -> ActivationEngine:
        """Lazy-load and cache ActivationEngine."""
        if self._activation_engine is None:
            from aurora_core.activation import ActivationEngine
            self._activation_engine = ActivationEngine()
        return self._activation_engine

    def search(self, query: str, ...):
        retriever = HybridRetriever(
            self.memory_store,
            self.activation_engine,  # ← Reuse cached instance
            self.embedding_provider,
        )
```

**Expected Improvement:**
- **Time saved:** 50-100ms per search (engine initialization)
- **Memory:** ~5MB less per-search overhead
- **Effort:** Low (5-10 lines of code)

---

### 1.2 Share HybridRetriever Instance Across Searches

**Problem Identified:**
```python
# Current: Creates new HybridRetriever every search
def search(self, query: str, ...):
    retriever = HybridRetriever(...)  # ← NEW instance, loses cached BM25 index
    results = retriever.retrieve(query, ...)
```

**Root Cause:** Each `HybridRetriever` instance:
1. Creates a new `QueryEmbeddingCache` (100 entries lost)
2. Re-loads BM25 index from disk
3. Re-initializes internal state

**Fix:**
```python
class MemoryManager:
    def __init__(self, ...):
        ...
        self._retriever: HybridRetriever | None = None
        self._retriever_initialized = False

    @property
    def hybrid_retriever(self) -> HybridRetriever:
        """Lazy-load and cache HybridRetriever."""
        if self._retriever is None:
            from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
            self._retriever = HybridRetriever(
                self.memory_store,
                self.activation_engine,
                self.embedding_provider,
            )
        return self._retriever

    def invalidate_retriever(self) -> None:
        """Call after reindexing to force retriever rebuild."""
        self._retriever = None

    def search(self, query: str, ...):
        results = self.hybrid_retriever.retrieve(query, ...)  # ← Reuse!
```

**Expected Improvement:**
- **Time saved:** 200-500ms per search (BM25 index reload, cache warmup)
- **Query cache hit rate:** 0% → 60%+ for repeated/similar queries
- **Effort:** Low (15-20 lines of code)

---

### 1.3 Confirm BM25 Index Is Being Built During Indexing

**Current State (VERIFIED WORKING):**
```python
# memory_manager.py:982 - Already calls _build_bm25_index()
self._build_bm25_index()  # ✓ Already implemented
```

**Action Required:** Verify index file exists after `aur mem index`:
```bash
ls -la .aurora/indexes/bm25_index.pkl
```

If missing, check:
1. `HybridConfig.bm25_index_path` is set correctly
2. `HybridConfig.enable_bm25_persistence` is `True`
3. Check logs for "Built and saved BM25 index" message

**Expected Improvement:**
- If index exists and loads: Already optimized
- If index missing: **8-10s saved on cold search** (51% of time)

---

## Phase 2: Persistent Caching (Week 2-3)

### 2.1 Content-Hash Based Embedding Cache

**Problem Identified:**
- Re-indexing regenerates ALL embeddings, even for unchanged files
- Embedding generation is ~88% of index time (~106ms per chunk)

**Solution:** Cache embeddings by content hash in SQLite.

**Implementation:**

```python
# NEW FILE: packages/context-code/src/aurora_context_code/semantic/embedding_cache.py

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Optional

class EmbeddingCache:
    """Content-hash based embedding cache for incremental indexing."""

    CACHE_VERSION = "1.0"

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database and schema."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.cache_path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                content_hash TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at REAL NOT NULL,
                version TEXT NOT NULL DEFAULT '1.0'
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_model ON embedding_cache(model_name)"
        )
        self._conn.commit()

    @staticmethod
    def content_hash(content: str) -> str:
        """Generate content hash for cache key."""
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, content: str, model_name: str) -> Optional[bytes]:
        """Get cached embedding by content hash."""
        hash_key = self.content_hash(content)
        cursor = self._conn.execute(
            "SELECT embedding FROM embedding_cache WHERE content_hash = ? AND model_name = ?",
            (hash_key, model_name)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def put(self, content: str, embedding: bytes, model_name: str) -> None:
        """Cache embedding with content hash."""
        hash_key = self.content_hash(content)
        self._conn.execute(
            """INSERT OR REPLACE INTO embedding_cache
               (content_hash, embedding, model_name, created_at, version)
               VALUES (?, ?, ?, ?, ?)""",
            (hash_key, embedding, model_name, time.time(), self.CACHE_VERSION)
        )
        self._conn.commit()

    def stats(self) -> dict:
        """Get cache statistics."""
        cursor = self._conn.execute("SELECT COUNT(*) FROM embedding_cache")
        count = cursor.fetchone()[0]
        cursor = self._conn.execute(
            "SELECT SUM(LENGTH(embedding)) FROM embedding_cache"
        )
        size = cursor.fetchone()[0] or 0
        return {"entries": count, "size_mb": size / (1024 * 1024)}

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
```

**Integration in Indexer:**
```python
# In CodeIndexer or wherever embeddings are generated

class CodeIndexer:
    def __init__(self, ..., embedding_cache: EmbeddingCache | None = None):
        self.embedding_cache = embedding_cache

    def _get_embedding(self, content: str) -> bytes:
        model_name = self.embedding_provider.model_name

        # Try cache first
        if self.embedding_cache:
            cached = self.embedding_cache.get(content, model_name)
            if cached:
                return cached

        # Generate embedding (expensive: ~106ms)
        embedding = self.embedding_provider.embed_text(content)
        embedding_bytes = embedding.tobytes()

        # Cache for future
        if self.embedding_cache:
            self.embedding_cache.put(content, embedding_bytes, model_name)

        return embedding_bytes
```

**Expected Improvement:**
- **Re-index time (unchanged files):** 100s → 15-25s (80-85% reduction)
- **Cache hit rate:** 70-95% for typical re-indexing
- **Storage:** ~2KB per chunk (384-dim float32) × chunk count
- **Effort:** Medium (new file + integration)

---

### 2.2 Tokenization Cache for BM25

**Problem Identified:**
- BM25 index rebuild tokenizes all documents with regex (36,924 calls for 500 chunks)
- Each tokenization involves regex splitting, lowercasing, stopword removal

**Solution:** Cache tokenized documents during index build.

**Implementation:**
```python
# Add to BM25Scorer or as separate module

class TokenizationCache:
    """Cache tokenized documents to avoid repeated regex operations."""

    def __init__(self, capacity: int = 10000):
        self._cache: dict[str, list[str]] = {}
        self.capacity = capacity
        self.hits = 0
        self.misses = 0

    def tokenize(self, doc_id: str, content: str, tokenizer_fn) -> list[str]:
        """Get cached tokens or tokenize and cache."""
        if doc_id in self._cache:
            self.hits += 1
            return self._cache[doc_id]

        self.misses += 1
        tokens = tokenizer_fn(content)

        if len(self._cache) < self.capacity:
            self._cache[doc_id] = tokens

        return tokens

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
```

**Expected Improvement:**
- **BM25 rebuild time:** Reduced by ~40% for cached documents
- **Memory:** ~10MB for 1000 documents
- **Effort:** Low-Medium

---

### 2.3 Batch Access Stats Fetching

**Problem Identified:**
- Activation calculation fetches access stats per-chunk in some paths
- N database round-trips for N chunks

**Solution:** Add batch fetching method.

**Implementation:**
```python
# In SQLiteStore

def get_access_stats_batch(
    self, chunk_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Batch fetch access stats for multiple chunks."""
    if not chunk_ids:
        return {}

    placeholders = ",".join("?" * len(chunk_ids))
    cursor = self.conn.execute(
        f"""SELECT chunk_id, access_count, last_access_time
            FROM access_stats
            WHERE chunk_id IN ({placeholders})""",
        chunk_ids
    )

    return {
        row[0]: {"access_count": row[1], "last_access_time": row[2]}
        for row in cursor.fetchall()
    }
```

**Expected Improvement:**
- **Time saved:** 10-50ms per search (eliminates N round-trips)
- **Effort:** Low (single method addition)

---

## Phase 3: Full Integration (Week 4)

### 3.1 Unified Cache Coordinator

**Purpose:** Single entry point for cache invalidation across all tiers.

```python
# NEW FILE: packages/core/src/aurora_core/optimization/cache_coordinator.py

from dataclasses import dataclass
from typing import Any

@dataclass
class CacheInvalidationEvent:
    """Event for cache invalidation."""
    event_type: str  # "reindex", "chunk_update", "version_change"
    affected_ids: list[str] | None = None
    metadata: dict[str, Any] | None = None

class CacheCoordinator:
    """Coordinates cache invalidation across all tiers."""

    def __init__(
        self,
        query_cache: Any = None,
        bm25_retriever: Any = None,
        embedding_cache: Any = None,
        graph_cache: Any = None,
    ):
        self._caches = {
            "query": query_cache,
            "bm25": bm25_retriever,
            "embedding": embedding_cache,
            "graph": graph_cache,
        }

    def invalidate_on_reindex(self) -> None:
        """Full invalidation after reindexing."""
        if self._caches["query"]:
            self._caches["query"].clear()
        if self._caches["bm25"]:
            self._caches["bm25"].invalidate_bm25_index()
        if self._caches["graph"]:
            self._caches["graph"].invalidate()
        # Note: embedding_cache NOT invalidated (content-hash based)

    def invalidate_chunk(self, chunk_id: str) -> None:
        """Selective invalidation for single chunk update."""
        if self._caches["query"]:
            self._caches["query"].clear()  # Conservative: clear all
        if self._caches["bm25"]:
            self._caches["bm25"].invalidate_bm25_index()  # Force rebuild
```

**Expected Improvement:**
- **Correctness:** Ensures caches stay consistent
- **Maintainability:** Single place for invalidation logic
- **Effort:** Medium

---

### 3.2 Memory Monitoring and Pressure Handling

```python
# Add to CacheManager

class CacheMemoryMonitor:
    """Monitor and bound cache memory usage."""

    MAX_CACHE_MB = 100  # Total memory budget

    def __init__(self):
        self._caches: dict[str, Any] = {}

    def register_cache(self, name: str, cache: Any) -> None:
        self._caches[name] = cache

    def get_total_usage_mb(self) -> float:
        """Estimate total cache memory usage."""
        total = 0.0
        for name, cache in self._caches.items():
            if hasattr(cache, "size_bytes"):
                total += cache.size_bytes() / (1024 * 1024)
        return total

    def apply_pressure(self) -> None:
        """Reduce cache sizes if over budget."""
        usage = self.get_total_usage_mb()
        if usage > self.MAX_CACHE_MB:
            # Evict from largest caches first
            for cache in self._caches.values():
                if hasattr(cache, "evict_lru"):
                    cache.evict_lru(percentage=0.25)
```

---

## Implementation Priority Matrix

| Optimization | Impact | Effort | Priority | Phase |
|--------------|--------|--------|----------|-------|
| 1.1 Share ActivationEngine | Medium | Low | P1 | 1 |
| 1.2 Share HybridRetriever | High | Low | P1 | 1 |
| 1.3 Verify BM25 index | High | None | P0 | 1 |
| 2.1 Content-hash embedding cache | High | Medium | P1 | 2 |
| 2.2 Tokenization cache | Medium | Low | P2 | 2 |
| 2.3 Batch access stats | Medium | Low | P2 | 2 |
| 3.1 Cache coordinator | Low | Medium | P3 | 3 |
| 3.2 Memory monitoring | Low | Medium | P3 | 3 |

---

## Verification Steps

### After Phase 1 Implementation

```bash
# 1. Check BM25 index exists
ls -la .aurora/indexes/bm25_index.pkl

# 2. Run search twice, measure time
time aur mem search "test query"  # First: cold
time aur mem search "test query"  # Second: warm (should be faster)

# 3. Check logs for cache hits
AUR_LOG_LEVEL=debug aur mem search "test query" 2>&1 | grep -i cache
```

### Performance Regression Guards

Add to `tests/performance/`:

```python
import pytest
import time

@pytest.mark.performance
def test_warm_search_under_2s(memory_manager_with_data):
    """Warm search should complete in under 2 seconds."""
    manager = memory_manager_with_data

    # Cold search (warm up)
    manager.search("test query")

    # Warm search (timed)
    start = time.time()
    manager.search("test query")
    elapsed = time.time() - start

    assert elapsed < 2.0, f"Warm search took {elapsed:.2f}s, expected <2s"

@pytest.mark.performance
def test_query_cache_hit_rate_above_50(memory_manager_with_data):
    """Query cache hit rate should be above 50% for repeated queries."""
    manager = memory_manager_with_data

    queries = ["auth", "database", "auth", "config", "auth", "database"]
    for q in queries:
        manager.search(q)

    stats = manager.hybrid_retriever._query_cache.stats
    assert stats.hit_rate > 0.5, f"Hit rate {stats.hit_rate:.2%}, expected >50%"
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Cache corruption | Validate on load, rebuild on error |
| Memory bloat | Bounded sizes, LRU eviction, monitoring |
| Stale data | TTLs, explicit invalidation on reindex |
| Version mismatch | Version headers in cache files |

---

## Summary

**Phase 1 (Quick Wins)** - Implement immediately:
1. Cache `ActivationEngine` instance
2. Cache `HybridRetriever` instance
3. Verify BM25 index is loading

**Expected Result:** Warm search 4-5s → 1-2s

**Phase 2 (Persistent Caching)** - Week 2-3:
1. Content-hash embedding cache
2. Tokenization cache
3. Batch access stats

**Expected Result:** Re-index 100s → 20s, cold search 15s → 3-5s

**Phase 3 (Integration)** - Week 4:
1. Cache coordinator
2. Memory monitoring

**Expected Result:** All targets met, bounded memory, maintainable caching
