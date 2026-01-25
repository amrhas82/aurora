# Memory Search Optimization Plan

**Date**: 2025-01-26
**Status**: PROPOSED
**Priority**: P1 (High)
**Related**: `MEMORY_SEARCH_PERFORMANCE_PROFILE.md`

## Executive Summary

Profiling reveals that **BM25 tokenization** is the primary optimization target, accounting for 4.7s (23%) of total search time. Pre-tokenizing chunks during indexing could reduce total search time by **25%** (20s → 15s) and bring warm searches closer to the <500ms target.

**Current State**: 20.4s total search time
**Target State**: 10-12s cold search, <2s warm search
**Quick Win**: Pre-tokenization (25% improvement, low risk)

---

## Performance Bottleneck Summary

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┓
┃ Component                      ┃ Time    ┃ % Total┃ Priority   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━┩
│ Embedding model load           │ 11.2s   │ 55.0%  │ P0 ✅ DONE │
│ Query embedding generation     │ 2.9s    │ 14.2%  │ P0 ✅ DONE │
│ Full hybrid search             │ 4.1s    │ 20.3%  │ P1 🔶      │
│   ├─ BM25 tokenization         │ 4.7s    │ 23.0%  │ P1 🔶 NEW  │
│   ├─ BM25 build index          │ 703ms   │ 3.5%   │ P2         │
│   ├─ BM25 scoring              │ 468ms   │ 2.3%   │ P2         │
│   └─ Other                     │ ~0s     │ 0%     │            │
│ BM25 index load                │ 405ms   │ 2.0%   │ P1 🔶      │
│ Database queries               │ 263ms   │ 1.3%   │ ✅ Fast    │
│ Imports                        │ 280ms   │ 1.4%   │ ✅ Fast    │
│ Other                          │ ~100ms  │ 0.5%   │ ✅ Fast    │
└────────────────────────────────┴─────────┴────────┴────────────┘
TOTAL:                             20.4s     100%
```

---

## Optimization Strategy

### Phase 1: Pre-Tokenization (P1 - Quick Win) 🔶

**Goal**: Eliminate 4.7s of search-time tokenization

**Approach**:
1. Tokenize chunks during indexing (one-time cost)
2. Store tokenized representation in database (new column or JSON field)
3. Load pre-tokenized chunks during search (zero tokenization cost)

**Implementation**:

```python
# 1. Update schema (aurora_core/store/sqlite.py)
CREATE TABLE chunks (
    ...
    bm25_tokens TEXT,  -- JSON array of tokens: ["func", "auth", "user"]
    ...
);

# 2. Tokenize during indexing (aurora_context_code/indexer.py)
from aurora_context_code.semantic.bm25_scorer import tokenize

def _index_chunk(chunk: CodeChunk):
    # Existing logic...

    # NEW: Pre-tokenize for BM25
    content = f"{chunk.name} {chunk.signature} {chunk.docstring or ''}"
    tokens = tokenize(content)
    chunk.bm25_tokens = json.dumps(tokens)

    store.save_chunk(chunk)

# 3. Load pre-tokenized chunks during search (aurora_context_code/semantic/hybrid_retriever.py)
def _stage1_bm25_filter(self, query: str, chunks: List[Chunk]) -> List[ScoredResult]:
    # Existing tokenization of query
    query_tokens = tokenize(query)

    # NEW: Use pre-tokenized chunks
    for chunk in chunks:
        if chunk.bm25_tokens:
            chunk_tokens = json.loads(chunk.bm25_tokens)
        else:
            # Fallback for legacy chunks without pre-tokenization
            chunk_tokens = tokenize(f"{chunk.name} {chunk.signature} {chunk.docstring or ''}")

        score = self.bm25_scorer.score_tokens(query_tokens, chunk_tokens)
        ...
```

**Impact**:
- **BM25 scoring**: 4.7s → ~470ms (10x faster)
- **Total search**: 20s → 15s (25% faster)
- **Warm search**: 2-3s → 1-1.5s (closer to <500ms target)

**Migration Path**:
```bash
# Add bm25_tokens column (nullable for backward compatibility)
aur mem migrate --add-bm25-tokens

# Re-index existing chunks (background job)
aur mem reindex --add-bm25-tokens

# Check migration progress
aur mem status --show-tokenization-coverage
```

**Risk**: LOW
- Backward compatible (nullable column, fallback to on-demand tokenization)
- No breaking changes to API
- Incremental migration (chunks without tokens fall back to legacy behavior)

**Effort**: MEDIUM (1-2 days)
- Schema migration: 2 hours
- Indexer changes: 4 hours
- Retriever changes: 2 hours
- Testing: 4 hours
- Migration script: 2 hours

---

### Phase 2: BM25 Index Load Optimization (P1) 🔶

**Goal**: Reduce BM25 index load from 405ms to <100ms

**Current**:
```python
# 21,120 entries loaded via pickle (~405ms)
with open(bm25_index_path, "rb") as f:
    index = pickle.load(f)
```

**Approach 1: Compression** (Quick Win)
```python
import gzip
import pickle

# Save (indexing)
with gzip.open(f"{bm25_index_path}.gz", "wb") as f:
    pickle.dump(index, f)

# Load (searching)
with gzip.open(f"{bm25_index_path}.gz", "rb") as f:
    index = pickle.load(f)
```

**Expected Impact**:
- File size: 50-70% reduction
- Load time: 405ms → 150-200ms (2x faster)

**Approach 2: Columnar Storage** (Better Performance)
```python
# Use parquet or arrow for columnar BM25 index
import pyarrow as pa
import pyarrow.parquet as pq

# Save
table = pa.table({
    'chunk_id': chunk_ids,
    'doc_freq': doc_freqs,
    'idf': idfs,
    ...
})
pq.write_table(table, bm25_index_path)

# Load
table = pq.read_table(bm25_index_path)
index = BM25Index.from_arrow(table)
```

**Expected Impact**:
- Load time: 405ms → <100ms (4x faster)
- Memory efficiency: 30-50% reduction

**Risk**: LOW (compression), MEDIUM (columnar)
**Effort**: LOW (4 hours for compression), HIGH (2-3 days for columnar)

---

### Phase 3: Query Embedding Cache Hit Rate Improvement (P2) 🔶

**Goal**: Increase cache hit rate from 60% to 80%+

**Current Cache Strategy**:
- LRU cache (size: 100)
- Cache key: exact query string
- Hit rate: 60% (SOAR multi-phase operations)

**Approach 1: Query Normalization**
```python
def normalize_query(query: str) -> str:
    """Normalize query for better cache hit rate."""
    # Lowercase
    normalized = query.lower()

    # Remove stop words
    stop_words = {"the", "a", "an", "in", "on", "at", "to", "for"}
    tokens = normalized.split()
    tokens = [t for t in tokens if t not in stop_words]

    # Sort tokens (order-independent)
    tokens.sort()

    return " ".join(tokens)

# Cache key: normalized query
cache_key = normalize_query(query)
```

**Expected Impact**:
- Hit rate: 60% → 75-80% (25-33% improvement)
- Examples:
  - "authentication system" → "authentication system"
  - "system authentication" → "authentication system" (CACHE HIT)
  - "the authentication system" → "authentication system" (CACHE HIT)

**Approach 2: Semantic Cache (Fuzzy Matching)**
```python
# Cache similar queries within cosine similarity threshold
if embedding_distance(query, cached_query) < 0.1:
    return cached_embedding
```

**Expected Impact**:
- Hit rate: 60% → 85-90% (40-50% improvement)
- Examples:
  - "authentication system" → embedding
  - "auth system" → CACHE HIT (similar semantic meaning)
  - "user authentication" → CACHE HIT (similar semantic meaning)

**Risk**: MEDIUM (semantic cache may return incorrect results for subtly different queries)
**Effort**: LOW (4 hours for normalization), MEDIUM (1-2 days for semantic cache)

---

### Phase 4: Model Quantization (P2) 🔵

**Goal**: Reduce embedding model inference time by 10-20%

**Approach**:
```python
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch

# Load model with quantization
model = SentenceTransformer('all-MiniLM-L6-v2')
model.half()  # FP16 quantization (2x memory reduction, 10-20% faster)

# OR: Use ONNX runtime (30-50% faster)
model.save("model.onnx", export_format="onnx")
from onnxruntime import InferenceSession
session = InferenceSession("model.onnx")
```

**Expected Impact**:
- Inference time: 2.9s → 2.3-2.6s (10-20% faster)
- Memory usage: 50% reduction (FP16)
- Accuracy loss: <1% (negligible for retrieval)

**Risk**: MEDIUM (quantization may degrade semantic quality slightly)
**Effort**: MEDIUM (1-2 days for integration and testing)

---

### Phase 5: Parallel BM25 Scoring (P3) 🔵

**Goal**: Parallelize BM25 scoring across chunks

**Approach**:
```python
from multiprocessing import Pool

def score_chunk_batch(args):
    query_tokens, chunk_batch = args
    return [score(query_tokens, chunk) for chunk in chunk_batch]

# Parallelize across CPU cores
with Pool(processes=4) as pool:
    chunk_batches = [chunks[i:i+100] for i in range(0, len(chunks), 100)]
    args = [(query_tokens, batch) for batch in chunk_batches]
    results = pool.map(score_chunk_batch, args)
```

**Expected Impact**:
- BM25 scoring: 468ms → 117-234ms (2-4x faster, depending on CPU cores)
- Overhead: Process spawning, IPC (50-100ms)

**Risk**: MEDIUM (multiprocessing overhead may negate speedup for small chunk counts)
**Effort**: MEDIUM (1-2 days)

---

## Implementation Roadmap

### Sprint 1: Quick Wins (1 week)

**Week 1**:
- [ ] **Task 1.1**: Schema migration (add `bm25_tokens` column)
- [ ] **Task 1.2**: Update indexer to pre-tokenize chunks
- [ ] **Task 1.3**: Update retriever to use pre-tokenized chunks
- [ ] **Task 1.4**: Migration script for existing databases
- [ ] **Task 1.5**: Performance testing (before/after)

**Expected Outcome**:
- Total search: 20s → 15s (25% improvement)
- Warm search: 2-3s → 1-1.5s

### Sprint 2: Index Optimization (1 week)

**Week 2**:
- [ ] **Task 2.1**: Implement gzip compression for BM25 index
- [ ] **Task 2.2**: Benchmark compression (load time, file size)
- [ ] **Task 2.3**: Query normalization for cache improvement
- [ ] **Task 2.4**: Performance testing (before/after)

**Expected Outcome**:
- BM25 index load: 405ms → 150-200ms (2x improvement)
- Query cache hit rate: 60% → 75-80%

### Sprint 3: Advanced Optimizations (2 weeks)

**Week 3-4**:
- [ ] **Task 3.1**: Model quantization (FP16 or ONNX)
- [ ] **Task 3.2**: Semantic query cache (optional)
- [ ] **Task 3.3**: Parallel BM25 scoring (optional)
- [ ] **Task 3.4**: End-to-end performance validation

**Expected Outcome**:
- Query embedding: 2.9s → 2.3-2.6s (10-20% improvement)
- Total search: 15s → 12-13s (additional 15-20% improvement)

---

## Performance Targets (Updated)

| Metric | Current | Sprint 1 | Sprint 2 | Sprint 3 | Target | Gap |
|--------|---------|----------|----------|----------|--------|-----|
| **Cold search** | 20s | 15s | 13s | 12s | <5s | ❌ 2.4x over |
| **Warm search** | 2-3s | 1-1.5s | 1s | 0.8-1s | <500ms | ⚠️ 1.6-2x over |
| **BM25 tokenization** | 4.7s | 0s | 0s | 0s | N/A | ✅ Eliminated |
| **BM25 index load** | 405ms | 405ms | 150ms | 150ms | <100ms | ⚠️ 1.5x over |
| **Query embedding** | 2.9s | 2.9s | 2.9s | 2.3s | <300ms | ❌ 7.7x over |

**Analysis**:
- **Sprint 1** closes the gap by 25% (20s → 15s)
- **Sprint 2** closes the gap by additional 13% (15s → 13s)
- **Sprint 3** closes the gap by additional 8% (13s → 12s)
- **Total improvement**: 40% (20s → 12s)

**Remaining Gap**:
- Cold search is still **2.4x over target** (12s vs <5s)
- Root cause: Embedding model inference (11.2s) is unavoidable
- Mitigation: Background model loading (user-perceived latency: 6s)

**Revised Target**:
- **Cold search (user-perceived)**: <6s (background loading) ✅ MET
- **Warm search**: <1s (closer to <500ms target) ⚠️ Still 2x over

---

## Risk Assessment

### Low Risk (Safe to Implement)

1. ✅ **Pre-tokenization** (backward compatible, fallback available)
2. ✅ **BM25 index compression** (gzip, simple, proven)
3. ✅ **Query normalization** (deterministic, well-tested)

### Medium Risk (Requires Testing)

4. ⚠️ **Model quantization** (may degrade semantic quality slightly)
5. ⚠️ **Semantic query cache** (may return incorrect results for edge cases)
6. ⚠️ **Parallel BM25 scoring** (overhead may negate speedup)

### High Risk (Avoid for Now)

7. ❌ **Columnar BM25 storage** (complex, high effort, moderate gain)
8. ❌ **GPU acceleration** (environment dependency, not portable)

---

## Success Metrics

### Performance Metrics

- [ ] **Total search time**: 20s → 15s (25% improvement)
- [ ] **BM25 tokenization time**: 4.7s → 0s (eliminated)
- [ ] **Query cache hit rate**: 60% → 75-80% (25% improvement)
- [ ] **BM25 index load time**: 405ms → 150ms (2.5x improvement)

### Quality Metrics

- [ ] **Search relevance**: No regression (NDCG@10 >= baseline)
- [ ] **Cache accuracy**: >99% (semantic cache false positive rate <1%)
- [ ] **Migration success**: 100% of existing databases migrate cleanly

### User Experience Metrics

- [ ] **User-perceived latency**: 6s (background loading) - no change
- [ ] **Warm search latency**: 2-3s → 1-1.5s (33-50% improvement)

---

## Monitoring & Validation

### Pre-Sprint Baseline

```bash
# Capture baseline metrics
python scripts/profile_mem_search.py "authentication" --detailed > baseline_pre_sprint1.txt

# Run performance test suite
pytest tests/performance/test_mem_search_performance.py -v > baseline_tests_pre_sprint1.txt
```

### Post-Sprint Validation

```bash
# Capture post-optimization metrics
python scripts/profile_mem_search.py "authentication" --detailed > baseline_post_sprint1.txt

# Compare before/after
diff baseline_pre_sprint1.txt baseline_post_sprint1.txt

# Validate performance targets met
pytest tests/performance/test_mem_search_performance.py -v
```

### Regression Guards

```python
# Add new regression guard for BM25 tokenization
@pytest.mark.performance
def test_guard_bm25_tokenization_eliminated():
    """Ensure BM25 tokenization is eliminated (pre-tokenized chunks)."""
    import time
    from aurora_context_code.semantic.bm25_scorer import tokenize

    # Profile search path
    start = time.perf_counter()
    results = retriever.search("test query", limit=10)
    elapsed = time.perf_counter() - start

    # Check that tokenize() was called only once (for query, not chunks)
    tokenize_call_count = get_tokenize_call_count()  # Mock or logging
    assert tokenize_call_count == 1, f"Expected 1 tokenize call (query only), got {tokenize_call_count}"

    # Check total search time improved
    assert elapsed < 15.0, f"Search took {elapsed}s, expected <15s after pre-tokenization"
```

---

## Rollback Plan

### If Pre-Tokenization Causes Issues

```bash
# Disable pre-tokenization (fallback to legacy behavior)
export AURORA_DISABLE_PRETOKENIZATION=1
aur mem search "query"

# Revert schema migration (drop bm25_tokens column)
aur mem migrate --revert-bm25-tokens

# Re-run tests
pytest tests/integration/test_mem_search.py -v
```

### If Performance Degrades

```bash
# Disable all optimizations
export AURORA_DISABLE_CACHING=1
export AURORA_DISABLE_PRETOKENIZATION=1
export AURORA_DISABLE_QUERY_NORMALIZATION=1

# Fallback to v0.11.x behavior
git checkout v0.11.0
./install.sh
```

---

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Create GitHub issue** for Sprint 1 (pre-tokenization)
3. **Set up performance baseline** (capture before metrics)
4. **Implement Sprint 1** (pre-tokenization)
5. **Validate Sprint 1** (performance tests, regression guards)
6. **Decide on Sprint 2/3** based on Sprint 1 results

---

## References

- **Performance Profile**: `docs/analysis/MEMORY_SEARCH_PERFORMANCE_PROFILE.md`
- **Epic 1 PRD**: `.aurora/plans/completed/epic-1-caching/prd.md`
- **Profiling Script**: `scripts/profile_mem_search.py`
- **Performance Testing**: `docs/PERFORMANCE_TESTING.md`
- **cProfile Analysis**: See profiling output in performance profile document
