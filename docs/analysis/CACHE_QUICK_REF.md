# Cache Hit/Miss Quick Reference

**Quick lookup guide for Aurora's caching system**

Related: `CACHE_HIT_MISS_ANALYSIS.md` (full analysis)

---

## 3 Cache Layers (Overview)

| Layer | Purpose | Hit Rate | Impact | Key |
|-------|---------|----------|--------|-----|
| **HybridRetriever** | Reuse retriever instances | ~70% | 30-40% speedup | `(db_path, config_hash)` |
| **QueryEmbedding** | Reuse query embeddings | 60%+ | 99.8% speedup (on hit) | `MD5(normalized_query)` |
| **ActivationEngine** | Share activation engine | ~95% | 40-50% speedup | `db_path` |

---

## Common Cache Patterns

### ✅ Cache HIT (Fast)

```python
# Scenario 1: Repeated query (same session)
aur mem search "authentication"    # MISS (2.9s)
aur mem search "authentication"    # HIT (<5ms) - 99.8% faster

# Scenario 2: Case/whitespace variations
aur mem search "Authentication"    # MISS
aur mem search "authentication"    # HIT (normalized)

# Scenario 3: SOAR multi-phase (automatic)
# Phase 2: RETRIEVE → MISS
# Phase 7: SYNTHESIZE → HIT (same retriever cached)
```

### ❌ Cache MISS (Slow)

```python
# Scenario 1: Word variations (most common miss)
aur mem search "authentication"    # MISS
aur mem search "authenticate"      # MISS (different word)
aur mem search "auth"              # MISS (abbreviation)

# Scenario 2: Word order changes
aur mem search "user authentication"    # MISS
aur mem search "authentication user"    # MISS (different order)

# Scenario 3: Stop words
aur mem search "authentication system"      # MISS
aur mem search "the authentication system"  # MISS ("the" included)

# Scenario 4: TTL expiration (30 min default)
aur mem search "auth"    # MISS (t=0)
# ... 31 minutes later ...
aur mem search "auth"    # MISS (expired)
```

---

## Performance Cheat Sheet

| Scenario | Time | Notes |
|----------|------|-------|
| **Cold search (MISS)** | 10-12s | First search, all caches miss |
| **Warm search (HIT)** | 2-3s | Retriever + query embedding cached |
| **Query cache HIT** | <5ms | 580x faster than MISS (2.9s) |
| **Query cache MISS** | 2.9s | Transformer inference |
| **Index rebuild (MISS)** | 9.7s | Avoided on retriever cache HIT |
| **Index load (HIT)** | 405ms | 24x faster than rebuild |

---

## Environment Variables

```bash
# Retriever cache
export AURORA_RETRIEVER_CACHE_SIZE=10      # Max retrievers (default: 10)
export AURORA_RETRIEVER_CACHE_TTL=1800     # TTL in seconds (default: 30 min)

# Query cache (via HybridConfig)
# Set in config.json: context.code.hybrid_weights.query_cache_size
# Set in config.json: context.code.hybrid_weights.query_cache_ttl_seconds

# Disable all caching (debugging only)
export AURORA_DISABLE_CACHING=1
```

---

## Cache Statistics (Programmatic)

```python
# Retriever cache stats
from aurora_context_code.semantic.hybrid_retriever import get_cache_stats
stats = get_cache_stats()
# {
#   "total_hits": 42,
#   "total_misses": 8,
#   "hit_rate": 0.84,
#   "cache_size": 3
# }

# Query cache stats (via retriever instance)
stats = retriever.get_cache_stats()
# {
#   "query_cache_enabled": True,
#   "query_cache_size": 42,
#   "query_cache_capacity": 100,
#   "hits": 73,
#   "misses": 49,
#   "hit_rate": 0.60,
#   "evictions": 0
# }
```

---

## Cache Invalidation

```bash
# Clear retriever cache (forces BM25 index rebuild)
aur mem index .

# Clear all caches (nuclear option)
aur mem clear-cache

# Python API
from aurora_context_code.semantic.hybrid_retriever import (
    clear_retriever_cache,
    clear_shared_query_cache
)
clear_retriever_cache()
clear_shared_query_cache()
```

---

## Optimization Quick Wins

| Optimization | Hit Rate Gain | Effort | Risk |
|--------------|---------------|--------|------|
| **Enhanced query normalization** | 60% → 80% (+20%) | 4-6 hours | LOW |
| **Adaptive TTL** | -5% misses | 1-2 days | LOW |
| **Increased capacity (100→200)** | -2.5% misses | 1 hour | LOW |
| **Semantic clustering** | 60% → 75% (+15%) | 3-5 days | MEDIUM |

**Recommended**: Start with enhanced query normalization (quick win, low risk).

---

## Debug Logging

```bash
# Enable cache debug logs
export AURORA_LOG_LEVEL=DEBUG
aur mem search "authentication"
```

**Expected output**:
```
DEBUG - Creating new HybridRetriever for db_path=... (hit_rate=0.0%)
DEBUG - Cached embedding for: authentication...
DEBUG - Reusing cached HybridRetriever for db_path=... (hit_rate=50.0%)
DEBUG - Query cache hit for: authentication...
```

---

## Common Pitfalls

### ❌ Pitfall 1: Assuming cache invalidation on index changes

**Problem**: Adding/removing chunks doesn't invalidate retriever cache.

**Workaround**: Run `aur mem index .` after significant index changes.

**Why**: Cache key is `(db_path, config_hash)`, not `(db_path, index_version)`.

### ❌ Pitfall 2: Expecting cache hits for similar queries

**Problem**: "auth" and "authentication" are different cache keys.

**Workaround**: Use exact query wording, or implement enhanced normalization.

**Why**: Current normalization only handles case/whitespace, not stemming.

### ❌ Pitfall 3: Expecting persistent cache across process restarts

**Problem**: Cache is in-memory (module-level), lost on restart.

**Workaround**: Consider persistent query cache (future enhancement).

**Why**: Simplicity and correctness (no stale cache on code changes).

---

## Query Normalization (Current vs Enhanced)

### Current (v0.11.x)

```python
def _normalize_query(query: str) -> str:
    """Normalize query for cache key."""
    return " ".join(query.lower().split())
```

**Handles**:
- ✅ Case: "Auth" → "auth"
- ✅ Whitespace: "auth  system" → "auth system"

**Doesn't handle**:
- ❌ Stop words: "the auth system" ≠ "auth system"
- ❌ Word order: "user auth" ≠ "auth user"
- ❌ Stemming: "authenticate" ≠ "authentication"

### Enhanced (Proposed)

```python
def _normalize_query(query: str) -> str:
    normalized = query.lower()
    tokens = normalized.split()
    # Remove stop words
    tokens = [t for t in tokens if t not in STOP_WORDS]
    # Stem words
    tokens = [stemmer.stem(t) for t in tokens]
    # Sort for order-invariance
    tokens.sort()
    return " ".join(tokens)
```

**Handles**:
- ✅ Stop words: "the auth system" → "auth system"
- ✅ Word order: "user auth" → "auth user"
- ✅ Stemming: "authenticate" → "authent"

**Expected impact**: 60% → 80%+ hit rate.

---

## Monitoring Checklist

- [ ] Track hit rates (retriever and query cache)
- [ ] Monitor cache size vs capacity
- [ ] Watch for TTL expirations (>10% is high)
- [ ] Alert on evictions (indicates capacity issues)
- [ ] Measure average query time (target: <500ms warm)

---

## Related Documentation

- **Full Analysis**: `CACHE_HIT_MISS_ANALYSIS.md`
- **Performance Profile**: `MEMORY_SEARCH_PERFORMANCE_PROFILE.md`
- **Optimization Plan**: `MEMORY_SEARCH_OPTIMIZATION_PLAN.md`
- **Epic 1 PRD**: `.aurora/plans/completed/epic-1-caching/prd.md`
