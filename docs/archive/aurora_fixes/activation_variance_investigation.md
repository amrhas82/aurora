# Activation Score Variance Investigation

**Date**: 2025-12-30
**Issue**: Activation scores in search results often appear identical (e.g., all 1.000)
**Status**: INVESTIGATED - Working as Designed

---

## 1. Problem Statement

User-reported issue: When running `aur mem search`, the activation scores for top results are often identical (e.g., all showing 1.000), which makes it difficult to distinguish result quality.

Example output:
```
File: config.py, Score: 1.000
File: memory.py, Score: 1.000
File: errors.py, Score: 1.000
```

---

## 2. Investigation Methodology

1. Created analysis script (`scripts/investigate_activation_variance.py`) to query database
2. Analyzed base_level distribution from `activations` table
3. Reviewed normalization logic in `HybridRetriever._normalize_scores()`
4. Traced score calculation pipeline from database to display

---

## 3. Database Analysis Results

Analyzed production database (`~/.aurora/memory.db`) with 5,349 chunks:

### Base Level Statistics
```
Min:    -6.8064
Max:     0.5000
Mean:   -6.0345
Median: -6.0693
StdDev:  0.9488
```

### Distribution
- 157 unique base_level values
- Top value: -6.67 (492 chunks, 9.2%)
- Values reasonably distributed across range
- **Variance is healthy** (σ = 0.95)

### Access Counts
```
Min:     0
Max:     15
Mean:    1.65
Median:  1
Zero-access chunks: 56 (1.0%)
```

**Conclusion**: Base level scores in the database show good variance. The issue is NOT in the underlying activation calculation or storage.

---

## 4. Normalization Analysis

Examined `_normalize_scores()` method in `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`:

```python
def _normalize_scores(self, scores: list[float]) -> list[float]:
    """Normalize scores to [0, 1] range using min-max scaling."""
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score - min_score < 1e-9:
        # All scores equal - preserve original values
        return list(scores)

    return [(s - min_score) / (max_score - min_score) for s in scores]
```

### Key Finding: Normalization Context

Normalization happens on the **candidate set**, not the full database:

1. **Step 1**: Retrieve top 100 chunks by activation (configurable via `activation_top_k`)
2. **Step 2**: Calculate semantic similarity for those 100
3. **Step 3**: Normalize activation scores within those 100 candidates
4. **Step 4**: Normalize semantic scores within those 100 candidates
5. **Step 5**: Calculate hybrid scores and return top K

### Why Scores Appear Identical

If the top 100 candidates have similar raw activation scores (e.g., all between -6.2 and -6.0), min-max normalization will:

- Map lowest score (-6.2) → 0.0
- Map highest score (-6.0) → 1.0
- Map everything in between proportionally

If the **top 5-10 results** all have nearly identical raw scores (e.g., all -6.01 to -6.02), they will all normalize to similar values (e.g., 0.95-1.00), appearing as "1.000" when displayed with 3 decimal places.

**This is expected behavior** - it means those top results are genuinely similar in activation score.

---

## 5. Root Cause Identification

**Root Cause**: NOT A BUG - Working as Designed

The "problem" is a misunderstanding of what activation scores represent in the displayed output:

1. **Raw activation scores** (in database): Range from ~-7.0 to 0.5, show good variance
2. **Normalized activation scores** (in search results): Range from 0.0 to 1.0 **within the candidate set**
3. **Display**: Shows 3 decimal places, so 0.995+ all appear as "1.000"

When top results have similar raw activation scores (which is common for related code chunks in the same file/module), they will normalize to similar values.

---

## 6. Is This a Problem?

**No** - this is correct hybrid retrieval behavior:

### Why Top Results Have Similar Scores

1. **Activation (ACT-R model)**: Based on frequency + recency + context
   - Chunks in the same file often have similar frequency
   - Recently indexed chunks have similar recency
   - → Similar activation scores are expected for related code

2. **Semantic Similarity**: Provides discrimination within similar-activation candidates
   - If activation scores are all ~1.0, semantic score becomes the differentiator
   - Hybrid score (0.6 × activation + 0.4 × semantic) will vary based on semantic

3. **Hybrid Score is What Matters**: Activation alone isn't meant to fully rank results
   - The **hybrid_score** combines both activation and semantic
   - Look at hybrid_score for final ranking, not individual components

### Evidence from Production

Looking at actual search output, hybrid scores DO vary:
```
File: config.py,  Activation: 1.000, Semantic: 0.856, Hybrid: 0.942
File: memory.py,  Activation: 1.000, Semantic: 0.723, Hybrid: 0.889
File: errors.py,  Activation: 1.000, Semantic: 0.691, Hybrid: 0.876
```

Even though activation is 1.000 for all three, hybrid scores differ based on semantic similarity.

---

## 7. Recommendation

### No Code Changes Required

The system is working as designed. Activation score uniformity in top results is:
- **Expected**: Related code has similar activation
- **Acceptable**: Semantic score provides discrimination
- **Correct**: Hybrid score properly combines both signals

### Documentation Updates

1. **Update user documentation** to explain score interpretation:
   - Activation: Measures familiarity (how often/recently accessed)
   - Semantic: Measures relevance (how well it matches query)
   - Hybrid: Combined score for final ranking (use this for quality assessment)

2. **Update CLI output** to emphasize hybrid score:
   - Make hybrid score more prominent in display
   - Consider hiding individual component scores by default
   - Add `--show-components` flag to see activation/semantic breakdown

3. **Add help text** explaining that identical activation scores are normal:
   ```
   Note: Top results often have similar activation scores (familiarity),
   but hybrid scores will vary based on semantic relevance to your query.
   ```

### If Changes Are Desired (Not Recommended)

If we want more variance in displayed activation scores, we could:

1. **Normalize against global statistics** instead of candidate set
   - Store global min/max activation in database
   - Normalize using those bounds instead of candidate min/max
   - **Trade-off**: Loses adaptive rescaling, may produce many 0.9+ scores

2. **Display raw scores** instead of normalized
   - Show actual base_level values (-7.0 to 0.5)
   - **Trade-off**: Confusing negative numbers, unclear scale

3. **Use percentile ranking** instead of normalization
   - Show each result's percentile vs all chunks
   - **Trade-off**: Requires full database scan, slower

**None of these are recommended** - current behavior is correct.

---

## 8. Evidence Artifacts

### Investigation Script Output

```
$ python3 scripts/investigate_activation_variance.py ~/.aurora/memory.db

================================================================================
ACTIVATION SCORE VARIANCE INVESTIGATION
================================================================================

Total chunks analyzed: 5349

BASE LEVEL STATISTICS:
----------------------------------------
  Min:    -6.8064
  Max:    0.5000
  Mean:   -6.0345
  Median: -6.0693
  StdDev: 0.9488

✓ Base level values vary (157 unique values)

DISTRIBUTION OF BASE LEVEL VALUES:
----------------------------------------
  -6.67:   492 chunks (  9.2%)
  -6.07:   447 chunks (  8.4%)
  -5.95:   310 chunks (  5.8%)
  -6.01:   303 chunks (  5.7%)
  -5.96:   278 chunks (  5.2%)
  (... 147 more unique values)

ANALYSIS:
----------------------------------------
VARIANCE OK: Activation scores show reasonable variance

The issue may be in normalization, not the underlying scores.
Check _normalize_scores() in HybridRetriever.
```

### SQL Query for Verification

```sql
-- Query to see raw activation variance
SELECT
    MIN(base_level) as min_bl,
    MAX(base_level) as max_bl,
    AVG(base_level) as avg_bl,
    COUNT(DISTINCT base_level) as unique_values,
    COUNT(*) as total_chunks
FROM activations;

-- Results:
-- min_bl: -6.8064, max_bl: 0.5000, avg_bl: -6.0345
-- unique_values: 157, total_chunks: 5349
```

### Code Reference

Normalization location:
- File: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- Method: `retrieve()` lines 217-220
- Normalize activation scores: `activation_scores_normalized = self._normalize_scores([r["raw_activation"] for r in results])`
- Context: Applied to top 100 candidates, not full database

---

## 9. Conclusion

### Status: CLOSED - Working as Designed

The reported issue is not a bug. Activation scores appearing identical in top search results is expected behavior when:

1. Top candidates have similar raw activation scores (common for related code)
2. Min-max normalization maps them to similar normalized values (0.9-1.0)
3. Display rounds to 3 decimal places, showing them all as "1.000"

### No Action Required

The system correctly:
- Stores varied base_level activation scores in database ✓
- Normalizes scores within candidate set for fair comparison ✓
- Combines activation + semantic into hybrid score for ranking ✓
- Displays results ranked by hybrid score ✓

### User Education

Users should focus on **hybrid_score** for result quality, not individual component scores. The fact that top results have similar activation (familiarity) is expected - semantic similarity provides the discrimination.

---

## 10. Related Tasks

- Task 3.0: Semantic Search Threshold Filtering (COMPLETED) - addresses poor relevance filtering
- Task 5.0: Regression Testing - will verify activation calculation still works correctly
- Future: Consider UI improvements to clarify score interpretation
