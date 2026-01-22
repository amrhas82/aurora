# Tasks: Epic 1 - Foundation Caching (PRD 0031)

**PRD:** `/home/hamr/PycharmProjects/aurora/tasks/aur-mem-search/0031-prd-epic1-foundation-caching.md`
**Status:** Ready for Implementation
**Timeline:** 5 days (1 week)
**Created:** 2026-01-22

---

## Relevant Files

### Core Implementation Files
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - HybridRetriever class, QueryEmbeddingCache (lines 122-230), _try_load_bm25_index (lines 847-874), _get_bm25_index_path (lines 830-845)
- `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/activation/engine.py` - ActivationEngine class initialization
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/memory/retrieval.py` - MemoryRetriever._get_retriever() (lines 88-101)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/memory.py` - Search command entry point (line 546)
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py` - BM25Scorer.load_index() and save_index()

### Test Files
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_cache.py` - New file for HybridRetriever cache tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/core/activation/test_engine_cache.py` - New file for ActivationEngine cache tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_bm25_persistence.py` - New file for BM25 persistence tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_query_cache_sharing.py` - New file for shared QueryEmbeddingCache tests
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_memory_search_caching.py` - New file for end-to-end cache integration tests
- `/home/hamr/PycharmProjects/aurora/tests/performance/test_cache_performance.py` - New file for cache overhead measurement

### Configuration Files
- `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/config/defaults.json` - Add cache configuration defaults

### Documentation
- `/home/hamr/PycharmProjects/aurora/CLAUDE.md` - Update with caching behavior (Memory System section)

---

## Notes

### Testing Framework
- **Framework**: Aurora uses pytest with markers (@pytest.mark.unit, @pytest.mark.integration, @pytest.mark.performance)
- **TDD Approach**: Write test first for each feature, watch it fail, then implement minimal code to pass
- **Verification**: Run `pytest <file>::<test_name> -v` for individual tests; `make test-unit` for full unit suite

### Performance Targets
- **Cold Search**: 15-19s → 10-12s (30-40% improvement via BM25 index load)
- **Warm Search**: 4-5s → 2-3s (40-50% improvement via instance caching)
- **Cache Overhead**: <10ms per lookup
- **Memory Overhead**: <50MB for typical usage

### Implementation Patterns
- **Thread Safety**: Use `threading.Lock()` for all module-level caches
- **Cache Keys**: Use tuples for composite keys (e.g., `(db_path, config_hash)`)
- **Logging**: INFO level for cache hits/misses; DEBUG for internal details
- **Graceful Degradation**: All cache failures must fallback to uncached behavior (no search failures)
- **Config Hash**: Use `hashlib.md5(json.dumps(config.model_dump(), sort_keys=True).encode()).hexdigest()`

### Critical Constraints
- **Backward Compatibility**: No breaking changes to public APIs
- **Search Equivalence**: Cached searches must return identical results (bit-exact scores)
- **Thread Safety**: Must support concurrent SOAR phases and parallel searches
- **No Schema Changes**: Work with existing SQLite storage layer

### Performance Baseline Measurement
Before implementation, run baseline benchmarks:
```bash
make benchmark-soar > /tmp/baseline-epic1-cold.txt
# Run second search immediately for warm baseline
aur mem search "test query" --limit 10
```

---

## Tasks

- [x] 0.0 Setup and Baseline Measurement
  - [x] 0.1 Create feature branch `feature/epic1-foundation-caching`
    - tdd: no
    - verify: `git branch --show-current`
    - **Details**: Branch from main, ensure clean working directory
  - [x] 0.2 Measure baseline performance (cold search)
    - tdd: no
    - verify: Save output to `/tmp/baseline-epic1-cold.txt`
    - **Details**: Run `make benchmark-soar`, capture timing for "aur mem search" operations
    - **PRD Ref**: Section 9 Success Metrics, baseline 15-19s cold search
  - [x] 0.3 Measure baseline performance (warm search)
    - tdd: no
    - verify: Save output to `/tmp/baseline-epic1-warm.txt`
    - **Details**: Run `aur mem search "test query" --limit 10` twice consecutively, measure second run
    - **PRD Ref**: Section 9 Success Metrics, baseline 4-5s warm search
  - [x] 0.4 Create test directories
    - tdd: no
    - verify: `ls -d tests/unit/context_code/semantic tests/unit/core/activation tests/integration tests/performance`
    - **Details**: Ensure test directory structure exists for new test files

- [ ] 1.0 HybridRetriever Instance Caching (~200 LOC)
  - [ ] 1.1 Write test: test_retriever_cache_same_db_config
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_same_db_config -v`
    - **Details**: Create two HybridRetriever instances with same db_path and config, verify same object returned (use `id()` to check identity)
    - **PRD Ref**: FR1.1, Section 8.1 UT1
  - [ ] 1.2 Write test: test_retriever_cache_different_db
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_different_db -v`
    - **Details**: Create two retrievers with different db_path, verify different instances returned
    - **PRD Ref**: FR1.1, Section 8.1 UT1
  - [ ] 1.3 Write test: test_retriever_cache_different_config
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_different_config -v`
    - **Details**: Create two retrievers with same db_path but different config (e.g., bm25_weight=0.4 vs 0.6), verify different instances (cache miss)
    - **PRD Ref**: FR1.4, Section 8.1 UT1
  - [ ] 1.4 Write test: test_retriever_cache_hit_rate_stats
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_hit_rate_stats -v`
    - **Details**: Create retriever 3 times with same params, verify cache hit rate is 66% (2 hits, 1 miss), test get_cache_stats() API
    - **PRD Ref**: FR1.5, NFR3.1, Section 8.1 UT1
  - [ ] 1.5 Write test: test_retriever_cache_thread_safety
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_thread_safety -v`
    - **Details**: Launch 5 threads creating retriever concurrently, verify all get same instance and no race conditions
    - **PRD Ref**: FR1.5, NFR2.3, Section 8.1 UT1
  - [ ] 1.6 Implement get_cached_retriever() function
    - tdd: yes (tests written above)
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py -v`
    - **Details**: Add module-level cache dict, lock, get_cached_retriever(store, activation_engine, embedding_provider, config) returns cached or new instance
    - **PRD Ref**: FR1.1-FR1.5, Section 7.1
    - **Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (add before HybridRetriever class definition, around line 250)
  - [ ] 1.7 Add config hash computation
    - tdd: yes (covered by test_retriever_cache_different_config)
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_different_config -v`
    - **Details**: Use `hashlib.md5(json.dumps(config.model_dump(), sort_keys=True).encode()).hexdigest()` for cache key
    - **PRD Ref**: FR1.4, Section 7.1
    - **Location**: Inside get_cached_retriever() function
  - [ ] 1.8 Add thread-safe cache access with lock
    - tdd: yes (covered by test_retriever_cache_thread_safety)
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_thread_safety -v`
    - **Details**: Wrap cache lookup/insert in `with _retriever_cache_lock:` block
    - **PRD Ref**: FR1.5, NFR2.3, Section 7.1
    - **Location**: Inside get_cached_retriever() function
  - [ ] 1.9 Add cache statistics API
    - tdd: yes (covered by test_retriever_cache_hit_rate_stats)
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py::test_retriever_cache_hit_rate_stats -v`
    - **Details**: Track hits/misses, add get_cache_stats() function returning dict with hit_rate, total_hits, total_misses, cache_size
    - **PRD Ref**: NFR3.3, Section 7.1
    - **Location**: Add module-level stats tracking in hybrid_retriever.py
  - [ ] 1.10 Add DEBUG logging for cache hits/misses
    - tdd: no (manual verification via log inspection)
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py -v -s | grep "Reusing cached HybridRetriever"`
    - **Details**: Log "Creating new HybridRetriever for {db_path}" on miss, "Reusing cached HybridRetriever for {db_path}" on hit
    - **PRD Ref**: NFR3.1, Section 7.1
    - **Location**: Inside get_cached_retriever() function
  - [ ] 1.11 Update MemoryRetriever to use get_cached_retriever()
    - tdd: yes (integration test in Task 5.1)
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_end_to_end_cache_hit -v`
    - **Details**: Replace `HybridRetriever(...)` call in _get_retriever() with `get_cached_retriever(...)`
    - **PRD Ref**: FR1.1-FR1.5, Section 6.5.2
    - **Location**: `packages/cli/src/aurora_cli/memory/retrieval.py` line 97
  - [ ] 1.12 Add environment variable for cache size
    - tdd: no (configuration only)
    - verify: `AURORA_RETRIEVER_CACHE_SIZE=5 python -c "from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever; print('OK')"`
    - **Details**: Read `AURORA_RETRIEVER_CACHE_SIZE` env var (default 10), implement LRU eviction when cache exceeds size
    - **PRD Ref**: FR1.2, Section 7.1
    - **Location**: Add at module level in hybrid_retriever.py
  - [ ] 1.13 Add environment variable for cache TTL
    - tdd: no (configuration only)
    - verify: `AURORA_RETRIEVER_CACHE_TTL=600 python -c "from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever; print('OK')"`
    - **Details**: Read `AURORA_RETRIEVER_CACHE_TTL` env var (default 1800s), track creation timestamp, evict stale entries
    - **PRD Ref**: FR1.3, Section 7.1
    - **Location**: Add at module level in hybrid_retriever.py
  - [ ] 1.14 Verify: All HybridRetriever cache unit tests pass
    - tdd: no
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_cache.py -v`
    - **Details**: All 5 unit tests (same_db_config, different_db, different_config, hit_rate_stats, thread_safety) must pass

- [ ] 2.0 ActivationEngine Instance Caching (~120 LOC)
  - [ ] 2.1 Write test: test_engine_cache_same_db
    - tdd: yes
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py::test_engine_cache_same_db -v`
    - **Details**: Create two ActivationEngine instances with same db_path, verify same object returned (singleton pattern)
    - **PRD Ref**: FR2.1, Section 8.1 UT2
  - [ ] 2.2 Write test: test_engine_cache_different_db
    - tdd: yes
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py::test_engine_cache_different_db -v`
    - **Details**: Create two engines with different db_path, verify different instances returned
    - **PRD Ref**: FR2.1, Section 8.1 UT2
  - [ ] 2.3 Write test: test_engine_cache_memory_db
    - tdd: yes
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py::test_engine_cache_memory_db -v`
    - **Details**: Create engine with `:memory:` db_path, verify it caches correctly (singleton per `:memory:`)
    - **PRD Ref**: FR2.1, Section 6.1 TC3
  - [ ] 2.4 Write test: test_engine_cache_thread_safety
    - tdd: yes
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py::test_engine_cache_thread_safety -v`
    - **Details**: Launch 5 threads creating engine concurrently, verify all get same instance and no race conditions
    - **PRD Ref**: FR2.3, NFR2.3, Section 8.1 UT2
  - [ ] 2.5 Write test: test_engine_cache_lazy_initialization
    - tdd: yes
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py::test_engine_cache_lazy_initialization -v`
    - **Details**: Verify engine is not created until first access (lazy init pattern)
    - **PRD Ref**: FR2.4, Section 8.1 UT2
  - [ ] 2.6 Implement get_cached_engine() function
    - tdd: yes (tests written above)
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py -v`
    - **Details**: Add module-level cache dict keyed by db_path, lock, get_cached_engine(store, config=None) returns singleton per db_path
    - **PRD Ref**: FR2.1-FR2.4, Section 7.2
    - **Location**: `packages/core/src/aurora_core/activation/engine.py` (add at module level, before ActivationEngine class)
  - [ ] 2.7 Add thread-safe singleton access
    - tdd: yes (covered by test_engine_cache_thread_safety)
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py::test_engine_cache_thread_safety -v`
    - **Details**: Wrap cache lookup/creation in `with _engine_cache_lock:` block
    - **PRD Ref**: FR2.3, NFR2.3, Section 7.2
    - **Location**: Inside get_cached_engine() function
  - [ ] 2.8 Add DEBUG logging for cache hits/misses
    - tdd: no (manual verification via log inspection)
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py -v -s | grep "Reusing cached ActivationEngine"`
    - **Details**: Log "Creating new ActivationEngine for {db_path}" on miss, "Reusing cached ActivationEngine for {db_path}" on hit
    - **PRD Ref**: NFR3.1, Section 7.2
    - **Location**: Inside get_cached_engine() function
  - [ ] 2.9 Update MemoryRetriever to use get_cached_engine()
    - tdd: yes (integration test in Task 5.1)
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_end_to_end_cache_hit -v`
    - **Details**: Replace `ActivationEngine()` call in _get_retriever() with `get_cached_engine(self._store)`
    - **PRD Ref**: FR2.1-FR2.4, Section 6.5.2
    - **Location**: `packages/cli/src/aurora_cli/memory/retrieval.py` line 92
  - [ ] 2.10 Verify: All ActivationEngine cache unit tests pass
    - tdd: no
    - verify: `pytest tests/unit/core/activation/test_engine_cache.py -v`
    - **Details**: All 5 unit tests (same_db, different_db, memory_db, thread_safety, lazy_initialization) must pass

- [ ] 3.0 BM25 Index Persistence Validation (~80 LOC)
  - [ ] 3.1 Write test: test_bm25_index_saves_on_build
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_index_saves_on_build -v`
    - **Details**: Build index with 100 chunks, verify `.aurora/indexes/bm25_index.pkl` file exists and has size >0
    - **PRD Ref**: FR3.1-FR3.2, Section 8.1 UT3
  - [ ] 3.2 Write test: test_bm25_index_loads_from_disk
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_index_loads_from_disk -v`
    - **Details**: Save index with 100 docs, create new HybridRetriever, verify _bm25_index_loaded=True and corpus_size=100
    - **PRD Ref**: FR3.1-FR3.2, Section 8.1 UT3
  - [ ] 3.3 Write test: test_bm25_index_corrupted_fallback
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_index_corrupted_fallback -v`
    - **Details**: Write garbage bytes to index file, create retriever, verify WARNING logged and index rebuilds (no crash)
    - **PRD Ref**: FR3.4, NFR2.2, Section 8.1 UT3
  - [ ] 3.4 Write test: test_bm25_index_missing_rebuilds
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_index_missing_rebuilds -v`
    - **Details**: Delete index file, create retriever, verify INFO logged "No persistent BM25 index found" and index rebuilds on first search
    - **PRD Ref**: FR3.1, Section 8.1 UT3
  - [ ] 3.5 Write test: test_bm25_path_resolution_absolute_vs_relative
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_path_resolution_absolute_vs_relative -v`
    - **Details**: Test _get_bm25_index_path() returns correct path for both relative and absolute db_path
    - **PRD Ref**: FR3.3, Section 6.5.3
  - [ ] 3.6 Enhance _try_load_bm25_index() logging
    - tdd: yes (covered by tests above)
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py -v -s | grep "Loaded BM25 index"`
    - **Details**: Change DEBUG to INFO for "No persistent BM25 index found", add ✓/✗ symbols, log corpus_size and file size on success
    - **PRD Ref**: FR3.5, NFR3.2, Section 7.3
    - **Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` lines 847-874
  - [ ] 3.7 Add validation for loaded index corpus_size
    - tdd: yes (covered by test_bm25_index_loads_from_disk)
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_index_loads_from_disk -v`
    - **Details**: After load_index(), verify self.bm25_scorer.corpus_size > 0, log corpus_size in success message
    - **PRD Ref**: FR3.2, Section 7.3
    - **Location**: Inside _try_load_bm25_index() after load_index() call
  - [ ] 3.8 Improve error handling for pickle format mismatches
    - tdd: yes (covered by test_bm25_index_corrupted_fallback)
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py::test_bm25_index_corrupted_fallback -v`
    - **Details**: Catch specific pickle exceptions (UnpicklingError, ModuleNotFoundError), log type(e).__name__ in WARNING message
    - **PRD Ref**: FR3.2, FR3.4, Section 7.3
    - **Location**: Inside _try_load_bm25_index() except block
  - [ ] 3.9 Verify: All BM25 persistence unit tests pass
    - tdd: no
    - verify: `pytest tests/unit/context_code/semantic/test_bm25_persistence.py -v`
    - **Details**: All 5 unit tests (saves_on_build, loads_from_disk, corrupted_fallback, missing_rebuilds, path_resolution) must pass

- [ ] 4.0 Shared QueryEmbeddingCache (~100 LOC)
  - [ ] 4.1 Write test: test_query_cache_shared_across_retrievers
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_shared_across_retrievers -v`
    - **Details**: Cache embedding in retriever A with query "test", create retriever B, verify retriever B hits cache for same query (check cache stats)
    - **PRD Ref**: FR4.1-FR4.2, Section 8.1 UT4
  - [ ] 4.2 Write test: test_query_cache_lru_eviction
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_lru_eviction -v`
    - **Details**: Create cache with capacity=3, add 4 queries, verify oldest evicted (LRU works across retrievers)
    - **PRD Ref**: FR4.4, Section 8.1 UT4
  - [ ] 4.3 Write test: test_query_cache_ttl_expiration
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_ttl_expiration -v`
    - **Details**: Create cache with ttl=1s, add query, sleep 2s, verify cache miss on next access (TTL works)
    - **PRD Ref**: FR4.4, Section 8.1 UT4
  - [ ] 4.4 Write test: test_query_cache_thread_safety
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_thread_safety -v`
    - **Details**: Launch 5 threads accessing shared cache concurrently, verify no race conditions
    - **PRD Ref**: FR4.3, NFR2.3, Section 8.1 UT4
  - [ ] 4.5 Write test: test_query_cache_stats_aggregation
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_stats_aggregation -v`
    - **Details**: Verify cache stats aggregate across all retrievers (2 retrievers with 1 miss + 1 hit each = 50% hit rate)
    - **PRD Ref**: FR4.5, NFR3.3, Section 8.1 UT4
  - [ ] 4.6 Implement get_shared_query_cache() function
    - tdd: yes (tests written above)
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py -v`
    - **Details**: Add module-level _shared_query_cache variable, lock, get_shared_query_cache(capacity, ttl) returns singleton
    - **PRD Ref**: FR4.1-FR4.5, Section 7.4
    - **Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (add at module level, before QueryEmbeddingCache class around line 120)
  - [ ] 4.7 Add thread-safe cache access
    - tdd: yes (covered by test_query_cache_thread_safety)
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_thread_safety -v`
    - **Details**: Wrap cache creation in `with _query_cache_lock:` block, ensure QueryEmbeddingCache methods are thread-safe
    - **PRD Ref**: FR4.3, NFR2.3, Section 7.4
    - **Location**: Inside get_shared_query_cache() function
  - [ ] 4.8 Update HybridRetriever.__init__ to use shared cache
    - tdd: yes (covered by test_query_cache_shared_across_retrievers)
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_shared_across_retrievers -v`
    - **Details**: Replace instance-level QueryEmbeddingCache creation with call to get_shared_query_cache()
    - **PRD Ref**: FR4.1-FR4.2, Section 7.4
    - **Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` in __init__ (around lines 290-300)
  - [ ] 4.9 Preserve existing cache statistics API
    - tdd: yes (covered by test_query_cache_stats_aggregation)
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py::test_query_cache_stats_aggregation -v`
    - **Details**: Ensure HybridRetriever.get_cache_stats() continues to work, now returns shared cache stats
    - **PRD Ref**: FR4.5, NFR3.3, Section 7.4
    - **Location**: Verify existing get_cache_stats() method in HybridRetriever
  - [ ] 4.10 Verify: All shared QueryEmbeddingCache unit tests pass
    - tdd: no
    - verify: `pytest tests/unit/context_code/semantic/test_query_cache_sharing.py -v`
    - **Details**: All 5 unit tests (shared_across_retrievers, lru_eviction, ttl_expiration, thread_safety, stats_aggregation) must pass

- [ ] 5.0 Integration Testing (~150 LOC)
  - [ ] 5.1 Write test: test_end_to_end_cache_hit
    - tdd: yes
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_end_to_end_cache_hit -v`
    - **Details**: Run search twice with same query, verify second search reuses cached HybridRetriever and ActivationEngine (check cache stats)
    - **PRD Ref**: Section 8.2 IT1, IT2
  - [ ] 5.2 Write test: test_search_result_equivalence
    - tdd: yes
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_search_result_equivalence -v`
    - **Details**: Run search without cache (clear cache), save results; run with cache, verify results identical (chunk_ids, scores match exactly)
    - **PRD Ref**: NFR4.1, Section 8.2 IT1
  - [ ] 5.3 Write test: test_bm25_persistence_across_sessions
    - tdd: yes
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_bm25_persistence_across_sessions -v`
    - **Details**: Index 500 chunks, save BM25 index, restart process (clear Python cache), run search, verify "✓ Loaded BM25 index" in logs and search <3s
    - **PRD Ref**: FR3.1-FR3.5, Section 8.2 IT4
  - [ ] 5.4 Write test: test_soar_multi_phase_embedding_cache
    - tdd: yes
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_soar_multi_phase_embedding_cache -v`
    - **Details**: Simulate SOAR phases 2, 5, 8 with same query, verify embedding cache hit on phases 5 and 8 (2/3 hit rate)
    - **PRD Ref**: FR4.1-FR4.2, Section 8.2 IT3
  - [ ] 5.5 Write test: test_concurrent_searches_thread_safety
    - tdd: yes
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_concurrent_searches_thread_safety -v`
    - **Details**: Launch 10 concurrent searches with same query, verify no crashes, cache hit rate >80% (9/10 cache hits)
    - **PRD Ref**: NFR2.3, Section 8.3 PT3
  - [ ] 5.6 Write test: test_cache_failure_graceful_degradation
    - tdd: yes
    - verify: `pytest tests/integration/test_memory_search_caching.py::test_cache_failure_graceful_degradation -v`
    - **Details**: Inject cache error (mock lock failure), verify search continues with uncached behavior (no crash)
    - **PRD Ref**: NFR2.1, Section 8.2
  - [ ] 5.7 Verify: All integration tests pass
    - tdd: no
    - verify: `pytest tests/integration/test_memory_search_caching.py -v`
    - **Details**: All 6 integration tests (end_to_end_cache_hit, search_result_equivalence, bm25_persistence, soar_multi_phase, concurrent_searches, cache_failure) must pass

- [ ] 6.0 Performance Testing and Validation (~100 LOC)
  - [ ] 6.1 Write test: test_cache_lookup_overhead
    - tdd: yes
    - verify: `pytest tests/performance/test_cache_performance.py::test_cache_lookup_overhead -v`
    - **Details**: Measure cache lookup time (avg over 100 iterations), verify <10ms per lookup
    - **PRD Ref**: NFR1.1, Section 8.3 PT1
  - [ ] 6.2 Write test: test_thread_contention_overhead
    - tdd: yes
    - verify: `pytest tests/performance/test_cache_performance.py::test_thread_contention_overhead -v`
    - **Details**: Measure lock contention with 5 concurrent threads, verify <5ms overhead vs single-threaded
    - **PRD Ref**: NFR1.2, Section 8.3 PT1
  - [ ] 6.3 Write test: test_cache_memory_overhead
    - tdd: yes
    - verify: `pytest tests/performance/test_cache_performance.py::test_cache_memory_overhead -v`
    - **Details**: Create 10 retrievers + 100 cached embeddings, measure memory usage via tracemalloc, verify <50MB
    - **PRD Ref**: NFR1.3, Section 8.3 PT1
  - [ ] 6.4 Run benchmark: Cold search performance
    - tdd: no
    - verify: Save output to `/tmp/epic1-cold-after.txt`, compare to baseline
    - **Details**: Run `make benchmark-soar`, verify cold search time improved from 15-19s to 10-12s (30-40% improvement)
    - **PRD Ref**: G1, Section 9.1
  - [ ] 6.5 Run benchmark: Warm search performance
    - tdd: no
    - verify: Save output to `/tmp/epic1-warm-after.txt`, compare to baseline
    - **Details**: Run `aur mem search "test query" --limit 10` twice, verify second run improved from 4-5s to 2-3s (40-50% improvement)
    - **PRD Ref**: G2, Section 9.1
  - [ ] 6.6 Verify: HybridRetriever cache hit rate ≥60%
    - tdd: no
    - verify: Parse cache stats from logs or API, verify ≥60% hit rate in typical usage
    - **Details**: Run 10 searches with 4 unique queries, verify 6/10 cache hits (60%)
    - **PRD Ref**: G3, Section 9.2
  - [ ] 6.7 Verify: ActivationEngine cache hit rate ≥80%
    - tdd: no
    - verify: Parse cache stats from logs or API, verify ≥80% hit rate in typical usage
    - **Details**: Run 10 searches with same db_path, verify 9/10 cache hits (90% > 80% target)
    - **PRD Ref**: G4, Section 9.2
  - [ ] 6.8 Verify: BM25 index load time <100ms
    - tdd: no
    - verify: Parse logs for "Loaded BM25 index" timing, verify <100ms (98% improvement from 9.7s)
    - **Details**: Measure time between HybridRetriever init and first search, verify BM25 load <100ms
    - **PRD Ref**: G5, Section 9.1
  - [ ] 6.9 Verify: All performance tests pass
    - tdd: no
    - verify: `pytest tests/performance/test_cache_performance.py -v`
    - **Details**: All 3 performance tests (cache_lookup_overhead, thread_contention_overhead, cache_memory_overhead) must pass

- [ ] 7.0 Configuration and Documentation (~50 LOC)
  - [ ] 7.1 Add cache configuration to defaults.json
    - tdd: no (configuration only)
    - verify: `cat packages/core/src/aurora_core/config/defaults.json | grep -A 10 "caching"`
    - **Details**: Add section with retriever_cache_size=10, retriever_cache_ttl=1800, enable_bm25_persistence=true
    - **PRD Ref**: FR1.2, FR1.3, NFR4.2
    - **Location**: `packages/core/src/aurora_core/config/defaults.json`
  - [ ] 7.2 Document cache environment variables in CLAUDE.md
    - tdd: no (documentation only)
    - verify: `cat CLAUDE.md | grep "AURORA_RETRIEVER_CACHE"`
    - **Details**: Add to "Memory System (ACT-R)" section: AURORA_RETRIEVER_CACHE_SIZE, AURORA_RETRIEVER_CACHE_TTL, AURORA_DISABLE_CACHING
    - **PRD Ref**: NFR4.2, Section 11.1
    - **Location**: `/home/hamr/PycharmProjects/aurora/CLAUDE.md` (Memory System section)
  - [ ] 7.3 Document caching behavior in CLAUDE.md
    - tdd: no (documentation only)
    - verify: `cat CLAUDE.md | grep "Module-level caches"`
    - **Details**: Add section explaining HybridRetriever cache (keyed by db_path+config), ActivationEngine singleton (keyed by db_path), shared QueryEmbeddingCache
    - **PRD Ref**: Section 11.1, NFR4.2
    - **Location**: `/home/hamr/PycharmProjects/aurora/CLAUDE.md` (Memory System section)
  - [ ] 7.4 Add cache invalidation documentation
    - tdd: no (documentation only)
    - verify: `cat CLAUDE.md | grep "cache invalidation"`
    - **Details**: Document that `aur mem index` should invalidate caches, config changes trigger new cache entries
    - **PRD Ref**: Section 13 Q5, NFR4.2
    - **Location**: `/home/hamr/PycharmProjects/aurora/CLAUDE.md` (Memory System section)

- [ ] 8.0 Final Validation and Cleanup
  - [ ] 8.1 Run full test suite
    - tdd: no
    - verify: `make test-unit && make test-integration`
    - **Details**: Verify all unit and integration tests pass (existing + new tests)
    - **PRD Ref**: Section 14.2
  - [ ] 8.2 Run code quality checks
    - tdd: no
    - verify: `make quality-check`
    - **Details**: Run lint, type-check, ensure no regressions
    - **PRD Ref**: Section 14.3
  - [ ] 8.3 Compare before/after benchmarks
    - tdd: no
    - verify: `diff /tmp/baseline-epic1-cold.txt /tmp/epic1-cold-after.txt`
    - **Details**: Generate comparison report showing 30-40% cold search improvement, 40-50% warm search improvement
    - **PRD Ref**: Section 9.1, Section 14.3
  - [ ] 8.4 Verify all success metrics met
    - tdd: no
    - verify: Review checklist in Section 9 of PRD
    - **Details**: Cold search 10-12s (✓), warm search 2-3s (✓), HybridRetriever cache hit ≥60% (✓), ActivationEngine cache hit ≥80% (✓), BM25 load <100ms (✓)
    - **PRD Ref**: Section 9 Success Metrics
  - [ ] 8.5 Verify backward compatibility
    - tdd: no
    - verify: Run existing test suite without modifications, verify no failures
    - **Details**: Ensure no breaking changes to public APIs, search results identical (equivalence tests pass)
    - **PRD Ref**: Section 6.1 PC2, Section 6.1 PC3
  - [ ] 8.6 Create performance comparison report
    - tdd: no
    - verify: Save report to `/home/hamr/PycharmProjects/aurora/tasks/aur-mem-search/EPIC1_PERFORMANCE_REPORT.md`
    - **Details**: Document baseline vs after for cold/warm searches, cache hit rates, memory overhead
    - **PRD Ref**: Section 14.3

---

## Self-Verification Checklist

### Coverage Check
- [ ] All PRD requirements (FR1-FR4) have corresponding tasks
- [ ] All parent tasks end with Verify subtask
- [ ] Filename matches PRD: `tasks-0031-epic1-foundation-caching.md` ✓

### Bloat/Redundancy Check
- [ ] No duplicate tasks covering same functionality
- [ ] No over-granular tasks (all tasks are appropriately scoped)
- [ ] No vague tasks (each has clear, specific action)
- [ ] No tasks outside PRD scope

### TDD Check
- [ ] Every implementation task has corresponding test task(s) written FIRST
- [ ] All tests have clear verification commands
- [ ] TDD markers correctly identify which tasks require tests

---

## Summary

**Total Tasks**: 8 parent tasks, 70+ subtasks
**Estimated Timeline**: 5 days (1 week) as per PRD
**Key Deliverables**:
- HybridRetriever instance caching (module-level, config-hashed)
- ActivationEngine singleton caching (per db_path)
- BM25 index persistence validation (enhanced logging, error handling)
- Shared QueryEmbeddingCache (cross-retriever sharing)
- 30-40% cold search improvement (15-19s → 10-12s)
- 40-50% warm search improvement (4-5s → 2-3s)

**Risk Level**: Low (pure caching, no algorithmic changes)
**Success Criteria**: All metrics in Section 9 of PRD met, backward compatibility maintained
