# PRD: Epic 1 - Instance & Cache Infrastructure (Foundation)

**PRD ID**: 0031
**Epic**: 1 of 3 - `aur mem search` Performance Optimization
**Status**: Draft
**Author**: Code Developer
**Created**: 2026-01-22

---

## 1. Problem Statement

`aur mem search` is unacceptably slow at 15-19s for cold searches and 4-5s for warm searches, making it impractical for interactive development workflows. The primary bottlenecks are redundant component initialization and missing cache layers:

1. **No HybridRetriever instance caching**: Every search creates a new HybridRetriever instance (200-500ms overhead per search)
2. **No ActivationEngine instance caching**: Every search initializes a new ActivationEngine (50-100ms overhead per search)
3. **BM25 index persistence not working**: Index is rebuilt from scratch on every search (9.7s overhead, 51% of total search time)
4. **No shared QueryEmbeddingCache**: Each HybridRetriever instance has its own embedding cache, preventing cache hits across SOAR phases

These are low-risk wins - pure caching optimizations with no algorithmic changes that could affect search quality.

## 2. Goals

- **G1**: Reduce cold search time from 15-19s to 10-12s (30-40% improvement)
- **G2**: Reduce warm search time from 4-5s to 2-3s (40-50% improvement)
- **G3**: Achieve 60%+ cache hit rate for HybridRetriever instances
- **G4**: Achieve 80%+ cache hit rate for ActivationEngine instances
- **G5**: Reduce BM25 index load time from 9.7s to <100ms (98%+ improvement)
- **G6**: Enable embedding cache sharing across SOAR phases and multiple search contexts

## 3. User Stories

**US1**: As a developer running repeated searches during debugging, I want the second and subsequent searches to be significantly faster without restarting the process, so I can iterate quickly on code exploration.

**US2**: As a system administrator, I want the memory system to automatically persist and reuse expensive indexes across sessions, so search performance remains consistent without manual intervention.

**US3**: As a SOAR orchestrator, I want query embeddings to be cached across all phases of reasoning, so repeated queries like "What is the memory architecture?" don't regenerate embeddings multiple times.

**US4**: As a developer, I want search performance to be predictable and fast enough for interactive use (<3s), so I can confidently use `aur mem search` as my primary code exploration tool.

## 4. Requirements

### 4.1 Functional Requirements

**FR1**: HybridRetriever Instance Caching
- **FR1.1**: Implement module-level LRU cache keyed by `(store.db_path, config_hash)`
- **FR1.2**: Cache size configurable via `AURORA_RETRIEVER_CACHE_SIZE` (default: 10)
- **FR1.3**: Cache TTL configurable via `AURORA_RETRIEVER_CACHE_TTL` (default: 1800s / 30min)
- **FR1.4**: Cache invalidation on config changes (detected via config hash)
- **FR1.5**: Thread-safe cache access for concurrent searches

**FR2**: ActivationEngine Instance Caching
- **FR2.1**: Implement module-level singleton cache keyed by `store.db_path`
- **FR2.2**: Single ActivationEngine instance per database (1:1 mapping)
- **FR2.3**: Thread-safe singleton access pattern
- **FR2.4**: Lazy initialization (create on first use)

**FR3**: BM25 Index Persistence Fix
- **FR3.1**: Verify `_try_load_bm25_index()` is actually loading from disk (add logging)
- **FR3.2**: Validate pickle format compatibility (handle version mismatches gracefully)
- **FR3.3**: Ensure `bm25_index_path` resolution works correctly (relative vs absolute paths)
- **FR3.4**: Add error handling for corrupted index files (rebuild if corrupted)
- **FR3.5**: Log "Loaded BM25 index from X" on successful load vs "Building BM25 index from candidates" on rebuild

**FR4**: Shared QueryEmbeddingCache
- **FR4.1**: Move `QueryEmbeddingCache` from instance-level to module-level
- **FR4.2**: Share cache across all HybridRetriever instances in the process
- **FR4.3**: Thread-safe cache access with proper locking
- **FR4.4**: Maintain existing LRU eviction and TTL behavior
- **FR4.5**: Preserve existing cache statistics and monitoring

### 4.2 Non-Functional Requirements

**NFR1**: Performance
- **NFR1.1**: Cache lookup overhead MUST be <10ms per operation
- **NFR1.2**: Thread safety mechanisms MUST NOT introduce >5ms contention overhead
- **NFR1.3**: Memory overhead for caches MUST be <50MB for typical usage (10 retrievers, 100 cached embeddings)

**NFR2**: Reliability
- **NFR2.1**: Cache failures MUST fallback gracefully to uncached behavior (no search failures due to caching)
- **NFR2.2**: Corrupted BM25 index MUST auto-rebuild without manual intervention
- **NFR2.3**: Thread safety MUST prevent race conditions in concurrent search scenarios

**NFR3**: Observability
- **NFR3.1**: Cache hit/miss rates MUST be logged at DEBUG level
- **NFR3.2**: BM25 index load vs rebuild MUST be logged at INFO level
- **NFR3.3**: Cache statistics MUST be accessible via `HybridRetriever.get_cache_stats()`

**NFR4**: Maintainability
- **NFR4.1**: Caching implementation MUST NOT modify search result semantics (equivalence required)
- **NFR4.2**: Cache configuration MUST be externalized (environment variables or config file)
- **NFR4.3**: Backward compatibility MUST be maintained (no breaking changes to public APIs)

## 5. Non-Goals

- **NG1**: Algorithmic changes to BM25 scoring or tokenization (covered in Epic 2)
- **NG2**: Connection pool optimization for SQLite (covered in Epic 3)
- **NG3**: Content-hash embedding cache for re-indexing (covered in Epic 3)
- **NG4**: Distributed caching across multiple processes (out of scope)
- **NG5**: Cache warming strategies (future enhancement)
- **NG6**: Cache eviction telemetry beyond basic hit/miss stats (future enhancement)

## 6. Constraints

### 6.1 Technical Constraints

**TC1**: Must maintain backward compatibility with existing Aurora codebase
**TC2**: Must work with existing SQLite-based storage layer (no schema changes)
**TC3**: Must support both in-memory (`:memory:`) and file-based databases
**TC4**: Must be thread-safe for concurrent SOAR phases and parallel searches

### 6.2 Project Constraints

**PC1**: Implementation timeline: 1 week (5 working days)
**PC2**: No breaking changes to public APIs (maintain API contracts)
**PC3**: Must pass existing test suite without modifications (search equivalence required)

## 6.5 Current State Analysis

### 6.5.1 Object Creation Flow

**Call Chain (from `aur mem search` to object creation):**

```
aur mem search "query"
  ↓
packages/cli/src/aurora_cli/commands/memory.py:546
  store = SQLiteStore(str(db_path_resolved))
  retriever = MemoryRetriever(store=store, config=config)  ← NEW INSTANCE EVERY SEARCH
  ↓
packages/cli/src/aurora_cli/memory/retrieval.py:71-103
  MemoryRetriever._get_retriever():
    activation_engine = ActivationEngine()  ← NEW INSTANCE EVERY SEARCH (line 92)
    HybridRetriever(store, activation_engine, embedding_provider)  ← NEW INSTANCE EVERY SEARCH (line 97)
  ↓
packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:269-309
  HybridRetriever.__init__():
    self._bm25_index_loaded = False  ← PERSISTENT INDEX NOT LOADED (line 305)
    if enable_bm25_persistence:
      self._try_load_bm25_index()  ← CALLED BUT FAILS SILENTLY (line 309)
```

**Code Evidence:**

1. **MemoryRetriever Created Every Search:**
   - File: `packages/cli/src/aurora_cli/commands/memory.py:546`
   - Code:
     ```python
     store = SQLiteStore(str(db_path_resolved))
     retriever = MemoryRetriever(store=store, config=config)  # ← NEW INSTANCE
     ```
   - Impact: Fresh HybridRetriever + ActivationEngine created every search

2. **HybridRetriever Created Every Call:**
   - File: `packages/cli/src/aurora_cli/memory/retrieval.py:88-101`
   - Code:
     ```python
     if self._retriever is None:
         from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
         from aurora_core.activation.engine import ActivationEngine

         activation_engine = ActivationEngine()  # ← NEW INSTANCE (line 92)
         embedding_provider = self._get_embedding_provider()

         self._retriever = HybridRetriever(  # ← NEW INSTANCE (line 97)
             self._store,
             activation_engine,
             embedding_provider,
         )
     ```
   - Impact: 200-500ms overhead per search (HybridRetriever init + BM25 index rebuild)

3. **ActivationEngine Created Every Call:**
   - File: `packages/cli/src/aurora_cli/memory/retrieval.py:92`
   - Code:
     ```python
     activation_engine = ActivationEngine()  # ← NEW INSTANCE
     ```
   - Impact: 50-100ms overhead per search (database connection + initialization)

### 6.5.2 Root Cause: No Caching Layer

**Problem 1: MemoryRetriever Created Every Search**
- File: `packages/cli/src/aurora_cli/commands/memory.py:546`
- Code:
  ```python
  # CURRENT: Creates new MemoryRetriever every time
  store = SQLiteStore(str(db_path_resolved))
  retriever = MemoryRetriever(store=store, config=config)
  raw_results, is_full_hybrid = retriever.retrieve_fast(query, ...)
  ```
- Impact: Each search creates new HybridRetriever + ActivationEngine, wasting 250-600ms on initialization

**Problem 2: HybridRetriever Created Every Call**
- File: `packages/cli/src/aurora_cli/memory/retrieval.py:88-101`
- Code:
  ```python
  # CURRENT: MemoryRetriever._get_retriever() creates new HybridRetriever
  if self._retriever is None:
      activation_engine = ActivationEngine()
      embedding_provider = self._get_embedding_provider()
      self._retriever = HybridRetriever(
          self._store, activation_engine, embedding_provider
      )
  ```
- Impact: 200-500ms overhead per search (BM25 index rebuild is main culprit)
- Cache key should be: `(db_path, config_hash)` to enable reuse across MemoryRetriever instances

**Problem 3: ActivationEngine Created Every Call**
- File: `packages/cli/src/aurora_cli/memory/retrieval.py:92`
- Code:
  ```python
  # CURRENT: New ActivationEngine created for each HybridRetriever
  activation_engine = ActivationEngine()
  ```
- Impact: 50-100ms overhead per search (database connection establishment)
- Should be singleton per database: one ActivationEngine instance per `db_path`

### 6.5.3 BM25 Index Persistence Analysis

**Investigation Results:**

**Q1: Is `build_and_save_bm25_index` called during indexing?**
- YES - Called at the end of every successful `aur mem index` operation
- File: `packages/cli/src/aurora_cli/memory_manager.py:982`
- Code:
  ```python
  # Build and save BM25 index for faster search (eliminates 51% of search time)
  if stats["chunks"] > 0:
      report_progress(IndexProgress("bm25_index", stats["chunks"], stats["chunks"],
                                   detail="Building BM25 index"))
      self._build_bm25_index()  # ← CALLED (line 982)
  ```
- Delegates to: `memory_manager.py:1812` which calls `retriever.build_and_save_bm25_index()`

**Q2: Is `_try_load_bm25_index` called during search?**
- YES - Called in HybridRetriever constructor
- File: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:308-309`
- Code:
  ```python
  # Try to load persistent BM25 index if configured
  if self.config.enable_bm25_persistence and self.config.bm25_weight > 0:
      self._try_load_bm25_index()  # ← CALLED (line 309)
  ```

**Q3: Does `.aurora/indexes/bm25_index.pkl` exist after indexing?**
- YES - File exists and is current:
  ```bash
  $ ls -lah .aurora/indexes/
  total 2.8M
  -rw-rw-r-- 1 hamr hamr 2.8M Jan 22 11:23 bm25_index.pkl
  ```
- File size: 2.8MB (reasonable for indexed codebase)

**Q4: What does `_get_bm25_index_path()` return?**
- File: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:830-845`
- Code:
  ```python
  def _get_bm25_index_path(self) -> Path | None:
      if self.config.bm25_index_path:
          return Path(self.config.bm25_index_path).expanduser()

      # Default: try to find .aurora directory relative to store's db_path
      if hasattr(self.store, "db_path") and self.store.db_path != ":memory:":
          db_path = Path(self.store.db_path)
          return db_path.parent / "indexes" / "bm25_index.pkl"  # ← CORRECT PATH

      return None
  ```
- Returns: `.aurora/indexes/bm25_index.pkl` (correct path)

**Root Cause Hypothesis: Why is BM25 index NOT being loaded?**

After reviewing the code flow, the root cause is likely one of these:

1. **HybridConfig mismatch**: `config.bm25_index_path` is not being set correctly, causing path resolution to fail
2. **Permissions issue**: File exists but cannot be read (unlikely given file permissions)
3. **Silent failure in pickle load**: `_try_load_bm25_index()` catches all exceptions and returns False without raising
4. **Config not propagated**: `enable_bm25_persistence=True` not being passed to HybridRetriever constructor

**Evidence from hybrid_retriever.py:847-874:**
```python
def _try_load_bm25_index(self) -> bool:
    index_path = self._get_bm25_index_path()
    if index_path is None or not index_path.exists():
        logger.debug(f"No persistent BM25 index found at {index_path}")  # ← DEBUG LEVEL
        return False

    try:
        self.bm25_scorer = BM25Scorer(k1=1.5, b=0.75)
        self.bm25_scorer.load_index(index_path)
        self._bm25_index_loaded = True
        logger.info(f"Loaded BM25 index from {index_path} ...")  # ← INFO LEVEL
        return True
    except Exception as e:
        logger.warning(f"Failed to load BM25 index from {index_path}: {e}")  # ← WARNING
        self.bm25_scorer = None
        self._bm25_index_loaded = False
        return False
```

**Investigation needed**: Check logs for:
- DEBUG: "No persistent BM25 index found" → path resolution issue
- WARNING: "Failed to load BM25 index" → pickle load failure
- Neither message? → `_try_load_bm25_index()` not being called at all

### 6.5.4 Performance Breakdown

**Where the 15-19s is spent (Cold Search):**

| Component | Time (ms) | % of Total | Cacheable? | Epic 1 Fix |
|-----------|-----------|------------|------------|------------|
| HybridRetriever creation | 200-500 | 1-3% | YES | Module-level cache keyed by `(db_path, config_hash)` |
| ActivationEngine creation | 50-100 | <1% | YES | Singleton cache keyed by `db_path` |
| **BM25 index rebuild** | **9,700** | **51%** | **YES** | **Fix `_try_load_bm25_index()` to actually load from disk** |
| Embedding model load (first use) | 2,000-3,000 | 10-15% | Partial | Background loading (already implemented) |
| SQLite query (activation retrieval) | 500-1,000 | 3-5% | NO | Epic 3 (connection pool) |
| Semantic similarity computation | 1,000-2,000 | 5-10% | Partial | Shared QueryEmbeddingCache (Epic 1) |
| Embedding cache miss | 100-200 | <1% | YES | Shared QueryEmbeddingCache (Epic 1) |
| Other overhead | 2,000-3,000 | 10-15% | NO | Various (Epic 2 & 3) |
| **Total Cacheable (Epic 1)** | **10,050-10,500** | **53-55%** | - | **Target: 30-40% speedup** |

**Where the 4-5s is spent (Warm Search, after first search):**

| Component | Time (ms) | % of Total | Cacheable? | Epic 1 Fix |
|-----------|-----------|------------|------------|------------|
| HybridRetriever creation | 200-500 | 4-10% | YES | Module-level cache |
| ActivationEngine creation | 50-100 | 1-2% | YES | Singleton cache |
| BM25 index rebuild | 0 | 0% | N/A | Already cached in current instance |
| Embedding model (cached) | 0 | 0% | N/A | Already loaded |
| SQLite query | 500-1,000 | 10-20% | NO | Epic 3 |
| Semantic similarity | 1,000-2,000 | 20-40% | Partial | Shared cache |
| Embedding cache miss | 100-200 | 2-4% | YES | Shared cache |
| Other overhead | 2,000-3,000 | 40-60% | NO | Various |
| **Total Cacheable (Epic 1)** | **350-800** | **7-16%** | - | **Target: 40-50% speedup** |

**Key Insight for Epic 1:**
- Cold search: 53-55% of time is cacheable (10.0-10.5s out of 15-19s)
- Warm search: Only 7-16% cacheable because BM25 is already cached within the current HybridRetriever instance
- Solution: Module-level caches enable warm-search performance from the FIRST search by reusing instances across invocations

## 7. Technical Approach

### 7.1 HybridRetriever Instance Caching

**Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

**Implementation**:
```python
from functools import lru_cache
import threading
import hashlib

# Module-level cache with thread safety
_retriever_cache: dict[tuple[str, str], HybridRetriever] = {}
_retriever_cache_lock = threading.Lock()

def get_cached_retriever(
    store: Any,
    activation_engine: Any,
    embedding_provider: Any,
    config: HybridConfig,
) -> HybridRetriever:
    """Get or create cached HybridRetriever instance.

    Cache key: (db_path, config_hash)
    - db_path ensures separate caches per database
    - config_hash ensures cache invalidation on config changes
    """
    db_path = getattr(store, "db_path", ":memory:")
    config_hash = hashlib.md5(
        json.dumps(config.model_dump(), sort_keys=True).encode()
    ).hexdigest()

    cache_key = (db_path, config_hash)

    with _retriever_cache_lock:
        if cache_key not in _retriever_cache:
            logger.debug(f"Creating new HybridRetriever for {db_path}")
            _retriever_cache[cache_key] = HybridRetriever(
                store, activation_engine, embedding_provider, config
            )
        else:
            logger.debug(f"Reusing cached HybridRetriever for {db_path}")

        return _retriever_cache[cache_key]
```

### 7.2 ActivationEngine Instance Caching

**Location**: `packages/core/src/aurora_core/activation/engine.py`

**Implementation**:
```python
import threading

# Module-level singleton cache
_engine_cache: dict[str, ActivationEngine] = {}
_engine_cache_lock = threading.Lock()

def get_cached_engine(
    store: Any,
    config: ActivationConfig | None = None,
) -> ActivationEngine:
    """Get or create cached ActivationEngine instance.

    One engine per database (singleton per db_path).
    """
    db_path = getattr(store, "db_path", ":memory:")

    with _engine_cache_lock:
        if db_path not in _engine_cache:
            logger.debug(f"Creating new ActivationEngine for {db_path}")
            _engine_cache[db_path] = ActivationEngine(config)
        else:
            logger.debug(f"Reusing cached ActivationEngine for {db_path}")

        return _engine_cache[db_path]
```

### 7.3 BM25 Index Persistence Validation

**Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (lines 847-874)

**Investigation Steps**:
1. Add logging to `_try_load_bm25_index()` to distinguish load vs rebuild
2. Verify `_get_bm25_index_path()` returns correct absolute path
3. Test pickle load with `try/except` and detailed error logging
4. Add validation that loaded index has expected corpus_size > 0

**Enhanced Logging**:
```python
def _try_load_bm25_index(self) -> bool:
    index_path = self._get_bm25_index_path()
    if index_path is None or not index_path.exists():
        logger.info(f"No persistent BM25 index found at {index_path} - will rebuild on first search")
        return False

    try:
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer

        self.bm25_scorer = BM25Scorer(k1=1.5, b=0.75)
        self.bm25_scorer.load_index(index_path)
        self._bm25_index_loaded = True

        logger.info(
            f"✓ Loaded BM25 index from {index_path} "
            f"({self.bm25_scorer.corpus_size} documents, {index_path.stat().st_size / 1024:.1f}KB)"
        )
        return True
    except Exception as e:
        logger.warning(
            f"✗ Failed to load BM25 index from {index_path} - will rebuild: {type(e).__name__}: {e}"
        )
        self.bm25_scorer = None
        self._bm25_index_loaded = False
        return False
```

### 7.4 Shared QueryEmbeddingCache

**Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (lines 122-230)

**Implementation**:
```python
import threading

# Module-level shared cache (moved from instance-level)
_shared_query_cache: QueryEmbeddingCache | None = None
_query_cache_lock = threading.Lock()

def get_shared_query_cache(
    capacity: int = 100,
    ttl_seconds: int = 1800,
) -> QueryEmbeddingCache:
    """Get module-level shared query embedding cache.

    Shared across all HybridRetriever instances in the process.
    """
    global _shared_query_cache

    with _query_cache_lock:
        if _shared_query_cache is None:
            _shared_query_cache = QueryEmbeddingCache(capacity, ttl_seconds)
            logger.debug(f"Created shared QueryEmbeddingCache (size={capacity}, ttl={ttl_seconds}s)")

        return _shared_query_cache


# In HybridRetriever.__init__():
if self.config.enable_query_cache:
    # Use shared cache instead of instance-level cache
    self._query_cache = get_shared_query_cache(
        capacity=self.config.query_cache_size,
        ttl_seconds=self.config.query_cache_ttl_seconds,
    )
else:
    self._query_cache = None
```

## 8. Testing Strategy

### 8.1 Unit Tests

**UT1**: HybridRetriever Cache
- Create two retrievers with same db_path and config → verify same instance returned
- Create two retrievers with different db_path → verify different instances
- Create two retrievers with different config → verify different instances (cache miss)
- Verify cache hit rate statistics

**UT2**: ActivationEngine Cache
- Create two engines with same db_path → verify same instance returned
- Create two engines with different db_path → verify different instances
- Verify thread safety with concurrent access

**UT3**: BM25 Index Persistence
- Create and save index → verify file exists
- Load index from disk → verify corpus_size matches
- Corrupt index file → verify graceful fallback to rebuild
- Delete index file → verify rebuild on next search

**UT4**: Shared QueryEmbeddingCache
- Cache embedding in retriever A → verify retriever B can access it
- Verify LRU eviction works across multiple retrievers
- Verify TTL expiration works correctly
- Verify thread safety with concurrent cache access

### 8.2 Integration Tests

**IT1**: End-to-End Search Equivalence
- Run search without caching → save results
- Run same search with caching → verify identical results
- Verify scores match exactly (no floating point drift)

**IT2**: Cold vs Warm Search Performance
- First search (cold) → measure time, verify no cache hits
- Second search (warm) → measure time, verify cache hits, verify 40-50% speedup
- Third search → verify cache hits persist

**IT3**: SOAR Multi-Phase Caching
- Simulate SOAR phases 2, 5, 8 with same query
- Verify embedding cache hit on phases 5 and 8
- Verify 100-200ms savings per cache hit

**IT4**: BM25 Index Persistence Across Sessions
- Index 500 chunks → save BM25 index
- Restart process → run search
- Verify "Loaded BM25 index" log message
- Verify search completes in <3s (vs 15s rebuild)

### 8.3 Performance Tests

**PT1**: Cache Lookup Overhead
- Measure cache lookup time (should be <10ms)
- Measure thread contention overhead (should be <5ms)
- Verify memory overhead <50MB for typical usage

**PT2**: Benchmark Before/After
- Run `make benchmark-soar` before changes → baseline
- Run `make benchmark-soar` after changes → verify 30-40% improvement
- Verify warm searches improve 40-50%

**PT3**: Concurrent Search Stress Test
- Run 10 concurrent searches with same query
- Verify thread safety (no crashes, no race conditions)
- Verify cache hit rate >80% (9 of 10 searches hit cache)

## 9. Success Metrics

### 9.1 Primary Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|--------------------|
| Cold search time | 15-19s | 10-12s (30-40% ↓) | `make benchmark-soar` |
| Warm search time | 4-5s | 2-3s (40-50% ↓) | Second search after cold |
| BM25 index load time | 9.7s | <100ms (98% ↓) | Log parsing + timing |

### 9.2 Cache Performance Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|--------------------|
| HybridRetriever cache hit rate | 0% | 60%+ | Cache stats API |
| ActivationEngine cache hit rate | 0% | 80%+ | Cache stats API |
| QueryEmbeddingCache hit rate | 0% | 40%+ | Cache stats API |
| Cache lookup overhead | N/A | <10ms | Performance profiling |

### 9.3 Reliability Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Search result equivalence | 100% (bit-exact) | Integration tests |
| Graceful cache failure handling | 100% (no crashes) | Error injection tests |
| Thread safety (concurrent searches) | 100% (no races) | Stress tests |

## 10. Risk Assessment & Mitigation

### 10.1 Low Risk (Pure Caching)

**Risk**: Cache introduces search result differences
- **Likelihood**: Low (caching doesn't change algorithms)
- **Impact**: High (breaks search accuracy)
- **Mitigation**: Comprehensive equivalence tests (FR4.1), bit-exact score comparison

**Risk**: Thread safety issues with concurrent caching
- **Likelihood**: Medium (threading bugs are subtle)
- **Impact**: High (crashes, race conditions)
- **Mitigation**: Use standard library locks (threading.Lock), stress tests with 10+ concurrent searches

**Risk**: BM25 index corruption causes search failures
- **Likelihood**: Low (pickle is stable)
- **Impact**: Medium (degraded UX, but rebuild works)
- **Mitigation**: Try/except with automatic fallback to rebuild (FR3.4)

### 10.2 Rollback Plan

If cache hit rates are below target OR search equivalence fails:
1. Feature flag to disable caching (`AURORA_DISABLE_CACHING=1`)
2. Revert to baseline behavior (no caches)
3. Debug in isolated environment with verbose logging
4. Re-enable after fixes

## 11. Implementation Tasks

### 11.1 Task Breakdown (5 days)

**Day 1**: HybridRetriever Instance Caching
- [ ] Implement `get_cached_retriever()` with LRU cache
- [ ] Add config hash for cache key
- [ ] Add thread safety (lock)
- [ ] Unit tests for cache behavior
- [ ] Integration test for cache hit rate

**Day 2**: ActivationEngine Instance Caching
- [ ] Implement `get_cached_engine()` singleton cache
- [ ] Add thread safety (lock)
- [ ] Unit tests for singleton behavior
- [ ] Integration test for cache hit rate

**Day 3**: BM25 Index Persistence Validation
- [ ] Add enhanced logging to `_try_load_bm25_index()`
- [ ] Validate pickle format and error handling
- [ ] Test corrupted index fallback
- [ ] Verify absolute path resolution
- [ ] Integration test for index persistence across sessions

**Day 4**: Shared QueryEmbeddingCache
- [ ] Move QueryEmbeddingCache to module-level
- [ ] Implement `get_shared_query_cache()`
- [ ] Update HybridRetriever.__init__ to use shared cache
- [ ] Unit tests for cache sharing
- [ ] Integration test for SOAR multi-phase caching

**Day 5**: Integration, Testing & Validation
- [ ] Run full test suite (unit + integration + performance)
- [ ] Run `make benchmark-soar` before/after comparison
- [ ] Verify 30-40% improvement on cold searches
- [ ] Verify 40-50% improvement on warm searches
- [ ] Document cache configuration (environment variables)
- [ ] Update CLAUDE.md with caching behavior

## 12. Dependencies

**No blocking dependencies** - all tasks are independent and can proceed in parallel:
- HybridRetriever caching: Independent
- ActivationEngine caching: Independent
- BM25 index persistence: Independent
- QueryEmbeddingCache sharing: Independent

**Upstream dependencies for Epic 2 and Epic 3**:
- Epic 2 (BM25 Tokenization) depends on Epic 1 (needs working BM25 index to validate)
- Epic 3 (Connection Pool) depends on Epic 1 (needs stable cache layer)

## 13. Open Questions

**Q1**: Should cache size and TTL be configurable per HybridRetriever instance or globally?
- **Recommendation**: Start with global configuration (environment variables), add per-instance config if needed

**Q2**: Should we persist the QueryEmbeddingCache across process restarts?
- **Recommendation**: No - embeddings are fast to regenerate (100-200ms), persistence adds complexity. Revisit in future if needed.

**Q3**: What should happen if BM25 index path is not writable?
- **Recommendation**: Log warning, continue without persistence (rebuild on each search). Don't fail the search.

**Q4**: Should we add cache warming on startup for common queries?
- **Recommendation**: No - cache warming is out of scope (NG5). Lazy caching is sufficient for interactive use.

**Q5**: How do we handle cache invalidation when database is re-indexed?
- **Recommendation**: `aur mem index` should call `invalidate_bm25_index()` and clear retriever cache. Add this in implementation.

## 14. Validation Plan

### 14.1 Pre-Implementation Validation

- [ ] Review epic breakdown document for accuracy
- [ ] Confirm baseline performance (run `make benchmark-soar` on current main)
- [ ] Review existing HybridRetriever and ActivationEngine code
- [ ] Identify integration points (SOAR phases, CLI commands)

### 14.2 Implementation Validation

- [ ] Daily: Run unit tests for completed tasks
- [ ] Daily: Run integration tests to catch regressions
- [ ] Day 5: Run full performance benchmark suite
- [ ] Day 5: Compare before/after benchmark results

### 14.3 Post-Implementation Validation

- [ ] Run `make quality-check` (lint + type + test)
- [ ] Verify all metrics meet targets (see Section 9)
- [ ] Document cache configuration in CLAUDE.md
- [ ] Create pull request with before/after benchmark comparison

## 15. References

- **Epic Breakdown**: `/home/hamr/PycharmProjects/aurora/tasks/aur-mem-search/EPIC_SPRINT_BREAKDOWN.md`
- **HybridRetriever**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- **ActivationEngine**: `packages/core/src/aurora_core/activation/engine.py`
- **SQLiteStore**: `packages/core/src/aurora_core/store/sqlite.py`
- **Performance Tests**: `tests/performance/test_soar_startup_performance.py`
- **SOAR Architecture**: `docs/reference/SOAR_ARCHITECTURE.md`

---

**Next Steps**:
1. Review PRD with stakeholder
2. Proceed to task generation (`2-generate-tasks`)
3. Begin implementation (estimated 1 week / 5 days)
