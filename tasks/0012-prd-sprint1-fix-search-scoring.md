# Product Requirements Document: Sprint 1 - Fix Search Scoring

**Document ID**: PRD-SPRINT1-001
**Date**: 2025-12-29
**Status**: Ready for Implementation
**Target Audience**: Agent Executor
**Sprint Duration**: 1-2 days (8-16 hours)
**Priority**: CRITICAL (P1)

---

## 1. Introduction/Overview

### Problem Statement

The Aurora CLI `aur mem search` command returns search results with completely broken scoring. All score types (activation, semantic, and hybrid) consistently return 1.000 regardless of query relevance, making search ranking meaningless and preventing users from identifying the most relevant results.

**IMPORTANT**: Activation scoring has TWO components that must both work:
1. **Git-Based BLA Initialization** - Provides initial activation values during indexing based on commit history (FUNCTION-level, not file-level)
2. **Runtime Access Tracking** - Updates activation values during search operations via `record_access()`

Both are broken. Git BLA exists in code but fails silently (falls back to None), and `record_access()` is not being called. This sprint fixes BOTH as they are inseparable parts of the activation scoring system.

This is a critical blocker for Aurora's core functionality because:
- Search retrieval quality cannot be assessed when all scores are identical
- Users cannot distinguish between highly relevant and barely relevant results
- The hybrid retrieval system (60% activation + 40% semantic) appears non-functional
- Complexity assessment depends on good retrieval to function properly
- Both CLI and MCP interfaces are affected (shared core logic)

### High-Level Goal

Restore proper scoring functionality to the Aurora memory search system so that:
- Activation, semantic, and hybrid scores vary appropriately based on relevance (range 0.0-1.0)
- More relevant results receive higher scores
- Results are ranked in meaningful order
- The ACT-R activation scoring formula is properly applied
- Semantic similarity (cosine distance) produces varied scores
- The 60/40 hybrid blend is correctly calculated

---

## 2. Goals

1. **Fix score calculation** - All three score types (activation, semantic, hybrid) must return varied values that reflect actual relevance
2. **Fix activation tracking** - Both Git-Based BLA initialization (indexing) and runtime access tracking (search) must work
3. **Restore ranking quality** - Search results must be sorted with most relevant items first
4. **Enable function-level activation** - Functions in same file have different activation scores based on commit history
5. **Preserve existing functionality** - No regressions in other CLI features or test suites
6. **Add regression protection** - Create E2E tests that detect score variance issues (including Git BLA)
7. **Document root cause** - Produce investigation report identifying the exact bug location and mechanism
8. **Verify manually** - Provide bash command evidence showing varied scores in real usage

---

## 3. User Stories

### Story 1: Developer Searches Codebase
**As a** developer using Aurora to search indexed code
**I want** search results ranked by relevance with varied scores
**So that** I can quickly identify the most relevant code chunks for my query

**Acceptance Criteria**:
- Activation scores vary across results (not all 1.000)
- Semantic scores vary across results (not all 1.000)
- Hybrid scores vary across results (not all 1.000)
- Top-ranked results contain query-relevant content
- Average scores displayed show variance

### Story 2: Agent Investigates Scoring Bug
**As an** agent executing this sprint
**I want** to systematically investigate all four hypothesized root causes
**So that** I can identify the exact bug location before attempting a fix

**Acceptance Criteria**:
- Investigation report created at `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/search_scoring_investigation.md`
- Root cause identified with specific file and line numbers
- Minimal reproduction test case documented
- Proposed fix approach described
- All four hypotheses evaluated (activation, semantic, hybrid blending, normalization)

### Story 3: Quality Engineer Verifies Fix
**As a** QA engineer
**I want** E2E tests that verify score variance
**So that** future regressions are automatically detected

**Acceptance Criteria**:
- E2E test fails before fix (proves bug exists)
- E2E test passes after fix (proves bug is resolved)
- Test verifies max score != min score for all three score types
- Test verifies scores are in valid range [0.0, 1.0]
- Test verifies results are sorted by hybrid score descending

### Story 4: Developer Indexes Git Repository
**As a** developer indexing a Git repository
**I want** chunks to be initialized with activation scores based on commit history at function level
**So that** frequently/recently modified functions are prioritized in search from the start

**Acceptance Criteria**:
- Git commit history extracted at FUNCTION level (not file level)
- `base_level` initialized with BLA calculated from commit timestamps
- `access_count` initialized with number of commits touching the function
- Functions in SAME file have DIFFERENT activation scores
- Git metadata (git_hash, commit_count) stored in chunk metadata
- Non-Git directories fall back gracefully (base_level=0.5)
- Database query shows BLA variance across functions

### Story 5: End User Validates Functionality
**As an** Aurora user
**I want** to run manual CLI commands and see varied scores
**So that** I can trust the search ranking system

**Acceptance Criteria**:
- `aur mem search "SOAR reasoning"` shows varied activation scores
- `aur mem search "database storage"` shows varied semantic scores
- `aur mem search "activation scoring"` shows varied hybrid scores
- Top results for each query are actually relevant to the query terms
- Database shows Git BLA values vary per function
- Manual test report updated (TEST 9: ⚠️ PARTIAL → ✅ PASSED)

---

## 4. Functional Requirements

### FR-1: Root Cause Investigation

**The system implementer must**:

1.1. Read and analyze the complete scoring pipeline in these files:
   - `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/memory_manager.py` - `search()` method
   - `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/sqlite.py` - `retrieve_by_activation()` and `retrieve_by_semantic()`
   - `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - `retrieve()`, `_normalize_scores()`, `_blend_scores()`
   - `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/activation/engine.py` - ACT-R activation calculation

1.2. Investigate Hypothesis 1 - Activation Tracking (includes Git BLA initialization):
   - Query the database: `sqlite3 ~/.aurora/memory.db "SELECT chunk_id, base_level, access_count FROM activations LIMIT 10"`
   - Expected: Varied `base_level` values based on Git commit history
   - Suspected issues:
     * All `base_level` = 0.0 (Git BLA initialization not working)
     * All `access_count` = 0 (record_access() not being called)
     * GitSignalExtractor silently falling back to None
   - Check if Git BLA is calculated at FUNCTION level during indexing (not file level)
   - Verify functions in SAME file have DIFFERENT activation scores
   - Check if `record_access()` is called after search operations

1.3. Investigate Hypothesis 2 - Semantic Embeddings:
   - Write Python script to inspect stored embeddings
   - Verify embeddings are different vectors (not all identical or None)
   - Check cosine similarity calculation for correctness (division by zero, wrong axis, etc.)

1.4. Investigate Hypothesis 3 - Hybrid Blending:
   - Verify `_blend_scores()` applies 60% activation + 40% semantic
   - Check array lengths match before blending
   - Ensure scores are normalized BEFORE blending (not after)
   - Verify blend result isn't overwritten by normalization

1.5. Investigate Hypothesis 4 - Normalization Bug:
   - Examine `_normalize_scores()` logic
   - Suspected issue: When all input scores are equal, function returns `[1.0, 1.0, ...]` instead of preserving original values
   - Check min-max normalization handles edge cases correctly

1.6. Create investigation report at `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/search_scoring_investigation.md` containing:
   - Root cause identification (which component is broken)
   - Specific line numbers where bug occurs
   - Minimal reproduction test case
   - Proposed fix approach
   - Evidence supporting the diagnosis

**Success Criteria**: Can pinpoint exact bug location with file path, line number, and explanation of mechanism.

---

### FR-2: Fix Implementation

**The system implementer must**:

2.1. **IF Root Cause = Activation Tracking Not Working** (includes Git BLA initialization):

2.1.1. **Fix Git BLA Initialization** (runs during indexing):
   - Extract Git commit history AT FUNCTION LEVEL (not file level)
   - Use `git blame -L <start>,<end> <file> --line-porcelain` for each function's line range
   - Calculate BLA using ACT-R formula: `B = ln(Σ t_j^(-d))` where t_j = time since commit, d = decay rate
   - Initialize `base_level` with BLA (not 0.0)
   - Initialize `access_count` with commit count (not 0)
   - Store git_hash, last_modified, commit_count in chunk metadata
   - Ensure functions in SAME file have DIFFERENT BLA scores
   - Gracefully fall back to base_level=0.5 for non-Git directories

2.1.2. **Fix Runtime Access Tracking** (runs during search):
   - Add `record_access()` calls in `memory_manager.py` after retrieving results
   - Pass `access_time` as `datetime.now(timezone.utc)`
   - Include query context in access record
   - Verify activations table populates with access counts > 0

2.1.3. **Implementation Files**:
   - `packages/context-code/src/aurora_context_code/git.py` (NEW) - Git signal extraction
   - `packages/cli/src/aurora_cli/memory_manager.py` - Pass line_start/line_end to Git extractor
   - `packages/core/src/aurora_core/activation/engine.py` - Use function-specific BLA
   - `packages/core/src/aurora_core/models/chunk.py` - Store line_start/line_end, git metadata

2.2. **IF Root Cause = Normalization Bug**:
   - Modify `_normalize_scores()` in `hybrid_retriever.py`
   - Change behavior: When all scores equal, return original scores (not `[1.0, 1.0, ...]`)
   - Handle edge case: When `range_score == 0`, return scores as-is
   - Preserve standard min-max normalization for non-equal scores

2.3. **IF Root Cause = Semantic Embeddings Broken**:
   - Check embedding computation during indexing (`index()` function)
   - Verify cosine similarity formula correctness
   - Ensure vectors are normalized properly
   - Fix any divide-by-zero errors

2.4. **IF Root Cause = Hybrid Blending Not Applied**:
   - Verify `_blend_scores()` calculates `0.6 * activation + 0.4 * semantic`
   - Ensure arrays are same length before blending
   - Confirm scores are normalized BEFORE blending
   - Check blend result isn't accidentally overwritten

2.5. Fix production code only (NOT test parsing or output formatting)

2.6. Verify fix logic with unit tests if possible

**Success Criteria**: Production code modified to resolve root cause, no changes to test parsing/formatting.

---

### FR-3: E2E Test Implementation

**The system implementer must**:

3.1. Create `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_search_scoring.py`

3.2. Implement `test_search_returns_varied_scores()`:
   - Index a diverse codebase (e.g., `packages/core/`)
   - Execute search: `aur mem search "activation scoring" --output json`
   - Parse JSON output to extract scores
   - Assert max activation score != min activation score
   - Assert max semantic score != min semantic score
   - Assert max hybrid score != min hybrid score
   - Assert all scores in range [0.0, 1.0]
   - Provide clear failure messages indicating which score type failed

3.3. Implement `test_search_ranks_relevant_results_higher()`:
   - Index code about a specific topic (e.g., `packages/core/src/aurora_core/activation/`)
   - Search for that topic (e.g., "activation scoring algorithm")
   - Assert results are sorted by hybrid score descending
   - Assert top result content mentions query terms
   - Verify higher-scored results are actually more relevant

3.4. Add additional test case: `test_semantic_similarity_varies()`:
   - Index diverse code with different functionality areas
   - Search for specific domain term (e.g., "database storage")
   - Verify semantic scores reflect actual similarity
   - Assert most semantically similar results ranked first

3.5. Add additional test case: `test_activation_frequency_affects_score()`:
   - Index codebase
   - Search for term multiple times (3-5 repetitions)
   - Verify activation scores increase with repeated access
   - Ensure frequently accessed chunks rank higher in subsequent searches

3.6. Add additional test case: `test_hybrid_blend_combines_both_signals()`:
   - Index code with both frequently accessed and semantically similar chunks
   - Search with query matching semantic content
   - Verify hybrid score is between activation and semantic scores
   - Confirm blending ratio is approximately 60/40

3.7. Add additional test case: `test_git_bla_initialization()`:
   - Index a Git repository with known commit history
   - Query database to verify base_level varies across functions
   - Verify functions in SAME file have DIFFERENT activation scores
   - Check git_hash, commit_count in chunk metadata
   - Verify frequently-edited functions have higher BLA than rarely-touched functions
   - Test graceful fallback for non-Git directories

3.8. Run tests before fix - **MUST FAIL** (proves bug exists)

3.9. Run tests after fix - **MUST PASS** (proves bug is resolved)

**Success Criteria**: Test file created with 6 test cases (including Git BLA test), tests fail pre-fix, tests pass post-fix.

---

### FR-4: Manual Verification

**The system implementer must**:

4.1. Clean environment:
   ```bash
   rm -rf ~/.aurora
   aur init
   ```

4.2. Index test codebase:
   ```bash
   aur mem index /home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/
   ```
   Expected: Files indexed: 29, Chunks created: 361 (or similar)

4.3. Execute varied searches and capture output:
   ```bash
   aur mem search "SOAR reasoning"
   aur mem search "database storage"
   aur mem search "activation scoring"
   ```

4.4. Verify for each search:
   - Activation scores vary (not all 1.000)
   - Semantic scores vary (not all 1.000)
   - Hybrid scores vary (not all 1.000)
   - More relevant results have higher scores
   - Top-ranked results mention query terms

4.5. Check database activation tracking (Git BLA initialization):
   ```bash
   # Check BLA values vary
   sqlite3 ~/.aurora/memory.db "SELECT AVG(base_level), COUNT(DISTINCT base_level) FROM activations WHERE base_level > 0"
   ```
   Expected: Average > 0.0, Distinct > 10

   ```bash
   # Check Git metadata present
   sqlite3 ~/.aurora/memory.db "SELECT COUNT(*) FROM chunks WHERE metadata->>'git_hash' IS NOT NULL"
   ```
   Expected: > 0 (chunks have Git metadata)

   ```bash
   # CRITICAL: Verify functions in SAME file have DIFFERENT scores
   sqlite3 ~/.aurora/memory.db "
     SELECT
       c.name,
       a.base_level,
       a.access_count
     FROM chunks c
     JOIN activations a ON c.chunk_id = a.chunk_id
     WHERE c.file_path LIKE '%memory_manager.py'
     ORDER BY a.base_level DESC;
   "
   ```
   Expected: Different functions in same file have different base_level values

4.6. Update manual test report:
   - File: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/MANUAL_CLI_TEST_REPORT.md`
   - Change TEST 9 from `⚠️ PARTIAL` to `✅ PASSED`
   - Add verification notes with example output

**Success Criteria**: Manual commands produce varied scores, database shows activation tracking, test report updated.

---

### FR-5: Regression Testing

**The system implementer must**:

5.1. Run full test suite:
   ```bash
   make test
   ```
   Expected: All existing tests still pass (no regressions)

5.2. Run type checking:
   ```bash
   make type-check
   ```
   Expected: No new mypy errors introduced

5.3. Run quality gates:
   ```bash
   make quality-check
   ```
   Expected: Linting, formatting, and type checks all pass

5.4. Verify no changes to test parsing logic (grep for changes in test assertion parsing)

**Success Criteria**: 2,369 existing tests pass, no new type errors, quality checks pass.

---

## 5. Non-Goals (Out of Scope)

The following issues are **explicitly excluded** from this sprint and must NOT be addressed:

1. **Complexity Assessment Issues** - Multi-keyword query classification (TEST 12 failure) is deferred to Sprint 3
2. **Single File Indexing** - File indexing returning 0 chunks (TEST 6 failure) is deferred to Sprint 2
3. **Documentation Inconsistencies** - Help text errors (`--verify`, `--limit`, `budget status`) are deferred to Phase 2
4. **Config Command Missing** - `aur config show` command absence is deferred to Phase 2
5. **MCP Integration** - SOAR integration in MCP tools is deferred to Phase 2
6. **Performance Optimization** - Search latency improvements are not in scope
7. **UI/UX Improvements** - Output formatting changes are not in scope
8. **New Features** - No new scoring algorithms, no new search modes

**Scope Management**: If tempted to fix other issues encountered during implementation, create a separate sprint/task instead. This sprint focuses ONLY on search scoring variance.

---

## 6. Design Considerations

### 6.1 Existing Architecture

**Scoring Pipeline Flow**:
```
User Query → memory_manager.search()
           → hybrid_retriever.retrieve()
              → sqlite.retrieve_by_activation()  (ACT-R formula)
              → sqlite.retrieve_by_semantic()    (Cosine similarity)
              → hybrid_retriever._blend_scores() (60/40 blend)
              → hybrid_retriever._normalize_scores()
           → Return ranked results
```

**ACT-R Activation Formula** (from `engine.py`):
```
Activation = Base Level + Context Boost
Base Level = ln(Σ(t_i^-d)) where t_i = time since access i, d = decay rate
Context = Relevance * Weight
```

**Hybrid Blending**:
```
Hybrid Score = 0.6 * Activation Score + 0.4 * Semantic Score
```

### 6.2 Data Flow

1. **Indexing** (one-time setup):
   - Parse code into chunks
   - Generate embeddings (sentence-transformers)
   - Store in SQLite with metadata

2. **Search** (runtime):
   - Embed query using same model
   - Retrieve by activation (frequency/recency)
   - Retrieve by semantic (cosine similarity)
   - Blend and normalize scores
   - Return top-k results

3. **Access Tracking** (should happen but may not):
   - Record each retrieval in activations table
   - Update access_count and timestamps
   - Used by ACT-R formula for future retrievals

### 6.3 Expected Score Characteristics

**Activation Scores**:
- Range: 0.0-1.0 (after normalization)
- Influenced by: frequency of past accesses, recency of accesses
- Should vary based on how often chunks have been retrieved

**Semantic Scores**:
- Range: 0.0-1.0 (cosine similarity)
- Influenced by: embedding similarity between query and chunk
- Should vary based on content relevance

**Hybrid Scores**:
- Range: 0.0-1.0
- Weighted average: 60% activation + 40% semantic
- Should reflect both popularity and relevance

### 6.4 UI Output Format

```
Found 5 results for 'SOAR reasoning phases'

┏━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━┓
┃ File      ┃ Type  ┃ Name   ┃ Lines ┃ Score ┃
┡━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━┩
│ file.py   │ code  │ Func   │ 10-20 │ 0.82 │
│ other.py  │ code  │ Class  │ 30-50 │ 0.65 │
└───────────┴───────┴────────┴───────┴─────┘

Average scores:
  Activation: 0.567  ← Should vary
  Semantic:   0.723  ← Should vary
  Hybrid:     0.628  ← Should vary
```

---

## 7. Technical Considerations

### 7.1 Implementation Constraints

- **No Breaking Changes**: Must maintain backward compatibility with existing CLI and MCP interfaces
- **Database Schema**: Cannot modify SQLite schema (would require migration)
- **Embedding Model**: Must use existing `all-MiniLM-L6-v2` model (no model changes)
- **Performance**: Fix must not significantly degrade search latency (target: <2s for simple queries)
- **Dependencies**: No new package dependencies allowed

### 7.2 Testing Requirements

**Test Coverage**:
- Unit tests: 97%+ coverage maintained (current: 81.06%, but critical paths covered)
- E2E tests: 5 new tests for score variance
- Manual tests: 3 search scenarios verified

**Test Isolation**:
- E2E tests must clean database before running
- Must not pollute `~/.aurora/` directory
- Use temporary test database paths

**Test Performance**:
- E2E tests should complete in <5 minutes total
- Individual test cases should complete in <30 seconds

### 7.3 Suggested Technical Approach

**Investigation Strategy**:
1. Start with database inspection (easiest to verify)
2. Check activation tracking (most likely culprit)
3. Examine normalization logic (second most likely)
4. Verify hybrid blending (least likely but critical)
5. Test semantic embeddings (if all else fails)

**Fix Priority Order** (based on likelihood):
1. Add missing `record_access()` calls (Hypothesis 1) - 60% likely
2. Fix `_normalize_scores()` edge case (Hypothesis 4) - 30% likely
3. Fix hybrid blending logic (Hypothesis 3) - 8% likely
4. Fix semantic similarity calculation (Hypothesis 2) - 2% likely

**Verification Checkpoints**:
- After investigation: Can reproduce bug with minimal test case
- After fix: Unit test passes demonstrating fix
- After E2E tests: All 5 tests pass
- After manual testing: Real CLI shows varied scores
- After regression: All 2,369 tests still pass

### 7.4 Integration Points

**Upstream Dependencies**:
- Tree-sitter parsing (Python only)
- Sentence-transformers embeddings
- SQLite database

**Downstream Consumers**:
- CLI `aur mem search` command
- MCP `aurora_memory_search` tool
- SOAR Retrieve phase
- Complexity assessment (depends on good retrieval)

**Shared Components**:
- `aurora_core.memory_manager.MemoryManager`
- `aurora_core.sqlite.SQLiteStore`
- `aurora_context_code.semantic.hybrid_retriever.HybridRetriever`

---

## 8. Success Metrics

### 8.1 Quantitative Metrics

**Score Variance** (Primary Success Metric):
- **Baseline**: All scores = 1.000 (variance = 0.0)
- **Target**: Score variance > 0.1 for typical queries
- **Measurement**: Standard deviation of scores in search results

**Score Range**:
- **Baseline**: All scores in range [1.0, 1.0]
- **Target**: Scores use full range [0.0, 1.0] appropriately
- **Measurement**: Max score - min score > 0.3 for diverse queries

**Ranking Quality**:
- **Baseline**: Random ranking (all scores equal)
- **Target**: Top result mentions query terms 80%+ of the time
- **Measurement**: Manual inspection of top 3 results for 10 test queries

**Regression Prevention**:
- **Target**: 0 test regressions
- **Measurement**: Test pass rate remains 97% (2,369 tests)

### 8.2 Qualitative Metrics

**User Confidence**:
- Users can identify most relevant results by looking at scores
- Search results feel "ranked by relevance" not random

**Code Quality**:
- Root cause clearly documented
- Fix is minimal and targeted (not over-engineered)
- No code duplication introduced

**Maintainability**:
- E2E tests provide clear regression protection
- Investigation report serves as documentation for future developers

### 8.3 Acceptance Criteria (Sprint Cannot Complete Without These)

1. ✅ **Root cause identified and documented** in investigation report
2. ✅ **Bug fixed in production code** (NOT test parsing or formatting)
3. ✅ **E2E tests pass** - All 6 new tests verify score variance (including Git BLA test)
4. ✅ **Manual testing shows varied scores** - Command output captured
5. ✅ **Top-ranked results are relevant** - Query terms appear in top results
6. ✅ **No regression** - All 2,369 existing tests still pass
7. ✅ **Database activation tracking works** - SQLite queries show varied base_level values
8. ✅ **Git BLA initialization works** - Base-level activation varies based on Git commit history
9. ✅ **Function-level tracking works** - Functions in same file have different activation scores
10. ✅ **Manual test report updated** - TEST 9 status changed to PASSED

### 8.4 Evidence Required Before Sprint Completion

**Evidence 1: Varied Scores in CLI Output**
```bash
aur mem search "SOAR" | grep "Average scores"
# Output MUST show:
#   Activation: 0.567  (NOT 1.000)
#   Semantic:   0.723  (NOT 1.000)
#   Hybrid:     0.628  (NOT 1.000)
```

**Evidence 2: Database Shows Activation Tracking**
```bash
sqlite3 ~/.aurora/memory.db \
  "SELECT AVG(base_level), COUNT(DISTINCT base_level) FROM activations WHERE base_level > 0"
# Output: Average > 0.0, Distinct > 10
```

**Evidence 3: E2E Tests Pass**
```bash
pytest /home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_search_scoring.py -v
# Output: 6/6 PASSED (including Git BLA test)
```

**Evidence 3.1: Git BLA Function-Level Tracking**
```bash
sqlite3 ~/.aurora/memory.db "
  SELECT
    c.name,
    a.base_level,
    a.access_count,
    c.metadata->>'commit_count' as commits
  FROM chunks c
  JOIN activations a ON c.chunk_id = a.chunk_id
  WHERE c.file_path LIKE '%memory_manager.py'
  ORDER BY a.base_level DESC
  LIMIT 5;
"
# Output: Functions in same file have DIFFERENT base_level values
# Example expected output:
# index_file          | 2.45 | 8  | 8
# search              | 1.82 | 5  | 5
# get_stats           | 0.91 | 2  | 2
# _validate_path      | 0.50 | 1  | 1
```

**Evidence 4: No Regressions**
```bash
make test
# Output: 2,369 passed, 14 skipped (same as baseline)
```

---

## 9. Open Questions

### 9.1 Technical Questions

**Q1**: Should activation tracking record access for all retrieved chunks or only the top-k returned to user?
- **Impact**: Affects activation score evolution over time
- **Recommendation**: Record all retrieved chunks (matches ACT-R theory)
- **Decision Needed**: Before implementing fix

**Q2**: If normalization bug is the root cause, should we normalize before or after blending?
- **Impact**: Affects score distribution and hybrid balance
- **Recommendation**: Normalize individual scores before blending (preserves 60/40 ratio)
- **Decision Needed**: During investigation phase

**Q3**: What is the expected score distribution for a typical query?
- **Impact**: Helps validate fix correctness
- **Recommendation**: Top result 0.7-1.0, middle results 0.4-0.7, bottom results 0.1-0.4
- **Decision Needed**: Before defining "success" criteria

**Q4**: Should we add logging to track score calculation steps for debugging?
- **Impact**: Helps future debugging but adds code complexity
- **Recommendation**: Add debug logging under `DEBUG=1` environment variable
- **Decision Needed**: During fix implementation

### 9.2 Process Questions

**Q5**: Should we create a feature branch or commit directly to main?
- **Recommendation**: Create feature branch `fix/search-scoring`
- **Rationale**: Allows review before merge, safer for critical fix

**Q6**: How should we handle if multiple hypotheses are true (multiple bugs)?
- **Recommendation**: Fix all identified bugs in sequence, test after each fix
- **Rationale**: Multiple bugs may be cascading (one causing another)

**Q7**: If fix requires significant refactoring, should we proceed or re-scope?
- **Threshold**: If >200 lines changed, re-evaluate approach
- **Recommendation**: Prefer minimal targeted fix over large refactor
- **Decision Needed**: During implementation if this situation arises

---

## 10. Sprint Execution Checklist

### Pre-Sprint
- [ ] Read full PRD
- [ ] Understand all 4 root cause hypotheses
- [ ] Review scoring pipeline architecture (Section 6.1)
- [ ] Verify no dependencies on other sprints
- [ ] Create feature branch: `fix/search-scoring`

### Investigation Phase (FR-1)
- [ ] Read all 4 implementation files
- [ ] Investigate Hypothesis 1: Activation tracking
- [ ] Investigate Hypothesis 2: Semantic embeddings
- [ ] Investigate Hypothesis 3: Hybrid blending
- [ ] Investigate Hypothesis 4: Normalization bug
- [ ] Create investigation report with root cause
- [ ] Document minimal reproduction test case

### Fix Phase (FR-2)
- [ ] Implement Git BLA initialization (if needed)
  - [ ] Create `packages/context-code/src/aurora_context_code/git.py`
  - [ ] Implement `GitSignalExtractor` class with function-level tracking
  - [ ] Integrate in `memory_manager.py` index_file() method
  - [ ] Verify Chunk model has line_start/line_end fields
  - [ ] Test graceful fallback for non-Git directories
- [ ] Implement runtime access tracking (if needed)
  - [ ] Add `record_access()` calls after search operations
  - [ ] Verify access_count increments properly
- [ ] Implement other fixes (normalization, semantic, blending) as needed
- [ ] Write unit test demonstrating fix (if applicable)
- [ ] Verify fix logic with simple Python script
- [ ] Ensure no test parsing modifications

### Testing Phase (FR-3, FR-4, FR-5)
- [ ] Create E2E test file with 6 test cases (including Git BLA test)
- [ ] Run E2E tests - verify they FAIL pre-fix
- [ ] Apply fix
- [ ] Run E2E tests - verify they PASS post-fix
- [ ] Clean environment and run manual tests
- [ ] Verify Git BLA with database queries (function-level variance)
- [ ] Test non-Git directory fallback
- [ ] Capture manual test output as evidence
- [ ] Run full test suite - verify no regressions
- [ ] Run quality checks - verify no new issues

### Documentation Phase
- [ ] Update MANUAL_CLI_TEST_REPORT.md (TEST 9 → PASSED)
- [ ] Ensure investigation report is complete
- [ ] Add code comments explaining fix (if not obvious)

### Verification Phase
- [ ] Collect all evidence items (Section 8.4) including Git BLA
- [ ] Verify all 10 acceptance criteria met (Section 8.3)
- [ ] Verify function-level Git BLA tracking (same file, different scores)
- [ ] Double-check no scope creep occurred
- [ ] Confirm no test masking or shortcuts taken

### Completion Phase
- [ ] Commit with clear message: `fix(search): resolve all scores returning 1.000`
- [ ] Update sprint status in AURORA_MAJOR_FIXES.md
- [ ] Request code review (if applicable)
- [ ] Merge feature branch to main

---

## 11. Red Flags (Sprint Failure Indicators)

**STOP immediately and reassess if ANY of these occur**:

- ❌ Modifying test parsing instead of production code
- ❌ Changing expected values in tests to match broken behavior
- ❌ Adding `|| true` or similar to mask failures
- ❌ Removing assertions from tests
- ❌ Tests pass but feature doesn't actually work when tested manually
- ❌ Expanding scope to include complexity assessment or single file indexing
- ❌ Adding sleep() or retry logic to make tests pass
- ❌ Skipping manual verification step
- ❌ Claiming "tests pass" without showing actual CLI output
- ❌ Making changes to output formatting to help tests parse results

**If a red flag is raised**: Document the situation, stop work, and re-evaluate the approach.

---

## 12. Context References

### Related Documents
- **Sprint Plan**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/AURORA_MAJOR_FIXES.md` (SPRINT 1 section)
- **Manual Test Report**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/MANUAL_CLI_TEST_REPORT.md` (TEST 9)
- **E2E Failure Analysis**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/E2E_FAILURE_REMEDIATION_PLAN.md` (Category 3: Git BLA)
- **PRD Phase 1**: `/home/hamr/PycharmProjects/aurora/tasks/0010-prd-aurora-phase1-core-restoration.md` (US-8, FR-8: Git BLA implementation details)
- **Architecture**: `/home/hamr/PycharmProjects/aurora/docs/architecture/SOAR_ARCHITECTURE.md`
- **Testing Guide**: `/home/hamr/PycharmProjects/aurora/docs/development/TESTING.md`

### Phase 2A Context (Reference Only)
Phase 2A attempted to fix 11 issues in one sprint and resulted in test masking instead of actual fixes. This sprint deliberately uses a focused approach:
- One feature only (search scoring)
- Manual verification required
- No test parsing modifications allowed

See AURORA_MAJOR_FIXES.md Section "Lessons Learned from Phase 2A" for details on what went wrong and how this sprint avoids those pitfalls.

---

## Appendix A: Root Cause Hypothesis Details

### Hypothesis 1: Activation Tracking Not Working (60% Likelihood)

**Theory**: `record_access()` is never called after search operations, so all chunks have `access_count = 0` and `base_level = 0.0`, resulting in identical activation scores.

**Verification**:
```bash
sqlite3 ~/.aurora/memory.db "SELECT COUNT(*) FROM activations WHERE access_count > 0"
# Expected if broken: 0
```

**Fix Location**: `packages/core/src/aurora_core/memory_manager.py` in `search()` method

**Fix Approach**: Add `record_access()` calls in a loop after retrieving results:
```python
for result in results:
    self._store.record_access(
        result["chunk_id"],
        datetime.now(timezone.utc),
        context=query
    )
```

---

### Hypothesis 2: Semantic Embeddings Broken (2% Likelihood)

**Theory**: Embeddings are not computed correctly, or cosine similarity has a bug (division by zero, wrong axis).

**Verification**:
```python
from aurora_core.sqlite import SQLiteStore
store = SQLiteStore("~/.aurora/memory.db")
chunks = store.retrieve_chunks(limit=5)
for chunk in chunks:
    print(f"{chunk.chunk_id}: {chunk.embedding[:5] if chunk.embedding else None}")
# Expected: Different vectors
# If broken: All None or all identical
```

**Fix Location**: `packages/context-code/src/aurora_context_code/semantic/` - embedding generation or similarity calculation

**Fix Approach**: Depends on specific bug found (likely cosine similarity formula error)

---

### Hypothesis 3: Hybrid Blending Not Applied (8% Likelihood)

**Theory**: The 60/40 blend is computed but then overwritten by normalization, or blend formula is incorrect.

**Verification**: Add debug logging in `_blend_scores()` to print intermediate values.

**Fix Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` in `_blend_scores()`

**Fix Approach**: Ensure blend happens after individual normalization but before final output, verify formula is `0.6 * A + 0.4 * S`

---

### Hypothesis 4: Normalization Bug (30% Likelihood)

**Theory**: `_normalize_scores()` has an edge case where equal input values return `[1.0, 1.0, ...]` instead of preserving the original values.

**Verification**:
```python
# Test normalization directly
from aurora_context_code.semantic.hybrid_retriever import _normalize_scores
print(_normalize_scores([0.5, 0.5, 0.5]))
# If broken: [1.0, 1.0, 1.0]
# If correct: [0.5, 0.5, 0.5] or [1.0, 1.0, 1.0] (both valid, but must be consistent)
```

**Fix Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` in `_normalize_scores()`

**Fix Approach**:
```python
def _normalize_scores(scores):
    if not scores:
        return []

    # Edge case: All scores equal
    if len(set(scores)) == 1:
        return scores  # Return as-is, don't normalize to [1.0, 1.0, ...]

    # Standard min-max normalization
    min_score = min(scores)
    max_score = max(scores)
    range_score = max_score - min_score

    if range_score == 0:
        return scores

    return [(s - min_score) / range_score for s in scores]
```

---

## Appendix A-Ext: Git-Based BLA Initialization (Part of Hypothesis 1)

### Background

Git-Based BLA (Base-Level Activation) initialization is NOT a separate feature - it is an integral part of activation scoring. When chunks are first created during indexing, they need INITIAL activation values. Without Git BLA, all chunks start with `base_level=0.0` and `access_count=0`, which means activation scores are identical until runtime usage differentiates them.

Git BLA provides "warm start" activation values based on commit history, so that frequently/recently modified functions are prioritized from the start.

### Critical Requirement: Function-Level Tracking

**IMPORTANT**: Git BLA MUST be calculated PER FUNCTION, not per file. This is because:
- Different functions in the same file have different edit histories
- Frequently-changed functions (e.g., bug fixes, feature additions) should have higher activation than rarely-touched functions
- Tree-sitter provides line ranges (line_start, line_end) for each function

**Example**: In `memory_manager.py`:
- `index_file()` modified in 8 commits → BLA = 2.45
- `search()` modified in 5 commits → BLA = 1.82
- `get_stats()` modified in 2 commits → BLA = 0.91
- `_validate_path()` modified in 1 commit → BLA = 0.50

All four functions are in the SAME file, but have DIFFERENT activation scores.

### Implementation Details

**Step 1: Extract Git Commit History (Function-Level)**

Create new file: `packages/context-code/src/aurora_context_code/git.py`

```python
# File: packages/context-code/src/aurora_context_code/git.py
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
import math

class GitSignalExtractor:
    """Extract Git signals for BLA initialization at FUNCTION level."""

    def get_function_commit_times(
        self,
        file_path: Path,
        start_line: int,
        end_line: int
    ) -> List[int]:
        """Get Unix timestamps for commits that touched this specific function.

        Args:
            file_path: Path to source file
            start_line: Function start line (from tree-sitter)
            end_line: Function end line (from tree-sitter)

        Returns:
            List of Unix timestamps for commits touching these lines,
            newest first. Empty list if not in Git or no history.
        """
        try:
            # Get git blame for function's line range
            result = subprocess.run(
                [
                    "git", "blame",
                    "-L", f"{start_line},{end_line}",
                    str(file_path),
                    "--line-porcelain"
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode != 0:
                return []

            # Extract unique commit SHAs from blame output
            commit_shas = set()
            for line in result.stdout.splitlines():
                # git blame --line-porcelain format: first 40 chars of line is SHA
                if len(line) >= 40 and not line.startswith('\t'):
                    potential_sha = line.split()[0]
                    if len(potential_sha) == 40:
                        try:
                            int(potential_sha, 16)  # Verify it's hex
                            commit_shas.add(potential_sha)
                        except ValueError:
                            continue

            # Get timestamp for each commit
            timestamps = []
            for sha in commit_shas:
                ts = self._get_commit_timestamp(sha)
                if ts:
                    timestamps.append(ts)

            return sorted(timestamps, reverse=True)  # Newest first

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _get_commit_timestamp(self, commit_sha: str) -> Optional[int]:
        """Get Unix timestamp for a specific commit."""
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%ct", commit_sha],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            return None

    def calculate_bla(self, commit_times: List[int], decay: float = 0.5) -> float:
        """Calculate base-level activation from commit history.

        Args:
            commit_times: Unix timestamps of commits
            decay: Decay rate (default 0.5)

        Returns:
            BLA score using ACT-R formula: B = ln(Σ t_j^(-d))
        """
        if not commit_times:
            return 0.5  # Default for non-Git files

        now = datetime.now(timezone.utc).timestamp()

        # Calculate sum of decayed accesses
        sum_decayed = 0.0
        for commit_time in commit_times:
            time_since = max(now - commit_time, 1.0)  # Avoid division by zero
            sum_decayed += time_since ** (-decay)

        # BLA = ln(sum)
        bla = math.log(sum_decayed) if sum_decayed > 0 else 0.5
        return bla
```

**Step 2: Integrate Git BLA in Memory Manager**

Modify: `packages/cli/src/aurora_cli/memory_manager.py`

```python
# In index_file() method, after parsing chunks:
def index_file(self, file_path: Path) -> List[Chunk]:
    # Parse file to get chunks (each has line_start, line_end from tree-sitter)
    chunks = self.parser.parse_file(file_path)

    # NEW: Extract Git signals PER FUNCTION
    try:
        git_extractor = GitSignalExtractor()
        logger.debug(f"Initialized GitSignalExtractor for {file_path}")
    except Exception as e:
        logger.warning(f"Could not initialize Git extractor: {e}. Using default BLA values.")
        git_extractor = None

    for chunk in chunks:
        # Get commits specific to THIS function's line range
        if git_extractor and hasattr(chunk, "line_start") and hasattr(chunk, "line_end"):
            try:
                commit_times = git_extractor.get_function_commit_times(
                    file_path=file_path,
                    start_line=chunk.line_start,
                    end_line=chunk.line_end
                )

                if commit_times:
                    # Calculate BLA from THIS function's commit history
                    initial_bla = git_extractor.calculate_bla(commit_times, decay=0.5)
                    commit_count = len(commit_times)

                    # Store metadata (function-specific)
                    chunk.metadata["git_hash"] = commit_times[0] if commit_times else None
                    chunk.metadata["last_modified"] = commit_times[0] if commit_times else None
                    chunk.metadata["commit_count"] = commit_count

                    # Initialize activation with FUNCTION-SPECIFIC BLA
                    self.store.store_chunk(chunk)
                    self.store.initialize_activation(
                        chunk_id=chunk.chunk_id,
                        base_level=initial_bla,
                        access_count=commit_count
                    )
                else:
                    # No Git history for this function
                    self._store_chunk_with_default_bla(chunk)
            except Exception as e:
                logger.warning(f"Git BLA extraction failed for {chunk.name}: {e}")
                self._store_chunk_with_default_bla(chunk)
        else:
            # Non-Git directory or chunk missing line info
            self._store_chunk_with_default_bla(chunk)

def _store_chunk_with_default_bla(self, chunk: Chunk):
    """Store chunk with default BLA values."""
    self.store.store_chunk(chunk)
    self.store.initialize_activation(
        chunk_id=chunk.chunk_id,
        base_level=0.5,  # Default for non-Git
        access_count=1
    )
```

**Step 3: Verify Chunk Model Stores Line Ranges**

Verify: `packages/core/src/aurora_core/models/chunk.py`

Ensure Chunk model has:
- `line_start: int` - Function start line (from tree-sitter)
- `line_end: int` - Function end line (from tree-sitter)
- `metadata: dict` - Stores git_hash, last_modified, commit_count

### Verification Steps

After implementing Git BLA:

**1. Check Database for BLA Variance**
```bash
sqlite3 ~/.aurora/memory.db "
  SELECT AVG(base_level), MIN(base_level), MAX(base_level), COUNT(DISTINCT base_level)
  FROM activations
  WHERE base_level > 0
"
# Expected: Average > 0.5, Max > 2.0, Distinct > 20
```

**2. Verify Function-Level Tracking**
```bash
sqlite3 ~/.aurora/memory.db "
  SELECT
    c.file_path,
    c.name,
    a.base_level,
    a.access_count,
    c.metadata->>'commit_count' as commits
  FROM chunks c
  JOIN activations a ON c.chunk_id = a.chunk_id
  WHERE c.file_path LIKE '%memory_manager.py'
  ORDER BY a.base_level DESC;
"
# Expected: Functions in SAME file have DIFFERENT base_level values
```

**3. Check Git Metadata Present**
```bash
sqlite3 ~/.aurora/memory.db "
  SELECT COUNT(*) as with_git, (SELECT COUNT(*) FROM chunks) as total
  FROM chunks
  WHERE metadata->>'git_hash' IS NOT NULL
"
# Expected: with_git > 0 (for Git repositories)
```

**4. Test Non-Git Fallback**
```bash
mkdir /tmp/no-git-test
echo "def test(): pass" > /tmp/no-git-test/file.py
aur mem index /tmp/no-git-test

sqlite3 ~/.aurora/memory.db "
  SELECT base_level, access_count
  FROM activations
  WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE file_path LIKE '%no-git-test%')
"
# Expected: base_level = 0.5, access_count = 1 (graceful fallback)
```

### Known Issues from E2E_FAILURE_REMEDIATION_PLAN.md

From Category 3 (lines 199-266):
- GitSignalExtractor initialization may fail silently
- Falls back to `git_extractor = None` without proper logging
- E2E tests fail because BLA remains 0.0 for all chunks

**Root Cause**: Code exists but has execution path issues (silent failures).

**Fix Required**:
1. Better error logging to understand WHY initialization fails
2. Ensure correct repo path detection
3. Add fallback that still sets reasonable BLA (not 0.0) even without Git
4. E2E tests should verify `git_extractor is not None` before proceeding

---

## Appendix B: Example Investigation Report Template

Create file at: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/search_scoring_investigation.md`

```markdown
# Search Scoring Investigation Report

**Date**: [Date]
**Investigator**: [Agent/Developer Name]
**Sprint**: Sprint 1 - Fix Search Scoring

## Executive Summary

[1-2 sentences: What was the root cause?]

## Investigation Process

### Hypothesis 1: Activation Tracking
**Tested**: [Yes/No]
**Method**: [SQL queries, code inspection, etc.]
**Result**: [Bug found / Not the cause]
**Evidence**: [Command output, code snippets]

### Hypothesis 2: Semantic Embeddings
**Tested**: [Yes/No]
**Method**: [Python script, database inspection, etc.]
**Result**: [Bug found / Not the cause]
**Evidence**: [Output, observations]

### Hypothesis 3: Hybrid Blending
**Tested**: [Yes/No]
**Method**: [Debug logging, code review, etc.]
**Result**: [Bug found / Not the cause]
**Evidence**: [Log output, code analysis]

### Hypothesis 4: Normalization Bug
**Tested**: [Yes/No]
**Method**: [Direct function testing, code inspection]
**Result**: [Bug found / Not the cause]
**Evidence**: [Test output, code snippet]

## Root Cause Identified

**Component**: [File path and function name]
**Line Number(s)**: [Specific lines]
**Bug Description**: [Clear explanation of what's wrong]

**Minimal Reproduction**:
```python
# Code to reproduce the bug
```

**Expected Behavior**: [What should happen]
**Actual Behavior**: [What currently happens]

## Proposed Fix

**Approach**: [High-level fix strategy]
**Files to Modify**: [List of files]
**Changes Required**: [Description of code changes]

**Fix Code**:
```python
# Proposed fix implementation
```

## Impact Assessment

**Scope**: [How widespread is the bug?]
**Downstream Effects**: [What else might be affected?]
**Risk**: [Low/Medium/High - risk of fix causing regressions]

## Testing Strategy

**Unit Tests**: [Specific unit tests to add]
**E2E Tests**: [E2E test scenarios]
**Manual Verification**: [Commands to run]

## Conclusion

[Summary of findings and confidence level in proposed fix]
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-29 | Claude Sonnet 4.5 | Initial PRD creation |
| 1.1 | 2025-12-29 | Claude Sonnet 4.5 | Added Git-Based BLA initialization as integral part of activation scoring fix (FR-8 from PRD-0010, Category 3 from E2E failures) |

---

**END OF DOCUMENT**
