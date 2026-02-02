# AURORA Performance Tuning Guide

**Version**: 1.0
**Date**: December 23, 2025
**Status**: Production Ready

---

## Executive Summary

This guide provides comprehensive strategies for optimizing AURORA's performance in large codebases (1K-100K+ chunks). Through proper configuration of caching, thresholds, batching, and parallel execution, you can achieve sub-500ms retrieval times even with 10K+ code chunks.

**Performance Targets**:
- 100 chunks: <100ms retrieval
- 1K chunks: <200ms retrieval
- 10K chunks: <500ms retrieval (p95)
- Cache hit rate: ≥30% after 1000 queries
- Memory footprint: ≤100MB for 10K chunks

**Key Optimization Strategies**:
1. **Multi-Tier Caching**: Hot cache (LRU) + persistent cache + activation scores cache
2. **Threshold Filtering**: Skip low-activation chunks early
3. **Type Pre-filtering**: Query only relevant chunk types
4. **Batch Processing**: Calculate activations in batches
5. **Graph Caching**: Rebuild relationship graphs infrequently
6. **Parallel Execution**: Run multiple agents concurrently

---

## Table of Contents

1. [Performance Baseline](#performance-baseline)
2. [Caching Strategies](#caching-strategies)
3. [Threshold Optimization](#threshold-optimization)
4. [Query Optimization](#query-optimization)
5. [Batch Processing](#batch-processing)
6. [Parallel Execution](#parallel-execution)
7. [Memory Management](#memory-management)
8. [Profiling and Monitoring](#profiling-and-monitoring)
9. [Configuration Reference](#configuration-reference)
10. [Troubleshooting](#troubleshooting)

---

## Performance Baseline

### Understanding Performance Bottlenecks

AURORA's retrieval pipeline has several stages, each with performance characteristics:

```
┌────────────────────────────────────────────────────────────────┐
│ 1. Query Parsing & Keyword Extraction           (~5ms)         │
│    - Extract keywords from query                               │
│    - Remove stop words, normalize                              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 2. Candidate Selection                          (~10-50ms)     │
│    - Type pre-filtering (if enabled)                          │
│    - Load chunks from database                                │
│    - Apply quick filters                                      │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 3. Activation Calculation                       (~100-400ms)   │
│    - Base-level activation (BLA)                              │
│    - Spreading activation (if graph available)                │
│    - Context boost                                            │
│    - Decay penalty                                            │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 4. Semantic Similarity (if enabled)             (~50-100ms)    │
│    - Embed query                                              │
│    - Calculate cosine similarity                              │
│    - Hybrid scoring (60% activation + 40% semantic)           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 5. Sorting & Threshold Filtering                (~5ms)         │
│    - Sort by total activation/score                           │
│    - Filter below threshold                                   │
│    - Return top-k results                                     │
└────────────────────────────────────────────────────────────────┘
```

**Bottleneck**: Stage 3 (Activation Calculation) dominates for large codebases.

### Benchmarking Your System

Before optimizing, establish a baseline:

```python
from aurora_core.optimization import QueryOptimizer, OptimizationConfig
from aurora_core.activation import ActivationEngine, ActivationRetriever
import time

# Setup
engine = ActivationEngine()
retriever = ActivationRetriever(engine)

# Benchmark: 1000 chunks
start = time.time()
results = retriever.retrieve(
    chunks=chunks_1k,
    query_keywords={'database', 'query'},
    active_chunk_ids=set(),
    graph=relationship_graph
)
elapsed_ms = (time.time() - start) * 1000

print(f"1K chunks: {elapsed_ms:.1f}ms")
print(f"Results: {len(results)}")
```

**Interpreting Results**:
- <200ms: ✅ Excellent, no optimization needed
- 200-500ms: ⚠️ Acceptable, but room for improvement
- 500-1000ms: ❌ Needs optimization
- >1000ms: ❌ Critical, apply all optimizations

---

## Caching Strategies

### Multi-Tier Cache Architecture

AURORA uses a three-tier caching system:

```
┌─────────────────────────────────────────────────┐
│ Tier 1: Hot Cache (In-Memory LRU)              │
│ - Size: 1000 chunks                            │
│ - Lookup: <1ms                                 │
│ - Eviction: LRU (Least Recently Used)          │
│ - Use: Frequently accessed chunks              │
└─────────────────────────────────────────────────┘
           Cache Miss ↓        Cache Hit ↑
┌─────────────────────────────────────────────────┐
│ Tier 2: Persistent Cache (SQLite)              │
│ - Size: All chunks                             │
│ - Lookup: <5ms                                 │
│ - Use: Avoid redundant parsing/analysis        │
└─────────────────────────────────────────────────┘
           Cache Miss ↓        Cache Hit ↑
┌─────────────────────────────────────────────────┐
│ Tier 3: Activation Scores Cache (TTL)          │
│ - Size: Recent calculations                    │
│ - Lookup: <1ms                                 │
│ - TTL: 10 minutes                              │
│ - Use: Avoid redundant activation calculations │
└─────────────────────────────────────────────────┘
```

### Tier 1: Hot Cache Configuration

```python
from aurora_core.optimization import CacheManager, CacheConfig

# Configure hot cache
config = CacheConfig(
    hot_cache_size=1000,      # Number of chunks in LRU cache
    hot_cache_enabled=True,   # Enable hot cache
    hot_cache_ttl=None        # No TTL, relies on LRU eviction
)

cache_manager = CacheManager(config)
```

**Tuning hot_cache_size**:
- Small codebase (<1K chunks): 500
- Medium codebase (1K-10K): 1000 (default)
- Large codebase (>10K): 2000-5000

**Memory Impact**:
```
Memory = hot_cache_size × avg_chunk_size
        ≈ 1000 × 5KB = 5MB
```

**Trade-offs**:
- Larger cache: Higher hit rate, more memory
- Smaller cache: Lower hit rate, less memory

### Tier 2: Persistent Cache

```python
config = CacheConfig(
    persistent_cache_enabled=True,
    persistent_cache_path="~/.aurora/cache.db",
    persistent_cache_sync_interval=100  # Write to disk every 100 ops
)
```

**When to Use**:
- ✅ Repeatedly analyzing same codebase
- ✅ Multiple AURORA instances on same machine
- ❌ Continuously changing codebase (cache thrashing)
- ❌ Distributed systems (cache invalidation hard)

### Tier 3: Activation Scores Cache

```python
config = CacheConfig(
    activation_cache_enabled=True,
    activation_cache_ttl=600,    # 10 minutes in seconds
    activation_cache_size=5000   # Max entries
)
```

**Purpose**: Cache expensive activation calculations.

**TTL Tuning**:
- Active development: 300s (5 min) - code changes frequently
- Code review: 600s (10 min, default) - slower pace
- Documentation search: 1800s (30 min) - static content

**Invalidation**: Automatically invalidates on code changes.

### Cache Promotion Strategy

Chunks are promoted from persistent to hot cache based on access frequency:

```python
# Automatic promotion when access_count crosses threshold
promotion_threshold = 3  # Promote after 3 accesses
```

**Manual Promotion**:
```python
# Pre-warm cache with critical chunks
critical_chunks = ["main.py", "auth.py", "database.py"]
for chunk_id in critical_chunks:
    cache_manager.promote_to_hot(chunk_id)
```

### Monitoring Cache Performance

```python
# Get cache statistics
stats = cache_manager.get_stats()

print(f"Hot cache hit rate: {stats.hot_hit_rate:.1%}")
print(f"Persistent cache hit rate: {stats.persistent_hit_rate:.1%}")
print(f"Overall hit rate: {stats.overall_hit_rate:.1%}")
print(f"Evictions: {stats.evictions}")
print(f"Promotions: {stats.promotions}")
```

**Target Metrics**:
- Hot cache hit rate: ≥20%
- Overall hit rate: ≥30%
- Evictions: Should stabilize after warm-up period

**Tuning Based on Metrics**:
```python
if stats.hot_hit_rate < 0.15:
    # Hit rate too low, increase hot cache size
    config.hot_cache_size = 2000

if stats.evictions > 10000:
    # Too many evictions, cache thrashing
    config.hot_cache_size = 3000
```

---

## Threshold Optimization

### Activation Threshold Filtering

Skip chunks with activation below threshold to save computation:

```python
from aurora_core.activation import RetrievalConfig

config = RetrievalConfig(
    threshold=-2.0,    # Only chunks with activation > -2.0
    max_results=20     # Return top 20
)
```

### Choosing the Right Threshold

| Threshold | Effect | Use Case |
|-----------|--------|----------|
| -5.0 | Permissive, many results | Discovery, exploration |
| -2.0 | Balanced (default) | General-purpose coding |
| -1.0 | Strict, few results | Highly specific queries |
| 0.0 | Very strict | Production debugging |

**Empirical Tuning**:

```python
# Measure precision at different thresholds
thresholds = [-5.0, -3.0, -2.0, -1.0, 0.0]
for threshold in thresholds:
    config = RetrievalConfig(threshold=threshold)
    retriever = ActivationRetriever(engine, config)
    results = retriever.retrieve(chunks, query_keywords, ...)

    # Manually label results as relevant/not relevant
    relevant = count_relevant(results)
    precision = relevant / len(results)

    print(f"Threshold {threshold:4.1f}: {len(results)} results, "
          f"{precision:.1%} precision")
```

**Expected Output**:
```
Threshold -5.0: 150 results, 35% precision
Threshold -3.0:  85 results, 55% precision
Threshold -2.0:  45 results, 75% precision ← Best balance
Threshold -1.0:  20 results, 85% precision
Threshold  0.0:   5 results, 95% precision
```

### Dynamic Threshold Adjustment

Adjust threshold based on query complexity:

```python
def adaptive_threshold(query_keywords: Set[str]) -> float:
    """Choose threshold based on query specificity."""
    keyword_count = len(query_keywords)

    if keyword_count == 1:
        return -3.0  # Broad query, be permissive
    elif keyword_count <= 3:
        return -2.0  # Typical query, balanced
    else:
        return -1.0  # Specific query, be strict

config = RetrievalConfig(
    threshold=adaptive_threshold(query_keywords)
)
```

---

## Query Optimization

### Type Pre-Filtering

Infer expected chunk types from query keywords:

```python
from aurora_core.optimization import QueryOptimizer, OptimizationConfig

# Enable type pre-filtering
config = OptimizationConfig(
    enable_type_filtering=True,
    type_patterns={
        'function': ['function', 'def', 'method', 'call'],
        'class': ['class', 'object', 'instance'],
        'test': ['test', 'spec', 'unittest', 'assert'],
    }
)

optimizer = QueryOptimizer(store, engine, config)
```

**How It Works**:
```python
# Query: "test database connection function"
# Inferred types: ['test', 'function']
# Only queries chunks of type 'test' or 'function'
# Reduces candidates from 10K to ~2K (5x speedup)
```

**Performance Impact**:
```
Without type filtering: 10,000 chunks → 450ms
With type filtering:     2,000 chunks →  90ms (5x faster)
```

**When to Use**:
- ✅ Large codebases (>5K chunks)
- ✅ Well-organized code (clear types)
- ❌ Small codebases (<1K chunks, overhead not worth it)
- ❌ Poorly organized code (types not meaningful)

### Keyword Optimization

Extract high-quality keywords to improve relevance:

```python
from aurora_core.activation import ContextBoostConfig

config = ContextBoostConfig(
    enable_stop_words=True,
    stop_words={
        # Common stop words
        'the', 'a', 'an', 'in', 'of', 'to', 'for',
        # Code-specific (keep programming terms!)
        'code', 'function', 'class', 'method',
    },
    programming_terms={
        # Keep these even if in stop words
        'if', 'for', 'while', 'def', 'class', 'return',
        'import', 'from', 'try', 'except', 'with'
    }
)
```

**Impact on Context Boost**:
```
Query: "how to handle database connection errors"

Without stop words:
  Keywords: ['how', 'to', 'handle', 'database', 'connection', 'errors']
  Matching chunk: ['database', 'connection', 'errors', 'try', 'except']
  Overlap: 3/6 = 50%

With stop words:
  Keywords: ['handle', 'database', 'connection', 'errors']
  Matching chunk: ['database', 'connection', 'errors', 'try', 'except']
  Overlap: 3/4 = 75% ← Better signal
```

---

## Batch Processing

### Batch Activation Calculation

Calculate activations in batches to reduce database queries:

```python
from aurora_core.activation import ActivationRetriever

# Process chunks in batches of 1000
results = retriever.retrieve(
    chunks=large_chunk_list,  # 10,000 chunks
    query_keywords=query_keywords,
    active_chunk_ids=active_ids,
    graph=graph,
    batch_size=1000  # Process 1000 at a time
)
```

**How It Works**:
```python
# Without batching: N queries (one per chunk)
# With batching: N/batch_size queries

# Example: 10,000 chunks
Without batching: 10,000 queries × 0.5ms = 5000ms
With batching:       10 queries × 50ms  =  500ms (10x faster)
```

**Optimal Batch Size**:
```python
# Small batches: More queries, less memory
batch_size = 500   # Conservative

# Medium batches: Balanced (recommended)
batch_size = 1000  # Default

# Large batches: Fewer queries, more memory
batch_size = 5000  # Aggressive
```

**Memory Impact**:
```
Memory = batch_size × chunk_size × concurrent_batches
       = 1000 × 5KB × 1 = 5MB ← Acceptable
       = 5000 × 5KB × 2 = 50MB ← High
```

### Batch Embedding Generation

Generate embeddings in batches for better GPU utilization:

```python
from aurora_context_code.semantic import EmbeddingProvider

provider = EmbeddingProvider()

# Batch embed multiple chunks
embeddings = provider.embed_batch(
    texts=[chunk.content for chunk in chunks],
    batch_size=32  # GPU-friendly batch size
)
```

**GPU Batch Size Tuning**:
- CPU: 8-16 (limited by memory)
- GPU: 32-128 (limited by VRAM)

---

## Parallel Execution

### Concurrent Agent Execution

Run multiple SOAR agents in parallel:

```python
from aurora_core.optimization import ParallelExecutor, ParallelConfig

config = ParallelConfig(
    max_workers=4,              # Number of concurrent agents
    enable_early_termination=True,  # Stop all if one fails critically
    enable_result_streaming=True,   # Return results as they arrive
    dynamic_scaling=True         # Adjust concurrency based on load
)

executor = ParallelExecutor(config)
```

**Concurrency Tuning**:
```python
# CPU cores available
import os
cpu_count = os.cpu_count()

# Conservative: Use half of cores
max_workers = cpu_count // 2

# Aggressive: Use all cores
max_workers = cpu_count

# For I/O-bound tasks (LLM API calls): Can exceed core count
max_workers = cpu_count * 2
```

**Performance Impact**:
```
Sequential execution:
  Agent 1: 2.5s
  Agent 2: 2.0s
  Agent 3: 1.8s
  Total: 6.3s

Parallel execution (3 workers):
  All agents: max(2.5s, 2.0s, 1.8s) = 2.5s
  Speedup: 2.5x
```

### Dynamic Concurrency Scaling

Automatically adjust based on response times:

```python
config = ParallelConfig(
    dynamic_scaling=True,
    min_workers=2,           # Never go below 2
    max_workers=8,           # Never exceed 8
    scale_up_threshold=500,  # Scale up if response time > 500ms
    scale_down_threshold=100 # Scale down if response time < 100ms
)
```

**Scaling Algorithm**:
```python
if avg_response_time > scale_up_threshold and workers < max_workers:
    workers += 1  # Add worker
elif avg_response_time < scale_down_threshold and workers > min_workers:
    workers -= 1  # Remove worker
```

---

## Memory Management

### Memory Footprint by Component

| Component | Memory Usage | Tuning Parameter |
|-----------|-------------|------------------|
| Hot cache | 5-50MB | `hot_cache_size` |
| Relationship graph | 10-30MB | `max_edges` |
| Activation scores cache | 2-10MB | `activation_cache_size` |
| Chunk metadata | 10-100MB | N/A (data-dependent) |
| Embeddings | 50-500MB | `embedding_cache_size` |

**Total for 10K chunks**: ~100-700MB (depends on configuration)

### Memory-Constrained Configuration

For systems with limited RAM:

```python
# Minimize memory footprint
cache_config = CacheConfig(
    hot_cache_size=500,           # Reduce hot cache
    activation_cache_size=1000,   # Reduce activation cache
    embedding_cache_size=500      # Reduce embedding cache
)

spreading_config = SpreadingConfig(
    max_edges=500,                # Limit graph size
    max_hops=2                    # Reduce traversal depth
)

optimization_config = OptimizationConfig(
    batch_size=500,               # Smaller batches
    enable_type_filtering=True    # Reduce candidates
)
```

**Memory Savings**:
```
Default config:  ~200MB
Memory-constrained: ~50MB (4x reduction)
Performance impact: ~20% slower (acceptable trade-off)
```

### Memory Profiling

Monitor memory usage:

```python
import tracemalloc

# Start profiling
tracemalloc.start()

# Execute retrieval
results = retriever.retrieve(...)

# Get memory usage
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

tracemalloc.stop()
```

---

## Profiling and Monitoring

### Built-in Metrics

AURORA collects performance metrics automatically:

```python
from aurora_core.resilience import MetricsCollector

collector = MetricsCollector()

# After running queries, get metrics
metrics = collector.get_metrics()

print("=== Performance Metrics ===")
print(f"Total queries: {metrics['query_count']}")
print(f"Average latency: {metrics['avg_latency_ms']:.1f}ms")
print(f"P95 latency: {metrics['p95_latency_ms']:.1f}ms")
print(f"P99 latency: {metrics['p99_latency_ms']:.1f}ms")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
print(f"Error rate: {metrics['error_rate']:.1%}")
```

### Custom Profiling

Profile specific components:

```python
import time

def profile_activation_calculation():
    """Profile activation calculation performance."""
    times = []

    for _ in range(100):
        start = time.time()
        engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading,
            chunk_keywords=chunk_keywords,
            query_keywords=query_keywords
        )
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)

    print(f"Activation calculation:")
    print(f"  Average: {sum(times) / len(times):.2f}ms")
    print(f"  Min: {min(times):.2f}ms")
    print(f"  Max: {max(times):.2f}ms")
    print(f"  P95: {sorted(times)[94]:.2f}ms")

profile_activation_calculation()
```

### Performance Dashboard

Monitor in real-time:

```python
from aurora_core.resilience import AlertingSystem, AlertRule

# Setup alerting
alerting = AlertingSystem()
alerting.add_rule(AlertRule(
    name="high_latency",
    condition=lambda m: m['p95_latency_ms'] > 1000,
    severity="warning",
    message="P95 latency exceeds 1000ms"
))

alerting.add_rule(AlertRule(
    name="low_cache_hit_rate",
    condition=lambda m: m['cache_hit_rate'] < 0.2,
    severity="info",
    message="Cache hit rate below 20%"
))

# Check periodically
import time
while True:
    metrics = collector.get_metrics()
    alerting.check(metrics)
    time.sleep(60)  # Check every minute
```

---

## Configuration Reference

### Complete Performance Configuration

```python
from aurora_core.optimization import (
    CacheManager, CacheConfig,
    QueryOptimizer, OptimizationConfig,
    ParallelExecutor, ParallelConfig
)
from aurora_core.activation import (
    ActivationEngine, ActivationConfig,
    RetrievalConfig
)

# === Cache Configuration ===
cache_config = CacheConfig(
    # Hot cache (Tier 1)
    hot_cache_size=1000,
    hot_cache_enabled=True,
    hot_cache_ttl=None,

    # Persistent cache (Tier 2)
    persistent_cache_enabled=True,
    persistent_cache_path="~/.aurora/cache.db",
    persistent_cache_sync_interval=100,

    # Activation scores cache (Tier 3)
    activation_cache_enabled=True,
    activation_cache_ttl=600,
    activation_cache_size=5000,

    # Promotion
    promotion_threshold=3
)

# === Query Optimization ===
optimization_config = OptimizationConfig(
    enable_type_filtering=True,
    type_patterns={
        'function': ['function', 'def', 'method'],
        'class': ['class', 'object', 'interface'],
        'test': ['test', 'spec', 'unittest'],
    },
    batch_size=1000,
    enable_batching=True
)

# === Retrieval Configuration ===
retrieval_config = RetrievalConfig(
    threshold=-2.0,
    max_results=20,
    include_components=False  # Disable for performance
)

# === Activation Configuration ===
activation_config = ActivationConfig(
    # Optimize spreading (most expensive)
    spreading_config=SpreadingConfig(
        max_hops=3,
        max_edges=1000,
        cache_rebuild_interval=100
    ),
    # Other components (already fast)
    bla_config=BLAConfig(decay_rate=0.5),
    context_config=ContextBoostConfig(boost_factor=0.5),
    decay_config=DecayConfig(decay_factor=0.5)
)

# === Parallel Execution ===
parallel_config = ParallelConfig(
    max_workers=4,
    enable_early_termination=True,
    enable_result_streaming=True,
    dynamic_scaling=True,
    min_workers=2,
    max_workers=8
)

# Initialize components
cache_manager = CacheManager(cache_config)
activation_engine = ActivationEngine(activation_config)
optimizer = QueryOptimizer(store, activation_engine, optimization_config)
retriever = ActivationRetriever(activation_engine, retrieval_config)
executor = ParallelExecutor(parallel_config)
```

### Configuration Presets

**Preset 1: Maximum Performance (Default)**
```python
config = PerformancePreset.MAXIMUM
# - All caching enabled
# - Type filtering enabled
# - Parallel execution enabled
# - Target: <500ms for 10K chunks
```

**Preset 2: Memory Constrained**
```python
config = PerformancePreset.MEMORY_CONSTRAINED
# - Small caches
# - Limited graph size
# - Smaller batches
# - Target: <100MB memory, <800ms latency
```

**Preset 3: Balanced**
```python
config = PerformancePreset.BALANCED
# - Moderate caching
# - Standard batching
# - Conservative parallelism
# - Target: <300ms for 5K chunks
```

---

## Troubleshooting

### Problem 1: High Latency (>1000ms)

**Symptoms**:
- Queries take >1 second
- Users experience noticeable delay

**Diagnosis**:
```python
# Profile each component
from aurora_core.profiling import profile_retrieval

profile = profile_retrieval(retriever, chunks, query)
print(profile.breakdown)
```

**Output**:
```
Candidate selection: 50ms
Activation calculation: 800ms ← Bottleneck
Semantic similarity: 150ms
Sorting: 5ms
```

**Solutions**:
1. **Enable caching**:
   ```python
   config.activation_cache_enabled = True
   ```

2. **Reduce candidates with type filtering**:
   ```python
   config.enable_type_filtering = True
   ```

3. **Increase threshold**:
   ```python
   retrieval_config.threshold = -1.0  # More strict
   ```

4. **Reduce graph size**:
   ```python
   spreading_config.max_edges = 500
   spreading_config.max_hops = 2
   ```

---

### Problem 2: Low Cache Hit Rate (<20%)

**Symptoms**:
- Cache hit rate below 20%
- Not seeing performance benefits from caching

**Diagnosis**:
```python
stats = cache_manager.get_stats()
print(f"Hot hits: {stats.hot_hits}")
print(f"Hot misses: {stats.hot_misses}")
print(f"Evictions: {stats.evictions}")
```

**Causes & Solutions**:

1. **Cache too small (high evictions)**:
   ```python
   # Increase cache size
   config.hot_cache_size = 2000
   ```

2. **Queries too diverse (no repeated access)**:
   ```python
   # Pre-warm cache with common queries
   common_queries = load_query_log()
   for query in common_queries:
       retriever.retrieve(chunks, query)
   ```

3. **TTL too short (cache expires)**:
   ```python
   # Increase TTL
   config.activation_cache_ttl = 1800  # 30 minutes
   ```

---

### Problem 3: High Memory Usage (>500MB)

**Symptoms**:
- Memory usage exceeds budget
- Out of memory errors

**Diagnosis**:
```python
import tracemalloc
tracemalloc.start()
# ... run retrieval ...
current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")
```

**Solutions**:

1. **Reduce cache sizes**:
   ```python
   config.hot_cache_size = 500
   config.activation_cache_size = 1000
   ```

2. **Limit graph size**:
   ```python
   config.max_edges = 500
   ```

3. **Disable embeddings cache**:
   ```python
   config.embedding_cache_size = 0  # Disable
   ```

4. **Use smaller batches**:
   ```python
   config.batch_size = 500
   ```

---

## Summary

### Quick Reference: Optimization Checklist

**For Small Codebases (<1K chunks)**:
- [ ] Use default configuration
- [ ] Enable hot cache (500 chunks)
- [ ] No need for type filtering
- [ ] Threshold: -2.0

**For Medium Codebases (1K-10K chunks)**:
- [ ] Enable all caching tiers
- [ ] Hot cache: 1000-2000 chunks
- [ ] Enable type filtering
- [ ] Batch size: 1000
- [ ] Threshold: -2.0
- [ ] Monitor cache hit rate (target: 30%)

**For Large Codebases (>10K chunks)**:
- [ ] Enable all optimizations
- [ ] Hot cache: 2000-5000 chunks
- [ ] Type filtering: Required
- [ ] Batch size: 1000-2000
- [ ] Threshold: -1.0 (stricter)
- [ ] Parallel execution: 4-8 workers
- [ ] Graph cache: Rebuild every 100 retrievals

### Performance Targets by Scale

| Chunks | Target Latency (p95) | Configuration |
|--------|---------------------|---------------|
| 100 | <100ms | Default |
| 1K | <200ms | Hot cache + batching |
| 10K | <500ms | All tiers + type filter |
| 100K | <1000ms | Aggressive optimization |

---

**Document Version**: 1.0
**Status**: Production Ready
**Last Updated**: December 23, 2025
**Related Tasks**: Task 8.5, Task 8.6
**Test Coverage**: Performance benchmarks validated

---

*For questions on performance tuning, refer to the AURORA project team or file a performance issue.*
