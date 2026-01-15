# Plan Decomposition Cache Performance Benchmarks

Comprehensive performance benchmarking suite comparing cached vs non-cached decomposition operations.

## Overview

This benchmark suite measures the performance impact of the plan decomposition cache layer, validating that:
- Cache lookups are fast enough to provide net benefit
- Cache overhead on misses is negligible
- Persistent storage performs within acceptable bounds
- End-to-end decomposition achieves significant speedup

## Running Benchmarks

```bash
# Run all cache benchmarks
pytest tests/performance/test_decomposition_cache_benchmarks.py -v --benchmark-only

# Run specific benchmark class
pytest tests/performance/test_decomposition_cache_benchmarks.py::TestMemoryCacheGetPerformance -v --benchmark-only

# Generate comparison report
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only --benchmark-compare

# Save baseline for comparison
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only --benchmark-save=baseline

# Compare against baseline
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only --benchmark-compare=baseline
```

## Performance Targets

### Cache Operations
| Operation | Target | Critical Path |
|-----------|--------|--------------|
| Memory cache GET (hit) | <1ms | Yes - every decomposition |
| Memory cache GET (miss) | <1ms | Yes - first decomposition |
| Memory cache SET | <5ms | No - async after decomposition |
| Persistent cache GET (cold) | <5ms | Yes - cross-session reuse |
| Persistent cache SET | <10ms | No - async write |

### Key Metrics
| Metric | Target | Rationale |
|--------|--------|-----------|
| Cache hit speedup | ≥50x | Justifies cache complexity |
| Cache miss overhead | <5% | Negligible when miss occurs |
| Key computation | <0.1ms | Minimal overhead |
| 99th percentile latency | <2x mean | Consistent performance |

### End-to-End Impact
| Scenario | Without Cache | With Cache (hit) | Speedup |
|----------|--------------|------------------|---------|
| Simple decomposition | ~5ms | <0.5ms | 10x |
| Moderate decomposition | ~10ms | <0.5ms | 20x |
| Complex decomposition | ~50ms | <1ms | 50x |

## Benchmark Categories

### 1. Cache Key Computation (`TestCacheKeyComputationPerformance`)

Measures overhead of computing cache keys from goal, complexity, and context files.

**Key Tests:**
- `test_key_computation_simple` - Basic key generation (<0.1ms)
- `test_key_computation_with_context` - Key with 10 context files (<0.2ms)

**Why It Matters:**
Key computation happens on every decomposition call (hit or miss). Must be fast enough to not negate cache benefits.

### 2. Memory Cache GET (`TestMemoryCacheGetPerformance`)

Measures latency of in-memory cache lookups.

**Key Tests:**
- `test_cache_hit_latency` - Hot cache hit (<1ms)
- `test_cache_miss_latency` - Cache miss (<1ms)
- `test_cache_hit_with_lru_access` - Hit with LRU update (<2ms)

**Why It Matters:**
Memory cache is the fast path. Most decompositions should hit here for optimal performance.

### 3. Memory Cache SET (`TestMemoryCacheSetPerformance`)

Measures latency of writing to in-memory cache.

**Key Tests:**
- `test_cache_set_new_entry` - Add new entry (<5ms)
- `test_cache_set_with_eviction` - SET triggering LRU eviction (<10ms)
- `test_cache_update_existing` - Update existing entry (<5ms)

**Why It Matters:**
SET operations happen after decomposition completes. Acceptable to be slower than GET, but shouldn't block.

### 4. Persistent Cache GET (`TestPersistentCacheGetPerformance`)

Measures latency of SQLite persistent cache reads.

**Key Tests:**
- `test_persistent_hit_cold_cache` - Cold cache, DB read (<5ms)
- `test_persistent_hit_warm_cache` - After promotion to memory (<1ms)

**Why It Matters:**
Persistent cache enables cross-session reuse. Must be fast enough that cold starts still benefit from cache.

### 5. Persistent Cache SET (`TestPersistentCacheSetPerformance`)

Measures latency of SQLite persistent cache writes.

**Key Tests:**
- `test_persistent_set_latency` - Single write operation (<10ms)
- `test_bulk_persistent_writes` - 100 writes (<1000ms)

**Why It Matters:**
Persistent writes happen asynchronously. Can be slower than memory operations but must complete within session.

### 6. Cache Scalability (`TestCacheScalabilityPerformance`)

Validates cache performance at scale (1000 entries).

**Key Tests:**
- `test_cache_performance_at_capacity` - Access when full (<2ms)
- `test_eviction_at_scale` - Eviction at 1000 entries (<10ms)

**Why It Matters:**
Cache must maintain performance characteristics as it fills. LRU operations shouldn't degrade significantly.

### 7. End-to-End Speedup (`TestEndToEndCacheSpeedup`)

Measures real-world cache benefit vs non-cached decomposition.

**Key Tests:**
- `test_decomposition_speedup_ratio` - Cached vs non-cached (≥50x)
- `test_cache_overhead_on_miss` - Miss overhead (<1ms, <5% of decomposition)

**Why It Matters:**
Ultimate validation that cache provides net benefit. Speedup must justify implementation complexity.

### 8. Additional Benchmarks

- **Metrics Overhead** - Cost of metrics tracking (<0.1ms)
- **Serialization** - Subgoal serialization/deserialization (<1ms)
- **Concurrent Access** - Mixed read/write workloads (<5ms)
- **Comparison Summary** - Comprehensive before/after comparison

## Interpreting Results

### Success Criteria

All benchmarks pass if:
1. Mean times meet targets (stated in assertions)
2. Standard deviation is low (consistent performance)
3. Speedup ratios exceed minimums
4. No performance regressions vs baseline

### Warning Signs

Investigate if you see:
- Cache hit >1ms consistently (memory cache too slow)
- Cache miss >5% of decomposition time (overhead too high)
- Speedup <50x (cache not providing sufficient benefit)
- High standard deviation (inconsistent performance)
- Persistent cache >10ms (SQLite I/O issues)

### Performance Tuning

If benchmarks fail:

**Cache too slow:**
- Review LRU implementation (OrderedDict operations)
- Check if serialization is bottleneck
- Profile cache key computation
- Consider disabling metrics in production

**Persistent cache too slow:**
- Check SQLite pragma settings
- Review index usage (timestamp index)
- Consider batch writes
- Verify I/O is not blocking

**Insufficient speedup:**
- Increase cache capacity (default: 100)
- Extend TTL (default: 24h)
- Review cache key strategy (are hits occurring?)
- Profile actual decomposition time

## Example Output

```
===== Cache Performance Summary =====
Memory cache hit:          0.234ms
Memory cache miss:         0.456ms
Full decomposition (sim):  10.0ms
Cache speedup:             42.7x
Cache miss overhead:       4.6%
=====================================

test_cache_hit_latency PASSED                    [mean: 0.234ms, std: 0.012ms]
test_cache_miss_latency PASSED                   [mean: 0.456ms, std: 0.023ms]
test_decomposition_speedup_ratio PASSED          [speedup: 42.7x]
test_persistent_hit_cold_cache PASSED            [mean: 3.456ms, std: 0.234ms]
test_cache_overhead_on_miss PASSED               [overhead: 4.6%]
```

## Comparison with Existing Benchmarks

### vs Activation Benchmarks (`test_activation_benchmarks.py`)

**Similarities:**
- Use pytest-benchmark for accurate timing
- Test realistic data distributions
- Validate performance targets from design
- Measure component vs full-system performance

**Differences:**
- Cache benchmarks focus on I/O latency (memory, SQLite)
- Activation benchmarks focus on computation (math, traversal)
- Cache measures speedup ratios vs absolute times
- Cache tests persistence layer (activation doesn't)

### Integration

Both benchmark suites validate Aurora's performance-critical paths:
- Activation: Memory retrieval ranking (hot path)
- Cache: Plan decomposition reuse (reduces LLM calls)

Together they ensure Aurora meets <200ms retrieval + decomposition target.

## Continuous Monitoring

### CI Integration

Add to CI pipeline:
```yaml
- name: Run cache performance benchmarks
  run: |
    pytest tests/performance/test_decomposition_cache_benchmarks.py \
      --benchmark-only \
      --benchmark-compare=baseline \
      --benchmark-fail=mean:0.005  # Fail if mean >5ms
```

### Performance Regression Detection

1. Establish baseline: `pytest --benchmark-save=baseline`
2. On each commit: `pytest --benchmark-compare=baseline`
3. Alert if:
   - Mean increases >20%
   - Standard deviation increases >50%
   - Any assertion fails (targets not met)

### Monitoring Dashboards

Track in production:
- Cache hit rate (target: ≥40%)
- Average GET latency (target: <1ms)
- 99th percentile latency (target: <2ms)
- Eviction rate
- Persistent storage size

## Troubleshooting

### Benchmark Flakiness

If benchmarks are inconsistent:
1. Run with more iterations: `--benchmark-min-rounds=100`
2. Increase warmup: `--benchmark-warmup=on`
3. Disable CPU frequency scaling
4. Run on dedicated benchmarking host

### Platform Differences

Performance targets are for reference hardware (modern multi-core):
- Memory cache should be consistent across platforms
- Persistent cache may vary with I/O performance
- Adjust targets for embedded/constrained environments

### Profiling

For detailed analysis:
```bash
# Profile specific benchmark
pytest tests/performance/test_decomposition_cache_benchmarks.py::TestMemoryCacheGetPerformance::test_cache_hit_latency \
  --benchmark-only \
  --profile

# Generate flame graph
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only --profile-svg
```

## Contributing

When adding cache features:
1. Add corresponding performance benchmark
2. Set target based on use case criticality
3. Validate speedup justifies complexity
4. Update this guide with new benchmarks

When optimizing cache:
1. Run benchmarks before changes (baseline)
2. Make optimization
3. Run benchmarks after changes
4. Verify improvement and no regressions
5. Update targets if justified
