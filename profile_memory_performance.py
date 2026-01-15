#!/usr/bin/env python3
"""Memory indexing and query performance profiler.

Profiles memory operations to establish baseline metrics:
- Indexing throughput (files/sec, chunks/sec)
- Query latency (semantic, hybrid, BM25)
- Database I/O performance
- Embedding generation speed
- Memory usage patterns
"""

import json
import sqlite3
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aurora_cli.config import load_config
from aurora_cli.memory_manager import MemoryManager


@dataclass
class IndexingMetrics:
    """Metrics from indexing operation."""

    total_files: int
    total_chunks: int
    duration_seconds: float
    files_per_second: float
    chunks_per_second: float
    avg_file_parse_ms: float
    avg_chunk_embed_ms: float
    db_write_ms: float
    git_extraction_ms: float
    errors: int
    warnings: int


@dataclass
class QueryMetrics:
    """Metrics from query operation."""

    query: str
    result_count: int
    total_ms: float
    semantic_ms: float
    bm25_ms: float
    hybrid_ms: float
    activation_ms: float
    avg_score: float
    min_score: float
    max_score: float


@dataclass
class DatabaseMetrics:
    """Database-level metrics."""

    total_chunks: int
    total_files: int
    db_size_mb: float
    index_count: int
    table_count: int
    avg_chunk_size_bytes: int
    chunk_distribution: dict[str, int]  # type -> count


def profile_indexing(test_dir: Path, db_path: Path) -> IndexingMetrics:
    """Profile indexing performance on a test directory.

    Args:
        test_dir: Directory to index
        db_path: Database path for test

    Returns:
        IndexingMetrics with timing data
    """
    print(f"\n{'='*60}")
    print("INDEXING PERFORMANCE PROFILE")
    print(f"{'='*60}")
    print(f"Test directory: {test_dir}")
    print(f"Database: {db_path}")

    # Create config with test DB
    config = load_config()
    config.db_path = str(db_path)

    # Initialize manager
    manager = MemoryManager(config=config)

    # Track phase timings
    phase_times: dict[str, list[float]] = defaultdict(list)
    phase_start: dict[str, float] = {}

    def progress_callback(progress) -> None:
        """Track phase transitions for timing."""
        current_phase = progress.phase
        current_time = time.time()

        # End previous phase
        for phase in phase_start:
            if phase != current_phase:
                elapsed = current_time - phase_start[phase]
                phase_times[phase].append(elapsed)
                del phase_start[phase]
                break

        # Start new phase
        if current_phase not in phase_start:
            phase_start[current_phase] = current_time

    # Run indexing
    print("\nIndexing files...")
    start = time.time()
    stats = manager.index_path(test_dir, progress_callback=progress_callback)
    duration = time.time() - start

    # Calculate derived metrics
    files_per_sec = stats.files_indexed / duration if duration > 0 else 0
    chunks_per_sec = stats.chunks_created / duration if duration > 0 else 0
    avg_file_ms = (duration / stats.files_indexed * 1000) if stats.files_indexed > 0 else 0

    # Estimate phase durations (from accumulated times)
    git_time = sum(phase_times.get("git_blame", [0]))
    embed_time = sum(phase_times.get("embedding", [0]))
    store_time = sum(phase_times.get("storing", [0]))
    parse_time = sum(phase_times.get("parsing", [0]))

    avg_chunk_embed_ms = (
        (embed_time / stats.chunks_created * 1000) if stats.chunks_created > 0 else 0
    )

    metrics = IndexingMetrics(
        total_files=stats.files_indexed,
        total_chunks=stats.chunks_created,
        duration_seconds=duration,
        files_per_second=files_per_sec,
        chunks_per_second=chunks_per_sec,
        avg_file_parse_ms=avg_file_ms,
        avg_chunk_embed_ms=avg_chunk_embed_ms,
        db_write_ms=store_time * 1000,
        git_extraction_ms=git_time * 1000,
        errors=stats.errors,
        warnings=stats.warnings,
    )

    # Display results
    print(f"\n{'Results:':<30}")
    print(f"  Files indexed:        {metrics.total_files:>8,}")
    print(f"  Chunks created:       {metrics.total_chunks:>8,}")
    print(f"  Duration:             {metrics.duration_seconds:>8.2f}s")
    print(f"  Files/sec:            {metrics.files_per_second:>8.1f}")
    print(f"  Chunks/sec:           {metrics.chunks_per_second:>8.1f}")
    print(f"  Avg file parse:       {metrics.avg_file_parse_ms:>8.1f}ms")
    print(f"  Avg chunk embed:      {metrics.avg_chunk_embed_ms:>8.3f}ms")
    print(f"  DB write time:        {metrics.db_write_ms:>8.1f}ms")
    print(f"  Git extraction:       {metrics.git_extraction_ms:>8.1f}ms")
    print(f"  Errors:               {metrics.errors:>8}")
    print(f"  Warnings:             {metrics.warnings:>8}")

    return metrics


def profile_queries(
    db_path: Path, test_queries: list[str], iterations: int = 5
) -> list[QueryMetrics]:
    """Profile query performance with multiple test queries.

    Args:
        db_path: Database path
        test_queries: List of test queries
        iterations: Number of times to run each query

    Returns:
        List of QueryMetrics for each query
    """
    print(f"\n{'='*60}")
    print("QUERY PERFORMANCE PROFILE")
    print(f"{'='*60}")
    print(f"Database: {db_path}")
    print(f"Test queries: {len(test_queries)}")
    print(f"Iterations per query: {iterations}")

    config = load_config()
    config.db_path = str(db_path)
    manager = MemoryManager(config=config)

    all_metrics = []

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        timings = []

        # Warm-up run
        _ = manager.search(query, limit=10)

        # Timed runs
        for i in range(iterations):
            start = time.time()
            results = manager.search(query, limit=10)
            duration = (time.time() - start) * 1000  # ms

            timings.append(duration)

            if i == 0:
                # Collect metrics from first run
                scores = [r.hybrid_score for r in results]
                avg_score = statistics.mean(scores) if scores else 0.0
                min_score = min(scores) if scores else 0.0
                max_score = max(scores) if scores else 0.0

        # Calculate statistics
        avg_ms = statistics.mean(timings)
        median_ms = statistics.median(timings)
        stdev_ms = statistics.stdev(timings) if len(timings) > 1 else 0.0

        metrics = QueryMetrics(
            query=query,
            result_count=len(results),
            total_ms=avg_ms,
            semantic_ms=0.0,  # Not separately tracked yet
            bm25_ms=0.0,
            hybrid_ms=avg_ms,
            activation_ms=0.0,
            avg_score=avg_score,
            min_score=min_score,
            max_score=max_score,
        )

        all_metrics.append(metrics)

        # Display
        print(f"  Results:          {metrics.result_count}")
        print(f"  Avg time:         {avg_ms:>8.2f}ms")
        print(f"  Median:           {median_ms:>8.2f}ms")
        print(f"  Std dev:          {stdev_ms:>8.2f}ms")
        print(f"  Avg score:        {avg_score:>8.3f}")
        print(f"  Score range:      {min_score:.3f} - {max_score:.3f}")

    return all_metrics


def profile_database(db_path: Path) -> DatabaseMetrics:
    """Profile database characteristics and structure.

    Args:
        db_path: Database path

    Returns:
        DatabaseMetrics with database stats
    """
    print(f"\n{'='*60}")
    print("DATABASE PROFILE")
    print(f"{'='*60}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Total chunks
    cursor.execute("SELECT COUNT(*) FROM chunks")
    total_chunks = cursor.fetchone()[0]

    # Total files
    cursor.execute("SELECT COUNT(DISTINCT file_path) FROM chunks")
    total_files = cursor.fetchone()[0]

    # DB size
    db_size_mb = db_path.stat().st_size / (1024 * 1024)

    # Index count
    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    )
    index_count = cursor.fetchone()[0]

    # Table count
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]

    # Average chunk size
    cursor.execute("SELECT AVG(LENGTH(content)) FROM chunks")
    avg_chunk_size = int(cursor.fetchone()[0] or 0)

    # Chunk distribution by type
    cursor.execute("SELECT type, COUNT(*) FROM chunks GROUP BY type")
    chunk_distribution = dict(cursor.fetchall())

    conn.close()

    metrics = DatabaseMetrics(
        total_chunks=total_chunks,
        total_files=total_files,
        db_size_mb=db_size_mb,
        index_count=index_count,
        table_count=table_count,
        avg_chunk_size_bytes=avg_chunk_size,
        chunk_distribution=chunk_distribution,
    )

    print(f"  Total chunks:         {metrics.total_chunks:>8,}")
    print(f"  Total files:          {metrics.total_files:>8,}")
    print(f"  DB size:              {metrics.db_size_mb:>8.2f} MB")
    print(f"  Indexes:              {metrics.index_count:>8}")
    print(f"  Tables:               {metrics.table_count:>8}")
    print(f"  Avg chunk size:       {metrics.avg_chunk_size_bytes:>8,} bytes")
    print(f"\n  Chunk distribution:")
    for chunk_type, count in sorted(
        metrics.chunk_distribution.items(), key=lambda x: x[1], reverse=True
    ):
        pct = count / metrics.total_chunks * 100 if metrics.total_chunks > 0 else 0
        print(f"    {chunk_type:<15} {count:>8,} ({pct:>5.1f}%)")

    return metrics


def generate_report(
    indexing: IndexingMetrics,
    queries: list[QueryMetrics],
    database: DatabaseMetrics,
    output_path: Path,
) -> None:
    """Generate comprehensive performance report.

    Args:
        indexing: Indexing metrics
        queries: Query metrics
        database: Database metrics
        output_path: Output JSON path
    """
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "indexing": asdict(indexing),
        "queries": [asdict(q) for q in queries],
        "database": asdict(database),
        "summary": {
            "indexing_throughput": f"{indexing.files_per_second:.1f} files/sec",
            "chunk_throughput": f"{indexing.chunks_per_second:.1f} chunks/sec",
            "avg_query_latency_ms": statistics.mean([q.total_ms for q in queries]),
            "median_query_latency_ms": statistics.median([q.total_ms for q in queries]),
            "db_efficiency": f"{database.total_chunks / database.db_size_mb:.0f} chunks/MB",
        },
    }

    output_path.write_text(json.dumps(report, indent=2))
    print(f"\n{'='*60}")
    print(f"Report written to: {output_path}")
    print(f"{'='*60}")


def main() -> None:
    """Run complete performance profiling suite."""
    # Configuration
    test_dir = Path("packages")  # Index Aurora packages as test
    test_db = Path(".aurora/test_profile.db")
    report_path = Path("MEMORY_PERFORMANCE_PROFILE.json")

    # Clean up old test DB
    if test_db.exists():
        test_db.unlink()
    test_db.parent.mkdir(parents=True, exist_ok=True)

    # Test queries (representative of actual usage)
    test_queries = [
        "memory search indexing",
        "SOAR orchestrator",
        "chunk embedding generation",
        "git blame extraction",
        "spawn task execution",
        "plan decomposition",
    ]

    try:
        # Profile indexing
        indexing_metrics = profile_indexing(test_dir, test_db)

        # Profile queries
        query_metrics = profile_queries(test_db, test_queries, iterations=5)

        # Profile database
        db_metrics = profile_database(test_db)

        # Generate report
        generate_report(indexing_metrics, query_metrics, db_metrics, report_path)

        print("\n" + "=" * 60)
        print("PERFORMANCE PROFILE SUMMARY")
        print("=" * 60)
        print(f"\nIndexing Performance:")
        print(f"  Throughput:        {indexing_metrics.files_per_second:.1f} files/sec")
        print(f"  Chunk rate:        {indexing_metrics.chunks_per_second:.1f} chunks/sec")
        print(f"\nQuery Performance:")
        avg_query = statistics.mean([q.total_ms for q in query_metrics])
        print(f"  Avg latency:       {avg_query:.2f}ms")
        print(
            f"  P50 latency:       {statistics.median([q.total_ms for q in query_metrics]):.2f}ms"
        )
        print(f"\nDatabase Efficiency:")
        print(f"  Size:              {db_metrics.db_size_mb:.2f} MB")
        print(
            f"  Density:           {db_metrics.total_chunks / db_metrics.db_size_mb:.0f} chunks/MB"
        )

    finally:
        # Cleanup
        if test_db.exists():
            print(f"\nCleaning up test database: {test_db}")
            test_db.unlink()


if __name__ == "__main__":
    main()
