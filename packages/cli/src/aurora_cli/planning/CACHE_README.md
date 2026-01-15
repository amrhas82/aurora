# Plan Decomposition Cache

Specialized caching layer for PlanDecomposer to avoid redundant LLM calls and expensive SOAR operations.

## Architecture

### Cache Strategy

**Multi-tier cache** with LRU eviction and TTL expiration:

1. **In-Memory Cache** (Tier 1): Fast LRU cache for frequent access
   - Capacity: 100 decompositions (configurable)
   - Eviction: Least Recently Used (LRU)
   - Performance: <1ms lookup

2. **Persistent Cache** (Tier 2): SQLite storage for cross-session caching
   - Location: `.aurora/cache/decomposition_cache.db`
   - TTL: 24 hours (configurable)
   - Auto-promotion to in-memory on access

### Cache Key Generation

Cache keys incorporate:
- Goal text (full string)
- Complexity level (SIMPLE, MODERATE, COMPLEX)
- Context files (sorted list for consistent ordering)

Hash: SHA256 truncated to 32 characters

### Data Structure

**In-Memory**: OrderedDict for O(1) access and LRU ordering
**Persistent**: SQLite with indexed timestamp for TTL cleanup

## Usage

### Basic Usage

```python
from aurora_cli.planning.decompose import PlanDecomposer
from aurora_cli.planning.models import Complexity

# Initialize with cache
decomposer = PlanDecomposer(
    cache_capacity=100,
    cache_ttl_hours=24,
    enable_persistent_cache=True
)

# Decompose (automatically cached)
subgoals, source = decomposer.decompose(
    goal="Add authentication",
    complexity=Complexity.MODERATE,
    context_files=["auth.py", "user.py"]
)

# Check cache statistics
stats = decomposer.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Cache size: {stats['size']}/{stats['capacity']}")
```

### Cache Statistics

```python
stats = decomposer.get_cache_stats()
# Returns:
# {
#     'size': 42,           # Current entries
#     'capacity': 100,      # Maximum capacity
#     'hits': 85,           # Cache hits
#     'misses': 58,         # Cache misses
#     'hit_rate': 0.594,    # Hit rate (0.0-1.0)
#     'evictions': 3        # LRU evictions
# }
```

### Manual Cache Management

```python
# Clear all caches
decomposer.clear_cache()

# Direct cache access
from aurora_cli.planning.cache import PlanDecompositionCache
from pathlib import Path

cache = PlanDecompositionCache(
    capacity=50,
    ttl_hours=12,
    persistent_path=Path(".aurora/cache/custom_cache.db")
)

# Get cached result
result = cache.get("Add auth", Complexity.MODERATE)
if result:
    subgoals, source = result

# Set cached result
cache.set("Add auth", Complexity.MODERATE, subgoals, "soar")

# Cleanup expired entries
removed = cache.cleanup_expired()
```

## Performance Targets

- **Cache hit rate**: ≥40% for typical workflows
- **Memory footprint**: ≤5MB for 100 cached decompositions
- **Cache lookup**: <1ms (in-memory), <5ms (persistent)
- **Cache promotion**: <2ms (persistent → in-memory)

## Configuration

### Environment Variables

None currently - configured via constructor parameters.

### Constructor Parameters

```python
PlanDecomposer(
    cache_capacity=100,              # Max in-memory entries
    cache_ttl_hours=24,              # TTL for cache entries
    enable_persistent_cache=True     # Enable SQLite persistence
)
```

### Persistent Cache Location

Default: `.aurora/cache/decomposition_cache.db`

The cache directory is created automatically if it doesn't exist.

## Cache Behavior

### Cache Hits

Cache hits when:
- Exact goal string match
- Same complexity level
- Same context files (order-independent)
- Entry not expired (TTL)

### Cache Misses

Cache misses when:
- Goal differs
- Complexity level differs
- Context files differ
- Entry expired
- Cache cleared/evicted

### LRU Eviction

When cache reaches capacity:
1. Least recently used entry is evicted
2. Most recently accessed entries are preserved
3. Recent access updates LRU ordering

### TTL Expiration

Entries expire after configured TTL:
- Default: 24 hours
- Expired entries removed on access
- Periodic cleanup via `cleanup_expired()`

## Testing

Comprehensive test suite covering:
- Cache hits and misses
- LRU eviction behavior
- TTL expiration
- Persistent storage
- Cache promotion
- Statistics tracking
- Key generation

Run tests:
```bash
pytest tests/unit/cli/planning/test_cache.py -v
```

## Integration Points

### PlanDecomposer Integration

The cache is transparently integrated into `PlanDecomposer.decompose()`:

```python
def decompose(self, goal, complexity, context_files):
    # Check cache first
    cached_result = self.cache.get(goal, complexity, context_files)
    if cached_result:
        return cached_result

    # Expensive decomposition...
    subgoals = self._call_soar(...)

    # Cache result
    self.cache.set(goal, complexity, subgoals, "soar", context_files)
    return (subgoals, "soar")
```

### SOAR Integration

Cache wraps SOAR decomposition to avoid redundant LLM calls:
- First call: Invoke SOAR, cache result
- Subsequent calls: Return cached result (skip SOAR)
- Cache miss: Re-invoke SOAR if needed

## Memory Management

### Memory Estimates

- In-memory cache: ~50KB per decomposition
- 100 decompositions: ~5MB
- Persistent storage: ~100KB per decomposition (includes JSON)

### Cache Size Recommendations

- **Small projects**: 50 decompositions (2.5MB)
- **Medium projects**: 100 decompositions (5MB) - default
- **Large projects**: 200 decompositions (10MB)

### Cleanup Strategies

1. **Automatic TTL**: Entries expire after 24 hours
2. **LRU eviction**: Old entries removed when capacity reached
3. **Manual cleanup**: Call `clear_cache()` or `cleanup_expired()`

## Future Enhancements

Potential improvements:
- [ ] Cache warming on project load
- [ ] Adaptive TTL based on access patterns
- [ ] Cache size metrics and monitoring
- [ ] Distributed cache for team workflows
- [ ] Cache export/import for sharing
- [ ] Compression for persistent storage
- [ ] Multi-level cache statistics

## Related Components

- **CacheManager** (`aurora_core.optimization.cache_manager`): General-purpose multi-tier cache
- **MemoryRetriever** (`aurora_cli.memory.retrieval`): Context retrieval with its own caching
- **SOAR Decompose** (`aurora_soar.phases.decompose`): Has module-level cache (in-memory only)

## Design Decisions

### Why LRU?

LRU (Least Recently Used) is optimal for decomposition caching because:
- Frequently used goals stay in cache
- Recent queries are likely to be repeated
- Simple implementation with O(1) operations
- Predictable memory usage

### Why TTL?

TTL prevents stale decompositions from persisting when:
- Codebase changes (new files, refactoring)
- Agent manifest updates (new agents available)
- Planning strategies evolve

### Why Persistent Cache?

Persistent storage provides:
- Cross-session caching (faster startup)
- Reduced LLM costs for repeated workflows
- Cache survival across restarts
- Shared cache in team environments (future)

### Why Not Redis/Memcached?

Tradeoffs:
- SQLite: Simple, no dependencies, file-based
- Redis: Better for distributed, requires server
- Memcached: Better for high concurrency, requires server

Decision: Start simple with SQLite, migrate to Redis if needed for team workflows.
