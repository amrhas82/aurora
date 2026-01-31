# Embedding Load Time Profiling Infrastructure

> **Comprehensive tooling for measuring, tracking, and optimizing embedding model load times**

## Quick Start

### Run profiling now (5 runs, warm start)
```bash
cd /home/hamr/PycharmProjects/aurora
python3 scripts/profile_embedding_load.py
```

### Interactive workflow example
```bash
./examples/profiling_workflow_example.sh
```

## What This Provides

This profiling infrastructure gives you:

1. ✅ **Detailed load time measurements** - Stage-by-stage breakdown of model loading
2. ✅ **Statistical confidence** - Multiple runs with mean, median, stdev, min, max
3. ✅ **Memory profiling** - Track memory usage during loading
4. ✅ **Performance targets** - Clear benchmarks for acceptable performance
5. ✅ **Baseline comparison** - Detect improvements or regressions
6. ✅ **Actionable recommendations** - Data-driven optimization suggestions
7. ✅ **CI/CD integration** - Automated regression detection

## Tools Included

| Tool | Purpose | Usage |
|------|---------|-------|
| **profile_embedding_load.py** | Main profiling tool | `python3 scripts/profile_embedding_load.py` |
| **run_embedding_profile.sh** | Shell wrapper | `./scripts/run_embedding_profile.sh` |
| **check_performance_regression.py** | CI/CD regression check | `python3 scripts/check_performance_regression.py` |
| **profiling_workflow_example.sh** | Interactive tutorial | `./examples/profiling_workflow_example.sh` |

## Documentation

- **📖 [Complete Documentation](docs/performance/embedding_load_profiling.md)** - Methodology, targets, optimization strategies
- **📝 [Quick Reference](scripts/README_PROFILING.md)** - Commands and examples
- **📊 [Summary](PROFILING_SUMMARY.md)** - Deliverables overview

## Common Tasks

### Establish Baseline
```bash
# First time - establish baseline
python3 scripts/profile_embedding_load.py \
  --output reports/embedding_load_warm_baseline.json
```

### Before/After Comparison
```bash
# Before optimization
python3 scripts/profile_embedding_load.py --output reports/before.json

# ... make optimization changes ...

# After optimization - compare with before
python3 scripts/profile_embedding_load.py --baseline reports/before.json
```

### Test Cold Start (First-time User Experience)
```bash
python3 scripts/profile_embedding_load.py --cold-start
```

### Compare Different Models
```bash
# Default model (MiniLM-L6)
python3 scripts/profile_embedding_load.py --model all-MiniLM-L6-v2

# Faster model (MiniLM-L3)
python3 scripts/profile_embedding_load.py --model paraphrase-MiniLM-L3-v2

# Higher quality model (MPNet)
python3 scripts/profile_embedding_load.py --model all-mpnet-base-v2
```

### CI/CD Integration
```bash
# Profile and check for regression
python3 scripts/profile_embedding_load.py --output reports/current.json
python3 scripts/check_performance_regression.py \
  --current reports/current.json \
  --baseline reports/baseline.json \
  --threshold 1.2  # Fail if >20% slower
```

## What Gets Measured

### Stage Breakdown
1. **Import Time** - Loading sentence-transformers and dependencies
2. **Model Init Time** - Instantiating and loading model weights
3. **First Encode Time** - First embedding generation (warmup)
4. **Memory Usage** - Memory delta from start to finish

### Statistics Per Stage
- Mean (average across runs)
- Median (middle value)
- Standard deviation (variability)
- Min/Max (range)

## Performance Targets

| Metric | Target (Warm) | Current Status |
|--------|---------------|----------------|
| Total Load Time | ≤ 5.0s | Run profiling to measure |
| Import Time | ≤ 1.0s | Run profiling to measure |
| Model Init | ≤ 3.0s | Run profiling to measure |
| First Encode | ≤ 200ms | Run profiling to measure |
| Memory Usage | ≤ 500MB | Run profiling to measure |

## Example Output

```
================================================================================
PROFILING RESULTS
================================================================================

📋 Summary (WARM START)
   Model: all-MiniLM-L6-v2
   Runs: 5 (5 successful)

⏱️  Timing Breakdown (mean ± stdev)
--------------------------------------------------------------------------------
   Total Load Time:       3.28 ± 0.15s  (range: 3.10-3.45s)
   ├─ Import Time:        0.84 ± 0.08s  (range: 0.75-0.92s)
   ├─ Model Init Time:    2.31 ± 0.12s  (range: 2.18-2.44s)
   └─ First Encode Time:  0.13 ± 0.02s  (range: 0.11-0.15s)

💾 Memory Usage
--------------------------------------------------------------------------------
   Memory Delta:  243.8 ± 5.2MB

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
```

## Workflow

### 1. Initial Setup
```bash
# Establish baseline (run once)
python3 scripts/profile_embedding_load.py \
  --output reports/embedding_load_warm_baseline.json
```

### 2. Before Making Changes
```bash
# Profile current state
python3 scripts/profile_embedding_load.py --output reports/before.json
```

### 3. After Making Changes
```bash
# Profile and compare
python3 scripts/profile_embedding_load.py \
  --baseline reports/before.json \
  --output reports/after.json
```

### 4. Verify No Regression
```bash
# Automated check (for CI/CD)
python3 scripts/check_performance_regression.py \
  --current reports/after.json \
  --baseline reports/before.json \
  --threshold 1.2
```

## Integration Points

### Development
- Profile before optimization work
- Profile after to measure impact
- Use recommendations to guide next steps

### CI/CD Pipeline
```yaml
- name: Profile Embedding Load
  run: |
    python3 scripts/profile_embedding_load.py \
      --output reports/current.json

- name: Check Regression
  run: |
    python3 scripts/check_performance_regression.py \
      --current reports/current.json \
      --baseline reports/baseline.json \
      --threshold 1.2
```

### Performance Tracking
- Generate reports periodically
- Store in version control
- Track trends over time
- Identify gradual degradation

## Dependencies

### Required
```bash
pip install sentence-transformers torch
```

### Optional (for memory profiling)
```bash
pip install psutil
```

## Files Created

```
aurora/
├── scripts/
│   ├── profile_embedding_load.py          # Main profiling tool
│   ├── check_performance_regression.py    # Regression checker
│   ├── run_embedding_profile.sh           # Shell wrapper
│   └── README_PROFILING.md                # Quick reference
├── examples/
│   └── profiling_workflow_example.sh      # Interactive tutorial
├── docs/
│   └── performance/
│       └── embedding_load_profiling.md    # Full documentation
├── reports/                                # Generated reports (git-ignored)
│   ├── baseline_warm.json
│   ├── baseline_cold.json
│   └── *.json
├── PROFILING_SUMMARY.md                    # Deliverables summary
└── README_EMBEDDING_PROFILING.md           # This file
```

## Optimization Context

This profiling infrastructure helps measure the impact of:

### Current Optimizations
- **Background loading** (`BackgroundModelLoader` in `model_utils.py`)
- **Lazy initialization** (`EmbeddingProvider` in `embedding_provider.py`)
- **Graceful degradation** (BM25-only fallback in `retrieval.py`)

### Potential Optimizations
- Model quantization (INT8)
- Model pruning
- Persistent model service
- ONNX/TorchScript compilation
- Alternative models (MiniLM-L3 for speed, MPNet for quality)

## Troubleshooting

### "command not found: python"
Use `python3` instead:
```bash
python3 scripts/profile_embedding_load.py
```

### "sentence-transformers not installed"
Install dependencies:
```bash
pip install sentence-transformers torch
```

### High variability in results
- Close other applications
- Increase runs: `--runs 10`
- Check disk I/O (SSD vs HDD)

### Memory shows 0MB
Install psutil:
```bash
pip install psutil
```

## Getting Help

1. **Quick reference**: `cat scripts/README_PROFILING.md`
2. **Full docs**: `cat docs/performance/embedding_load_profiling.md`
3. **Tool help**: `python3 scripts/profile_embedding_load.py --help`
4. **Interactive tutorial**: `./examples/profiling_workflow_example.sh`

## What's Next?

1. ✅ **Run profiling** - Establish your baseline metrics
2. ✅ **Review results** - Understand current performance
3. ✅ **Identify bottlenecks** - Use stage breakdown to find issues
4. ✅ **Implement optimizations** - Try suggestions from recommendations
5. ✅ **Measure impact** - Re-run profiling with baseline comparison
6. ✅ **Track over time** - Add to CI/CD for continuous monitoring

## Success Criteria

Your profiling is successful when:
- ✅ Baseline metrics are established
- ✅ Performance targets are understood
- ✅ Bottlenecks are identified
- ✅ Optimization impact is measured
- ✅ Regressions are prevented via CI/CD

---

**Ready to start?** Run the interactive tutorial:
```bash
./examples/profiling_workflow_example.sh
```

Or dive straight in with:
```bash
python3 scripts/profile_embedding_load.py
```
