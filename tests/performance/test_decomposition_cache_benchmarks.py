"""Performance benchmarks for plan decomposition cache.

This test suite benchmarks cached vs non-cached decomposition operations:
1. Cache GET latency (memory vs persistent hits)
2. Cache SET latency (in-memory vs persistent storage)
3. Cache key computation overhead
4. End-to-end decomposition speedup with cache
5. Cache eviction performance at scale
6. Persistent storage I/O performance

Performance Targets:
- Memory cache GET: <1ms (99th percentile)
- Persistent cache GET: <5ms (99th percentile)
- Cache SET: <10ms (99th percentile)
- Cache hit speedup: ≥50x faster than full decomposition
- Key computation: <0.1ms
- Cache overhead: <5% when miss occurs

Test Strategy:
- Use pytest-benchmark for accurate timing measurements
- Test realistic cache scenarios (hit rates, eviction patterns)
- Measure both hot (in-memory) and cold (persistent) cache paths
- Compare cached vs non-cached decomposition end-to-end
- Verify cache provides significant performance benefit
"""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from aurora_cli.planning.cache import PlanDecompositionCache
from aurora_cli.planning.models import Complexity, Subgoal


@pytest.fixture
def sample_subgoals() -> list[Subgoal]:
    """Standard set of subgoals for benchmarking."""
    return [
        Subgoal(
            id="sg-1",
            title="Design approach",
            description="Design the solution architecture and data model",
            ideal_agent="@system-architect",
            ideal_agent_desc="System architecture specialist",
            assigned_agent="@system-architect",
            dependencies=[],
        ),
        Subgoal(
            id="sg-2",
            title="Implement core logic",
            description="Implement the core business logic and algorithms",
            ideal_agent="@code-developer",
            ideal_agent_desc="Full-stack development specialist",
            assigned_agent="@code-developer",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Add validation",
            description="Add input validation and error handling",
            ideal_agent="@code-developer",
            ideal_agent_desc="Full-stack development specialist",
            assigned_agent="@code-developer",
            dependencies=["sg-2"],
        ),
        Subgoal(
            id="sg-4",
            title="Write tests",
            description="Write comprehensive unit and integration tests",
            ideal_agent="@quality-assurance",
            ideal_agent_desc="Quality assurance and testing specialist",
            assigned_agent="@quality-assurance",
            dependencies=["sg-2", "sg-3"],
        ),
    ]


@pytest.fixture
def memory_cache() -> PlanDecompositionCache:
    """In-memory only cache for benchmarking."""
    return PlanDecompositionCache(
        capacity=1000,
        ttl_hours=24,
        persistent_path=None,
        enable_metrics=True,
    )


@pytest.fixture
def persistent_cache() -> PlanDecompositionCache:
    """Persistent cache for benchmarking."""
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "benchmark_cache.db"
        cache = PlanDecompositionCache(
            capacity=1000,
            ttl_hours=24,
            persistent_path=cache_path,
            enable_metrics=True,
        )
        yield cache


def create_test_goals(count: int) -> list[tuple[str, Complexity]]:
    """Create diverse test goals for benchmarking."""
    goals = []
    complexities = [Complexity.SIMPLE, Complexity.MODERATE, Complexity.COMPLEX]

    templates = [
        "Add {feature} to the system",
        "Implement {feature} with proper validation",
        "Create {feature} following best practices",
        "Build {feature} with comprehensive tests",
        "Design and implement {feature}",
    ]

    features = [
        "authentication",
        "caching",
        "logging",
        "monitoring",
        "API endpoint",
        "database migration",
        "file upload",
        "email notification",
        "search",
        "user profile",
        "admin dashboard",
        "reporting",
        "export",
        "import",
    ]

    for i in range(count):
        template = templates[i % len(templates)]
        feature = features[i % len(features)]
        goal = template.format(feature=feature)
        complexity = complexities[i % len(complexities)]
        goals.append((goal, complexity))

    return goals


class TestCacheKeyComputationPerformance:
    """Benchmark cache key computation overhead."""

    def test_key_computation_simple(self, benchmark, memory_cache):
        """Benchmark key computation for simple goal (no context)."""
        goal = "Add authentication to the system"
        complexity = Complexity.MODERATE

        def compute_key():
            return memory_cache._compute_cache_key(goal, complexity, None)

        result = benchmark(compute_key)
        assert len(result) == 32

        # Target: <0.1ms (100 microseconds)
        mean_time_us = benchmark.stats.stats.mean * 1_000_000
        assert (
            benchmark.stats.stats.mean < 0.0001
        ), f"Key computation too slow: {mean_time_us:.1f}μs > 100μs"

    def test_key_computation_with_context(self, benchmark, memory_cache):
        """Benchmark key computation with context files."""
        goal = "Add authentication to the system"
        complexity = Complexity.MODERATE
        context_files = [f"src/module_{i}.py" for i in range(10)]

        def compute_key():
            return memory_cache._compute_cache_key(goal, complexity, context_files)

        result = benchmark(compute_key)
        assert len(result) == 32

        # Target: <0.2ms with context files
        mean_time_us = benchmark.stats.stats.mean * 1_000_000
        assert (
            benchmark.stats.stats.mean < 0.0002
        ), f"Key computation with context too slow: {mean_time_us:.1f}μs > 200μs"


class TestMemoryCacheGetPerformance:
    """Benchmark in-memory cache GET operations."""

    def test_cache_hit_latency(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark latency of memory cache hits."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Pre-populate cache
        memory_cache.set(goal, complexity, sample_subgoals, "soar")

        def cache_get():
            return memory_cache.get(goal, complexity)

        result = benchmark(cache_get)
        assert result is not None

        # Target: <1ms for memory cache hit (99th percentile)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        p99_time_ms = (benchmark.stats.stats.mean + 2 * benchmark.stats.stats.stddev) * 1000

        assert (
            benchmark.stats.stats.mean < 0.001
        ), f"Memory cache hit too slow: {mean_time_ms:.3f}ms > 1ms"
        assert p99_time_ms < 1.0, f"99th percentile too slow: {p99_time_ms:.3f}ms > 1ms"

        print(f"\nMemory cache hit: {mean_time_ms:.3f}ms (p99: {p99_time_ms:.3f}ms, target: <1ms)")

    def test_cache_miss_latency(self, benchmark, memory_cache):
        """Benchmark latency of memory cache misses."""
        goal = "Nonexistent goal"
        complexity = Complexity.MODERATE

        def cache_get():
            return memory_cache.get(goal, complexity)

        result = benchmark(cache_get)
        assert result is None

        # Target: <1ms for memory cache miss
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.001
        ), f"Memory cache miss too slow: {mean_time_ms:.3f}ms > 1ms"

    def test_cache_hit_with_lru_access(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark cache hits that update LRU ordering."""
        # Fill cache with 100 items
        for i in range(100):
            memory_cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        # Benchmark accessing an item (which updates LRU)
        goal = "Goal 50"

        def cache_get_with_lru():
            return memory_cache.get(goal, Complexity.MODERATE)

        result = benchmark(cache_get_with_lru)
        assert result is not None

        # LRU update should still be very fast
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.002
        ), f"Cache hit with LRU update too slow: {mean_time_ms:.3f}ms > 2ms"


class TestMemoryCacheSetPerformance:
    """Benchmark in-memory cache SET operations."""

    def test_cache_set_new_entry(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark adding new entries to cache."""
        goals = create_test_goals(100)
        counter = {"i": 0}

        def cache_set():
            goal, complexity = goals[counter["i"] % len(goals)]
            memory_cache.set(goal, complexity, sample_subgoals, "soar")
            counter["i"] += 1

        benchmark(cache_set)

        # Target: <5ms for cache SET
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.005
        ), f"Memory cache SET too slow: {mean_time_ms:.3f}ms > 5ms"

        print(f"\nMemory cache SET: {mean_time_ms:.3f}ms (target: <5ms)")

    def test_cache_set_with_eviction(self, benchmark, sample_subgoals):
        """Benchmark cache SET operations that trigger evictions."""
        # Small cache to trigger evictions
        cache = PlanDecompositionCache(capacity=50, ttl_hours=24)

        # Pre-fill to capacity
        for i in range(50):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        counter = {"i": 50}

        def cache_set_with_eviction():
            cache.set(f"Goal {counter['i']}", Complexity.MODERATE, sample_subgoals, "soar")
            counter["i"] += 1

        benchmark(cache_set_with_eviction)

        # Eviction should add minimal overhead
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.010
        ), f"Cache SET with eviction too slow: {mean_time_ms:.3f}ms > 10ms"

    def test_cache_update_existing(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark updating existing cache entries."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Pre-populate
        memory_cache.set(goal, complexity, sample_subgoals, "soar")

        def cache_update():
            memory_cache.set(goal, complexity, sample_subgoals, "heuristic")

        benchmark(cache_update)

        # Update should be similar to new entry
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.005
        ), f"Cache update too slow: {mean_time_ms:.3f}ms > 5ms"


class TestPersistentCacheGetPerformance:
    """Benchmark persistent cache GET operations."""

    def test_persistent_hit_cold_cache(self, benchmark, persistent_cache, sample_subgoals):
        """Benchmark persistent cache hits (cold in-memory cache)."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Pre-populate persistent storage
        persistent_cache.set(goal, complexity, sample_subgoals, "soar")

        def cold_cache_get():
            # Clear hot cache before each access
            persistent_cache.clear_hot_cache()
            return persistent_cache.get(goal, complexity)

        result = benchmark(cold_cache_get)
        assert result is not None

        # Target: <5ms for persistent cache hit (cold)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.005
        ), f"Persistent cache hit too slow: {mean_time_ms:.3f}ms > 5ms"

        print(f"\nPersistent cache hit (cold): {mean_time_ms:.3f}ms (target: <5ms)")

    def test_persistent_hit_warm_cache(self, benchmark, persistent_cache, sample_subgoals):
        """Benchmark persistent cache hits after promotion to memory."""
        goal = "Add authentication"
        complexity = Complexity.MODERATE

        # Pre-populate persistent storage
        persistent_cache.set(goal, complexity, sample_subgoals, "soar")

        # First access promotes to memory
        persistent_cache.clear_hot_cache()
        persistent_cache.get(goal, complexity)

        def warm_cache_get():
            return persistent_cache.get(goal, complexity)

        result = benchmark(warm_cache_get)
        assert result is not None

        # After promotion, should be as fast as memory cache
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.001
        ), f"Warm cache hit too slow: {mean_time_ms:.3f}ms > 1ms"


class TestPersistentCacheSetPerformance:
    """Benchmark persistent cache SET operations."""

    def test_persistent_set_latency(self, benchmark, persistent_cache, sample_subgoals):
        """Benchmark SET operations with persistent storage."""
        goals = create_test_goals(100)
        counter = {"i": 0}

        def persistent_set():
            goal, complexity = goals[counter["i"] % len(goals)]
            persistent_cache.set(goal, complexity, sample_subgoals, "soar")
            counter["i"] += 1

        benchmark(persistent_set)

        # Target: <10ms for persistent SET
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.010
        ), f"Persistent cache SET too slow: {mean_time_ms:.3f}ms > 10ms"

        print(f"\nPersistent cache SET: {mean_time_ms:.3f}ms (target: <10ms)")

    def test_bulk_persistent_writes(self, benchmark, persistent_cache, sample_subgoals):
        """Benchmark bulk writes to persistent storage."""
        goals = create_test_goals(100)

        def bulk_write():
            for goal, complexity in goals:
                persistent_cache.set(goal, complexity, sample_subgoals, "soar")

        benchmark(bulk_write)

        # 100 writes should complete in reasonable time
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 1.0
        ), f"Bulk write (100 items) too slow: {mean_time_ms:.1f}ms > 1000ms"

        print(f"\nBulk write (100 items): {mean_time_ms:.1f}ms")


class TestCacheScalabilityPerformance:
    """Benchmark cache performance at scale."""

    def test_cache_performance_at_capacity(self, benchmark, sample_subgoals):
        """Benchmark cache performance when at full capacity."""
        cache = PlanDecompositionCache(capacity=1000, ttl_hours=24)

        # Fill to capacity
        for i in range(1000):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        def access_full_cache():
            # Access middle element (requires LRU traversal)
            return cache.get("Goal 500", Complexity.MODERATE)

        result = benchmark(access_full_cache)
        assert result is not None

        # Should still be fast even at capacity
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.002
        ), f"Full cache access too slow: {mean_time_ms:.3f}ms > 2ms"

    def test_eviction_at_scale(self, benchmark, sample_subgoals):
        """Benchmark eviction performance at large scale."""
        cache = PlanDecompositionCache(capacity=1000, ttl_hours=24)

        # Fill to capacity
        for i in range(1000):
            cache.set(f"Goal {i}", Complexity.MODERATE, sample_subgoals, "soar")

        counter = {"i": 1000}

        def evict_at_scale():
            cache.set(f"Goal {counter['i']}", Complexity.MODERATE, sample_subgoals, "soar")
            counter["i"] += 1

        benchmark(evict_at_scale)

        # Eviction should be efficient even at scale
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.010
        ), f"Eviction at scale too slow: {mean_time_ms:.3f}ms > 10ms"


class TestEndToEndCacheSpeedup:
    """Benchmark end-to-end speedup from caching."""

    def test_decomposition_speedup_ratio(self, memory_cache, sample_subgoals):
        """Measure speedup ratio: cached vs non-cached decomposition.

        This simulates real-world usage where decomposition is expensive.
        """
        goal = "Add authentication system with JWT tokens"
        complexity = Complexity.COMPLEX

        # Simulate expensive decomposition (10ms - realistic SOAR call)
        def simulate_expensive_decomposition():
            time.sleep(0.010)  # 10ms
            return sample_subgoals

        # Measure non-cached time
        start = time.perf_counter()
        result = simulate_expensive_decomposition()
        non_cached_time = time.perf_counter() - start

        # Cache the result
        memory_cache.set(goal, complexity, result, "soar")

        # Measure cached time
        start = time.perf_counter()
        cached_result = memory_cache.get(goal, complexity)
        cached_time = time.perf_counter() - start

        assert cached_result is not None

        # Calculate speedup
        speedup = non_cached_time / cached_time

        # Target: ≥50x speedup (10ms vs <0.2ms)
        assert speedup >= 50.0, f"Cache speedup insufficient: {speedup:.1f}x < 50x"

        print(
            f"\nCache speedup: {speedup:.1f}x (non-cached: {non_cached_time * 1000:.2f}ms, "
            f"cached: {cached_time * 1000:.3f}ms)",
        )

    def test_cache_overhead_on_miss(self, memory_cache):
        """Measure cache overhead when miss occurs."""
        goal = "Nonexistent goal"
        complexity = Complexity.MODERATE

        # Measure cache miss overhead
        start = time.perf_counter()
        result = memory_cache.get(goal, complexity)
        miss_time = time.perf_counter() - start

        assert result is None

        # Cache miss overhead should be negligible (<0.1ms)
        miss_time_ms = miss_time * 1000
        assert miss_time < 0.001, f"Cache miss overhead too high: {miss_time_ms:.3f}ms > 1ms"

        print(f"\nCache miss overhead: {miss_time_ms:.3f}ms (target: <1ms)")


class TestCacheMetricsPerformance:
    """Benchmark cache metrics tracking overhead."""

    def test_metrics_overhead_enabled(self, benchmark, sample_subgoals):
        """Benchmark overhead of metrics tracking when enabled."""
        cache = PlanDecompositionCache(capacity=100, ttl_hours=24, enable_metrics=True)

        # Pre-populate
        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")

        def get_with_metrics():
            return cache.get("Goal 1", Complexity.MODERATE)

        result = benchmark(get_with_metrics)
        assert result is not None

        mean_time_ms = benchmark.stats.stats.mean * 1000

        # Metrics should add minimal overhead
        assert (
            benchmark.stats.stats.mean < 0.002
        ), f"Metrics overhead too high: {mean_time_ms:.3f}ms > 2ms"

    def test_metrics_overhead_disabled(self, benchmark, sample_subgoals):
        """Benchmark performance when metrics are disabled."""
        cache = PlanDecompositionCache(capacity=100, ttl_hours=24, enable_metrics=False)

        # Pre-populate
        cache.set("Goal 1", Complexity.MODERATE, sample_subgoals, "soar")

        def get_without_metrics():
            return cache.get("Goal 1", Complexity.MODERATE)

        result = benchmark(get_without_metrics)
        assert result is not None

        # Should be slightly faster without metrics
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.001
        ), f"Cache without metrics too slow: {mean_time_ms:.3f}ms > 1ms"


class TestCacheSerializationPerformance:
    """Benchmark subgoal serialization/deserialization."""

    def test_subgoal_serialization(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark serialization of subgoals."""

        def serialize():
            return [memory_cache._serialize_subgoal(sg) for sg in sample_subgoals]

        result = benchmark(serialize)
        assert len(result) == len(sample_subgoals)

        # Serialization should be very fast
        mean_time_us = benchmark.stats.stats.mean * 1_000_000
        assert (
            benchmark.stats.stats.mean < 0.001
        ), f"Serialization too slow: {mean_time_us:.1f}μs > 1000μs"

    def test_subgoal_deserialization(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark deserialization of subgoals."""
        serialized = [memory_cache._serialize_subgoal(sg) for sg in sample_subgoals]

        def deserialize():
            return [memory_cache._deserialize_subgoal(sg) for sg in serialized]

        result = benchmark(deserialize)
        assert len(result) == len(sample_subgoals)

        # Deserialization should be very fast
        mean_time_us = benchmark.stats.stats.mean * 1_000_000
        assert (
            benchmark.stats.stats.mean < 0.001
        ), f"Deserialization too slow: {mean_time_us:.1f}μs > 1000μs"


class TestCacheConcurrentAccess:
    """Benchmark cache behavior under concurrent access patterns."""

    def test_alternating_read_write(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark alternating read/write pattern."""
        goals = create_test_goals(10)
        counter = {"i": 0}

        def alternating_access():
            idx = counter["i"] % len(goals)
            goal, complexity = goals[idx]

            if counter["i"] % 2 == 0:
                # Write
                memory_cache.set(goal, complexity, sample_subgoals, "soar")
            else:
                # Read
                memory_cache.get(goal, complexity)

            counter["i"] += 1

        benchmark(alternating_access)

        # Mixed workload should be efficient
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.005
        ), f"Mixed read/write too slow: {mean_time_ms:.3f}ms > 5ms"

    def test_read_heavy_workload(self, benchmark, memory_cache, sample_subgoals):
        """Benchmark read-heavy workload (90% reads, 10% writes)."""
        goals = create_test_goals(10)

        # Pre-populate
        for goal, complexity in goals:
            memory_cache.set(goal, complexity, sample_subgoals, "soar")

        counter = {"i": 0}

        def read_heavy():
            idx = counter["i"] % len(goals)
            goal, complexity = goals[idx]

            if counter["i"] % 10 == 0:
                # 10% writes
                memory_cache.set(goal, complexity, sample_subgoals, "heuristic")
            else:
                # 90% reads
                memory_cache.get(goal, complexity)

            counter["i"] += 1

        benchmark(read_heavy)

        # Read-heavy should be very fast
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.002
        ), f"Read-heavy workload too slow: {mean_time_ms:.3f}ms > 2ms"


class TestCacheComparisonSummary:
    """Generate comparison summary of cache vs non-cached performance."""

    def test_comprehensive_comparison(self, memory_cache, sample_subgoals):
        """Comprehensive comparison of cached vs non-cached operations.

        Generates a performance summary showing:
        - Memory cache hit vs miss
        - Persistent cache hit vs cold start
        - Cache overhead
        - Speedup ratios
        """
        goal = "Add authentication system"
        complexity = Complexity.COMPLEX

        # 1. Memory cache hit
        memory_cache.set(goal, complexity, sample_subgoals, "soar")
        start = time.perf_counter()
        memory_cache.get(goal, complexity)
        memory_hit_time = time.perf_counter() - start

        # 2. Memory cache miss
        start = time.perf_counter()
        memory_cache.get("Nonexistent", complexity)
        memory_miss_time = time.perf_counter() - start

        # 3. Simulated full decomposition
        simulated_decomposition_time = 0.010  # 10ms

        # 4. Calculate metrics
        cache_speedup = simulated_decomposition_time / memory_hit_time
        miss_overhead_pct = (memory_miss_time / simulated_decomposition_time) * 100

        print("\n" + "=" * 60)
        print("CACHE PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"Memory cache hit:          {memory_hit_time * 1000:.3f}ms")
        print(f"Memory cache miss:         {memory_miss_time * 1000:.3f}ms")
        print(f"Full decomposition (sim):  {simulated_decomposition_time * 1000:.1f}ms")
        print(f"Cache speedup:             {cache_speedup:.1f}x")
        print(f"Cache miss overhead:       {miss_overhead_pct:.1f}%")
        print("=" * 60)

        # Verify targets
        assert memory_hit_time < 0.001, "Memory hit target not met"
        assert memory_miss_time < 0.001, "Memory miss target not met"
        assert cache_speedup >= 50.0, f"Speedup target not met: {cache_speedup:.1f}x < 50x"
        assert miss_overhead_pct < 5.0, f"Miss overhead too high: {miss_overhead_pct:.1f}% > 5%"


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "-v", "--benchmark-only"])
