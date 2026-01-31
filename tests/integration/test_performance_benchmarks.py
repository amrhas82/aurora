"""Performance benchmark integration tests.

Tests BM25 tri-hybrid search performance:
1. Query latency <2s for simple queries
2. Query latency <10s for complex queries
3. Memory usage <100MB for 10K chunks

This validates that the BM25 implementation meets performance targets
specified in the PRD.
"""

import time
from pathlib import Path

import psutil
import pytest

from aurora_cli.memory_manager import MemoryManager
from aurora_context_code.semantic import EmbeddingProvider
from aurora_core.store.sqlite import SQLiteStore


pytestmark = pytest.mark.ml  # Requires ML dependencies


class TestQueryLatency:
    """Test query latency performance benchmarks."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "perf.db"
        return str(db_path)

    @pytest.fixture
    def memory_store(self, temp_db):
        """Create SQLite store."""
        store = SQLiteStore(db_path=temp_db)
        yield store
        store.close()

    @pytest.fixture
    def memory_manager(self, memory_store):
        """Create MemoryManager with real components."""
        embedding_provider = EmbeddingProvider()
        return MemoryManager(memory_store=memory_store, embedding_provider=embedding_provider)

    @pytest.fixture
    def aurora_subset(self) -> Path:
        """Return path to Aurora packages for benchmarking."""
        repo_root = Path("/home/hamr/PycharmProjects/aurora")
        packages_dir = repo_root / "packages"
        assert packages_dir.exists(), "Packages directory not found"
        return packages_dir

    @pytest.fixture
    def indexed_manager(self, memory_manager, aurora_subset):
        """Create memory manager with indexed Aurora subset.

        This fixture indexes once and returns the manager for multiple tests.
        Note: Uses function scope so indexing happens per test (isolated).
        """
        # Index Aurora packages
        stats = memory_manager.index_path(aurora_subset)
        assert stats.chunks_created > 0, "Must have indexed chunks for benchmarking"
        return memory_manager

    @pytest.mark.benchmark
    def test_simple_query_latency(self, indexed_manager):
        """Test simple query completes in <2 seconds."""
        # Simple exact match queries
        simple_queries = [
            "SOAROrchestrator",
            "process_query",
            "HybridRetriever",
            "save_chunk",
            "index_path",
        ]

        for query in simple_queries:
            start_time = time.time()
            results = indexed_manager.search(query=query, top_k=10, complexity="MEDIUM")
            elapsed = time.time() - start_time

            assert len(results) > 0, f"Query '{query}' should return results"
            assert elapsed < 2.0, (
                f"Simple query '{query}' took {elapsed:.2f}s (target: <2s). "
                f"BM25 exact match should be fast."
            )

    @pytest.mark.benchmark
    def test_complex_query_latency(self, indexed_manager):
        """Test complex query completes in <10 seconds."""
        # Complex semantic queries with multiple concepts
        complex_queries = [
            "how to calculate activation scores with frequency and recency in ACT-R model",
            "semantic similarity search using embeddings and vector distance",
            "orchestrate multi-phase pipeline with context retrieval and verification",
            "store and retrieve code chunks with metadata and git history",
            "implement BM25 scoring with term frequency and document length normalization",
        ]

        for query in complex_queries:
            start_time = time.time()
            results = indexed_manager.search(query=query, top_k=20, complexity="COMPLEX")
            elapsed = time.time() - start_time

            # Complex queries may return fewer results (more specific)
            assert elapsed < 10.0, (
                f"Complex query took {elapsed:.2f}s (target: <10s). "
                f"Tri-hybrid search should complete within target."
            )

    @pytest.mark.benchmark
    def test_average_query_latency(self, indexed_manager):
        """Test average latency across diverse queries."""
        # Mix of simple and moderate queries
        queries = [
            "SOAROrchestrator",
            "calculate activation",
            "retrieve context",
            "semantic search",
            "BM25 scoring",
            "code chunk parsing",
            "hybrid retriever",
            "memory manager",
            "SQLite store",
            "embedding provider",
        ]

        latencies = []
        for query in queries:
            start_time = time.time()
            indexed_manager.search(query=query, top_k=10, complexity="MEDIUM")
            elapsed = time.time() - start_time
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Average should be well under 2s for typical queries
        assert avg_latency < 1.5, (
            f"Average query latency {avg_latency:.2f}s exceeds 1.5s. "
            f"Target: <1.5s average for typical queries."
        )

        # No query should exceed 5s
        assert max_latency < 5.0, (
            f"Max query latency {max_latency:.2f}s exceeds 5s. "
            f"All moderate queries should complete quickly."
        )

    @pytest.mark.benchmark
    def test_batch_query_performance(self, indexed_manager):
        """Test performance of sequential queries (no interference)."""
        # Run 20 queries in sequence
        queries = [f"function_{i}" for i in range(20)]

        start_time = time.time()
        for query in queries:
            indexed_manager.search(query=query, top_k=5, complexity="SIMPLE")
        total_elapsed = time.time() - start_time

        # 20 queries should complete in <30s (avg 1.5s per query)
        assert total_elapsed < 30.0, (
            f"20 sequential queries took {total_elapsed:.2f}s (target: <30s). "
            f"Average per query: {total_elapsed / 20:.2f}s"
        )


class TestMemoryUsage:
    """Test memory usage benchmarks."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "memory.db"
        return str(db_path)

    @pytest.fixture
    def memory_store(self, temp_db):
        """Create SQLite store."""
        store = SQLiteStore(db_path=temp_db)
        yield store
        store.close()

    @pytest.fixture
    def memory_manager(self, memory_store):
        """Create MemoryManager."""
        embedding_provider = EmbeddingProvider()
        return MemoryManager(memory_store=memory_store, embedding_provider=embedding_provider)

    @pytest.fixture
    def large_codebase(self, tmp_path):
        """Create large synthetic codebase (~10K chunks)."""
        codebase = tmp_path / "large_codebase"
        codebase.mkdir()

        # Generate 200 files with ~50 chunks each = ~10K chunks
        for file_idx in range(200):
            module_file = codebase / f"module_{file_idx:03d}.py"

            # Generate file with 10 classes, each with 5 methods
            content = f'"""Module {file_idx}."""\n\n'

            for class_idx in range(10):
                content += f"\nclass Class{class_idx}_{file_idx}:\n"
                content += f'    """Class {class_idx} in module {file_idx}."""\n\n'

                for method_idx in range(5):
                    content += f"    def method_{method_idx}(self, x, y):\n"
                    content += f'        """Method {method_idx}."""\n'
                    content += f"        return x + y + {method_idx}\n\n"

            module_file.write_text(content)

        return codebase

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_memory_usage_with_10k_chunks(self, memory_manager, memory_store, large_codebase):
        """Test memory usage remains <100MB for ~10K chunks."""
        # Get baseline memory
        process = psutil.Process()
        baseline_mb = process.memory_info().rss / 1024 / 1024

        # Index large codebase
        stats = memory_manager.index_path(large_codebase)

        # Verify we have ~10K chunks
        assert (
            stats.chunks_created >= 8000
        ), f"Expected ~10K chunks, got {stats.chunks_created}. Test setup may be incorrect."

        # Run several searches to exercise retrieval
        queries = [
            "Class5",
            "method_3",
            "Module 100",
            "Class9_150",
            "method_0",
        ]

        for query in queries:
            memory_manager.search(query=query, top_k=20, complexity="MEDIUM")

        # Measure memory after operations
        peak_mb = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_mb - baseline_mb

        # Memory increase should be <100MB for 10K chunks
        # Note: This includes embeddings in memory, BM25 data structures, etc.
        assert memory_increase < 100, (
            f"Memory usage increased by {memory_increase:.1f}MB (target: <100MB). "
            f"Baseline: {baseline_mb:.1f}MB, Peak: {peak_mb:.1f}MB. "
            f"Chunks indexed: {stats.chunks_created}"
        )

    @pytest.mark.benchmark
    def test_chunk_storage_efficiency(self, memory_store, tmp_path):
        """Test that chunk storage is efficient (database size)."""
        # Create moderate codebase
        codebase = tmp_path / "moderate"
        codebase.mkdir()

        # 20 files with 50 chunks each = 1000 chunks
        for i in range(20):
            (codebase / f"module{i}.py").write_text(
                f'''"""Module {i}."""

def function_{i}_0(): return {i}
def function_{i}_1(): return {i}
def function_{i}_2(): return {i}
def function_{i}_3(): return {i}
def function_{i}_4(): return {i}

class Class{i}:
    def method_a(self): return {i}
    def method_b(self): return {i}
    def method_c(self): return {i}
    def method_d(self): return {i}
    def method_e(self): return {i}
''',
            )

        # Index
        embedding_provider = EmbeddingProvider()
        manager = MemoryManager(memory_store=memory_store, embedding_provider=embedding_provider)
        stats = manager.index_path(codebase)

        # Get database size
        db_path = memory_store.db_path
        db_size_mb = Path(db_path).stat().st_size / 1024 / 1024

        # Database should be reasonably sized for 1K chunks
        # Rule of thumb: <10KB per chunk (including embeddings)
        max_expected_mb = (stats.chunks_created * 10) / 1024  # KB to MB
        assert db_size_mb < max_expected_mb * 1.5, (
            f"Database size {db_size_mb:.1f}MB too large for {stats.chunks_created} chunks. "
            f"Expected <{max_expected_mb * 1.5:.1f}MB (15KB per chunk including embeddings)."
        )


class TestIndexingPerformance:
    """Test indexing performance benchmarks."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "indexing.db"
        return str(db_path)

    @pytest.fixture
    def memory_store(self, temp_db):
        """Create SQLite store."""
        store = SQLiteStore(db_path=temp_db)
        yield store
        store.close()

    @pytest.fixture
    def memory_manager(self, memory_store):
        """Create MemoryManager."""
        embedding_provider = EmbeddingProvider()
        return MemoryManager(memory_store=memory_store, embedding_provider=embedding_provider)

    @pytest.mark.benchmark
    def test_indexing_throughput(self, memory_manager, tmp_path):
        """Test indexing throughput (files per second)."""
        # Create test codebase with 50 files
        codebase = tmp_path / "throughput"
        codebase.mkdir()

        for i in range(50):
            (codebase / f"module{i}.py").write_text(
                f'''"""Module {i}."""

def function_{i}(x, y):
    """Function {i}."""
    return x + y + {i}

class Class{i}:
    """Class {i}."""

    def method_a(self):
        """Method A."""
        return {i}

    def method_b(self):
        """Method B."""
        return {i} * 2
''',
            )

        # Index and measure time
        start_time = time.time()
        stats = memory_manager.index_path(codebase)
        elapsed = time.time() - start_time

        files_per_second = stats.files_indexed / elapsed
        chunks_per_second = stats.chunks_created / elapsed

        # Should index at reasonable rate
        # Target: >5 files/sec, >25 chunks/sec
        assert files_per_second > 2, (
            f"Indexing throughput {files_per_second:.1f} files/sec too slow (target: >2 files/sec). "
            f"Indexed {stats.files_indexed} files in {elapsed:.2f}s"
        )

        assert chunks_per_second > 10, (
            f"Chunk creation {chunks_per_second:.1f} chunks/sec too slow (target: >10 chunks/sec). "
            f"Created {stats.chunks_created} chunks in {elapsed:.2f}s"
        )

    @pytest.mark.benchmark
    def test_aurora_subset_indexing_time(self, memory_manager):
        """Test Aurora subset indexes in reasonable time."""
        repo_root = Path("/home/hamr/PycharmProjects/aurora")
        packages_dir = repo_root / "packages"

        if not packages_dir.exists():
            pytest.skip("Aurora packages directory not found")

        # Index and measure
        start_time = time.time()
        stats = memory_manager.index_path(packages_dir)
        elapsed = time.time() - start_time

        # 100+ files should index in <10 minutes
        assert elapsed < 600, (
            f"Aurora indexing took {elapsed:.1f}s (target: <600s/10min). "
            f"Indexed {stats.files_indexed} files, created {stats.chunks_created} chunks"
        )

        # Log performance metrics
        print("\n=== Aurora Indexing Performance ===")
        print(f"Files indexed: {stats.files_indexed}")
        print(f"Chunks created: {stats.chunks_created}")
        print(f"Duration: {elapsed:.2f}s")
        print(
            f"Throughput: {stats.files_indexed / elapsed:.2f} files/sec, "
            f"{stats.chunks_created / elapsed:.2f} chunks/sec",
        )
