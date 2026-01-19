#!/usr/bin/env python3
"""Profile memory indexing performance with detailed metrics.

This script profiles the `aur mem index` operation to identify bottlenecks
in I/O, CPU, and memory usage patterns.
"""

import cProfile
import io
import pstats
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from pstats import SortKey

import psutil


def profile_indexing_with_memory_tracking(test_path: Path):
    """Profile indexing with memory and CPU tracking."""

    print(f"Profiling indexing of: {test_path}")
    print(f"Files to index: {sum(1 for _ in test_path.rglob('*.py'))}")
    print()

    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Get process handle for monitoring
        process = psutil.Process()

        # Memory tracking
        mem_samples = []
        cpu_samples = []
        io_samples = []

        # Start profiling
        profiler = cProfile.Profile()

        start_time = time.time()
        start_mem = process.memory_info().rss / 1024 / 1024  # MB
        start_io = process.io_counters()

        profiler.enable()

        # Import after profiler starts to capture all overhead
        from aurora_cli.config import Config
        from aurora_cli.memory_manager import MemoryManager

        config = Config(db_path=str(db_path))
        manager = MemoryManager(config=config)

        # Sample metrics during indexing
        def progress_callback(progress):
            nonlocal mem_samples, cpu_samples, io_samples
            mem_samples.append(process.memory_info().rss / 1024 / 1024)
            cpu_samples.append(process.cpu_percent())
            try:
                io_current = process.io_counters()
                io_samples.append(
                    {
                        "read_bytes": io_current.read_bytes,
                        "write_bytes": io_current.write_bytes,
                        "read_count": io_current.read_count,
                        "write_count": io_current.write_count,
                    }
                )
            except Exception:
                pass

        # Run indexing
        stats = manager.index_path(test_path, progress_callback=progress_callback)

        profiler.disable()

        end_time = time.time()
        end_mem = process.memory_info().rss / 1024 / 1024  # MB
        end_io = process.io_counters()

        duration = end_time - start_time

        # Print summary
        print("=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        print("\nIndexing Stats:")
        print(f"  Files indexed: {stats.files_indexed}")
        print(f"  Chunks created: {stats.chunks_created}")
        print(f"  Duration: {stats.duration_seconds:.2f}s")
        print(f"  Files/sec: {stats.files_indexed / duration:.1f}")
        print(f"  Chunks/sec: {stats.chunks_created / duration:.1f}")

        print("\nMemory Usage:")
        print(f"  Start: {start_mem:.1f} MB")
        print(f"  End: {end_mem:.1f} MB")
        print(f"  Delta: {end_mem - start_mem:.1f} MB")
        print(f"  Peak: {max(mem_samples):.1f} MB" if mem_samples else "N/A")
        print(f"  Avg: {sum(mem_samples)/len(mem_samples):.1f} MB" if mem_samples else "N/A")

        print("\nI/O Stats:")
        io_read_mb = (end_io.read_bytes - start_io.read_bytes) / 1024 / 1024
        io_write_mb = (end_io.write_bytes - start_io.write_bytes) / 1024 / 1024
        print(f"  Read: {io_read_mb:.1f} MB ({end_io.read_count - start_io.read_count} ops)")
        print(f"  Write: {io_write_mb:.1f} MB ({end_io.write_count - start_io.write_count} ops)")
        print(f"  Total I/O: {io_read_mb + io_write_mb:.1f} MB")
        print(
            f"  I/O per file: {(io_read_mb + io_write_mb) / stats.files_indexed:.2f} MB"
            if stats.files_indexed > 0
            else "N/A"
        )

        print("\nCPU Usage:")
        print(f"  Avg CPU: {sum(cpu_samples)/len(cpu_samples):.1f}%" if cpu_samples else "N/A")
        print(f"  Peak CPU: {max(cpu_samples):.1f}%" if cpu_samples else "N/A")

        # Print detailed profiling stats
        print("\n" + "=" * 80)
        print("DETAILED PROFILING (Top 30 functions by cumulative time)")
        print("=" * 80 + "\n")

        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.print_stats(30)
        print(s.getvalue())

        # Print top time consumers
        print("\n" + "=" * 80)
        print("TOP TIME CONSUMERS (by total time)")
        print("=" * 80 + "\n")

        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.TIME)
        ps.print_stats(20)
        print(s.getvalue())

        # Analyze hotspots
        print("\n" + "=" * 80)
        print("BOTTLENECK ANALYSIS")
        print("=" * 80 + "\n")

        # Extract key metrics
        stats_obj = pstats.Stats(profiler)
        total_time = sum(stat[2] for stat in stats_obj.stats.values())

        # Find expensive operations
        expensive_ops = {}
        for func, stat in stats_obj.stats.items():
            func_name = f"{func[0]}:{func[1]}({func[2]})"
            total_func_time = stat[2]
            if total_func_time > total_time * 0.01:  # >1% of total time
                expensive_ops[func_name] = {
                    "time": total_func_time,
                    "percent": (total_func_time / total_time) * 100,
                    "calls": stat[0],
                }

        # Categorize by operation type
        categories = {
            "parsing": [],
            "embedding": [],
            "git": [],
            "database": [],
            "io": [],
            "other": [],
        }

        for func_name, data in sorted(
            expensive_ops.items(), key=lambda x: x[1]["time"], reverse=True
        )[:15]:
            entry = f"  {data['percent']:5.1f}% | {data['time']:7.2f}s | {data['calls']:>6} calls | {func_name}"

            if "parse" in func_name.lower() or "tree_sitter" in func_name.lower():
                categories["parsing"].append(entry)
            elif "embed" in func_name.lower() or "transformers" in func_name.lower():
                categories["embedding"].append(entry)
            elif "git" in func_name.lower() or "blame" in func_name.lower():
                categories["git"].append(entry)
            elif (
                "sql" in func_name.lower()
                or "database" in func_name.lower()
                or "sqlite" in func_name.lower()
            ):
                categories["database"].append(entry)
            elif (
                "read" in func_name.lower()
                or "write" in func_name.lower()
                or "open" in func_name.lower()
            ):
                categories["io"].append(entry)
            else:
                categories["other"].append(entry)

        for category, entries in categories.items():
            if entries:
                print(f"\n{category.upper()}:")
                for entry in entries:
                    print(entry)

        # Database analysis
        print("\n" + "=" * 80)
        print("DATABASE ANALYSIS")
        print("=" * 80 + "\n")

        db_size = db_path.stat().st_size / 1024 / 1024
        print(f"Database size: {db_size:.1f} MB")
        print(
            f"Size per file: {db_size / stats.files_indexed:.2f} MB"
            if stats.files_indexed > 0
            else "N/A"
        )
        print(
            f"Size per chunk: {db_size / stats.chunks_created:.4f} MB"
            if stats.chunks_created > 0
            else "N/A"
        )

        # Recommendations
        print("\n" + "=" * 80)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 80 + "\n")

        recommendations = []

        # Memory recommendations
        mem_delta = end_mem - start_mem
        if mem_delta > 500:
            recommendations.append(
                "⚠️  HIGH MEMORY USAGE: Consider reducing batch size or streaming embeddings"
            )

        # I/O recommendations
        if io_read_mb > stats.files_indexed * 0.5:  # >0.5MB per file
            recommendations.append("⚠️  HIGH I/O: Consider file reading optimizations or caching")

        # Speed recommendations
        files_per_sec = stats.files_indexed / duration
        if files_per_sec < 10:
            recommendations.append(
                "⚠️  LOW THROUGHPUT: Consider parallelization or batch processing"
            )

        if recommendations:
            for rec in recommendations:
                print(rec)
        else:
            print("✓ Performance looks reasonable")

        return stats


if __name__ == "__main__":
    # Profile on a subset of the codebase
    test_paths = [
        Path("/home/hamr/PycharmProjects/aurora/packages/cli/src"),
        Path("/home/hamr/PycharmProjects/aurora/packages/core/src"),
        # Path("/home/hamr/PycharmProjects/aurora"),  # Full codebase
    ]

    for test_path in test_paths:
        if test_path.exists():
            print(f"\n{'='*80}")
            print(f"Testing: {test_path}")
            print(f"{'='*80}\n")
            profile_indexing_with_memory_tracking(test_path)
            print("\n\n")
            break
