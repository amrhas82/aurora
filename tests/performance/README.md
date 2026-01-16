# Aurora Performance Benchmarks

This directory contains performance regression tests for Aurora commands, with a focus on startup time optimization.

## Quick Start

```bash
# Run all performance benchmarks
make benchmark

# Run only SOAR startup benchmarks
make benchmark-soar

# Run all startup benchmarks (soar, goals, init)
make benchmark-startup
```

## SOAR Startup Benchmarks

`test_soar_startup_performance.py` tracks the initialization time for `aur soar` command.

### Key Metrics

**Target: <3 seconds from invocation to first LLM call**

Breakdown:
- CLI parsing and imports: <2s
- Config loading: <500ms
- Database connection: <100ms
- Agent discovery: <1s
- Orchestrator initialization: <500ms
- Background model loading: non-blocking

### Test Categories

1. **Command Startup**
   - Help response time (<1s)
   - Critical import time (<2s)
   - No heavy imports at module level

2. **Configuration**
   - Config load time (<500ms)

3. **Store Initialization**
   - SQLite connection (<100ms)
   - Memory check query (<50ms)

4. **Agent Discovery**
   - Registry initialization (<100ms)
   - Manifest loading (<1s)

5. **Orchestrator Setup**
   - Orchestrator init without LLM (<500ms)

6. **Background Loading**
   - Background model loading start (<100ms)
   - Cache check is lightweight (no torch import)

7. **End-to-End**
   - Full startup to LLM call (<3s)
   - Phase callbacks fire early (<1s)

8. **Regression Guards**
   - Strict thresholds prevent performance degradation
   - Fails CI if startup time regresses

## Running Specific Test Classes

```bash
# Test only import time
pytest tests/performance/test_soar_startup_performance.py::TestSOARCommandStartup -v

# Test only background loading
pytest tests/performance/test_soar_startup_performance.py::TestBackgroundModelLoading -v

# Test regression guards
pytest tests/performance/test_soar_startup_performance.py::TestRegressionGuards -v
```

## Understanding Results

### Example Output
```
test_soar_help_response_time PASSED [0.234s]
test_critical_imports_fast PASSED [1.456s]
test_soar_command_startup_to_llm_call PASSED [2.789s]
```

Times in brackets are actual execution times. Assertions verify they're under target thresholds.

### Baseline Performance

On typical developer machine with warm cache:
- Help: ~200-400ms
- Imports: ~1-1.5s
- Config: ~100-300ms
- Store init: ~20-50ms
- Total startup: ~2-2.5s

### Regression Indicators

If tests fail:
1. Check for new heavy imports at module level
2. Verify background loading is working
3. Check if config loading is doing heavy I/O
4. Review database connection pooling
5. Profile with `pytest --profile` or `py-spy`

## Optimization History

Track improvements here:

- v0.9.0: Initial baseline (~5-7s startup)
- v0.10.0: Added background model loading (~3-4s)
- v0.11.0: Lazy imports for torch/transformers (~2-3s)
- Target: <3s consistent startup time

## Adding New Benchmarks

```python
def test_new_operation_fast(self):
    """Verify new operation is fast (<Xms)."""
    start = time.time()
    # ... operation ...
    elapsed = time.time() - start

    assert elapsed < TARGET, (
        f"Operation took {elapsed:.3f}s (target: <{TARGET}s). "
        "Explanation of why this matters."
    )
```

Always include:
- Clear target threshold
- Timing measurement
- Helpful error message explaining impact
- Context about why the operation should be fast

## CI Integration

These tests run in CI to prevent performance regressions:

```yaml
- name: Performance Tests
  run: make benchmark-startup
```

Failures block PRs that degrade startup performance.
