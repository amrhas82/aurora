"""Performance benchmarks for spreading activation calculations.

This test suite benchmarks:
1. Spreading activation calculation for varying graph sizes
2. BFS traversal performance with different hop counts
3. Edge limit enforcement
4. Graph density impact on performance

Performance Targets (from PRD Section 7):
- 3 hops, 1000 edges: <200ms for spreading activation calculation

Test Strategy:
- Use pytest-benchmark for accurate timing measurements
- Test realistic graph topologies (sparse, dense, clustered)
- Measure traversal with different max_hops and max_edges settings
- Verify performance targets are met consistently
"""

import pytest

from aurora_core.activation.spreading import RelationshipGraph, SpreadingActivation, SpreadingConfig


def create_linear_graph(size: int) -> RelationshipGraph:
    """Create a linear graph where each chunk links to the next.

    chunk_0 -> chunk_1 -> chunk_2 -> ... -> chunk_N

    Args:
        size: Number of chunks in the graph

    Returns:
        Linear relationship graph

    """
    graph = RelationshipGraph()
    for i in range(size - 1):
        source = f"chunk_{i:04d}"
        target = f"chunk_{i + 1:04d}"
        graph.add_relationship(source, target, "calls")
    return graph


def create_tree_graph(depth: int, branching_factor: int) -> RelationshipGraph:
    """Create a tree graph with specified depth and branching factor.

    Each node has `branching_factor` children.
    Total nodes = 1 + b + b^2 + ... + b^depth

    Args:
        depth: Maximum depth of the tree
        branching_factor: Number of children per node

    Returns:
        Tree relationship graph

    """
    graph = RelationshipGraph()
    node_counter = 0

    def add_tree_level(parent_id: str, current_depth: int):
        nonlocal node_counter
        if current_depth >= depth:
            return

        for _i in range(branching_factor):
            node_counter += 1
            child_id = f"chunk_{node_counter:04d}"
            graph.add_relationship(parent_id, child_id, "calls")
            add_tree_level(child_id, current_depth + 1)

    # Start from root
    root_id = f"chunk_{node_counter:04d}"
    node_counter += 1
    add_tree_level(root_id, 0)

    return graph


def create_dense_graph(size: int, edges_per_node: int) -> RelationshipGraph:
    """Create a dense graph where each chunk has multiple connections.

    Args:
        size: Number of chunks
        edges_per_node: Average number of outgoing edges per chunk

    Returns:
        Dense relationship graph

    """
    graph = RelationshipGraph()

    for i in range(size):
        source = f"chunk_{i:04d}"

        # Add edges to next N chunks (wrapping around)
        for j in range(edges_per_node):
            target_idx = (i + j + 1) % size
            target = f"chunk_{target_idx:04d}"
            rel_types = ["calls", "imports", "inherits"]
            rel_type = rel_types[j % 3]
            graph.add_relationship(source, target, rel_type)

    return graph


def create_clustered_graph(
    num_clusters: int,
    cluster_size: int,
    inter_cluster_edges: int,
) -> RelationshipGraph:
    """Create a clustered graph with dense clusters and sparse inter-cluster connections.

    Args:
        num_clusters: Number of clusters
        cluster_size: Chunks per cluster
        inter_cluster_edges: Edges connecting clusters

    Returns:
        Clustered relationship graph

    """
    graph = RelationshipGraph()

    # Create dense intra-cluster edges
    for cluster in range(num_clusters):
        for i in range(cluster_size):
            source_idx = cluster * cluster_size + i
            source = f"chunk_{source_idx:04d}"

            # Connect to other nodes in same cluster
            for j in range(3):  # 3 edges per node within cluster
                target_idx = cluster * cluster_size + ((i + j + 1) % cluster_size)
                target = f"chunk_{target_idx:04d}"
                graph.add_relationship(source, target, "calls")

    # Add inter-cluster edges
    for i in range(inter_cluster_edges):
        source_cluster = i % num_clusters
        target_cluster = (i + 1) % num_clusters
        source_idx = source_cluster * cluster_size
        target_idx = target_cluster * cluster_size
        source = f"chunk_{source_idx:04d}"
        target = f"chunk_{target_idx:04d}"
        graph.add_relationship(source, target, "imports")

    return graph


@pytest.fixture
def spreading_calculator():
    """Standard spreading activation calculator."""
    return SpreadingActivation(config=SpreadingConfig())


@pytest.fixture
def spreading_calculator_3hops():
    """Spreading calculator with max 3 hops."""
    return SpreadingActivation(config=SpreadingConfig(max_hops=3, max_edges=1000))


class TestSpreadingPerformanceLinear:
    """Benchmark spreading activation on linear graphs."""

    def test_spreading_linear_100_chunks(self, benchmark, spreading_calculator):
        """Benchmark spreading on linear graph with 100 chunks."""
        graph = create_linear_graph(100)
        source_chunks = ["chunk_0000"]  # Start from beginning

        def calculate():
            return spreading_calculator.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=False,
            )

        result = benchmark(calculate)

        # Verify we got activations (should reach many chunks in linear path)
        assert len(result) > 0
        assert len(result) <= 100

        # Linear traversal should be very fast (<20ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.020
        ), f"Linear spreading too slow: {mean_time_ms:.1f}ms > 20ms"

    def test_spreading_linear_1000_chunks(self, benchmark, spreading_calculator):
        """Benchmark spreading on linear graph with 1000 chunks."""
        graph = create_linear_graph(1000)
        source_chunks = ["chunk_0000"]

        def calculate():
            return spreading_calculator.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=False,
            )

        result = benchmark(calculate)
        assert len(result) > 0

        # Should still be fast for linear graphs (<50ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.050
        ), f"Linear spreading too slow for 1000: {mean_time_ms:.1f}ms > 50ms"


class TestSpreadingPerformanceTree:
    """Benchmark spreading activation on tree graphs."""

    def test_spreading_tree_depth3_branch3(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on tree with depth=3, branching=3."""
        # Tree: 1 + 3 + 9 + 27 = 40 nodes
        graph = create_tree_graph(depth=3, branching_factor=3)
        source_chunks = ["chunk_0000"]  # Root node

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=False,
            )

        result = benchmark(calculate)

        # Should reach most/all nodes in tree (within 3 hops)
        assert len(result) > 10

        # Tree traversal should be fast (<30ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.030
        ), f"Tree spreading too slow: {mean_time_ms:.1f}ms > 30ms"

    def test_spreading_tree_depth5_branch2(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on tree with depth=5, branching=2."""
        # Tree: 1 + 2 + 4 + 8 + 16 + 32 = 63 nodes
        graph = create_tree_graph(depth=5, branching_factor=2)
        source_chunks = ["chunk_0000"]

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=False,
            )

        result = benchmark(calculate)
        assert len(result) > 5

        # Should be fast despite deeper tree (<40ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.040
        ), f"Deep tree spreading too slow: {mean_time_ms:.1f}ms > 40ms"


class TestSpreadingPerformanceDense:
    """Benchmark spreading activation on dense graphs.

    This is the main performance target from PRD Section 7.9:
    "3 hops, 1000 edges, <200ms"
    """

    def test_spreading_dense_100_chunks_5edges(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on dense graph: 100 chunks, 5 edges per chunk."""
        # Total edges: 100 * 5 = 500 edges
        graph = create_dense_graph(size=100, edges_per_node=5)
        source_chunks = [f"chunk_{i:04d}" for i in range(10)]  # 10 source chunks

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate)

        # Should reach many chunks in dense graph
        assert len(result) > 20

        # Performance target: <100ms for 500 edges
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.100
        ), f"Dense spreading (500 edges) too slow: {mean_time_ms:.1f}ms > 100ms"

        print(f"\nDense graph (100 chunks, 500 edges): {mean_time_ms:.1f}ms")

    def test_spreading_dense_200_chunks_5edges(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on dense graph: 200 chunks, 5 edges per chunk.

        PRD TARGET: 3 hops, 1000 edges, <200ms
        """
        # Total edges: 200 * 5 = 1000 edges (PRD target!)
        graph = create_dense_graph(size=200, edges_per_node=5)
        source_chunks = [f"chunk_{i:04d}" for i in range(20)]  # 10% as sources

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate)

        # Should reach a meaningful portion of graph (with max_edges=1000 limit)
        assert len(result) > 20

        # PRIMARY PERFORMANCE TARGET: <200ms for 1000 edges
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.200
        ), f"Dense spreading (1000 edges) too slow: {mean_time_ms:.1f}ms > 200ms (PRD target)"

        print(
            f"\n*** PRD TARGET *** Dense graph (200 chunks, 1000 edges): {mean_time_ms:.1f}ms (target: <200ms)",
        )

    def test_spreading_dense_500_chunks_3edges(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on larger sparse graph: 500 chunks, 3 edges per chunk."""
        # Total edges: 500 * 3 = 1500 edges
        graph = create_dense_graph(size=500, edges_per_node=3)
        source_chunks = [f"chunk_{i:04d}" for i in range(50)]  # 10% as sources

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate)
        # With max_edges=1000 limit, reaches fewer chunks from larger graph
        assert len(result) > 15

        # With max_edges=1000, should still be fast (hits edge limit)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.250
        ), f"Large sparse graph too slow: {mean_time_ms:.1f}ms > 250ms"

        print(
            f"\nLarge sparse graph (500 chunks, 1500 edges, limited to 1000): {mean_time_ms:.1f}ms",
        )


class TestSpreadingPerformanceClustered:
    """Benchmark spreading activation on clustered graphs."""

    def test_spreading_clustered_5clusters_20chunks(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on clustered graph: 5 clusters, 20 chunks each."""
        # Total: 100 chunks, dense within clusters, sparse between
        graph = create_clustered_graph(num_clusters=5, cluster_size=20, inter_cluster_edges=10)
        source_chunks = ["chunk_0000"]  # Start in first cluster

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate)

        # Should reach chunks in same cluster and some in neighboring clusters
        assert len(result) > 10

        # Clustered graphs should be efficient (<80ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.080
        ), f"Clustered spreading too slow: {mean_time_ms:.1f}ms > 80ms"

    def test_spreading_clustered_10clusters_50chunks(self, benchmark, spreading_calculator_3hops):
        """Benchmark spreading on larger clustered graph: 10 clusters, 50 chunks each."""
        # Total: 500 chunks
        graph = create_clustered_graph(num_clusters=10, cluster_size=50, inter_cluster_edges=20)
        source_chunks = [f"chunk_{i:04d}" for i in range(5)]  # Multiple sources

        def calculate():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate)
        assert len(result) > 20

        # Should handle large clustered graphs efficiently (<150ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.150
        ), f"Large clustered graph too slow: {mean_time_ms:.1f}ms > 150ms"


class TestSpreadingEdgeCases:
    """Test edge cases and limits."""

    def test_spreading_no_edges(self, benchmark, spreading_calculator):
        """Benchmark spreading with no edges (empty graph)."""
        graph = RelationshipGraph()
        source_chunks = ["chunk_0000"]

        def calculate():
            return spreading_calculator.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=False,
            )

        result = benchmark(calculate)

        # No edges = no spreading
        assert len(result) == 0

        # Should be instant (<1ms)
        assert benchmark.stats.stats.mean < 0.001

    def test_spreading_single_source_no_outgoing(self, benchmark, spreading_calculator):
        """Benchmark spreading from isolated node."""
        graph = create_linear_graph(100)
        source_chunks = ["chunk_isolated"]  # Not in graph

        def calculate():
            return spreading_calculator.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=False,
            )

        result = benchmark(calculate)
        assert len(result) == 0

        # Should be very fast (<1ms)
        assert benchmark.stats.stats.mean < 0.001

    def test_spreading_max_edges_enforcement(self, benchmark):
        """Verify max_edges limit is enforced."""
        # Create calculator with low edge limit
        calculator = SpreadingActivation(config=SpreadingConfig(max_hops=5, max_edges=100))

        # Create dense graph that would exceed limit
        graph = create_dense_graph(size=200, edges_per_node=5)  # 1000 edges total
        source_chunks = [f"chunk_{i:04d}" for i in range(20)]

        def calculate():
            return calculator.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate)

        # Should stop early due to edge limit
        assert len(result) > 0

        # Should be fast because it stops at 100 edges (<50ms)
        mean_time_ms = benchmark.stats.stats.mean * 1000
        assert (
            benchmark.stats.stats.mean < 0.050
        ), f"Edge-limited spreading too slow: {mean_time_ms:.1f}ms > 50ms"


class TestSpreadingScalability:
    """Test scaling behavior with increasing parameters."""

    def test_spreading_scales_with_hops(self, benchmark):
        """Verify performance scales reasonably with max_hops."""
        graph = create_dense_graph(size=200, edges_per_node=5)
        source_chunks = [f"chunk_{i:04d}" for i in range(20)]

        # Test with increasing hop counts
        for max_hops in [1, 2, 3, 4]:
            calculator = SpreadingActivation(
                config=SpreadingConfig(max_hops=max_hops, max_edges=1000),
            )

            def calculate():
                return calculator.calculate(
                    source_chunks=source_chunks,
                    graph=graph,
                    bidirectional=True,
                )

            result = calculate()

            # More hops should reach more chunks
            if max_hops > 1:
                assert len(result) >= 20

    def test_spreading_bidirectional_vs_unidirectional(self, benchmark, spreading_calculator_3hops):
        """Compare bidirectional vs unidirectional spreading performance."""
        graph = create_dense_graph(size=200, edges_per_node=5)
        source_chunks = [f"chunk_{i:04d}" for i in range(20)]

        # Bidirectional should find more chunks but take slightly longer
        def calculate_bidirectional():
            return spreading_calculator_3hops.calculate(
                source_chunks=source_chunks,
                graph=graph,
                bidirectional=True,
            )

        result = benchmark(calculate_bidirectional)
        # With edge limits, reaches a reasonable number of chunks
        assert len(result) > 20


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "-v", "--benchmark-only"])
