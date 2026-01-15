# Spec: Multi-Factor Scoring

## ADDED Requirements

### Requirement: MultiFactorScorer Configuration

The system SHALL initialize MultiFactorScorer with configurable weights for each scoring component.

**Interface**:
```python
class MultiFactorScorer:
    def __init__(
        self,
        semantic_weight: float = 0.4,
        structural_weight: float = 0.3,
        recency_weight: float = 0.2,
        type_relevance_weight: float = 0.1
    ):
```

#### Scenario: Default weights sum to 1.0
- **WHEN** MultiFactorScorer initialized with default weights
- **THEN** semantic_weight is 0.4
- **AND** structural_weight is 0.3
- **AND** recency_weight is 0.2
- **AND** type_relevance_weight is 0.1
- **AND** weights sum to 1.0

#### Scenario: Custom weights provided
- **WHEN** initializing with custom weights (0.5, 0.3, 0.15, 0.05)
- **THEN** use provided weights for scoring

---

### Requirement: Combined Score Calculation

The system SHALL calculate combined confidence score using weighted sum of component scores.

**Formula**: `confidence = semantic_weight * semantic_score + structural_weight * structural_score + recency_weight * recency_score + type_relevance_weight * type_relevance_score`

#### Scenario: High confidence from all factors
- **WHEN** semantic_score is 0.9, structural_score is 0.8, recency_score is 1.0, type_relevance is 1.0
- **AND** using default weights (0.4, 0.3, 0.2, 0.1)
- **THEN** confidence is 0.4*0.9 + 0.3*0.8 + 0.2*1.0 + 0.1*1.0 = 0.9

#### Scenario: Moderate confidence with mixed scores
- **WHEN** semantic_score is 0.6, structural_score is 0.5, recency_score is 0.3, type_relevance is 1.0
- **AND** using default weights
- **THEN** confidence is 0.4*0.6 + 0.3*0.5 + 0.2*0.3 + 0.1*1.0 = 0.55

#### Scenario: Low confidence filtered out
- **WHEN** combined confidence is 0.45
- **AND** min_confidence threshold is 0.6
- **THEN** file is excluded from results

---

### Requirement: Semantic Score Component

The system SHALL use semantic scores from memory retriever based on keyword matching quality.

#### Scenario: Strong keyword match (0.7-1.0)
- **WHEN** memory retriever returns score 0.92
- **THEN** semantic_score is 0.92
- **AND** contributes 0.92 * 0.4 = 0.368 to combined score

#### Scenario: Moderate keyword match (0.4-0.7)
- **WHEN** memory retriever returns score 0.65
- **THEN** semantic_score is 0.65
- **AND** contributes 0.65 * 0.4 = 0.26 to combined score

#### Scenario: Weak keyword match (0.0-0.4)
- **WHEN** memory retriever returns score 0.35
- **THEN** semantic_score is 0.35
- **AND** contributes 0.35 * 0.4 = 0.14 to combined score

---

### Requirement: Structural Score Component

The system SHALL use structural scores from dependency graph traversal.

#### Scenario: Seed file (distance 0)
- **WHEN** file is in seed_files
- **THEN** structural_score is 1.0
- **AND** contributes 1.0 * 0.3 = 0.3 to combined score

#### Scenario: Direct dependency (distance 1)
- **WHEN** file is 1 hop from seed with max_depth=2
- **THEN** structural_score is 0.5
- **AND** contributes 0.5 * 0.3 = 0.15 to combined score

#### Scenario: No structural relationship
- **WHEN** file not found in dependency graph
- **THEN** structural_score is 0.0
- **AND** contributes 0.0 to combined score

---

### Requirement: Recency Score Component

The system SHALL calculate recency scores using file modification time decay function.

**Decay Function**:
- age ≤ 7 days → 1.0
- age ≤ 30 days → 0.8
- age ≤ 90 days → 0.5
- age ≤ 180 days → 0.3
- age > 180 days → 0.1

#### Scenario: Recently modified file (last week)
- **WHEN** file modified 5 days ago
- **THEN** recency_score is 1.0
- **AND** contributes 1.0 * 0.2 = 0.2 to combined score

#### Scenario: Moderately recent file (last month)
- **WHEN** file modified 20 days ago
- **THEN** recency_score is 0.8
- **AND** contributes 0.8 * 0.2 = 0.16 to combined score

#### Scenario: Old file (over 6 months)
- **WHEN** file modified 200 days ago
- **THEN** recency_score is 0.1
- **AND** contributes 0.1 * 0.2 = 0.02 to combined score

#### Scenario: File not found fallback
- **WHEN** file stat fails (FileNotFoundError)
- **THEN** recency_score defaults to 0.5 (neutral)

---

### Requirement: Type Relevance Score Component

The system SHALL calculate type relevance based on file type matching change type.

#### Scenario: TEST change with test file
- **WHEN** change_type is TEST
- **AND** file matches test patterns (test_*.py, *_test.py, tests/)
- **THEN** type_relevance_score is 1.0

#### Scenario: TEST change with non-test file
- **WHEN** change_type is TEST
- **AND** file is source file (not test)
- **THEN** type_relevance_score is 0.3

#### Scenario: DOCUMENTATION change with doc file
- **WHEN** change_type is DOCUMENTATION
- **AND** file is .md, .rst, or .txt
- **THEN** type_relevance_score is 1.0

#### Scenario: DOCUMENTATION change with code file
- **WHEN** change_type is DOCUMENTATION
- **AND** file is .py, .js, etc.
- **THEN** type_relevance_score is 0.2

#### Scenario: BUG_FIX change with test file
- **WHEN** change_type is BUG_FIX
- **AND** file is test file
- **THEN** type_relevance_score is 0.5 (penalty)

#### Scenario: BUG_FIX change with source file
- **WHEN** change_type is BUG_FIX
- **AND** file is source file
- **THEN** type_relevance_score is 1.0

#### Scenario: ADD_FEATURE or REFACTOR (no penalty)
- **WHEN** change_type is ADD_FEATURE or REFACTOR
- **THEN** type_relevance_score is 1.0 for any file type

---

### Requirement: Score Explanation Generation

The system SHALL generate human-readable explanations for confidence scores.

**Format**: Semicolon-separated factors contributing to score

#### Scenario: Strong semantic and structural
- **WHEN** semantic_score is 0.92, structural_score is 0.78
- **THEN** explanation includes "strong keyword match (0.92); structurally related (0.78)"

#### Scenario: Moderate semantic only
- **WHEN** semantic_score is 0.65, structural_score is 0.0
- **THEN** explanation includes "moderate keyword match (0.65)"

#### Scenario: Recently modified added
- **WHEN** recency_score is 0.9
- **THEN** explanation includes "recently modified"

#### Scenario: Type penalty noted
- **WHEN** type_relevance_score is 0.3
- **THEN** explanation includes "lower type relevance"

#### Scenario: General relevance fallback
- **WHEN** no strong factors present
- **THEN** explanation is "general relevance"

---

### Requirement: Confidence Threshold Filtering

The system SHALL filter files by minimum confidence threshold before returning results.

#### Scenario: File above threshold included
- **WHEN** file confidence is 0.75
- **AND** min_confidence is 0.6
- **THEN** file is included in results

#### Scenario: File below threshold excluded
- **WHEN** file confidence is 0.55
- **AND** min_confidence is 0.6
- **THEN** file is excluded from results

#### Scenario: Threshold raised from 0.3 to 0.6
- **WHEN** using new threshold of 0.6
- **THEN** fewer files returned (better precision)
- **AND** false positives reduced

---

### Requirement: Candidate Merging

The system SHALL merge semantic and structural results into unified candidate set.

#### Scenario: File in both semantic and structural
- **WHEN** file appears in semantic results with score 0.8
- **AND** file appears in structural results with score 0.6
- **THEN** candidate has both scores populated
- **AND** combined score uses both components

#### Scenario: File only in semantic results
- **WHEN** file in semantic results with score 0.7
- **AND** file not in structural results
- **THEN** candidate has semantic_score=0.7, structural_score=0.0

#### Scenario: File only in structural results
- **WHEN** file in structural results with score 0.9
- **AND** file not in semantic results
- **THEN** candidate has semantic_score=0.0, structural_score=0.9

---

### Requirement: Performance Targets

The system SHALL meet performance targets for scoring operations.

#### Scenario: Scoring time per subgoal
- **WHEN** scoring 50 candidate files
- **THEN** complete in <10ms

#### Scenario: Memory overhead
- **WHEN** candidate set has 50 files
- **THEN** memory usage is <1KB

---

### Requirement: Weight Normalization

The system SHALL normalize weights if they don't sum to 1.0 and log warnings for unusual configurations.

#### Scenario: Weights auto-normalized
- **WHEN** weights provided are (0.5, 0.5, 0.5, 0.5) sum=2.0
- **THEN** normalize to (0.25, 0.25, 0.25, 0.25) sum=1.0
- **AND** log warning about normalization

#### Scenario: All zero weights
- **WHEN** weights are (0.0, 0.0, 0.0, 0.0)
- **THEN** log error
- **AND** use default weights (0.4, 0.3, 0.2, 0.1)

---

### Requirement: Error Handling

The system SHALL handle missing scores and file errors gracefully.

#### Scenario: Missing semantic score
- **WHEN** semantic_score not provided
- **THEN** default to 0.0

#### Scenario: Missing structural score
- **WHEN** structural_score not provided
- **THEN** default to 0.0

#### Scenario: Recency calculation fails
- **WHEN** cannot stat file for mtime
- **THEN** default recency_score to 0.5 (neutral)

#### Scenario: File deleted since indexing
- **WHEN** file no longer exists
- **THEN** skip from candidates
- **AND** do not include in results
