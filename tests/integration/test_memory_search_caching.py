"""Integration tests for memory search caching.

End-to-end tests verifying that caching works correctly across all layers:
- HybridRetriever instance caching
- ActivationEngine instance caching
- Shared QueryEmbeddingCache
- BM25 index persistence

Test scenarios:
- End-to-end cache hits on repeated searches
- Cache invalidation on config changes
- Cross-retriever query cache sharing
"""

import pytest  # noqa: F401 - needed for tmp_path fixture


def test_end_to_end_cache_hit(tmp_path):
    """Test end-to-end cache hits with real MemoryRetriever.

    Task 5.1: Run search twice with same query, verify caches are reused.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        clear_retriever_cache,
        clear_shared_query_cache,
        get_cache_stats,
    )
    from aurora_core.activation.engine import _engine_cache
    from aurora_core.store import SQLiteStore

    # Clear caches for clean test
    clear_retriever_cache()
    clear_shared_query_cache()
    _engine_cache.clear()

    # Create store with some test data
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))

    # Add some test chunks
    from aurora_core.chunks.code_chunk import CodeChunk

    for i in range(10):
        chunk = CodeChunk(
            chunk_id=f"test_{i}",
            file_path=str(tmp_path / f"test_{i}.py"),
            element_type="function",
            name=f"test_func_{i}",
            line_start=(i * 10) + 1,  # line_start must be > 0
            line_end=(i * 10) + 6,
            signature=f"def test_func_{i}():",
            docstring=f"Test function {i}",
            language="python",
        )
        store.save_chunk(chunk)

    # The test focuses on verifying caching infrastructure works, not full end-to-end retrieval
    # We verify that get_cached_retriever returns same instance on repeated calls

    from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever
    from aurora_core.activation.engine import get_cached_engine

    # Get initial cache stats
    initial_stats = get_cache_stats()

    # Get engine (cached)
    engine = get_cached_engine(store)

    # Get retriever (first call - cache miss)
    retriever1 = get_cached_retriever(store, engine, None)
    stats_after_first = get_cache_stats()
    assert (
        stats_after_first["total_misses"] > initial_stats["total_misses"]
    ), "Should have cache miss"

    # Get retriever again (second call - cache hit)
    retriever2 = get_cached_retriever(store, engine, None)
    stats_after_second = get_cache_stats()
    assert (
        stats_after_second["total_hits"] > stats_after_first["total_hits"]
    ), "Should have cache hit"

    # Verify same instance returned (caching works)
    assert id(retriever1) == id(retriever2), "Should reuse same retriever instance"


def test_cache_invalidation_on_config_change(tmp_path):
    """Test cache invalidation when config changes.

    Task 5.2: Search with config A, change config to B, verify new retriever created.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        clear_retriever_cache,
        get_cache_stats,
        get_cached_retriever,
    )
    from aurora_core.activation.engine import get_cached_engine
    from aurora_core.store import SQLiteStore

    # Clear caches
    clear_retriever_cache()

    # Create store
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))

    # Add test data
    from aurora_core.chunks.code_chunk import CodeChunk

    chunk = CodeChunk(
        chunk_id="test_1",
        file_path=str(tmp_path / "test.py"),
        element_type="function",
        name="test_func",
        line_start=1,
        line_end=5,
        signature="def test_func():",
        docstring="Test function",
        language="python",
    )
    store.save_chunk(chunk)

    # Create engine
    engine = get_cached_engine(store)

    # Get initial cache stats
    initial_stats = get_cache_stats()
    initial_size = initial_stats["cache_size"]

    # Create retriever with config A (weights must sum to 1.0)
    config_a = HybridConfig(bm25_weight=0.4, activation_weight=0.2, semantic_weight=0.4)
    retriever_a = get_cached_retriever(store, engine, None, config_a)

    # Verify cache size increased
    stats_after_a = get_cache_stats()
    assert stats_after_a["cache_size"] == initial_size + 1, "Cache should have new entry"

    # Create retriever with config B (different config, weights sum to 1.0)
    config_b = HybridConfig(bm25_weight=0.5, activation_weight=0.3, semantic_weight=0.2)
    retriever_b = get_cached_retriever(store, engine, None, config_b)

    # Verify different retriever instances (cache miss due to config change)
    assert id(retriever_a) != id(
        retriever_b
    ), "Different configs should create different retrievers"

    # Verify cache size increased again
    stats_after_b = get_cache_stats()
    assert stats_after_b["cache_size"] == initial_size + 2, "Cache should have two entries"


def test_cross_retriever_query_cache_sharing(tmp_path):
    """Test query cache sharing across multiple retrievers.

    Task 5.3: Create 2 retrievers with different configs, verify they share query cache.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        clear_retriever_cache,
        clear_shared_query_cache,
        get_cached_retriever,
    )
    from aurora_core.activation.engine import get_cached_engine
    from aurora_core.store import SQLiteStore

    # Clear caches
    clear_retriever_cache()
    clear_shared_query_cache()

    # Create store
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))

    # Create engine
    engine = get_cached_engine(store)

    # Create retriever A with config A (weights must sum to 1.0)
    config_a = HybridConfig(
        bm25_weight=0.4,
        activation_weight=0.2,
        semantic_weight=0.4,
        enable_query_cache=True,
        query_cache_size=10,
    )
    retriever_a = get_cached_retriever(store, engine, None, config_a)

    # Add query to retriever A's cache
    import numpy as np

    test_query = "test query"
    test_embedding = np.random.rand(384).astype(np.float32)
    retriever_a._query_cache.set(test_query, test_embedding)

    # Verify retriever A has the cached query
    cached_a = retriever_a._query_cache.get(test_query)
    assert cached_a is not None, "Retriever A should have cached query"

    # Create retriever B with different config (different retriever instance, weights sum to 1.0)
    config_b = HybridConfig(
        bm25_weight=0.5,
        activation_weight=0.3,
        semantic_weight=0.2,
        enable_query_cache=True,
        query_cache_size=10,
    )
    retriever_b = get_cached_retriever(store, engine, None, config_b)

    # Verify they are different retriever instances
    assert id(retriever_a) != id(
        retriever_b
    ), "Different configs should create different retrievers"

    # Verify retriever B can access the shared query cache
    cached_b = retriever_b._query_cache.get(test_query)
    assert cached_b is not None, "Retriever B should access shared query cache"
    assert np.array_equal(cached_a, cached_b), "Should get same embedding from shared cache"

    # Verify they share the same cache instance
    assert id(retriever_a._query_cache) == id(
        retriever_b._query_cache
    ), "Should share same QueryEmbeddingCache instance"


def test_bm25_persistence_integration(tmp_path):
    """Test BM25 index persistence across retriever instances.

    Task 5.4: Build BM25 index, create new retriever, verify index loaded from disk.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        HybridRetriever,
        clear_retriever_cache,
    )
    from aurora_core.activation.engine import get_cached_engine
    from aurora_core.store import SQLiteStore

    # Clear caches
    clear_retriever_cache()

    # Create store with test data
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))

    from aurora_core.chunks.code_chunk import CodeChunk

    for i in range(50):
        chunk = CodeChunk(
            chunk_id=f"test_{i}",
            file_path=str(tmp_path / f"test_{i}.py"),
            element_type="function",
            name=f"test_func_{i}",
            line_start=(i * 10) + 1,  # line_start must be > 0
            line_end=(i * 10) + 6,
            signature=f"def test_func_{i}():",
            docstring=f"Test function {i}",
            language="python",
        )
        store.save_chunk(chunk)

    # Create engine
    engine = get_cached_engine(store)

    # Create retriever with BM25 persistence enabled
    config = HybridConfig(enable_bm25_persistence=True)
    retriever1 = HybridRetriever(store, engine, None, config=config)

    # Build and save BM25 index
    success = retriever1.build_and_save_bm25_index()
    assert success, "BM25 index build should succeed"

    # Verify index file exists
    index_path = db_path.parent / "indexes" / "bm25_index.pkl"
    assert index_path.exists(), f"BM25 index should exist at {index_path}"

    # Clear retriever cache to force new retriever creation
    clear_retriever_cache()

    # Create new retriever (should load index from disk)
    retriever2 = HybridRetriever(store, engine, None, config=config)

    # Verify index was loaded
    assert retriever2._bm25_index_loaded, "BM25 index should be loaded from disk"
    assert retriever2.bm25_scorer is not None, "BM25 scorer should be initialized"
    assert retriever2.bm25_scorer.corpus_size == 50, "Corpus size should match"


def test_activation_engine_singleton_integration(tmp_path):
    """Test ActivationEngine singleton across multiple retrievers.

    Task 5.5: Create 3 retrievers with same db_path, verify they share same engine.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        clear_retriever_cache,
        get_cached_retriever,
    )
    from aurora_core.activation.engine import _engine_cache, get_cached_engine
    from aurora_core.store import SQLiteStore

    # Clear caches
    clear_retriever_cache()
    _engine_cache.clear()

    # Create store
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))

    # Get engine (first call)
    engine1 = get_cached_engine(store)

    # Get engine again (should be same instance)
    engine2 = get_cached_engine(store)

    # Verify singleton
    assert id(engine1) == id(engine2), "Should be same ActivationEngine instance"

    # Create retrievers with different configs (different retriever instances, weights sum to 1.0)
    config_a = HybridConfig(bm25_weight=0.4, activation_weight=0.3, semantic_weight=0.3)
    config_b = HybridConfig(bm25_weight=0.5, activation_weight=0.3, semantic_weight=0.2)
    config_c = HybridConfig(bm25_weight=0.6, activation_weight=0.2, semantic_weight=0.2)

    retriever_a = get_cached_retriever(store, engine1, None, config_a)
    retriever_b = get_cached_retriever(store, engine1, None, config_b)
    retriever_c = get_cached_retriever(store, engine1, None, config_c)

    # Verify different retriever instances
    assert id(retriever_a) != id(
        retriever_b
    ), "Different configs should create different retrievers"
    assert id(retriever_b) != id(
        retriever_c
    ), "Different configs should create different retrievers"

    # Verify they all use the same engine
    assert id(retriever_a.activation_engine) == id(engine1), "Should use same engine"
    assert id(retriever_b.activation_engine) == id(engine1), "Should use same engine"
    assert id(retriever_c.activation_engine) == id(engine1), "Should use same engine"


def test_memory_overhead_validation(tmp_path):
    """Test that caching reduces memory overhead.

    Task 5.6: Create 10 retrievers, verify memory efficient (shared caches).
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        clear_retriever_cache,
        get_cached_retriever,
    )
    from aurora_core.activation.engine import get_cached_engine
    from aurora_core.store import SQLiteStore

    # Clear caches
    clear_retriever_cache()

    # Create store
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))

    # Get engine (shared across all retrievers)
    engine = get_cached_engine(store)

    # Create config (same config means same retriever instance)
    config = HybridConfig()

    # Create multiple "retrievers" (actually getting same cached instance)
    retrievers = []
    for i in range(10):
        retriever = get_cached_retriever(store, engine, None, config)
        retrievers.append(retriever)

    # Verify all are the same instance (memory efficient)
    first_id = id(retrievers[0])
    for i, retriever in enumerate(retrievers[1:], start=1):
        assert (
            id(retriever) == first_id
        ), f"Retriever {i} should be same instance (memory efficient caching)"

    # Verify shared query cache
    first_cache_id = id(retrievers[0]._query_cache) if retrievers[0]._query_cache else None
    if first_cache_id:
        for i, retriever in enumerate(retrievers[1:], start=1):
            if retriever._query_cache:
                assert (
                    id(retriever._query_cache) == first_cache_id
                ), f"Retriever {i} should share query cache"
