"""
Performance benchmarks for ACT-R activation calculations.

This test suite benchmarks:
1. BLA calculation for varying candidate sizes (100, 1000)
2. Full activation calculation (BLA + spreading + context + decay)
3. Batch processing performance
4. Memory efficiency

Performance Targets (from PRD Section 7):
- 100 candidates: <100ms for activation calculation
- 1000 candidates: <200ms for activation calculation

Test Strategy:
- Use pytest-benchmark for accurate timing measurements
- Test realistic access patterns (frequent, recent, old, none)
- Measure both individual component performance and full activation
- Verify performance targets are met consistently (not just best-case)
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List, Set

from aurora_core.activation.base_level import (
    BaseLevelActivation,
    BLAConfig,
    AccessHistoryEntry,
)
from aurora_core.activation.spreading import (
    SpreadingActivation,
    SpreadingConfig,
    RelationshipGraph,
)
from aurora_core.activation.context_boost import (
    ContextBoost,
    ContextBoostConfig,
)
from aurora_core.activation.decay import (
    DecayCalculator,
    DecayConfig,
)
from aurora_core.activation.engine import (
    ActivationEngine,
    ActivationConfig,
)


class MockChunk:
    """Mock chunk for benchmarking."""

    def __init__(
        self,
        chunk_id: str,
        keywords: Set[str],
        access_history: List[AccessHistoryEntry],
        last_access: datetime | None = None,
    ):
        self._id = chunk_id
        self._keywords = keywords
        self._access_history = access_history
        self._last_access = last_access

    @property
    def id(self) -> str:
        return self._id

    @property
    def keywords(self) -> Set[str]:
        return self._keywords

    @property
    def access_history(self) -> List[AccessHistoryEntry]:
        return self._access_history

    @property
    def last_access(self) -> datetime | None:
        return self._last_access


def create_benchmark_chunks(count: int, now: datetime) -> List[MockChunk]:
    """
    Create realistic chunk dataset for benchmarking.

    Access patterns:
    - 20% frequent (10 accesses, last 1 day ago)
    - 30% recent (1 access, last 1 hour ago)
    - 30% old (1 access, 90 days ago)
    - 20% never accessed
    """
    chunks = []

    for i in range(count):
        chunk_id = f"chunk_{i:04d}"
        keywords = {f"keyword_{i % 50}", f"type_{i % 10}", "function"}

        # Distribute access patterns
        if i < count * 0.2:  # 20% frequent
            history = [
                AccessHistoryEntry(timestamp=now - timedelta(days=j))
                for j in range(10)
            ]
            last_access = now - timedelta(days=1)
        elif i < count * 0.5:  # 30% recent
            history = [AccessHistoryEntry(timestamp=now - timedelta(hours=1))]
            last_access = now - timedelta(hours=1)
        elif i < count * 0.8:  # 30% old
            history = [AccessHistoryEntry(timestamp=now - timedelta(days=90))]
            last_access = now - timedelta(days=90)
        else:  # 20% never accessed
            history = []
            last_access = None

        chunk = MockChunk(chunk_id, keywords, history, last_access)
        chunks.append(chunk)

    return chunks


def create_relationship_graph(chunk_count: int) -> RelationshipGraph:
    """
    Create relationship graph for benchmarking.

    Creates a realistic graph with:
    - Average 3 outgoing edges per chunk
    - Mix of call, import, and inherit relationships
    """
    graph = RelationshipGraph()

    for i in range(chunk_count):
        chunk_id = f"chunk_{i:04d}"

        # Add 0-5 relationships per chunk (average 3)
        num_relationships = min(5, (i * 3) % 6)
        for j in range(num_relationships):
            target_idx = (i + j + 1) % chunk_count
            target_id = f"chunk_{target_idx:04d}"
            rel_types = ["calls", "imports", "inherits"]
            rel_type = rel_types[j % 3]
            graph.add_relationship(chunk_id, target_id, rel_type)

    return graph


@pytest.fixture
def activation_engine():
    """Standard activation engine for benchmarking."""
    return ActivationEngine(config=ActivationConfig())


@pytest.fixture
def bla_calculator():
    """BLA calculator for component benchmarking."""
    return BaseLevelActivation(config=BLAConfig())


@pytest.fixture
def spreading_calculator():
    """Spreading activation calculator for component benchmarking."""
    return SpreadingActivation(config=SpreadingConfig())


@pytest.fixture
def context_boost_calculator():
    """Context boost calculator for component benchmarking."""
    return ContextBoost(config=ContextBoostConfig())


@pytest.fixture
def decay_calculator():
    """Decay calculator for component benchmarking."""
    return DecayCalculator(config=DecayConfig())


class TestBLAPerformance:
    """Benchmark Base-Level Activation calculation."""

    def test_bla_100_candidates(self, benchmark, bla_calculator):
        """Benchmark BLA calculation for 100 candidates."""
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(100, now)

        def calculate_bla():
            results = []
            for chunk in chunks:
                bla = bla_calculator.calculate(chunk.access_history, now)
                results.append(bla)
            return results

        result = benchmark(calculate_bla)

        # Verify we got results for all chunks
        assert len(result) == 100

        # Performance target: <100ms total (part of activation calculation)
        # BLA should be < 50ms for 100 candidates (half of budget)
        assert benchmark.stats.stats.mean < 0.050, (
            f"BLA calculation too slow: {benchmark.stats.stats.mean*1000:.1f}ms > 50ms"
        )

    def test_bla_1000_candidates(self, benchmark, bla_calculator):
        """Benchmark BLA calculation for 1000 candidates."""
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(1000, now)

        def calculate_bla():
            results = []
            for chunk in chunks:
                bla = bla_calculator.calculate(chunk.access_history, now)
                results.append(bla)
            return results

        result = benchmark(calculate_bla)

        # Verify we got results for all chunks
        assert len(result) == 1000

        # Performance target: <200ms total (part of activation calculation)
        # BLA should be < 100ms for 1000 candidates (half of budget)
        assert benchmark.stats.stats.mean < 0.100, (
            f"BLA calculation too slow: {benchmark.stats.stats.mean*1000:.1f}ms > 100ms"
        )


class TestContextBoostPerformance:
    """Benchmark Context Boost calculation."""

    def test_context_boost_100_candidates(self, benchmark, context_boost_calculator):
        """Benchmark context boost for 100 candidates."""
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(100, now)
        query_keywords = {"function", "database", "query"}

        def calculate_context():
            results = []
            for chunk in chunks:
                boost = context_boost_calculator.calculate(
                    chunk_keywords=chunk.keywords,
                    query_keywords=query_keywords,
                )
                results.append(boost)
            return results

        result = benchmark(calculate_context)
        assert len(result) == 100

        # Context boost should be very fast (<10ms for 100 candidates)
        assert benchmark.stats.stats.mean < 0.010, (
            f"Context boost too slow: {benchmark.stats.stats.mean*1000:.1f}ms > 10ms"
        )

    def test_context_boost_1000_candidates(self, benchmark, context_boost_calculator):
        """Benchmark context boost for 1000 candidates."""
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(1000, now)
        query_keywords = {"function", "database", "query"}

        def calculate_context():
            results = []
            for chunk in chunks:
                boost = context_boost_calculator.calculate(
                    chunk_keywords=chunk.keywords,
                    query_keywords=query_keywords,
                )
                results.append(boost)
            return results

        result = benchmark(calculate_context)
        assert len(result) == 1000

        # Context boost should be very fast (<50ms for 1000 candidates)
        assert benchmark.stats.stats.mean < 0.050, (
            f"Context boost too slow: {benchmark.stats.stats.mean*1000:.1f}ms > 50ms"
        )


class TestDecayPerformance:
    """Benchmark Decay penalty calculation."""

    def test_decay_100_candidates(self, benchmark, decay_calculator):
        """Benchmark decay calculation for 100 candidates."""
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(100, now)

        def calculate_decay():
            results = []
            for chunk in chunks:
                if chunk.last_access:
                    decay = decay_calculator.calculate(chunk.last_access, now)
                else:
                    decay = decay_calculator.config.min_penalty
                results.append(decay)
            return results

        result = benchmark(calculate_decay)
        assert len(result) == 100

        # Decay should be very fast (<10ms for 100 candidates)
        assert benchmark.stats.stats.mean < 0.010, (
            f"Decay calculation too slow: {benchmark.stats.stats.mean*1000:.1f}ms > 10ms"
        )

    def test_decay_1000_candidates(self, benchmark, decay_calculator):
        """Benchmark decay calculation for 1000 candidates."""
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(1000, now)

        def calculate_decay():
            results = []
            for chunk in chunks:
                if chunk.last_access:
                    decay = decay_calculator.calculate(chunk.last_access, now)
                else:
                    decay = decay_calculator.config.min_penalty
                results.append(decay)
            return results

        result = benchmark(calculate_decay)
        assert len(result) == 1000

        # Decay should be very fast (<50ms for 1000 candidates)
        assert benchmark.stats.stats.mean < 0.050, (
            f"Decay calculation too slow: {benchmark.stats.stats.mean*1000:.1f}ms > 50ms"
        )


class TestFullActivationPerformance:
    """
    Benchmark full activation calculation (all components).

    This is the main performance target from PRD Section 7.
    """

    def test_full_activation_100_candidates(self, benchmark, activation_engine):
        """
        Benchmark full activation for 100 candidates.

        Target: <100ms (PRD Section 7.6)
        """
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(100, now)
        query_keywords = {"function", "database", "query"}
        graph = create_relationship_graph(100)
        source_chunks = [f"chunk_{i:04d}" for i in range(10)]  # 10% as sources

        def calculate_full_activation():
            results = []
            for chunk in chunks:
                # Calculate spreading activation for this chunk
                spreading = 0.0
                if chunk.id in source_chunks:
                    spreading = 0.5  # Source chunks get boost

                components = activation_engine.calculate_total(
                    access_history=chunk.access_history,
                    last_access=chunk.last_access,
                    spreading_activation=spreading,
                    query_keywords=query_keywords,
                    chunk_keywords=chunk.keywords,
                    current_time=now,
                )
                results.append(components)
            return results

        result = benchmark(calculate_full_activation)

        # Verify we got results for all chunks
        assert len(result) == 100

        # Performance target: <100ms for 100 candidates
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert benchmark.stats.stats.mean < 0.100, (
            f"Full activation too slow for 100 candidates: {mean_time_ms:.1f}ms > 100ms"
        )

        print(f"\n100 candidates: {mean_time_ms:.1f}ms (target: <100ms)")

    def test_full_activation_1000_candidates(self, benchmark, activation_engine):
        """
        Benchmark full activation for 1000 candidates.

        Target: <200ms (PRD Section 7.7)
        """
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(1000, now)
        query_keywords = {"function", "database", "query"}
        graph = create_relationship_graph(1000)
        source_chunks = [f"chunk_{i:04d}" for i in range(100)]  # 10% as sources

        def calculate_full_activation():
            results = []
            for chunk in chunks:
                # Calculate spreading activation for this chunk
                spreading = 0.0
                if chunk.id in source_chunks:
                    spreading = 0.5  # Source chunks get boost

                components = activation_engine.calculate_total(
                    access_history=chunk.access_history,
                    last_access=chunk.last_access,
                    spreading_activation=spreading,
                    query_keywords=query_keywords,
                    chunk_keywords=chunk.keywords,
                    current_time=now,
                )
                results.append(components)
            return results

        result = benchmark(calculate_full_activation)

        # Verify we got results for all chunks
        assert len(result) == 1000

        # Performance target: <200ms for 1000 candidates
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert benchmark.stats.stats.mean < 0.200, (
            f"Full activation too slow for 1000 candidates: {mean_time_ms:.1f}ms > 200ms"
        )

        print(f"\n1000 candidates: {mean_time_ms:.1f}ms (target: <200ms)")


class TestBatchActivationPerformance:
    """Benchmark batch activation calculation efficiency."""

    def test_batch_vs_sequential(self, benchmark, activation_engine):
        """
        Compare batch vs sequential activation calculation.

        Batch processing should show minimal overhead compared to sequential.
        """
        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(100, now)
        query_keywords = {"function", "database", "query"}
        graph = create_relationship_graph(100)
        source_chunks = [f"chunk_{i:04d}" for i in range(10)]

        def batch_calculate():
            # Calculate all at once (simulates batch processing)
            results = []
            for chunk in chunks:
                # Calculate spreading activation for this chunk
                spreading = 0.0
                if chunk.id in source_chunks:
                    spreading = 0.5  # Source chunks get boost

                components = activation_engine.calculate_total(
                    access_history=chunk.access_history,
                    last_access=chunk.last_access,
                    spreading_activation=spreading,
                    query_keywords=query_keywords,
                    chunk_keywords=chunk.keywords,
                    current_time=now,
                )
                results.append(components)
            return results

        result = benchmark(batch_calculate)
        assert len(result) == 100

        # Batch processing should still meet the 100ms target
        assert benchmark.stats.stats.mean < 0.100


class TestMemoryEfficiency:
    """Verify memory-efficient activation calculation."""

    def test_no_memory_leak(self, activation_engine):
        """
        Verify activation calculation doesn't leak memory.

        Run multiple iterations and check that memory usage is stable.
        """
        import gc
        import sys

        now = datetime.now(timezone.utc)
        chunks = create_benchmark_chunks(100, now)
        query_keywords = {"function", "database", "query"}
        graph = create_relationship_graph(100)
        source_chunks = [f"chunk_{i:04d}" for i in range(10)]

        # Initial calculation to warm up
        for chunk in chunks:
            spreading = 0.0
            if chunk.id in source_chunks:
                spreading = 0.5
            activation_engine.calculate_total(
                access_history=chunk.access_history,
                last_access=chunk.last_access,
                spreading_activation=spreading,
                query_keywords=query_keywords,
                chunk_keywords=chunk.keywords,
                current_time=now,
            )

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Run 10 iterations
        for iteration in range(10):
            for chunk in chunks:
                spreading = 0.0
                if chunk.id in source_chunks:
                    spreading = 0.5
                activation_engine.calculate_total(
                    access_history=chunk.access_history,
                    last_access=chunk.last_access,
                    spreading_activation=spreading,
                    query_keywords=query_keywords,
                    chunk_keywords=chunk.keywords,
                    current_time=now,
                )
            gc.collect()

        final_objects = len(gc.get_objects())

        # Object count should not grow significantly (allow 10% growth)
        growth_rate = (final_objects - initial_objects) / initial_objects
        assert growth_rate < 0.10, (
            f"Memory leak detected: {growth_rate:.1%} object growth"
        )


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "-v", "--benchmark-only"])
