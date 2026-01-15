# Memory Indexing Performance Profile Report

**Date:** 2026-01-13
**Test Configuration:** 10 Python files, 95 chunks, 840 code elements
**Total Duration:** 102.4 seconds

## Executive Summary

Memory indexing performance is dominated by embedding generation (85.9% of time). The current implementation processes at 0.9 files/sec with a throughput of 9.5 embeddings/sec, indicating significant optimization opportunities.

### Key Findings

| Phase | Duration (ms) | % of Total | Throughput | Status |
|-------|--------------|------------|------------|--------|
| Embedding generation | 87,973 | 85.9% | 9.5 ops/sec | **Critical bottleneck** |
| Git blame extraction | 7,947 | 7.8% | 12.0 ops/sec | Acceptable |
| Parsing files | 4,212 | 4.1% | 22.6 ops/sec | Minor concern |
| Database writes | 2,114 | 2.1% | 397.4 ops/sec | Excellent |
| File discovery | 133 | 0.1% | 7.5 ops/sec | Negligible impact |

## Detailed Analysis

### 1. Embedding Generation (Critical)

**Impact:** 85.9% of total indexing time
**Current Performance:** 9.5 chunks/sec
**Location:** `packages/cli/src/aurora_cli/memory_manager.py:310-311`

**Bottleneck Details:**
- Average time per embedding: 104.7ms (3258ms per batch of 32)
- Batch processing is implemented but throughput is still low
- Current batch size: 32 chunks
- Using CPU-based sentence-transformers model

**Root Causes:**
1. CPU-only inference (no GPU acceleration)
2. Model size vs speed tradeoff (potentially using larger model)
3. Sequential batch processing
4. Synchronous blocking during embedding generation

**Evidence from Code:**
```python
# packages/cli/src/aurora_cli/memory_manager.py:311
embeddings = self.embedding_provider.embed_batch(texts, batch_size=batch_size)
```

This single line dominates execution time. The `embed_batch` call blocks the entire indexing pipeline.

### 2. Git Blame Extraction (Moderate)

**Impact:** 7.8% of total indexing time
**Current Performance:** 12.0 files/sec
**Location:** `packages/context-code/src/aurora_context_code/git.py`

**Bottleneck Details:**
- File-level blame caching already implemented (good)
- Still takes 83.7ms average per file
- Proportionally high for codebases with extensive git history
- 26 git processes spawned per file on average

**Optimization Opportunities:**
1. Disable git signals during initial indexing (add as CLI flag)
2. Async/parallel git blame extraction
3. Cache git blame results to disk for incremental updates
4. Use libgit2 bindings instead of subprocess calls

### 3. File Parsing (Minor)

**Impact:** 4.1% of total indexing time
**Current Performance:** 22.6 files/sec
**Location:** `packages/context-code/src/aurora_context_code/languages/python.py`

**Bottleneck Details:**
- Average 44.3ms per file
- Tree-sitter parsing is generally fast
- Sequential processing (no parallelization)
- Some overhead from AST traversal

**Optimization Opportunities:**
1. Parallel file parsing with ProcessPoolExecutor
2. Cache parse results for unchanged files
3. Optimize tree-sitter queries
4. Skip parsing for non-modified files (incremental indexing)

### 4. Database Writes (Excellent)

**Impact:** 2.1% of total indexing time
**Current Performance:** 397.4 chunks/sec
**Location:** `packages/core/src/aurora_core/store/sqlite.py`

**Current State:**
- Excellent throughput (397 ops/sec)
- Batch writes already implemented
- Retry logic with exponential backoff
- No significant bottleneck

**Notes:**
- Database writes are well-optimized
- SQLite performance is acceptable
- File-level batching prevents lock contention

### 5. File Discovery (Negligible)

**Impact:** 0.1% of total indexing time
**Current Performance:** 7.5 ops/sec (misleading - single operation)
**Location:** `packages/cli/src/aurora_cli/memory_manager.py:664-693`

**Current State:**
- Single-threaded recursive directory walk
- Pattern matching with glob
- Ignore pattern filtering
- Not a bottleneck (only runs once)

## Performance Comparison: Expected vs Actual

| Metric | Expected | Actual | Gap |
|--------|----------|--------|-----|
| Overall throughput | 10-50 files/sec | 0.9 files/sec | **49x slower** |
| Embedding throughput | 50-200 chunks/sec | 9.5 chunks/sec | **21x slower** |
| Parsing throughput | 100-500 files/sec | 22.6 files/sec | **22x slower** |
| DB write throughput | 100-1000 chunks/sec | 397.4 chunks/sec | Within range |

## Optimization Recommendations

### Priority 1: Embedding Generation (High Impact)

**Estimated Improvement:** 10-20x faster (90-180 chunks/sec)

1. **GPU Acceleration** (Highest ROI)
   ```python
   # Use CUDA-enabled sentence-transformers
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
   ```
   - Expected speedup: 10-15x on consumer GPU
   - Requires: CUDA-compatible GPU, updated dependencies

2. **Larger Batch Sizes**
   ```python
   # Increase from 32 to 128 or 256
   embeddings = self.embedding_provider.embed_batch(texts, batch_size=128)
   ```
   - Expected speedup: 2-3x
   - Requires: More GPU memory or batched CPU processing

3. **Faster Embedding Models**
   - Switch from `all-mpnet-base-v2` (768 dims) to `all-MiniLM-L6-v2` (384 dims)
   - Expected speedup: 2-3x with minimal quality loss
   - 50% reduction in storage and memory

4. **Async Embedding Pipeline**
   ```python
   # Use asyncio or threading for non-blocking embedding
   async def embed_async(texts):
       loop = asyncio.get_event_loop()
       return await loop.run_in_executor(None, embed_batch, texts)
   ```
   - Allows overlap with parsing/git operations
   - Expected speedup: 1.5-2x

### Priority 2: Parallel Processing (Medium Impact)

**Estimated Improvement:** 2-4x faster overall

1. **Parallel File Parsing**
   ```python
   from concurrent.futures import ProcessPoolExecutor

   with ProcessPoolExecutor(max_workers=4) as executor:
       futures = [executor.submit(parse_file, f) for f in files]
       results = [f.result() for f in futures]
   ```
   - Expected speedup: 3-4x (CPU-bound operation)
   - Requires: Multi-core CPU, careful state management

2. **Async Git Blame Extraction**
   ```python
   async def extract_git_signals_parallel(files):
       tasks = [extract_git_signals(f) for f in files]
       return await asyncio.gather(*tasks)
   ```
   - Expected speedup: 2-3x
   - Requires: Async subprocess handling

### Priority 3: Incremental Indexing (Low Effort, High Value)

**Estimated Improvement:** Skip 80-95% of work on re-index

1. **Track File Modifications**
   ```python
   # Store file hash and mtime in metadata table
   CREATE TABLE file_metadata (
       file_path TEXT PRIMARY KEY,
       content_hash TEXT,
       last_indexed TIMESTAMP
   )
   ```

2. **Skip Unchanged Files**
   ```python
   current_hash = hash_file(file_path)
   if db.get_file_hash(file_path) == current_hash:
       logger.debug(f"Skipping unchanged file: {file_path}")
       continue
   ```

### Priority 4: Configuration Flags (Quick Wins)

1. **Add CLI flags for selective indexing**
   ```bash
   aur mem index . --skip-git-signals      # 8% faster
   aur mem index . --fast-mode             # Skip git + use fast embeddings
   aur mem index . --incremental           # Only changed files
   ```

2. **Database Optimization Pragmas**
   ```python
   # During indexing only
   PRAGMA synchronous = OFF;
   PRAGMA journal_mode = MEMORY;
   PRAGMA cache_size = 10000;
   ```
   - Expected speedup: 5-10% for writes

## Implementation Priority Matrix

| Optimization | Effort | Impact | ROI | Priority |
|--------------|--------|--------|-----|----------|
| GPU acceleration | Medium | Very High | **Highest** | P0 |
| Larger batch sizes | Low | High | **Very High** | P0 |
| Faster embedding model | Low | High | **Very High** | P0 |
| Incremental indexing | Medium | Very High | **High** | P1 |
| Parallel file parsing | Medium | Medium | Medium | P2 |
| Async git extraction | Medium | Low | Low | P3 |
| CLI optimization flags | Low | Low | Medium | P2 |

## Benchmarking Strategy

To validate optimizations, use this benchmarking framework:

```python
# tests/performance/test_indexing_benchmarks.py
import pytest

@pytest.mark.benchmark
def test_indexing_throughput(benchmark, test_codebase):
    """Benchmark indexing throughput (target: >10 files/sec)."""
    manager = MemoryManager()
    stats = benchmark(manager.index_path, test_codebase)

    throughput = stats.files_indexed / stats.duration_seconds
    assert throughput > 10, f"Throughput too low: {throughput:.1f} files/sec"

@pytest.mark.benchmark
def test_embedding_throughput(benchmark, test_chunks):
    """Benchmark embedding generation (target: >100 chunks/sec)."""
    provider = EmbeddingProvider()
    texts = [chunk.content for chunk in test_chunks]

    duration = benchmark(provider.embed_batch, texts, batch_size=128)
    throughput = len(texts) / duration
    assert throughput > 100, f"Embedding too slow: {throughput:.1f} chunks/sec"
```

## Monitoring Recommendations

Add telemetry to track performance improvements:

```python
# packages/cli/src/aurora_cli/memory_manager.py
@dataclass
class IndexingMetrics:
    """Track indexing performance metrics."""

    files_per_second: float
    chunks_per_second: float
    embeddings_per_second: float
    parsing_time_ms: float
    embedding_time_ms: float
    git_time_ms: float
    db_write_time_ms: float

    def to_json(self) -> str:
        """Export metrics for analysis."""
        return json.dumps(asdict(self))
```

Store metrics in `.aurora/metrics/indexing_TIMESTAMP.json` for trend analysis.

## Conclusion

Memory indexing performance is currently bottlenecked by embedding generation (86% of time). The following optimizations will provide the greatest impact:

1. **GPU acceleration** for embeddings → 10-15x speedup
2. **Larger batch sizes** → 2-3x speedup
3. **Faster embedding model** → 2-3x speedup
4. **Incremental indexing** → Skip 80-95% of work

Combined, these optimizations can achieve **50-100x overall speedup**, reducing indexing time from 102s to 1-2s for the test codebase.

Current bottleneck distribution:
- **Embedding: 86%** ← Primary focus
- Git blame: 8%
- Parsing: 4%
- Database: 2%

After optimization, target distribution:
- Embedding: 40-50%
- Parsing: 30-40%
- Git blame: 10-20%
- Database: 5-10%

## Appendix: Profiling Methodology

**Test Environment:**
- Hardware: [CPU/GPU specs from run]
- Python version: 3.10+
- Packages: aurora-cli v0.7.0
- Test corpus: 10 Python files, 840 code elements

**Profiling Tools:**
- cProfile for function-level timing
- Custom phase tracking for pipeline analysis
- SQLite query logging (disabled for baseline)

**Reproducibility:**
```bash
python3 profile_memory_indexing.py \
    --path packages/cli/src/aurora_cli \
    --num-files 10 \
    --output memory_profile_report.json
```

See `memory_profile_report.json` for raw profiling data.
