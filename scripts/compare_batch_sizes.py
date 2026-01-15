#!/usr/bin/env python3
"""Compare embedding batch sizes for optimal throughput.

Tests different batch sizes to find the sweet spot between
memory usage and parallelization efficiency.

Usage:
    python compare_batch_sizes.py [path_to_index]
"""

import time
from pathlib import Path

from aurora_cli.config import load_config
from aurora_cli.memory_manager import MemoryManager


def benchmark_batch_size(path: Path, batch_size: int) -> dict:
    """Benchmark indexing with a specific batch size.

    Args:
        path: Path to index
        batch_size: Embedding batch size

    Returns:
        Dictionary with timing results
    """
    import tempfile

    config = load_config()
    temp_db = Path(tempfile.mktemp(suffix=".db"))
    config.db_path = str(temp_db)

    try:
        manager = MemoryManager(config=config)

        start = time.perf_counter()
        stats = manager.index_path(path, batch_size=batch_size)
        elapsed = time.perf_counter() - start

        return {
            "batch_size": batch_size,
            "total_time": elapsed,
            "files_processed": stats.files_indexed,
            "chunks_created": stats.chunks_created,
            "throughput": stats.chunks_created / elapsed,
        }

    finally:
        if temp_db.exists():
            temp_db.unlink()


def main():
    """Main benchmark runner."""
    import sys

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        # Default to small test directory
        path = Path(__file__).parent / "packages" / "cli" / "src" / "aurora_cli" / "commands"

    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)

    # Test batch sizes
    batch_sizes = [8, 16, 32, 64, 128, 256]

    print("=" * 80)
    print("BATCH SIZE COMPARISON")
    print("=" * 80)
    print(f"\nIndexing path: {path}")
    print("Testing batch sizes: 8, 16, 32, 64, 128, 256\n")

    results = []
    for batch_size in batch_sizes:
        print(f"Testing batch_size={batch_size}...", end=" ", flush=True)
        result = benchmark_batch_size(path, batch_size)
        results.append(result)
        print(f"{result['total_time']:.1f}s ({result['throughput']:.1f} chunks/s)")

    # Find optimal
    optimal = max(results, key=lambda x: x["throughput"])

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n{'Batch Size':<12} {'Time (s)':<10} {'Throughput':<15} {'vs Optimal':<12}")
    print("-" * 80)

    for r in results:
        speedup_pct = (r["throughput"] / optimal["throughput"] - 1) * 100
        speedup_str = f"{speedup_pct:+.1f}%" if r != optimal else "OPTIMAL"
        print(
            f"{r['batch_size']:<12} {r['total_time']:>8.1f}   {r['throughput']:>8.1f} chunks/s   {speedup_str:<12}"
        )

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(f"\nOptimal batch size: {optimal['batch_size']}")
    print(f"  Throughput: {optimal['throughput']:.1f} chunks/s")
    print(f"  Total time: {optimal['total_time']:.1f}s")

    # Estimate memory usage
    print("\nEstimated memory per batch:")
    for batch_size in [32, 64, 128, 256]:
        # Rough estimate: ~1MB per embedding (384 dims * 4 bytes * batch_size)
        mem_mb = (batch_size * 384 * 4) / (1024 * 1024)
        print(f"  batch_size={batch_size:>3}: ~{mem_mb:.1f}MB")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
