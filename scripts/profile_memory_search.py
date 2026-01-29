"""Performance profiling script for aur mem search.

This script profiles the memory search implementation to identify bottlenecks.
It uses cProfile and outputs detailed timing information for each component.

Usage:
    python profile_memory_search.py [query] [--db-path PATH]
"""

import cProfile
import pstats
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any

# Add packages to path for local development
sys.path.insert(0, str(Path(__file__).parent / "packages" / "cli" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "core" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "context-code" / "src"))


def profile_search(query: str, db_path: str | None = None) -> dict[str, Any]:
    """Profile a memory search operation.

    Args:
        query: Search query text
        db_path: Optional database path (uses default if None)

    Returns:
        Dictionary with profiling results and timings
    """
    from aurora_cli.config import Config
    from aurora_cli.memory.retrieval import MemoryRetriever
    from aurora_core.store.sqlite import SQLiteStore

    # Load configuration
    config = Config()
    if db_path:
        config.db_path = db_path

    db_path_resolved = Path(config.get_db_path())

    if not db_path_resolved.exists():
        print(f"Error: Database not found at {db_path_resolved}", file=sys.stderr)
        print("Run 'aur mem index .' first to create the database", file=sys.stderr)
        sys.exit(1)

    print(f"Profiling search for: '{query}'")
    print(f"Database: {db_path_resolved}")
    print("-" * 80)

    # Phase 1: Initialization timing
    print("\n[Phase 1] Initialization")
    init_start = time.time()

    store = SQLiteStore(str(db_path_resolved))
    retriever = MemoryRetriever(store=store, config=config)

    init_elapsed = time.time() - init_start
    print(f"  Store + Retriever init: {init_elapsed:.3f}s")

    # Phase 2: Check if model is cached (non-blocking)
    print("\n[Phase 2] Model Status Check")
    model_check_start = time.time()

    model_ready = retriever.is_embedding_model_ready()
    model_loading = retriever.is_embedding_model_loading()

    model_check_elapsed = time.time() - model_check_start
    print(f"  Model ready: {model_ready}")
    print(f"  Model loading: {model_loading}")
    print(f"  Check time: {model_check_elapsed:.3f}s")

    # Phase 3: First retrieval (cold cache) - PROFILED
    print("\n[Phase 3] First Retrieval (Cold Cache) - PROFILED")

    profiler = cProfile.Profile()
    profiler.enable()

    first_start = time.time()
    results_first, is_hybrid_first = retriever.retrieve_fast(query, limit=10)
    first_elapsed = time.time() - first_start

    profiler.disable()

    print(f"  Results: {len(results_first)} chunks")
    print(f"  Hybrid mode: {is_hybrid_first}")
    print(f"  Total time: {first_elapsed:.3f}s")

    # Save profile stats
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)

    # Print top 30 slowest functions
    print("\n  Top 30 slowest functions:")
    stats.sort_stats("cumulative")
    stats.print_stats(30)
    profile_output = stream.getvalue()
    print(profile_output)

    # Phase 4: Second retrieval (warm cache)
    print("\n[Phase 4] Second Retrieval (Warm Cache)")
    second_start = time.time()
    results_second, is_hybrid_second = retriever.retrieve_fast(query, limit=10)
    second_elapsed = time.time() - second_start

    print(f"  Results: {len(results_second)} chunks")
    print(f"  Hybrid mode: {is_hybrid_second}")
    print(f"  Total time: {second_elapsed:.3f}s")
    print(f"  Speedup: {first_elapsed / second_elapsed:.2f}x")

    # Phase 5: Component breakdown (manual timing)
    print("\n[Phase 5] Component Breakdown")

    # BM25 scoring
    try:
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer

        bm25_start = time.time()
        bm25_scorer = BM25Scorer()

        # Get all chunks for BM25 scoring
        all_chunks = store.list_chunks(limit=10000)
        corpus = [chunk.content or "" for chunk in all_chunks]
        bm25_scorer.fit(corpus)
        _ = bm25_scorer.score(query, corpus)

        bm25_elapsed = time.time() - bm25_start
        print(f"  BM25 scoring ({len(all_chunks)} chunks): {bm25_elapsed:.3f}s")
    except Exception as e:
        print(f"  BM25 scoring: Failed ({e})")

    # Embedding generation (if available)
    if is_hybrid_first:
        try:
            from aurora_context_code.semantic import EmbeddingProvider

            embed_start = time.time()
            provider = EmbeddingProvider()
            _ = provider.embed_query(query)
            embed_elapsed = time.time() - embed_start

            print(f"  Query embedding generation: {embed_elapsed:.3f}s")

            # Batch embedding for chunks
            if len(results_first) > 0:
                batch_start = time.time()
                texts = [r.content for r in results_first[:10]]
                _ = provider.embed_batch(texts)
                batch_elapsed = time.time() - batch_start
                print(f"  Batch embedding (10 chunks): {batch_elapsed:.3f}s")
        except Exception as e:
            print(f"  Embedding generation: Failed ({e})")

    # Activation scoring
    try:
        from aurora_core.activation.engine import ActivationEngine

        activation_start = time.time()
        engine = ActivationEngine()

        # Score top 10 chunks
        for chunk in all_chunks[:10]:
            engine.calculate_total(
                access_history=chunk.access_history or [],
                last_access=chunk.last_access,
                spreading_activation=0.0,
                query_keywords=set(query.lower().split()),
                chunk_keywords=set((chunk.content or "").lower().split()[:100]),
            )

        activation_elapsed = time.time() - activation_start
        print(f"  Activation scoring (10 chunks): {activation_elapsed:.3f}s")
    except Exception as e:
        print(f"  Activation scoring: Failed ({e})")

    # Database query timing
    try:
        db_start = time.time()
        _ = store.list_chunks(limit=100)
        db_elapsed = time.time() - db_start
        print(f"  Database query (100 chunks): {db_elapsed:.3f}s")
    except Exception as e:
        print(f"  Database query: Failed ({e})")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Initialization:        {init_elapsed:.3f}s")
    print(f"First search (cold):   {first_elapsed:.3f}s")
    print(f"Second search (warm):  {second_elapsed:.3f}s")
    print(f"Cache speedup:         {first_elapsed / second_elapsed:.2f}x")
    print()

    return {
        "query": query,
        "db_path": str(db_path_resolved),
        "init_time": init_elapsed,
        "first_search_time": first_elapsed,
        "second_search_time": second_elapsed,
        "speedup": first_elapsed / second_elapsed,
        "model_ready": model_ready,
        "hybrid_mode": is_hybrid_first,
        "results_count": len(results_first),
        "profile_output": profile_output,
    }


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Profile aur mem search performance")
    parser.add_argument("query", nargs="?", default="search query", help="Search query")
    parser.add_argument("--db-path", help="Database path (optional)")
    parser.add_argument("--output", help="Save profile results to file")

    args = parser.parse_args()

    # Run profiling
    results = profile_search(args.query, args.db_path)

    # Save results if requested
    if args.output:
        import json

        output_path = Path(args.output)
        with open(output_path, "w") as f:
            # Remove profile_output for JSON serialization
            json_results = {k: v for k, v in results.items() if k != "profile_output"}
            json.dump(json_results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

        # Save profile output separately
        profile_output_path = output_path.with_suffix(".txt")
        with open(profile_output_path, "w") as f:
            f.write(results["profile_output"])
        print(f"Profile output saved to: {profile_output_path}")


if __name__ == "__main__":
    main()
