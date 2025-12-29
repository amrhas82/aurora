# Search Scoring Investigation Report

**Date**: 2025-12-29
**Sprint**: Sprint 1 - Fix Search Scoring
**Status**: ROOT CAUSES IDENTIFIED

---

## Executive Summary

All search results show identical scores (activation=1.000, semantic=1.000, hybrid=1.000) due to three interconnected bugs in the scoring pipeline. The bugs prevent both activation and semantic scores from being properly retrieved and calculated.

---

## Root Causes Identified

### Bug 1: Missing Activation Attribute (CRITICAL)

**Location**: `packages/core/src/aurora_core/store/sqlite.py`, lines 376-394
**Function**: `SQLiteStore.retrieve_by_activation()`

**Problem**: The SQL query retrieves chunks but does NOT select the `base_level` from the `activations` table:

```python
cursor = conn.execute(
    """
    SELECT c.id, c.type, c.content, c.metadata, c.embeddings, c.created_at, c.updated_at
    FROM chunks c
    JOIN activations a ON c.id = a.chunk_id
    WHERE a.base_level >= ?
    ORDER BY a.base_level DESC
    LIMIT ?
    """,
    (actual_min, limit),
)
```

The `a.base_level` is used for filtering and ordering, but it is NOT selected and NOT attached to the returned chunk objects. When `HybridRetriever.retrieve()` calls `getattr(chunk, 'activation', 0.0)`, it always gets the default 0.0.

**Evidence**:
```python
>>> chunks = store.retrieve_by_activation(min_activation=0.0, limit=3)
>>> hasattr(chunks[0], 'activation')
False
>>> getattr(chunks[0], 'activation', 0.0)
0.0
```

**Fix Required**: Modify the SQL query to include `a.base_level AS activation` and set it on the chunk object during deserialization.

---

### Bug 2: Wrong Embedding Attribute Name (CRITICAL)

**Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`, line 180
**Function**: `HybridRetriever.retrieve()`

**Problem**: The code looks for `chunk.embedding` (singular) but the actual attribute is `chunk.embeddings` (plural):

```python
# Line 180 in hybrid_retriever.py
chunk_embedding = getattr(chunk, "embedding", None)  # WRONG: should be "embeddings"
```

This causes `chunk_embedding` to always be `None`, triggering the fallback to `semantic_score = 0.0`.

**Evidence**:
```python
>>> hasattr(chunk, 'embedding')
False
>>> hasattr(chunk, 'embeddings')
True
>>> isinstance(chunk.embeddings, bytes)
True
```

**Fix Required**: Change `getattr(chunk, "embedding", None)` to `getattr(chunk, "embeddings", None)`.

---

### Bug 3: Normalization Edge Case (MODERATE)

**Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`, lines 306-325
**Function**: `HybridRetriever._normalize_scores()`

**Problem**: When all input scores are equal (e.g., all 0.0), the function returns `[1.0, 1.0, 1.0, ...]` instead of preserving the original scores:

```python
def _normalize_scores(self, scores: list[float]) -> list[float]:
    if max_score - min_score < 1e-9:
        # All scores equal, return uniform distribution
        return [1.0] * len(scores)  # BUG: Should preserve original scores
```

This masks the underlying data issues by showing 1.0 for all scores.

**Evidence**:
```python
>>> retriever._normalize_scores([0.5, 0.5, 0.5])
[1.0, 1.0, 1.0]  # Expected: [0.5, 0.5, 0.5]

>>> retriever._normalize_scores([0.0, 0.0, 0.0])
[1.0, 1.0, 1.0]  # Expected: [0.0, 0.0, 0.0]
```

**Fix Required**: When all scores are equal, return the original scores unchanged.

---

## Evidence from Hypothesis Investigation

### Hypothesis 1: Activation Tracking - PARTIALLY CONFIRMED

**Database Has Varied BLA Values** (NOT the root cause):
```
Distinct base_level values: 229
Base level distribution:
  base_level=-6.639629714053534: count=6
  base_level=0.0: count=5
  base_level=-5.531816926660755: count=5
```

**Git BLA IS Working**: The database shows 229 distinct base_level values, indicating Git BLA initialization works during indexing.

**Bug**: The values are correctly stored in the database but NOT retrieved and attached to chunk objects.

### Hypothesis 2: Semantic Embeddings - NOT THE ROOT CAUSE

**Embeddings Are Different Vectors**:
```
Chunk 1: Sum=-0.2679, Norm=1.0000
Chunk 2: Sum=-0.6886, Norm=1.0000
Cosine similarity between chunks: 0.6346
All embeddings identical: False
```

The embeddings are unique and properly stored. The bug is the attribute name mismatch (`embedding` vs `embeddings`).

### Hypothesis 3: Hybrid Blending - NOT THE ROOT CAUSE

The hybrid blending formula is correct (0.6 * activation + 0.4 * semantic). The issue is that both inputs are 0.0, which then get normalized to 1.0.

### Hypothesis 4: Normalization Bug - CONFIRMED

```python
>>> _normalize_scores([0.0, 0.0, 0.0, 0.0, 0.0])
[1.0, 1.0, 1.0, 1.0, 1.0]  # BUG!
```

---

## Minimal Reproduction Test Case

```python
import sys
sys.path.insert(0, '/home/hamr/PycharmProjects/aurora/packages/cli/src')
sys.path.insert(0, '/home/hamr/PycharmProjects/aurora/packages/core/src')
sys.path.insert(0, '/home/hamr/PycharmProjects/aurora/packages/context-code/src')

from aurora_cli.config import Config
from aurora_core.store import SQLiteStore
from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
from aurora_core.activation import ActivationEngine
from aurora_context_code.semantic import EmbeddingProvider

config = Config()
store = SQLiteStore(config.get_db_path())
engine = ActivationEngine()
provider = EmbeddingProvider()
retriever = HybridRetriever(store, engine, provider)

# Search and observe identical scores
results = retriever.retrieve("activation scoring", top_k=5)
for r in results:
    print(f"activation={r['activation_score']:.4f}, semantic={r['semantic_score']:.4f}, hybrid={r['hybrid_score']:.4f}")
    # Expected: varied scores
    # Actual: all 1.0000
```

---

## Proposed Fix Approach

### Fix 1: Attach Activation Score to Chunk Objects

**File**: `packages/core/src/aurora_core/store/sqlite.py`

1. Modify SQL query in `retrieve_by_activation()` to select `a.base_level`
2. Modify `_deserialize_chunk()` to accept and attach activation score to chunk

```python
# In retrieve_by_activation():
cursor = conn.execute(
    """
    SELECT c.id, c.type, c.content, c.metadata, c.embeddings, c.created_at, c.updated_at,
           a.base_level AS activation
    FROM chunks c
    JOIN activations a ON c.id = a.chunk_id
    ...
    """,
)

# When deserializing:
chunk.activation = row_data.get('activation', 0.0)
```

### Fix 2: Correct Embedding Attribute Name

**File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

Change line 180:
```python
# Before:
chunk_embedding = getattr(chunk, "embedding", None)

# After:
chunk_embedding = getattr(chunk, "embeddings", None)
```

### Fix 3: Fix Normalization Edge Case

**File**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

Change `_normalize_scores()`:
```python
def _normalize_scores(self, scores: list[float]) -> list[float]:
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score - min_score < 1e-9:
        # All scores equal - return original scores unchanged
        return list(scores)  # FIX: preserve original values

    return [(s - min_score) / (max_score - min_score) for s in scores]
```

---

## Testing Strategy

1. **Unit Tests**: Test `_normalize_scores()` edge cases
2. **Integration Tests**: Test `retrieve_by_activation()` returns chunks with activation attribute
3. **E2E Tests**: Test full search returns varied scores (stddev > 0)

---

## Files to Modify

| File | Change |
|------|--------|
| `packages/core/src/aurora_core/store/sqlite.py` | Add `a.base_level` to SQL query, attach to chunk |
| `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` | Fix attribute name, fix normalization |

---

## Risk Assessment

- **Low Risk**: These are isolated bugs in the scoring pipeline
- **No Database Schema Changes**: Only code changes required
- **Backwards Compatible**: Changes don't affect public API contracts
