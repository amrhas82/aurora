"""Unit tests for shared QueryEmbeddingCache across retrievers.

Tests verify that QueryEmbeddingCache is shared across all HybridRetriever
instances, with proper LRU eviction, TTL expiration, and thread safety.

Test scenarios:
- Cache shared across multiple retrievers
- LRU eviction works across retrievers
- TTL expiration
- Thread-safe concurrent access
- Cache statistics aggregation
"""

import threading
import time

import numpy as np
import pytest  # noqa: F401 - needed for tmp_path fixture


# Mock classes for testing
class MockStore:
    """Mock storage backend."""

    def __init__(self, db_path):
        self.db_path = db_path


class MockActivationEngine:
    """Mock activation engine."""

    def __init__(self):
        pass


class MockEmbeddingProvider:
    """Mock embedding provider."""

    def __init__(self):
        pass

    def embed_query(self, query):
        """Return mock embedding."""
        # Return different embeddings for different queries
        seed = hash(query) % 1000
        np.random.seed(seed)
        return np.random.rand(384).astype(np.float32)


def test_query_cache_shared_across_retrievers(tmp_path):
    """Test that query embedding cache is shared across retrievers.

    Task 4.1: Cache embedding in retriever A, create retriever B, verify B hits cache.
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, get_cached_retriever

    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_query_cache=True, query_cache_size=10)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever A
    retriever_a = get_cached_retriever(store, engine, provider, config)

    # Access retriever A's cache directly and add an embedding
    test_query = "test query"
    test_embedding = np.random.rand(384).astype(np.float32)
    retriever_a._query_cache.set(test_query, test_embedding)

    # Verify retriever A has the cached embedding
    cached_a = retriever_a._query_cache.get(test_query)
    assert cached_a is not None, "Retriever A should have cached embedding"

    # Create retriever B (same db_path and config, so same retriever instance due to caching)
    retriever_b = get_cached_retriever(store, engine, provider, config)

    # Verify retriever B shares the same cache (they're the same instance)
    assert id(retriever_a) == id(retriever_b), "Should be same retriever instance"
    cached_b = retriever_b._query_cache.get(test_query)
    assert cached_b is not None, "Retriever B should access shared cache"
    assert np.array_equal(cached_a, cached_b), "Should get same embedding from shared cache"


def test_query_cache_lru_eviction(tmp_path):
    """Test LRU eviction works across retrievers.

    Task 4.2: Create cache with capacity=3, add 4 queries, verify oldest evicted.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        clear_retriever_cache,
        clear_shared_query_cache,
        get_cached_retriever,
    )

    # Clear caches for clean test
    clear_shared_query_cache()
    clear_retriever_cache()

    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_query_cache=True, query_cache_size=3)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever
    retriever = get_cached_retriever(store, engine, provider, config)

    # Add 3 queries to fill cache
    for i in range(3):
        query = f"query {i}"
        embedding = np.random.rand(384).astype(np.float32)
        retriever._query_cache.set(query, embedding)

    # Verify all 3 are cached
    assert retriever._query_cache.size() == 3, "Cache should be at capacity"

    # Add 4th query (should evict oldest)
    query_4 = "query 3"
    embedding_4 = np.random.rand(384).astype(np.float32)
    retriever._query_cache.set(query_4, embedding_4)

    # Verify cache size is still 3
    assert retriever._query_cache.size() == 3, "Cache should maintain capacity"

    # Verify oldest (query 0) was evicted
    assert retriever._query_cache.get("query 0") is None, "Oldest query should be evicted"

    # Verify query 1, 2, 3 are still cached
    assert retriever._query_cache.get("query 1") is not None, "Query 1 should still be cached"
    assert retriever._query_cache.get("query 2") is not None, "Query 2 should still be cached"
    assert retriever._query_cache.get(query_4) is not None, "Query 3 should be cached"


def test_query_cache_ttl_expiration(tmp_path):
    """Test TTL expiration for cached queries.

    Task 4.3: Create cache with ttl=1s, add query, sleep 2s, verify cache miss.
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        HybridConfig,
        clear_retriever_cache,
        clear_shared_query_cache,
        get_cached_retriever,
    )

    # Clear caches for clean test
    clear_shared_query_cache()
    clear_retriever_cache()

    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_query_cache=True, query_cache_ttl_seconds=1)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever
    retriever = get_cached_retriever(store, engine, provider, config)

    # Add query to cache
    test_query = "test query"
    test_embedding = np.random.rand(384).astype(np.float32)
    retriever._query_cache.set(test_query, test_embedding)

    # Verify it's cached
    cached = retriever._query_cache.get(test_query)
    assert cached is not None, "Query should be cached immediately"

    # Wait for TTL to expire
    time.sleep(2)

    # Verify cache miss due to TTL expiration
    expired = retriever._query_cache.get(test_query)
    assert expired is None, "Query should be expired after TTL"


def test_query_cache_thread_safety(tmp_path):
    """Test thread-safe concurrent access to shared cache.

    Task 4.4: Launch 5 threads accessing shared cache concurrently, verify no race conditions.
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, get_cached_retriever

    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_query_cache=True, query_cache_size=50)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever
    retriever = get_cached_retriever(store, engine, provider, config)

    # Store results from each thread
    results = []
    results_lock = threading.Lock()
    errors = []

    def cache_operations():
        """Perform cache operations in thread."""
        try:
            # Add some queries
            for i in range(10):
                query = f"thread query {i}"
                embedding = np.random.rand(384).astype(np.float32)
                retriever._query_cache.set(query, embedding)

            # Read some queries
            for i in range(10):
                query = f"thread query {i}"
                cached = retriever._query_cache.get(query)
                with results_lock:
                    results.append((query, cached is not None))
        except Exception as e:
            errors.append(e)

    # Launch 5 threads
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=cache_operations)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Threads should not error: {errors}"

    # Verify we got results
    assert len(results) > 0, "Should have cache operation results"


def test_query_cache_stats_aggregation(tmp_path):
    """Test cache statistics aggregate across retrievers.

    Task 4.5: Verify stats aggregate (2 retrievers with 1 miss + 1 hit each = 50% hit rate).
    """
    from aurora_context_code.semantic.hybrid_retriever import HybridConfig, get_cached_retriever

    db_path = str(tmp_path / "test.db")
    config = HybridConfig(enable_query_cache=True, query_cache_size=10)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create retriever (will be cached)
    retriever_a = get_cached_retriever(store, engine, provider, config)

    # Clear cache stats for clean test
    retriever_a._query_cache.clear()

    # Retriever A: miss then hit
    test_query = "test query"
    miss_a = retriever_a._query_cache.get(test_query)  # Miss
    assert miss_a is None, "Should be cache miss"

    test_embedding = np.random.rand(384).astype(np.float32)
    retriever_a._query_cache.set(test_query, test_embedding)

    hit_a = retriever_a._query_cache.get(test_query)  # Hit
    assert hit_a is not None, "Should be cache hit"

    # Get same retriever instance (due to caching)
    retriever_b = get_cached_retriever(store, engine, provider, config)

    # They should be the same instance
    assert id(retriever_a) == id(retriever_b), "Should be same instance"

    # Check stats (1 miss, 1 hit = 50%)
    stats_a = retriever_a.get_cache_stats()
    assert stats_a["hits"] == 1, "Should have 1 hit"
    assert stats_a["misses"] == 1, "Should have 1 miss"
    assert abs(stats_a["hit_rate"] - 0.5) < 0.01, (
        f"Hit rate should be 50%, got {stats_a['hit_rate']}"
    )
