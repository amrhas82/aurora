#!/usr/bin/env python3
"""Example demonstrating optimized embedding loading strategies.

This script showcases different loading strategies and their performance
characteristics. Use this to understand which strategy fits your use case.

Usage:
    python examples/optimized_embedding_loading.py [strategy]

Strategies:
    lazy        - Load on first use (default, minimal startup cost)
    background  - Load in background immediately
    progressive - Load tokenizer first, model in background
    quantized   - Load with INT8 quantization (experimental)
    cached      - Use cached compiled model (future)

Examples:
    # Lazy loading (minimal startup, load on first use)
    python examples/optimized_embedding_loading.py lazy

    # Background loading (best for long-running services)
    python examples/optimized_embedding_loading.py background

    # Progressive loading (best for CLI tools)
    python examples/optimized_embedding_loading.py progressive
"""

import argparse
import sys
import time
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "context-code" / "src"))

from aurora_context_code.semantic import (
    LoadingStrategy,
    OptimizedEmbeddingLoader,
    get_embedding_provider,
    preload_embeddings,
)


def measure_time(func, *args, **kwargs):
    """Measure execution time of a function."""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def demo_lazy_loading():
    """Demonstrate lazy loading strategy."""
    print("\n" + "=" * 80)
    print("LAZY LOADING STRATEGY")
    print("=" * 80)
    print("\nDescription:")
    print("  - Model loads on first use (embed_chunk/embed_query call)")
    print("  - Minimal startup cost (< 10ms)")
    print("  - Best for: Commands that may not need embeddings")
    print("\nMeasuring startup time...")

    # Reset any existing loader
    OptimizedEmbeddingLoader.reset()

    # Measure initialization time
    loader, init_time = measure_time(
        OptimizedEmbeddingLoader,
        strategy=LoadingStrategy.LAZY,
    )
    print(f"  ✓ Initialization: {init_time*1000:.1f}ms")

    # Start "loading" (does nothing for lazy)
    _, start_time = measure_time(loader.start_loading)
    print(f"  ✓ start_loading(): {start_time*1000:.1f}ms")

    print(f"\n  Total startup: {(init_time + start_time)*1000:.1f}ms")
    print("  Model status: Not loaded (will load on first use)")

    # Measure first use (triggers loading)
    print("\nMeasuring first use (triggers model loading)...")
    provider, load_time = measure_time(loader.get_provider, timeout=60.0)
    print(f"  ✓ First get_provider(): {load_time:.2f}s")

    if provider:
        # Measure first embedding
        _, embed_time = measure_time(provider.embed_query, "test query")
        print(f"  ✓ First embedding: {embed_time*1000:.1f}ms")

    return loader


def demo_background_loading():
    """Demonstrate background loading strategy."""
    print("\n" + "=" * 80)
    print("BACKGROUND LOADING STRATEGY")
    print("=" * 80)
    print("\nDescription:")
    print("  - Model starts loading immediately in background")
    print("  - Returns control to caller immediately")
    print("  - Best for: Long-running services, daemons")
    print("\nMeasuring startup time...")

    # Reset any existing loader
    OptimizedEmbeddingLoader.reset()

    # Measure initialization time
    loader, init_time = measure_time(
        OptimizedEmbeddingLoader,
        strategy=LoadingStrategy.BACKGROUND,
    )
    print(f"  ✓ Initialization: {init_time*1000:.1f}ms")

    # Start loading in background
    _, start_time = measure_time(loader.start_loading)
    print(f"  ✓ start_loading(): {start_time*1000:.1f}ms (returned immediately)")

    print(f"\n  Total startup: {(init_time + start_time)*1000:.1f}ms")
    print("  Model status: Loading in background...")

    # Simulate doing other work
    print("\nSimulating other initialization work (2 seconds)...")
    for i in range(4):
        time.sleep(0.5)
        status = "Loading..." if loader.is_loading() else "Ready!" if loader.is_loaded() else "Idle"
        print(f"  [{i+1}/4] Other work... (model status: {status})")

    # Get provider (may be ready, or may need to wait)
    print("\nGetting provider...")
    provider, wait_time = measure_time(loader.get_provider, timeout=60.0)

    if loader.is_loaded():
        print(f"  ✓ Model was already loaded! Wait time: {wait_time*1000:.1f}ms")
    else:
        print(f"  ✓ Waited for loading: {wait_time:.2f}s")

    if provider:
        # Measure first embedding
        _, embed_time = measure_time(provider.embed_query, "test query")
        print(f"  ✓ First embedding: {embed_time*1000:.1f}ms")

    total_time = loader.get_load_time()
    print(f"\n  Total load time (background): {total_time:.2f}s")

    return loader


def demo_progressive_loading():
    """Demonstrate progressive loading strategy."""
    print("\n" + "=" * 80)
    print("PROGRESSIVE LOADING STRATEGY (RECOMMENDED)")
    print("=" * 80)
    print("\nDescription:")
    print("  - Loads metadata and tokenizer first (fast)")
    print("  - Loads model weights in background")
    print("  - Embedding dimension available immediately")
    print("  - Best for: CLI tools with mixed embedding usage")
    print("\nMeasuring startup time...")

    # Reset any existing loader
    OptimizedEmbeddingLoader.reset()

    # Measure initialization time
    loader, init_time = measure_time(
        OptimizedEmbeddingLoader,
        strategy=LoadingStrategy.PROGRESSIVE,
    )
    print(f"  ✓ Initialization: {init_time*1000:.1f}ms")

    # Start progressive loading
    _, start_time = measure_time(loader.start_loading)
    print(f"  ✓ start_loading(): {start_time*1000:.1f}ms (returned immediately)")

    # Check if embedding dimension is available
    embed_dim = loader.get_embedding_dim_fast()
    if embed_dim:
        print(f"  ✓ Embedding dimension available: {embed_dim}")

    print(f"\n  Total startup: {(init_time + start_time)*1000:.1f}ms")
    print("  Model status: Loading progressively...")

    # Simulate other work
    print("\nSimulating other initialization work...")
    for i in range(3):
        time.sleep(0.5)
        status = "Loading..." if loader.is_loading() else "Ready!" if loader.is_loaded() else "Idle"
        print(f"  [{i+1}/3] Other work... (model status: {status})")

    # Get provider
    print("\nGetting provider...")
    provider, wait_time = measure_time(loader.get_provider, timeout=60.0)

    if loader.is_loaded():
        print(f"  ✓ Model ready! Wait time: {wait_time*1000:.1f}ms")
    else:
        print(f"  ✓ Waited for loading: {wait_time:.2f}s")

    if provider:
        _, embed_time = measure_time(provider.embed_query, "test query")
        print(f"  ✓ First embedding: {embed_time*1000:.1f}ms")

    total_time = loader.get_load_time()
    print(f"\n  Total load time (progressive): {total_time:.2f}s")

    return loader


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("\n" + "=" * 80)
    print("CONVENIENCE FUNCTIONS")
    print("=" * 80)
    print("\nThe easiest way to use optimized loading:")
    print("\nExample 1: preload_embeddings() at startup")
    print("-" * 80)

    # Reset
    OptimizedEmbeddingLoader.reset()

    print("\n# At application startup:")
    print("from aurora_context_code.semantic import preload_embeddings")
    print("preload_embeddings()  # Returns immediately")

    preload_embeddings()
    print("\n  ✓ Started background loading")

    print("\n# Later, when needed:")
    print("from aurora_context_code.semantic import get_embedding_provider")
    print("provider = get_embedding_provider()")

    # Simulate work
    print("\nSimulating other work (2 seconds)...")
    time.sleep(2.0)

    # Get provider
    provider, wait_time = measure_time(get_embedding_provider, timeout=60.0)

    if provider:
        print(f"  ✓ Provider ready! Wait time: {wait_time*1000:.1f}ms")
        print("  ✓ Model was pre-loaded in background")
    else:
        print("  ✗ Failed to get provider")

    print("\nExample 2: get_embedding_provider() with strategy")
    print("-" * 80)

    # Reset
    OptimizedEmbeddingLoader.reset()

    print("\nfrom aurora_context_code.semantic import get_embedding_provider, LoadingStrategy")
    print("provider = get_embedding_provider(strategy=LoadingStrategy.PROGRESSIVE)")

    provider, load_time = measure_time(
        get_embedding_provider,
        strategy=LoadingStrategy.PROGRESSIVE,
        timeout=60.0,
    )

    if provider:
        print(f"  ✓ Provider ready! Total time: {load_time:.2f}s")


def demo_resource_detection():
    """Demonstrate resource profile detection."""
    print("\n" + "=" * 80)
    print("RESOURCE PROFILE DETECTION")
    print("=" * 80)
    print("\nAutomatic system resource detection:")

    from aurora_context_code.semantic import ResourceProfile

    profile = ResourceProfile.detect()

    print(f"\n  CPU Cores:        {profile.cpu_count}")
    print(f"  Available Memory: {profile.available_memory_mb:.0f} MB")
    print(f"  CUDA Available:   {profile.has_cuda}")
    print(f"  MPS Available:    {profile.has_mps}")
    print(f"  SSD Detected:     {profile.is_ssd}")
    print(f"\nRecommendations:")
    print(f"  Device:           {profile.recommended_device}")
    print(f"  Batch Size:       {profile.recommended_batch_size}")


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(
        description="Demonstrate optimized embedding loading strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "strategy",
        nargs="?",
        default="all",
        choices=["lazy", "background", "progressive", "convenience", "resources", "all"],
        help="Strategy to demonstrate (default: all)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("OPTIMIZED EMBEDDING LOADING DEMONSTRATIONS")
    print("=" * 80)

    if args.strategy in ["all", "lazy"]:
        demo_lazy_loading()

    if args.strategy in ["all", "background"]:
        demo_background_loading()

    if args.strategy in ["all", "progressive"]:
        demo_progressive_loading()

    if args.strategy in ["all", "convenience"]:
        demo_convenience_functions()

    if args.strategy in ["all", "resources"]:
        demo_resource_detection()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nRecommended strategies by use case:")
    print("  - CLI tools:            PROGRESSIVE (fast startup, ready when needed)")
    print("  - Long-running services: BACKGROUND (load immediately)")
    print("  - Optional embeddings:   LAZY (zero cost if not used)")
    print("  - Memory constrained:    QUANTIZED (experimental, lower memory)")
    print("\nBest practices:")
    print("  1. Use preload_embeddings() early in startup")
    print("  2. Use get_embedding_provider() to get the provider")
    print("  3. Cache the provider instance (don't create multiple)")
    print("  4. Choose strategy based on your use case")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
