# Embedding Model Load Time Profiling

This document describes the profiling methodology and baseline metrics for measuring embedding model load times in the Aurora project.

## Overview

The embedding model loading process is a critical performance bottleneck that can impact:
- **CLI startup time**: First-run experience for commands using semantic search
- **Background loading**: Impact on concurrent operations during startup
- **User experience**: Perceived responsiveness of the application

## Profiling Tool

### Location
`scripts/profile_embedding_load.py`

### Purpose
Comprehensive profiling of the embedding model loading process with:
- Stage-by-stage timing breakdown
- Multiple run statistics with confidence intervals
- Memory usage tracking
- Performance target comparisons
- JSON report generation for historical tracking

### Usage

#### Basic profiling (warm start, 5 runs)
```bash
python3 scripts/profile_embedding_load.py
```

#### Cold start profiling (clears cache)
```bash
python3 scripts/profile_embedding_load.py --cold-start
```

#### Custom configuration
```bash
python3 scripts/profile_embedding_load.py \
  --model all-MiniLM-L6-v2 \
  --runs 10 \
  --output reports/my_baseline.json
```

#### Compare with baseline
```bash
python3 scripts/profile_embedding_load.py \
  --baseline reports/embedding_load_warm_baseline.json
```

#### Using the shell runner
```bash
# Warm start (default)
./scripts/run_embedding_profile.sh

# Cold start
COLD_START=true ./scripts/run_embedding_profile.sh

# Custom configuration
RUNS=10 MODEL=all-mpnet-base-v2 ./scripts/run_embedding_profile.sh
```

## Load Time Breakdown

The profiling tool measures four distinct stages:

### 1. Import Time
**What it measures**: Time to import `sentence_transformers` and dependencies (torch, transformers, etc.)

**Typical range**: 0.5s - 1.5s (warm start)

**Optimization opportunities**:
- Lazy imports (defer until actually needed)
- Conditional imports (skip if embeddings not required)
- Pre-compiled bytecode caching

### 2. Model Init Time
**What it measures**: Time to instantiate `SentenceTransformer` and load model weights from cache

**Typical range**: 2.0s - 4.0s (warm start with cached model)

**Optimization opportunities**:
- Background loading in separate thread
- Model file optimization (quantization, pruning)
- Faster storage (SSD vs HDD impact)

### 3. First Encode Time
**What it measures**: Time for first embedding generation (model warmup)

**Typical range**: 50ms - 200ms

**Notes**:
- First encode is slower due to CUDA initialization (if using GPU)
- Subsequent encodes are much faster (~10-50ms)

### 4. Memory Usage
**What it measures**: Memory delta from before import to after first encode

**Typical range**: 100MB - 400MB (model size + runtime overhead)

**Factors**:
- Model size (MiniLM-L6 ~90MB, MPNet ~420MB)
- Torch/CUDA overhead
- Python interpreter overhead

## Performance Targets

Current performance targets for **warm start** (model cached):

| Metric | Target | Rationale |
|--------|--------|-----------|
| Total Load Time | ≤ 5.0s | Acceptable startup delay for CLI operations |
| Import Time | ≤ 1.0s | Minimize dependency import overhead |
| Model Init Time | ≤ 3.0s | Allow time for loading model weights |
| First Encode | ≤ 200ms | Quick warmup for first operation |
| Memory Usage | ≤ 500MB | Reasonable memory footprint |

For **cold start** (model not cached):
- Add ~30-90 seconds for model download (88MB for default model)
- First-time users expected to wait during download
- Should only occur once per environment

## Baseline Metrics

### Default Model (all-MiniLM-L6-v2)

**Warm Start Baseline** (as of YYYY-MM-DD):
```
Total Load Time:    X.XX ± X.XX s
├─ Import Time:     X.XX ± X.XX s
├─ Model Init:      X.XX ± X.XX s
└─ First Encode:    X.XX ± X.XX s

Memory Delta:       XXX ± XX MB
```

To establish initial baseline:
```bash
python3 scripts/profile_embedding_load.py --output reports/embedding_load_warm_baseline.json
```

**Cold Start Baseline**:
```bash
python3 scripts/profile_embedding_load.py --cold-start --output reports/embedding_load_cold_baseline.json
```

## Interpreting Results

### Good Performance Indicators
- ✓ Total time < 5s (warm start)
- ✓ Low standard deviation (< 0.5s) indicates consistent performance
- ✓ Import time < 1s
- ✓ Memory usage < 500MB

### Performance Concerns
- ⚠️ Total time > 5s: Consider background loading or optimization
- ⚠️ High standard deviation (> 1s): Investigate system resource contention
- ⚠️ Import time > 2s: Heavy dependency imports, consider lazy loading
- ⚠️ Model init > 5s: Slow disk I/O or large model, consider caching strategy

## Optimization Strategies

### 1. Background Loading (Current Implementation)
**File**: `packages/context-code/src/aurora_context_code/semantic/model_utils.py`

**Class**: `BackgroundModelLoader`

**Strategy**: Start model loading in background thread during CLI initialization, before embeddings are needed.

**Benefits**:
- Non-blocking startup
- Model ready by the time user needs it
- Graceful fallback to BM25-only if not ready

**Implementation**:
```python
# Early in CLI startup
from aurora_context_code.semantic.model_utils import BackgroundModelLoader
loader = BackgroundModelLoader.get_instance()
loader.start_loading()  # Returns immediately

# Later, when embeddings needed
provider = loader.wait_for_model(timeout=60.0)
```

### 2. Lazy Initialization (Current Implementation)
**File**: `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py`

**Strategy**: Defer model loading until first `embed_*()` call.

**Benefits**:
- Zero startup cost if embeddings not used
- Commands like `aur --help` remain instant

### 3. Offline Mode
**Strategy**: Set `HF_HUB_OFFLINE=1` to skip network checks when model is cached.

**Benefits**:
- Faster initialization (no network timeout)
- Works in offline environments

### 4. Model Selection
Consider alternative models for different use cases:

| Model | Size | Load Time | Quality | Use Case |
|-------|------|-----------|---------|----------|
| paraphrase-MiniLM-L3-v2 | 66MB | ~2s | Good | Fast iteration |
| all-MiniLM-L6-v2 | 88MB | ~3s | Better | Default (current) |
| all-mpnet-base-v2 | 420MB | ~8s | Best | High-quality search |

## Continuous Monitoring

### Tracking Over Time
1. Run profiling before making changes:
   ```bash
   python3 scripts/profile_embedding_load.py --output reports/before.json
   ```

2. Make optimization changes

3. Run profiling again:
   ```bash
   python3 scripts/profile_embedding_load.py --baseline reports/before.json
   ```

4. Review comparison output to verify improvement

### Regression Detection
- Run profiling in CI/CD pipeline
- Compare against baseline to detect regressions
- Alert if load time increases > 20%

### Example CI Integration
```yaml
- name: Profile Embedding Load Time
  run: |
    python3 scripts/profile_embedding_load.py \
      --output reports/current.json \
      --baseline reports/baseline.json

    # Fail if >20% slower than baseline
    python3 scripts/check_performance_regression.py \
      --current reports/current.json \
      --baseline reports/baseline.json \
      --threshold 1.2
```

## Related Files

- `scripts/profile_embedding_load.py` - Main profiling tool
- `scripts/run_embedding_profile.sh` - Shell runner script
- `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py` - Embedding provider with lazy loading
- `packages/context-code/src/aurora_context_code/semantic/model_utils.py` - Background loader implementation
- `packages/cli/src/aurora_cli/memory/retrieval.py` - Integration point for CLI

## Dependencies

Profiling requires:
- `sentence-transformers` - ML dependencies
- `psutil` (optional) - For memory measurement
- Python 3.10+

Install with:
```bash
pip install sentence-transformers psutil
```

## Troubleshooting

### "sentence-transformers not installed"
Install ML dependencies:
```bash
pip install aurora-context-code[ml]
# or
pip install sentence-transformers torch
```

### High variability in results
- Close other applications to reduce resource contention
- Run with more iterations: `--runs 10`
- Check disk I/O (loading from HDD vs SSD)

### Cold start fails
- Ensure internet connectivity for model download
- Check HuggingFace Hub status
- Verify disk space (~200MB needed)

### Memory measurement shows 0MB
Install psutil:
```bash
pip install psutil
```

## Future Improvements

Potential optimization areas:
1. **Model quantization**: Reduce model size with INT8 quantization
2. **Model pruning**: Remove unnecessary layers
3. **Precompiled models**: Use ONNX/TorchScript for faster loading
4. **Persistent model service**: Keep model loaded in background service
5. **Progressive loading**: Load critical layers first, remaining in background

## References

- [sentence-transformers documentation](https://www.sbert.net/)
- [HuggingFace Hub caching](https://huggingface.co/docs/huggingface_hub/guides/manage-cache)
- [PyTorch model loading optimization](https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html)
