#!/usr/bin/env python3
"""Performance profiling script for memory indexing.

Profiles three key bottlenecks:
1. Parsing - tree-sitter syntax tree construction
2. Embedding generation - sentence-transformer model inference
3. Database writes - SQLite INSERT operations

Usage:
    python profile_indexing.py [path_to_index]
"""

import cProfile
import io
import json
import pstats
import sqlite3
import time
from pathlib import Path
from pstats import SortKey
from typing import Any

from aurora_cli.config import load_config
from aurora_cli.memory_manager import MemoryManager


class ProfilingResults:
    """Container for profiling results."""

    def __init__(self):
        self.parsing_time = 0.0
        self.embedding_time = 0.0
        self.db_write_time = 0.0
        self.git_blame_time = 0.0
        self.total_time = 0.0
        self.files_processed = 0
        self.chunks_created = 0
        self.parse_calls = 0
        self.embed_calls = 0
        self.db_write_calls = 0
        self.avg_parse_per_file = 0.0
        self.avg_embed_per_chunk = 0.0
        self.avg_db_per_chunk = 0.0


def profile_indexing(path: Path, batch_size: int = 32) -> ProfilingResults:
    """Profile indexing with granular timing.

    Args:
        path: Path to index
        batch_size: Embedding batch size

    Returns:
        ProfilingResults with timing breakdown
    """
    results = ProfilingResults()

    # Use temp database for profiling
    config = load_config()
    import tempfile

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    config.db_path = str(temp_db)

    try:
        manager = MemoryManager(config=config)

        # Track timing phases
        phase_times: dict[str, list[float]] = {
            "parsing": [],
            "git_blame": [],
            "embedding": [],
            "db_write": [],
        }

        # Monkey-patch to track timing
        original_parse = None
        original_embed_batch = None
        original_save_chunk = None

        # Track parsing time
        if manager.parser_registry:
            # Store original parse methods
            from aurora_context_code.languages.python import PythonParser

            original_python_parse = PythonParser.parse

            def timed_parse(self, file_path):
                start = time.perf_counter()
                result = original_python_parse(self, file_path)
                elapsed = time.perf_counter() - start
                phase_times["parsing"].append(elapsed)
                return result

            PythonParser.parse = timed_parse

        # Track embedding time
        original_embed_batch = manager.embedding_provider.embed_batch

        def timed_embed_batch(texts, batch_size=32):
            start = time.perf_counter()
            result = original_embed_batch(texts, batch_size)
            elapsed = time.perf_counter() - start
            phase_times["embedding"].append(elapsed)
            return result

        manager.embedding_provider.embed_batch = timed_embed_batch

        # Track database write time
        original_save_chunk = manager.memory_store.save_chunk

        def timed_save_chunk(chunk):
            start = time.perf_counter()
            result = original_save_chunk(chunk)
            elapsed = time.perf_counter() - start
            phase_times["db_write"].append(elapsed)
            return result

        manager.memory_store.save_chunk = timed_save_chunk

        # Track git blame time (if extractor available)
        try:
            from aurora_context_code.git import GitSignalExtractor

            git_extractor = GitSignalExtractor()
            original_get_function_commit_times = git_extractor.get_function_commit_times

            def timed_get_function_commit_times(file_path, line_start, line_end):
                start = time.perf_counter()
                result = original_get_function_commit_times(file_path, line_start, line_end)
                elapsed = time.perf_counter() - start
                phase_times["git_blame"].append(elapsed)
                return result

            git_extractor.get_function_commit_times = timed_get_function_commit_times
        except Exception:
            pass

        # Run indexing
        overall_start = time.perf_counter()
        stats = manager.index_path(path, batch_size=batch_size)
        overall_elapsed = time.perf_counter() - overall_start

        # Aggregate results
        results.total_time = overall_elapsed
        results.files_processed = stats.files_indexed
        results.chunks_created = stats.chunks_created

        results.parsing_time = sum(phase_times["parsing"])
        results.parse_calls = len(phase_times["parsing"])

        results.embedding_time = sum(phase_times["embedding"])
        results.embed_calls = len(phase_times["embedding"])

        results.db_write_time = sum(phase_times["db_write"])
        results.db_write_calls = len(phase_times["db_write"])

        results.git_blame_time = sum(phase_times["git_blame"])

        # Calculate averages
        if results.files_processed > 0:
            results.avg_parse_per_file = results.parsing_time / results.files_processed

        if results.chunks_created > 0:
            results.avg_embed_per_chunk = results.embedding_time / results.chunks_created
            results.avg_db_per_chunk = results.db_write_time / results.chunks_created

    finally:
        # Cleanup temp database
        if temp_db.exists():
            temp_db.unlink()

    return results


def profile_with_cprofile(path: Path) -> pstats.Stats:
    """Profile using cProfile for detailed function-level analysis.

    Args:
        path: Path to index

    Returns:
        pstats.Stats object
    """
    config = load_config()
    import tempfile

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    config.db_path = str(temp_db)

    try:
        profiler = cProfile.Profile()
        profiler.enable()

        manager = MemoryManager(config=config)
        manager.index_path(path)

        profiler.disable()

        # Convert to stats
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        return stats

    finally:
        if temp_db.exists():
            temp_db.unlink()


def analyze_database_performance(db_path: Path) -> dict[str, Any]:
    """Analyze SQLite database performance characteristics.

    Args:
        db_path: Path to database

    Returns:
        Dictionary with performance metrics
    """
    metrics = {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for indexes
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
        indexes = cursor.fetchall()
        metrics["index_count"] = len(indexes)
        metrics["indexes"] = [{"name": name, "sql": sql} for name, sql in indexes]

        # Check table sizes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_stats = {}
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table_stats[table_name] = count
        metrics["table_row_counts"] = table_stats

        # Check page size
        cursor.execute("PRAGMA page_size")
        metrics["page_size"] = cursor.fetchone()[0]

        # Check cache size
        cursor.execute("PRAGMA cache_size")
        metrics["cache_size"] = cursor.fetchone()[0]

        # Check journal mode
        cursor.execute("PRAGMA journal_mode")
        metrics["journal_mode"] = cursor.fetchone()[0]

        # Check synchronous mode
        cursor.execute("PRAGMA synchronous")
        metrics["synchronous"] = cursor.fetchone()[0]

        conn.close()

    except Exception as e:
        metrics["error"] = str(e)

    return metrics


def print_results(results: ProfilingResults, db_metrics: dict[str, Any] | None = None):
    """Print profiling results in readable format.

    Args:
        results: ProfilingResults to display
        db_metrics: Optional database performance metrics
    """
    print("\n" + "=" * 80)
    print("MEMORY INDEXING PERFORMANCE PROFILE")
    print("=" * 80)

    print(f"\nTotal Time:        {results.total_time:.2f}s")
    print(f"Files Processed:   {results.files_processed}")
    print(f"Chunks Created:    {results.chunks_created}")
    print(f"Throughput:        {results.files_processed / results.total_time:.1f} files/s")
    print(f"                   {results.chunks_created / results.total_time:.1f} chunks/s")

    print("\n" + "-" * 80)
    print("TIME BREAKDOWN (by phase)")
    print("-" * 80)

    # Calculate percentages
    phases = [
        ("Parsing", results.parsing_time),
        ("Git Blame", results.git_blame_time),
        ("Embedding", results.embedding_time),
        ("DB Writes", results.db_write_time),
    ]

    # Add overhead (untracked time)
    tracked_time = sum(t for _, t in phases)
    overhead = results.total_time - tracked_time
    phases.append(("Overhead", overhead))

    for phase_name, phase_time in phases:
        pct = (phase_time / results.total_time) * 100 if results.total_time > 0 else 0
        bar_width = int(pct / 2)  # 50 chars max
        bar = "█" * bar_width
        print(f"{phase_name:12} {phase_time:7.2f}s  {pct:5.1f}%  {bar}")

    print("\n" + "-" * 80)
    print("DETAILED METRICS")
    print("-" * 80)

    print(f"\nParsing:")
    print(f"  Total calls:       {results.parse_calls}")
    print(f"  Avg per file:      {results.avg_parse_per_file * 1000:.1f}ms")

    print(f"\nEmbedding:")
    print(f"  Total batches:     {results.embed_calls}")
    print(f"  Total chunks:      {results.chunks_created}")
    print(f"  Avg per chunk:     {results.avg_embed_per_chunk * 1000:.1f}ms")
    if results.embed_calls > 0:
        avg_batch = results.chunks_created / results.embed_calls
        print(f"  Avg batch size:    {avg_batch:.1f} chunks")

    print(f"\nDatabase Writes:")
    print(f"  Total writes:      {results.db_write_calls}")
    print(f"  Avg per chunk:     {results.avg_db_per_chunk * 1000:.2f}ms")

    if db_metrics:
        print("\n" + "-" * 80)
        print("DATABASE CONFIGURATION")
        print("-" * 80)
        print(f"  Page size:         {db_metrics.get('page_size', 'N/A')} bytes")
        print(f"  Cache size:        {db_metrics.get('cache_size', 'N/A')} pages")
        print(f"  Journal mode:      {db_metrics.get('journal_mode', 'N/A')}")
        print(f"  Synchronous:       {db_metrics.get('synchronous', 'N/A')}")
        print(f"  Index count:       {db_metrics.get('index_count', 'N/A')}")

    print("\n" + "=" * 80)
    print("BOTTLENECK ANALYSIS")
    print("=" * 80)

    # Identify top bottleneck
    phases_sorted = sorted(phases[:-1], key=lambda x: x[1], reverse=True)
    top_bottleneck = phases_sorted[0]

    print(f"\nTop bottleneck: {top_bottleneck[0]}")
    print(f"  Time: {top_bottleneck[1]:.2f}s ({(top_bottleneck[1] / results.total_time) * 100:.1f}%)")

    # Recommendations
    print("\nOptimization Recommendations:")

    if top_bottleneck[0] == "Parsing":
        print("  • Parsing is the primary bottleneck")
        print("  • Consider parallel parsing with multiprocessing")
        print("  • Cache parsed ASTs for unchanged files")
        print("  • Profile tree-sitter grammar for hotspots")

    elif top_bottleneck[0] == "Embedding":
        print("  • Embedding generation is the primary bottleneck")
        print("  • Increase batch_size (currently processing in batches)")
        print("  • Use GPU acceleration if available")
        print("  • Consider lighter embedding model (e.g., MiniLM)")
        print("  • Cache embeddings for unchanged code")

    elif top_bottleneck[0] == "DB Writes":
        print("  • Database writes are the primary bottleneck")
        print("  • Enable WAL mode: PRAGMA journal_mode=WAL")
        print("  • Increase cache size: PRAGMA cache_size=10000")
        print("  • Use transactions for batch writes")
        print("  • Consider async writes with background thread")

    elif top_bottleneck[0] == "Git Blame":
        print("  • Git history extraction is the primary bottleneck")
        print("  • Already uses file-level caching")
        print("  • Consider skipping git blame with --no-git flag")
        print("  • Use shallow git history (git clone --depth)")

    print("\n" + "=" * 80)


def save_results_json(results: ProfilingResults, output_path: Path):
    """Save profiling results to JSON.

    Args:
        results: ProfilingResults to save
        output_path: Path to output JSON file
    """
    data = {
        "total_time": results.total_time,
        "files_processed": results.files_processed,
        "chunks_created": results.chunks_created,
        "throughput_files_per_sec": results.files_processed / results.total_time
        if results.total_time > 0
        else 0,
        "throughput_chunks_per_sec": results.chunks_created / results.total_time
        if results.total_time > 0
        else 0,
        "phases": {
            "parsing": {
                "total_time": results.parsing_time,
                "calls": results.parse_calls,
                "avg_per_call_ms": results.avg_parse_per_file * 1000,
                "percentage": (results.parsing_time / results.total_time) * 100
                if results.total_time > 0
                else 0,
            },
            "git_blame": {
                "total_time": results.git_blame_time,
                "percentage": (results.git_blame_time / results.total_time) * 100
                if results.total_time > 0
                else 0,
            },
            "embedding": {
                "total_time": results.embedding_time,
                "calls": results.embed_calls,
                "avg_per_chunk_ms": results.avg_embed_per_chunk * 1000,
                "percentage": (results.embedding_time / results.total_time) * 100
                if results.total_time > 0
                else 0,
            },
            "db_write": {
                "total_time": results.db_write_time,
                "calls": results.db_write_calls,
                "avg_per_write_ms": results.avg_db_per_chunk * 1000,
                "percentage": (results.db_write_time / results.total_time) * 100
                if results.total_time > 0
                else 0,
            },
        },
    }

    output_path.write_text(json.dumps(data, indent=2))
    print(f"\nResults saved to: {output_path}")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        # Default to profiling the aurora codebase itself
        path = Path(__file__).parent

    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)

    print(f"Profiling indexing for: {path}")
    print("This may take a few minutes...\n")

    # Run profiling
    results = profile_indexing(path)

    # Get database metrics (if available)
    config = load_config()
    db_path = Path(config.get_db_path())
    db_metrics = None
    if db_path.exists():
        db_metrics = analyze_database_performance(db_path)

    # Print results
    print_results(results, db_metrics)

    # Save to JSON
    output_path = Path("profiling_results.json")
    save_results_json(results, output_path)

    print("\nFor detailed function-level profiling, run:")
    print("  python -m cProfile -o profile.stats profile_indexing.py")
    print("  python -m pstats profile.stats")


if __name__ == "__main__":
    main()
