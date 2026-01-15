"""Performance benchmarks for storage layer.

These benchmarks verify that storage operations meet the required
performance targets specified in the PRD:
- Write operations: < 50ms
- Read operations: < 50ms
- Cold start: < 200ms
"""

import time

import pytest

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.store.memory import MemoryStore
from aurora_core.store.sqlite import SQLiteStore
from aurora_core.types import ChunkID

# Performance targets from PRD
WRITE_TARGET_MS = 50
READ_TARGET_MS = 50
COLD_START_TARGET_MS = 200


def measure_time_ms(func):
    """Decorator to measure execution time in milliseconds."""

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        return result, elapsed_ms

    return wrapper


class TestStoragePerformance:
    """Performance benchmarks for storage operations."""

    @pytest.fixture
    def memory_store(self):
        """Create a MemoryStore for benchmarking."""
        store = MemoryStore()
        yield store
        store.close()

    @pytest.fixture
    def sqlite_store(self, tmp_path):
        """Create a SQLiteStore for benchmarking."""
        db_path = tmp_path / "benchmark.db"
        store = SQLiteStore(db_path=str(db_path))
        yield store
        store.close()

    @pytest.fixture
    def sample_chunks(self) -> list[CodeChunk]:
        """Create sample chunks for benchmarking."""
        return [
            CodeChunk(
                chunk_id=f"test:chunk:{i}",
                file_path="/test/benchmark.py",
                element_type="function",
                name=f"func_{i}",
                line_start=(i * 10) + 1,  # line_start must be > 0
                line_end=(i * 10) + 5,
            )
            for i in range(100)
        ]

    def test_memory_store_write_performance(self, memory_store, sample_chunks):
        """Benchmark MemoryStore write performance."""
        chunk = sample_chunks[0]

        @measure_time_ms
        def write_chunk():
            return memory_store.save_chunk(chunk)

        result, elapsed_ms = write_chunk()
        print(f"\nMemoryStore write: {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < WRITE_TARGET_MS
        ), f"MemoryStore write took {elapsed_ms:.2f}ms, target is {WRITE_TARGET_MS}ms"

    def test_memory_store_read_performance(self, memory_store, sample_chunks):
        """Benchmark MemoryStore read performance."""
        chunk = sample_chunks[0]
        memory_store.save_chunk(chunk)

        @measure_time_ms
        def read_chunk():
            return memory_store.get_chunk(ChunkID(chunk.id))

        result, elapsed_ms = read_chunk()
        print(f"\nMemoryStore read: {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < READ_TARGET_MS
        ), f"MemoryStore read took {elapsed_ms:.2f}ms, target is {READ_TARGET_MS}ms"

    def test_sqlite_store_write_performance(self, sqlite_store, sample_chunks):
        """Benchmark SQLiteStore write performance."""
        chunk = sample_chunks[0]

        @measure_time_ms
        def write_chunk():
            return sqlite_store.save_chunk(chunk)

        result, elapsed_ms = write_chunk()
        print(f"\nSQLiteStore write: {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < WRITE_TARGET_MS
        ), f"SQLiteStore write took {elapsed_ms:.2f}ms, target is {WRITE_TARGET_MS}ms"

    def test_sqlite_store_read_performance(self, sqlite_store, sample_chunks):
        """Benchmark SQLiteStore read performance."""
        chunk = sample_chunks[0]
        sqlite_store.save_chunk(chunk)

        @measure_time_ms
        def read_chunk():
            return sqlite_store.get_chunk(ChunkID(chunk.id))

        result, elapsed_ms = read_chunk()
        print(f"\nSQLiteStore read: {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < READ_TARGET_MS
        ), f"SQLiteStore read took {elapsed_ms:.2f}ms, target is {READ_TARGET_MS}ms"

    def test_sqlite_cold_start_performance(self, tmp_path):
        """Benchmark SQLiteStore cold start (initialization) performance."""
        db_path = tmp_path / "cold_start.db"

        @measure_time_ms
        def cold_start():
            return SQLiteStore(db_path=str(db_path))

        store, elapsed_ms = cold_start()
        print(f"\nSQLiteStore cold start: {elapsed_ms:.2f}ms")

        store.close()

        assert (
            elapsed_ms < COLD_START_TARGET_MS
        ), f"SQLiteStore cold start took {elapsed_ms:.2f}ms, target is {COLD_START_TARGET_MS}ms"

    def test_bulk_write_performance(self, sqlite_store, sample_chunks):
        """Benchmark bulk write operations."""
        start = time.perf_counter()

        for chunk in sample_chunks[:10]:  # Write 10 chunks
            sqlite_store.save_chunk(chunk)

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        avg_ms = elapsed_ms / 10

        print(f"\nBulk write (10 chunks): {elapsed_ms:.2f}ms total, {avg_ms:.2f}ms avg")

        assert (
            avg_ms < WRITE_TARGET_MS
        ), f"Average write time {avg_ms:.2f}ms exceeds target {WRITE_TARGET_MS}ms"

    def test_bulk_read_performance(self, sqlite_store, sample_chunks):
        """Benchmark bulk read operations."""
        # Pre-populate store
        chunks_to_read = sample_chunks[:10]
        for chunk in chunks_to_read:
            sqlite_store.save_chunk(chunk)

        start = time.perf_counter()

        for chunk in chunks_to_read:
            sqlite_store.get_chunk(ChunkID(chunk.id))

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        avg_ms = elapsed_ms / 10

        print(f"\nBulk read (10 chunks): {elapsed_ms:.2f}ms total, {avg_ms:.2f}ms avg")

        assert (
            avg_ms < READ_TARGET_MS
        ), f"Average read time {avg_ms:.2f}ms exceeds target {READ_TARGET_MS}ms"

    def test_activation_update_performance(self, sqlite_store, sample_chunks):
        """Benchmark activation update operations."""
        chunk = sample_chunks[0]
        sqlite_store.save_chunk(chunk)

        @measure_time_ms
        def update_activation():
            sqlite_store.update_activation(ChunkID(chunk.id), 1.0)

        _, elapsed_ms = update_activation()
        print(f"\nActivation update: {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < WRITE_TARGET_MS
        ), f"Activation update took {elapsed_ms:.2f}ms, target is {WRITE_TARGET_MS}ms"

    def test_retrieve_by_activation_performance(self, sqlite_store, sample_chunks):
        """Benchmark retrieve_by_activation query performance."""
        # Pre-populate with activated chunks
        for i, chunk in enumerate(sample_chunks[:20]):
            sqlite_store.save_chunk(chunk)
            sqlite_store.update_activation(ChunkID(chunk.id), float(i))

        @measure_time_ms
        def retrieve_by_activation():
            return sqlite_store.retrieve_by_activation(min_activation=5.0, limit=10)

        results, elapsed_ms = retrieve_by_activation()
        print(f"\nRetrieve by activation (20 chunks, limit 10): {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < READ_TARGET_MS
        ), f"Retrieve by activation took {elapsed_ms:.2f}ms, target is {READ_TARGET_MS}ms"

    def test_add_relationship_performance(self, sqlite_store, sample_chunks):
        """Benchmark relationship creation performance."""
        chunk1, chunk2 = sample_chunks[0], sample_chunks[1]
        sqlite_store.save_chunk(chunk1)
        sqlite_store.save_chunk(chunk2)

        @measure_time_ms
        def add_relationship():
            return sqlite_store.add_relationship(
                ChunkID(chunk1.id), ChunkID(chunk2.id), "depends_on"
            )

        _, elapsed_ms = add_relationship()
        print(f"\nAdd relationship: {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < WRITE_TARGET_MS
        ), f"Add relationship took {elapsed_ms:.2f}ms, target is {WRITE_TARGET_MS}ms"

    def test_get_related_chunks_performance(self, sqlite_store, sample_chunks):
        """Benchmark relationship traversal performance."""
        # Create a chain of relationships
        chunks = sample_chunks[:10]
        for chunk in chunks:
            sqlite_store.save_chunk(chunk)

        for i in range(len(chunks) - 1):
            sqlite_store.add_relationship(
                ChunkID(chunks[i].id), ChunkID(chunks[i + 1].id), "depends_on"
            )

        @measure_time_ms
        def get_related_chunks():
            return sqlite_store.get_related_chunks(ChunkID(chunks[0].id), max_depth=2)

        results, elapsed_ms = get_related_chunks()
        print(f"\nGet related chunks (depth=2, 10 chunks): {elapsed_ms:.2f}ms")

        assert (
            elapsed_ms < READ_TARGET_MS * 2
        ), f"Get related chunks took {elapsed_ms:.2f}ms, target is {READ_TARGET_MS * 2}ms"

    def test_concurrent_write_performance(self, sqlite_store, sample_chunks):
        """Benchmark concurrent write simulation (sequential in same thread)."""
        chunks = sample_chunks[:5]

        start = time.perf_counter()

        # Simulate concurrent writes (sequential simulation)
        for chunk in chunks:
            sqlite_store.save_chunk(chunk)

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        avg_ms = elapsed_ms / 5

        print(f"\nConcurrent writes (5 chunks): {elapsed_ms:.2f}ms total, {avg_ms:.2f}ms avg")

        assert (
            avg_ms < WRITE_TARGET_MS
        ), f"Average concurrent write time {avg_ms:.2f}ms exceeds target {WRITE_TARGET_MS}ms"

    @pytest.mark.skipif(True, reason="Large scale test - run manually")
    def test_large_scale_performance(self, tmp_path):
        """Benchmark performance with large number of chunks (1000+)."""
        db_path = tmp_path / "large_scale.db"
        store = SQLiteStore(db_path=str(db_path))

        # Create 1000 chunks
        chunks = [
            CodeChunk(
                chunk_id=f"test:chunk:{i}",
                file_path="/test/large.py",
                element_type="function",
                name=f"func_{i}",
                line_start=(i * 10) + 1,  # line_start must be > 0
                line_end=(i * 10) + 5,
            )
            for i in range(1000)
        ]

        # Measure bulk write
        start = time.perf_counter()
        for chunk in chunks:
            store.save_chunk(chunk)
        write_time = (time.perf_counter() - start) * 1000
        avg_write = write_time / 1000

        print(f"\nLarge scale write (1000 chunks): {write_time:.2f}ms total, {avg_write:.2f}ms avg")

        # Measure bulk read
        start = time.perf_counter()
        for chunk in chunks[:100]:  # Read first 100
            store.get_chunk(ChunkID(chunk.id))
        read_time = (time.perf_counter() - start) * 1000
        avg_read = read_time / 100

        print(f"Large scale read (100 chunks): {read_time:.2f}ms total, {avg_read:.2f}ms avg")

        store.close()

        assert avg_write < WRITE_TARGET_MS, f"Large scale write avg {avg_write:.2f}ms"
        assert avg_read < READ_TARGET_MS, f"Large scale read avg {avg_read:.2f}ms"


__all__ = ["TestStoragePerformance"]
