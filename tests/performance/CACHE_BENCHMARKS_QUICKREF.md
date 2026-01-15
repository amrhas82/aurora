# Cache Benchmarks Quick Reference

## Run Commands

```bash
# All benchmarks
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only

# Specific category
pytest tests/performance/test_decomposition_cache_benchmarks.py::TestMemoryCacheGetPerformance --benchmark-only

# With comparison summary
pytest tests/performance/test_decomposition_cache_benchmarks.py::TestCacheComparisonSummary::test_comprehensive_comparison -v -s

# Save baseline
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only --benchmark-save=baseline

# Compare against baseline
pytest tests/performance/test_decomposition_cache_benchmarks.py --benchmark-only --benchmark-compare=baseline
```

## Performance Targets At-a-Glance

| Operation | Target | Pass/Fail Threshold |
|-----------|--------|---------------------|
| Memory cache hit | <1ms | 1ms |
| Memory cache miss | <1ms | 1ms |
| Memory cache SET | <5ms | 5ms |
| Persistent cache hit | <5ms | 5ms |
| Persistent cache SET | <10ms | 10ms |
| Cache key computation | <0.1ms | 0.1ms |
| Cache speedup | ≥50x | 50x |
| Cache miss overhead | <5% | 5% |

## Benchmark Categories (8 total, 25+ tests)

1. **Key Computation** - Hash generation overhead
2. **Memory GET** - In-memory lookup latency
3. **Memory SET** - In-memory write latency
4. **Persistent GET** - SQLite read latency
5. **Persistent SET** - SQLite write latency
6. **Scalability** - Performance at capacity (1000 entries)
7. **End-to-End** - Real-world speedup validation
8. **Additional** - Metrics, serialization, concurrency

## Expected Output

```
Memory cache hit: 0.234ms (target: <1ms) ✓
Persistent cache hit (cold): 3.456ms (target: <5ms) ✓
Cache speedup: 42.7x (target: ≥50x) ✗ (failed)
Cache miss overhead: 4.6% (target: <5%) ✓

CACHE PERFORMANCE SUMMARY
Memory cache hit:          0.234ms
Memory cache miss:         0.456ms
Full decomposition (sim):  10.0ms
Cache speedup:             42.7x
Cache miss overhead:       4.6%

PASSED: 24/25 (96%)
FAILED: test_decomposition_speedup_ratio (speedup: 42.7x < 50x)
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Cache hit >1ms | LRU overhead | Profile OrderedDict ops |
| Speedup <50x | Low simulated time | Adjust to realistic 10-50ms |
| Persistent >10ms | SQLite I/O | Check pragmas, indexes |
| High std dev | System load | Run on idle system |
| Flaky tests | Warmup needed | Add --benchmark-warmup |

## Integration with Existing Tests

```bash
# Run all performance benchmarks (activation + cache)
pytest tests/performance/ --benchmark-only

# Compare activation vs cache performance
pytest tests/performance/test_activation_benchmarks.py::TestFullActivationPerformance --benchmark-only
pytest tests/performance/test_decomposition_cache_benchmarks.py::TestEndToEndCacheSpeedup --benchmark-only
```

## CI/CD Integration

```yaml
# .github/workflows/performance.yml
- name: Cache Performance Benchmarks
  run: |
    pytest tests/performance/test_decomposition_cache_benchmarks.py \
      --benchmark-only \
      --benchmark-compare=baseline \
      --benchmark-fail=mean:0.005
```

## Key Metrics for Monitoring

- **Cache hit rate**: ≥40% (operational target)
- **Mean GET latency**: <1ms (performance target)
- **99th percentile latency**: <2ms (consistency target)
- **Speedup ratio**: ≥50x (value target)
- **Miss overhead**: <5% (efficiency target)
