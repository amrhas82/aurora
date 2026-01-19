#!/usr/bin/env python3
"""Profile memory indexing to identify bottlenecks."""

import cProfile
import pstats
import tempfile
import time
from io import StringIO
from pathlib import Path

from aurora_cli.config import Config
from aurora_cli.memory_manager import IndexProgress, MemoryManager


def profile_indexing():
    """Profile the indexing process with detailed timing."""

    # Use a test directory
    test_path = Path("/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli")

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    config = Config(db_path=db_path)
    manager = MemoryManager(config=config)

    # Track phase timings
    phase_times = {}
    phase_start = None
    current_phase = None

    def progress_callback(prog: IndexProgress) -> None:
        nonlocal phase_start, current_phase, phase_times

        # Record phase transition
        if prog.phase != current_phase:
            if current_phase and phase_start:
                duration = time.time() - phase_start
                phase_times[current_phase] = phase_times.get(current_phase, 0) + duration

            current_phase = prog.phase
            phase_start = time.time()

    print(f"Profiling indexing of: {test_path}")
    print(f"Database: {db_path}")
    print()

    # Profile with cProfile
    profiler = cProfile.Profile()
    profiler.enable()

    overall_start = time.time()
    stats = manager.index_path(test_path, progress_callback=progress_callback)
    overall_duration = time.time() - overall_start

    profiler.disable()

    # Record final phase
    if current_phase and phase_start:
        duration = time.time() - phase_start
        phase_times[current_phase] = phase_times.get(current_phase, 0) + duration

    # Print phase timing breakdown
    print("=" * 80)
    print("PHASE TIMING BREAKDOWN")
    print("=" * 80)

    for phase in ["discovering", "parsing", "git_blame", "embedding", "storing", "complete"]:
        if phase in phase_times:
            duration = phase_times[phase]
            percent = (duration / overall_duration) * 100
            print(f"{phase:15s}: {duration:7.2f}s ({percent:5.1f}%)")

    print("-" * 80)
    print(f"{'Total':15s}: {overall_duration:7.2f}s (100.0%)")
    print()

    # Print indexing stats
    print("=" * 80)
    print("INDEXING STATS")
    print("=" * 80)
    print(f"Files indexed:  {stats.files_indexed}")
    print(f"Chunks created: {stats.chunks_created}")
    print(f"Errors:         {stats.errors}")
    print(f"Warnings:       {stats.warnings}")
    print(f"Duration:       {stats.duration_seconds:.2f}s")
    print()

    # Calculate throughput
    if stats.files_indexed > 0:
        files_per_sec = stats.files_indexed / overall_duration
        chunks_per_sec = stats.chunks_created / overall_duration
        print(f"Throughput:     {files_per_sec:.1f} files/sec, {chunks_per_sec:.1f} chunks/sec")
        print()

    # Print top time-consuming functions
    print("=" * 80)
    print("TOP 30 TIME-CONSUMING FUNCTIONS")
    print("=" * 80)

    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats("cumulative")
    ps.print_stats(30)

    print(s.getvalue())

    print("=" * 80)
    print("TOP 30 FUNCTIONS BY TOTAL TIME (excluding subcalls)")
    print("=" * 80)

    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats("time")
    ps.print_stats(30)

    print(s.getvalue())

    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    print(f"\nCleaned up temp database: {db_path}")


if __name__ == "__main__":
    profile_indexing()
