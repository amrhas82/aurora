# Performance Testing Guide

This guide explains how to measure, track, and improve Aurora's startup performance using the benchmark suite.

## Quick Start

```bash
# Run all SOAR startup benchmarks
make benchmark-soar

# Run all startup benchmarks (soar, goals, init)
make benchmark-startup

# Run full benchmark suite
make benchmark
```

## Why Startup Performance Matters

Users experience startup time as **latency before seeing progress**. A slow startup feels broken:

- 0-1s: Instant (ideal)
- 1-3s: Acceptable (current target)
- 3-5s: Noticeable delay
- 5s+: Feels broken, users report bugs

### Current State

Command | Target | Typical | Status
--------|--------|---------|-------
`aur soar` | <3s | 2-3s | ✓ Target met
`aur goals` | <5s | 3-4s | ✓ Target met
`aur init` | <7s | 5-6s | ✓ Target met

## Understanding the Benchmarks

### test_soar_startup_performance.py

Tracks `aur soar` startup from CLI invocation to first LLM call.

**Key metrics:**
- Total startup time: <3s
- Import time: <2s
- Config loading: <500ms
- Store initialization: <100ms
- Agent discovery: <1s

**What it tests:**
1. No heavy imports at module level
2. Background model loading is non-blocking
3. Lazy loading works correctly
4. Database connections are fast
5. Configuration parsing is efficient

### Regression Guards

`TestRegressionGuards` class contains strict thresholds that **fail CI** if performance regresses:

```python
MAX_IMPORT_TIME = 2.0           # seconds
MAX_CONFIG_TIME = 0.5           # seconds
MAX_STORE_INIT_TIME = 0.1       # seconds
MAX_TOTAL_STARTUP_TIME = 3.0    # seconds
```

These run on every push to `main` to catch regressions immediately.

## Running Benchmarks Locally

### Full benchmark with statistics

```bash
pytest tests/performance/test_soar_startup_performance.py -v \
  --benchmark-only --benchmark-verbose
```

Output shows min/max/mean/stddev for each test.

### Quick validation (regression guards only)

```bash
pytest tests/performance/test_soar_startup_performance.py::TestRegressionGuards -v
```

This is what runs in CI. Fast way to check if changes broke performance.

### Specific test class

```bash
# Test just imports
pytest tests/performance/test_soar_startup_performance.py::TestSOARCommandStartup -v

# Test just background loading
pytest tests/performance/test_soar_startup_performance.py::TestBackgroundModelLoading -v

# Test end-to-end startup
pytest tests/performance/test_soar_startup_performance.py::TestEndToEndStartup -v
```

## Profiling Slow Startups

If benchmarks fail or you want to dig deeper:

### 1. Use pytest profiling

```bash
pytest tests/performance/test_soar_startup_performance.py \
  --profile --profile-svg
```

Opens an SVG flamegraph showing where time is spent.

### 2. Use py-spy for production profiling

```bash
# Profile actual command
py-spy record -o profile.svg -- aur soar "test query"
```

Shows real-world performance including imports and initialization.

### 3. Add timing instrumentation

```python
import time

start = time.time()
# ... code to measure ...
print(f"Operation took {time.time() - start:.3f}s")
```

Quick way to narrow down slow code paths.

## Common Performance Issues

### Issue: Heavy imports at module level

**Symptom:** Import time test fails (>2s)

**Check:**
```bash
pytest tests/performance/test_soar_startup_performance.py::TestSOARCommandStartup::test_no_heavy_imports_at_module_level -v
```

**Fix:** Move imports inside functions or use lazy loading:

```python
# Bad - imports torch at module level
import torch
from sentence_transformers import SentenceTransformer

# Good - lazy import
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(...)
```

### Issue: Config loading doing heavy I/O

**Symptom:** Config time test fails (>500ms)

**Check:**
```bash
pytest tests/performance/test_soar_startup_performance.py::TestConfigurationLoading -v
```

**Fix:**
- Cache parsed config
- Defer file discovery until needed
- Use lazy properties for expensive operations

### Issue: Background model loading not working

**Symptom:** Total startup >3s but should be ~2s

**Check:**
```bash
pytest tests/performance/test_soar_startup_performance.py::TestBackgroundModelLoading -v
```

**Fix:**
- Verify `_start_background_model_loading()` is called early
- Check that model cache check is lightweight
- Ensure thread is actually started

### Issue: Database operations slow

**Symptom:** Store init test fails (>100ms)

**Check:**
```bash
pytest tests/performance/test_soar_startup_performance.py::TestStoreInitialization -v
```

**Fix:**
- Check database file location (should be local)
- Verify no heavy migrations on connect
- Use connection pooling
- Defer index creation until first use

## Optimizing Startup

### Priority order

1. **Remove heavy imports from module level** (biggest impact)
2. **Enable background model loading** (parallel work)
3. **Lazy load config** (defer until needed)
4. **Cache expensive operations** (avoid recomputation)
5. **Profile and optimize hotspots** (data-driven)

### Measuring improvement

Before and after any optimization:

```bash
# Run benchmark 10 times and compare
for i in {1..10}; do
  time aur soar "test query" > /dev/null
done

# Or use hyperfine for statistical comparison
hyperfine 'aur soar "test"' --warmup 3
```

### Setting targets

When adding new benchmarks:

```python
# Base target on current performance + 20% buffer
# Example: Current = 400ms, Target = 500ms
assert elapsed < 0.5, "Config loading regression"
```

This allows normal variation while catching real regressions.

## CI Integration

### What runs automatically

On every push to `main`:
```bash
pytest tests/performance/test_soar_startup_performance.py::TestRegressionGuards -v
```

This ensures no PR degrades startup performance.

### Interpreting CI failures

If CI fails on performance tests:

1. Check the test output for which threshold failed
2. Run locally: `make benchmark-soar`
3. Compare timing to threshold
4. If consistently over threshold, investigate (see profiling above)
5. If just noisy CI, may need to adjust threshold

### Adjusting thresholds

Edit `tests/performance/test_soar_startup_performance.py`:

```python
class TestRegressionGuards:
    # Adjust these if CI is too strict/loose
    MAX_IMPORT_TIME = 2.0
    MAX_CONFIG_TIME = 0.5
    # ...
```

Guidelines:
- Threshold should be ~20-30% above typical time
- Account for CI environment being slower
- Don't set too loose or regressions slip through
- Don't set too strict or false positives occur

## Adding New Benchmarks

When adding new commands or features:

```python
def test_new_feature_startup_fast(self):
    """Verify new feature doesn't slow startup (<Xms)."""
    start = time.time()

    # Measure the operation
    from aurora_cli.commands.new_feature import new_command

    elapsed = time.time() - start

    assert elapsed < TARGET, (
        f"New feature import took {elapsed:.3f}s (target: <{TARGET}s). "
        "Avoid heavy imports at module level."
    )
```

Then add to regression guards:

```python
class TestRegressionGuards:
    MAX_NEW_FEATURE_TIME = 1.0  # seconds

    def test_guard_new_feature_time(self):
        """REGRESSION GUARD: New feature must stay fast."""
        # ... test implementation ...
```

## Best Practices

1. **Measure first, optimize second** - Profile before changing code
2. **One optimization at a time** - Easier to identify what helped
3. **Compare before/after** - Use `hyperfine` or benchmark suite
4. **Document improvements** - Update performance history in README
5. **Set regression guards** - Prevent future slowdowns

## Performance History

Track major improvements here:

Version | Optimization | Before | After | Improvement
--------|--------------|--------|-------|------------
v0.9.0  | Baseline | - | 5-7s | -
v0.10.0 | Background loading | 5-7s | 3-4s | 40-50%
v0.11.0 | Lazy imports | 3-4s | 2-3s | 25-33%

Target: Maintain <3s startup time across all environments.

## Troubleshooting

### Tests pass locally but fail in CI

**Cause:** CI environment slower than local machine

**Solutions:**
- Check CI runner specs vs local
- Add 30-50% buffer to thresholds
- Use relative measurements (compare runs, not absolute time)

### Benchmarks are noisy/flaky

**Cause:** Background processes, thermal throttling, shared CI

**Solutions:**
- Run with `--benchmark-warmup` to stabilize
- Increase sample size: `--benchmark-min-rounds=10`
- Use median instead of mean for comparisons

### Can't reproduce performance issue

**Cause:** Environment differences, cache state, hardware

**Solutions:**
- Clear caches: `make clean && make install`
- Check Python version matches
- Profile in same environment as issue report
- Use `py-spy` to capture real-world usage

## Resources

- [pytest-benchmark docs](https://pytest-benchmark.readthedocs.io/)
- [py-spy profiler](https://github.com/benfred/py-spy)
- [Python profiling guide](https://docs.python.org/3/library/profile.html)
- [hyperfine benchmarking](https://github.com/sharkdp/hyperfine)
