"""Performance benchmarks for memory indexing operations.

Provides comprehensive benchmarking suite to measure and validate indexing performance.
Run with: pytest tests/performance/test_indexing_benchmarks.py -v --benchmark-only
"""

import tempfile
import time
from pathlib import Path

import pytest

from aurora_cli.config import Config
from aurora_cli.memory_manager import MemoryManager

pytestmark = [pytest.mark.performance, pytest.mark.ml]


class TestIndexingThroughput:
    """Benchmark indexing throughput metrics."""

    @pytest.fixture
    def small_codebase(self, tmp_path):
        """Create small test codebase (~10 files, 100 functions)."""
        codebase = tmp_path / "small"
        codebase.mkdir()

        for i in range(10):
            content_lines = [
                f'"""Module {i}."""',
                "",
            ]
            for j in range(10):
                content_lines.extend(
                    [
                        f"def function_{i}_{j}(x, y):",
                        f'    """Function {i}_{j}."""',
                        f"    return x + y + {i * j}",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    @pytest.fixture
    def medium_codebase(self, tmp_path):
        """Create medium test codebase (~50 files, 500 functions)."""
        codebase = tmp_path / "medium"
        codebase.mkdir()

        for i in range(50):
            content_lines = [
                f'"""Module {i}."""',
                "",
            ]
            for j in range(10):
                content_lines.extend(
                    [
                        f"def function_{i}_{j}(x, y):",
                        f'    """Function {i}_{j}."""',
                        f"    result = x + y + {i * j}",
                        "    return result",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    @pytest.fixture
    def large_codebase(self, tmp_path):
        """Create large test codebase (~100 files, 1000 functions)."""
        codebase = tmp_path / "large"
        codebase.mkdir()

        for i in range(100):
            content_lines = [
                f'"""Module {i}."""',
                "",
            ]
            for j in range(10):
                content_lines.extend(
                    [
                        f"def function_{i}_{j}(x, y, z=None):",
                        f'    """Function {i}_{j} with multiple operations."""',
                        "    temp = x + y",
                        f"    result = temp * {i} + {j}",
                        "    if z:",
                        "        result += z",
                        "    return result",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    def test_benchmark_small_codebase(self, small_codebase, tmp_path, benchmark):
        """Benchmark indexing small codebase (baseline)."""

        def index_small():
            db_path = tmp_path / f"bench_small_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(small_codebase)
            db_path.unlink()
            return stats

        result = benchmark(index_small)
        assert result.files_indexed > 0
        assert result.chunks_created > 0

    def test_benchmark_medium_codebase(self, medium_codebase, tmp_path, benchmark):
        """Benchmark indexing medium codebase."""

        def index_medium():
            db_path = tmp_path / f"bench_medium_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(medium_codebase)
            db_path.unlink()
            return stats

        result = benchmark(index_medium)
        assert result.files_indexed > 0
        assert result.chunks_created > 0

    def test_benchmark_large_codebase(self, large_codebase, tmp_path, benchmark):
        """Benchmark indexing large codebase."""

        def index_large():
            db_path = tmp_path / f"bench_large_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(large_codebase)
            db_path.unlink()
            return stats

        result = benchmark(index_large)
        assert result.files_indexed > 0
        assert result.chunks_created > 0


class TestBatchSizeImpact:
    """Benchmark impact of different batch sizes on embedding generation."""

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase with consistent size."""
        codebase = tmp_path / "batch_test"
        codebase.mkdir()

        for i in range(20):
            content_lines = [f'"""Module {i}."""', ""]
            for j in range(10):
                content_lines.extend(
                    [
                        f"def function_{i}_{j}(x):",
                        f'    """Function {i}_{j}."""',
                        f"    return x * {i} + {j}",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    def test_benchmark_batch_size_8(self, test_codebase, tmp_path, benchmark):
        """Benchmark with batch size 8."""

        def index_batch_8():
            db_path = tmp_path / f"batch_8_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(test_codebase, batch_size=8)
            db_path.unlink()
            return stats

        result = benchmark(index_batch_8)
        assert result.chunks_created > 0

    def test_benchmark_batch_size_32(self, test_codebase, tmp_path, benchmark):
        """Benchmark with batch size 32 (default)."""

        def index_batch_32():
            db_path = tmp_path / f"batch_32_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(test_codebase, batch_size=32)
            db_path.unlink()
            return stats

        result = benchmark(index_batch_32)
        assert result.chunks_created > 0

    def test_benchmark_batch_size_64(self, test_codebase, tmp_path, benchmark):
        """Benchmark with batch size 64."""

        def index_batch_64():
            db_path = tmp_path / f"batch_64_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(test_codebase, batch_size=64)
            db_path.unlink()
            return stats

        result = benchmark(index_batch_64)
        assert result.chunks_created > 0

    def test_benchmark_batch_size_128(self, test_codebase, tmp_path, benchmark):
        """Benchmark with batch size 128."""

        def index_batch_128():
            db_path = tmp_path / f"batch_128_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(test_codebase, batch_size=128)
            db_path.unlink()
            return stats

        result = benchmark(index_batch_128)
        assert result.chunks_created > 0


class TestPhaseTimingBreakdown:
    """Measure timing breakdown across indexing phases."""

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase."""
        codebase = tmp_path / "phase_test"
        codebase.mkdir()

        for i in range(30):
            content_lines = [f'"""Module {i}."""', ""]
            for j in range(10):
                content_lines.extend(
                    [
                        f"class Class_{i}_{j}:",
                        f'    """Class {i}_{j}."""',
                        "",
                        f"    def method_{j}(self, x):",
                        f'        """Method {j}."""',
                        f"        return x + {i} * {j}",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    def test_phase_timing_breakdown(self, test_codebase, tmp_path):
        """Measure time spent in each indexing phase."""
        db_path = tmp_path / "phase_timing.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        phase_times = {}
        phase_start = None
        current_phase = None

        def progress_callback(progress):
            nonlocal phase_start, current_phase, phase_times

            if progress.phase != current_phase:
                if current_phase and phase_start:
                    duration = time.time() - phase_start
                    phase_times[current_phase] = phase_times.get(current_phase, 0) + duration

                current_phase = progress.phase
                phase_start = time.time()

        overall_start = time.time()
        stats = manager.index_path(test_codebase, progress_callback=progress_callback)
        overall_duration = time.time() - overall_start

        # Record final phase
        if current_phase and phase_start:
            duration = time.time() - phase_start
            phase_times[current_phase] = phase_times.get(current_phase, 0) + duration

        # Assertions
        assert stats.files_indexed > 0
        assert stats.chunks_created > 0
        assert overall_duration > 0

        # Print breakdown for analysis
        print("\n=== Phase Timing Breakdown ===")
        for phase in ["discovering", "parsing", "git_blame", "embedding", "storing", "complete"]:
            if phase in phase_times:
                duration = phase_times[phase]
                percent = (duration / overall_duration) * 100
                print(f"{phase:15s}: {duration:7.2f}s ({percent:5.1f}%)")

        print(f"{'Total':15s}: {overall_duration:7.2f}s (100.0%)")

        # Validate phase proportions (embedding should be significant portion)
        if "embedding" in phase_times:
            embedding_percent = (phase_times["embedding"] / overall_duration) * 100
            assert embedding_percent > 10, "Embedding should be significant portion of time"

        db_path.unlink()


class TestConcurrentIndexing:
    """Benchmark concurrent/parallel indexing scenarios."""

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase."""
        codebase = tmp_path / "concurrent_test"
        codebase.mkdir()

        for i in range(40):
            content_lines = [f'"""Module {i}."""', ""]
            for j in range(8):
                content_lines.extend(
                    [
                        f"def func_{i}_{j}(a, b, c):",
                        f'    """Function {i}_{j}."""',
                        f"    result = (a + b) * c + {i * j}",
                        "    return result",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    def test_sequential_indexing(self, test_codebase, tmp_path, benchmark):
        """Benchmark sequential single-process indexing (baseline)."""

        def index_sequential():
            db_path = tmp_path / f"sequential_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(test_codebase)
            db_path.unlink()
            return stats

        result = benchmark(index_sequential)
        assert result.chunks_created > 0


class TestMemoryUsage:
    """Benchmark memory usage during indexing."""

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase."""
        codebase = tmp_path / "memory_test"
        codebase.mkdir()

        for i in range(50):
            content_lines = [f'"""Module {i}."""', ""]
            for j in range(10):
                content_lines.extend(
                    [
                        f"def function_{i}_{j}(x, y):",
                        f'    """Function {i}_{j} does computations."""',
                        "    temp = x + y",
                        f"    result = temp * {i * j}",
                        "    return result",
                        "",
                    ]
                )
            (codebase / f"module_{i}.py").write_text("\n".join(content_lines))

        return codebase

    def test_memory_baseline(self, test_codebase, tmp_path):
        """Measure baseline memory usage during indexing."""
        import tracemalloc

        db_path = tmp_path / "memory_baseline.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        stats = manager.index_path(test_codebase)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Calculate memory delta
        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_diff = sum(stat.size_diff for stat in top_stats)

        print("\n=== Memory Usage ===")
        print(f"Files indexed: {stats.files_indexed}")
        print(f"Chunks created: {stats.chunks_created}")
        print(f"Memory delta: {total_diff / 1024 / 1024:.2f} MB")

        # Top 10 memory allocations
        print("\nTop 10 memory allocations:")
        for stat in top_stats[:10]:
            print(f"  {stat}")

        assert stats.chunks_created > 0
        db_path.unlink()


class TestRealWorldCodebase:
    """Benchmark on real-world Aurora codebase."""

    def test_index_aurora_cli(self, tmp_path, benchmark):
        """Benchmark indexing Aurora CLI package."""
        cli_path = Path(__file__).parent.parent.parent / "packages" / "cli" / "src" / "aurora_cli"

        if not cli_path.exists():
            pytest.skip("Aurora CLI source not found")

        def index_cli():
            db_path = tmp_path / f"aurora_cli_{time.time()}.db"
            config = Config(db_path=str(db_path))
            manager = MemoryManager(config=config)
            stats = manager.index_path(cli_path)
            db_path.unlink()
            return stats

        result = benchmark(index_cli)
        assert result.files_indexed > 0
        assert result.chunks_created > 0

        print("\n=== Aurora CLI Indexing ===")
        print(f"Files indexed: {result.files_indexed}")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Throughput: {result.files_indexed / result.duration_seconds:.1f} files/sec")


class TestIndexingCorrectness:
    """Validate correctness of indexed data."""

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase with known structure."""
        codebase = tmp_path / "correctness_test"
        codebase.mkdir()

        # Create file with specific functions
        (codebase / "test_module.py").write_text(
            '''"""Test module for validation."""


def simple_function():
    """A simple function."""
    return 42


def function_with_args(x, y, z=None):
    """Function with arguments."""
    if z:
        return x + y + z
    return x + y


class TestClass:
    """A test class."""

    def method_one(self):
        """Method one."""
        return "one"

    def method_two(self, value):
        """Method two."""
        return value * 2
'''
        )

        return codebase

    def test_all_chunks_indexed(self, test_codebase, tmp_path):
        """Verify all expected chunks are indexed."""
        db_path = tmp_path / "correctness.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        stats = manager.index_path(test_codebase)

        # Should have: simple_function, function_with_args, TestClass, method_one, method_two
        assert stats.chunks_created >= 5, f"Expected at least 5 chunks, got {stats.chunks_created}"

        # Search for each expected element
        expected_names = [
            "simple_function",
            "function_with_args",
            "TestClass",
            "method_one",
            "method_two",
        ]

        for name in expected_names:
            results = manager.search(name, limit=10)
            matching = [r for r in results if name in r.chunk_id or name in r.content]
            assert len(matching) > 0, f"Expected to find '{name}' in index"

        db_path.unlink()

    def test_chunk_metadata_completeness(self, test_codebase, tmp_path):
        """Verify indexed chunks have complete metadata."""
        db_path = tmp_path / "metadata.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        stats = manager.index_path(test_codebase)
        assert stats.chunks_created > 0

        # Search and validate metadata
        results = manager.search("function", limit=10)
        assert len(results) > 0

        for result in results:
            # Validate essential fields
            assert result.chunk_id, "Chunk should have ID"
            assert result.file_path, "Chunk should have file path"
            assert result.line_range, "Chunk should have line range"
            assert result.line_range[0] > 0, "Line start should be positive"
            assert result.line_range[1] >= result.line_range[0], "Line end should be >= start"

        db_path.unlink()

    def test_embeddings_generated(self, test_codebase, tmp_path):
        """Verify embeddings are generated for all chunks."""
        db_path = tmp_path / "embeddings.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        stats = manager.index_path(test_codebase)
        assert stats.chunks_created > 0

        # Search should work (requires embeddings)
        results = manager.search("simple function returns forty two", limit=5)
        assert len(results) > 0, "Semantic search should find results"

        # First result should be simple_function
        assert "simple_function" in results[0].content, "Should find semantically similar function"

        db_path.unlink()


class TestProgressReporting:
    """Validate progress reporting accuracy."""

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase."""
        codebase = tmp_path / "progress_test"
        codebase.mkdir()

        for i in range(15):
            (codebase / f"module_{i}.py").write_text(
                f'''"""Module {i}."""


def function_{i}():
    """Function {i}."""
    return {i}
'''
            )

        return codebase

    def test_progress_callback_invoked(self, test_codebase, tmp_path):
        """Verify progress callback is invoked during indexing."""
        db_path = tmp_path / "progress.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        progress_calls = []

        def progress_callback(progress):
            progress_calls.append(
                {
                    "phase": progress.phase,
                    "current": progress.current,
                    "total": progress.total,
                    "file_path": progress.file_path,
                }
            )

        stats = manager.index_path(test_codebase, progress_callback=progress_callback)

        # Should have received progress updates
        assert len(progress_calls) > 0, "Progress callback should be invoked"

        # Should see multiple phases
        phases_seen = set(call["phase"] for call in progress_calls)
        expected_phases = {"discovering", "parsing", "embedding", "storing"}
        assert (
            len(phases_seen & expected_phases) >= 2
        ), f"Should see multiple phases, got {phases_seen}"

        # Final call should be "complete"
        assert progress_calls[-1]["phase"] == "complete", "Final phase should be 'complete'"

        db_path.unlink()


class TestErrorHandling:
    """Validate error handling during indexing."""

    def test_invalid_python_file(self, tmp_path):
        """Test indexing with invalid Python syntax."""
        codebase = tmp_path / "error_test"
        codebase.mkdir()

        # Valid file
        (codebase / "valid.py").write_text(
            '''"""Valid module."""


def valid_function():
    """Valid function."""
    return True
'''
        )

        # Invalid file
        (codebase / "invalid.py").write_text(
            '''"""Invalid module."""

def broken_function(
    # Missing closing paren
    return True
'''
        )

        db_path = tmp_path / "error.db"
        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        stats = manager.index_path(codebase)

        # Should index valid file, skip invalid
        assert stats.files_indexed >= 1, "Should index valid file"
        assert stats.errors >= 1, "Should record error for invalid file"

        db_path.unlink()
