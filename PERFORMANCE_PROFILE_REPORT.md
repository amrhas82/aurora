# Memory Indexing Performance Profile Report

**Date:** 2026-01-13
**Analyzed Component:** Aurora Memory Indexing Pipeline
**Test Dataset:** packages/cli/src/aurora_cli (95 Python files, 840 code chunks)

## Executive Summary

Memory indexing performance is **dominated by embedding generation (88.4% of total time)**. With a throughput of 8.3 chunks/second, embedding 840 chunks takes 89 seconds—nearly the entire 100-second runtime.

**Critical Finding:** Embedding is the bottleneck by a factor of 24x compared to the next-slowest component (parsing at 3.6%).

## Performance Breakdown

### Overall Metrics
- **Total Time:** 100.74s
- **Files Processed:** 95
- **Chunks Created:** 840
- **Throughput:** 0.9 files/sec, 8.3 chunks/sec

### Phase Timing (Percentage of Total)

| Phase | Time (s) | % of Total | Status |
|-------|----------|------------|--------|
| **Embedding** | 89.05 | 88.4% | 🔴 Critical Bottleneck |
| Overhead | 6.89 | 6.8% | 🟡 Minor |
| Parsing | 3.58 | 3.6% | 🟢 Acceptable |
| DB Writes | 1.22 | 1.2% | 🟢 Acceptable |
| Git Blame | 0.00 | 0.0% | 🟢 Negligible |

### Per-Operation Metrics

**Parsing (111 calls)**
- Avg per file: 37.7ms
- Well-optimized, not a bottleneck

**Embedding (27 batches)**
- Avg per chunk: 106.0ms
- Avg batch size: 31.1 chunks
- **Most expensive operation by far**

**Database Writes (840 writes)**
- Avg per write: 1.45ms
- SQLite WAL mode enabled
- Already optimized

## Bottleneck Analysis

### 1. Embedding Generation (PRIMARY BOTTLENECK)

**Impact:** 88.4% of total time

**Root Cause:**
- CPU-bound sentence-transformer model inference
- Sequential batch processing (batch_size=32)
- No GPU acceleration detected
- Heavy model (likely all-MiniLM-L6-v2 or larger)

**Evidence:**
- 106ms per chunk is extremely slow for embedding
- 27 batches × 3.3s per batch = 89s total
- Model loading/inference dominates pipeline

### 2. Parsing (ACCEPTABLE)

**Impact:** 3.6% of total time

**Performance:**
- 37.7ms per file (fast)
- tree-sitter parsing is efficient
- Not a bottleneck

### 3. Database Writes (OPTIMIZED)

**Impact:** 1.2% of total time

**Configuration:**
- WAL mode: ✓ Enabled
- Page size: 4096 bytes
- Cache size: -2000 pages (~2MB)
- Synchronous: FULL (level 2)
- 1.45ms per write is reasonable

**Already Optimized:**
- Batch writes per file
- WAL journal mode
- Adequate cache size

### 4. Git Blame (NEGLIGIBLE)

**Impact:** 0.0% of total time

**Status:**
- File-level caching working perfectly
- No performance concern

## Optimization Recommendations

### Priority 1: Embedding Acceleration (24x Impact)

**Option A: GPU Acceleration** (Fastest)
```python
# Install: pip install sentence-transformers[onnx]
# Use CUDA if available, ~10-50x speedup
embedding_provider = EmbeddingProvider(device="cuda")
```
Expected: 89s → 2-9s (10-50x faster)

**Option B: Lighter Model** (Easy)
```python
# Switch from all-MiniLM-L6-v2 (384 dim) to:
# - paraphrase-MiniLM-L3-v2 (128 dim, 2x faster)
# - all-MiniLM-L12-v2 (lightweight, 1.5x faster)
```
Expected: 89s → 45-60s (1.5-2x faster)

**Option C: Embedding Cache** (Best Long-term)
```python
# Cache embeddings by content hash
# Skip re-embedding unchanged code
cache = EmbeddingCache(store)
embeddings = cache.get_or_compute(content_hash, content)
```
Expected: Incremental indexing ~90% faster

**Option D: Parallel Batch Processing** (Moderate)
```python
# Process multiple batches concurrently
# Requires careful model thread safety
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(embed_batch, batch) for batch in batches]
```
Expected: 89s → 45s (2x faster)

### Priority 2: Pipeline Optimization

**Increase Batch Size**
```python
# Current: batch_size=32
# Try: batch_size=64 or 128
manager.index_path(path, batch_size=128)
```
Expected: 5-10% speedup (batch overhead reduction)

### Priority 3: Database Tuning (Already Good)

Current configuration is solid:
- WAL mode ✓
- Reasonable cache size ✓
- Batch writes ✓

Minor improvements:
```sql
PRAGMA cache_size = -10000;  -- Increase to 10MB
PRAGMA synchronous = NORMAL;  -- Less fsync (safe with WAL)
```
Expected: 1.22s → 0.8s (marginal improvement)

## Performance Targets

| Scenario | Current | Target | Method |
|----------|---------|--------|--------|
| Full Codebase Index | 100.74s | **10-15s** | GPU + Cache |
| Incremental Re-index | 100.74s | **5-10s** | Embedding Cache |
| Large Repo (10,000 chunks) | ~20 min | **2-3 min** | GPU Acceleration |

## Implementation Priority

1. **Implement GPU acceleration** (if hardware available)
   - Check: `torch.cuda.is_available()`
   - Instant 10-50x speedup

2. **Add embedding cache layer**
   - Hash-based content deduplication
   - Persistent cache across runs
   - Skip unchanged code

3. **Optimize batch processing**
   - Increase batch_size to 128
   - Profile memory usage

4. **Consider model alternatives**
   - Benchmark lighter models
   - Trade-off: speed vs. quality

## Monitoring Recommendations

Add telemetry for:
```python
# Track per-phase timing
metrics = {
    "parsing_ms": parsing_time * 1000,
    "embedding_ms": embedding_time * 1000,
    "db_write_ms": db_write_time * 1000,
    "throughput_chunks_per_sec": chunks / total_time,
}
```

Log to `.aurora/performance_metrics.json` for regression tracking.

## Conclusion

**Embedding generation is the critical bottleneck (88.4% of runtime)**. Optimization efforts should focus exclusively on this phase. GPU acceleration alone could reduce indexing time from 100s to 10s—a 10x improvement. Combined with embedding caching for incremental indexing, the system could achieve 20-50x speedups for typical workflows.

Parsing and database writes are already well-optimized and require no immediate attention.
