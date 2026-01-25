#!/usr/bin/env python3
"""Performance benchmarking script for Epic 2.

This script measures:
1. HybridRetriever creation time (<50ms target)
2. Fallback search speed (<1s target)

Usage:
    python benchmark_epic2_performance.py
"""

import os
import sys
import time

# Add packages to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages/core/src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages/context-code/src"))

from aurora_context_code.semantic.embedding_provider import EmbeddingProvider
from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
from aurora_core.activation import ActivationEngine
from aurora_core.store.sqlite import SQLiteStore


def benchmark_creation_time():
    """Benchmark HybridRetriever creation time."""
    print("=" * 80)
    print("Benchmark 1: HybridRetriever Creation Time")
    print("=" * 80)
    print()

    db_path = ".aurora/memory.db"
    if not os.path.exists(db_path):
        print("ERROR: Database not found at .aurora/memory.db")
        sys.exit(1)

    store = SQLiteStore(db_path)
    activation_engine = ActivationEngine()
    embedding_provider = EmbeddingProvider()

    # Measure creation time (10 iterations for accuracy)
    times = []
    for i in range(10):
        start = time.perf_counter()
        retriever = HybridRetriever(store, activation_engine, embedding_provider)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed*1000:.1f}ms")

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print()
    print(f"Average creation time: {avg_time*1000:.1f}ms")
    print(f"Min: {min_time*1000:.1f}ms, Max: {max_time*1000:.1f}ms")
    print(f"Target: <50ms")
    print(f"Result: {'PASS ✓' if avg_time < 0.050 else 'FAIL ✗'}")
    print()

    return avg_time < 0.050


def benchmark_fallback_search_speed():
    """Benchmark fallback search speed (BM25+Activation without embeddings)."""
    print("=" * 80)
    print("Benchmark 2: Fallback Search Speed (BM25+Activation)")
    print("=" * 80)
    print()

    db_path = ".aurora/memory.db"
    store = SQLiteStore(db_path)
    activation_engine = ActivationEngine()

    # Disable embeddings to trigger fallback
    os.environ["AURORA_EMBEDDING_PROVIDER"] = "none"
    embedding_provider = None

    retriever = HybridRetriever(store, activation_engine, embedding_provider)

    # Warm up (load BM25 index)
    print("Warming up (loading BM25 index)...")
    start_warmup = time.perf_counter()
    retriever.retrieve("warmup", top_k=10)
    warmup_time = time.perf_counter() - start_warmup
    print(f"  Warmup complete: {warmup_time:.2f}s")
    print()

    # Measure search time (5 iterations)
    query = "SoarOrchestrator"
    print(f"Measuring fallback search for query: '{query}'")
    times = []
    for i in range(5):
        start = time.perf_counter()
        results = retriever.retrieve(query, top_k=10)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.2f}s ({len(results)} results)")

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print()
    print(f"Average fallback search time: {avg_time:.2f}s")
    print(f"Min: {min_time:.2f}s, Max: {max_time:.2f}s")
    print(f"Target: <1s")
    print(f"Result: {'PASS ✓' if avg_time < 1.0 else 'FAIL ✗'}")
    print()

    # Clean up env var
    os.environ.pop("AURORA_EMBEDDING_PROVIDER", None)

    return avg_time < 1.0


def main():
    """Run all performance benchmarks."""
    print()
    print("=" * 80)
    print("Epic 2 Performance Benchmarks")
    print("=" * 80)
    print()

    # Run benchmarks
    creation_pass = benchmark_creation_time()
    fallback_pass = benchmark_fallback_search_speed()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"1. HybridRetriever Creation (<50ms):     {'PASS ✓' if creation_pass else 'FAIL ✗'}")
    print(f"2. Fallback Search Speed (<1s):          {'PASS ✓' if fallback_pass else 'FAIL ✗'}")
    print()

    if creation_pass and fallback_pass:
        print("All performance targets met! ✓")
        return 0
    else:
        print("Some performance targets not met. ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
