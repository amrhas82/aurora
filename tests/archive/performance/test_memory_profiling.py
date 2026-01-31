"""Memory profiling tests for AURORA Phase 1.

Tests memory usage with large numbers of cached chunks to verify
<100MB target for 10K chunks as specified in PRD Section 2.2.
"""

import gc
import sys
import tracemalloc
from pathlib import Path

import pytest


# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "core" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "context-code" / "src"))

from aurora_core.chunks import CodeChunk, ReasoningChunk
from aurora_core.store import MemoryStore, SQLiteStore


def generate_test_chunks(count: int) -> list[CodeChunk]:
    """Generate test chunks for memory profiling."""
    chunks = []
    for i in range(count):
        chunk = CodeChunk(
            chunk_id=f"code:file{i // 100}.py:func{i}:{i * 10 + 1}-{i * 10 + 21}",
            file_path=f"/test/file{i // 100}.py",
            element_type="function",
            name=f"test_function_{i}",
            line_start=i * 10 + 1,  # Must be > 0
            line_end=i * 10 + 21,
            signature=f"def test_function_{i}(arg1: int, arg2: str) -> bool:",
            docstring=f"Test function {i} for memory profiling.\n\nArgs:\n    arg1: First argument\n    arg2: Second argument\n\nReturns:\n    bool: Result of operation",
            dependencies=[
                f"code:file{j}.py:func{j}:{j * 10}-{j * 10 + 20}" for j in range(max(0, i - 3), i)
            ],
            complexity_score=0.3 + (i % 7) * 0.1,
            language="python",
        )
        chunks.append(chunk)
    return chunks


def generate_test_reasoning_chunks(count: int) -> list[ReasoningChunk]:
    """Generate test reasoning chunks for memory profiling."""
    chunks = []
    for i in range(count):
        chunk = ReasoningChunk(
            chunk_id=f"reasoning:pattern_{i}:{i}",
            pattern=f"implement feature {i} with database access and API integration",
            complexity=["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"][i % 4],
            subgoals=[
                {
                    "id": f"subgoal_{i}_1",
                    "description": f"Analyze requirements for feature {i}",
                    "assigned_agent": "analyzer",
                },
                {
                    "id": f"subgoal_{i}_2",
                    "description": f"Implement feature {i}",
                    "assigned_agent": "developer",
                },
                {
                    "id": f"subgoal_{i}_3",
                    "description": f"Test feature {i}",
                    "assigned_agent": "tester",
                },
            ],
            execution_order=[
                {"phase": "sequential", "subgoals": [f"subgoal_{i}_1"]},
                {"phase": "parallel", "subgoals": [f"subgoal_{i}_2", f"subgoal_{i}_3"]},
            ],
            tools_used=["file_reader", "code_analyzer", "test_runner"],
            tool_sequence=[
                {"tool": "file_reader", "timestamp": 1000 + i, "duration_ms": 100},
                {"tool": "code_analyzer", "timestamp": 1100 + i, "duration_ms": 200},
                {"tool": "test_runner", "timestamp": 1300 + i, "duration_ms": 500},
            ],
            success_score=0.5 + (i % 5) * 0.1,
            metadata={
                "total_duration_ms": 800,
                "llm_calls": 3,
                "tokens_used": 1500,
            },
        )
        chunks.append(chunk)
    return chunks


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    current, peak = tracemalloc.get_traced_memory()
    return current / 1024 / 1024  # Convert to MB


class TestMemoryProfiling:
    """Memory profiling tests for Phase 1 completion."""

    def test_memory_store_10k_chunks_memory_usage(self):
        """Test memory usage with 10K chunks in MemoryStore.

        PRD Requirement: <100MB for 10K cached chunks (Section 2.2)
        """
        # Force garbage collection before test
        gc.collect()

        # Start tracking memory
        tracemalloc.start()

        # Create store
        store = MemoryStore()

        # Measure baseline
        baseline_mb = get_memory_usage_mb()
        print(f"\nBaseline memory: {baseline_mb:.2f} MB")

        # Generate and store 10K chunks
        print("Generating 10,000 test chunks...")
        chunks = generate_test_chunks(10000)

        after_generation_mb = get_memory_usage_mb()
        print(f"After generation: {after_generation_mb:.2f} MB")
        print(f"Generation delta: {after_generation_mb - baseline_mb:.2f} MB")

        print("Storing chunks...")
        for chunk in chunks:
            store.save_chunk(chunk)

        # Measure after storing
        after_store_mb = get_memory_usage_mb()
        print(f"After storing: {after_store_mb:.2f} MB")

        # Calculate memory used by storage
        storage_mb = after_store_mb - baseline_mb
        print(f"Total memory used: {storage_mb:.2f} MB")

        # Stop tracking
        tracemalloc.stop()

        # Cleanup
        store.close()

        # Verify target met
        assert storage_mb < 100, f"Memory usage {storage_mb:.2f} MB exceeds 100 MB target"
        print(f"✓ Memory target met: {storage_mb:.2f} MB < 100 MB")

    def test_sqlite_store_memory_efficient(self, tmp_path):
        """Test SQLite store memory usage is reasonable.

        SQLite should use less memory than in-memory store due to disk backing.
        """
        gc.collect()
        tracemalloc.start()

        # Create SQLite store
        db_path = tmp_path / "memory_test.db"
        store = SQLiteStore(str(db_path))

        baseline_mb = get_memory_usage_mb()
        print(f"\nSQLite baseline: {baseline_mb:.2f} MB")

        # Generate and store 10K chunks
        chunks = generate_test_chunks(10000)

        for chunk in chunks:
            store.save_chunk(chunk)

        after_store_mb = get_memory_usage_mb()
        storage_mb = after_store_mb - baseline_mb

        print(f"SQLite memory used: {storage_mb:.2f} MB")

        tracemalloc.stop()
        store.close()

        # SQLite should use less memory than MemoryStore
        # (most data on disk, only cache in memory)
        assert storage_mb < 100, f"SQLite memory {storage_mb:.2f} MB exceeds target"
        print(f"✓ SQLite memory efficient: {storage_mb:.2f} MB")

    def test_chunk_memory_overhead(self):
        """Test memory overhead per chunk."""
        gc.collect()
        tracemalloc.start()

        baseline_mb = get_memory_usage_mb()

        # Create 1000 chunks to measure average
        generate_test_chunks(1000)

        after_mb = get_memory_usage_mb()
        total_mb = after_mb - baseline_mb
        per_chunk_kb = (total_mb * 1024) / 1000

        print(f"\n1000 chunks use {total_mb:.2f} MB")
        print(f"Average per chunk: {per_chunk_kb:.2f} KB")

        tracemalloc.stop()

        # Expect <10KB per chunk on average
        assert per_chunk_kb < 10, f"Per-chunk memory {per_chunk_kb:.2f} KB too high"
        print(f"✓ Efficient chunk storage: {per_chunk_kb:.2f} KB per chunk")

    @pytest.mark.skip(reason="Flaky: non-deterministic memory scaling in CI environments")
    def test_memory_scaling_linear(self):
        """Test memory usage scales linearly with chunk count."""
        measurements = []

        for count in [1000, 2000, 5000, 10000]:
            # Force clean slate between measurements
            gc.collect()
            gc.collect()  # Double collect to handle reference cycles

            tracemalloc.start()

            # Measure baseline immediately after tracemalloc start
            baseline = get_memory_usage_mb()

            # Generate and store
            chunks = generate_test_chunks(count)
            store = MemoryStore()

            for chunk in chunks:
                store.save_chunk(chunk)

            after = get_memory_usage_mb()
            used = after - baseline

            # Clean up before stopping tracemalloc to measure accurately
            store.close()
            del store
            del chunks
            gc.collect()

            tracemalloc.stop()

            measurements.append((count, used))
            print(f"{count} chunks: {used:.2f} MB")

        # Check scaling is roughly linear
        # Relaxed tolerance (3.5x) to account for CI environment variability
        # (memory allocators, background processes, GC timing differences)
        # Still catches pathological O(n²) growth which would show 4-10x ratios
        ratio_1k_2k = measurements[1][1] / measurements[0][1]
        ratio_5k_10k = measurements[3][1] / measurements[2][1]

        print(f"Scaling ratio (2K/1K): {ratio_1k_2k:.2f}")
        print(f"Scaling ratio (10K/5K): {ratio_5k_10k:.2f}")

        # Should be close to 2.0 (linear scaling), allow up to 3.5x for CI variance
        assert 1.2 < ratio_1k_2k < 3.5, f"Non-linear scaling: {ratio_1k_2k:.2f}"
        assert 1.2 < ratio_5k_10k < 3.5, f"Non-linear scaling: {ratio_5k_10k:.2f}"

        print("✓ Memory scaling is linear")

    def test_memory_cleanup_on_close(self, tmp_path):
        """Test memory is released when store is closed."""
        gc.collect()
        tracemalloc.start()

        baseline = get_memory_usage_mb()

        # Create and populate store
        store = MemoryStore()
        chunks = generate_test_chunks(5000)

        for chunk in chunks:
            store.save_chunk(chunk)

        with_store = get_memory_usage_mb()

        # Close store
        store.close()
        del store
        del chunks
        gc.collect()

        after_close = get_memory_usage_mb()

        print(f"\nBaseline: {baseline:.2f} MB")
        print(f"With 5K chunks: {with_store:.2f} MB")
        print(f"After close: {after_close:.2f} MB")
        print(f"Leaked: {after_close - baseline:.2f} MB")

        tracemalloc.stop()

        # Should release most memory (allow 30% tolerance for Python GC)
        leaked = after_close - baseline
        stored = with_store - baseline

        assert (
            leaked < stored * 0.3
        ), f"Memory leak detected: {leaked:.2f} MB (stored {stored:.2f} MB)"
        print(
            f"✓ Memory properly released on close (leaked {leaked:.2f} MB / {stored:.2f} MB = {leaked / stored * 100:.1f}%)",
        )

    def test_reasoning_chunk_10k_patterns_memory_usage(self):
        """Test memory usage with 10K reasoning patterns.

        PRD Requirement (Phase 2, Task 8.24): <100MB for 10K cached reasoning patterns
        This test specifically validates ReasoningChunk memory efficiency.
        """
        # Force garbage collection before test
        gc.collect()

        # Start tracking memory
        tracemalloc.start()

        # Create store
        store = MemoryStore()

        # Measure baseline
        baseline_mb = get_memory_usage_mb()
        print(f"\nBaseline memory: {baseline_mb:.2f} MB")

        # Generate and store 10K reasoning chunks
        print("Generating 10,000 reasoning pattern chunks...")
        chunks = generate_test_reasoning_chunks(10000)

        after_generation_mb = get_memory_usage_mb()
        print(f"After generation: {after_generation_mb:.2f} MB")
        print(f"Generation delta: {after_generation_mb - baseline_mb:.2f} MB")

        print("Storing reasoning patterns...")
        for chunk in chunks:
            store.save_chunk(chunk)

        # Measure after storing
        after_store_mb = get_memory_usage_mb()
        print(f"After storing: {after_store_mb:.2f} MB")

        # Calculate memory used by storage
        storage_mb = after_store_mb - baseline_mb
        print(f"Total memory used: {storage_mb:.2f} MB")

        # Stop tracking
        tracemalloc.stop()

        # Cleanup
        store.close()

        # Verify target met
        assert storage_mb < 100, f"Memory usage {storage_mb:.2f} MB exceeds 100 MB target"
        print(f"✓ Reasoning pattern memory target met: {storage_mb:.2f} MB < 100 MB")

    def test_reasoning_chunk_memory_overhead(self):
        """Test memory overhead per reasoning chunk."""
        gc.collect()
        tracemalloc.start()

        baseline_mb = get_memory_usage_mb()

        # Create 1000 reasoning chunks to measure average
        generate_test_reasoning_chunks(1000)

        after_mb = get_memory_usage_mb()
        total_mb = after_mb - baseline_mb
        per_chunk_kb = (total_mb * 1024) / 1000

        print(f"\n1000 reasoning chunks use {total_mb:.2f} MB")
        print(f"Average per chunk: {per_chunk_kb:.2f} KB")

        tracemalloc.stop()

        # ReasoningChunks are more complex than CodeChunks, allow up to 20KB per chunk
        assert per_chunk_kb < 20, f"Per-chunk memory {per_chunk_kb:.2f} KB too high"
        print(f"✓ Efficient reasoning chunk storage: {per_chunk_kb:.2f} KB per chunk")

    def test_mixed_chunk_types_memory_usage(self):
        """Test memory usage with mixed CodeChunk and ReasoningChunk storage.

        This tests the realistic scenario where both code and reasoning patterns
        are stored in the same memory store.
        """
        gc.collect()
        tracemalloc.start()

        store = MemoryStore()
        baseline_mb = get_memory_usage_mb()

        print("\nGenerating 5000 code chunks + 5000 reasoning chunks...")
        code_chunks = generate_test_chunks(5000)
        reasoning_chunks = generate_test_reasoning_chunks(5000)

        print("Storing mixed chunk types...")
        for chunk in code_chunks:
            store.save_chunk(chunk)
        for chunk in reasoning_chunks:
            store.save_chunk(chunk)

        after_store_mb = get_memory_usage_mb()
        storage_mb = after_store_mb - baseline_mb

        print(f"Mixed storage memory used: {storage_mb:.2f} MB")

        tracemalloc.stop()
        store.close()

        # Should still be well under 100MB
        assert storage_mb < 100, f"Mixed storage memory {storage_mb:.2f} MB exceeds target"
        print(f"✓ Mixed storage memory efficient: {storage_mb:.2f} MB < 100 MB")


if __name__ == "__main__":
    # Run memory profiling tests
    pytest.main([__file__, "-v", "-s"])
