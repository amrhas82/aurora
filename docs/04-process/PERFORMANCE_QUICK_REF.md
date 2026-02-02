# Performance Testing Quick Reference

One-page reference for Aurora performance benchmarks.

## Commands

```bash
make benchmark-soar          # SOAR startup only (~30s)
make benchmark-startup       # All startup tests (~2min)
make benchmark              # Full suite (~5min)
```

## Current Targets

| Command | Target | Status |
|---------|--------|--------|
| `aur soar` | <3s | ✓ |
| `aur goals` | <5s | ✓ |
| `aur init` | <7s | ✓ |

## Regression Guards (CI)

```python
MAX_IMPORT_TIME = 2.0s           # CLI imports
MAX_CONFIG_TIME = 0.5s           # Config loading
MAX_STORE_INIT_TIME = 0.1s       # Database connection
MAX_TOTAL_STARTUP_TIME = 3.0s    # End-to-end
```

## Quick Validation

```bash
# Run CI checks locally
pytest tests/performance/test_soar_startup_performance.py::TestRegressionGuards -v
```

## Common Fixes

### Import too slow (>2s)
```python
# Move heavy imports inside functions
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(...)
```

### Config too slow (>500ms)
```python
# Use lazy properties
@property
def expensive_setting(self):
    if not hasattr(self, '_cached'):
        self._cached = compute_expensive()
    return self._cached
```

### Store init too slow (>100ms)
- Check database file location
- Defer index creation
- Use connection pooling

## Profiling

```bash
# Interactive flamegraph
py-spy record -o profile.svg -- aur soar "test"

# Benchmark with stats
pytest tests/performance/test_soar_startup_performance.py \
  --benchmark-only --benchmark-verbose

# Compare runs
hyperfine 'aur soar "test"' --warmup 3
```

## Adding New Tests

```python
def test_new_operation_fast(self):
    """Verify operation is fast (<Xms)."""
    start = time.time()
    # ... operation ...
    elapsed = time.time() - start

    assert elapsed < TARGET, (
        f"Took {elapsed:.3f}s (target: <{TARGET}s). "
        "Why this matters."
    )
```

## When CI Fails

1. Run locally: `make benchmark-soar`
2. Check which threshold failed
3. Profile: `py-spy record -o profile.svg -- aur soar "test"`
4. Fix the hotspot
5. Verify: Re-run benchmarks
6. Update threshold if environment changed

## Performance Checklist

Before merging:
- [ ] No new heavy imports at module level
- [ ] Config changes are lazy/cached
- [ ] Database operations are minimal
- [ ] Background loading still works
- [ ] Regression guards pass: `make benchmark-soar`

## Links

- Full guide: `docs/PERFORMANCE_TESTING.md`
- Test suite: `tests/performance/`
- Benchmark README: `tests/performance/README.md`
