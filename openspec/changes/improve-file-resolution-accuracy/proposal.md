# Proposal: Improve File Resolution Accuracy in aur goals

## Change ID
`improve-file-resolution-accuracy`

## Summary
Enhance the accuracy of file path resolution during `aur goals` decomposition by improving the `FilePathResolver` logic, adding semantic + structural analysis, and providing better context to users about which files are relevant for each subgoal.

## Problem Statement

Currently, `aur goals` can decompose goals into subgoals and match agents, but file resolution is less accurate:

1. **Low relevance scores**: `FilePathResolver` often returns files with low confidence (<0.5)
2. **Missing context**: No structural analysis (imports, dependencies, call graphs)
3. **Generic fallbacks**: When memory search fails, returns generic paths like "src/{keyword}.py"
4. **No file ranking**: Results not ranked by actual relevance to change type
5. **Limited feedback**: Users don't see why specific files were chosen

**Example current behavior**:
```bash
$ aur goals "Add OAuth2 authentication"
✓ Goals created with 3 subgoals
Files resolved: 2 (avg confidence: 0.35)  # Low confidence!
```

**Current code** (`packages/cli/src/aurora_cli/planning/memory.py:223-242`):
```python
def resolve_for_subgoal(self, subgoal: Subgoal, limit: int = 5) -> list[FileResolution]:
    # Simple keyword search from memory
    chunks = self.retriever.retrieve(subgoal.description, limit=limit)
    # No structural analysis, no dependency tracking
```

## Proposed Solution

Improve file resolution accuracy through multi-layered analysis:

### 1. Enhanced Semantic Search
- Use subgoal keywords + goal context (not just subgoal description)
- Boost scores for files with matching function/class names
- Penalize test files unless subgoal is about testing

### 2. Structural Analysis (New)
- **Import tracking**: Files that import relevant modules score higher
- **Call graph analysis**: Functions called by identified files
- **Dependency detection**: Files in same directory/package

### 3. Change Type Classification (New)
- Classify subgoals: "add feature", "refactor", "bug fix", "test"
- Apply type-specific file filters:
  - "add feature" → prioritize similar existing features
  - "refactor" → include callers and callees
  - "bug fix" → focus on error-prone files
  - "test" → prioritize test files

### 4. Confidence Scoring Improvements
- Multi-factor scoring: keyword match (40%) + structural (30%) + recency (20%) + type relevance (10%)
- Require minimum 0.6 confidence (vs current 0.3)
- Explain score breakdown to users

### Architecture

```
Current Flow:
subgoal description → memory keyword search → ranked files

Improved Flow:
subgoal + goal context → [Semantic Search] → candidate files
                       ↓
         [Structural Analyzer] → import/call graph → related files
                       ↓
         [Change Type Classifier] → filter by type → scored files
                       ↓
         [Multi-Factor Scorer] → combined score → ranked results (>0.6)
```

## Benefits

1. **Higher accuracy**: Multi-factor scoring reduces false positives
2. **Better coverage**: Structural analysis finds related files missed by keywords
3. **User confidence**: Transparency in scoring builds trust
4. **Reduced manual work**: Fewer files to review means faster planning

## Scope

### In Scope
- Enhanced FilePathResolver with multi-factor scoring
- New StructuralAnalyzer for import/call graph analysis
- Change type classification for subgoals
- Improved confidence thresholds and explanations
- Unit + integration tests for file resolution accuracy

### Out of Scope
- Real-time code parsing (use indexed metadata only)
- Cross-language dependency analysis (Python only for v1)
- Interactive file selection UI
- Machine learning-based scoring (rule-based for now)

## Dependencies

**Existing Systems**:
- `packages/cli/src/aurora_cli/planning/memory.py` - FilePathResolver (to enhance)
- `packages/cli/src/aurora_cli/memory/retrieval.py` - MemoryRetriever
- `packages/core/src/aurora_core/store/sqlite.py` - SQLiteStore (chunk metadata)
- Tree-sitter parsing (already used during indexing)

**New Components**:
- `packages/cli/src/aurora_cli/planning/structural.py` - StructuralAnalyzer
- `packages/cli/src/aurora_cli/planning/change_types.py` - ChangeTypeClassifier
- `packages/cli/src/aurora_cli/planning/scoring.py` - MultiFactorScorer

## Implementation Strategy

### Phase 1: Structural Analysis (3 tasks)
Extract import/dependency metadata from indexed chunks, build file relationship graph.

### Phase 2: Change Type Classification (2 tasks)
Classify subgoals by change type, define type-specific file filters.

### Phase 3: Multi-Factor Scoring (3 tasks)
Implement combined scoring algorithm, adjust confidence thresholds, add score explanations.

### Phase 4: Integration & Testing (3 tasks)
Integrate into FilePathResolver, comprehensive tests, benchmark accuracy improvements.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Performance overhead** | Medium | Cache structural analysis results, lazy load graphs |
| **Complexity** | Medium | Start with Python-only, simple heuristics |
| **False negatives** | Low | Keep keyword fallback, allow manual file addition |
| **Accuracy measurement** | Low | Create test suite with known file-to-subgoal mappings |

## Success Criteria

- [ ] Average confidence score increases from ~0.35 to >0.60
- [ ] File resolution recall improves: >80% of relevant files found
- [ ] File resolution precision improves: <20% false positives
- [ ] Users see score explanations in verbose output
- [ ] Performance overhead: <500ms added to `aur goals` execution
- [ ] 95%+ test coverage for new components
- [ ] Benchmark test suite: 20 known goals with ground truth files

## Open Questions

1. **Import metadata**: Is import information already in indexed chunks?
   - **Investigation needed**: Check SQLiteStore schema for import data

2. **Change type keywords**: What keywords define each type?
   - **Recommendation**: Start simple (add/create/implement, refactor/restructure, fix/bug, test)

3. **Score weights**: What balance for semantic vs structural?
   - **Recommendation**: A/B test with 40/30 vs 50/25 vs 60/20 splits

4. **Cross-language support**: Priority for JS/TS/Go?
   - **Recommendation**: Ship Python-only v1, add languages in v2

## Alternatives Considered

### Alternative 1: Machine Learning-Based Scoring
**Pros**: Could learn patterns from past successful resolutions
**Cons**: Requires training data, adds complexity, harder to explain
**Why rejected**: Rule-based approach is more transparent and maintainable

### Alternative 2: Full AST Analysis at Query Time
**Pros**: Most accurate structural information
**Cons**: Too slow (would add 5-10s to every goal command)
**Why rejected**: Performance unacceptable

### Alternative 3: Manual File Selection UI
**Pros**: Users have full control
**Cons**: Breaks automation, adds friction
**Why rejected**: Defeats purpose of "aur goals" automation

**Our approach**: Enhance existing automated resolution with better heuristics, keep it fast.

## Related Changes

- Complements existing memory indexing (no changes to indexing)
- Builds on agent gap detection (similar confidence scoring patterns)
- Enables future: file-aware task generation in `/plan`
