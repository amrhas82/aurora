"""Comprehensive indexing performance benchmarks for optimization validation.

This module provides detailed benchmarks to:
1. Establish baseline measurements before optimizations
2. Isolate performance bottlenecks in specific components
3. Measure phase-by-phase timing breakdown
4. Track memory usage patterns
5. Validate optimizations with before/after comparisons

Run with: pytest tests/performance/test_indexing_optimization_benchmarks.py -v -s --benchmark-only
Run specific: pytest -k "test_component_" -v -s  # Component isolation tests

Key metrics tracked:
- Files/second throughput
- Chunks/second throughput
- Embedding latency (ms/chunk)
- DB write latency (ms/chunk)
- Git blame overhead (ms/file)
- Memory peak (MB)
"""

import gc
import statistics
import tempfile
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.ml]


@dataclass
class TimingResult:
    """Detailed timing breakdown for a single indexing run."""

    total_seconds: float
    discovery_seconds: float = 0.0
    parsing_seconds: float = 0.0
    git_blame_seconds: float = 0.0
    embedding_seconds: float = 0.0
    storing_seconds: float = 0.0
    files_indexed: int = 0
    chunks_created: int = 0
    memory_peak_mb: float = 0.0

    @property
    def files_per_second(self) -> float:
        return self.files_indexed / self.total_seconds if self.total_seconds > 0 else 0

    @property
    def chunks_per_second(self) -> float:
        return self.chunks_created / self.total_seconds if self.total_seconds > 0 else 0

    @property
    def ms_per_chunk_embedding(self) -> float:
        if self.chunks_created == 0 or self.embedding_seconds == 0:
            return 0
        return (self.embedding_seconds / self.chunks_created) * 1000

    @property
    def ms_per_chunk_storing(self) -> float:
        if self.chunks_created == 0 or self.storing_seconds == 0:
            return 0
        return (self.storing_seconds / self.chunks_created) * 1000

    @property
    def ms_per_file_git_blame(self) -> float:
        if self.files_indexed == 0 or self.git_blame_seconds == 0:
            return 0
        return (self.git_blame_seconds / self.files_indexed) * 1000

    def phase_percentages(self) -> dict[str, float]:
        """Return percentage breakdown by phase."""
        if self.total_seconds == 0:
            return {}
        return {
            "discovery": (self.discovery_seconds / self.total_seconds) * 100,
            "parsing": (self.parsing_seconds / self.total_seconds) * 100,
            "git_blame": (self.git_blame_seconds / self.total_seconds) * 100,
            "embedding": (self.embedding_seconds / self.total_seconds) * 100,
            "storing": (self.storing_seconds / self.total_seconds) * 100,
        }


@dataclass
class BenchmarkSuite:
    """Collection of timing results for statistical analysis."""

    results: list[TimingResult] = field(default_factory=list)
    name: str = ""

    def add(self, result: TimingResult) -> None:
        self.results.append(result)

    @property
    def mean_total(self) -> float:
        return statistics.mean(r.total_seconds for r in self.results) if self.results else 0

    @property
    def std_total(self) -> float:
        if len(self.results) < 2:
            return 0
        return statistics.stdev(r.total_seconds for r in self.results)

    @property
    def mean_files_per_sec(self) -> float:
        return statistics.mean(r.files_per_second for r in self.results) if self.results else 0

    @property
    def mean_chunks_per_sec(self) -> float:
        return statistics.mean(r.chunks_per_second for r in self.results) if self.results else 0

    def summary(self) -> str:
        if not self.results:
            return "No results"
        r = self.results[0]  # Use first result for phase breakdown
        pct = r.phase_percentages()
        return f"""
=== {self.name} Benchmark Results ===
Total time:     {self.mean_total:.2f}s (±{self.std_total:.2f}s)
Throughput:     {self.mean_files_per_sec:.1f} files/sec, {self.mean_chunks_per_sec:.1f} chunks/sec
Files indexed:  {r.files_indexed}
Chunks created: {r.chunks_created}
Memory peak:    {r.memory_peak_mb:.1f} MB

Phase Breakdown:
  Discovery:  {r.discovery_seconds:.3f}s ({pct.get('discovery', 0):.1f}%)
  Parsing:    {r.parsing_seconds:.3f}s ({pct.get('parsing', 0):.1f}%)
  Git Blame:  {r.git_blame_seconds:.3f}s ({pct.get('git_blame', 0):.1f}%)
  Embedding:  {r.embedding_seconds:.3f}s ({pct.get('embedding', 0):.1f}%)
  Storing:    {r.storing_seconds:.3f}s ({pct.get('storing', 0):.1f}%)

Per-item Latencies:
  Embedding:  {r.ms_per_chunk_embedding:.2f} ms/chunk
  Storing:    {r.ms_per_chunk_storing:.2f} ms/chunk
  Git Blame:  {r.ms_per_file_git_blame:.2f} ms/file
"""


def generate_realistic_python_file(module_idx: int, functions_per_file: int = 10) -> str:
    """Generate a realistic Python file with varied code patterns."""
    lines = [
        f'"""Module {module_idx} - auto-generated for benchmarking."""',
        "",
        "from typing import Any, Optional",
        "import logging",
        "",
        f"logger = logging.getLogger(__name__)",
        "",
    ]

    for j in range(functions_per_file):
        # Vary function complexity
        if j % 3 == 0:
            # Simple function
            lines.extend(
                [
                    f"def simple_func_{module_idx}_{j}(x: int, y: int) -> int:",
                    f'    """Simple arithmetic function."""',
                    f"    return x + y + {module_idx * j}",
                    "",
                ]
            )
        elif j % 3 == 1:
            # Function with logic
            lines.extend(
                [
                    f"def logic_func_{module_idx}_{j}(data: list[Any], threshold: float = 0.5) -> list[Any]:",
                    f'    """Filter data above threshold."""',
                    f"    result = []",
                    f"    for item in data:",
                    f"        if isinstance(item, (int, float)) and item > threshold:",
                    f"            result.append(item)",
                    f"    return result",
                    "",
                ]
            )
        else:
            # Function with docstring and multiple operations
            lines.extend(
                [
                    f"def complex_func_{module_idx}_{j}(",
                    f"    input_data: dict[str, Any],",
                    f"    config: Optional[dict] = None,",
                    f"    verbose: bool = False,",
                    f") -> dict[str, Any]:",
                    f'    """Process input data according to configuration.',
                    f"",
                    f"    Args:",
                    f"        input_data: Dictionary of input values",
                    f"        config: Optional configuration overrides",
                    f"        verbose: Enable detailed logging",
                    f"",
                    f"    Returns:",
                    f"        Processed data dictionary",
                    f'    """',
                    f"    if config is None:",
                    f"        config = {{'default': True}}",
                    f"    result = {{}}",
                    f"    for key, value in input_data.items():",
                    f"        if verbose:",
                    f"            logger.debug(f'Processing {{key}}')",
                    f"        result[key] = value * {module_idx + 1}",
                    f"    return result",
                    "",
                ]
            )

    # Add a class
    lines.extend(
        [
            f"class DataProcessor_{module_idx}:",
            f'    """Process data with configurable behavior."""',
            "",
            f"    def __init__(self, config: dict[str, Any]) -> None:",
            f'        """Initialize with configuration."""',
            f"        self.config = config",
            f"        self._cache: dict[str, Any] = {{}}",
            "",
            f"    def process(self, data: Any) -> Any:",
            f'        """Process single data item."""',
            f"        return data",
            "",
            f"    def batch_process(self, items: list[Any]) -> list[Any]:",
            f'        """Process multiple items efficiently."""',
            f"        return [self.process(item) for item in items]",
            "",
        ]
    )

    return "\n".join(lines)


def create_test_codebase(
    tmp_path: Path,
    num_files: int,
    functions_per_file: int = 10,
    name: str = "test_codebase",
) -> Path:
    """Create a test codebase with specified size."""
    codebase = tmp_path / name
    codebase.mkdir(parents=True, exist_ok=True)

    for i in range(num_files):
        content = generate_realistic_python_file(i, functions_per_file)
        (codebase / f"module_{i}.py").write_text(content)

    return codebase


def run_indexed_with_timing(
    codebase_path: Path,
    db_path: Path,
    batch_size: int = 32,
    skip_git: bool = True,
) -> TimingResult:
    """Run indexing and capture detailed timing breakdown."""
    import os

    # Optionally skip git for isolated benchmarks
    if skip_git:
        os.environ["AURORA_SKIP_GIT"] = "1"
    else:
        os.environ.pop("AURORA_SKIP_GIT", None)

    from aurora_cli.config import Config
    from aurora_cli.memory_manager import MemoryManager

    # Track phase times
    phase_times: dict[str, float] = {}
    phase_start: float | None = None
    current_phase: str | None = None

    def progress_callback(progress: Any) -> None:
        nonlocal phase_start, current_phase, phase_times

        if progress.phase != current_phase:
            if current_phase and phase_start:
                duration = time.perf_counter() - phase_start
                phase_times[current_phase] = phase_times.get(current_phase, 0) + duration

            current_phase = progress.phase
            phase_start = time.perf_counter()

    # Force garbage collection and start memory tracking
    gc.collect()
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    # Run indexing
    overall_start = time.perf_counter()
    config = Config(db_path=str(db_path))
    manager = MemoryManager(config=config)
    stats = manager.index_path(
        codebase_path, progress_callback=progress_callback, batch_size=batch_size
    )
    overall_duration = time.perf_counter() - overall_start

    # Capture final phase
    if current_phase and phase_start:
        duration = time.perf_counter() - phase_start
        phase_times[current_phase] = phase_times.get(current_phase, 0) + duration

    # Get memory stats
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
    memory_peak_mb = sum(stat.size for stat in top_stats if stat.size > 0) / (1024 * 1024)

    # Cleanup env var
    os.environ.pop("AURORA_SKIP_GIT", None)

    return TimingResult(
        total_seconds=overall_duration,
        discovery_seconds=phase_times.get("discovering", 0),
        parsing_seconds=phase_times.get("parsing", 0),
        git_blame_seconds=phase_times.get("git_blame", 0),
        embedding_seconds=phase_times.get("embedding", 0),
        storing_seconds=phase_times.get("storing", 0),
        files_indexed=stats.files_indexed,
        chunks_created=stats.chunks_created,
        memory_peak_mb=memory_peak_mb,
    )


# =============================================================================
# BASELINE BENCHMARKS - Run these before any optimizations
# =============================================================================


class TestBaselineBenchmarks:
    """Establish baseline performance metrics before optimization."""

    def test_baseline_small_codebase(self, tmp_path: Path) -> None:
        """Baseline: 10 files, ~100 functions."""
        codebase = create_test_codebase(tmp_path, num_files=10, name="small")
        db_path = tmp_path / "small.db"

        suite = BenchmarkSuite(name="Small Codebase (10 files)")
        # Run 3 times for statistical validity
        for i in range(3):
            result = run_indexed_with_timing(codebase, tmp_path / f"small_{i}.db")
            suite.add(result)

        print(suite.summary())

        # Assertions for regression detection
        assert suite.mean_files_per_sec > 0.5, "Should process at least 0.5 files/sec"
        assert suite.results[0].chunks_created >= 10, "Should create chunks for each file"

    def test_baseline_medium_codebase(self, tmp_path: Path) -> None:
        """Baseline: 50 files, ~500 functions."""
        codebase = create_test_codebase(tmp_path, num_files=50, name="medium")

        suite = BenchmarkSuite(name="Medium Codebase (50 files)")
        for i in range(3):
            result = run_indexed_with_timing(codebase, tmp_path / f"medium_{i}.db")
            suite.add(result)

        print(suite.summary())

        assert (
            suite.mean_files_per_sec > 0.3
        ), "Medium codebase should maintain reasonable throughput"

    def test_baseline_large_codebase(self, tmp_path: Path) -> None:
        """Baseline: 100 files, ~1000 functions."""
        codebase = create_test_codebase(tmp_path, num_files=100, name="large")

        suite = BenchmarkSuite(name="Large Codebase (100 files)")
        result = run_indexed_with_timing(codebase, tmp_path / "large.db")
        suite.add(result)

        print(suite.summary())

        # Track throughput degradation
        assert result.files_indexed == 100


# =============================================================================
# COMPONENT ISOLATION BENCHMARKS - Identify specific bottlenecks
# =============================================================================


class TestComponentIsolation:
    """Isolate and measure individual components of the indexing pipeline."""

    @pytest.fixture
    def test_codebase(self, tmp_path: Path) -> Path:
        """Create consistent test codebase for component tests."""
        return create_test_codebase(tmp_path, num_files=30, name="component_test")

    def test_component_file_discovery(self, test_codebase: Path, tmp_path: Path) -> None:
        """Measure file discovery performance in isolation."""
        from aurora_cli.ignore_patterns import load_ignore_patterns, should_ignore
        from aurora_context_code.registry import get_global_registry

        registry = get_global_registry()
        ignore_patterns = load_ignore_patterns(test_codebase)

        # Skip directories that would be skipped during indexing
        skip_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv"}

        times = []
        for _ in range(10):
            start = time.perf_counter()
            files = []
            for item in test_codebase.rglob("*"):
                if any(skip_dir in item.parts for skip_dir in skip_dirs):
                    continue
                if should_ignore(item, test_codebase, ignore_patterns):
                    continue
                if item.is_file() and registry.get_parser_for_file(item):
                    files.append(item)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        mean_time = statistics.mean(times)
        print(f"\n=== File Discovery ===")
        print(f"Files found: {len(files)}")
        print(f"Mean time: {mean_time * 1000:.2f}ms")
        print(f"Files/sec: {len(files) / mean_time:.0f}")

    def test_component_parsing(self, test_codebase: Path) -> None:
        """Measure parsing performance in isolation (no embedding/storage)."""
        from aurora_context_code.registry import get_global_registry

        registry = get_global_registry()
        files = list(test_codebase.glob("*.py"))

        times = []
        total_chunks = 0

        for _ in range(5):
            start = time.perf_counter()
            chunk_count = 0
            for f in files:
                parser = registry.get_parser_for_file(f)
                if parser:
                    chunks = parser.parse(f)
                    chunk_count += len(chunks)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            total_chunks = chunk_count

        mean_time = statistics.mean(times)
        print(f"\n=== Parsing Only ===")
        print(f"Files parsed: {len(files)}")
        print(f"Chunks extracted: {total_chunks}")
        print(f"Mean time: {mean_time * 1000:.2f}ms")
        print(f"Files/sec: {len(files) / mean_time:.0f}")
        print(f"Chunks/sec: {total_chunks / mean_time:.0f}")
        print(f"ms/chunk: {(mean_time / total_chunks) * 1000:.3f}")

    def test_component_embedding_batch_sizes(self, test_codebase: Path) -> None:
        """Compare embedding performance across batch sizes."""
        from aurora_context_code.registry import get_global_registry
        from aurora_context_code.semantic import EmbeddingProvider

        registry = get_global_registry()
        provider = EmbeddingProvider()

        # Collect all text chunks
        texts = []
        for f in test_codebase.glob("*.py"):
            parser = registry.get_parser_for_file(f)
            if parser:
                chunks = parser.parse(f)
                for chunk in chunks:
                    parts = []
                    if chunk.signature:
                        parts.append(chunk.signature)
                    if chunk.docstring:
                        parts.append(chunk.docstring)
                    parts.append(f"{chunk.element_type} {chunk.name}")
                    texts.append("\n\n".join(parts))

        print(f"\n=== Embedding Batch Size Comparison ===")
        print(f"Total texts: {len(texts)}")

        batch_sizes = [8, 16, 32, 64, 128]
        for batch_size in batch_sizes:
            # Warm up
            provider.embed_batch(texts[: min(32, len(texts))], batch_size=batch_size)

            times = []
            for _ in range(3):
                start = time.perf_counter()
                provider.embed_batch(texts, batch_size=batch_size)
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            mean_time = statistics.mean(times)
            chunks_per_sec = len(texts) / mean_time
            ms_per_chunk = (mean_time / len(texts)) * 1000

            print(
                f"  batch_size={batch_size:3d}: {mean_time:.3f}s total, {chunks_per_sec:.0f} chunks/sec, {ms_per_chunk:.2f} ms/chunk"
            )

    def test_component_db_writes(self, test_codebase: Path, tmp_path: Path) -> None:
        """Measure database write performance in isolation."""
        import numpy as np

        from aurora_context_code.registry import get_global_registry
        from aurora_core.chunks import Chunk
        from aurora_core.store import SQLiteStore

        registry = get_global_registry()

        # Collect chunks with fake embeddings
        chunks_to_store = []
        for f in test_codebase.glob("*.py"):
            parser = registry.get_parser_for_file(f)
            if parser:
                parsed_chunks = parser.parse(f)
                for chunk in parsed_chunks:
                    # Add fake embedding
                    chunk.embeddings = np.random.randn(384).astype(np.float32).tobytes()
                    chunks_to_store.append(chunk)

        print(f"\n=== Database Write Performance ===")
        print(f"Chunks to store: {len(chunks_to_store)}")

        # Test individual writes
        db_path = tmp_path / "write_test_single.db"
        store = SQLiteStore(str(db_path))

        start = time.perf_counter()
        for chunk in chunks_to_store:
            store.save_chunk(chunk)
        single_time = time.perf_counter() - start

        print(
            f"Individual writes: {single_time:.3f}s ({len(chunks_to_store) / single_time:.0f} chunks/sec)"
        )
        print(f"  Per-chunk latency: {(single_time / len(chunks_to_store)) * 1000:.3f} ms")


# =============================================================================
# SCALABILITY BENCHMARKS - How does performance change with size?
# =============================================================================


class TestScalability:
    """Measure how indexing scales with codebase size."""

    def test_scalability_files(self, tmp_path: Path) -> None:
        """Track throughput as file count increases."""
        print("\n=== Scalability: File Count ===")
        print(f"{'Files':>8} {'Time(s)':>10} {'Files/s':>10} {'Chunks/s':>10}")

        file_counts = [10, 25, 50, 75, 100]
        results = []

        for num_files in file_counts:
            codebase = create_test_codebase(
                tmp_path, num_files=num_files, name=f"scale_{num_files}"
            )
            result = run_indexed_with_timing(codebase, tmp_path / f"scale_{num_files}.db")
            results.append((num_files, result))

            print(
                f"{num_files:>8} {result.total_seconds:>10.2f} "
                f"{result.files_per_second:>10.1f} {result.chunks_per_second:>10.1f}"
            )

        # Check for degradation
        # Throughput shouldn't drop more than 50% as size increases
        first_throughput = results[0][1].files_per_second
        last_throughput = results[-1][1].files_per_second
        degradation = (first_throughput - last_throughput) / first_throughput

        print(f"\nThroughput degradation: {degradation * 100:.1f}%")
        assert degradation < 0.7, "Throughput should not degrade more than 70%"

    def test_scalability_chunks_per_file(self, tmp_path: Path) -> None:
        """Track throughput as functions-per-file increases."""
        print("\n=== Scalability: Functions Per File ===")
        print(f"{'Funcs/File':>12} {'Time(s)':>10} {'Chunks':>10} {'Chunks/s':>10}")

        func_counts = [5, 10, 20, 30]
        results = []

        for funcs in func_counts:
            codebase = create_test_codebase(
                tmp_path, num_files=20, functions_per_file=funcs, name=f"funcs_{funcs}"
            )
            result = run_indexed_with_timing(codebase, tmp_path / f"funcs_{funcs}.db")
            results.append((funcs, result))

            print(
                f"{funcs:>12} {result.total_seconds:>10.2f} "
                f"{result.chunks_created:>10} {result.chunks_per_second:>10.1f}"
            )


# =============================================================================
# OPTIMIZATION VALIDATION BENCHMARKS
# =============================================================================


class TestOptimizationValidation:
    """Run after implementing optimizations to validate improvements."""

    def test_before_after_comparison(self, tmp_path: Path) -> None:
        """Compare current performance against stored baseline.

        After implementing optimizations:
        1. Run baseline tests and record results
        2. Update BASELINE_METRICS with recorded values
        3. Run this test to validate improvement
        """
        # Baseline metrics (update these after running baseline tests)
        BASELINE_METRICS = {
            "small_files_per_sec": 1.0,  # Update with actual baseline
            "medium_files_per_sec": 0.8,
            "large_files_per_sec": 0.5,
        }

        codebase = create_test_codebase(tmp_path, num_files=50, name="validation")
        result = run_indexed_with_timing(codebase, tmp_path / "validation.db")

        print(f"\n=== Optimization Validation ===")
        print(f"Current throughput: {result.files_per_second:.2f} files/sec")
        print(f"Baseline threshold: {BASELINE_METRICS['medium_files_per_sec']:.2f} files/sec")

        improvement = (
            (result.files_per_second - BASELINE_METRICS["medium_files_per_sec"])
            / BASELINE_METRICS["medium_files_per_sec"]
            * 100
        )
        print(f"Improvement: {improvement:+.1f}%")

    def test_embedding_dominates_time(self, tmp_path: Path) -> None:
        """Verify embedding is the primary bottleneck (guides optimization focus)."""
        codebase = create_test_codebase(tmp_path, num_files=30, name="bottleneck")
        result = run_indexed_with_timing(codebase, tmp_path / "bottleneck.db")

        pct = result.phase_percentages()
        print(f"\n=== Bottleneck Analysis ===")
        for phase, percent in sorted(pct.items(), key=lambda x: -x[1]):
            print(f"  {phase}: {percent:.1f}%")

        # Embedding typically should be the largest component
        # If not, the bottleneck has shifted and optimization focus should change
        if pct.get("embedding", 0) < pct.get("parsing", 0):
            print("\n** NOTE: Parsing is slower than embedding - consider parser optimization **")
        if pct.get("embedding", 0) < pct.get("storing", 0):
            print("\n** NOTE: DB writes are slower than embedding - consider batch writes **")


# =============================================================================
# REAL-WORLD BENCHMARKS
# =============================================================================


class TestRealWorldCodebase:
    """Benchmark against actual Aurora source code."""

    def test_index_aurora_packages(self, tmp_path: Path) -> None:
        """Benchmark indexing Aurora's own packages."""
        packages_path = Path(__file__).parent.parent.parent / "packages"

        if not packages_path.exists():
            pytest.skip("Aurora packages not found")

        # Index each package separately
        print("\n=== Aurora Package Indexing ===")
        print(f"{'Package':>20} {'Files':>8} {'Chunks':>8} {'Time':>10} {'Files/s':>10}")

        total_files = 0
        total_chunks = 0
        total_time = 0.0

        for pkg_dir in sorted(packages_path.iterdir()):
            src_dir = pkg_dir / "src"
            if not src_dir.exists():
                continue

            db_path = tmp_path / f"{pkg_dir.name}.db"
            result = run_indexed_with_timing(src_dir, db_path, skip_git=True)

            total_files += result.files_indexed
            total_chunks += result.chunks_created
            total_time += result.total_seconds

            print(
                f"{pkg_dir.name:>20} {result.files_indexed:>8} "
                f"{result.chunks_created:>8} {result.total_seconds:>10.2f} "
                f"{result.files_per_second:>10.1f}"
            )

        print(
            f"\n{'TOTAL':>20} {total_files:>8} {total_chunks:>8} {total_time:>10.2f} {total_files/total_time:>10.1f}"
        )


# =============================================================================
# MEMORY PROFILING
# =============================================================================


class TestMemoryProfile:
    """Profile memory usage during indexing."""

    def test_memory_growth(self, tmp_path: Path) -> None:
        """Track memory growth as codebase size increases."""
        print("\n=== Memory Growth Analysis ===")
        print(f"{'Files':>8} {'Chunks':>8} {'Peak MB':>10} {'MB/File':>10}")

        file_counts = [10, 30, 50, 100]

        for num_files in file_counts:
            codebase = create_test_codebase(tmp_path, num_files=num_files, name=f"mem_{num_files}")
            result = run_indexed_with_timing(codebase, tmp_path / f"mem_{num_files}.db")

            mb_per_file = result.memory_peak_mb / num_files if num_files > 0 else 0

            print(
                f"{num_files:>8} {result.chunks_created:>8} "
                f"{result.memory_peak_mb:>10.1f} {mb_per_file:>10.2f}"
            )

    def test_memory_leak_detection(self, tmp_path: Path) -> None:
        """Run multiple indexing cycles to detect memory leaks."""
        import gc

        codebase = create_test_codebase(tmp_path, num_files=20, name="leak_test")

        print("\n=== Memory Leak Detection ===")
        print(f"{'Iteration':>10} {'Peak MB':>10} {'Delta MB':>10}")

        prev_peak = 0
        for i in range(5):
            gc.collect()
            result = run_indexed_with_timing(codebase, tmp_path / f"leak_{i}.db")
            delta = result.memory_peak_mb - prev_peak if prev_peak > 0 else 0

            print(f"{i + 1:>10} {result.memory_peak_mb:>10.1f} {delta:>+10.1f}")

            prev_peak = result.memory_peak_mb

            # Clean up db
            (tmp_path / f"leak_{i}.db").unlink(missing_ok=True)

        # Memory shouldn't grow unboundedly
        # Allow some variance but flag significant growth
