#!/usr/bin/env python3
# Profile memory search implementation to identify bottlenecks

import cProfile
import pstats
import time
from io import StringIO
from pathlib import Path

from aurora_cli.config import load_config
from aurora_cli.memory_manager import MemoryManager


def profile_search_operation():
    config = load_config()
    db_path = Path(config.get_db_path())

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Run aur init and aur mem index . first")
        return

    print("=" * 80)
    print("MEMORY SEARCH PROFILING REPORT")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Size: {db_path.stat().st_size / (1024*1024):.2f} MB")
    print()

    manager = MemoryManager(config=config)
    stats = manager.get_stats()

    print("Database Statistics:")
    print(f"  Total Chunks: {stats.total_chunks:,}")
    print(f"  Total Files: {stats.total_files:,}")
    print()

    test_queries = [
        ("authentication", "Simple keyword"),
        ("parse python code", "Natural language"),
    ]

    for query, desc in test_queries:
        print(f"Query: {query} ({desc})")
        print("-" * 80)

        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        results = manager.search(query, limit=10)
        total_time = time.perf_counter() - start_time

        profiler.disable()

        print(f"Total Time: {total_time*1000:.2f}ms")
        print(f"Results: {len(results)}")
        print()

        s = StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.strip_dirs()
        ps.sort_stats("cumulative")
        ps.print_stats(15)
        print(s.getvalue())
        print("=" * 80)
        print()


if __name__ == "__main__":
    profile_search_operation()
