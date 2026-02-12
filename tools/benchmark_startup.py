#!/usr/bin/env python3
"""Benchmark SOAR startup optimizations."""

import tempfile
import time
from pathlib import Path

from aurora_core.chunks import CodeChunk
from aurora_core.store.connection_pool import get_connection_pool
from aurora_core.store.sqlite import SQLiteStore


def benchmark_store_creation(iterations=10):
    """Benchmark Store creation with and without connection pooling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create and populate database
        store = SQLiteStore(str(db_path))
        for i in range(5):
            chunk = CodeChunk(
                chunk_id=f"chunk-{i}",
                file_path=f"/tmp/test{i}.py",
                element_type="function",
                name=f"func{i}",
                line_start=1,
                line_end=10,
                signature=f"def func{i}():",
                docstring=f"Function {i}",
                language="python",
            )
            store.save_chunk(chunk)
        store.close()

        print(f"Benchmarking Store creation ({iterations} iterations)...")
        print("=" * 60)

        # Benchmark with connection pool
        times_with_pool = []
        for i in range(iterations):
            start = time.perf_counter()
            s = SQLiteStore(str(db_path))
            _ = s.get_chunk("chunk-0")  # Force connection
            elapsed = (time.perf_counter() - start) * 1000
            times_with_pool.append(elapsed)
            s.close()

        avg_with_pool = sum(times_with_pool) / len(times_with_pool)
        min_with_pool = min(times_with_pool)
        max_with_pool = max(times_with_pool)

        # Clear pool to test without caching
        get_connection_pool().clear_pool()

        # Benchmark without connection pool (fresh each time)
        times_without_pool = []
        for i in range(iterations):
            get_connection_pool().clear_pool(str(db_path))  # Clear before each
            start = time.perf_counter()
            s = SQLiteStore(str(db_path))
            _ = s.get_chunk("chunk-0")  # Force connection
            elapsed = (time.perf_counter() - start) * 1000
            times_without_pool.append(elapsed)
            s.close()

        avg_without_pool = sum(times_without_pool) / len(times_without_pool)
        min_without_pool = min(times_without_pool)
        max_without_pool = max(times_without_pool)

        print("\nWith Connection Pool:")
        print(f"  Average: {avg_with_pool:.2f}ms")
        print(f"  Min:     {min_with_pool:.2f}ms")
        print(f"  Max:     {max_with_pool:.2f}ms")

        print("\nWithout Connection Pool (cleared before each):")
        print(f"  Average: {avg_without_pool:.2f}ms")
        print(f"  Min:     {min_without_pool:.2f}ms")
        print(f"  Max:     {max_without_pool:.2f}ms")

        improvement = ((avg_without_pool - avg_with_pool) / avg_without_pool) * 100
        print(f"\nImprovement: {improvement:.1f}%")

        if improvement > 10:
            print("✓ Connection pooling is providing significant benefit")
        elif improvement > 0:
            print("✓ Connection pooling is providing some benefit")
        else:
            print("⚠ No measurable improvement (database may be too small)")


def benchmark_deferred_init():
    """Benchmark deferred schema initialization."""
    print("\n\nBenchmarking Deferred Schema Initialization...")
    print("=" * 60)

    iterations = 50

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # First, create database
        store = SQLiteStore(str(db_path))
        chunk = CodeChunk(
            chunk_id="test",
            file_path="/tmp/test.py",
            element_type="function",
            name="test",
            line_start=1,
            line_end=10,
            signature="def test():",
            docstring="Test",
            language="python",
        )
        store.save_chunk(chunk)
        store.close()
        get_connection_pool().clear_pool()

        # Measure __init__ time only (before deferred init optimization)
        init_times = []
        for _ in range(iterations):
            get_connection_pool().clear_pool(str(db_path))
            start = time.perf_counter()
            s = SQLiteStore(str(db_path))
            init_time = (time.perf_counter() - start) * 1000
            init_times.append(init_time)
            # Don't access DB - just measure __init__
            s.close()

        avg_init = sum(init_times) / len(init_times)
        print(f"\nStore.__init__() average: {avg_init:.3f}ms")
        print("  This includes: directory check, thread-local setup")
        print("  Schema init is deferred until first DB operation")

        # Measure first DB access time
        access_times = []
        for _ in range(iterations):
            get_connection_pool().clear_pool(str(db_path))
            s = SQLiteStore(str(db_path))
            start = time.perf_counter()
            _ = s.get_chunk("test")  # First DB access triggers schema init
            access_time = (time.perf_counter() - start) * 1000
            access_times.append(access_time)
            s.close()

        avg_access = sum(access_times) / len(access_times)
        print(f"\nFirst DB access average: {avg_access:.3f}ms")
        print("  This includes: connection pool lookup, schema init, query")

        print(f"\nTotal average (init + first access): {avg_init + avg_access:.3f}ms")
        print("  Without deferred init, this would all happen in __init__")


if __name__ == "__main__":
    benchmark_store_creation(iterations=20)
    benchmark_deferred_init()
