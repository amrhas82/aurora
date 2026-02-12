"""Unit tests for HybridRetriever instance caching.

Tests verify that HybridRetriever instances are properly cached based on
db_path and config hash, with thread-safe access and cache statistics.

Test scenarios:
- Cache hit when same db_path and config (identity check)
- Cache miss when different db_path
- Cache miss when different config
- Cache statistics (hit rate calculation)
- Thread-safe concurrent access
"""

import threading

import pytest  # noqa: F401 - needed for tmp_path fixture

from aurora_context_code.semantic.hybrid_retriever import HybridConfig


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


def test_retriever_cache_same_db_config(tmp_path):
    """Test that two retrievers with same db_path and config return same instance.

    Task 1.1: Verify cache hit for identical parameters using id() check.
    """
    # Import the caching function (will be implemented in task 1.6)
    from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever

    db_path = str(tmp_path / "test.db")
    config = HybridConfig()

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create two retrievers with same parameters
    retriever1 = get_cached_retriever(store, engine, provider, config)
    retriever2 = get_cached_retriever(store, engine, provider, config)

    # Verify they are the same object (identity check)
    assert id(retriever1) == id(retriever2), "Same db_path and config should return cached instance"


def test_retriever_cache_different_db(tmp_path):
    """Test that two retrievers with different db_path return different instances.

    Task 1.2: Verify cache miss for different database paths.
    """
    from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever

    db_path1 = str(tmp_path / "test1.db")
    db_path2 = str(tmp_path / "test2.db")
    config = HybridConfig()

    # Create mock dependencies for first retriever
    store1 = MockStore(db_path1)
    engine1 = MockActivationEngine()
    provider1 = MockEmbeddingProvider()

    # Create mock dependencies for second retriever
    store2 = MockStore(db_path2)
    engine2 = MockActivationEngine()
    provider2 = MockEmbeddingProvider()

    # Create two retrievers with different db_paths
    retriever1 = get_cached_retriever(store1, engine1, provider1, config)
    retriever2 = get_cached_retriever(store2, engine2, provider2, config)

    # Verify they are different objects
    assert id(retriever1) != id(retriever2), "Different db_path should return different instances"


def test_retriever_cache_different_config(tmp_path):
    """Test that two retrievers with different config return different instances.

    Task 1.3: Verify cache miss for different configurations (config hash).
    """
    from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever

    db_path = str(tmp_path / "test.db")
    config1 = HybridConfig(bm25_weight=0.4, activation_weight=0.3, semantic_weight=0.3)
    config2 = HybridConfig(bm25_weight=0.6, activation_weight=0.2, semantic_weight=0.2)

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Create two retrievers with different configs
    retriever1 = get_cached_retriever(store, engine, provider, config1)
    retriever2 = get_cached_retriever(store, engine, provider, config2)

    # Verify they are different objects (cache miss due to config change)
    assert id(retriever1) != id(retriever2), "Different config should return different instances"


def test_retriever_cache_hit_rate_stats(tmp_path):
    """Test cache hit rate statistics tracking.

    Task 1.4: Verify cache statistics API and hit rate calculation.
    Create retriever 3 times with same params, expect 66% hit rate (2 hits, 1 miss).
    """
    from aurora_context_code.semantic.hybrid_retriever import (
        clear_retriever_cache,
        get_cache_stats,
        get_cached_retriever,
    )

    db_path = str(tmp_path / "test.db")
    config = HybridConfig()

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Clear cache stats before test
    clear_retriever_cache()

    # Create retriever 3 times with same parameters
    retriever1 = get_cached_retriever(store, engine, provider, config)
    retriever2 = get_cached_retriever(store, engine, provider, config)
    retriever3 = get_cached_retriever(store, engine, provider, config)

    # Get cache statistics
    stats = get_cache_stats()

    # Verify statistics
    assert "total_hits" in stats, "Stats should include total_hits"
    assert "total_misses" in stats, "Stats should include total_misses"
    assert "hit_rate" in stats, "Stats should include hit_rate"
    assert "cache_size" in stats, "Stats should include cache_size"

    # First call is miss, second and third are hits
    assert stats["total_misses"] >= 1, "Should have at least 1 miss (first call)"
    assert stats["total_hits"] >= 2, "Should have at least 2 hits (second and third calls)"

    # Calculate expected hit rate (2 hits / 3 total = 66.7%)
    total = stats["total_hits"] + stats["total_misses"]
    if total > 0:
        hit_rate = stats["total_hits"] / total
        # Allow some tolerance for other test interference
        assert hit_rate >= 0.6, f"Hit rate should be >= 60%, got {hit_rate:.2%}"


def test_retriever_cache_thread_safety(tmp_path):
    """Test thread-safe concurrent access to retriever cache.

    Task 1.5: Verify no race conditions with concurrent retriever creation.
    Launch 5 threads creating retriever concurrently, verify all get same instance.
    """
    from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever

    db_path = str(tmp_path / "test.db")
    config = HybridConfig()

    # Create mock dependencies
    store = MockStore(db_path)
    engine = MockActivationEngine()
    provider = MockEmbeddingProvider()

    # Store retriever instances from each thread
    retrievers = []
    retriever_lock = threading.Lock()
    errors = []

    def create_retriever():
        """Create retriever in thread."""
        try:
            retriever = get_cached_retriever(store, engine, provider, config)
            with retriever_lock:
                retrievers.append(retriever)
        except Exception as e:
            errors.append(e)

    # Launch 5 threads
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=create_retriever)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Threads should not error: {errors}"

    # Verify all threads got retrievers
    assert len(retrievers) == 5, f"Should have 5 retrievers, got {len(retrievers)}"

    # Verify all retrievers are the same instance (no race conditions)
    first_id = id(retrievers[0])
    for i, retriever in enumerate(retrievers[1:], start=1):
        assert id(retriever) == first_id, (
            f"Retriever {i} has different id: "
            f"{id(retriever)} vs {first_id} (race condition detected)"
        )
