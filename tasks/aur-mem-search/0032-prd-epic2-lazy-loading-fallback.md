# PRD: Epic 2 - Memory Search Performance Optimizations (Lazy Loading + Dual-Hybrid Fallback)

**Date**: 2026-01-25
**Status**: APPROVED
**Priority**: P1 (High)
**Epic**: Epic 2 - Memory Search Performance Phase 2
**Related**: Epic 1 (Foundation Caching) - Completed

---

## 1. Overview

### 1.1 Problem Statement

Despite Epic 1 caching improvements (15-19s → 10-12s cold search), Aurora's memory search still falls short of performance targets (<3s cold, <500ms warm). Two specific bottlenecks remain:

1. **HybridRetriever creation overhead (100-200ms)**: BM25 index loading in `__init__()` (lines 532-533) slows retriever instantiation even for non-search operations like `aur goals` and `aur soar` that create retrievers but never call `retrieve()`.

2. **Degraded search quality in fallback mode (~60%)**: When embedding model fails to load, `_fallback_to_activation_only()` (lines 930-956) returns activation scores only (BM25=0, semantic=0), reducing search quality to ~60% compared to tri-hybrid's 95%+. Users experience poor results when embeddings are unavailable.

**User Impact**:
- Developers experience 100-200ms delay in operations that don't need BM25 (goals evaluation, complexity assessment)
- Users with embedding model issues get significantly degraded search quality (~60% vs 95%+)
- No user-facing indication that search is operating in degraded mode

### 1.2 Solution Summary

This PRD proposes two low-risk optimizations to address these bottlenecks:

**Feature 1: Lazy BM25 Index Loading**
- Defer `_try_load_bm25_index()` from `__init__()` to first `retrieve()` call
- Proven pattern from `aur goals` optimization (saved 200ms)
- Impact: 100-200ms faster retriever creation for non-search operations

**Feature 2: BM25+Activation Dual-Hybrid Fallback**
- Replace `_fallback_to_activation_only()` with `_fallback_to_dual_hybrid()`
- Use BM25+Activation (no embeddings) when embedding model fails
- Impact: ~85% search quality (vs 60% activation-only) in degraded mode, <1s search time

**Combined Impact**:
- Cold search: 10-12s → 9-11s (100-200ms from lazy loading)
- Fallback search quality: 60% → 85% (25 percentage point improvement)
- Non-search operations: 100-200ms faster (goals, soar assessment phases)

### 1.3 Goals

1. **Performance**: Reduce HybridRetriever creation time by 100-200ms for non-search operations
2. **Quality**: Improve fallback search quality from ~60% to ~85% when embeddings unavailable
3. **Speed**: Maintain <1s search time in fallback mode (BM25+Activation)
4. **Reliability**: No regressions in normal tri-hybrid search path
5. **Testing**: Comprehensive unit + performance tests for both features

### 1.4 Success Metrics

| Metric | Current | Target | Validation |
|--------|---------|--------|------------|
| **HybridRetriever creation (non-search)** | 150-250ms | <50ms | Performance test |
| **Fallback search quality** | ~60% | ~85% | Qualitative testing |
| **Fallback search time** | 2-3s | <1s | Performance test |
| **Tri-hybrid search (normal path)** | 10-12s | No regression | Regression test |
| **Test coverage** | 84% | 85%+ | Coverage report |

---

## 2. User Stories

**As a developer using `aur goals`**, I want retriever creation to be fast, so that I don't experience unnecessary delays when the retriever is only used for context lookup (not full search).

**As a user with embedding model issues**, I want search to still return relevant results using BM25+Activation, so that I can continue working with acceptable quality (~85%) rather than poor quality (~60%).

**As a maintainer**, I want fallback mode to be clearly logged, so that users can diagnose embedding model issues and restore full tri-hybrid search.

---

## 3. Requirements

### 3.1 Feature 1: Lazy BM25 Index Loading

#### 3.1.1 Core Requirements

**REQ-F1.1**: MUST defer BM25 index loading to first `retrieve()` call
- Remove `self._try_load_bm25_index()` call from `__init__()` (lines 532-533)
- Add lazy loading check at start of `_stage1_bm25_filter()` (lines 794-795)
- Use `_bm25_index_loaded` flag to ensure one-time loading

**REQ-F1.2**: MUST maintain thread-safety for lazy loading
- Use `threading.Lock` to prevent race conditions if multiple threads call `retrieve()` simultaneously
- Lock pattern: `with self._bm25_lock: if not self._bm25_index_loaded: ...`

**REQ-F1.3**: MUST preserve all existing BM25 index loading behavior
- Same error handling (pickle errors, empty index validation)
- Same logging (INFO level for success, WARNING for errors)
- Same fallback (build from candidates if no persistent index)

**REQ-F1.4**: MUST NOT break retriever caching
- `get_cached_retriever()` must continue to return retrievers without loading BM25 index eagerly
- Cache hit/miss behavior unchanged
- TTL expiration unchanged

#### 3.1.2 Performance Requirements

**REQ-F1.5**: MUST reduce HybridRetriever creation time to <50ms for non-search operations
- Target: 150-250ms → <50ms (3-5x improvement)
- Measured without BM25 index loading

**REQ-F1.6**: MUST NOT increase first `retrieve()` call latency by more than 5%
- First search pays one-time 100ms BM25 load cost
- Subsequent searches unchanged (index already loaded)

#### 3.1.3 Code Changes

**File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

**Change 1: Add lock to `__init__()`** (after line 529)
```python
# BM25 scorer (lazy-initialized in retrieve() or loaded from persistent index)
self.bm25_scorer: Any = None  # BM25Scorer from aurora_context_code.semantic.bm25_scorer
self._bm25_index_loaded = False  # Track if we've loaded the persistent index
self._bm25_lock = threading.Lock()  # NEW: Thread-safety for lazy loading
```

**Change 2: Remove eager loading from `__init__()`** (lines 532-533)
```python
# REMOVE THESE LINES:
# Try to load persistent BM25 index if configured
if self.config.enable_bm25_persistence and self.config.bm25_weight > 0:
    self._try_load_bm25_index()
```

**Change 3: Add lazy loading to `_stage1_bm25_filter()`** (after line 790, before line 791)
```python
def _stage1_bm25_filter(self, query: str, candidates: list[Any]) -> list[Any]:
    """Stage 1: Filter candidates using BM25 keyword matching.

    Uses persistent BM25 index if available, otherwise builds from candidates.
    The persistent index is built during indexing and loaded on first retrieve(),
    eliminating the O(n) index build on each query (51% of search time savings).

    Args:
        query: User query string
        candidates: Chunks retrieved by activation

    Returns:
        Top stage1_top_k candidates by BM25 score

    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer

    # NEW: Lazy load BM25 index on first retrieve() call (thread-safe)
    if not self._bm25_index_loaded and self.config.enable_bm25_persistence:
        with self._bm25_lock:
            # Double-check pattern (another thread may have loaded while we waited)
            if not self._bm25_index_loaded:
                self._try_load_bm25_index()

    # Use persistent index if loaded, otherwise build from candidates
    if self._bm25_index_loaded and self.bm25_scorer is not None:
        logger.debug("Using persistent BM25 index")
    else:
        # Build BM25 index from candidates (fallback if no persistent index)
        ...existing code...
```

---

### 3.2 Feature 2: BM25+Activation Dual-Hybrid Fallback

#### 3.2.1 Core Requirements

**REQ-F2.1**: MUST replace `_fallback_to_activation_only()` with `_fallback_to_dual_hybrid()`
- Rename method from `_fallback_to_activation_only()` to `_fallback_to_dual_hybrid()`
- Run `_stage1_bm25_filter()` to get BM25 scores for candidates
- Calculate hybrid_score = bm25_weight*bm25 + activation_weight*activation (no semantic component)
- Update all call sites (lines 628, 639)

**REQ-F2.2**: MUST normalize weights to sum to 1.0 in dual-hybrid mode
- When semantic_weight > 0 but embeddings unavailable, redistribute:
  - `bm25_dual = bm25_weight / (bm25_weight + activation_weight)`
  - `activation_dual = activation_weight / (bm25_weight + activation_weight)`
- Example: (0.3, 0.3, 0.4) → (0.5, 0.5, 0.0) in fallback

**REQ-F2.3**: MUST log fallback mode at WARNING level
- Clear message: "Embedding model unavailable - using BM25+Activation fallback (estimated 85% quality vs 95% tri-hybrid)"
- Include instructions: "To restore full quality, check embedding model installation: pip install sentence-transformers"

**REQ-F2.4**: MUST maintain tri-hybrid result format in fallback
- Return same dict structure: `chunk_id`, `content`, `bm25_score`, `activation_score`, `semantic_score`, `hybrid_score`, `metadata`
- Set `semantic_score: 0.0` for all results
- Set `hybrid_score: bm25_dual*bm25 + activation_dual*activation`

#### 3.2.2 Performance Requirements

**REQ-F2.5**: MUST complete fallback search in <1s (warm search)
- BM25 filter: ~200-300ms (from profiling)
- Activation scoring: ~100-200ms
- Total: <1s (vs 2-3s in current activation-only)

**REQ-F2.6**: MUST NOT regress normal tri-hybrid search performance
- No additional overhead in happy path
- Fallback only triggered on embedding generation failure

#### 3.2.3 Code Changes

**File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

**Change 4: Rename and reimplement fallback method** (lines 930-956)
```python
def _fallback_to_dual_hybrid(
    self,
    activation_candidates: list[Any],
    query: str,
    top_k: int
) -> list[dict[str, Any]]:
    """Fallback to BM25+Activation dual-hybrid when embeddings unavailable.

    This fallback provides better search quality (~85%) than activation-only (~60%)
    by leveraging keyword matching (BM25) alongside access patterns (activation).

    Args:
        activation_candidates: Chunks retrieved by activation
        query: User query string
        top_k: Number of results to return

    Returns:
        List of results with BM25+Activation dual-hybrid scores (semantic=0)

    """
    logger.warning(
        "Embedding model unavailable - using BM25+Activation fallback "
        "(estimated 85% quality vs 95% tri-hybrid). "
        "To restore full quality, check: pip install sentence-transformers"
    )

    # Run Stage 1 BM25 filter to get keyword scores
    stage1_candidates = self._stage1_bm25_filter(query, activation_candidates)

    # Normalize weights (redistribute semantic_weight to bm25 and activation)
    total_weight = self.config.bm25_weight + self.config.activation_weight
    if total_weight < 1e-6:
        # Edge case: both weights are 0, fall back to activation-only
        logger.warning("Both BM25 and activation weights are 0 - using activation-only")
        bm25_dual = 0.0
        activation_dual = 1.0
    else:
        bm25_dual = self.config.bm25_weight / total_weight
        activation_dual = self.config.activation_weight / total_weight

    # Build results with dual-hybrid scoring
    results = []
    for chunk in stage1_candidates:
        activation_score = getattr(chunk, "activation", 0.0)

        # Get BM25 score (already calculated in _stage1_bm25_filter)
        if self.config.bm25_weight > 0 and self.bm25_scorer is not None:
            chunk_content = self._get_chunk_content_for_bm25(chunk)
            bm25_score = self.bm25_scorer.score(query, chunk_content)
        else:
            bm25_score = 0.0

        results.append({
            "chunk": chunk,
            "raw_activation": activation_score,
            "raw_semantic": 0.0,  # No embeddings available
            "raw_bm25": bm25_score,
        })

    # Normalize scores independently
    activation_scores_normalized = self._normalize_scores([r["raw_activation"] for r in results])
    bm25_scores_normalized = self._normalize_scores([r["raw_bm25"] for r in results])

    # Batch fetch access stats (N+1 query optimization)
    chunk_ids = [r["chunk"].id for r in results]
    access_stats_cache: dict[str, dict[str, Any]] = {}
    if hasattr(self.store, "get_access_stats_batch"):
        try:
            access_stats_cache = self.store.get_access_stats_batch(chunk_ids)
        except Exception as e:
            logger.debug(f"Batch access stats failed: {e}")

    # Calculate dual-hybrid scores
    final_results = []
    for i, result_data in enumerate(results):
        chunk = result_data["chunk"]
        activation_norm = activation_scores_normalized[i]
        bm25_norm = bm25_scores_normalized[i]

        # Dual-hybrid scoring: weighted BM25 + activation (no semantic)
        hybrid_score = bm25_dual * bm25_norm + activation_dual * activation_norm

        content, metadata = self._extract_chunk_content_metadata(
            chunk,
            access_stats_cache=access_stats_cache,
        )

        final_results.append({
            "chunk_id": chunk.id,
            "content": content,
            "bm25_score": bm25_norm,
            "activation_score": activation_norm,
            "semantic_score": 0.0,  # Embeddings unavailable
            "hybrid_score": hybrid_score,
            "metadata": metadata,
        })

    # Sort by hybrid score (descending)
    final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

    # Return top K results
    return final_results[:top_k]
```

**Change 5: Update call sites** (lines 628, 639)
```python
# Line 628 (no embedding provider)
if self.embedding_provider is None:
    logger.debug("No embedding provider - using BM25+Activation fallback")
    return self._fallback_to_dual_hybrid(activation_candidates, query, top_k)

# Line 639 (embedding generation failed)
except Exception as e:
    if self.config.fallback_to_activation:
        return self._fallback_to_dual_hybrid(activation_candidates, query, top_k)
    raise ValueError(f"Failed to generate query embedding: {e}") from e
```

---

### 3.3 Testing Requirements

#### 3.3.1 Unit Tests

**REQ-T1**: MUST add unit test for lazy BM25 loading
- File: `tests/unit/context_code/semantic/test_hybrid_retriever_lazy_loading.py`
- Test cases:
  1. Retriever creation does NOT load BM25 index
  2. First `retrieve()` call loads BM25 index
  3. Subsequent `retrieve()` calls reuse loaded index
  4. Thread-safety: concurrent `retrieve()` calls load index exactly once

**REQ-T2**: MUST add unit test for dual-hybrid fallback
- File: `tests/unit/context_code/semantic/test_hybrid_retriever_dual_fallback.py`
- Test cases:
  1. Fallback returns BM25+Activation scores when embeddings unavailable
  2. Weights normalized correctly (bm25_dual + activation_dual = 1.0)
  3. Result format matches tri-hybrid (semantic_score=0.0)
  4. WARNING log emitted with clear instructions

**REQ-T3**: MUST add regression test for tri-hybrid happy path
- Existing tests in `test_hybrid_retriever.py` must pass unchanged
- No performance regression in normal search path

#### 3.3.2 Performance Tests

**REQ-T4**: MUST add performance test for lazy loading
- File: `tests/performance/test_hybrid_retriever_lazy_loading.py`
- Measure retriever creation time (without BM25 load)
- Assert creation time < 50ms
- Measure first `retrieve()` time (with BM25 load)
- Assert first retrieve < 1.05x baseline (5% tolerance)

**REQ-T5**: MUST add performance test for fallback speed
- File: `tests/performance/test_hybrid_retriever_dual_fallback.py`
- Measure fallback search time (warm, no embeddings)
- Assert search time < 1s
- Compare to baseline tri-hybrid (should be faster due to no embedding computation)

#### 3.3.3 Qualitative Testing

**REQ-T6**: MUST validate search quality in fallback mode
- Manual testing with 10 representative queries
- Compare results: tri-hybrid vs dual-hybrid vs activation-only
- Document methodology in `docs/analysis/FALLBACK_QUALITY_ANALYSIS.md`
- Expected: dual-hybrid ~85% quality, activation-only ~60% quality

---

## 4. Design Details

### 4.1 Lazy BM25 Index Loading

#### 4.1.1 Current Flow (Eager Loading)
```
HybridRetriever.__init__()
  ├─ Initialize config, store, engine
  ├─ self._try_load_bm25_index()  <-- EAGER LOAD (100-200ms)
  │   ├─ Check if index file exists
  │   ├─ Load BM25 index from disk (pickle.load)
  │   └─ Validate corpus size > 0
  └─ Initialize query cache

Total __init__ time: 150-250ms
```

#### 4.1.2 New Flow (Lazy Loading)
```
HybridRetriever.__init__()
  ├─ Initialize config, store, engine
  ├─ self._bm25_index_loaded = False  <-- NO LOADING
  ├─ self._bm25_lock = threading.Lock()
  └─ Initialize query cache

Total __init__ time: <50ms (3-5x faster)

---

First retrieve() call:
  ├─ Check if self._bm25_index_loaded == False
  ├─ Acquire self._bm25_lock
  ├─ Double-check self._bm25_index_loaded (race condition guard)
  ├─ self._try_load_bm25_index()  <-- ONE-TIME LOAD (100-200ms)
  │   ├─ Load BM25 index from disk
  │   └─ Set self._bm25_index_loaded = True
  ├─ Release lock
  └─ Continue with search...

First retrieve() time: baseline + 100-200ms (one-time cost)

---

Subsequent retrieve() calls:
  ├─ Check if self._bm25_index_loaded == True  <-- ALREADY LOADED
  └─ Skip loading, proceed directly to search

Subsequent retrieve() time: baseline (no overhead)
```

#### 4.1.3 Thread-Safety Design

**Problem**: Multiple threads calling `retrieve()` simultaneously might load index multiple times.

**Solution**: Double-checked locking pattern
```python
# Fast path (no lock contention after first load)
if not self._bm25_index_loaded:
    with self._bm25_lock:
        # Double-check: another thread may have loaded while we waited
        if not self._bm25_index_loaded:
            self._try_load_bm25_index()
            self._bm25_index_loaded = True
```

**Rationale**:
- First check (no lock): Fast path for already-loaded case (99.9% of calls)
- Lock acquisition: Only when index not loaded (first call, or multiple threads racing)
- Second check (under lock): Prevents duplicate loading if another thread loaded while we waited

---

### 4.2 BM25+Activation Dual-Hybrid Fallback

#### 4.2.1 Current Fallback (Activation-Only)
```
_fallback_to_activation_only(chunks, top_k)
  ├─ Take top_k chunks by activation score (pre-sorted)
  ├─ Set bm25_score = 0.0 for all results
  ├─ Set semantic_score = 0.0 for all results
  ├─ Set hybrid_score = activation_score (pure activation)
  └─ Return results

Quality: ~60% (access patterns only, no keyword matching)
Time: <200ms (no computation, just slicing)
```

#### 4.2.2 New Fallback (BM25+Activation Dual-Hybrid)
```
_fallback_to_dual_hybrid(chunks, query, top_k)
  ├─ Run _stage1_bm25_filter(query, chunks)  <-- ADD KEYWORD MATCHING
  │   ├─ Tokenize query
  │   ├─ Load/build BM25 index
  │   ├─ Score all chunks with BM25
  │   └─ Return top stage1_top_k candidates (default: 100)
  ├─ Normalize weights (redistribute semantic to bm25+activation)
  │   ├─ bm25_dual = bm25_weight / (bm25_weight + activation_weight)
  │   └─ activation_dual = activation_weight / (bm25_weight + activation_weight)
  ├─ Calculate dual-hybrid scores
  │   ├─ Normalize BM25 scores to [0, 1]
  │   ├─ Normalize activation scores to [0, 1]
  │   └─ hybrid_score = bm25_dual * bm25_norm + activation_dual * activation_norm
  ├─ Sort by hybrid_score (descending)
  └─ Return top_k results

Quality: ~85% (keyword + access patterns, similar to dual-hybrid mode)
Time: <1s (BM25 filter ~200-300ms + scoring ~100-200ms)
```

#### 4.2.3 Weight Normalization Logic

**Tri-Hybrid (Normal)**: Weights sum to 1.0
- BM25: 0.3 (30%)
- Activation: 0.3 (30%)
- Semantic: 0.4 (40%)

**Dual-Hybrid (Fallback)**: Redistribute semantic weight proportionally
- BM25: 0.3 / (0.3 + 0.3) = 0.5 (50%)
- Activation: 0.3 / (0.3 + 0.3) = 0.5 (50%)
- Semantic: 0.0 (0%)

**Edge Case**: Both BM25 and activation weights are 0
- BM25: 0.0 (0%)
- Activation: 1.0 (100%)
- Semantic: 0.0 (0%)
- Fallback to pure activation-only

#### 4.2.4 Quality Comparison

| Mode | BM25 | Activation | Semantic | Estimated Quality | Use Case |
|------|------|------------|----------|-------------------|----------|
| **Tri-Hybrid (normal)** | 30% | 30% | 40% | 95%+ | Normal operation (embeddings available) |
| **Dual-Hybrid (fallback)** | 50% | 50% | 0% | ~85% | Embeddings unavailable, BM25 available |
| **Activation-Only (legacy)** | 0% | 100% | 0% | ~60% | No BM25, no embeddings (worst case) |

**Rationale for 85% quality estimate**:
- BM25 provides strong keyword matching (exact matches, function names)
- Activation provides access patterns (recently used, frequently accessed)
- Combined dual-hybrid captures ~85% of tri-hybrid quality
- Missing semantic similarity (40%) reduces quality by ~10-15 percentage points

---

## 5. Acceptance Criteria

### 5.1 Feature 1: Lazy BM25 Index Loading

**AC-F1.1**: HybridRetriever creation completes in <50ms (without BM25 load)
- Measured via `time.perf_counter()` in performance test
- Baseline (with eager load): 150-250ms
- Target (lazy load): <50ms

**AC-F1.2**: First `retrieve()` call loads BM25 index successfully
- Index loaded from disk (persistent index path)
- Corpus size validated (>0 documents)
- `_bm25_index_loaded` flag set to `True`

**AC-F1.3**: Subsequent `retrieve()` calls reuse loaded index
- No additional file I/O
- No duplicate loading
- Performance unchanged from baseline

**AC-F1.4**: Thread-safety guaranteed for concurrent calls
- Unit test: 10 threads call `retrieve()` simultaneously
- Assert: BM25 index loaded exactly once
- Assert: No race conditions, no exceptions

**AC-F1.5**: Existing BM25 persistence tests pass unchanged
- `test_hybrid_retriever_cache.py`: All tests pass
- `test_hybrid_retriever_threshold.py`: All tests pass
- No regressions in index load behavior

---

### 5.2 Feature 2: BM25+Activation Dual-Hybrid Fallback

**AC-F2.1**: Fallback mode triggered when embeddings unavailable
- Scenario 1: `embedding_provider=None`
- Scenario 2: `embed_query()` raises exception
- Assert: `_fallback_to_dual_hybrid()` called

**AC-F2.2**: Fallback returns BM25+Activation scores
- All results have `bm25_score > 0` (keyword matching applied)
- All results have `activation_score > 0` (access patterns applied)
- All results have `semantic_score == 0.0` (no embeddings)

**AC-F2.3**: Weights normalized to sum to 1.0
- Example: (0.3, 0.3, 0.4) → (0.5, 0.5, 0.0)
- Assert: `bm25_dual + activation_dual == 1.0` (within 1e-6 tolerance)

**AC-F2.4**: WARNING log emitted with clear instructions
- Log level: `WARNING`
- Message contains: "BM25+Activation fallback", "85% quality", "pip install sentence-transformers"
- Log visible in `aur mem search` output

**AC-F2.5**: Search completes in <1s (warm search, fallback mode)
- Measured via `time.perf_counter()` in performance test
- Baseline (activation-only): 2-3s
- Target (dual-hybrid): <1s

**AC-F2.6**: Search quality ~85% vs tri-hybrid
- Manual testing with 10 queries
- Results overlap: dual-hybrid vs tri-hybrid (top 10 results)
- Expected: 7-9 results match (70-90% overlap)

---

### 5.3 General Acceptance Criteria

**AC-G1**: All existing tests pass unchanged
- `make test-unit`: 100% pass rate
- `make test-integration`: 100% pass rate
- No regressions introduced

**AC-G2**: Code coverage maintained at 85%+
- Feature 1: Lazy loading code covered
- Feature 2: Dual-hybrid fallback code covered
- Edge cases covered (empty index, thread races, weight edge cases)

**AC-G3**: Performance regression tests pass
- Cold search: No regression (10-12s maintained)
- Warm search: No regression (2-3s maintained in tri-hybrid)
- Fallback search: <1s (improvement over activation-only)

**AC-G4**: Documentation updated
- `hybrid_retriever.py`: Docstrings updated for both features
- `CLAUDE.md`: Performance section updated with new benchmarks
- `MEMORY_SEARCH_OPTIMIZATION_PLAN.md`: Updated with implementation status

---

## 6. Implementation Plan

### 6.1 Task Breakdown

**Task 1: Lazy BM25 Index Loading** (4 hours)
- [ ] **1.1**: Add `_bm25_lock` to `__init__()` (30 min)
- [ ] **1.2**: Remove eager `_try_load_bm25_index()` call from `__init__()` (15 min)
- [ ] **1.3**: Add lazy loading to `_stage1_bm25_filter()` with double-checked locking (1 hour)
- [ ] **1.4**: Add unit tests for lazy loading (4 test cases) (1 hour)
- [ ] **1.5**: Add performance test for creation time <50ms (30 min)
- [ ] **1.6**: Run full test suite, fix any regressions (1 hour)

**Task 2: BM25+Activation Dual-Hybrid Fallback** (6 hours)
- [ ] **2.1**: Rename `_fallback_to_activation_only()` to `_fallback_to_dual_hybrid()` (15 min)
- [ ] **2.2**: Implement BM25 filter in fallback method (1 hour)
- [ ] **2.3**: Implement weight normalization logic (30 min)
- [ ] **2.4**: Implement dual-hybrid scoring calculation (30 min)
- [ ] **2.5**: Update call sites (lines 628, 639) (15 min)
- [ ] **2.6**: Add WARNING logging with instructions (15 min)
- [ ] **2.7**: Add unit tests for dual-hybrid fallback (5 test cases) (1.5 hours)
- [ ] **2.8**: Add performance test for fallback speed <1s (30 min)
- [ ] **2.9**: Run full test suite, fix any regressions (1.5 hours)

**Task 3: Qualitative Validation** (3 hours)
- [ ] **3.1**: Manual testing with 10 queries (tri-hybrid vs dual-hybrid) (1 hour)
- [ ] **3.2**: Document results in `FALLBACK_QUALITY_ANALYSIS.md` (1 hour)
- [ ] **3.3**: Performance benchmarking (before/after) (1 hour)

**Task 4: Documentation & Review** (2 hours)
- [ ] **4.1**: Update docstrings in `hybrid_retriever.py` (30 min)
- [ ] **4.2**: Update `CLAUDE.md` performance section (30 min)
- [ ] **4.3**: Update `MEMORY_SEARCH_OPTIMIZATION_PLAN.md` (30 min)
- [ ] **4.4**: Code review, address feedback (30 min)

**Total Estimated Effort**: 15 hours (2 working days)

---

### 6.2 Testing Strategy

#### 6.2.1 Unit Tests

**File**: `tests/unit/context_code/semantic/test_hybrid_retriever_lazy_loading.py`
```python
@pytest.mark.unit
def test_lazy_loading_not_triggered_on_init(store, engine, provider):
    """Test that BM25 index is NOT loaded during __init__()."""
    retriever = HybridRetriever(store, engine, provider)
    assert retriever._bm25_index_loaded is False
    assert retriever.bm25_scorer is None

@pytest.mark.unit
def test_lazy_loading_triggered_on_first_retrieve(store, engine, provider):
    """Test that BM25 index is loaded on first retrieve() call."""
    retriever = HybridRetriever(store, engine, provider)
    results = retriever.retrieve("test query", top_k=5)
    assert retriever._bm25_index_loaded is True
    assert retriever.bm25_scorer is not None

@pytest.mark.unit
def test_lazy_loading_reuses_index_on_subsequent_calls(store, engine, provider):
    """Test that BM25 index is reused (not reloaded) on subsequent calls."""
    retriever = HybridRetriever(store, engine, provider)
    retriever.retrieve("test query 1", top_k=5)
    scorer_first = retriever.bm25_scorer

    retriever.retrieve("test query 2", top_k=5)
    scorer_second = retriever.bm25_scorer

    assert scorer_first is scorer_second  # Same object (not reloaded)

@pytest.mark.unit
def test_lazy_loading_thread_safety(store, engine, provider):
    """Test that BM25 index is loaded exactly once with concurrent calls."""
    import threading
    retriever = HybridRetriever(store, engine, provider)

    def search():
        retriever.retrieve("test query", top_k=5)

    threads = [threading.Thread(target=search) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Assert: Index loaded exactly once (not 10 times)
    assert retriever._bm25_index_loaded is True
```

**File**: `tests/unit/context_code/semantic/test_hybrid_retriever_dual_fallback.py`
```python
@pytest.mark.unit
def test_fallback_triggered_when_no_provider(store, engine):
    """Test that dual-hybrid fallback is triggered when provider=None."""
    retriever = HybridRetriever(store, engine, embedding_provider=None)
    results = retriever.retrieve("test query", top_k=5)

    # Assert: All results have semantic_score=0.0
    for result in results:
        assert result["semantic_score"] == 0.0
        assert result["bm25_score"] > 0.0
        assert result["activation_score"] > 0.0

@pytest.mark.unit
def test_fallback_triggered_when_embed_fails(store, engine, mock_provider):
    """Test that dual-hybrid fallback is triggered when embed_query() fails."""
    mock_provider.embed_query.side_effect = RuntimeError("Model load failed")

    config = HybridConfig(fallback_to_activation=True)
    retriever = HybridRetriever(store, engine, mock_provider, config)

    results = retriever.retrieve("test query", top_k=5)

    # Assert: Fallback used (no exception raised)
    assert len(results) > 0
    for result in results:
        assert result["semantic_score"] == 0.0

@pytest.mark.unit
def test_fallback_normalizes_weights_correctly(store, engine):
    """Test that weights are normalized to sum to 1.0 in fallback."""
    config = HybridConfig(bm25_weight=0.3, activation_weight=0.3, semantic_weight=0.4)
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    results = retriever.retrieve("test query", top_k=5)

    # Check weights in result calculation
    # Expected: bm25_dual=0.5, activation_dual=0.5
    # (0.3 / (0.3 + 0.3) = 0.5)

    # Verify by checking hybrid_score formula matches expected weights
    for result in results:
        expected_hybrid = (
            0.5 * result["bm25_score"] +
            0.5 * result["activation_score"]
        )
        assert abs(result["hybrid_score"] - expected_hybrid) < 1e-6

@pytest.mark.unit
def test_fallback_logs_warning(store, engine, caplog):
    """Test that WARNING log is emitted with fallback instructions."""
    retriever = HybridRetriever(store, engine, embedding_provider=None)

    with caplog.at_level(logging.WARNING):
        retriever.retrieve("test query", top_k=5)

    # Assert: Warning logged
    assert any("BM25+Activation fallback" in record.message for record in caplog.records)
    assert any("85% quality" in record.message for record in caplog.records)
    assert any("pip install sentence-transformers" in record.message for record in caplog.records)

@pytest.mark.unit
def test_fallback_handles_edge_case_zero_weights(store, engine):
    """Test fallback when both BM25 and activation weights are 0."""
    config = HybridConfig(bm25_weight=0.0, activation_weight=0.0, semantic_weight=1.0)
    retriever = HybridRetriever(store, engine, embedding_provider=None, config=config)

    results = retriever.retrieve("test query", top_k=5)

    # Assert: Falls back to activation-only (100%)
    for result in results:
        expected_hybrid = result["activation_score"]
        assert abs(result["hybrid_score"] - expected_hybrid) < 1e-6
```

#### 6.2.2 Performance Tests

**File**: `tests/performance/test_hybrid_retriever_lazy_loading.py`
```python
@pytest.mark.performance
def test_perf_lazy_loading_creation_time(store, engine, provider):
    """Test that retriever creation completes in <50ms (lazy loading)."""
    import time

    start = time.perf_counter()
    retriever = HybridRetriever(store, engine, provider)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.050, f"Creation took {elapsed*1000:.1f}ms, expected <50ms"

@pytest.mark.performance
def test_perf_lazy_loading_first_retrieve_overhead(store, engine, provider):
    """Test that first retrieve() adds <5% overhead (one-time BM25 load)."""
    # Measure baseline (retriever with BM25 already loaded)
    retriever_baseline = HybridRetriever(store, engine, provider)
    retriever_baseline._try_load_bm25_index()  # Force load

    import time
    start = time.perf_counter()
    retriever_baseline.retrieve("test query", top_k=10)
    baseline_time = time.perf_counter() - start

    # Measure lazy loading (first retrieve loads BM25)
    retriever_lazy = HybridRetriever(store, engine, provider)
    start = time.perf_counter()
    retriever_lazy.retrieve("test query", top_k=10)
    lazy_time = time.perf_counter() - start

    # Assert: First retrieve overhead <5%
    overhead = (lazy_time - baseline_time) / baseline_time
    assert overhead < 0.05, f"First retrieve overhead {overhead*100:.1f}%, expected <5%"
```

**File**: `tests/performance/test_hybrid_retriever_dual_fallback.py`
```python
@pytest.mark.performance
def test_perf_fallback_search_speed(store, engine):
    """Test that dual-hybrid fallback completes in <1s (warm search)."""
    retriever = HybridRetriever(store, engine, embedding_provider=None)

    # Warm up (load BM25 index)
    retriever.retrieve("warmup query", top_k=10)

    # Measure fallback search
    import time
    start = time.perf_counter()
    results = retriever.retrieve("test query", top_k=10)
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"Fallback search took {elapsed:.2f}s, expected <1s"
    assert len(results) > 0

@pytest.mark.performance
def test_perf_fallback_faster_than_activation_only(store, engine):
    """Test that dual-hybrid fallback is faster than activation-only."""
    # This test validates that BM25+Activation is actually faster than
    # activation-only (counterintuitive, but true due to better candidate filtering)

    # TODO: Implement after baseline activation-only performance measured
    pass
```

#### 6.2.3 Qualitative Testing

**Manual Testing Protocol** (document in `docs/analysis/FALLBACK_QUALITY_ANALYSIS.md`):

1. **Setup**:
   - Index Aurora codebase: `aur mem index .`
   - Prepare 10 test queries (mix of exact matches, semantic queries)

2. **Test Queries**:
   ```
   1. "SoarOrchestrator class implementation"
   2. "memory search caching"
   3. "BM25 scoring algorithm"
   4. "agent discovery system"
   5. "activation engine ACT-R"
   6. "embedding provider configuration"
   7. "CLI command parsing"
   8. "retriever initialization"
   9. "hybrid weights normalization"
   10. "fallback mode handling"
   ```

3. **Execution**:
   - For each query:
     - Run tri-hybrid (normal): `aur mem search "query" --limit=10`
     - Run dual-hybrid (fallback): `AURORA_EMBEDDING_PROVIDER=none aur mem search "query" --limit=10`
     - Record top 10 results for both modes

4. **Analysis**:
   - Calculate overlap: `len(set(tri_results) & set(dual_results)) / 10`
   - Average overlap across 10 queries
   - Expected: 70-90% overlap (7-9 matching results)

5. **Documentation**:
   - Create table: Query | Tri-Hybrid Results | Dual-Hybrid Results | Overlap %
   - Summary: Average overlap, quality assessment, edge cases
   - Recommendation: Is 85% quality claim validated?

---

## 7. Performance Benchmarks

### 7.1 Baseline (Current)

| Operation | Time | Notes |
|-----------|------|-------|
| **HybridRetriever creation** | 150-250ms | Includes eager BM25 index load |
| **Cold search (tri-hybrid)** | 10-12s | Epic 1 improvements applied |
| **Warm search (tri-hybrid)** | 2-3s | Embeddings cached |
| **Fallback search (activation-only)** | 2-3s | No BM25, no embeddings |
| **Fallback quality (activation-only)** | ~60% | Access patterns only |

### 7.2 Target (After Epic 2)

| Operation | Time | Change | Notes |
|-----------|------|--------|-------|
| **HybridRetriever creation** | <50ms | -75% | Lazy BM25 loading |
| **Cold search (tri-hybrid)** | 10-12s | 0% | No regression |
| **Warm search (tri-hybrid)** | 2-3s | 0% | No regression |
| **Fallback search (dual-hybrid)** | <1s | -67% | BM25+Activation |
| **Fallback quality (dual-hybrid)** | ~85% | +25pp | Keyword matching added |

### 7.3 Validation Commands

**Benchmark retriever creation time**:
```bash
python -c "
import time
from aurora_core.store import SQLiteStore
from aurora_core.activation import ActivationEngine
from aurora_context_code.semantic import EmbeddingProvider, HybridRetriever

store = SQLiteStore('.aurora/memory.db')
engine = ActivationEngine(store)
provider = EmbeddingProvider()

# Measure creation time (10 iterations for accuracy)
times = []
for _ in range(10):
    start = time.perf_counter()
    retriever = HybridRetriever(store, engine, provider)
    elapsed = time.perf_counter() - start
    times.append(elapsed)

avg_time = sum(times) / len(times)
print(f'Average creation time: {avg_time*1000:.1f}ms')
print(f'Target: <50ms')
print(f'Pass: {avg_time < 0.050}')
"
```

**Benchmark fallback search speed**:
```bash
# Disable embeddings to trigger fallback
export AURORA_EMBEDDING_PROVIDER=none

python -c "
import time
from aurora_core.store import SQLiteStore
from aurora_core.activation import ActivationEngine
from aurora_context_code.semantic import HybridRetriever

store = SQLiteStore('.aurora/memory.db')
engine = ActivationEngine(store)

retriever = HybridRetriever(store, engine, embedding_provider=None)

# Warm up (load BM25 index)
retriever.retrieve('warmup', top_k=10)

# Measure search time (5 iterations)
times = []
for _ in range(5):
    start = time.perf_counter()
    results = retriever.retrieve('SoarOrchestrator', top_k=10)
    elapsed = time.perf_counter() - start
    times.append(elapsed)

avg_time = sum(times) / len(times)
print(f'Average fallback search time: {avg_time:.2f}s')
print(f'Target: <1s')
print(f'Pass: {avg_time < 1.0}')
"
```

---

## 8. Risk Assessment

### 8.1 Feature 1: Lazy BM25 Index Loading

**Risk Level**: LOW

**Risks**:
1. **Thread-safety issues** (MEDIUM)
   - Multiple threads calling `retrieve()` might load index multiple times
   - Mitigation: Double-checked locking pattern (proven, well-tested)
   - Validation: Unit test with 10 concurrent threads

2. **First retrieve() latency spike** (LOW)
   - First search pays one-time 100ms BM25 load cost
   - Mitigation: Acceptable trade-off (saves 100ms on non-search ops)
   - Validation: Performance test ensures overhead <5%

3. **Retriever caching interaction** (LOW)
   - Cached retrievers must not eagerly load BM25 index
   - Mitigation: `get_cached_retriever()` unchanged, lazy loading preserved
   - Validation: Existing cache tests pass unchanged

**Rollback Plan**:
- Revert: Restore eager loading in `__init__()`
- Command: `git revert <commit-hash>`
- Impact: 100-200ms slower retriever creation (acceptable fallback)

---

### 8.2 Feature 2: BM25+Activation Dual-Hybrid Fallback

**Risk Level**: LOW

**Risks**:
1. **Search quality degradation** (MEDIUM)
   - Dual-hybrid may return less relevant results than tri-hybrid
   - Mitigation: Qualitative testing validates ~85% quality (acceptable)
   - Validation: Manual testing with 10 queries, document overlap

2. **Weight normalization bugs** (LOW)
   - Edge cases (zero weights, negative weights) might break formula
   - Mitigation: Unit tests cover edge cases, validation checks
   - Validation: Test zero weights, test normalization sum=1.0

3. **Performance regression in happy path** (LOW)
   - Normal tri-hybrid search might be slowed by fallback code paths
   - Mitigation: Fallback only triggered on exception, no happy path impact
   - Validation: Regression test ensures tri-hybrid unchanged

**Rollback Plan**:
- Revert: Restore `_fallback_to_activation_only()` (rename back)
- Command: `git revert <commit-hash>`
- Impact: Search quality drops to 60% in fallback (known limitation)

---

### 8.3 Combined Risk Assessment

**Overall Risk**: LOW

**Rationale**:
- Both features are isolated (no interaction between them)
- Both features follow proven patterns (lazy loading, dual-hybrid scoring)
- Both features have comprehensive tests (unit + performance + qualitative)
- Rollback is straightforward (single commit revert)

**Recommendation**: PROCEED with implementation

---

## 9. Open Questions

None - all decisions have been made and documented in the PRD.

---

## 10. Non-Goals

The following are explicitly OUT OF SCOPE for this PRD:

**NG-1**: Pre-tokenization optimization (deferred to Epic 3)
- Reason: Larger effort (schema migration, indexer changes)
- Priority: P1 (next sprint)

**NG-2**: Query embedding cache improvements (deferred to Epic 3)
- Reason: Query normalization, semantic cache require research
- Priority: P2 (future sprint)

**NG-3**: BM25 index compression (deferred to Epic 3)
- Reason: Gzip/columnar storage requires benchmarking
- Priority: P2 (future sprint)

**NG-4**: Model quantization (deferred to Epic 3)
- Reason: FP16/ONNX requires accuracy testing
- Priority: P2 (future sprint)

**NG-5**: User-facing fallback mode indicator
- Reason: CLI output formatting is separate concern
- Priority: P3 (nice-to-have)

**NG-6**: Automatic embedding model installation
- Reason: Package management is user responsibility
- Priority: P3 (nice-to-have)

---

## 11. Success Metrics Summary

### 11.1 Performance Metrics

| Metric | Baseline | Target | Validation Method |
|--------|----------|--------|-------------------|
| HybridRetriever creation (non-search) | 150-250ms | <50ms | `test_perf_lazy_loading_creation_time` |
| First retrieve() overhead | 0ms | <5% | `test_perf_lazy_loading_first_retrieve_overhead` |
| Fallback search time (warm) | 2-3s | <1s | `test_perf_fallback_search_speed` |
| Tri-hybrid search (no regression) | 10-12s | 10-12s | `test_perf_trihybrid_regression` |

### 11.2 Quality Metrics

| Metric | Baseline | Target | Validation Method |
|--------|----------|--------|-------------------|
| Fallback search quality | ~60% | ~85% | Manual testing, overlap analysis |
| Tri-hybrid search quality | 95%+ | 95%+ | No regression |

### 11.3 Reliability Metrics

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Thread-safety (lazy loading) | 100% | `test_lazy_loading_thread_safety` |
| Edge case handling (zero weights) | 100% | `test_fallback_handles_edge_case_zero_weights` |
| Code coverage | 85%+ | `make coverage` |

---

## 12. Documentation Updates

### 12.1 Code Documentation

**File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- Update class docstring to mention lazy loading
- Update `__init__()` docstring to note BM25 loaded on first `retrieve()`
- Update `_stage1_bm25_filter()` docstring to mention lazy loading logic
- Update `_fallback_to_dual_hybrid()` docstring (new method)

**File**: `packages/context-code/src/aurora_context_code/semantic/__init__.py`
- No changes needed (public API unchanged)

### 12.2 Project Documentation

**File**: `CLAUDE.md`
- Update "Performance Optimization Rules" section
- Add note about lazy BM25 loading pattern
- Update "Memory System" section with fallback mode description

**File**: `docs/KNOWLEDGE_BASE.md`
- Update performance benchmarks (retriever creation <50ms)
- Add fallback quality metrics (85% vs 60%)

**File**: `docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md`
- Mark Epic 2 tasks as COMPLETED
- Update roadmap with Epic 3 tasks (pre-tokenization, etc.)

### 12.3 New Documentation

**File**: `docs/analysis/FALLBACK_QUALITY_ANALYSIS.md` (NEW)
- Document qualitative testing methodology
- 10 test queries with tri-hybrid vs dual-hybrid results
- Overlap analysis, quality assessment
- Recommendations for future improvements

---

## 13. Appendix

### 13.1 Exact Code Changes Summary

**File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

| Line Range | Change Type | Description |
|------------|-------------|-------------|
| 529 (after) | ADD | Add `self._bm25_lock = threading.Lock()` |
| 532-533 | REMOVE | Remove eager `self._try_load_bm25_index()` call |
| 790 (before) | ADD | Add lazy loading with double-checked locking |
| 628 | MODIFY | Change `_fallback_to_activation_only` to `_fallback_to_dual_hybrid` |
| 639 | MODIFY | Change `_fallback_to_activation_only` to `_fallback_to_dual_hybrid` |
| 930-956 | REPLACE | Replace method implementation with dual-hybrid logic |

**Total Lines Changed**: ~120 lines (50 lines modified, 70 lines added)

### 13.2 Test Files to Create

1. `tests/unit/context_code/semantic/test_hybrid_retriever_lazy_loading.py` (~100 lines)
2. `tests/unit/context_code/semantic/test_hybrid_retriever_dual_fallback.py` (~150 lines)
3. `tests/performance/test_hybrid_retriever_lazy_loading.py` (~80 lines)
4. `tests/performance/test_hybrid_retriever_dual_fallback.py` (~60 lines)

**Total Test Lines**: ~390 lines

### 13.3 Performance Improvement Summary

| Optimization | Impact | Measurement |
|-------------|--------|-------------|
| **Lazy BM25 Loading** | -75% retriever creation | 150-250ms → <50ms |
| **Dual-Hybrid Fallback** | +25pp quality | 60% → 85% |
| **Dual-Hybrid Fallback** | -67% fallback time | 2-3s → <1s |

**Combined Epic 1 + Epic 2**:
- Cold search: 15-19s (baseline) → 9-11s (67% of target <3s)
- Warm search: 4-5s (baseline) → 2-3s (60% of target <500ms)
- Fallback quality: 60% → 85% (+42% relative improvement)

**Remaining Gap to Target**:
- Cold search: Need 6-8s more improvement (Epic 3: pre-tokenization, compression)
- Warm search: Need 1.5-2.5s more improvement (Epic 3: query cache, model quantization)

---

## 14. References

- **Epic 1 PRD**: `tasks/aur-mem-search/0031-prd-epic1-foundation-caching.md`
- **Epic 1 Report**: `tasks/aur-mem-search/EPIC1_PERFORMANCE_REPORT.md`
- **Optimization Plan**: `docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md`
- **Performance Profile**: `docs/analysis/MEMORY_SEARCH_PERFORMANCE_PROFILE.md`
- **Cache Analysis**: `docs/analysis/CACHE_HIT_MISS_ANALYSIS.md`
- **CLAUDE.md**: `CLAUDE.md` (project instructions)
- **API Contracts**: `docs/reference/API_CONTRACTS_v1.0.md`

---

**End of PRD**
