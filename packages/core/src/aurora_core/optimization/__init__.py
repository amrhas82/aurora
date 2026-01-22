"""AURORA Core - Performance Optimization Module

This module provides performance optimization components for large codebase support:

- **QueryOptimizer**: Pre-filtering, activation thresholding, batch processing
- **CacheManager**: Multi-tier caching (hot cache, persistent, activation scores)
- **ParallelAgentExecutor**: Dynamic concurrency, early termination, result streaming

**Performance Targets**:
- 100 chunks: <100ms retrieval
- 1K chunks: <200ms retrieval
- 10K chunks: <500ms retrieval (p95)
- Cache hit rate: ≥30% after 1000 queries
- Memory footprint: ≤100MB for 10K cached chunks

**Usage**::

    from aurora_core.optimization import QueryOptimizer, CacheManager

    # Initialize cache manager
    cache = CacheManager(hot_cache_size=1000, ttl_seconds=600)

    # Optimize queries with pre-filtering and thresholding
    optimizer = QueryOptimizer(
        cache_manager=cache,
        activation_threshold=0.3,
        enable_type_filtering=True
    )

    # Execute optimized retrieval
    results = optimizer.retrieve(
        query="authentication logic",
        top_k=10,
        chunk_types=["function", "class"]
    )

**Architecture**:

1. **Query Optimization** (query_optimizer.py):
   - Pre-filter by chunk type (infer from query keywords)
   - Apply activation threshold (skip chunks < 0.3)
   - Batch activation calculations (single SQL query)

2. **Multi-Tier Caching** (cache_manager.py):
   - Hot cache: LRU, 1000 chunks, in-memory
   - Persistent cache: SQLite, all chunks
   - Activation scores cache: 10-minute TTL
   - Cache promotion on access

3. **Parallel Execution** (parallel_executor.py):
   - Dynamic concurrency scaling
   - Early termination on critical failures
   - Result streaming (start synthesis early)

**Performance Considerations**:

- Pre-compute embeddings during storage, not query-time
- Cache relationship graph for spreading activation
- Use activation threshold to skip low-activation chunks early
- Batch activation calculations to minimize database queries
- Limit spreading activation to 3 hops, 1000 edges max
"""

from aurora_core.optimization.cache_manager import CacheManager
from aurora_core.optimization.parallel_executor import ParallelAgentExecutor
from aurora_core.optimization.query_optimizer import QueryOptimizer


__all__ = [
    "CacheManager",
    "ParallelAgentExecutor",
    "QueryOptimizer",
]
