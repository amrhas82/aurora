# Embedding Load Time Profiling Scripts

Quick reference for profiling embedding model load times in Aurora.

## Quick Start

### Run default profiling (warm start, 5 runs)
```bash
./scripts/run_embedding_profile.sh
```

### Run cold start profiling (clears cache)
```bash
COLD_START=true ./scripts/run_embedding_profile.sh
```

### Custom runs
```bash
RUNS=10 MODEL=all-mpnet-base-v2 ./scripts/run_embedding_profile.sh
```

## Direct Python Usage

### Basic profiling
```bash
python3 scripts/profile_embedding_load.py
```

### All options
```bash
python3 scripts/profile_embedding_load.py \
  --model all-MiniLM-L6-v2 \
  --runs 5 \
  --output reports/my_report.json \
  --baseline reports/baseline.json \
  --cold-start
```

### Help
```bash
python3 scripts/profile_embedding_load.py --help
```

## Output

The tool generates:
1. **Console output**: Detailed timing breakdown and recommendations
2. **JSON report**: Saved to `reports/` directory for tracking over time

### Sample Output
```
================================================================================
EMBEDDING MODEL LOAD PROFILING
================================================================================

Model: all-MiniLM-L6-v2
Runs: 5

📦 Using cached model (warm start)

🔍 Running 5 profiling iterations...

  Run #1 (warm start)
    [1/4] Importing dependencies... 0.87s
    [2/4] Loading model... 2.34s
    [3/4] First encode (warmup)... 0.12s
    [4/4] Measuring memory... 245.3MB
    ✓ Total: 3.33s

  [... additional runs ...]

================================================================================
PROFILING RESULTS
================================================================================

⏱️  Timing Breakdown (mean ± stdev)
--------------------------------------------------------------------------------
   Total Load Time:       3.28 ± 0.15s  (range: 3.10-3.45s)
   ├─ Import Time:        0.84 ± 0.08s  (range: 0.75-0.92s)
   ├─ Model Init Time:    2.31 ± 0.12s  (range: 2.18-2.44s)
   └─ First Encode Time:  0.13 ± 0.02s  (range: 0.11-0.15s)

💾 Memory Usage
--------------------------------------------------------------------------------
   Memory Delta:  243.8 ± 5.2MB  (range: 238.0-250.0MB)

🎯 Performance vs Targets
--------------------------------------------------------------------------------
   ✓ Total Load             3.28s / 5.0s target
   ✓ Import                 0.84s / 1.0s target
   ✓ Model Init             2.31s / 3.0s target
   ✓ First Encode           130ms / 200ms target
   ✓ Memory Usage           244MB / 500MB target

💡 Recommendations
--------------------------------------------------------------------------------
   ✓ Warm start time (3.28s) meets target (5.0s)
   ✓ Acceptable memory usage (244MB)

💾 Report saved to: reports/embedding_load_warm_baseline.json
```

## Files

- **profile_embedding_load.py** - Main profiling tool with detailed metrics
- **run_embedding_profile.sh** - Shell wrapper for easy execution
- **benchmark_embedding_models.py** - Compare different models (encoding speed)

## Performance Targets

| Metric | Target (Warm) | Target (Cold) |
|--------|---------------|---------------|
| Total Load | ≤ 5.0s | ~30-90s (download) |
| Import | ≤ 1.0s | ≤ 1.0s |
| Model Init | ≤ 3.0s | ~30-90s |
| First Encode | ≤ 200ms | ≤ 200ms |
| Memory | ≤ 500MB | ≤ 500MB |

## Establishing Baseline

### First time setup
```bash
# Warm start baseline
python3 scripts/profile_embedding_load.py \
  --output reports/embedding_load_warm_baseline.json

# Cold start baseline
python3 scripts/profile_embedding_load.py \
  --cold-start \
  --output reports/embedding_load_cold_baseline.json
```

### Compare changes
```bash
# Before making changes
python3 scripts/profile_embedding_load.py \
  --output reports/before.json

# ... make optimization changes ...

# After changes - compare with before
python3 scripts/profile_embedding_load.py \
  --baseline reports/before.json
```

## Interpreting Results

### Good Signs ✓
- Total time < 5s (warm start)
- Low standard deviation (< 0.5s)
- All metrics meet targets
- Memory usage < 500MB

### Warning Signs ⚠️
- Total time > 5s - Consider background loading
- High std dev (> 1s) - System resource contention
- Import time > 2s - Too many heavy dependencies
- Model init > 5s - Slow disk or large model

## Optimization Tips

1. **Background loading** - Start loading early, use `BackgroundModelLoader`
2. **Lazy initialization** - Don't load until needed
3. **Offline mode** - Set `HF_HUB_OFFLINE=1` when cached
4. **Smaller model** - Consider paraphrase-MiniLM-L3-v2 for faster load
5. **SSD storage** - Store cache on SSD vs HDD

## Dependencies

```bash
# Required for profiling
pip install sentence-transformers torch

# Optional (for memory measurement)
pip install psutil
```

## Documentation

See `docs/performance/embedding_load_profiling.md` for comprehensive documentation.

## Common Issues

### Import errors
```bash
pip install sentence-transformers torch
```

### Permission errors on cache clear
```bash
# Run with appropriate permissions or skip cold-start
# (warm start doesn't need cache clear)
```

### No baseline file
```bash
# First run creates baseline automatically
python3 scripts/profile_embedding_load.py
```

## Integration with Development

### Before committing optimization
```bash
# Profile before changes
python3 scripts/profile_embedding_load.py --output reports/before.json

# Make changes...

# Profile after and compare
python3 scripts/profile_embedding_load.py --baseline reports/before.json
```

### CI/CD Integration
Add to CI pipeline to catch regressions:
```yaml
- run: python3 scripts/profile_embedding_load.py --baseline reports/baseline.json
```

## Related Tools

- **benchmark_embedding_models.py** - Compare different models
- **test_embedding_provider.py** - Unit tests for embedding provider
- **test_embedding_benchmarks.py** - Archived performance tests

## Contact

For questions or issues with profiling, see:
- `docs/performance/embedding_load_profiling.md` - Full documentation
- `packages/context-code/src/aurora_context_code/semantic/` - Implementation
