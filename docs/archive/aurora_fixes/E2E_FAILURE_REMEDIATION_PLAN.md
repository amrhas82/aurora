# E2E Test Failure Remediation Plan - Ultrathink Analysis
**Generated**: 2025-12-29
**Status**: Phase 1 Post-Mortem Analysis
**Test Run**: CI/CD Run #20564741391 (48+ E2E/Integration Tests Failing)

## Executive Summary

**Critical Finding**: E2E tests are failing due to IMPLEMENTATION GAPS, not pre-existing issues. The code structure is correct (unit tests pass), but runtime behavior is broken due to:
1. **Placeholder implementations** that return hardcoded values (0, empty, defaults)
2. **Missing database queries** in stats/tracking methods
3. **Incorrect keyword matching** in complexity assessment
4. **Database path confusion** between test isolation and actual persistence

All failures trace back to functions that EXIST and COMPILE, but DON'T ACTUALLY WORK when called end-to-end.

---

## Failure Category 1: E2E Complexity Assessment (9 Failures)

### Root Cause
**Location**: `packages/soar/src/aurora_soar/phases/assess.py` lines 33-158

**Issue**: Keywords ARE in the code, but the MATCHING LOGIC is wrong for domain terms.

#### Evidence from Code Analysis:
```python
# Lines 102-122 - MEDIUM_KEYWORDS set
MEDIUM_KEYWORDS = {
    # ... other keywords ...
    # Domain-specific terms (Aurora, ACT-R, SOAR, AI)
    "soar",
    "actr",
    "act-r",
    "activation",
    "retrieval",
    "reasoning",
    "agentic",
    "marketplace",
    "aurora",
    "orchestration",
    "cognitive",
    "memory",
    # ...
}
```

**The Problem**: Lines 225-260 show the keyword matching algorithm:
```python
def _assess_tier1_keyword(query: str) -> tuple[str, float, float]:
    query_lower = query.lower()
    query_words = set(re.findall(r"\b\w+\b", query_lower))

    simple_matches = len(query_words & SIMPLE_KEYWORDS)
    medium_matches = len(query_words & MEDIUM_KEYWORDS)
    complex_matches = len(query_words & COMPLEX_KEYWORDS)

    # Calculate weighted scores
    simple_score = simple_matches / total_keywords
    medium_score = (medium_matches / total_keywords) * 1.2
    complex_score = (complex_matches / total_keywords) * 1.5
```

**Why E2E Fails**:
1. Query: "How does SOAR orchestration work?"
2. Tokenized words: `{"how", "does", "soar", "orchestration", "work"}`
3. SIMPLE_KEYWORDS matches: `how = 1`
4. MEDIUM_KEYWORDS matches: `soar, orchestration = 2`
5. Score calculation:
   - simple_score = 1/5 = 0.20
   - medium_score = (2/5) * 1.2 = 0.48
6. **Result**: SIMPLE wins because the algorithm picks `max(scores)` and simple_score is boosted by other words

**The Fix Required**: Adjust scoring algorithm to give stronger weight to domain-specific keywords. When "SOAR" or "ACT-R" appears, it should ALWAYS be at least MEDIUM complexity, regardless of other words.

#### Failing Tests:
```
tests/e2e/test_e2e_complexity_assessment.py::test_complex_query_complexity
tests/e2e/test_e2e_complexity_assessment.py::test_moderate_query_complexity
tests/e2e/test_e2e_complexity_assessment.py::test_simple_query_complexity
```

#### Code Locations to Fix:
1. `packages/soar/src/aurora_soar/phases/assess.py` lines 240-260 - Scoring algorithm
2. Need to add "domain keyword override" logic that forces MEDIUM+ when domain terms present

#### Priority: **P1** (Impacts user query routing decisions)

---

## Failure Category 2: E2E Database Persistence (6 Failures)

### Root Cause
**Location**: `packages/cli/src/aurora_cli/memory_manager.py` lines 568-627

**Issue**: Stats methods are PLACEHOLDER implementations that return hardcoded 0/empty.

#### Evidence from Code:
```python
# Lines 568-582
def _count_total_chunks(self) -> int:
    """Count total chunks in memory store."""
    try:
        # This is a simplified implementation
        # In reality, we'd query the store's database
        # For now, return 0 as placeholder
        # TODO: Implement proper chunk counting based on Store API
        return 0  # <--- HARDCODED!
    except Exception as e:
        logger.warning(f"Failed to count chunks: {e}")
        return 0

# Lines 584-595
def _count_unique_files(self) -> int:
    """Count unique files in memory store."""
    try:
        # TODO: Implement proper file counting based on Store API
        return 0  # <--- HARDCODED!
    except Exception as e:
        logger.warning(f"Failed to count files: {e}")
        return 0

# Lines 597-608
def _get_language_distribution(self) -> dict[str, int]:
    """Get distribution of chunks by language."""
    try:
        # TODO: Implement proper language distribution based on Store API
        return {}  # <--- HARDCODED!
    except Exception as e:
        logger.warning(f"Failed to get language distribution: {e}")
        return {}
```

**Why E2E Fails**:
1. User runs `aur mem index .` → Indexes 100 chunks successfully
2. User runs `aur mem stats` → Shows "0 chunks" because `_count_total_chunks()` returns 0
3. E2E test: `assert stats.total_chunks > 0` → FAILS

**Why Unit Tests Pass**: Unit tests likely mock these methods or don't test the actual database queries.

#### Failing Tests:
```
tests/e2e/test_e2e_database_persistence.py::test_data_persists_across_sessions
tests/e2e/test_e2e_database_persistence.py::test_stats_reflect_indexed_data
tests/e2e/test_e2e_database_persistence.py::test_database_path_from_config
```

#### Code Locations to Fix:
1. `packages/cli/src/aurora_cli/memory_manager.py` lines 568-582 - `_count_total_chunks()`
2. `packages/cli/src/aurora_cli/memory_manager.py` lines 584-595 - `_count_unique_files()`
3. `packages/cli/src/aurora_cli/memory_manager.py` lines 597-608 - `_get_language_distribution()`

**Required Implementation**:
```python
def _count_total_chunks(self) -> int:
    """Count total chunks in memory store."""
    try:
        if hasattr(self.memory_store, '_transaction'):
            with self.memory_store._transaction() as conn:
                result = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
                return result[0] if result else 0
        return 0
    except Exception as e:
        logger.warning(f"Failed to count chunks: {e}")
        return 0

def _count_unique_files(self) -> int:
    """Count unique files in memory store."""
    try:
        if hasattr(self.memory_store, '_transaction'):
            with self.memory_store._transaction() as conn:
                result = conn.execute(
                    "SELECT COUNT(DISTINCT metadata->>'file_path') FROM chunks"
                ).fetchone()
                return result[0] if result else 0
        return 0
    except Exception as e:
        logger.warning(f"Failed to count files: {e}")
        return 0

def _get_language_distribution(self) -> dict[str, int]:
    """Get distribution of chunks by language."""
    try:
        if hasattr(self.memory_store, '_transaction'):
            with self.memory_store._transaction() as conn:
                rows = conn.execute(
                    "SELECT metadata->>'language', COUNT(*) FROM chunks GROUP BY metadata->>'language'"
                ).fetchall()
                return {row[0]: row[1] for row in rows if row[0]}
        return {}
    except Exception as e:
        logger.warning(f"Failed to get language distribution: {e}")
        return {}
```

#### Priority: **P0** (Critical - blocks verification of indexing functionality)

---

## Failure Category 3: E2E Git BLA Initialization (11 Failures)

### Root Cause
**Location**: `packages/cli/src/aurora_cli/memory_manager.py` lines 207-315

**Issue**: Git BLA initialization code EXISTS but has EXECUTION PATH issues.

#### Evidence from Code:
```python
# Lines 207-215 - Git extractor initialization
try:
    git_extractor = GitSignalExtractor()
    logger.debug(f"Initialized GitSignalExtractor for {path}")
except Exception as e:
    logger.warning(
        f"Could not initialize Git extractor: {e}. Using default BLA values."
    )
    git_extractor = None  # <--- Falls back to None silently

# Lines 238-280 - Git BLA calculation
if (
    git_extractor
    and hasattr(chunk, "line_start")
    and hasattr(chunk, "line_end")
):
    try:
        # Get commit times for this specific function
        commit_times = git_extractor.get_function_commit_times(
            file_path=str(file_path),
            line_start=chunk.line_start,
            line_end=chunk.line_end,
        )

        if commit_times:
            initial_bla = git_extractor.calculate_bla(
                commit_times, decay=0.5
            )
            commit_count = len(commit_times)
```

**Why E2E Fails**:
1. E2E test creates temp directory with git repo
2. Code runs `GitSignalExtractor()` initialization
3. If init fails (wrong repo path, permissions, etc.), code silently falls back to `git_extractor = None`
4. All subsequent BLA calculations are skipped (lines 241-243 condition fails)
5. E2E test: `assert chunk.base_level > 0.0` → FAILS (all chunks have BLA = 0.0)

**Why Unit Tests Pass**: Unit tests likely mock GitSignalExtractor or don't test actual git operations.

#### Failing Tests:
```
tests/e2e/test_e2e_git_bla_initialization.py::test_bla_values_initialized_from_git
tests/e2e/test_e2e_git_bla_initialization.py::test_activation_decay_over_time
tests/e2e/test_e2e_git_bla_initialization.py::test_commit_count_tracking
```

#### Code Locations to Fix:
1. `packages/cli/src/aurora_cli/memory_manager.py` lines 207-215 - Git extractor initialization
2. `packages/context_code/src/aurora_context_code/git.py` - GitSignalExtractor class

**Required Fixes**:
1. Add better error logging to understand WHY GitSignalExtractor initialization fails
2. Ensure GitSignalExtractor uses correct repo path (from config or cwd)
3. Add fallback strategy that still sets reasonable BLA values (not 0.0) even without git
4. E2E tests should verify git_extractor is not None before proceeding

#### Priority: **P1** (Important - impacts activation tracking quality)

---

## Failure Category 4: E2E New User Workflow (7 Failures)

### Root Cause
**Location**: `packages/cli/src/aurora_cli/config.py` lines 211-345

**Issue**: Config file search order might not respect E2E test environment isolation.

#### Evidence from Code:
```python
# Lines 237-247 - Config file search order
def load_config(path: str | None = None) -> Config:
    if path is None:
        search_paths = [
            Path("./aurora.config.json"),  # Current directory
            _get_aurora_home() / "config.json",  # Aurora home
        ]

        for search_path in search_paths:
            if search_path.exists():
                path = str(search_path)
                break

# Lines 197-208 - Aurora home detection
def _get_aurora_home() -> Path:
    """Get Aurora home directory, respecting AURORA_HOME environment variable."""
    aurora_home_env = os.environ.get("AURORA_HOME")
    if aurora_home_env:
        return Path(aurora_home_env)
    return Path.home() / ".aurora"
```

**Why E2E Fails**:
1. E2E test sets `AURORA_HOME` environment variable to temp directory
2. Test creates config file in `$AURORA_HOME/config.json`
3. CLI command runs in different working directory
4. `load_config()` first checks `./aurora.config.json` in cwd (line 240)
5. If found (from previous test run), uses wrong config!
6. E2E test expects config from temp dir, but CLI uses config from cwd

**Why Unit Tests Pass**: Unit tests likely run in clean environments without stale config files.

#### Failing Tests:
```
tests/e2e/test_e2e_new_user_workflow.py::test_first_time_setup
tests/e2e/test_e2e_new_user_workflow.py::test_config_creation
tests/e2e/test_e2e_new_user_workflow.py::test_directory_initialization
```

#### Code Locations to Fix:
1. `packages/cli/src/aurora_cli/config.py` lines 237-247 - Config search order
2. E2E test fixtures should clean up after themselves more thoroughly

**Required Fixes**:
1. Change config search order: Prioritize `AURORA_HOME` over cwd when env var is set
2. E2E tests should explicitly pass `--config` path to CLI commands to avoid ambiguity
3. Add logging to show which config file was loaded

#### Priority: **P2** (Medium - impacts onboarding experience)

---

## Failure Category 5: E2E Query/Search Tests (13+ Failures)

### Root Cause Analysis

**Location**: Multiple locations in search/query flow

**Issue**: Queries DO retrieve from index, but the RESULTS are broken due to upstream issues.

#### Evidence from Code Path Tracing:

**Path 1**: `aur mem search` command
```
packages/cli/src/aurora_cli/commands/memory.py:214
  → manager.search(query, limit=limit)
    → packages/cli/src/aurora_cli/memory_manager.py:357
      → HybridRetriever.retrieve(query, top_k=limit)
        → Returns results with activation_score, semantic_score, hybrid_score
```

**Path 2**: `aur query` command
```
packages/cli/src/aurora_cli/main.py
  → QueryExecutor.execute_with_auto_escalation()
    → packages/cli/src/aurora_cli/execution.py:182
      → assess_complexity(query)  # FAILS HERE - always returns SIMPLE
      → execute_direct_llm(query, memory_store=store)
        → _get_memory_context(memory_store, query, limit=3)
          → packages/cli/src/aurora_cli/execution.py:417
            → manager.search(query, limit=limit)  # Returns empty due to stats bug
```

**Why E2E Fails - Cascading Failures**:
1. **Stats Bug**: `_count_total_chunks()` returns 0 → Search thinks DB is empty
2. **Complexity Bug**: Queries classified as SIMPLE → Don't use memory properly
3. **BLA Bug**: All activation scores are 0.0 → Ranking is broken
4. **Result**: Queries return wrong results or empty results

#### Failing Tests:
```
tests/e2e/test_e2e_query_uses_index.py::test_query_uses_memory
tests/e2e/test_e2e_query_uses_index.py::test_direct_llm_includes_context
tests/e2e/test_e2e_search_accuracy.py::test_different_queries_return_different_results
tests/e2e/test_e2e_search_accuracy.py::test_activation_scores_have_variance
tests/e2e/test_e2e_search_accuracy.py::test_semantic_scores_vary_by_relevance
```

#### Code Locations to Fix:
This is a **CASCADING FAILURE** - fixing Categories 1, 2, and 3 will automatically fix most of Category 5.

**Additional Issues**:
1. `packages/cli/src/aurora_cli/memory_manager.py` line 443 - Search might not be recording access properly
2. `packages/context_code/src/aurora_context_code/semantic/hybrid_retriever.py` - Hybrid scoring might have issues

#### Priority: **P0** (Critical - core functionality broken)

---

## Failure Category 6: Integration Tests (2 Failures)

### Root Cause
**Location**: `packages/cli/src/aurora_cli/execution.py` lines 182-291

**Issue**: Auto-escalation logic works, but relies on broken complexity assessment.

#### Evidence from Code:
```python
# Lines 219-231
def execute_with_auto_escalation(self, query: str, ...):
    # Assess query complexity
    from aurora_soar.phases.assess import assess_complexity

    llm = self._initialize_llm_client(api_key)
    assessment = assess_complexity(query, llm_client=llm)

    complexity = assessment.get("complexity", "SIMPLE")
    confidence = assessment.get("confidence", 1.0)

    # ... escalation logic based on complexity and confidence
```

**Why Integration Tests Fail**:
1. Test calls `execute_with_auto_escalation()` with COMPLEX query
2. `assess_complexity()` returns "SIMPLE" (due to Category 1 bug)
3. Query is NOT escalated to SOAR
4. Test expects SOAR execution, but gets direct LLM
5. Test: `assert metadata['escalated'] == True` → FAILS

#### Failing Tests:
```
tests/integration/test_auto_escalation.py::test_auto_escalation_threshold
tests/integration/test_retrieval_context.py::test_retrieval_context_passing
```

#### Code Locations to Fix:
This is a **DEPENDENT FAILURE** - fixing Category 1 (complexity assessment) will automatically fix Category 6.

#### Priority: **P1** (Blocked by Category 1)

---

## Priority-Ordered Remediation Plan

### Phase 2A: Critical Blockers (P0) - Fix First
**Goal**: Restore core indexing and search functionality

1. **Fix Stats Methods** (Category 2)
   - File: `packages/cli/src/aurora_cli/memory_manager.py`
   - Lines: 568-627
   - Change: Implement actual database queries instead of returning 0/empty
   - Estimated Effort: 2 hours
   - Test: `pytest tests/e2e/test_e2e_database_persistence.py -v`

2. **Fix Query/Search Results** (Category 5)
   - Dependencies: Fix #1 must complete first
   - File: Multiple (see Category 5 analysis)
   - Change: Verify search chain works after stats fix
   - Estimated Effort: 1 hour (mostly verification)
   - Test: `pytest tests/e2e/test_e2e_query_uses_index.py -v`

### Phase 2B: High Priority (P1) - Fix Second
**Goal**: Restore intelligent query routing and activation tracking

3. **Fix Complexity Assessment** (Category 1)
   - File: `packages/soar/src/aurora_soar/phases/assess.py`
   - Lines: 209-260
   - Change: Add domain keyword override logic
   - Estimated Effort: 3 hours
   - Test: `pytest tests/e2e/test_e2e_complexity_assessment.py -v`

4. **Fix Git BLA Initialization** (Category 3)
   - File: `packages/cli/src/aurora_cli/memory_manager.py`, `packages/context_code/src/aurora_context_code/git.py`
   - Lines: 207-315
   - Change: Better error handling, repo path detection
   - Estimated Effort: 4 hours
   - Test: `pytest tests/e2e/test_e2e_git_bla_initialization.py -v`

5. **Fix Auto-Escalation** (Category 6)
   - Dependencies: Fix #3 must complete first
   - File: `packages/cli/src/aurora_cli/execution.py`
   - Change: Verify escalation logic works after complexity fix
   - Estimated Effort: 1 hour (mostly verification)
   - Test: `pytest tests/integration/test_auto_escalation.py -v`

### Phase 2C: Medium Priority (P2) - Fix Third
**Goal**: Polish onboarding and config management

6. **Fix New User Workflow** (Category 4)
   - File: `packages/cli/src/aurora_cli/config.py`
   - Lines: 237-247
   - Change: Prioritize AURORA_HOME over cwd in config search
   - Estimated Effort: 2 hours
   - Test: `pytest tests/e2e/test_e2e_new_user_workflow.py -v`

---

## Test Strategy for Verification

### Pre-Fix Baseline
```bash
# Capture current failure count
pytest tests/e2e/ tests/integration/ -v --tb=short > baseline_failures.txt
grep "FAILED" baseline_failures.txt | wc -l  # Should be 48+
```

### Fix Verification (After Each Fix)
```bash
# After fixing stats methods (Fix #1)
pytest tests/e2e/test_e2e_database_persistence.py -v
pytest tests/e2e/test_e2e_query_uses_index.py::test_query_uses_memory -v

# After fixing complexity assessment (Fix #3)
pytest tests/e2e/test_e2e_complexity_assessment.py -v
pytest tests/integration/test_auto_escalation.py -v

# After fixing Git BLA (Fix #4)
pytest tests/e2e/test_e2e_git_bla_initialization.py -v

# After fixing config (Fix #6)
pytest tests/e2e/test_e2e_new_user_workflow.py -v
```

### Full Regression Check
```bash
# After all fixes, run complete E2E + integration suite
pytest tests/e2e/ tests/integration/ -v --tb=short
pytest tests/unit/ -v  # Ensure unit tests still pass

# Run full quality check
make quality-check
```

### Manual Verification (Critical Workflows)
```bash
# Test 1: Index and Search
cd /tmp/test_project
aur mem index .
aur mem stats  # Should show >0 chunks
aur mem search "function"  # Should return varied results

# Test 2: Query with Memory
aur query "How does SOAR work?"  # Should be classified as MEDIUM/COMPLEX

# Test 3: New User Setup
rm -rf ~/.aurora
aur --verify  # Should create config and prompt for setup
```

---

## Dependency Graph

```
Fix #1 (Stats) → Fix #2 (Query/Search)
Fix #3 (Complexity) → Fix #5 (Auto-Escalation)
Fix #4 (Git BLA) → (Independent, improves activation quality)
Fix #6 (Config) → (Independent, improves onboarding)
```

**Critical Path**: Fix #1 → Fix #2 → Fix #3 → Fix #5

**Estimated Total Effort**: 13 hours (with parallel work on independent fixes)

---

## Code Review Checklist (Post-Fix)

For each fix, verify:

- [ ] Implementation matches specification (no more placeholder code)
- [ ] Unit tests updated to test actual behavior (not mocked)
- [ ] E2E tests pass for this category
- [ ] No regression in other test categories
- [ ] Code follows existing patterns (no breaking changes)
- [ ] Error handling is robust (no silent failures)
- [ ] Logging is adequate for debugging
- [ ] Documentation updated if API changes

---

## Root Cause Summary - Why Unit Tests Passed but E2E Failed

### The "Wrong References" Pattern

All failures follow the same pattern:
1. **Function signature exists** → Type checker passes
2. **Function returns correct type** → Unit tests pass (mocked or default values)
3. **Function doesn't do actual work** → E2E tests fail (real execution)

**Examples**:
- `_count_total_chunks()` exists, returns `int`, but returns hardcoded `0`
- `assess_complexity()` exists, returns `dict`, but classification logic is wrong
- `GitSignalExtractor()` exists, initializes, but fails silently and falls back to None

### Why This Happened

**Phase 1 Implementation Strategy** likely focused on:
1. Creating function signatures and interfaces
2. Ensuring type correctness for mypy
3. Writing unit tests with mocks
4. Getting lint/type/security checks to pass

**What Was Missed**:
1. Actual implementation of TODO methods
2. End-to-end integration testing
3. Runtime behavior verification
4. Database query implementation

**Lesson Learned**: CI/CD should block on E2E test failures, not just unit tests + lint.

---

## Appendix: Detailed Code Locations Reference

### File: packages/cli/src/aurora_cli/memory_manager.py
- Lines 568-582: `_count_total_chunks()` - **FIX REQUIRED**
- Lines 584-595: `_count_unique_files()` - **FIX REQUIRED**
- Lines 597-608: `_get_language_distribution()` - **FIX REQUIRED**
- Lines 207-215: Git extractor initialization - **IMPROVE ERROR HANDLING**
- Lines 238-280: Git BLA calculation - **VERIFY EXECUTION PATH**

### File: packages/soar/src/aurora_soar/phases/assess.py
- Lines 33-158: Keyword sets - **CORRECT, NO CHANGES**
- Lines 209-260: `_assess_tier1_keyword()` - **FIX SCORING ALGORITHM**

### File: packages/cli/src/aurora_cli/config.py
- Lines 237-247: `load_config()` search order - **PRIORITIZE AURORA_HOME**
- Lines 197-208: `_get_aurora_home()` - **CORRECT, NO CHANGES**

### File: packages/cli/src/aurora_cli/execution.py
- Lines 182-291: `execute_with_auto_escalation()` - **VERIFY AFTER FIX #3**
- Lines 417-461: `_get_memory_context()` - **CORRECT, NO CHANGES**

### File: packages/cli/src/aurora_cli/commands/memory.py
- Lines 59-139: `index_command()` - **CORRECT, NO CHANGES**
- Lines 141-234: `search_command()` - **CORRECT, NO CHANGES**
- Lines 236-299: `stats_command()` - **VERIFY AFTER FIX #1**

---

## Next Steps

1. **Review this document** with team for accuracy
2. **Assign fixes** to developers (parallelizable except dependencies)
3. **Create tracking issues** for each fix category
4. **Implement fixes** in priority order (P0 → P1 → P2)
5. **Run verification** after each fix
6. **Full regression** before merging

**Target**: All 48+ E2E/Integration tests passing within 2-3 days.
