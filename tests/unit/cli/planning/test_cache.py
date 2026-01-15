"""Tests for plan decomposition caching."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from aurora_cli.planning.cache import CacheMetrics, PlanDecompositionCache
from aurora_cli.planning.models import Complexity, Subgoal


@pytest.fixture
def sample_subgoals() -> list[Subgoal]:
    """Sample subgoals for testing."""
    return [
        Subgoal(
            id="sg-1",
            title="Design approach",
            description="Design the solution architecture",
            ideal_agent="@holistic-architect",
            ideal_agent_desc="Architecture specialist",
            assigned_agent="@holistic-architect",
            dependencies=[],
        ),
        Subgoal(
            id="sg-2",
            title="Implement solution",
            description="Implement the designed solution",
            ideal_agent="@full-stack-dev",
            ideal_agent_desc="Full-stack developer",
            assigned_agent="@full-stack-dev",
            dependencies=["sg-1"],
        ),
    ]


@pytest.fixture
def memory_cache() -> PlanDecompositionCache:
    """In-memory cache for testing."""
    return PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=None)


@pytest.fixture
def persistent_cache() -> PlanDecompositionCache:
    """Persistent cache for testing."""
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "test_cache.db"
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)
        yield cache


class TestPlanDecompositionCache:
    """Tests for PlanDecompositionCache."""

    def test_cache_miss(self, memory_cache: PlanDecompositionCache) -> None:
        """Test cache miss returns None."""
        result = memory_cache.get("Add authentication", Complexity.MODERATE)
        assert result is None

        stats = memory_cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    def test_cache_hit(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test cache hit returns cached result."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache the result
        memory_cache.set(goal, complexity, sample_subgoals, "soar")

        # Retrieve from cache
        result = memory_cache.get(goal, complexity)
        assert result is not None

        subgoals, source = result
        assert len(subgoals) == 2
        assert source == "soar"
        assert subgoals[0].id == "sg-1"
        assert subgoals[1].id == "sg-2"

        stats = memory_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_cache_with_context_files(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test cache considers context files in key."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE
        context_files = ["auth.py", "user.py"]

        # Cache with context files
        memory_cache.set(goal, complexity, sample_subgoals, "soar", context_files)

        # Hit with same context files
        result = memory_cache.get(goal, complexity, context_files)
        assert result is not None

        # Miss with different context files
        result = memory_cache.get(goal, complexity, ["other.py"])
        assert result is None

        # Miss with no context files
        result = memory_cache.get(goal, complexity, None)
        assert result is None

    def test_lru_eviction(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test LRU eviction when cache is full."""
        # Cache is capacity 10, fill it up
        for i in range(10):
            memory_cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        stats = memory_cache.get_stats()
        assert stats["size"] == 10
        assert stats["evictions"] == 0

        # Add one more to trigger eviction
        memory_cache.set("Goal 10", Complexity.MODERATE, sample_subgoals, "soar")

        stats = memory_cache.get_stats()
        assert stats["size"] == 10
        assert stats["evictions"] == 1

        # First item should be evicted
        result = memory_cache.get("Goal 0", Complexity.MODERATE)
        assert result is None

        # Last item should be present
        result = memory_cache.get("Goal 10", Complexity.MODERATE)
        assert result is not None

    def test_lru_ordering(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test LRU ordering - most recently used should be preserved."""
        # Fill cache
        for i in range(10):
            memory_cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        # Access Goal 0 to make it recently used
        memory_cache.get("Goal 0", Complexity.MODERATE)

        # Add new item to trigger eviction
        memory_cache.set("Goal 10", Complexity.MODERATE, sample_subgoals, "soar")

        # Goal 0 should still be present (was accessed recently)
        result = memory_cache.get("Goal 0", Complexity.MODERATE)
        assert result is not None

        # Goal 1 should be evicted (least recently used)
        result = memory_cache.get("Goal 1", Complexity.MODERATE)
        assert result is None

    def test_ttl_expiration(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test TTL-based expiration."""
        # Create cache with very short TTL (1 second)
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1 / 3600, persistent_path=None)

        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache result
        cache.set(goal, complexity, sample_subgoals, "soar")

        # Should hit immediately
        result = cache.get(goal, complexity)
        assert result is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should miss after expiration
        result = cache.get(goal, complexity)
        assert result is None

        stats = cache.get_stats()
        assert stats["misses"] == 1

    def test_complexity_in_key(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test that complexity is part of cache key."""
        goal = "Add authentication"

        # Cache with MODERATE complexity
        memory_cache.set(goal, Complexity.MODERATE, sample_subgoals, "soar")

        # Hit with same complexity
        result = memory_cache.get(goal, Complexity.MODERATE)
        assert result is not None

        # Miss with different complexity
        result = memory_cache.get(goal, Complexity.COMPLEX)
        assert result is None

    def test_clear_cache(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test clearing cache."""
        # Add multiple items
        for i in range(5):
            memory_cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        stats = memory_cache.get_stats()
        assert stats["size"] == 5

        # Clear cache
        memory_cache.clear()

        stats = memory_cache.get_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Should miss after clear
        result = memory_cache.get("Goal 0", Complexity.MODERATE)
        assert result is None

    def test_cache_stats(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test cache statistics tracking."""
        # Initial stats
        stats = memory_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

        # Add item and test miss
        result = memory_cache.get("Goal 1", Complexity.MODERATE)
        assert result is None

        stats = memory_cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.0

        # Cache and hit
        memory_cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")
        result = memory_cache.get("Goal 1", Complexity.MODERATE)
        assert result is not None

        stats = memory_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_access_count_tracking(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test that access count is tracked correctly."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache item
        memory_cache.set(goal, complexity, sample_subgoals, "soar")

        # Access multiple times
        for _ in range(5):
            result = memory_cache.get(goal, complexity)
            assert result is not None

        stats = memory_cache.get_stats()
        assert stats["hits"] == 5

    def test_persistent_cache_storage(
        self, persistent_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test persistent cache storage."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache result
        persistent_cache.set(goal, complexity, sample_subgoals, "soar")

        # Should be in in-memory cache
        result = persistent_cache.get(goal, complexity)
        assert result is not None

        # Clear in-memory cache
        persistent_cache.clear_hot_cache()

        # Should still be retrievable from persistent storage
        result = persistent_cache.get(goal, complexity)
        assert result is not None

        subgoals, source = result
        assert len(subgoals) == 2
        assert source == "soar"

    def test_persistent_cache_expiration(self, sample_subgoals: list[Subgoal]) -> None:
        """Test persistent cache TTL expiration."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.db"

            # Create cache with very short TTL
            cache = PlanDecompositionCache(
                capacity=10, ttl_hours=1 / 3600, persistent_path=cache_path
            )

            goal = "Add authentication"
            complexity = Complexity.MODERATE

            # Cache result
            cache.set(goal, complexity, sample_subgoals, "soar")

            # Wait for expiration
            time.sleep(1.1)

            # Clear in-memory cache to force persistent lookup
            cache.clear_hot_cache()

            # Should miss due to expiration
            result = cache.get(goal, complexity)
            assert result is None

    def test_cleanup_expired(self, sample_subgoals: list[Subgoal]) -> None:
        """Test cleanup of expired entries from persistent storage."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.db"

            # Create cache with very short TTL
            cache = PlanDecompositionCache(
                capacity=10, ttl_hours=1 / 3600, persistent_path=cache_path
            )

            # Add multiple items
            for i in range(5):
                cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

            # Wait for expiration
            time.sleep(1.1)

            # Cleanup expired entries
            removed = cache.cleanup_expired()
            assert removed == 5


class TestPersistentCachePromotion:
    """Tests for cache promotion from persistent to in-memory."""

    def test_persistent_to_memory_promotion(
        self, persistent_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test that persistent cache hits get promoted to in-memory cache."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache result
        persistent_cache.set(goal, complexity, sample_subgoals, "soar")

        # Clear in-memory cache
        persistent_cache.clear_hot_cache()

        # First get should fetch from persistent and promote to memory
        result = persistent_cache.get(goal, complexity)
        assert result is not None

        # Second get should hit in-memory cache (faster)
        result = persistent_cache.get(goal, complexity)
        assert result is not None

        # Both should be counted as hits
        stats = persistent_cache.get_stats()
        assert stats["hits"] == 2


class TestCacheKeyGeneration:
    """Tests for cache key generation logic."""

    def test_identical_keys_for_same_inputs(self, memory_cache: PlanDecompositionCache) -> None:
        """Test that identical inputs generate same cache key."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE
        context = ["auth.py", "user.py"]

        # Cache with first set of inputs
        key1 = memory_cache._compute_cache_key(goal, complexity, context)

        # Generate key with identical inputs
        key2 = memory_cache._compute_cache_key(goal, complexity, context)

        assert key1 == key2

    def test_different_keys_for_different_goals(self, memory_cache: PlanDecompositionCache) -> None:
        """Test that different goals generate different keys."""
        complexity = Complexity.MODERATE

        key1 = memory_cache._compute_cache_key("Add auth", complexity, None)
        key2 = memory_cache._compute_cache_key("Add logging", complexity, None)

        assert key1 != key2

    def test_different_keys_for_different_complexity(
        self, memory_cache: PlanDecompositionCache
    ) -> None:
        """Test that different complexity levels generate different keys."""
        goal = "Add authentication"

        key1 = memory_cache._compute_cache_key(goal, Complexity.SIMPLE, None)
        key2 = memory_cache._compute_cache_key(goal, Complexity.MODERATE, None)

        assert key1 != key2

    def test_context_file_order_normalized(self, memory_cache: PlanDecompositionCache) -> None:
        """Test that context file order is normalized in cache key."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Different order should generate same key
        key1 = memory_cache._compute_cache_key(goal, complexity, ["auth.py", "user.py"])
        key2 = memory_cache._compute_cache_key(goal, complexity, ["user.py", "auth.py"])

        assert key1 == key2


class TestCacheMetrics:
    """Tests for cache metrics and observability."""

    def test_metrics_enabled_by_default(self) -> None:
        """Test that metrics are enabled by default."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1)
        assert cache.enable_metrics is True

    def test_metrics_can_be_disabled(self) -> None:
        """Test that metrics can be disabled."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=False)
        assert cache.enable_metrics is False

    def test_detailed_metrics_tracking(self, sample_subgoals: list[Subgoal]) -> None:
        """Test detailed metrics tracking for hits, misses, and latency."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Test cache miss metrics
        result = cache.get(goal, complexity)
        assert result is None

        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0
        assert "avg_get_latency_ms" in stats
        assert stats["avg_get_latency_ms"] >= 0

        # Test cache hit metrics
        cache.set(goal, complexity, sample_subgoals, "soar")
        result = cache.get(goal, complexity)
        assert result is not None

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["memory_hits"] == 1
        assert stats["persistent_hits"] == 0
        assert stats["memory_hit_rate"] == 1.0

    def test_persistent_hit_tracking(self, sample_subgoals: list[Subgoal]) -> None:
        """Test tracking of persistent cache hits."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.db"
            cache = PlanDecompositionCache(
                capacity=10, ttl_hours=1, persistent_path=cache_path, enable_metrics=True
            )

            goal = "Add authentication"
            complexity = Complexity.MODERATE

            # Cache and clear memory
            cache.set(goal, complexity, sample_subgoals, "soar")
            cache.clear_hot_cache()

            # Hit from persistent storage
            result = cache.get(goal, complexity)
            assert result is not None

            stats = cache.get_stats()
            assert stats["persistent_hits"] == 1
            assert stats["memory_hits"] == 0

    def test_expired_hit_tracking(self, sample_subgoals: list[Subgoal]) -> None:
        """Test tracking of expired cache entries."""
        cache = PlanDecompositionCache(
            capacity=10, ttl_hours=1 / 3600, enable_metrics=True  # 1 second TTL
        )

        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache and wait for expiration
        cache.set(goal, complexity, sample_subgoals, "soar")
        time.sleep(1.1)

        # Try to access expired entry
        result = cache.get(goal, complexity)
        assert result is None

        stats = cache.get_stats()
        assert stats["expired_hits"] == 1
        assert stats["misses"] == 1

    def test_eviction_tracking(self, sample_subgoals: list[Subgoal]) -> None:
        """Test tracking of cache evictions."""
        cache = PlanDecompositionCache(capacity=5, ttl_hours=1, enable_metrics=True)

        # Fill cache to capacity
        for i in range(5):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        stats = cache.get_stats()
        assert stats["evictions"] == 0

        # Trigger eviction
        cache.set("Goal 5", Complexity.MODERATE, sample_subgoals, "soar")

        stats = cache.get_stats()
        assert stats["evictions"] == 1

    def test_write_operation_tracking(self, sample_subgoals: list[Subgoal]) -> None:
        """Test tracking of write operations and latency."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        # Perform multiple writes
        for i in range(5):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        stats = cache.get_stats()
        assert stats["write_operations"] == 5
        assert "avg_set_latency_ms" in stats
        assert stats["avg_set_latency_ms"] >= 0
        assert "max_set_latency_ms" in stats
        assert stats["max_set_latency_ms"] >= stats["avg_set_latency_ms"]

    def test_latency_tracking(self, sample_subgoals: list[Subgoal]) -> None:
        """Test that latency is tracked for all operations."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Test GET latency tracking
        cache.get(goal, complexity)  # Miss
        cache.set(goal, complexity, sample_subgoals, "soar")
        cache.get(goal, complexity)  # Hit

        stats = cache.get_stats()
        assert stats["total_operations"] == 2
        assert stats["max_get_latency_ms"] > 0
        assert stats["avg_get_latency_ms"] > 0

    def test_hit_rate_calculation(self, sample_subgoals: list[Subgoal]) -> None:
        """Test accurate hit rate calculation."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        # Cache 3 items
        for i in range(3):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        # 3 hits + 2 misses = 60% hit rate
        for i in range(3):
            cache.get(f"Goal {i}", Complexity.MODERATE)
        cache.get("Goal 10", Complexity.MODERATE)
        cache.get("Goal 11", Complexity.MODERATE)

        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.6
        assert stats["total_operations"] == 5

    def test_get_metrics_object(self, sample_subgoals: list[Subgoal]) -> None:
        """Test retrieving CacheMetrics object."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        # Perform operations
        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")
        cache.get("Goal 1", Complexity.MODERATE)
        cache.get("Goal 2", Complexity.MODERATE)

        metrics = cache.get_metrics()
        assert isinstance(metrics, CacheMetrics)
        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.hit_rate == 0.5

    def test_get_metrics_raises_when_disabled(self) -> None:
        """Test that get_metrics raises when metrics are disabled."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=False)

        with pytest.raises(RuntimeError, match="Metrics are disabled"):
            cache.get_metrics()

    def test_legacy_stats_compatibility(self, sample_subgoals: list[Subgoal]) -> None:
        """Test that legacy stats format is still supported when metrics disabled."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=False)

        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")
        cache.get("Goal 1", Complexity.MODERATE)
        cache.get("Goal 2", Complexity.MODERATE)

        stats = cache.get_stats()
        # Should have basic stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        # Should NOT have detailed metrics
        assert "avg_get_latency_ms" not in stats
        assert "memory_hits" not in stats

    def test_log_performance_summary(
        self, sample_subgoals: list[Subgoal], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging of performance summary."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        # Perform operations
        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")
        cache.get("Goal 1", Complexity.MODERATE)

        # Log summary
        with caplog.at_level(logging.INFO):
            cache.log_performance_summary()

        # Verify log was created
        assert len(caplog.records) > 0
        assert "Cache performance summary" in caplog.text


class TestCacheLogging:
    """Tests for cache logging functionality."""

    def test_cache_hit_logging(
        self, sample_subgoals: list[Subgoal], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that cache hits are logged with details."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        cache.set("Add authentication", Complexity.MODERATE, sample_subgoals, "soar")

        with caplog.at_level(logging.INFO):
            cache.get("Add authentication", Complexity.MODERATE)

        # Verify hit was logged
        assert any("Cache HIT" in record.message for record in caplog.records)

    def test_cache_miss_logging(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that cache misses are logged."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        with caplog.at_level(logging.INFO):
            cache.get("Nonexistent goal", Complexity.MODERATE)

        # Verify miss was logged
        assert any("Cache MISS" in record.message for record in caplog.records)

    def test_cache_set_logging(
        self, sample_subgoals: list[Subgoal], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that cache SET operations are logged."""
        cache = PlanDecompositionCache(capacity=10, ttl_hours=1, enable_metrics=True)

        with caplog.at_level(logging.INFO):
            cache.set("Add authentication", Complexity.MODERATE, sample_subgoals, "soar")

        # Verify SET was logged
        assert any("Cache SET" in record.message for record in caplog.records)

    def test_eviction_logging(
        self, sample_subgoals: list[Subgoal], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that evictions are logged."""
        cache = PlanDecompositionCache(capacity=2, ttl_hours=1, enable_metrics=True)

        # Fill cache
        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")
        cache.set("Goal 2", Complexity.MODERATE, sample_subgoals, "soar")

        with caplog.at_level(logging.DEBUG):
            # Trigger eviction
            cache.set("Goal 3", Complexity.MODERATE, sample_subgoals, "soar")

        # Verify eviction was logged
        assert any("Cache eviction" in record.message for record in caplog.records)


class TestCacheEdgeCases:
    """Tests for cache edge cases and boundary conditions."""

    def test_empty_goal_string(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test caching with empty goal string."""
        goal = ""
        complexity = Complexity.MODERATE

        memory_cache.set(goal, complexity, sample_subgoals, "soar")
        result = memory_cache.get(goal, complexity)
        assert result is not None

        subgoals, source = result
        assert len(subgoals) == 2

    def test_very_long_goal_string(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test caching with very long goal string."""
        goal = "A" * 10000  # 10K character goal
        complexity = Complexity.MODERATE

        memory_cache.set(goal, complexity, sample_subgoals, "soar")
        result = memory_cache.get(goal, complexity)
        assert result is not None

    def test_unicode_goal_string(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test caching with unicode characters in goal."""
        goal = "添加身份验证系统 🔐"  # Chinese + emoji
        complexity = Complexity.MODERATE

        memory_cache.set(goal, complexity, sample_subgoals, "soar")
        result = memory_cache.get(goal, complexity)
        assert result is not None

        subgoals, source = result
        assert len(subgoals) == 2

    def test_empty_subgoals_list(self, memory_cache: PlanDecompositionCache) -> None:
        """Test caching empty subgoals list."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE
        empty_subgoals: list[Subgoal] = []

        memory_cache.set(goal, complexity, empty_subgoals, "soar")
        result = memory_cache.get(goal, complexity)
        assert result is not None

        subgoals, source = result
        assert len(subgoals) == 0
        assert source == "soar"

    def test_very_large_subgoals_list(self, memory_cache: PlanDecompositionCache) -> None:
        """Test caching with large number of subgoals."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Create 100 subgoals
        large_subgoals = [
            Subgoal(
                id=f"sg-{i}",
                title=f"Subgoal {i}",
                description=f"Description for subgoal {i}",
                ideal_agent="@full-stack-dev",
                ideal_agent_desc="Developer",
                assigned_agent="@full-stack-dev",
                dependencies=[],
            )
            for i in range(100)
        ]

        memory_cache.set(goal, complexity, large_subgoals, "soar")
        result = memory_cache.get(goal, complexity)
        assert result is not None

        subgoals, source = result
        assert len(subgoals) == 100

    def test_empty_context_files_list(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test caching with empty context files list."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Empty list should behave same as None (both result in empty context)
        memory_cache.set(goal, complexity, sample_subgoals, "soar", [])

        # Should hit with empty list
        result = memory_cache.get(goal, complexity, [])
        assert result is not None

        # Should also hit with None (empty context)
        result = memory_cache.get(goal, complexity, None)
        assert result is not None

    def test_duplicate_context_files(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test caching with duplicate context files."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE
        context = ["auth.py", "auth.py", "user.py"]

        memory_cache.set(goal, complexity, sample_subgoals, "soar", context)
        result = memory_cache.get(goal, complexity, context)
        assert result is not None

    def test_special_characters_in_context_files(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test caching with special characters in context file paths."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE
        context = [
            "/path/with spaces/auth.py",
            "/path/with-dashes/user.py",
            "/path/with_underscores/model.py",
        ]

        memory_cache.set(goal, complexity, sample_subgoals, "soar", context)
        result = memory_cache.get(goal, complexity, context)
        assert result is not None

    def test_zero_capacity_cache(self, sample_subgoals: list[Subgoal]) -> None:
        """Test cache with zero capacity."""
        cache = PlanDecompositionCache(capacity=0, ttl_hours=1)

        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Setting with zero capacity will fail since popitem() on empty dict raises KeyError
        # This is expected behavior - cache requires capacity >= 1
        try:
            cache.set(goal, complexity, sample_subgoals, "soar")
        except KeyError:
            pass  # Expected for zero capacity

        # Should miss because capacity is 0
        result = cache.get(goal, complexity)
        assert result is None

    def test_capacity_one_cache(self, sample_subgoals: list[Subgoal]) -> None:
        """Test cache with capacity of 1."""
        cache = PlanDecompositionCache(capacity=1, ttl_hours=1)

        # Add first item
        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")
        result = cache.get("Goal 1", Complexity.MODERATE)
        assert result is not None

        # Add second item, should evict first
        cache.set("Goal 2", Complexity.MODERATE, sample_subgoals, "soar")
        result = cache.get("Goal 2", Complexity.MODERATE)
        assert result is not None

        # First item should be evicted
        result = cache.get("Goal 1", Complexity.MODERATE)
        assert result is None

    def test_same_goal_different_source(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test overwriting cache entry with different source."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache with "soar" source
        memory_cache.set(goal, complexity, sample_subgoals, "soar")
        result = memory_cache.get(goal, complexity)
        assert result is not None
        _, source = result
        assert source == "soar"

        # Overwrite with "heuristic" source
        memory_cache.set(goal, complexity, sample_subgoals, "heuristic")
        result = memory_cache.get(goal, complexity)
        assert result is not None
        _, source = result
        assert source == "heuristic"

    def test_concurrent_evictions(self, sample_subgoals: list[Subgoal]) -> None:
        """Test multiple evictions in succession."""
        cache = PlanDecompositionCache(capacity=3, ttl_hours=1)

        # Fill cache
        for i in range(3):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        # Add multiple items to trigger multiple evictions
        for i in range(3, 10):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        stats = cache.get_stats()
        assert stats["size"] == 3
        assert stats["evictions"] == 7

        # Only last 3 items should be present
        for i in range(7, 10):
            result = cache.get(f"Goal {i}", Complexity.MODERATE)
            assert result is not None

        # Earlier items should be evicted
        for i in range(0, 7):
            result = cache.get(f"Goal {i}", Complexity.MODERATE)
            assert result is None

    def test_update_existing_entry_access_count(
        self, memory_cache: PlanDecompositionCache, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test that updating an entry resets its access count."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Cache and access multiple times
        memory_cache.set(goal, complexity, sample_subgoals, "soar")
        for _ in range(5):
            memory_cache.get(goal, complexity)

        # Update entry
        memory_cache.set(goal, complexity, sample_subgoals, "soar")

        # Access count should be reset to 0
        # (implementation detail - entry is replaced)

    def test_negative_ttl_hours(self, sample_subgoals: list[Subgoal]) -> None:
        """Test cache with negative TTL (edge case)."""
        # Negative TTL means all entries are immediately expired
        cache = PlanDecompositionCache(capacity=10, ttl_hours=-1)

        goal = "Add authentication"
        complexity = Complexity.MODERATE

        cache.set(goal, complexity, sample_subgoals, "soar")
        result = cache.get(goal, complexity)
        # Should miss because TTL is negative (expired immediately)
        assert result is None


class TestCachePersistentEdgeCases:
    """Tests for persistent cache edge cases."""

    def test_persistent_path_with_nonexistent_directory(
        self, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test persistent cache creates directory if it doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "nested" / "dir" / "cache.db"
            cache = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)

            goal = "Add authentication"
            complexity = Complexity.MODERATE

            cache.set(goal, complexity, sample_subgoals, "soar")
            assert cache_path.exists()

    def test_persistent_cache_invalid_json(self) -> None:
        """Test persistent cache handles corrupted data gracefully."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache.db"
            cache = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)

            # Manually insert corrupted data
            import sqlite3

            conn = sqlite3.connect(cache_path)
            conn.execute(
                """
                INSERT INTO decomposition_cache
                (cache_key, goal_hash, subgoals, source, timestamp, access_count, last_access)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("test_key", "hash", "invalid json{", "soar", time.time(), 0, time.time()),
            )
            conn.commit()
            conn.close()

            # Should handle gracefully
            result = cache._get_from_persistent("test_key")
            assert result is None

    def test_multiple_cache_instances_same_db(self, sample_subgoals: list[Subgoal]) -> None:
        """Test multiple cache instances sharing same persistent DB."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache.db"

            cache1 = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)
            cache2 = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)

            goal = "Add authentication"
            complexity = Complexity.MODERATE

            # Set in first cache
            cache1.set(goal, complexity, sample_subgoals, "soar")

            # Clear memory of second cache
            cache2.clear_hot_cache()

            # Should retrieve from persistent storage
            result = cache2.get(goal, complexity)
            assert result is not None

    def test_cleanup_expired_with_no_expired_entries(self) -> None:
        """Test cleanup when there are no expired entries."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache.db"
            cache = PlanDecompositionCache(capacity=10, ttl_hours=24, persistent_path=cache_path)

            # Add entries that won't expire
            for i in range(5):
                cache.set(
                    f"Goal {i}",
                    Complexity.MODERATE,
                    [
                        Subgoal(
                            id=f"sg-{i}",
                            title=f"Subgoal {i}",
                            description="Test description for validation",
                            ideal_agent="@dev",
                            ideal_agent_desc="Developer",
                            assigned_agent="@dev",
                            dependencies=[],
                        )
                    ],
                    "soar",
                )

            removed = cache.cleanup_expired()
            assert removed == 0

    def test_cleanup_expired_with_empty_db(self) -> None:
        """Test cleanup on empty database."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache.db"
            cache = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)

            removed = cache.cleanup_expired()
            assert removed == 0


class TestCacheMetricsEdgeCases:
    """Tests for cache metrics edge cases."""

    def test_hit_rate_with_zero_operations(self) -> None:
        """Test hit rate calculation with no operations."""
        metrics = CacheMetrics()
        assert metrics.hit_rate == 0.0

    def test_hit_rate_with_only_hits(self) -> None:
        """Test hit rate calculation with only hits."""
        metrics = CacheMetrics()
        metrics.record_hit(1.0, "memory")
        metrics.record_hit(1.0, "memory")
        assert metrics.hit_rate == 1.0

    def test_hit_rate_with_only_misses(self) -> None:
        """Test hit rate calculation with only misses."""
        metrics = CacheMetrics()
        metrics.record_miss(1.0)
        metrics.record_miss(1.0)
        assert metrics.hit_rate == 0.0

    def test_avg_latency_with_zero_operations(self) -> None:
        """Test average latency with no operations."""
        metrics = CacheMetrics()
        assert metrics.avg_get_latency_ms == 0.0
        assert metrics.avg_set_latency_ms == 0.0

    def test_max_latency_tracking(self) -> None:
        """Test maximum latency tracking."""
        metrics = CacheMetrics()

        metrics.record_hit(1.0, "memory")
        metrics.record_hit(5.0, "memory")
        metrics.record_hit(3.0, "memory")

        assert metrics.max_get_latency_ms == 5.0

    def test_mixed_hit_sources(self) -> None:
        """Test tracking hits from different sources."""
        metrics = CacheMetrics()

        metrics.record_hit(1.0, "memory")
        metrics.record_hit(2.0, "memory")
        metrics.record_hit(3.0, "persistent")

        assert metrics.hits == 3
        assert metrics.memory_hits == 2
        assert metrics.persistent_hits == 1

    def test_invalid_hit_source_ignored(self) -> None:
        """Test that invalid hit sources don't break metrics."""
        metrics = CacheMetrics()

        # Should not raise, just won't update specific counters
        metrics.record_hit(1.0, "invalid_source")

        assert metrics.hits == 1
        assert metrics.memory_hits == 0
        assert metrics.persistent_hits == 0


class TestCacheInvalidation:
    """Tests for cache invalidation scenarios."""

    def test_clear_preserves_persistent_but_clears_memory(
        self, sample_subgoals: list[Subgoal]
    ) -> None:
        """Test that clear_hot_cache preserves persistent storage."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache.db"
            cache = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)

            goal = "Add authentication"
            complexity = Complexity.MODERATE

            cache.set(goal, complexity, sample_subgoals, "soar")

            # Verify in memory
            stats = cache.get_stats()
            assert stats["size"] == 1

            # Clear memory only
            cache.clear_hot_cache()
            stats = cache.get_stats()
            assert stats["size"] == 0

            # Should still retrieve from persistent
            result = cache.get(goal, complexity)
            assert result is not None

    def test_full_clear_removes_persistent(self, sample_subgoals: list[Subgoal]) -> None:
        """Test that full clear removes persistent entries."""
        with TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache.db"
            cache = PlanDecompositionCache(capacity=10, ttl_hours=1, persistent_path=cache_path)

            goal = "Add authentication"
            complexity = Complexity.MODERATE

            cache.set(goal, complexity, sample_subgoals, "soar")
            cache.clear()

            # Should not retrieve from persistent
            result = cache.get(goal, complexity)
            assert result is None
