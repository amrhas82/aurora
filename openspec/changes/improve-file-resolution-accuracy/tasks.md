# Tasks: Improve File Resolution Accuracy in aur goals

**Total**: 11 tasks across 4 phases
**Agent assignments**: Based on proposal scope
**Estimated effort**: 1-2 weeks

---

## Phase 1: Structural Analysis (3 tasks)

**Goal**: Build dependency graph from indexed metadata

**Agent**: @holistic-architect (design), @full-stack-dev (implementation)

- [ ] 1. Extract import metadata from memory chunks
  - Modify `packages/core/src/aurora_core/store/sqlite.py`
  - Add method `get_import_relations() -> list[tuple[Path, Path]]`
  - Query chunks with import patterns, parse using heuristics
  - Cache results in memory for session
  - **Validation**: Unit test loads imports from test codebase, verifies accuracy

- [ ] 2. Build DependencyGraph data structure
  - Create `packages/cli/src/aurora_cli/planning/structural.py`
  - Implement `DependencyGraph` class with graph operations
  - Methods: `get_importers()`, `get_imports()`, BFS traversal
  - **Validation**: Unit test constructs graph from sample edges, queries neighbors

- [ ] 3. Implement StructuralAnalyzer with file discovery
  - Complete `StructuralAnalyzer` class in `structural.py`
  - Methods: `find_related_files()`, `_find_callers_and_callees()`, etc.
  - Support all change types with type-specific strategies
  - **Validation**: Unit test finds related files for each change type

---

## Phase 2: Change Type Classification (2 tasks)

**Goal**: Classify subgoals by change type for filtering

**Agent**: @full-stack-dev

- [ ] 4. Define ChangeType enum and patterns
  - Create `packages/cli/src/aurora_cli/planning/change_types.py`
  - Define `ChangeType` enum (ADD_FEATURE, REFACTOR, BUG_FIX, TEST, etc.)
  - Define keyword patterns for each type
  - **Validation**: Unit test classifies sample subgoal descriptions

- [ ] 5. Implement ChangeTypeClassifier
  - Complete `ChangeTypeClassifier` class in `change_types.py`
  - Method: `classify(subgoal, goal_context) -> ChangeType`
  - Keyword matching with weighted scoring
  - **Validation**: Unit test classifies 20 sample subgoals, >85% accuracy

---

## Phase 3: Multi-Factor Scoring (3 tasks)

**Goal**: Combine scoring factors with configurable weights

**Agent**: @full-stack-dev

- [ ] 6. Implement MultiFactorScorer
  - Create `packages/cli/src/aurora_cli/planning/scoring.py`
  - Class: `MultiFactorScorer` with configurable weights
  - Method: `score(candidates, subgoal, change_type) -> list[ScoredResolution]`
  - Calculate weighted combination: semantic (40%) + structural (30%) + recency (20%) + type (10%)
  - **Validation**: Unit test scores sample candidates, verifies weight application

- [ ] 7. Add score explanation generation
  - Method: `_explain_score()` in `MultiFactorScorer`
  - Generate human-readable explanation from component scores
  - Examples: "strong keyword match (0.92); structurally related (0.78)"
  - **Validation**: Unit test generates explanations for various score profiles

- [ ] 8. Implement type relevance and recency scoring
  - Methods: `_type_relevance()`, `_recency_score()` in `MultiFactorScorer`
  - Type relevance: prioritize test files for TEST change type, etc.
  - Recency: decay function based on file mtime (1.0 for <7 days, 0.1 for >180 days)
  - **Validation**: Unit test verifies type penalties and recency decay

---

## Phase 4: Integration & Testing (3 tasks)

**Goal**: Integrate into FilePathResolver and validate improvements

**Agent**: @full-stack-dev (integration), @qa-test-architect (testing)

- [ ] 9. Enhance FilePathResolver with new components
  - Modify `packages/cli/src/aurora_cli/planning/memory.py`
  - Update `FilePathResolver.__init__()` to accept new components
  - Rewrite `resolve_for_subgoal()` to use multi-factor analysis
  - Add `_extract_keywords()`, `_merge_candidates()` methods
  - Raise confidence threshold from 0.3 to 0.6
  - **Validation**: Integration test resolves files for sample subgoals

- [ ] 10. Update Goals model and CLI output
  - Modify `packages/cli/src/aurora_cli/planning/models.py`
  - Add `explanation: str` field to `FileResolution`
  - Update `packages/cli/src/aurora_cli/commands/goals.py`
  - Add verbose output showing score explanations
  - **Validation**: Manual test runs `aur goals --verbose`, verifies output

- [ ] 11. Create benchmark suite and measure improvements
  - Create `tests/performance/test_file_resolution_benchmarks.py`
  - Define 20 test cases with known ground truth file resolutions
  - Measure recall (% expected files found) and precision (% false positives)
  - Compare before/after: avg confidence, recall, precision
  - **Success criteria**:
    - Average confidence: 0.35 → >0.60
    - Recall: >80% of expected files found
    - Precision: <20% false positives
  - **Validation**: Benchmark test suite passes all metrics

---

## Dependency Graph

```
Phase 1 (Structural Analysis)
  ├─> Phase 2 (Change Type Classification)
  └─> Phase 3 (Multi-Factor Scoring)
      └─> Phase 4 (Integration & Testing)

Parallelizable:
- Tasks 1-2 (both read-only from memory store)
- Tasks 4-5 (independent from structural work)
- Tasks 6-8 (all in same scoring module)
```

---

## Validation Commands

After each phase:

```bash
# Type checking
mypy packages/cli/src/aurora_cli/planning --strict

# Unit tests (fast)
pytest tests/unit/cli/planning/test_structural.py -v
pytest tests/unit/cli/planning/test_change_types.py -v
pytest tests/unit/cli/planning/test_scoring.py -v
pytest tests/unit/cli/planning/test_memory.py::test_file_path_resolver -v

# Integration tests
pytest tests/integration/test_file_resolution_e2e.py -v

# Benchmarks
pytest tests/performance/test_file_resolution_benchmarks.py -v --benchmark-only

# Coverage check
pytest tests/unit/cli/planning --cov=aurora_cli.planning --cov-report=term-missing

# E2E test (manual)
aur goals "Add OAuth2 authentication" --verbose
```

---

## Example Execution Flow

**Before** (current behavior):
```bash
$ aur goals "Add OAuth2 authentication"
✓ Goals created: 3 subgoals
Files resolved: 2 (avg confidence: 0.35)

Subgoal 1: Implement OAuth2 token validation
  Files (2):
    [0.38] packages/core/src/config.py
    [0.32] packages/api/src/main.py
```

**After** (with multi-factor scoring):
```bash
$ aur goals "Add OAuth2 authentication" --verbose
✓ Goals created: 3 subgoals
Files resolved: 3 (avg confidence: 0.75)

Subgoal 1: Implement OAuth2 token validation
  Change type: add_feature
  Semantic candidates: 12 files
  Structural candidates: 5 files
  After scoring: 3 files (confidence > 0.6)

  Files (3):
    [0.85] packages/core/src/auth/oauth.py
           strong keyword match (0.92); structurally related (0.78); recently modified
    [0.72] packages/core/src/auth/tokens.py
           moderate keyword match (0.65); structurally related (0.88)
    [0.68] packages/api/src/routes/auth.py
           strong keyword match (0.78); general relevance
```

---

## Definition of Done

Each task is complete when:
- [ ] Code written and type-checked (mypy --strict passes)
- [ ] Unit tests added (95%+ coverage for new code)
- [ ] Integration tests where applicable
- [ ] Manual testing performed for user-facing features
- [ ] Code reviewed (self-review checklist)
- [ ] Documentation comments updated (docstrings for public methods)

---

## Testing Checklist

**Unit Tests** (per task):
- [ ] Happy path works
- [ ] Edge cases handled (None, empty, invalid input)
- [ ] Error cases return clear messages
- [ ] Type signatures correct (no `Any` unless justified)

**Integration Tests** (Phase 4):
- [ ] Full workflow: goal → subgoals → file resolution with multi-factor scoring
- [ ] Backward compatibility: existing code using FilePathResolver still works
- [ ] Graceful degradation: structural analysis disabled → semantic-only fallback
- [ ] Performance: file resolution adds <500ms overhead per subgoal

**Benchmark Tests** (Phase 4, Task 11):
- [ ] 20 test cases with ground truth file resolutions
- [ ] Recall: >80% of expected files found
- [ ] Precision: <20% false positives (returned files not in expected set)
- [ ] Average confidence: >0.60 (vs current ~0.35)
- [ ] Performance: <500ms added to `aur goals` total execution time

---

## Risk Mitigation

**Risk: Import metadata not in indexed chunks**
- **Mitigation**: Check schema during task 1, add indexing if needed
- **Fallback**: Parse files on-demand (slower but functional)

**Risk: Graph construction too slow**
- **Mitigation**: Cache graph per session, lazy load only when needed
- **Benchmark**: Measure graph build time, target <200ms for medium codebase

**Risk: Score weights not optimal**
- **Mitigation**: Make weights configurable, document tuning guide
- **Test**: A/B test with 40/30/20/10 vs 50/25/15/10 vs 60/20/15/5 splits

**Risk: False positives increase**
- **Mitigation**: Raise confidence threshold to 0.6, filter aggressively
- **Validation**: Benchmark suite measures precision (<20% false positives)

---

## Success Criteria (from Proposal)

- [ ] Average confidence score increases from ~0.35 to >0.60
- [ ] File resolution recall improves: >80% of relevant files found
- [ ] File resolution precision improves: <20% false positives
- [ ] Users see score explanations in verbose output
- [ ] Performance overhead: <500ms added to `aur goals` execution
- [ ] 95%+ test coverage for new components
- [ ] Benchmark test suite: 20 known goals with ground truth files

---

## Configuration Reference

Add to `packages/cli/src/aurora_cli/config.py`:

```python
@dataclass
class FileResolutionConfig:
    """Configuration for file path resolution."""
    min_confidence: float = 0.6  # Minimum confidence to include file
    max_files_per_subgoal: int = 5  # Limit returned files
    enable_structural_analysis: bool = True  # Toggle structural analysis
    semantic_weight: float = 0.4  # Weight for keyword match score
    structural_weight: float = 0.3  # Weight for graph-based score
    recency_weight: float = 0.2  # Weight for file modification recency
    type_relevance_weight: float = 0.1  # Weight for change type relevance
```

Users can override via:
```bash
aur goals "Add feature" --file-resolution-min-confidence 0.5
```

or in `.aurora/config.json`:
```json
{
  "file_resolution": {
    "min_confidence": 0.5,
    "semantic_weight": 0.5,
    "structural_weight": 0.25
  }
}
```
