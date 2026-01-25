# Memory Search Performance - Quick Reference

**Last Updated**: 2025-01-26
**Aurora Version**: v0.11.x (Phase 2, Epic 1)

## TL;DR

**Current**: 20.4s total search time
**Target**: <5s cold, <500ms warm
**Quick Win**: Pre-tokenize chunks (25% improvement, low risk)

---

## Performance at a Glance

```
┌────────────────────────────────────────────────────────┐
│ MEMORY SEARCH PERFORMANCE BREAKDOWN                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Embedding Model Load    ███████████████████  55.0%   │
│  Query Embedding         ████              14.2%      │
│  BM25 Tokenization       ████              23.0% ⚠️    │
│  BM25 Scoring           ██                  5.8%      │
│  BM25 Index Load        █                   2.0%      │
│  Database Queries       ▏                   1.3%      │
│  Other                  ▏                   0.7%      │
│                                                        │
│  TOTAL: 20.4 seconds                                   │
└────────────────────────────────────────────────────────┘

⚠️  = Optimization target
```

---

## Top 3 Bottlenecks

### 🔴 #1: Embedding Model Loading (55%)

**Time**: 11.2s
**Status**: ✅ **Mitigated** (background loading)
**User Impact**: 6s user-perceived latency (not 20s)

### 🔴 #2: BM25 Tokenization (23%)

**Time**: 4.7s
**Status**: ⚠️ **FIX AVAILABLE** (pre-tokenization)
**Impact**: 25% total speedup (20s → 15s)

### 🔴 #3: Query Embedding (14.2%)

**Time**: 2.9s
**Status**: ✅ **Partially optimized** (60% cache hit rate)
**Opportunity**: Improve hit rate to 80% (query normalization)

---

## Quick Commands

### Run Profiler

```bash
# Basic profile
python scripts/profile_mem_search.py "your query"

# Detailed mode
python scripts/profile_mem_search.py "your query" --detailed

# cProfile analysis
python scripts/profile_mem_search.py "your query" --cprofile

# Custom database
python scripts/profile_mem_search.py "your query" --db-path /path/to/memory.db
```

### Measure Real-World Performance

```bash
# Time actual search command
time aur mem search "query" --limit 10

# With background model loading (normal usage)
aur mem search "query"  # ~6s user-perceived latency
```

### Check Performance Baselines

```bash
# Run performance tests
pytest tests/performance/test_mem_search_performance.py -v

# Run SOAR startup benchmarks
make benchmark-soar

# Check regression guards
pytest tests/performance/test_soar_startup_performance.py::TestRegressionGuards -v
```

---

## Component Performance

| Component | Time | % | Status | Notes |
|-----------|------|---|--------|-------|
| Embedding model load | 11.2s | 55% | ✅ | Background loading |
| Query embedding | 2.9s | 14% | ⚠️ | 60% cache hit |
| **BM25 tokenization** | **4.7s** | **23%** | ❌ | **FIX AVAILABLE** |
| BM25 build index | 703ms | 3.5% | ⚠️ | Minor |
| BM25 score chunks | 468ms | 2.3% | ⚠️ | Minor |
| BM25 index load | 405ms | 2% | ⚠️ | Could be <100ms |
| Database queries | 263ms | 1.3% | ✅ | Fast, not bottleneck |
| Imports | 280ms | 1.4% | ✅ | Within target |

---

## Optimization Priorities

### P0: Completed ✅

- [x] Lazy embedding imports
- [x] Connection pooling
- [x] Background model loading
- [x] Query embedding cache
- [x] HybridRetriever cache
- [x] ActivationEngine cache

### P1: Quick Wins 🔶

- [ ] **Pre-tokenize chunks** (25% improvement, low risk)
- [ ] BM25 index compression (2x faster load)
- [ ] Query normalization (cache hit 60% → 80%)

### P2: Incremental Gains 🔶

- [ ] Model quantization (10-20% faster inference)
- [ ] Parallel BM25 scoring (2-4x faster)
- [ ] Semantic query cache (fuzzy matching)

### P3: Future Enhancements 🔵

- [ ] Columnar BM25 storage
- [ ] GPU acceleration
- [ ] Speculative model preload

---

## Key Insights

### What's Working ✅

1. **Database is NOT a bottleneck** (1.3% of time)
2. **Caching is effective** (30-50% speedup)
3. **Background loading works** (6s vs 20s user-perceived latency)
4. **Import time is fast** (<300ms)

### What Needs Work ❌

1. **BM25 tokenization dominates** (4.7s, 52K function calls)
2. **Cold search 2x over target** (10-12s vs <5s)
3. **Warm search 4-6x over target** (2-3s vs <500ms)

### Biggest Opportunity 🎯

**Pre-tokenize chunks during indexing**:
- Eliminates 4.7s of search-time tokenization
- 25% total speedup (20s → 15s)
- Low risk (backward compatible)
- Medium effort (1-2 days)

---

## Performance Targets

| Metric | Current | Target | Gap | Status |
|--------|---------|--------|-----|--------|
| **Cold search** | 10-12s | <5s | 2x | ⚠️ Over |
| **Warm search** | 2-3s | <500ms | 4-6x | ⚠️ Over |
| **User-perceived** | 6s | <6s | - | ✅ Met |
| Import time | 280ms | <2s | - | ✅ Met |
| Config load | 0.7ms | <500ms | - | ✅ Met |
| Store init | 3ms | <100ms | - | ✅ Met |
| DB query | 120-144ms | <200ms | - | ✅ Met |

**Note**: Cold search target (<5s) is difficult to meet without eliminating embedding model load entirely. Background loading achieves **user-perceived** latency <6s, which is acceptable.

---

## Real-World Performance

### Cold Search (Background Loading)

```bash
$ time aur mem search "authentication" --limit 5

⏳ Loading embedding model in background...
⚡ Fast mode (BM25+activation)

Found 5 results for 'authentication'
[... results ...]

real    0m6.394s
user    0m5.780s
sys     0m1.240s
```

**Breakdown** (estimated):
- Imports + config: ~280ms (4.4%)
- BM25 index load: ~400ms (6.3%)
- Database query: ~120ms (1.9%)
- BM25 scoring: ~1.2s (18.8%)
- Result formatting: ~100ms (1.6%)
- Background model load: ~4.3s (67%, parallel)

**User-perceived latency**: ~2.3s (time to first result)

### Warm Search (Model Cached)

**Time**: 2-3s
**Breakdown**:
- BM25 scoring: 1.2s (40-60%)
- Query embedding: 0.3s (10-15%, cache hit)
- Database: 0.3s (10-15%)
- Other: 0.2-1.2s (25-35%)

---

## cProfile Top Functions

```
Function                         Calls     Cumtime   % Time
─────────────────────────────────────────────────────────────
hybrid_retriever.retrieve()      1         5.150s    98%
bm25_scorer.score()              598       4.867s    93%
bm25_scorer.tokenize()           52,599    4.705s    90%  ⚠️
_stage1_bm25_filter()            1         3.099s    59%
re.findall()                     211,247   1.326s    25%
re.split()                       52,599    0.698s    13%
```

**Critical Finding**: `tokenize()` called **52,599 times** for 598 chunks (88x multiplier).

**Why**: Each chunk tokenizes multiple fields separately:
- chunk.name
- chunk.signature
- chunk.docstring
- chunk.content (if available)

**Fix**: Pre-tokenize once during indexing, store tokens in database.

---

## Monitoring

### Check Current Performance

```bash
# Run profiler
python scripts/profile_mem_search.py "test query" --detailed

# Compare against baseline
diff baseline_pre_optimization.txt baseline_post_optimization.txt

# Check regression guards
pytest tests/performance/test_soar_startup_performance.py::TestRegressionGuards -v
```

### Check Cache Status

```bash
# Check query cache hit rate (requires instrumentation)
aur mem search "query" --debug | grep "cache hit rate"

# Check retriever cache status
aur mem status --cache-stats
```

### Regression Guards

```python
# Performance regression guards (CI)
MAX_IMPORT_TIME = 2.0s           # ✅ 280ms actual
MAX_CONFIG_TIME = 0.5s           # ✅ 0.7ms actual
MAX_STORE_INIT_TIME = 0.1s       # ✅ 3ms actual
MAX_TOTAL_STARTUP_TIME = 3.0s    # ✅ <300ms actual

# NEW: Add guard for BM25 tokenization (after pre-tokenization)
MAX_BM25_TOKENIZATION_TIME = 0.5s  # Target after optimization
```

---

## References

- **Full Profile**: `docs/analysis/MEMORY_SEARCH_PERFORMANCE_PROFILE.md`
- **Optimization Plan**: `docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md`
- **Profiling Script**: `scripts/profile_mem_search.py`
- **Performance Tests**: `tests/performance/test_mem_search_performance.py`
- **Epic 1 (Caching)**: `.aurora/plans/completed/epic-1-caching/prd.md`
- **SOAR Architecture**: `docs/reference/SOAR_ARCHITECTURE.md`

---

## Quick Decision Tree

```
Need to optimize memory search?
│
├─ Is database slow (>200ms)?
│  └─ NO ✅ (1.3% of time, not bottleneck)
│
├─ Is BM25 tokenization slow (>1s)?
│  └─ YES ❌ (4.7s, 23% of time)
│     └─ ACTION: Implement pre-tokenization (P1)
│
├─ Is embedding model load slow (>10s)?
│  └─ YES ⚠️ (11.2s, 55% of time)
│     └─ STATUS: Mitigated with background loading (6s user-perceived)
│
├─ Is query embedding slow (>2s)?
│  └─ YES ⚠️ (2.9s, 14% of time)
│     └─ STATUS: 60% cache hit rate
│     └─ ACTION: Improve cache hit rate (query normalization)
│
└─ Is BM25 index load slow (>100ms)?
   └─ YES ⚠️ (405ms, 2% of time)
      └─ ACTION: Compress index (gzip, P1)
```

---

## Common Questions

**Q: Why is my search taking 20+ seconds?**
A: You're probably running the profiling script, which forces synchronous model loading. Normal usage takes ~6s with background loading.

**Q: Can we make cold search <5s?**
A: Difficult. Embedding model load (11.2s) dominates. Background loading achieves 6s user-perceived latency, which is close.

**Q: Why is BM25 tokenization so slow?**
A: Tokenization is called 52,599 times for 598 chunks (88x multiplier). Pre-tokenization eliminates this.

**Q: Is the database a bottleneck?**
A: No. Database queries take 263ms (1.3% of total). Not a bottleneck.

**Q: Should we optimize database further?**
A: No. Focus on BM25 tokenization (4.7s, 23%) and query embedding cache (2.9s, 14%).

**Q: What's the ROI of pre-tokenization?**
A: 25% total speedup (20s → 15s), low risk, medium effort (1-2 days). Best ROI optimization.
