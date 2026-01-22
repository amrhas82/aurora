# High-Level Design: Unified Caching Strategy

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Status** | Draft |
| **Author** | System Architect |
| **Date** | 2025-01-14 |
| **Related** | Performance Analysis, Hybrid Retrieval |

---

## 1. Executive Summary

This document defines a unified caching strategy for Aurora's memory retrieval system, targeting:
- **BM25 scores** - Keyword matching scores
- **Embeddings** - Semantic vectors
- **ACT-R activation values** - Memory access patterns

### Performance Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Cold search | 15-19s | <3s | 5-6x faster |
| Warm search | 4-5s | <500ms | 8-10x faster |
| Re-index time | 100s | <20s | 5x faster |
| Memory footprint | Unbounded | <100MB | Bounded |

---

## 2. Problem Statement

### Current Bottlenecks (from Performance Analysis)

1. **BM25 Index Rebuild (~51% of search time)**
   - Index rebuilt from scratch on each query when no persistent index
   - 36,924 regex tokenization calls for 500 chunks
   - No caching of tokenized documents

2. **Embedding Generation (~88% of index time)**
   - No content-hash based caching for unchanged code
   - Model inference dominates pipeline (106ms per chunk)
   - Query embeddings regenerated on repeat queries

3. **Activation Calculation (~100-400ms per search)**
   - Spreading activation graph rebuilt frequently
   - No caching of base-level activation between queries
   - Access stats fetched per-chunk in some paths

### Existing Caching Infrastructure

Aurora already has several caching components:

| Component | Location | Purpose | Gap |
|-----------|----------|---------|-----|
| `CacheManager` | `aurora_core/optimization/cache_manager.py` | 3-tier chunk cache | Not integrated with retrieval |
| `QueryEmbeddingCache` | `hybrid_retriever.py` | LRU query embedding cache | Not shared across retrievers |
| `RelationshipGraphCache` | `aurora_core/activation/graph_cache.py` | Spreading activation graph | Well implemented |
| `PlanDecompositionCache` | `aurora_cli/planning/cache.py` | SOAR decomposition results | N/A for retrieval |
| `BM25Scorer.save_index()` | `bm25_scorer.py` | Persistent BM25 index | Not called during indexing |

---

## 3. Architecture Overview

### 3.1 Cache Tier Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AURORA RETRIEVAL CACHE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                      TIER 1: HOT CACHE (In-Memory)                      │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │  │  Query Cache    │  │  BM25 Scores    │  │  Activation     │        │
│  │  │  (Embeddings)   │  │  (Document TF)  │  │  (Components)   │        │
│  │  │  LRU: 100       │  │  LRU: 1000      │  │  TTL: 10min     │        │
│  │  │  TTL: 30min     │  │  No TTL         │  │  Max: 5000      │        │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│  │  Target: <1ms lookup | ~50MB max memory                                │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                    │                                        │
│                                    ▼ (Promotion/Eviction)                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                    TIER 2: WARM CACHE (Persistent)                      │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │  │  BM25 Index     │  │  Embedding      │  │  Access Stats   │        │
│  │  │  (Pickle)       │  │  Cache (SQLite) │  │  (SQLite)       │        │
│  │  │  .aurora/       │  │  Content-hash   │  │  Per-chunk      │        │
│  │  │  indexes/       │  │  indexed        │  │  Already exists │        │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│  │  Target: <5ms lookup | Survives restart                                │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                    │                                        │
│                                    ▼ (Fallback)                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │                    TIER 3: COLD SOURCE (Compute)                        │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │  │  BM25 Scorer    │  │  Embedding      │  │  Activation     │        │
│  │  │  .build_index() │  │  Provider       │  │  Engine         │        │
│  │  │  .score()       │  │  .embed_query() │  │  .calculate()   │        │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│  │  Target: Full compute only on cache miss                               │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
Query → Normalize → Hash → Hot Cache Check → Warm Cache Check → Compute → Cache
                         │                 │                    │
                         ▼                 ▼                    ▼
                    Return (1ms)      Return (5ms)        Return + Store
```

---

## 4. Component Design

### 4.1 BM25 Score Caching

#### Current State
- `BM25Scorer` has `save_index()` and `load_index()` methods
- `build_and_save_bm25_index()` exists in `HybridRetriever` but **not called during indexing**
- Each search rebuilds BM25 index from candidates when no persistent index

#### Proposed Solution

**A. Persistent BM25 Index (Tier 2)**

```python
# Location: aurora_context_code/semantic/bm25_cache.py

class BM25Cache:
    """Persistent BM25 index with document tokenization cache."""

    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.token_cache_path = index_path.with_suffix('.tokens.db')
        self._scorer: BM25Scorer | None = None
        self._tokenized_docs: dict[str, list[str]] = {}  # doc_id -> tokens

    def get_or_build(self, documents: list[tuple[str, str]]) -> BM25Scorer:
        """Load cached index or build from documents."""
        if self._try_load():
            return self._scorer

        # Build and cache
        self._scorer = BM25Scorer(k1=1.5, b=0.75)
        self._scorer.build_index(documents)
        self._save()
        return self._scorer

    def _save(self) -> None:
        """Save index with tokenized documents for incremental updates."""
        self._scorer.save_index(self.index_path)
        # Also save tokenized docs for incremental updates
        self._save_token_cache()
```

**B. Tokenization Cache (Tier 1)**

```python
# Pre-cache tokenized documents during index build
class TokenizationCache:
    """Cache tokenized documents to avoid repeated regex operations."""

    def __init__(self, capacity: int = 10000):
        self._cache: dict[str, list[str]] = {}
        self.capacity = capacity

    def tokenize(self, doc_id: str, content: str) -> list[str]:
        """Get cached tokens or tokenize and cache."""
        if doc_id in self._cache:
            return self._cache[doc_id]

        tokens = bm25_tokenize(content)

        if len(self._cache) < self.capacity:
            self._cache[doc_id] = tokens

        return tokens
```

**C. Integration Point**

```python
# In aur mem index command (memory.py)
@cli.command("index")
def index(...):
    # After indexing chunks...
    retriever = get_hybrid_retriever(store)
    retriever.build_and_save_bm25_index()  # ← Add this call
```

#### Cache Key Strategy

| Component | Key Format | Example |
|-----------|------------|---------|
| BM25 Index | `{project_hash}_{chunk_count}_{schema_version}` | `a1b2c3_840_v1` |
| Tokenized Doc | `chunk_id` | `code:src/main.py:42:100` |

### 4.2 Embedding Caching

#### Current State
- Query embeddings cached via `QueryEmbeddingCache` (LRU, 100 entries, 30min TTL)
- Chunk embeddings stored in SQLite as BLOBs
- No content-hash based caching for unchanged chunks during re-index

#### Proposed Solution

**A. Query Embedding Cache (Tier 1) - Shared Instance**

```python
# Location: aurora_cli/memory/retrieval.py

class MemoryRetriever:
    # Make query cache a shared class attribute
    _shared_query_cache: QueryEmbeddingCache | None = None

    @classmethod
    def get_shared_query_cache(cls) -> QueryEmbeddingCache:
        if cls._shared_query_cache is None:
            cls._shared_query_cache = QueryEmbeddingCache(
                capacity=100,
                ttl_seconds=1800
            )
        return cls._shared_query_cache
```

**B. Chunk Embedding Cache (Tier 2) - Content-Hash Based**

```python
# Location: aurora_context_code/semantic/embedding_cache.py

class EmbeddingCache:
    """Content-hash based embedding cache for incremental indexing."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self._conn: sqlite3.Connection | None = None

    def _init_schema(self):
        """Create cache table with content hash index."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                content_hash TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)

    def get(self, content_hash: str) -> bytes | None:
        """Get cached embedding by content hash."""
        cursor = self._conn.execute(
            "SELECT embedding FROM embedding_cache WHERE content_hash = ?",
            (content_hash,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def put(self, content_hash: str, embedding: bytes, model_name: str) -> None:
        """Cache embedding with content hash."""
        self._conn.execute(
            """INSERT OR REPLACE INTO embedding_cache
               (content_hash, embedding, model_name, created_at)
               VALUES (?, ?, ?, ?)""",
            (content_hash, embedding, model_name, time.time())
        )
```

**C. Integration with Indexer**

```python
# In aurora_context_code/indexer.py

class CodeIndexer:
    def __init__(self, ..., embedding_cache: EmbeddingCache | None = None):
        self.embedding_cache = embedding_cache

    def _get_embedding(self, content: str) -> bytes:
        """Get embedding from cache or generate."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]

        if self.embedding_cache:
            cached = self.embedding_cache.get(content_hash)
            if cached:
                return cached

        # Generate embedding
        embedding = self.embedding_provider.embed_text(content)
        embedding_bytes = embedding.tobytes()

        if self.embedding_cache:
            self.embedding_cache.put(content_hash, embedding_bytes, self.model_name)

        return embedding_bytes
```

### 4.3 ACT-R Activation Caching

#### Current State
- `CacheManager.activation_cache` exists with 10-minute TTL
- `RelationshipGraphCache` caches spreading activation graph
- `ActivationEngine` recalculates all components each time

#### Proposed Solution

**A. Component-Level Activation Cache (Tier 1)**

```python
# Extend CacheManager in aurora_core/optimization/cache_manager.py

@dataclass
class ActivationCacheEntry:
    """Cached activation components."""
    bla: float
    decay: float
    access_count: int
    last_computed: float

class EnhancedCacheManager(CacheManager):
    """Extended cache manager with component-level activation caching."""

    def __init__(self, ...):
        super().__init__(...)
        self._activation_components: dict[ChunkID, ActivationCacheEntry] = {}
        self._activation_ttl = 600  # 10 minutes

    def get_activation_components(
        self,
        chunk_id: ChunkID,
        current_access_count: int
    ) -> ActivationCacheEntry | None:
        """Get cached activation components if still valid."""
        if chunk_id not in self._activation_components:
            return None

        entry = self._activation_components[chunk_id]

        # Invalidate if access count changed (BLA needs recalculation)
        if entry.access_count != current_access_count:
            return None

        # Check TTL for decay component
        if time.time() - entry.last_computed > self._activation_ttl:
            return None

        return entry
```

**B. Spreading Activation Cache - Already Well Implemented**

The existing `RelationshipGraphCache` is well-designed:
- Rebuilds every 100 retrievals
- Limits to 1000 edges max
- Thread-safe with TTL support

**Recommendation**: Keep as-is, but ensure it's integrated with the unified cache manager.

**C. Batch Activation Calculation**

```python
# In hybrid_retriever.py

def _calculate_activations_batch(
    self,
    chunk_ids: list[ChunkID],
    cache: CacheManager
) -> dict[ChunkID, float]:
    """Calculate activations with batch optimization."""
    results = {}
    to_compute = []

    # Check cache first
    for chunk_id in chunk_ids:
        cached = cache.get_activation(chunk_id)
        if cached is not None:
            results[chunk_id] = cached
        else:
            to_compute.append(chunk_id)

    if not to_compute:
        return results

    # Batch fetch access stats
    access_stats = self.store.get_access_stats_batch(to_compute)

    # Calculate and cache
    for chunk_id in to_compute:
        stats = access_stats.get(chunk_id, {})
        activation = self._calculate_single_activation(chunk_id, stats)
        cache.set_activation(chunk_id, activation)
        results[chunk_id] = activation

    return results
```

---

## 5. Cache Invalidation Strategy

### 5.1 Invalidation Triggers

| Trigger | Affected Caches | Action |
|---------|-----------------|--------|
| `aur mem index` | BM25, Embeddings | Full invalidation |
| Chunk update | BM25 (doc), Embedding (chunk) | Selective invalidation |
| TTL expiry | Query embeddings, Activations | Automatic |
| Memory pressure | Tier 1 caches | LRU eviction |
| Schema version change | All persistent | Full invalidation |

### 5.2 Invalidation Implementation

```python
# Location: aurora_core/optimization/cache_coordinator.py

class CacheCoordinator:
    """Coordinates cache invalidation across all tiers."""

    def __init__(
        self,
        hot_cache: CacheManager,
        bm25_cache: BM25Cache,
        embedding_cache: EmbeddingCache,
        graph_cache: RelationshipGraphCache
    ):
        self._caches = {
            'hot': hot_cache,
            'bm25': bm25_cache,
            'embedding': embedding_cache,
            'graph': graph_cache
        }

    def invalidate_on_index(self) -> None:
        """Full invalidation after reindexing."""
        self._caches['bm25'].invalidate()
        self._caches['hot'].clear_all()
        self._caches['graph'].invalidate()
        # Note: embedding_cache NOT invalidated (content-hash based)

    def invalidate_chunk(self, chunk_id: ChunkID, content_hash: str) -> None:
        """Selective invalidation for single chunk update."""
        self._caches['hot'].invalidate_chunk(chunk_id)
        self._caches['bm25'].invalidate_document(chunk_id)
        # embedding_cache: old hash naturally unused, new hash computed

    def invalidate_on_version_change(self, old_version: str, new_version: str) -> None:
        """Full invalidation on schema/version change."""
        for cache in self._caches.values():
            cache.clear_all()
```

### 5.3 Cache Versioning

```python
CACHE_VERSION = "1.0.0"

class VersionedCache:
    """Base class for versioned caches."""

    def _validate_version(self, stored_version: str) -> bool:
        """Check if cached data is compatible."""
        return stored_version.split('.')[0] == CACHE_VERSION.split('.')[0]
```

---

## 6. Memory Management

### 6.1 Memory Budgets

| Cache | Max Size | Estimated Memory |
|-------|----------|------------------|
| Query Embeddings | 100 entries | ~30KB (384-dim vectors) |
| BM25 Tokenized Docs | 1000 entries | ~10MB |
| Activation Components | 5000 entries | ~2MB |
| Hot Chunk Cache | 1000 entries | ~10MB |
| **Total Tier 1** | - | **~50MB max** |

### 6.2 Memory Monitoring

```python
class CacheMemoryMonitor:
    """Monitor cache memory usage."""

    def get_memory_usage(self) -> dict[str, int]:
        """Estimate memory usage per cache."""
        return {
            'query_embeddings': self._estimate_query_cache_size(),
            'bm25_tokens': self._estimate_token_cache_size(),
            'activations': self._estimate_activation_cache_size(),
            'hot_chunks': self._estimate_hot_cache_size(),
            'total': sum(...)
        }

    def apply_memory_pressure(self, target_mb: int) -> None:
        """Reduce cache sizes to meet memory target."""
        # Evict from largest caches first
        ...
```

---

## 7. Implementation Plan

### Phase 1: Quick Wins (Week 1)

| Task | Impact | Effort |
|------|--------|--------|
| Call `build_and_save_bm25_index()` during `aur mem index` | High | Low |
| Share `QueryEmbeddingCache` across retriever instances | Medium | Low |
| Cache `ActivationEngine` instance in `MemoryRetriever` | Medium | Low |

**Expected Result**: Warm search reduced from 4-5s to ~1-2s

### Phase 2: Persistent Caching (Week 2-3)

| Task | Impact | Effort |
|------|--------|--------|
| Implement content-hash based `EmbeddingCache` | High | Medium |
| Add tokenization cache to BM25 scoring | Medium | Medium |
| Create `CacheCoordinator` for unified invalidation | Medium | Medium |

**Expected Result**: Re-index reduced from 100s to ~20s for unchanged files

### Phase 3: Full Integration (Week 4)

| Task | Impact | Effort |
|------|--------|--------|
| Integrate with `CacheManager` for activation caching | Medium | Medium |
| Add memory monitoring and pressure handling | Low | Medium |
| Performance benchmarks and regression guards | Low | Low |

**Expected Result**: All targets met, bounded memory usage

---

## 8. ADRs (Architecture Decision Records)

### ADR-001: Use SQLite for Embedding Cache

**Context**: Need persistent storage for content-hash based embedding cache.

**Decision**: Use SQLite (same as memory.db) rather than file-based storage.

**Rationale**:
- Consistent with existing architecture
- Transactional integrity
- Easy to query by hash
- Single file to manage

**Alternatives Considered**:
- File-per-embedding: Too many files, no transactional integrity
- Redis: External dependency, overkill for local CLI
- In-memory only: Loses benefit across sessions

### ADR-002: Content-Hash for Embedding Cache Keys

**Context**: Need to cache embeddings to avoid regeneration on re-index.

**Decision**: Use SHA256 content hash (truncated to 32 chars) as cache key.

**Rationale**:
- Unchanged code automatically hits cache
- No need to track file paths or chunk IDs
- Works across renames/moves
- Collision probability negligible at 128 bits

### ADR-003: Separate Activation Component Caching

**Context**: Activation has 4 components with different invalidation needs.

**Decision**: Cache BLA and decay separately from spreading and context.

**Rationale**:
- BLA changes only when access count changes
- Decay is time-based (needs TTL)
- Spreading depends on relationship graph (separate cache)
- Context is query-specific (not cached)

---

## 9. Observability

### 9.1 Metrics to Track

```python
CACHE_METRICS = {
    # Hit rates
    "cache.bm25.hit_rate": Gauge,
    "cache.embedding.hit_rate": Gauge,
    "cache.activation.hit_rate": Gauge,

    # Latencies
    "cache.lookup.latency_ms": Histogram,
    "cache.compute.latency_ms": Histogram,

    # Sizes
    "cache.memory.bytes": Gauge,
    "cache.entries.count": Gauge,

    # Operations
    "cache.invalidation.count": Counter,
    "cache.eviction.count": Counter,
}
```

### 9.2 Logging

```python
# Debug logging for cache operations
logger.debug(
    "Cache lookup",
    extra={
        "cache": "bm25",
        "key": key[:16],
        "hit": hit,
        "latency_ms": elapsed,
    }
)
```

---

## 10. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache corruption | Low | High | Validate on load, rebuild on error |
| Memory bloat | Medium | Medium | Bounded sizes, LRU eviction |
| Stale data | Medium | Low | TTLs, explicit invalidation |
| Version mismatch | Low | Medium | Version headers, auto-invalidate |

---

## 11. Success Criteria

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Cold search time | <3s | `aur mem search` after clear |
| Warm search time | <500ms | `aur mem search` repeated |
| Re-index time (unchanged) | <20s | `aur mem index` on same code |
| Memory usage | <100MB | Process memory delta |
| Cache hit rate | >60% | After 10 queries |

---

## Appendix A: File Locations

| Component | Location |
|-----------|----------|
| CacheManager | `packages/core/src/aurora_core/optimization/cache_manager.py` |
| CacheCoordinator | `packages/core/src/aurora_core/optimization/cache_coordinator.py` (new) |
| BM25Cache | `packages/context-code/src/aurora_context_code/semantic/bm25_cache.py` (new) |
| EmbeddingCache | `packages/context-code/src/aurora_context_code/semantic/embedding_cache.py` (new) |
| QueryEmbeddingCache | `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` |
| GraphCache | `packages/core/src/aurora_core/activation/graph_cache.py` |

## Appendix B: Configuration Schema

```json
{
  "cache": {
    "bm25": {
      "enabled": true,
      "index_path": ".aurora/indexes/bm25_index.pkl"
    },
    "embedding": {
      "enabled": true,
      "cache_path": ".aurora/cache/embeddings.db",
      "max_entries": 50000
    },
    "activation": {
      "enabled": true,
      "ttl_seconds": 600,
      "max_entries": 5000
    },
    "query": {
      "enabled": true,
      "capacity": 100,
      "ttl_seconds": 1800
    }
  }
}
```
