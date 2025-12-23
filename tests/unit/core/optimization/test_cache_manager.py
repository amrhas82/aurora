"""
Unit tests for CacheManager.

Tests cover:
- LRU cache operations (get, set, eviction)
- Hot cache tier
- Activation scores cache with TTL
- Cache promotion
- Cache statistics
- Memory usage estimation
"""

import time

import pytest

from aurora_core.optimization.cache_manager import (
    CacheEntry,
    CacheManager,
    CacheStats,
    LRUCache,
)


class TestLRUCache:
    """Test LRU cache implementation."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = LRUCache(capacity=3)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key returns None."""
        cache = LRUCache(capacity=3)
        assert cache.get("nonexistent") is None

    def test_eviction_at_capacity(self):
        """Test LRU eviction when capacity is reached."""
        cache = LRUCache(capacity=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Add one more (should evict key1 - oldest)
        evicted = cache.set("key4", "value4")
        assert evicted is True
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key4") == "value4"  # New item present

    def test_lru_order_on_access(self):
        """Test that accessing an item updates its position."""
        cache = LRUCache(capacity=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 (moves it to end)
        cache.get("key1")

        # Add new item (should evict key2, not key1)
        cache.set("key4", "value4")
        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None  # Evicted

    def test_update_existing_key(self):
        """Test updating an existing key."""
        cache = LRUCache(capacity=3)
        cache.set("key1", "value1")
        cache.set("key1", "value1_updated")
        assert cache.get("key1") == "value1_updated"

    def test_access_count_increments(self):
        """Test that access count increments on get."""
        cache = LRUCache(capacity=3)
        cache.set("key1", "value1")

        # Access multiple times
        cache.get("key1")
        cache.get("key1")

        # Check access count in entry
        entry = cache.cache["key1"]
        assert entry.access_count == 2

    def test_clear(self):
        """Test clearing all entries."""
        cache = LRUCache(capacity=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None

    def test_size(self):
        """Test size reporting."""
        cache = LRUCache(capacity=10)
        assert cache.size() == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

    def test_items(self):
        """Test getting all items."""
        cache = LRUCache(capacity=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        items = cache.items()
        assert len(items) == 2
        assert ("key1", "value1") in items
        assert ("key2", "value2") in items


class TestCacheEntry:
    """Test CacheEntry data class."""

    def test_create_entry(self):
        """Test creating cache entry."""
        timestamp = time.time()
        entry = CacheEntry(
            value="test_value", timestamp=timestamp, access_count=0, last_access=timestamp
        )

        assert entry.value == "test_value"
        assert entry.timestamp == timestamp
        assert entry.access_count == 0
        assert entry.last_access == timestamp

    def test_default_last_access(self):
        """Test that last_access defaults to timestamp."""
        timestamp = time.time()
        entry = CacheEntry(
            value="test_value",
            timestamp=timestamp,
        )

        assert entry.last_access == timestamp

    def test_is_expired(self):
        """Test expiration check."""
        old_time = time.time() - 1000  # 1000 seconds ago
        entry = CacheEntry(
            value="test_value",
            timestamp=old_time,
        )

        # Should be expired with 100 second TTL
        assert entry.is_expired(ttl_seconds=100) is True

        # Should not be expired with 2000 second TTL
        assert entry.is_expired(ttl_seconds=2000) is False


class TestCacheManagerHotCache:
    """Test hot cache tier operations."""

    def test_set_and_get_chunk(self):
        """Test setting and getting chunks."""
        manager = CacheManager(hot_cache_size=10)
        chunk_data = {"id": "chunk1", "content": "test"}

        manager.set_chunk("chunk1", chunk_data)
        retrieved = manager.get_chunk("chunk1")

        assert retrieved == chunk_data

    def test_get_chunk_miss(self):
        """Test cache miss returns None."""
        manager = CacheManager(hot_cache_size=10)
        assert manager.get_chunk("nonexistent") is None

    def test_hot_cache_hit_tracking(self):
        """Test that hot cache hits are tracked."""
        manager = CacheManager(hot_cache_size=10)
        manager.set_chunk("chunk1", {"data": "test"})

        # First get - should be hot cache hit
        manager.get_chunk("chunk1")
        stats = manager.get_stats()
        assert stats.hot_hits == 1
        assert stats.hot_misses == 0

    def test_hot_cache_miss_tracking(self):
        """Test that hot cache misses are tracked."""
        manager = CacheManager(hot_cache_size=10)

        # Get nonexistent chunk - should be miss
        manager.get_chunk("nonexistent")
        stats = manager.get_stats()
        assert stats.hot_hits == 0
        assert stats.hot_misses == 1

    def test_hot_cache_eviction_tracking(self):
        """Test that evictions are tracked."""
        manager = CacheManager(hot_cache_size=2)

        # Fill cache
        manager.set_chunk("chunk1", {"data": "1"})
        manager.set_chunk("chunk2", {"data": "2"})

        # Add one more (triggers eviction)
        manager.set_chunk("chunk3", {"data": "3"})

        stats = manager.get_stats()
        assert stats.evictions == 1

    def test_clear_hot_cache(self):
        """Test clearing hot cache."""
        manager = CacheManager(hot_cache_size=10)
        manager.set_chunk("chunk1", {"data": "test"})

        manager.clear_hot_cache()
        assert manager.get_chunk("chunk1") is None


class TestActivationScoresCache:
    """Test activation scores caching with TTL."""

    def test_set_and_get_activation(self):
        """Test setting and getting activation scores."""
        manager = CacheManager(activation_ttl_seconds=600)
        manager.set_activation("chunk1", 2.5)

        score = manager.get_activation("chunk1")
        assert score == 2.5

    def test_get_activation_miss(self):
        """Test activation cache miss returns None."""
        manager = CacheManager(activation_ttl_seconds=600)
        assert manager.get_activation("nonexistent") is None

    def test_activation_expiration(self):
        """Test that expired activations are not returned."""
        manager = CacheManager(activation_ttl_seconds=1)  # 1 second TTL
        manager.set_activation("chunk1", 2.5)

        # Wait for expiration
        time.sleep(1.5)

        # Should return None (expired)
        score = manager.get_activation("chunk1")
        assert score is None

    def test_activation_hit_tracking(self):
        """Test that activation cache hits are tracked."""
        manager = CacheManager(activation_ttl_seconds=600)
        manager.set_activation("chunk1", 2.5)

        # Get activation - should be hit
        manager.get_activation("chunk1")
        stats = manager.get_stats()
        assert stats.activation_hits == 1
        assert stats.activation_misses == 0

    def test_activation_miss_tracking(self):
        """Test that activation cache misses are tracked."""
        manager = CacheManager(activation_ttl_seconds=600)

        # Get nonexistent - should be miss
        manager.get_activation("nonexistent")
        stats = manager.get_stats()
        assert stats.activation_hits == 0
        assert stats.activation_misses == 1

    def test_cleanup_expired_activations(self):
        """Test cleanup of expired activations."""
        manager = CacheManager(activation_ttl_seconds=1)

        # Add multiple activations
        manager.set_activation("chunk1", 1.0)
        manager.set_activation("chunk2", 2.0)

        # Wait for expiration
        time.sleep(1.5)

        # Cleanup
        removed = manager.cleanup_expired_activations()
        assert removed == 2

    def test_clear_activation_cache(self):
        """Test clearing activation cache."""
        manager = CacheManager(activation_ttl_seconds=600)
        manager.set_activation("chunk1", 2.5)
        manager.set_activation("chunk2", 3.0)

        manager.clear_activation_cache()
        assert manager.get_activation("chunk1") is None
        assert manager.get_activation("chunk2") is None


class TestCacheStats:
    """Test cache statistics tracking."""

    def test_stats_initialization(self):
        """Test stats start at zero."""
        stats = CacheStats()
        assert stats.hot_hits == 0
        assert stats.hot_misses == 0
        assert stats.activation_hits == 0
        assert stats.activation_misses == 0
        assert stats.evictions == 0

    def test_hot_hit_rate_calculation(self):
        """Test hot cache hit rate calculation."""
        stats = CacheStats()
        stats.hot_hits = 7
        stats.hot_misses = 3

        assert stats.hot_hit_rate == 0.7

    def test_hot_hit_rate_with_no_queries(self):
        """Test hit rate with no queries."""
        stats = CacheStats()
        assert stats.hot_hit_rate == 0.0

    def test_activation_hit_rate_calculation(self):
        """Test activation cache hit rate calculation."""
        stats = CacheStats()
        stats.activation_hits = 80
        stats.activation_misses = 20

        assert stats.activation_hit_rate == 0.8

    def test_overall_hit_rate(self):
        """Test overall hit rate across all tiers."""
        stats = CacheStats()
        stats.hot_hits = 50
        stats.hot_misses = 50
        stats.activation_hits = 30
        stats.activation_misses = 20

        # Total: 80 hits out of 150 queries
        assert stats.overall_hit_rate == 80 / 150

    def test_get_stats(self):
        """Test getting stats from manager."""
        manager = CacheManager()

        # Perform some operations
        manager.set_chunk("chunk1", {"data": "test"})
        manager.get_chunk("chunk1")  # Hit
        manager.get_chunk("chunk2")  # Miss

        stats = manager.get_stats()
        assert stats.hot_hits == 1
        assert stats.hot_misses == 1

    def test_clear_all_resets_stats(self):
        """Test that clear_all resets statistics."""
        manager = CacheManager()

        # Perform operations
        manager.set_chunk("chunk1", {"data": "test"})
        manager.get_chunk("chunk1")

        # Clear all
        manager.clear_all()

        # Stats should be reset
        stats = manager.get_stats()
        assert stats.hot_hits == 0
        assert stats.hot_misses == 0


class TestMemoryUsage:
    """Test memory usage estimation."""

    def test_memory_usage_empty(self):
        """Test memory usage with empty cache."""
        manager = CacheManager()
        usage = manager.get_memory_usage_estimate()

        assert usage["hot_cache_bytes"] == 0
        assert usage["activation_cache_bytes"] == 0
        assert usage["total_bytes"] == 0

    def test_memory_usage_with_chunks(self):
        """Test memory usage with cached chunks."""
        manager = CacheManager(hot_cache_size=10)

        # Add some chunks
        for i in range(5):
            manager.set_chunk(f"chunk{i}", {"data": f"test{i}"})

        usage = manager.get_memory_usage_estimate()

        # Should estimate ~10KB per chunk = ~50KB for 5 chunks
        assert usage["hot_cache_bytes"] == 50_000
        assert usage["total_bytes"] >= 50_000

    def test_memory_usage_with_activations(self):
        """Test memory usage with cached activations."""
        manager = CacheManager()

        # Add activation scores
        for i in range(100):
            manager.set_activation(f"chunk{i}", float(i))

        usage = manager.get_memory_usage_estimate()

        # Should estimate ~100 bytes per score = ~10KB for 100 scores
        assert usage["activation_cache_bytes"] == 10_000
        assert usage["total_bytes"] >= 10_000


class TestCacheIntegration:
    """Test integrated cache operations."""

    def test_mixed_cache_operations(self):
        """Test mixed operations across cache tiers."""
        manager = CacheManager(
            hot_cache_size=5,
            activation_ttl_seconds=600,
        )

        # Set chunks and activations
        for i in range(3):
            manager.set_chunk(f"chunk{i}", {"id": i})
            manager.set_activation(f"chunk{i}", float(i))

        # Retrieve
        chunk = manager.get_chunk("chunk1")
        activation = manager.get_activation("chunk1")

        assert chunk == {"id": 1}
        assert activation == 1.0

        # Check stats
        stats = manager.get_stats()
        assert stats.hot_hits == 1
        assert stats.activation_hits == 1

    def test_cache_thrashing(self):
        """Test cache behavior under thrashing conditions."""
        manager = CacheManager(hot_cache_size=2)  # Small cache

        # Add more items than capacity
        for i in range(10):
            manager.set_chunk(f"chunk{i}", {"id": i})

        # Should have evictions
        stats = manager.get_stats()
        assert stats.evictions >= 8  # At least 8 evictions

        # Only last 2 should be in cache
        assert manager.get_chunk("chunk9") is not None
        assert manager.get_chunk("chunk8") is not None
        assert manager.get_chunk("chunk0") is None  # Evicted


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_capacity_cache(self):
        """Test cache with zero capacity."""
        # This should work but always evict
        cache = LRUCache(capacity=1)
        cache.set("key1", "value1")
        evicted = cache.set("key2", "value2")

        assert evicted is True

    def test_negative_ttl(self):
        """Test behavior with negative TTL."""
        manager = CacheManager(activation_ttl_seconds=-1)
        manager.set_activation("chunk1", 1.0)

        # Should immediately expire
        score = manager.get_activation("chunk1")
        assert score is None

    def test_very_large_cache(self):
        """Test cache with very large capacity."""
        manager = CacheManager(hot_cache_size=100_000)

        # Should handle large capacity
        for i in range(100):
            manager.set_chunk(f"chunk{i}", {"id": i})

        # No evictions should occur
        stats = manager.get_stats()
        assert stats.evictions == 0

    def test_clear_all(self):
        """Test clearing all caches."""
        manager = CacheManager()

        # Add data
        manager.set_chunk("chunk1", {"data": "test"})
        manager.set_activation("chunk1", 1.0)

        # Clear all
        manager.clear_all()

        # Everything should be gone
        assert manager.get_chunk("chunk1") is None
        assert manager.get_activation("chunk1") is None

        # Stats should be reset
        stats = manager.get_stats()
        assert stats.hot_hits == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
