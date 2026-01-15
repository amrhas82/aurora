# Memory Indexing Performance - Quick Reference

## TL;DR

**Problem:** Indexing is 49x slower than expected (0.9 files/sec vs 10-50 target)
**Root Cause:** Embedding generation takes 86% of time at 9.5 chunks/sec
**Fix:** GPU acceleration + larger batches = 20-30x speedup

## Bottleneck Hierarchy

```
Total: 102.4s (0.9 files/sec)
├─ Embedding: 88.0s (86%) ← PRIMARY BOTTLENECK
├─ Git blame: 7.9s (8%)
├─ Parsing: 4.2s (4%)
└─ Database: 2.1s (2%)
```

## Quick Wins (Low Effort)

| Optimization | Code Change | Speedup | Effort |
|--------------|-------------|---------|--------|
| Larger batch size | `batch_size=128` | 2-3x | 5 min |
| Faster model | `all-MiniLM-L6-v2` | 2-3x | 10 min |
| Skip git on index | `--skip-git` flag | 1.1x | 30 min |
| DB pragmas | Add 3 PRAGMAs | 1.05x | 10 min |

**Combined quick wins: 4-9x faster with <1 hour work**

## Major Optimizations (High Effort)

| Optimization | Speedup | Effort | Requires |
|--------------|---------|--------|----------|
| GPU acceleration | 10-15x | 2-4 hours | CUDA GPU |
| Parallel parsing | 3-4x | 4-8 hours | Refactoring |
| Incremental indexing | Skip 80% | 1-2 days | Schema changes |

## Run Profiler

```bash
# Profile specific path
python3 profile_memory_indexing.py --path packages/cli --num-files 20

# Full codebase profile
python3 profile_memory_indexing.py --path . --output profile.json
```

## Measure Performance

```python
# Before optimization
from aurora_cli.memory_manager import MemoryManager
import time

start = time.time()
manager = MemoryManager(config=config)
stats = manager.index_path("packages/cli")
duration = time.time() - start
throughput = stats.files_indexed / duration
print(f"Throughput: {throughput:.1f} files/sec")
```

## Target Metrics

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Overall | 0.9 files/sec | 10+ files/sec | 11x |
| Embedding | 9.5 chunks/sec | 100+ chunks/sec | 10x |
| Parsing | 22.6 files/sec | 100+ files/sec | 4x |

## Implementation Checklist

**Phase 1: Quick wins (1 day)**
- [ ] Increase batch size to 128
- [ ] Switch to all-MiniLM-L6-v2 model
- [ ] Add --skip-git flag
- [ ] Add database pragmas
- [ ] Expected: 4-9x speedup

**Phase 2: GPU acceleration (2-4 days)**
- [ ] Add CUDA detection
- [ ] Conditional GPU model loading
- [ ] Fallback to CPU if no GPU
- [ ] Benchmarking suite
- [ ] Expected: +10-15x speedup (total: 40-135x)

**Phase 3: Parallelization (1 week)**
- [ ] ProcessPoolExecutor for parsing
- [ ] Async git blame
- [ ] Thread-safe state management
- [ ] Expected: +2-3x speedup (total: 80-405x)

**Phase 4: Incremental indexing (1-2 weeks)**
- [ ] File hash tracking
- [ ] Modification detection
- [ ] Partial re-indexing
- [ ] Expected: Skip 80-95% on re-index

## Code Locations

| Component | File | Line |
|-----------|------|------|
| Indexing pipeline | `packages/cli/src/aurora_cli/memory_manager.py` | 202-527 |
| Embedding generation | `packages/cli/src/aurora_cli/memory_manager.py` | 310-311 |
| Git blame | `packages/context-code/src/aurora_context_code/git.py` | - |
| DB writes | `packages/core/src/aurora_core/store/sqlite.py` | - |
| Parsing | `packages/context-code/src/aurora_context_code/languages/` | - |

## Example Optimization

**Before:**
```python
# Slow: CPU only, small batches
embeddings = self.embedding_provider.embed_batch(texts, batch_size=32)
```

**After:**
```python
# Fast: GPU + large batches
if torch.cuda.is_available():
    device = 'cuda'
    batch_size = 128
else:
    device = 'cpu'
    batch_size = 64

model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
```

## Validation

```bash
# Run benchmark suite
pytest tests/performance/test_indexing_benchmarks.py -v

# Profile after changes
python3 profile_memory_indexing.py --path packages/cli --num-files 50

# Compare results
diff memory_profile_report.json memory_profile_report_optimized.json
```

## Contact

See `MEMORY_INDEXING_PERFORMANCE_REPORT.md` for detailed analysis.
