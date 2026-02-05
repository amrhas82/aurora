#!/usr/bin/env python3
"""Example demonstrating cache metrics and observability features."""

import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from aurora_cli.planning.cache import PlanDecompositionCache
from aurora_cli.planning.models import Complexity, Subgoal


# Configure logging to see cache operations
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)


def create_sample_subgoals() -> list[Subgoal]:
    """Create sample subgoals for demonstration."""
    return [
        Subgoal(
            id="sg-1",
            title="Design approach",
            description="Design the solution architecture",
            ideal_agent="@system-architect",
            ideal_agent_desc="Architecture specialist",
            assigned_agent="@system-architect",
            dependencies=[],
        ),
        Subgoal(
            id="sg-2",
            title="Implement solution",
            description="Implement the designed solution",
            ideal_agent="@code-developer",
            ideal_agent_desc="Full-stack developer",
            assigned_agent="@code-developer",
            dependencies=["sg-1"],
        ),
    ]


def demonstrate_metrics():
    """Demonstrate cache metrics and logging."""
    print("=" * 70)
    print("Cache Metrics and Observability Demonstration")
    print("=" * 70)
    print()

    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "demo_cache.db"

        # Create cache with metrics enabled
        print("Creating cache with metrics enabled...")
        cache = PlanDecompositionCache(
            capacity=5,
            ttl_hours=24,
            persistent_path=cache_path,
            enable_metrics=True,
        )
        print()

        subgoals = create_sample_subgoals()

        # Demonstrate cache misses
        print("1. Cache Misses")
        print("-" * 70)
        for i in range(3):
            goal = f"Add feature {i}"
            result = cache.get(goal, Complexity.MODERATE)
            print(f"  GET '{goal}': {'HIT' if result else 'MISS'}")
        print()

        # Cache some entries
        print("2. Populating Cache")
        print("-" * 70)
        for i in range(3):
            goal = f"Add feature {i}"
            cache.set(goal, Complexity.MODERATE, subgoals, "soar")
            print(f"  SET '{goal}'")
        print()

        # Demonstrate cache hits
        print("3. Cache Hits")
        print("-" * 70)
        for i in range(3):
            goal = f"Add feature {i}"
            result = cache.get(goal, Complexity.MODERATE)
            print(f"  GET '{goal}': {'HIT' if result else 'MISS'}")
        print()

        # Show initial statistics
        print("4. Initial Statistics")
        print("-" * 70)
        stats = cache.get_stats()
        print(f"  Cache size: {stats['size']}/{stats['capacity']}")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']:.1%}")
        print(f"  Memory hits: {stats['memory_hits']}")
        print(f"  Persistent hits: {stats['persistent_hits']}")
        print(f"  Avg GET latency: {stats['avg_get_latency_ms']:.3f}ms")
        print(f"  Max GET latency: {stats['max_get_latency_ms']:.3f}ms")
        print(f"  Avg SET latency: {stats['avg_set_latency_ms']:.3f}ms")
        print()

        # Demonstrate eviction
        print("5. Cache Eviction (LRU)")
        print("-" * 70)
        print("  Filling cache to capacity (5 entries)...")
        for i in range(3, 5):
            goal = f"Add feature {i}"
            cache.set(goal, Complexity.MODERATE, subgoals, "soar")
            print(f"  SET '{goal}'")
        print()
        print("  Adding one more to trigger eviction...")
        cache.set("Add feature 5", Complexity.MODERATE, subgoals, "soar")
        print()
        stats = cache.get_stats()
        print(f"  Evictions: {stats['evictions']}")
        print()

        # Demonstrate persistent cache hits
        print("6. Persistent Cache Hits")
        print("-" * 70)
        print("  Clearing in-memory cache...")
        cache.clear_hot_cache()
        print("  Accessing previously cached entry...")
        result = cache.get("Add feature 1", Complexity.MODERATE)
        print(f"  GET 'Add feature 1': {'HIT' if result else 'MISS'} (from persistent)")
        print()
        stats = cache.get_stats()
        print(f"  Memory hits: {stats['memory_hits']}")
        print(f"  Persistent hits: {stats['persistent_hits']}")
        print()

        # Final performance summary
        print("7. Performance Summary")
        print("-" * 70)
        cache.log_performance_summary()
        print()
        stats = cache.get_stats()
        print(f"  Total operations: {stats['total_operations']}")
        print(f"  Overall hit rate: {stats['hit_rate']:.1%}")
        print(f"  Memory hit rate: {stats['memory_hit_rate']:.1%}")
        print(f"  Persistent hit rate: {stats['persistent_hit_rate']:.1%}")
        print()

        # Demonstrate metrics object
        print("8. Detailed Metrics Object")
        print("-" * 70)
        metrics = cache.get_metrics()
        print(f"  Hits: {metrics.hits}")
        print(f"  Misses: {metrics.misses}")
        print(f"  Expired hits: {metrics.expired_hits}")
        print(f"  Evictions: {metrics.evictions}")
        print(f"  Write operations: {metrics.write_operations}")
        print(f"  Hit rate: {metrics.hit_rate:.1%}")
        print()

        print("=" * 70)
        print("Demonstration Complete")
        print("=" * 70)


if __name__ == "__main__":
    demonstrate_metrics()
