# `aur mem search` Performance Optimization Program

## Executive Summary

Transform `aur mem search` from 15-19s cold/4-5s warm to <3s cold/<500ms warm through systematic caching and optimization. Three epics organized by risk profile and dependency chains, delivering incremental value across 3 sprints.

---

## Epic 1: Instance & Cache Infrastructure (Foundation)

**Goal**: Eliminate redundant initialization overhead and establish shared caching layer

**Total Impact**: 5-7s savings (30-40% improvement)
**Risk**: LOW (pure caching, no algorithmic changes)
**Sprint Duration**: 1 sprint (1 week)

### Sprint 1.1: Foundation Caching (Week 1)

**User Story**: "As a developer running repeated searches, I want the system to reuse initialized components so subsequent searches are fast without sacrificing accuracy."

#### Tasks

1. **Cache HybridRetriever instance** (200-500ms savings)
   - **Files**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
   - **Implementation**: Add module-level LRU cache (keyed by store.db_path + config hash)
   - **Success metric**: 0% → 60%+ cache hit rate, 200-500ms reduction per cached hit
   - **Test**: Run same query twice, second should be 200-500ms faster

2. **Cache ActivationEngine instance** (50-100ms savings)
   - **Files**: `packages/core/src/aurora_core/activation/engine.py`
   - **Implementation**: Add module-level singleton cache (keyed by store reference)
   - **Success metric**: 50-100ms reduction on repeat searches
   - **Test**: Measure initialization time before/after

3. **Verify and fix BM25 index persistence** (CRITICAL: 9.7s → 0s potential)
   - **Files**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (lines 847-874)
   - **Investigation**: Check if `_try_load_bm25_index()` is actually loading or silently failing
   - **Implementation**: Add logging, validate pickle format, ensure index_path resolution works
   - **Success metric**: BM25 index load time <100ms (vs 9.7s rebuild), log confirms "Loaded BM25 index"
   - **Test**: Run search, check logs for "Loaded BM25 index" vs "Building BM25 index from candidates"

4. **Shared QueryEmbeddingCache across retrievers** (100-200ms savings)
   - **Files**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (lines 122-230)
   - **Implementation**: Move `QueryEmbeddingCache` to module-level, share across all HybridRetriever instances
   - **Success metric**: 100-200ms embedding generation saved on repeat queries across different contexts
   - **Test**: Run same query in different SOAR phases, confirm cache hit

**Dependencies**: None (all independent optimizations)

**Deliverables**:
- Working instance caches with configurable TTL
- BM25 index persistence validated and fixed
- Shared embedding cache implementation
- Performance benchmark showing 30-40% improvement

**Validation**:
```bash
# Before sprint
make benchmark-soar  # Baseline: ~15-19s cold, ~4-5s warm

# After sprint
make benchmark-soar  # Target: ~10-12s cold, ~2-3s warm
aur mem search "test" --verbose  # Check logs for cache hits
```

---

## Epic 2: BM25 Tokenization & Import Optimization (Algorithmic)

**Goal**: Eliminate redundant tokenization and hot-loop imports

**Total Impact**: 2-4s savings (15-25% improvement)
**Risk**: MEDIUM (algorithmic change with test coverage required)
**Sprint Duration**: 1 sprint (1 week)

### Sprint 2.1: BM25 & Import Optimization (Week 2)

**User Story**: "As a system, I want to tokenize content once and use efficient imports so searches consume minimal CPU."

#### Tasks

1. **Fix double tokenization in BM25 scoring** (1-2s savings)
   - **Files**: `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py` (lines 243-290)
   - **Current problem**: 36,924 regex calls for 500 chunks (tokenizing query+doc repeatedly)
   - **Implementation**:
     - Cache tokenized query in `BM25Scorer.score()` method
     - Add `_tokenized_cache` dict keyed by content hash
     - Tokenize document once, reuse across multiple queries
   - **Success metric**: Regex calls reduced from 36,924 → <1,000 per search
   - **Test**: Profile `tokenize()` calls before/after, ensure scores unchanged

2. **Move cosine_similarity import out of loop** (50-100ms savings)
   - **Files**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (line 449)
   - **Current problem**: `from aurora_context_code.semantic.embedding_provider import cosine_similarity` inside `retrieve()` loop
   - **Implementation**: Move import to top of file
   - **Success metric**: 50-100ms reduction (eliminates repeated import overhead)
   - **Test**: Measure `retrieve()` timing before/after

3. **Add BM25 tokenization benchmarks** (validation)
   - **Files**: `tests/performance/test_bm25_tokenization.py` (new file)
   - **Implementation**: Benchmark tokenize() calls on 500 chunks, assert <100ms total
   - **Success metric**: Regression test catches future tokenization regressions
   - **Test**: `pytest tests/performance/test_bm25_tokenization.py -v`

**Dependencies**: Requires Epic 1 complete (BM25 index must be working to validate)

**Deliverables**:
- Tokenization cache implementation
- Import optimization
- Performance regression tests
- 15-25% additional improvement (cumulative 45-65% total)

**Validation**:
```bash
# Profile tokenization before/after
python -m cProfile -o profile.stats -m aurora_cli.main mem search "test"
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats('tokenize', 10)"

# Benchmark
make benchmark-soar  # Target: ~7-8s cold, ~1-2s warm
```

---

## Epic 3: Connection Pool & Embedding Cache (Infrastructure)

**Goal**: Fix connection leaks and optimize re-indexing performance

**Total Impact**: 1-2s savings on search, 75-85s on re-index (5-10% search improvement)
**Risk**: MEDIUM-HIGH (database internals, requires careful testing)
**Sprint Duration**: 1 sprint (1 week)

### Sprint 3.1: Database & Embedding Optimization (Week 3)

**User Story**: "As a system, I want to reuse database connections and cache embeddings by content hash so re-indexing is fast and searches don't leak resources."

#### Tasks

1. **Fix connection pool return bug** (100-200ms savings)
   - **Files**: `packages/core/src/aurora_core/store/sqlite.py`
   - **Current problem**: Connections never returned to pool, causing churn
   - **Implementation**:
     - Audit all `with self._get_connection()` blocks
     - Ensure connections returned via proper context manager
     - Add connection pool metrics (active/idle counts)
   - **Success metric**: Connection reuse rate >80%, pool size stable
   - **Test**: Run 100 searches, check connection pool stats

2. **Content-hash embedding cache** (re-index: 100s → 15-25s)
   - **Files**:
     - `packages/core/src/aurora_core/store/sqlite.py` (new table: `embedding_cache`)
     - `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py` (cache lookup)
   - **Implementation**:
     - Add `embedding_cache` table: `(content_hash TEXT PRIMARY KEY, embedding BLOB, created_at INTEGER)`
     - Before embedding, check cache with SHA256(content)
     - On re-index, reuse embeddings for unchanged chunks
   - **Success metric**: Re-index time reduced 75-85% (100s → 15-25s)
   - **Test**: Index 500 chunks, modify 10, re-index, confirm 490 cache hits

3. **Replace json with orjson** (50-100ms savings)
   - **Files**: All files using `import json`
   - **Implementation**:
     - Add `orjson` dependency to `pyproject.toml`
     - Replace `json.loads/dumps` with `orjson.loads/dumps`
     - Handle bytes return type from orjson
   - **Success metric**: 50-100ms reduction in JSON parsing overhead
   - **Test**: Benchmark JSON operations before/after

**Dependencies**: Requires Epic 1 complete (connection pool depends on stable caching layer)

**Deliverables**:
- Fixed connection pool with reuse metrics
- Content-hash embedding cache (SQLite table + lookup logic)
- orjson integration
- Re-indexing performance improvement 75-85%

**Validation**:
```bash
# Test connection pool
aur mem search "test" --verbose  # Check pool metrics in logs

# Test embedding cache
aur mem index .  # Index 500 chunks
aur mem index .  # Re-index, should be 75-85% faster

# Final benchmark
make benchmark-soar  # Target: <3s cold, <500ms warm
```

---

## Success Metrics Summary

### Performance Targets (Cumulative)

| Milestone | Cold Search | Warm Search | Re-Index (500 chunks) |
|-----------|-------------|-------------|-----------------------|
| Baseline | 15-19s | 4-5s | 100s |
| After Sprint 1 | 10-12s (30-40% ↓) | 2-3s (40-50% ↓) | 100s |
| After Sprint 2 | 7-8s (50-60% ↓) | 1-2s (60-80% ↓) | 100s |
| After Sprint 3 | <3s (80-85% ↓) | <500ms (85-90% ↓) | 15-25s (75-85% ↓) |

### Key Indicators

**Sprint 1 (Foundation)**:
- HybridRetriever cache hit rate: 0% → 60%+
- ActivationEngine cache hit rate: 0% → 80%+
- BM25 index load time: 9.7s → <100ms
- QueryEmbeddingCache hit rate: 0% → 40%+

**Sprint 2 (Algorithmic)**:
- BM25 tokenize() calls: 36,924 → <1,000 per search
- Import overhead: Eliminated from hot loop
- Tokenization time: 1-2s → <100ms

**Sprint 3 (Infrastructure)**:
- Connection pool reuse rate: 0% → 80%+
- Embedding cache hit rate on re-index: 0% → 98%
- JSON parsing time: Reduced 50-100ms

---

## Risk Mitigation

### Epic 1 (LOW RISK)
- **Mitigation**: Pure caching, no algorithmic changes. Easy to rollback.
- **Testing**: Benchmark before/after, compare search results for equivalence.

### Epic 2 (MEDIUM RISK)
- **Risk**: Tokenization changes could affect BM25 scores.
- **Mitigation**:
  - Add comprehensive regression tests comparing old vs new scores
  - Use frozen test corpus to validate score stability
  - Profile before/after to catch performance regressions

### Epic 3 (MEDIUM-HIGH RISK)
- **Risk**: Connection pool bug could cause deadlocks, embedding cache could serve stale data.
- **Mitigation**:
  - Feature flag for connection pool fix (rollback if issues)
  - Embedding cache includes content hash validation
  - Extensive integration tests with concurrent searches
  - Monitor connection pool metrics in production

---

## Dependencies & Sequencing

```
Epic 1 (Sprint 1)
    ├─ Task 1: Cache HybridRetriever (no deps)
    ├─ Task 2: Cache ActivationEngine (no deps)
    ├─ Task 3: Fix BM25 persistence (no deps)
    └─ Task 4: Shared QueryEmbeddingCache (no deps)
            ↓
Epic 2 (Sprint 2) [DEPENDS ON Epic 1 - needs working BM25 index]
    ├─ Task 1: Fix double tokenization
    ├─ Task 2: Move import out of loop
    └─ Task 3: Add tokenization benchmarks
            ↓
Epic 3 (Sprint 3) [DEPENDS ON Epic 1 - needs stable cache layer]
    ├─ Task 1: Fix connection pool
    ├─ Task 2: Content-hash embedding cache
    └─ Task 3: Replace json with orjson
```

---

## Recommended Approach

1. **Start with Epic 1 (Sprint 1)**: Lowest risk, highest value. Delivers 30-40% improvement immediately.
2. **Proceed to Epic 2 (Sprint 2)**: Medium risk, good value. Validates BM25 index from Epic 1.
3. **Finish with Epic 3 (Sprint 3)**: Highest risk, but Epic 1+2 already deliver 50-80% improvement. Epic 3 pushes to 80-90% and optimizes re-indexing.

This sequencing ensures:
- **Early wins**: 30-40% improvement in Week 1
- **Safe rollback**: Each epic is independently valuable
- **Risk isolation**: High-risk changes (connection pool, embedding cache) come last when foundation is solid

---

## Original Analysis Context

**SOAR Analysis Results:**
- Identified 9 optimization opportunities
- Performance profiling showed BM25 index persistence as critical bottleneck (51% of cold search time)
- Connection pool bug causing resource churn
- Double tokenization causing 36,924 regex calls per search

**Source:** SOAR wave-based execution analysis from `aur soar` query about improving search performance.

**Agent:** code-developer (agentId: a760715)
