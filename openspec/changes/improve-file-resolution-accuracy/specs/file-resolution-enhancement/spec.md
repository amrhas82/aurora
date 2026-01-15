# Spec: File Resolution Enhancement

## MODIFIED Requirements

### Requirement: FilePathResolver Enhancement

The system SHALL enhance FilePathResolver to use multi-factor analysis combining semantic, structural, recency, and type relevance scoring.

**Enhanced Interface**:
```python
class FilePathResolver:
    def __init__(
        self,
        retriever: MemoryRetriever,
        structural_analyzer: StructuralAnalyzer | None = None,
        change_classifier: ChangeTypeClassifier | None = None,
        scorer: MultiFactorScorer | None = None,
        config: FileResolutionConfig | None = None
    ):

    def resolve_for_subgoal(
        self,
        subgoal: Subgoal,
        goal_context: str = "",
        limit: int = 5
    ) -> list[FileResolution]:
```

#### Scenario: Multi-phase resolution workflow
- **WHEN** resolving files for subgoal
- **THEN** classify change type
- **AND** perform enhanced semantic search with keywords
- **AND** perform structural analysis (if enabled)
- **AND** merge semantic and structural candidates
- **AND** compute recency scores
- **AND** apply multi-factor scoring
- **AND** filter by confidence threshold (>0.6)
- **AND** sort and limit results

#### Scenario: Backward compatibility maintained
- **WHEN** FilePathResolver initialized with only MemoryRetriever
- **THEN** create default components automatically
- **AND** existing code continues to work

#### Scenario: goal_context improves keyword extraction
- **WHEN** subgoal is "Implement validation"
- **AND** goal_context is "Add OAuth2 authentication"
- **THEN** extract keywords from both sources
- **AND** improve semantic search relevance

---

## ADDED Requirements

### Requirement: Enhanced Keyword Extraction

The system SHALL extract keywords from subgoal description and goal context for improved semantic search.

#### Scenario: Keywords extracted from subgoal and context
- **WHEN** subgoal is "Implement token validation"
- **AND** goal_context is "Add OAuth2 authentication"
- **THEN** extract ["implement", "token", "validation", "oauth2", "authentication"]

#### Scenario: Stopwords filtered out
- **WHEN** text contains "the", "and", "or", "with"
- **THEN** filter out stopwords
- **AND** keep only meaningful terms (length > 3)

#### Scenario: Duplicates removed
- **WHEN** "authentication" appears in both subgoal and context
- **THEN** include "authentication" only once
- **AND** preserve order of first appearance

---

### Requirement: Candidate Merging

The system SHALL merge semantic and structural results into unified candidate set with component scores.

#### Scenario: File in both semantic and structural results
- **WHEN** file "auth/oauth.py" in semantic results (score 0.8)
- **AND** same file in structural results (score 0.6)
- **THEN** create candidate with semantic_score=0.8, structural_score=0.6

#### Scenario: File only in semantic results
- **WHEN** file "api/routes.py" in semantic results only
- **THEN** create candidate with semantic_score, structural_score=0.0

#### Scenario: File only in structural results
- **WHEN** file "auth/tokens.py" in structural results only
- **THEN** create candidate with structural_score, semantic_score=0.0

---

### Requirement: Recency Score Computation

The system SHALL compute recency scores from file modification times for all candidates.

#### Scenario: Recency computed for each candidate
- **WHEN** candidate has no recency_score
- **THEN** stat file for mtime
- **AND** compute recency score using decay function
- **AND** populate candidate.recency_score

#### Scenario: Batch recency computation
- **WHEN** processing multiple candidates
- **THEN** compute recency for all candidates before scoring
- **AND** handle missing files gracefully (default 0.5)

---

## MODIFIED Requirements

### Requirement: FileResolution Data Model

The system SHALL include explanation field in FileResolution for score transparency.

**Updated Model**:
```python
@dataclass
class FileResolution:
    path: str
    confidence: float
    explanation: str = ""  # NEW FIELD
```

#### Scenario: Explanation populated in results
- **WHEN** file resolution created
- **THEN** path is file path
- **AND** confidence is combined score
- **AND** explanation describes score components

---

## ADDED Requirements

### Requirement: Configuration

The system SHALL provide FileResolutionConfig for tuning resolution behavior.

**Config Structure**:
```python
@dataclass
class FileResolutionConfig:
    min_confidence: float = 0.6
    max_files_per_subgoal: int = 5
    enable_structural_analysis: bool = True
    semantic_weight: float = 0.4
    structural_weight: float = 0.3
    recency_weight: float = 0.2
    type_relevance_weight: float = 0.1
```

#### Scenario: Default configuration applied
- **WHEN** no config provided
- **THEN** use min_confidence=0.6 (raised from 0.3)
- **AND** enable_structural_analysis=True
- **AND** default weights (0.4, 0.3, 0.2, 0.1)

#### Scenario: User overrides min_confidence
- **WHEN** config specifies min_confidence=0.5
- **THEN** filter files with confidence >= 0.5
- **AND** more files included (lower threshold)

#### Scenario: Structural analysis disabled
- **WHEN** config specifies enable_structural_analysis=False
- **THEN** skip structural analysis phase
- **AND** fall back to semantic-only resolution

---

### Requirement: CLI Integration

The system SHALL integrate enhanced file resolution into `aur goals` command with verbose output option.

#### Scenario: Normal output shows file count
- **WHEN** running `aur goals "Add feature"`
- **THEN** display "Files resolved: 8 (avg confidence: 0.72)"
- **AND** list files with confidence scores

#### Scenario: Verbose output shows analysis details
- **WHEN** running `aur goals "Add feature" --verbose`
- **THEN** display change type detected
- **AND** display keywords extracted
- **AND** display semantic and structural candidate counts
- **AND** display files with confidence and explanations

#### Scenario: goals.json includes explanations
- **WHEN** goals.json written
- **THEN** each file includes path, confidence, explanation
- **AND** JSON structure preserves all metadata

---

### Requirement: Performance Targets

The system SHALL meet performance targets for enhanced file resolution.

#### Scenario: Total resolution time per subgoal
- **WHEN** resolving files for one subgoal
- **THEN** complete all phases in <500ms

#### Scenario: Graph construction overhead
- **WHEN** building dependency graph for medium codebase (5000 files)
- **THEN** complete in <200ms

#### Scenario: Scoring overhead
- **WHEN** scoring 50 candidate files
- **THEN** complete in <10ms

#### Scenario: Memory overhead acceptable
- **WHEN** graph cached in memory
- **THEN** overhead is <50MB

---

### Requirement: Backward Compatibility

The system SHALL maintain backward compatibility with existing FilePathResolver usage.

#### Scenario: Existing initialization works
- **WHEN** code calls FilePathResolver(retriever)
- **THEN** initialize successfully with defaults
- **AND** no code changes required

#### Scenario: Existing API calls work
- **WHEN** code calls resolve_for_subgoal(subgoal)
- **THEN** resolve files successfully
- **AND** goal_context defaults to empty string

#### Scenario: Old tests pass
- **WHEN** running existing test suite
- **THEN** all tests pass without modification

---

### Requirement: Graceful Degradation

The system SHALL gracefully degrade when components fail or are unavailable.

#### Scenario: Memory retriever returns empty
- **WHEN** semantic search returns no results
- **THEN** try with broader keywords
- **AND** if still empty, return empty list with warning

#### Scenario: Structural analyzer fails
- **WHEN** graph construction fails
- **THEN** disable structural analysis for session
- **AND** log warning
- **AND** fall back to semantic-only resolution

#### Scenario: File not found during recency
- **WHEN** file deleted since indexing
- **THEN** filter out from candidates
- **AND** log warning for debugging

---

### Requirement: Confidence Threshold Improvement

The system SHALL improve file resolution precision by raising confidence threshold from 0.3 to 0.6.

#### Scenario: Fewer files with higher precision
- **WHEN** using threshold 0.6
- **THEN** return fewer files than threshold 0.3
- **AND** reduce false positives
- **AND** improve precision to <20% false positive rate

#### Scenario: Recall maintained above 80%
- **WHEN** using threshold 0.6
- **THEN** still find >80% of relevant files
- **AND** balance precision vs recall

---

### Requirement: Success Metrics

The system SHALL achieve measurable improvements in file resolution accuracy.

#### Scenario: Average confidence improvement
- **WHEN** comparing before and after enhancement
- **THEN** average confidence increases from 0.35 to >0.60

#### Scenario: Recall improvement
- **WHEN** testing with benchmark suite (20 known goals)
- **THEN** recall (% relevant files found) is >80%

#### Scenario: Precision improvement
- **WHEN** testing with benchmark suite
- **THEN** precision (<20% false positives) achieved

#### Scenario: User-visible score explanations
- **WHEN** running aur goals --verbose
- **THEN** users see why each file was scored as relevant
- **AND** explanations are clear and actionable
