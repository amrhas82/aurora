# `aur mem search` Performance Optimization Program

## Current Status

**Baseline:** 15-19s cold, 4-5s warm
**After Epic 1 (✓ DONE):** ~10-12s cold, ~2-3s warm
**Goal:** <3s cold, <500ms warm

---

## Epic 1: Instance & Cache Infrastructure ✓ COMPLETED

**Result**: 30-40% improvement (5-7s savings)

### Completed Tasks
1. ✓ Cache HybridRetriever instance (200-500ms savings)
2. ✓ Cache ActivationEngine instance (50-100ms savings)
3. ✓ Verify and fix BM25 index persistence (9.7s → <100ms)
4. ✓ Shared QueryEmbeddingCache across retrievers (100-200ms savings)

**Files Modified:**
- `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- `packages/core/src/aurora_core/activation/engine.py`

---

## Next Steps: High-Confidence Optimizations

Research shows Epic 1 caching is ✅ done, but some patterns can still be applied.

### Current State Analysis (hybrid_retriever.py)

**What's Already Implemented:**
- ✅ Activation-only fallback exists (lines 930-956): `_fallback_to_activation_only()`
  - Triggers when embedding provider is None or embedding generation fails
  - Returns `activation_score` only (BM25=0, semantic=0)
  - **Note:** Log message says "activation+BM25" but code only uses activation
- ✅ BM25 persistence works (lines 1071-1122): Loads from `.aurora/indexes/bm25_index.pkl`
- ✅ Query embedding cache (shared singleton, lines 246-301)
- ✅ HybridRetriever instance cache (module-level, lines 332-415)

**What's NOT Implemented:**
- ❌ Lazy BM25 loading: Currently loads in `__init__()` (lines 532-533)
- ❌ BM25+Activation dual-hybrid fallback: Current fallback is activation-only

**Import in Loop (Minor Issue):**
- Line 673: `from aurora_context_code.semantic.embedding_provider import cosine_similarity`
- Inside `for chunk in stage1_candidates:` loop
- Python caches imports, so overhead is ~1-5ms total (not 50-100ms as claimed)
- **Verdict:** Not worth optimizing

---

### 1. Lazy BM25 Index Loading (100-200ms savings)

**Current:** `_try_load_bm25_index()` called in `__init__()` (line 532-533)
**Why Change:** Proven pattern from `aur goals`/`aur soar` optimization (reduced startup by 200ms)

**Implementation:**
- **File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:532-533`
- Remove `_try_load_bm25_index()` call from `__init__()`
- Call `_try_load_bm25_index()` in `_stage1_bm25_filter()` on first use (line 794-795)
- Check `if not self._bm25_index_loaded:` before loading

**Impact:** 100-200ms faster HybridRetriever creation (helps `aur goals`, `aur soar`, any non-search operations)
**Risk:** VERY LOW (proven pattern, no algorithmic changes)
**Effort:** 1-2 hours

---

### 2. Upgrade Fallback to BM25+Activation (Dual-Hybrid)

**Current:** Activation-only fallback (line 930-956): Returns activation scores, BM25=0
**Why Upgrade:** BM25+Activation gives better quality (~85%) than activation-only (~60%) when embeddings unavailable

**Implementation:**
- **File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:930-956`
- Rename `_fallback_to_activation_only()` → `_fallback_to_dual_hybrid()`
- Inside fallback, run `_stage1_bm25_filter()` if `bm25_weight > 0`
- Calculate hybrid score: `bm25_weight * bm25_norm + activation_weight * activation_norm`
- Update log message at line 628: "Using dual-hybrid fallback (BM25+Activation)"

**Impact:** Better search quality (~85% vs ~60%) when embedding model fails or is loading
**Risk:** LOW (fallback path only, doesn't affect normal tri-hybrid operation)
**Effort:** 2-3 hours

---

## Needs Profiling First

These optimizations have uncertain ROI. Profile to confirm bottleneck exists, then decide.

### 3. Fix Double Tokenization? (Claimed: 1-2s savings)

**Claim:** 36,924 tokenization calls per search (500 chunks) suggests query/docs tokenized repeatedly.

**Before implementing:**
```bash
# Profile tokenization overhead
python -m cProfile -o profile.stats -m aurora_cli.main mem search "test query"
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats('tokenize', 20)"
```

**Decision criteria:**
- If >1s spent in `tokenize()`: Fix it (cache tokenized query, cache doc tokens)
- If <500ms: Skip it (not the bottleneck)

**File:** `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py`
**Risk:** MEDIUM (could affect BM25 scores if done wrong)
**Effort:** 3-4 hours + testing

### 4. Fix Connection Pool? (Claimed: 100-200ms savings)

**Claim:** Connections never returned to pool, causing churn.

**Before implementing:**
```bash
# Add logging to check pool reuse
# In packages/core/src/aurora_core/store/sqlite.py
# Log connection get/return events, check pool size after 10 searches
```

**Decision criteria:**
- If pool size grows unbounded: Fix it
- If pool stable at 1-2 connections: Skip it

**File:** `packages/core/src/aurora_core/store/sqlite.py`
**Risk:** MEDIUM-HIGH (database internals, potential deadlocks)
**Effort:** 3-5 hours

---

## Future/Low Priority

Optimizations that don't align with current goal (search speed) or have unproven value.

### 5. Content-Hash Embedding Cache (Re-Index Speedup Only)

**Why Deferred:** Optimizes re-indexing (100s → 15-25s), not search speed. Only valuable if re-indexing is frequent pain point.

**File:** `packages/core/src/aurora_core/store/sqlite.py`, `embedding_provider.py`
**Risk:** MEDIUM (cache invalidation complexity)
**Effort:** 6-8 hours

### 6. Replace json with orjson (Claimed: 50-100ms)

**Why Deferred:** No profiling evidence that JSON parsing is a bottleneck. Adds dependency for unproven gain.

**Risk:** LOW (easy to rollback)
**Effort:** 2-3 hours

---

## Recommended Execution Order

1. **Do immediately** (4-6 hours total):
   - Lazy BM25 loading (1-2 hrs)
   - BM25-only fallback (2-3 hrs)
   - **Expected result:** 10-12s → ~8-10s cold, 2-3s → ~1-2s warm

2. **Profile next** (1 hour):
   - Run tokenization profiler
   - Check connection pool stats
   - **Then decide:** Fix tokenization if >1s overhead, fix pool if leaking

3. **Defer** until search speed goal met:
   - Embedding cache (re-index optimization)
   - orjson (needs evidence)

---

## Success Metrics

| Milestone | Cold Search | Warm Search |
|-----------|-------------|-------------|
| Baseline (before Epic 1) | 15-19s | 4-5s |
| After Epic 1 (✓ Done) | 10-12s | 2-3s |
| After lazy loading + fallback | 8-10s | 1-2s |
| After profiling-driven fixes | <5s | <1s |
| Stretch goal | <3s | <500ms |
