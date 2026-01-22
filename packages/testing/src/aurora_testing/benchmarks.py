"""Performance benchmarking utilities for AURORA testing.

Provides tools for:
- Timing operations and enforcing performance targets
- Memory profiling and tracking
- Statistical analysis of benchmark results
- Performance regression detection
"""

import gc
import statistics
import time
import tracemalloc
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar


T = TypeVar("T")


# ============================================================================
# Benchmark Results
# ============================================================================


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark.

    Attributes:
        name: Benchmark name.
        duration_ms: Execution time in milliseconds.
        iterations: Number of iterations run.
        mean_ms: Mean execution time per iteration.
        median_ms: Median execution time.
        std_dev_ms: Standard deviation.
        min_ms: Minimum execution time.
        max_ms: Maximum execution time.
        memory_peak_mb: Peak memory usage in MB.
        memory_delta_mb: Change in memory usage.
        passed: Whether benchmark met target criteria.
        target_ms: Target execution time (if specified).
        metadata: Additional metadata.

    """

    name: str
    duration_ms: float
    iterations: int = 1
    mean_ms: float = 0.0
    median_ms: float = 0.0
    std_dev_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0
    passed: bool = True
    target_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format benchmark result as string."""
        status = "✓ PASS" if self.passed else "✗ FAIL"
        lines = [
            f"{status} {self.name}",
            f"  Duration: {self.duration_ms:.2f}ms",
        ]

        if self.iterations > 1:
            lines.extend(
                [
                    f"  Iterations: {self.iterations}",
                    f"  Mean: {self.mean_ms:.2f}ms",
                    f"  Median: {self.median_ms:.2f}ms",
                    f"  Std Dev: {self.std_dev_ms:.2f}ms",
                    f"  Range: {self.min_ms:.2f}ms - {self.max_ms:.2f}ms",
                ],
            )

        if self.target_ms:
            lines.append(f"  Target: {self.target_ms:.2f}ms")

        if self.memory_peak_mb > 0:
            lines.append(f"  Memory Peak: {self.memory_peak_mb:.2f}MB")

        if self.memory_delta_mb != 0:
            lines.append(f"  Memory Delta: {self.memory_delta_mb:+.2f}MB")

        return "\n".join(lines)


# ============================================================================
# Performance Timer
# ============================================================================


class PerformanceTimer:
    """High-resolution timer for performance measurement.

    Examples:
        >>> with PerformanceTimer() as timer:
        ...     # Code to benchmark
        ...     result = expensive_operation()
        >>> print(f"Took {timer.elapsed_ms:.2f}ms")

        >>> timer = PerformanceTimer()
        >>> timer.start()
        >>> result = operation()
        >>> timer.stop()
        >>> assert timer.elapsed_ms < 100

    """

    def __init__(self) -> None:
        """Initialize timer."""
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.elapsed_ms: float = 0.0

    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.perf_counter()
        self.end_time = None

    def stop(self) -> float:
        """Stop the timer and return elapsed time.

        Returns:
            Elapsed time in milliseconds.

        """
        if self.start_time is None:
            raise RuntimeError("Timer was not started")

        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000
        return self.elapsed_ms

    def __enter__(self) -> "PerformanceTimer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


# ============================================================================
# Performance Benchmark
# ============================================================================


class PerformanceBenchmark:
    """Main benchmarking utility for performance testing.

    Provides comprehensive performance measurement including:
    - Execution time tracking
    - Multiple iteration support with statistics
    - Memory profiling
    - Target enforcement
    - Result reporting

    Examples:
        >>> benchmark = PerformanceBenchmark("Parse 1000 lines")
        >>> benchmark.set_target(200)  # 200ms target
        >>> result = benchmark.run(lambda: parser.parse(large_file))
        >>> assert result.passed

        >>> # Multiple iterations
        >>> result = benchmark.run(operation, iterations=10)
        >>> print(f"Mean: {result.mean_ms:.2f}ms")

        >>> # With memory profiling
        >>> result = benchmark.run(operation, track_memory=True)
        >>> print(f"Memory: {result.memory_peak_mb:.2f}MB")

    """

    def __init__(self, name: str = "Benchmark") -> None:
        """Initialize benchmark.

        Args:
            name: Benchmark name for reporting.

        """
        self.name = name
        self.target_ms: float | None = None
        self.warmup_iterations: int = 0
        self.results_history: list[BenchmarkResult] = []

    def set_target(self, target_ms: float) -> None:
        """Set performance target.

        Args:
            target_ms: Target execution time in milliseconds.

        """
        self.target_ms = target_ms

    def set_warmup(self, iterations: int) -> None:
        """Set number of warmup iterations (not measured).

        Args:
            iterations: Number of warmup iterations.

        """
        self.warmup_iterations = iterations

    def run(
        self,
        func: Callable[[], T],
        iterations: int = 1,
        track_memory: bool = False,
        fail_on_target_miss: bool = False,
    ) -> BenchmarkResult:
        """Run benchmark on function.

        Args:
            func: Function to benchmark (no arguments).
            iterations: Number of iterations to run.
            track_memory: Whether to track memory usage.
            fail_on_target_miss: Raise AssertionError if target missed.

        Returns:
            BenchmarkResult with timing and statistics.

        Raises:
            AssertionError: If fail_on_target_miss and target not met.

        """
        # Warmup
        for _ in range(self.warmup_iterations):
            func()

        # Collect garbage before measurement
        gc.collect()

        # Track memory if requested
        memory_peak_mb = 0.0
        memory_delta_mb = 0.0
        if track_memory:
            tracemalloc.start()
            memory_before = tracemalloc.get_traced_memory()[0]

        # Run iterations and collect timings
        timings: list[float] = []
        total_start = time.perf_counter()

        for _ in range(iterations):
            timer = PerformanceTimer()
            timer.start()
            func()
            elapsed = timer.stop()
            timings.append(elapsed)

        total_duration = (time.perf_counter() - total_start) * 1000

        # Memory tracking
        if track_memory:
            memory_after, peak = tracemalloc.get_traced_memory()
            memory_peak_mb = peak / (1024 * 1024)
            memory_delta_mb = (memory_after - memory_before) / (1024 * 1024)
            tracemalloc.stop()

        # Calculate statistics
        mean_ms = statistics.mean(timings) if timings else 0.0
        median_ms = statistics.median(timings) if timings else 0.0
        std_dev_ms = statistics.stdev(timings) if len(timings) > 1 else 0.0
        min_ms = min(timings) if timings else 0.0
        max_ms = max(timings) if timings else 0.0

        # Check if target met
        passed = True
        if self.target_ms is not None:
            # Use mean for multi-iteration, total for single
            check_time = mean_ms if iterations > 1 else total_duration
            passed = check_time <= self.target_ms

        # Create result
        result = BenchmarkResult(
            name=self.name,
            duration_ms=total_duration,
            iterations=iterations,
            mean_ms=mean_ms,
            median_ms=median_ms,
            std_dev_ms=std_dev_ms,
            min_ms=min_ms,
            max_ms=max_ms,
            memory_peak_mb=memory_peak_mb,
            memory_delta_mb=memory_delta_mb,
            passed=passed,
            target_ms=self.target_ms,
        )

        # Store in history
        self.results_history.append(result)

        # Fail if requested
        if fail_on_target_miss and not passed:
            raise AssertionError(
                f"Benchmark '{self.name}' failed: "
                f"{mean_ms if iterations > 1 else total_duration:.2f}ms > "
                f"{self.target_ms}ms target",
            )

        return result

    def compare_to_baseline(
        self,
        baseline_ms: float,
        tolerance_percent: float = 10.0,
    ) -> bool:
        """Compare most recent result to baseline.

        Args:
            baseline_ms: Baseline execution time.
            tolerance_percent: Acceptable regression percentage.

        Returns:
            True if within tolerance, False if regressed.

        Raises:
            ValueError: If no results available.

        """
        if not self.results_history:
            raise ValueError("No benchmark results available")

        latest = self.results_history[-1]
        check_time = latest.mean_ms if latest.iterations > 1 else latest.duration_ms

        max_allowed = baseline_ms * (1 + tolerance_percent / 100)
        return check_time <= max_allowed


# ============================================================================
# Benchmark Decorator
# ============================================================================


def benchmark(
    name: str | None = None,
    target_ms: float | None = None,
    track_memory: bool = False,
    iterations: int = 1,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for benchmarking functions.

    Args:
        name: Benchmark name (defaults to function name).
        target_ms: Performance target in milliseconds.
        track_memory: Whether to track memory usage.
        iterations: Number of iterations to run.

    Examples:
        >>> @benchmark(name="Fast operation", target_ms=50)
        ... def fast_op():
        ...     return sum(range(1000))

        >>> @benchmark(track_memory=True, iterations=10)
        ... def memory_intensive():
        ...     return [0] * 1000000

    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        bench_name = name or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            bench = PerformanceBenchmark(bench_name)
            if target_ms:
                bench.set_target(target_ms)

            # Wrap function to capture return value
            result_container: list[T] = []

            def run_func() -> T:
                result = func(*args, **kwargs)
                result_container.append(result)
                return result

            bench_result = bench.run(
                run_func,
                iterations=iterations,
                track_memory=track_memory,
            )

            # Print result (in test context)
            print(bench_result)

            # Return original function result (guaranteed to have at least one result)
            assert result_container, "Function must be called at least once"
            return result_container[-1]

        return wrapper

    return decorator


# ============================================================================
# Memory Profiler
# ============================================================================


class MemoryProfiler:
    """Memory profiling utility.

    Examples:
        >>> profiler = MemoryProfiler()
        >>> profiler.start()
        >>> data = [0] * 1000000
        >>> stats = profiler.stop()
        >>> print(f"Peak: {stats['peak_mb']:.2f}MB")

    """

    def __init__(self) -> None:
        """Initialize profiler."""
        self.is_running = False
        self.start_memory = 0
        self.snapshots: list[tuple[str, int]] = []

    def start(self) -> None:
        """Start memory profiling."""
        if self.is_running:
            raise RuntimeError("Profiler already running")

        gc.collect()
        tracemalloc.start()
        self.start_memory = tracemalloc.get_traced_memory()[0]
        self.is_running = True
        self.snapshots.clear()

    def snapshot(self, label: str = "") -> None:
        """Take a memory snapshot.

        Args:
            label: Optional label for snapshot.

        """
        if not self.is_running:
            raise RuntimeError("Profiler not running")

        current = tracemalloc.get_traced_memory()[0]
        self.snapshots.append((label, current))

    def stop(self) -> dict[str, float]:
        """Stop profiling and return statistics.

        Returns:
            Dictionary with memory statistics in MB.

        """
        if not self.is_running:
            raise RuntimeError("Profiler not running")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.is_running = False

        return {
            "start_mb": self.start_memory / (1024 * 1024),
            "end_mb": current / (1024 * 1024),
            "peak_mb": peak / (1024 * 1024),
            "delta_mb": (current - self.start_memory) / (1024 * 1024),
        }

    @contextmanager
    def profile(self) -> Any:  # Generator[MemoryProfiler, None, None]
        """Context manager for memory profiling.

        Yields:
            MemoryProfiler: Active profiler instance.

        Examples:
            >>> profiler = MemoryProfiler()
            >>> with profiler.profile():
            ...     data = create_large_data()
            ...     profiler.snapshot("after creation")
            >>> stats = profiler.stop()

        """
        self.start()
        try:
            yield self
        finally:
            if self.is_running:
                self.stop()


# ============================================================================
# Benchmark Suite
# ============================================================================


class BenchmarkSuite:
    """Collection of related benchmarks.

    Examples:
        >>> suite = BenchmarkSuite("Parser Benchmarks")
        >>> suite.add("Small file", lambda: parser.parse(small), target_ms=50)
        >>> suite.add("Large file", lambda: parser.parse(large), target_ms=200)
        >>> results = suite.run_all()
        >>> suite.print_summary()

    """

    def __init__(self, name: str = "Benchmark Suite") -> None:
        """Initialize suite.

        Args:
            name: Suite name.

        """
        self.name = name
        self.benchmarks: list[tuple[str, Callable[..., Any], dict[str, Any]]] = []
        self.results: list[BenchmarkResult] = []

    def add(
        self,
        name: str,
        func: Callable[..., Any],
        target_ms: float | None = None,
        iterations: int = 1,
        track_memory: bool = False,
    ) -> None:
        """Add benchmark to suite.

        Args:
            name: Benchmark name.
            func: Function to benchmark.
            target_ms: Performance target.
            iterations: Number of iterations.
            track_memory: Whether to track memory.

        """
        options = {
            "target_ms": target_ms,
            "iterations": iterations,
            "track_memory": track_memory,
        }
        self.benchmarks.append((name, func, options))

    def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmarks in suite.

        Returns:
            List of benchmark results.

        """
        self.results.clear()

        for name, func, options in self.benchmarks:
            bench = PerformanceBenchmark(name)
            if options["target_ms"]:
                bench.set_target(options["target_ms"])

            result = bench.run(
                func,
                iterations=options["iterations"],
                track_memory=options["track_memory"],
            )
            self.results.append(result)

        return self.results

    def print_summary(self) -> None:
        """Print summary of all results."""
        if not self.results:
            print(f"{self.name}: No results")
            return

        print(f"\n{'=' * 70}")
        print(f"{self.name}")
        print(f"{'=' * 70}")

        for result in self.results:
            print(result)
            print()

        # Overall statistics
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"{'=' * 70}")
        print(f"Summary: {passed}/{total} benchmarks passed")

    def all_passed(self) -> bool:
        """Check if all benchmarks passed.

        Returns:
            True if all passed, False otherwise.

        """
        return all(r.passed for r in self.results)
