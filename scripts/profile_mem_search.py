#!/usr/bin/env python3
"""Profile the `aur mem search` command to identify performance bottlenecks.

This script profiles the complete search path:
1. CLI startup / import time
2. Config loading
3. Database connection and store initialization
4. Embedding model loading (background vs synchronous)
5. BM25 index loading
6. Query embedding generation
7. Database queries (retrieve_by_activation)
8. BM25 scoring
9. Semantic similarity calculation
10. Result formatting and display

Usage:
    python scripts/profile_mem_search.py "search query" [--detailed]

Example:
    python scripts/profile_mem_search.py "authentication" --detailed
"""

from __future__ import annotations

import argparse
import cProfile
import io
import os
import pstats
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# Ensure we're using the local packages
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "cli" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "context-code" / "src"))


@dataclass
class TimingResult:
    """Results from a timing measurement."""
    name: str
    duration_ms: float
    details: str = ""
    children: list["TimingResult"] = field(default_factory=list)


class Profiler:
    """Profile the search command with detailed timing breakdowns."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: list[TimingResult] = []
        self._start_time: float = 0

    @contextmanager
    def time_section(self, name: str, details: str = ""):
        """Context manager to time a section of code."""
        start = time.perf_counter()
        result = TimingResult(name=name, duration_ms=0, details=details)
        try:
            yield result
        finally:
            result.duration_ms = (time.perf_counter() - start) * 1000
            self.results.append(result)
            if self.verbose:
                print(f"  [{result.duration_ms:7.2f}ms] {name}")

    def time_function(self, name: str) -> Callable:
        """Decorator to time a function."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.time_section(name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def print_summary(self) -> None:
        """Print a formatted summary of all timing results."""
        print("\n" + "=" * 70)
        print("PERFORMANCE PROFILE SUMMARY")
        print("=" * 70)

        total_ms = sum(r.duration_ms for r in self.results)

        # Sort by duration (slowest first)
        sorted_results = sorted(self.results, key=lambda r: r.duration_ms, reverse=True)

        print(f"\n{'Component':<40} {'Time (ms)':>12} {'% Total':>10}")
        print("-" * 70)

        for result in sorted_results:
            pct = (result.duration_ms / total_ms * 100) if total_ms > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"{result.name:<40} {result.duration_ms:>10.2f}ms {pct:>8.1f}% {bar}")
            if result.details:
                print(f"  └─ {result.details}")

        print("-" * 70)
        print(f"{'TOTAL':<40} {total_ms:>10.2f}ms")
        print("=" * 70)

        # Identify bottlenecks
        print("\n🔍 BOTTLENECK ANALYSIS:")
        bottlenecks = [r for r in sorted_results if r.duration_ms > total_ms * 0.1]
        if bottlenecks:
            for i, result in enumerate(bottlenecks, 1):
                pct = (result.duration_ms / total_ms * 100) if total_ms > 0 else 0
                print(f"  {i}. {result.name}: {result.duration_ms:.1f}ms ({pct:.1f}%)")
        else:
            print("  No single component takes >10% of total time (well balanced)")


def profile_imports(profiler: Profiler) -> dict[str, Any]:
    """Profile import times for key modules."""
    modules = {}

    with profiler.time_section("Import: aurora_cli.config"):
        from aurora_cli.config import Config
        modules["Config"] = Config

    with profiler.time_section("Import: aurora_core.store.sqlite"):
        from aurora_core.store.sqlite import SQLiteStore
        modules["SQLiteStore"] = SQLiteStore

    with profiler.time_section("Import: aurora_cli.memory.retrieval"):
        from aurora_cli.memory.retrieval import MemoryRetriever
        modules["MemoryRetriever"] = MemoryRetriever

    with profiler.time_section("Import: aurora_context_code.model_cache"):
        from aurora_context_code.model_cache import is_model_cached_fast
        modules["is_model_cached_fast"] = is_model_cached_fast

    return modules


def profile_config_loading(profiler: Profiler, Config: type) -> Any:
    """Profile configuration loading."""
    with profiler.time_section("Config loading"):
        config = Config()
        db_path = config.get_db_path()
    return config, db_path


def profile_store_init(profiler: Profiler, SQLiteStore: type, db_path: str) -> Any:
    """Profile SQLite store initialization."""
    with profiler.time_section("SQLiteStore initialization"):
        store = SQLiteStore(db_path)

    with profiler.time_section("Schema initialization (first query)"):
        # This triggers lazy schema init
        try:
            count = store.get_chunk_count()
        except Exception:
            count = 0

    return store, count


def profile_model_cache_check(profiler: Profiler, is_model_cached_fast: Callable) -> bool:
    """Profile embedding model cache checking."""
    with profiler.time_section("Model cache check (filesystem)"):
        cached = is_model_cached_fast()
    return cached


def profile_bm25_index_load(profiler: Profiler, db_path: str) -> Any:
    """Profile BM25 index loading."""
    bm25_index_path = Path(db_path).parent / "indexes" / "bm25_index.pkl"

    if not bm25_index_path.exists():
        return None

    with profiler.time_section("BM25 index load", f"from {bm25_index_path}"):
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer
        scorer = BM25Scorer()
        scorer.load_index(bm25_index_path)

    return scorer


def profile_retriever_init(profiler: Profiler, MemoryRetriever: type, store: Any, config: Any) -> Any:
    """Profile retriever initialization (no model loading)."""
    with profiler.time_section("MemoryRetriever initialization"):
        retriever = MemoryRetriever(store=store, config=config)
    return retriever


def profile_embedding_model_load(profiler: Profiler, model_cached: bool) -> Any:
    """Profile embedding model loading (synchronous)."""
    if not model_cached:
        print("⚠️  Embedding model not cached - skipping load test")
        return None

    with profiler.time_section("Embedding model load (synchronous)"):
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            from aurora_context_code.semantic.embedding_provider import EmbeddingProvider
            provider = EmbeddingProvider()
            provider.preload_model()
        except Exception as e:
            print(f"⚠️  Model load failed: {e}")
            return None

    return provider


def profile_query_embedding(profiler: Profiler, provider: Any, query: str) -> Any:
    """Profile query embedding generation."""
    if provider is None:
        return None

    with profiler.time_section("Query embedding generation"):
        embedding = provider.embed_query(query)

    return embedding


def profile_database_retrieval(profiler: Profiler, store: Any, limit: int = 500) -> list:
    """Profile database retrieval by activation."""
    with profiler.time_section("DB: retrieve_by_activation (with embeddings)", f"limit={limit}"):
        chunks_with_emb = store.retrieve_by_activation(
            min_activation=0.0,
            limit=limit,
            include_embeddings=True
        )

    with profiler.time_section("DB: retrieve_by_activation (no embeddings)", f"limit={limit}"):
        chunks_no_emb = store.retrieve_by_activation(
            min_activation=0.0,
            limit=limit,
            include_embeddings=False
        )

    return chunks_with_emb


def profile_bm25_scoring(profiler: Profiler, query: str, chunks: list) -> list:
    """Profile BM25 scoring of chunks."""
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer, tokenize

    with profiler.time_section("BM25: tokenize query"):
        query_tokens = tokenize(query)

    scorer = BM25Scorer()

    # Build mini-index from chunks
    with profiler.time_section("BM25: build index from chunks", f"{len(chunks)} chunks"):
        documents = []
        for chunk in chunks[:100]:  # Sample first 100
            content = ""
            if hasattr(chunk, "name"):
                content += f" {chunk.name}"
            if hasattr(chunk, "signature"):
                content += f" {chunk.signature}"
            if hasattr(chunk, "docstring"):
                content += f" {chunk.docstring}"
            documents.append((chunk.id, content))
        scorer.build_index(documents)

    with profiler.time_section("BM25: score all chunks", f"{len(documents)} chunks"):
        scores = []
        for doc_id, content in documents:
            score = scorer.score(query, content)
            scores.append((doc_id, score))

    return scores


def profile_semantic_scoring(profiler: Profiler, provider: Any, query_embedding: Any, chunks: list) -> list:
    """Profile semantic similarity scoring."""
    if provider is None or query_embedding is None:
        return []

    import numpy as np
    from aurora_context_code.semantic.embedding_provider import cosine_similarity

    with profiler.time_section("Semantic: score all chunks", f"{min(100, len(chunks))} chunks"):
        scores = []
        for chunk in chunks[:100]:
            if hasattr(chunk, "embeddings") and chunk.embeddings is not None:
                chunk_emb = np.frombuffer(chunk.embeddings, dtype=np.float32)
                score = cosine_similarity(query_embedding, chunk_emb)
                scores.append((chunk.id, score))

    return scores


def profile_full_search(profiler: Profiler, retriever: Any, query: str, limit: int = 10) -> list:
    """Profile the complete search path."""
    with profiler.time_section("Full search (retrieve_fast)", f"query='{query[:30]}...', limit={limit}"):
        results, is_hybrid = retriever.retrieve_fast(query, limit=limit)

    return results, is_hybrid


def run_cprofile(query: str, db_path: str) -> None:
    """Run cProfile on the full search for detailed analysis."""
    print("\n" + "=" * 70)
    print("cProfile ANALYSIS (top 30 functions by cumulative time)")
    print("=" * 70 + "\n")

    profiler = cProfile.Profile()
    profiler.enable()

    try:
        from aurora_cli.config import Config
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        config = Config()
        store = SQLiteStore(db_path)
        retriever = MemoryRetriever(store=store, config=config)
        results, _ = retriever.retrieve_fast(query, limit=10)
    finally:
        profiler.disable()

    # Print stats
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(30)
    print(stream.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile the `aur mem search` command for performance bottlenecks."
    )
    parser.add_argument("query", help="Search query to test")
    parser.add_argument(
        "--detailed", "-d", action="store_true",
        help="Show detailed timing for each step"
    )
    parser.add_argument(
        "--cprofile", "-c", action="store_true",
        help="Run cProfile for detailed function-level analysis"
    )
    parser.add_argument(
        "--db-path", type=str, default=None,
        help="Database path (default: .aurora/memory.db)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("AURORA `aur mem search` Performance Profiler")
    print("=" * 70)
    print(f"Query: {args.query}")
    print()

    profiler = Profiler(verbose=args.detailed)

    # Phase 1: Import timing
    print("📦 Phase 1: Import timing...")
    modules = profile_imports(profiler)

    # Phase 2: Config loading
    print("⚙️  Phase 2: Config loading...")
    config, db_path = profile_config_loading(profiler, modules["Config"])
    if args.db_path:
        db_path = args.db_path
    print(f"   Database: {db_path}")

    if not Path(db_path).exists():
        print(f"\n❌ Database not found: {db_path}")
        print("   Run `aur mem index .` first to create the database.")
        sys.exit(1)

    # Phase 3: Store initialization
    print("🗄️  Phase 3: Store initialization...")
    store, chunk_count = profile_store_init(profiler, modules["SQLiteStore"], db_path)
    print(f"   Chunks indexed: {chunk_count}")

    # Phase 4: Model cache check
    print("🔍 Phase 4: Model cache check...")
    model_cached = profile_model_cache_check(profiler, modules["is_model_cached_fast"])
    print(f"   Model cached: {model_cached}")

    # Phase 5: BM25 index loading
    print("📑 Phase 5: BM25 index loading...")
    bm25_scorer = profile_bm25_index_load(profiler, db_path)
    if bm25_scorer:
        print(f"   BM25 corpus size: {bm25_scorer.corpus_size}")
    else:
        print("   BM25 index not found (will be built on-demand)")

    # Phase 6: Retriever initialization
    print("🔧 Phase 6: Retriever initialization...")
    retriever = profile_retriever_init(profiler, modules["MemoryRetriever"], store, config)

    # Phase 7: Embedding model loading
    print("🧠 Phase 7: Embedding model loading...")
    provider = profile_embedding_model_load(profiler, model_cached)

    # Phase 8: Query embedding generation
    print("🔢 Phase 8: Query embedding generation...")
    query_embedding = profile_query_embedding(profiler, provider, args.query)

    # Phase 9: Database retrieval
    print("💾 Phase 9: Database retrieval...")
    chunks = profile_database_retrieval(profiler, store)
    print(f"   Retrieved {len(chunks)} chunks")

    # Phase 10: BM25 scoring
    print("📊 Phase 10: BM25 scoring...")
    bm25_scores = profile_bm25_scoring(profiler, args.query, chunks)

    # Phase 11: Semantic scoring
    print("🎯 Phase 11: Semantic scoring...")
    semantic_scores = profile_semantic_scoring(profiler, provider, query_embedding, chunks)

    # Phase 12: Full search (end-to-end)
    print("🔎 Phase 12: Full search (end-to-end)...")
    retriever2 = modules["MemoryRetriever"](store=store, config=config)
    results, is_hybrid = profile_full_search(profiler, retriever2, args.query)
    print(f"   Results: {len(results)}, Hybrid: {is_hybrid}")

    # Print summary
    profiler.print_summary()

    # Run cProfile if requested
    if args.cprofile:
        run_cprofile(args.query, db_path)

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")

    total_ms = sum(r.duration_ms for r in profiler.results)
    slowest = max(profiler.results, key=lambda r: r.duration_ms)

    if "Embedding model load" in slowest.name and slowest.duration_ms > 5000:
        print("  1. Embedding model loading is slow (~{:.1f}s)".format(slowest.duration_ms / 1000))
        print("     → Use background model loading (already implemented)")
        print("     → Consider model quantization or distillation")

    if any("BM25 index load" in r.name and r.duration_ms > 500 for r in profiler.results):
        print("  2. BM25 index loading is slow")
        print("     → Ensure BM25 index is persisted (already implemented)")
        print("     → Consider index compression")

    db_results = [r for r in profiler.results if "retrieve_by_activation" in r.name]
    if any(r.duration_ms > 200 for r in db_results):
        print("  3. Database queries are slow")
        print("     → Check SQLite indexes on activations and chunks tables")
        print("     → Consider using include_embeddings=False for BM25 pre-filtering")

    if any("Query embedding" in r.name and r.duration_ms > 50 for r in profiler.results):
        print("  4. Query embedding generation is slow")
        print("     → Query cache is enabled (check hit rate)")
        print("     → Consider batching for multiple queries")


if __name__ == "__main__":
    main()
