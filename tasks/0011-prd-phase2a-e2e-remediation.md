# Phase 2A: E2E Test Failure Remediation - Product Requirements Document

**Version**: 1.0
**Date**: 2025-12-29
**Status**: Ready for Implementation
**Target Release**: v0.2.1
**Priority**: P0 (Critical - Blocking)

---

## Table of Contents

1. [Introduction/Overview](#introductionoverview)
2. [Goals](#goals)
3. [User Stories](#user-stories)
4. [Root Cause Analysis](#root-cause-analysis)
5. [Functional Requirements](#functional-requirements)
6. [Non-Goals (Out of Scope)](#non-goals-out-of-scope)
7. [Technical Considerations](#technical-considerations)
8. [Implementation Strategy](#implementation-strategy)
9. [Success Metrics](#success-metrics)
10. [Testing Strategy](#testing-strategy)
11. [Documentation Requirements](#documentation-requirements)
12. [Open Questions](#open-questions)

---

## Introduction/Overview

### Problem Statement

After Phase 1 implementation focused on type correctness and unit test coverage, CI/CD reveals **48+ E2E and integration test failures**. All failures stem from a common "placeholder implementation pattern":

- ✅ Function signatures exist (type checking passes)
- ✅ Return types are correct (unit tests pass with mocks)
- ❌ Non-functional implementations (E2E tests fail with real execution)

**Example of the pattern:**
```python
def _count_total_chunks(self) -> int:
    """Count total chunks in memory store."""
    try:
        # TODO: Implement proper chunk counting
        return 0  # <--- HARDCODED PLACEHOLDER!
    except Exception as e:
        logger.warning(f"Failed to count chunks: {e}")
        return 0
```

This pattern exists across 6 critical failure categories, breaking core Aurora functionality when components integrate end-to-end.

### High-Level Goal

Replace all placeholder implementations with functional code that passes E2E tests, eliminating the gap between unit test success and runtime correctness.

### Scope

**In Scope:**
- Fix 6 identified failure categories (48+ tests)
- Audit entire codebase for similar placeholder patterns
- Add E2E test gate to CI/CD pipeline
- Update developer documentation

**Out of Scope:**
- New features or enhancements
- Performance optimization beyond correctness
- User-facing documentation updates
- MCP-specific improvements

---

## Goals

### Primary Goals

1. **Restore Core Functionality**: All 48+ E2E and integration tests pass
2. **Eliminate Placeholders**: No TODO/placeholder implementations remain in affected code paths
3. **Prevent Regression**: CI/CD blocks on E2E test failures going forward
4. **Maintain Quality**: Full test suite passes + `make quality-check` succeeds

### Secondary Goals

1. **Code Quality**: Basic error handling and logging for new implementations
2. **Documentation**: Update developer docs with corrected behavior and troubleshooting
3. **Pattern Detection**: Identify and fix similar placeholder patterns proactively

### Non-Goals (Explicitly Out of Scope)

- Comprehensive performance optimization
- Advanced error recovery mechanisms
- User-facing CLI/MCP enhancements
- New E2E test coverage beyond fixing existing failures

---

## User Stories

### Story 1: Developer Verifying Indexing
**As a** developer running the test suite
**I want** `aur mem stats` to show actual chunk counts after indexing
**So that** I can verify data persistence works correctly

**Acceptance Criteria:**
- After indexing N files, `aur mem stats` reports >0 chunks
- Stats methods query actual database, not hardcoded values
- E2E test `test_stats_reflect_indexed_data` passes

---

### Story 2: Developer Testing Search Quality
**As a** developer testing search functionality
**I want** different queries to return different, relevant results
**So that** I can verify hybrid retrieval works as designed

**Acceptance Criteria:**
- Query "SOAR" returns different results than query "database"
- Activation scores vary based on access patterns
- Semantic scores reflect relevance, not all 1.0
- E2E test `test_different_queries_return_different_results` passes

---

### Story 3: Developer Testing Complexity Assessment
**As a** developer testing SOAR routing
**I want** domain-specific queries to be classified as MEDIUM/COMPLEX
**So that** proper reasoning pipelines are triggered

**Acceptance Criteria:**
- Query "How does SOAR work?" classified as MEDIUM (not SIMPLE)
- Domain keywords (SOAR, ACT-R, orchestration) boost complexity score
- E2E test `test_complex_query_complexity` passes

---

### Story 4: Developer Testing Git Integration
**As a** developer indexing a git repository
**I want** chunks to have activation scores based on commit history
**So that** recently changed code ranks higher in search

**Acceptance Criteria:**
- GitSignalExtractor initializes successfully for valid repos
- Chunks have base_level > 0.0 derived from git history
- Clear error message if git initialization fails
- Fallback to reasonable default (0.5) for non-git directories
- E2E test `test_bla_values_initialized_from_git` passes

---

### Story 5: Developer Testing Config Management
**As a** developer running E2E tests
**I want** CLI commands to respect AURORA_HOME environment variable
**So that** test isolation works and stale configs don't interfere

**Acceptance Criteria:**
- When AURORA_HOME is set, config loaded from $AURORA_HOME/config.json
- CWD config only used if AURORA_HOME not set
- E2E test `test_first_time_setup` passes

---

### Story 6: Developer Running CI/CD
**As a** developer pushing code
**I want** CI/CD to fail if E2E tests don't pass
**So that** placeholder implementations can't merge to main

**Acceptance Criteria:**
- GitHub Actions runs E2E test suite
- Pipeline fails if any E2E test fails
- Test report shows which category failed
- E2E gate runs after unit tests, before merge

---

## Root Cause Analysis

### The "Placeholder Implementation Pattern"

Phase 1 focused on creating correct **interfaces** without complete **implementations**:

| Aspect | Phase 1 Status | Phase 2A Requirement |
|--------|---------------|---------------------|
| Function signatures | ✅ Exist | ✅ Maintain |
| Type annotations | ✅ Correct | ✅ Maintain |
| Return types | ✅ Match signatures | ✅ Maintain |
| **Runtime behavior** | ❌ **Hardcoded/placeholder** | ✅ **Functional** |
| Unit tests | ✅ Pass (mocked) | ✅ Maintain passing |
| E2E tests | ❌ Fail (real execution) | ✅ **Must pass** |

### Why Unit Tests Passed But E2E Failed

**Unit Test Pattern (Passed):**
```python
@patch('aurora_cli.memory_manager.MemoryManager._count_total_chunks')
def test_stats_command(mock_count):
    mock_count.return_value = 100  # Mocked!
    result = manager.get_stats()
    assert result.total_chunks == 100  # ✅ Passes
```

**E2E Test Pattern (Failed):**
```python
def test_stats_reflect_indexed_data():
    # Real execution, no mocks
    manager.index_directory("/path/to/code")
    stats = manager.get_stats()
    assert stats.total_chunks > 0  # ❌ Fails - returns 0!
```

### The 6 Failure Categories

| Category | Tests Failing | Root Cause | Priority |
|----------|--------------|------------|----------|
| 1. E2E Complexity Assessment | 9 | Keyword scoring algorithm broken for domain terms | P1 |
| 2. E2E Database Persistence | 6 | Stats methods return hardcoded 0/empty | P0 |
| 3. E2E Git BLA Initialization | 11 | Silent failures, poor error handling | P1 |
| 4. E2E New User Workflow | 7 | Config search order ignores AURORA_HOME | P2 |
| 5. E2E Query/Search Tests | 13+ | Cascading failure from #1, #2, #3 | P0 |
| 6. Integration Auto-Escalation | 2 | Dependent on #1 (complexity) | P1 |

**Critical Path Dependencies:**
```
Fix #2 (Stats) → Fix #5 (Query/Search)
Fix #1 (Complexity) → Fix #6 (Auto-Escalation)
Fix #3 (Git BLA) → (Independent, improves quality)
Fix #4 (Config) → (Independent, improves isolation)
```

---

## Functional Requirements

### FR-1: Stats Methods Return Real Data (Category 2 - P0)

**Requirement**: Stats methods in `MemoryManager` must query actual database.

#### FR-1.1: Implement `_count_total_chunks()`
**The system must** execute SQL query `SELECT COUNT(*) FROM chunks` against the store's database.

**Specification:**
- Method: `aurora_cli.memory_manager.MemoryManager._count_total_chunks()`
- Location: `packages/cli/src/aurora_cli/memory_manager.py:568-582`
- Implementation:
  ```python
  def _count_total_chunks(self) -> int:
      """Count total chunks in memory store."""
      try:
          if hasattr(self.memory_store, '_transaction'):
              with self.memory_store._transaction() as conn:
                  result = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
                  return result[0] if result else 0
          logger.warning("Store does not support direct SQL queries")
          return 0
      except Exception as e:
          logger.error(f"Failed to count chunks: {e}")
          return 0
  ```
- Error Handling: Log error, return 0 (graceful degradation)
- Test: `pytest tests/e2e/test_e2e_database_persistence.py::test_stats_reflect_indexed_data -v`

#### FR-1.2: Implement `_count_unique_files()`
**The system must** execute SQL query `SELECT COUNT(DISTINCT metadata->>'file_path') FROM chunks`.

**Specification:**
- Method: `aurora_cli.memory_manager.MemoryManager._count_unique_files()`
- Location: `packages/cli/src/aurora_cli/memory_manager.py:584-595`
- Implementation:
  ```python
  def _count_unique_files(self) -> int:
      """Count unique files in memory store."""
      try:
          if hasattr(self.memory_store, '_transaction'):
              with self.memory_store._transaction() as conn:
                  result = conn.execute(
                      "SELECT COUNT(DISTINCT metadata->>'file_path') FROM chunks"
                  ).fetchone()
                  return result[0] if result else 0
          logger.warning("Store does not support direct SQL queries")
          return 0
      except Exception as e:
          logger.error(f"Failed to count files: {e}")
          return 0
  ```
- Error Handling: Log error, return 0
- Test: Same as FR-1.1

#### FR-1.3: Implement `_get_language_distribution()`
**The system must** execute SQL query `SELECT metadata->>'language', COUNT(*) FROM chunks GROUP BY metadata->>'language'`.

**Specification:**
- Method: `aurora_cli.memory_manager.MemoryManager._get_language_distribution()`
- Location: `packages/cli/src/aurora_cli/memory_manager.py:597-608`
- Implementation:
  ```python
  def _get_language_distribution(self) -> dict[str, int]:
      """Get distribution of chunks by language."""
      try:
          if hasattr(self.memory_store, '_transaction'):
              with self.memory_store._transaction() as conn:
                  rows = conn.execute(
                      "SELECT metadata->>'language', COUNT(*) FROM chunks "
                      "GROUP BY metadata->>'language'"
                  ).fetchall()
                  return {row[0]: row[1] for row in rows if row[0]}
          logger.warning("Store does not support direct SQL queries")
          return {}
      except Exception as e:
          logger.error(f"Failed to get language distribution: {e}")
          return {}
  ```
- Error Handling: Log error, return empty dict
- Test: Same as FR-1.1

#### FR-1.4: Database Schema Validation
**The system must** validate that required database schema exists before executing queries.

**Specification:**
- Add schema validation method to `SQLiteStore`
- Check for tables: `chunks`, `activations`, `metadata`
- Check for required columns in each table
- Log clear error if schema is incomplete
- Document schema assumptions in `docs/architecture/DATABASE_SCHEMA.md`

**Success Criteria:**
- All stats methods return actual counts from database
- E2E test `test_stats_reflect_indexed_data` passes
- No hardcoded 0 or empty returns in happy path

---

### FR-2: Query/Search Return Relevant Results (Category 5 - P0)

**Requirement**: Search and query operations must retrieve and return relevant, varied results.

**Note**: This is primarily a cascading fix dependent on FR-1, FR-3, and FR-4. Most work is verification.

#### FR-2.1: Verify Search Uses Real Database
**The system must** confirm search retrieves from populated database, not empty/wrong DB.

**Specification:**
- Depends on: FR-1 (stats methods working proves DB is populated)
- Verification: After FR-1, run `pytest tests/e2e/test_e2e_query_uses_index.py -v`
- Expected: Tests pass without code changes

#### FR-2.2: Verify Activation Scores Vary
**The system must** return varied activation scores based on access patterns.

**Specification:**
- Depends on: FR-4 (Git BLA working)
- Verification: Check that `test_activation_scores_have_variance` passes
- If fails: Audit `HybridRetriever.retrieve()` for normalization bugs

#### FR-2.3: Verify Semantic Scores Vary
**The system must** return varied semantic scores based on query relevance.

**Specification:**
- Verification: Check that `test_semantic_scores_vary_by_relevance` passes
- If fails: Audit embedding generation during indexing
- Common issue: Embeddings not computed, all default to same vector

**Success Criteria:**
- Different queries return different results
- Activation scores show variance (not all 1.0)
- Semantic scores show variance (not all 1.0)
- E2E tests in `test_e2e_query_uses_index.py` and `test_e2e_search_accuracy.py` pass

---

### FR-3: Complexity Assessment Handles Domain Keywords (Category 1 - P1)

**Requirement**: Complexity assessment must correctly classify domain-specific queries.

#### FR-3.1: Add Domain Keyword Override Logic
**The system must** boost complexity score when domain-specific keywords are present.

**Specification:**
- File: `packages/soar/src/aurora_soar/phases/assess.py`
- Location: Lines 209-260 (`_assess_tier1_keyword` function)
- Changes:
  1. Add domain keyword detection before standard scoring
  2. If domain keywords present, force minimum MEDIUM classification
  3. Preserve existing keyword matching for non-domain queries

**Implementation:**
```python
def _assess_tier1_keyword(query: str) -> tuple[str, float, float]:
    query_lower = query.lower()
    query_words = set(re.findall(r"\b\w+\b", query_lower))

    # Domain keyword override - if present, minimum MEDIUM
    domain_keywords = {
        "soar", "actr", "act-r", "aurora", "orchestration",
        "activation", "retrieval", "reasoning", "agentic",
        "marketplace", "cognitive", "memory"
    }

    domain_matches = query_words & domain_keywords
    if domain_matches:
        # Domain query detected - force MEDIUM minimum
        logger.debug(f"Domain keywords detected: {domain_matches}")
        # Calculate base score, but ensure >= MEDIUM threshold
        simple_matches = len(query_words & SIMPLE_KEYWORDS)
        medium_matches = len(query_words & MEDIUM_KEYWORDS)
        complex_matches = len(query_words & COMPLEX_KEYWORDS)

        total_keywords = len(query_words)
        simple_score = simple_matches / total_keywords if total_keywords > 0 else 0
        medium_score = (medium_matches / total_keywords) * 1.2 if total_keywords > 0 else 0
        complex_score = (complex_matches / total_keywords) * 1.5 if total_keywords > 0 else 0

        # Apply domain boost - ensure score >= MEDIUM threshold (0.4)
        final_score = max(medium_score, 0.4)

        if complex_score > 0.5:
            return "COMPLEX", complex_score, 0.8
        else:
            return "MEDIUM", final_score, 0.7

    # Standard keyword matching (existing logic)
    # ... rest of existing implementation
```

#### FR-3.2: Multi-Question Detection
**The system must** detect multiple questions and boost complexity.

**Specification:**
- Add question mark counting: `question_count = query.count("?")`
- If `question_count >= 2`, boost score by 0.3 (max 1.0)
- Apply after domain keyword logic

#### FR-3.3: Scope Indicator Keywords
**The system must** recognize scope indicators that signal complex queries.

**Specification:**
- Add to MEDIUM_KEYWORDS: "research", "analyze", "compare", "design", "architecture"
- Add to MEDIUM_KEYWORDS: "list all", "find all", "explain how", "show me"
- Update keyword matching to handle multi-word phrases

**Success Criteria:**
- Query "How does SOAR work?" classified as MEDIUM (not SIMPLE)
- Query "research agentic ai market..." classified as COMPLEX
- E2E tests in `test_e2e_complexity_assessment.py` pass
- Confidence scores >= 0.6 for domain queries

---

### FR-4: Git BLA Initialization Handles Errors Properly (Category 3 - P1)

**Requirement**: Git BLA initialization must succeed reliably or fail gracefully with clear errors.

#### FR-4.1: Fix GitSignalExtractor Initialization
**The system must** accept explicit repo path parameter and validate it.

**Specification:**
- File: `packages/context_code/src/aurora_context_code/git.py`
- Class: `GitSignalExtractor`
- Changes:
  1. Add `repo_path: str | None = None` parameter to `__init__`
  2. If `repo_path` provided, use it; else use `cwd`
  3. Validate repo path before initializing pygit2.Repository
  4. Raise clear exception if repo invalid

**Implementation:**
```python
class GitSignalExtractor:
    def __init__(self, repo_path: str | None = None):
        """Initialize Git signal extractor.

        Args:
            repo_path: Path to git repository. If None, uses current directory.

        Raises:
            ValueError: If repo_path is not a valid git repository.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

        # Validate git repo exists
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(
                f"Not a git repository: {self.repo_path}\n"
                f"Git BLA requires a git repository with commit history.\n"
                f"Run 'git init && git add . && git commit -m \"Initial commit\"' first."
            )

        try:
            self.repo = pygit2.Repository(str(self.repo_path))
            logger.info(f"Initialized GitSignalExtractor for {self.repo_path}")
        except Exception as e:
            raise ValueError(
                f"Failed to open git repository at {self.repo_path}: {e}"
            ) from e
```

#### FR-4.2: Improve Error Handling in MemoryManager
**The system must** catch GitSignalExtractor errors and log clear messages.

**Specification:**
- File: `packages/cli/src/aurora_cli/memory_manager.py`
- Location: Lines 207-215
- Changes:
  1. Catch specific ValueError from GitSignalExtractor
  2. Log clear message explaining why Git BLA failed
  3. Log guidance on how to fix (git init, git commit)
  4. Continue with fallback BLA value

**Implementation:**
```python
# Lines 207-220
try:
    git_extractor = GitSignalExtractor(repo_path=str(path.parent))
    logger.debug(f"Initialized GitSignalExtractor for {path.parent}")
except ValueError as e:
    logger.warning(
        f"Git BLA initialization failed: {e}\n"
        f"Using default activation scores (BLA=0.5).\n"
        f"For git-based activation, ensure files are committed:\n"
        f"  git add . && git commit -m 'Initial commit'"
    )
    git_extractor = None
except Exception as e:
    logger.error(
        f"Unexpected error initializing Git extractor: {e}\n"
        f"Using default activation scores (BLA=0.5)."
    )
    git_extractor = None
```

#### FR-4.3: Implement Fallback BLA Strategy
**The system must** use reasonable default BLA (0.5) when Git not available.

**Specification:**
- When `git_extractor is None`, set `initial_bla = 0.5` (not 0.0)
- Rationale: 0.5 is neutral, better than 0.0 which suggests "never accessed"
- Log INFO message explaining fallback

**Implementation:**
```python
# Lines 240-260
if git_extractor and hasattr(chunk, "line_start") and hasattr(chunk, "line_end"):
    try:
        commit_times = git_extractor.get_function_commit_times(
            file_path=str(file_path),
            line_start=chunk.line_start,
            line_end=chunk.line_end,
        )
        if commit_times:
            initial_bla = git_extractor.calculate_bla(commit_times, decay=0.5)
            commit_count = len(commit_times)
        else:
            initial_bla = 0.5  # No commits for this chunk
            commit_count = 0
    except Exception as e:
        logger.warning(f"Failed to calculate Git BLA for {chunk.name}: {e}")
        initial_bla = 0.5
        commit_count = 0
else:
    # No git extractor or missing line info
    initial_bla = 0.5
    commit_count = 0
    logger.debug(f"Using default BLA (0.5) for chunk {chunk.name}")
```

#### FR-4.4: Handle Edge Cases
**The system must** handle shallow clones, detached HEAD, and other git edge cases.

**Specification:**
- Shallow clone detection: Check if `.git/shallow` exists
- Detached HEAD: Don't fail, just log warning
- Empty repo (no commits): Use BLA=0.5, don't crash
- Submodules: Handle gracefully, use parent repo

#### FR-4.5: E2E Testing with Real Repos
**The system must** pass E2E tests using real git repositories.

**Specification:**
- Test repos: `/home/hamr/PycharmProjects/aurora` and other real repos
- Test scenarios:
  1. Valid repo with commit history → BLA from git
  2. Non-git directory → BLA=0.5 fallback
  3. Shallow clone → BLA=0.5 with warning
  4. Empty repo (no commits) → BLA=0.5

**Success Criteria:**
- GitSignalExtractor initializes for valid repos
- Clear error messages for invalid repos
- Fallback BLA=0.5 used when git unavailable
- E2E tests in `test_e2e_git_bla_initialization.py` pass
- No silent failures (all failures logged)

---

### FR-5: Auto-Escalation Triggers on Low Confidence (Category 6 - P1)

**Requirement**: Auto-escalation from direct LLM to SOAR must work when confidence is low.

**Note**: This is primarily a verification fix dependent on FR-3 (complexity assessment).

#### FR-5.1: Verify Escalation Logic Exists
**The system must** confirm auto-escalation code is present and functional.

**Specification:**
- File: `packages/cli/src/aurora_cli/execution.py`
- Location: Lines 182-291 (`execute_with_auto_escalation`)
- Verification: Check that low confidence triggers SOAR

#### FR-5.2: Test After Complexity Fix
**The system must** pass integration tests after FR-3 is complete.

**Specification:**
- Depends on: FR-3 (complexity assessment working)
- Test: `pytest tests/integration/test_auto_escalation.py -v`
- Expected: Tests pass without code changes

#### FR-5.3: Add Logging for Escalation Decisions
**The system must** log when and why escalation occurs.

**Specification:**
- Add INFO log: "Auto-escalating to SOAR (confidence: {conf}, complexity: {comp})"
- Add DEBUG log with full assessment details

**Success Criteria:**
- Low confidence queries (<0.6) escalate to SOAR
- Integration test `test_auto_escalation_threshold` passes
- Clear logs explain escalation decisions

---

### FR-6: Config Search Prioritizes AURORA_HOME (Category 4 - P2)

**Requirement**: Config file search order must respect AURORA_HOME environment variable.

#### FR-6.1: Update Config Search Order
**The system must** check AURORA_HOME before CWD when environment variable is set.

**Specification:**
- File: `packages/cli/src/aurora_cli/config.py`
- Location: Lines 237-247 (`load_config` function)
- Changes:
  1. If AURORA_HOME env var set, prioritize $AURORA_HOME/config.json
  2. If AURORA_HOME not set, use existing order (CWD → ~/.aurora)

**Implementation:**
```python
def load_config(path: str | None = None) -> Config:
    """Load configuration from file.

    Search order:
    1. Explicit path parameter (if provided)
    2. $AURORA_HOME/config.json (if AURORA_HOME env var set)
    3. ./aurora.config.json (current directory)
    4. ~/.aurora/config.json (default home)
    """
    if path is None:
        search_paths = []

        # Priority 1: AURORA_HOME if set
        aurora_home_env = os.environ.get("AURORA_HOME")
        if aurora_home_env:
            search_paths.append(Path(aurora_home_env) / "config.json")

        # Priority 2: Current directory
        search_paths.append(Path("./aurora.config.json"))

        # Priority 3: Default home
        if not aurora_home_env:  # Only add if AURORA_HOME not set
            search_paths.append(_get_aurora_home() / "config.json")

        for search_path in search_paths:
            if search_path.exists():
                logger.info(f"Loading config from {search_path}")
                path = str(search_path)
                break

    # Rest of existing implementation...
```

#### FR-6.2: Add Config Source Logging
**The system must** log which config file was loaded.

**Specification:**
- Add INFO log: "Loading config from {path}"
- Add DEBUG log: "Config search paths: {search_paths}"
- Helps debugging E2E test isolation issues

**Success Criteria:**
- When AURORA_HOME set, config loaded from $AURORA_HOME/config.json
- E2E tests in `test_e2e_new_user_workflow.py` pass
- Config source logged clearly

---

### FR-7: Placeholder Pattern Audit (Scope Extension)

**Requirement**: Identify and fix all similar placeholder patterns across codebase.

#### FR-7.1: Automated Placeholder Detection
**The system must** scan codebase for common placeholder patterns.

**Specification:**
- Search patterns:
  - `return 0  # TODO`
  - `return {}  # TODO`
  - `return []  # TODO`
  - `pass  # TODO: Implement`
  - Hardcoded default returns in try/except with "TODO" comments
- Files to scan: All Python files in `packages/*/src/`
- Generate report: `docs/development/aurora_fixes/PLACEHOLDER_AUDIT.md`

#### FR-7.2: Fix High-Priority Placeholders
**The system must** fix placeholders in critical code paths.

**Specification:**
- Critical code paths:
  - Memory/storage operations
  - Search/retrieval logic
  - Activation tracking
  - Configuration management
- Lower priority: Non-critical utilities, optional features

#### FR-7.3: Document Intentional Placeholders
**The system must** document placeholders that are intentional (not bugs).

**Specification:**
- Change comment from `# TODO:` to `# PLACEHOLDER: Acceptable because...`
- Add justification for why placeholder is acceptable
- Example: Abstract base class methods

**Success Criteria:**
- Placeholder audit report generated
- All critical placeholders fixed
- Intentional placeholders documented
- No new E2E failures from audit fixes

---

### FR-8: CI/CD E2E Test Gate (Scope Extension)

**Requirement**: CI/CD pipeline must block merges when E2E tests fail.

#### FR-8.1: Add E2E Test Job to GitHub Actions
**The system must** run E2E tests in CI/CD pipeline.

**Specification:**
- File: `.github/workflows/test.yml`
- Add new job: `e2e-tests`
- Runs after: `unit-tests` job
- Command: `pytest tests/e2e/ tests/integration/ -v --tb=short`
- Fail pipeline if: Any E2E test fails

**Implementation:**
```yaml
  e2e-tests:
    name: E2E Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    needs: unit-tests  # Run after unit tests pass
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e "packages/core[dev]"
          pip install -e "packages/cli[dev]"
          # ... install all packages

      - name: Run E2E Tests
        run: |
          pytest tests/e2e/ tests/integration/ -v --tb=short
```

#### FR-8.2: Add Test Failure Categorization
**The system must** report which failure category caused pipeline failure.

**Specification:**
- Use pytest markers to categorize E2E tests
- Markers: `@pytest.mark.e2e_stats`, `@pytest.mark.e2e_complexity`, etc.
- CI summary shows failed categories

**Implementation:**
```python
# In test files
@pytest.mark.e2e_stats
def test_stats_reflect_indexed_data():
    ...

@pytest.mark.e2e_complexity
def test_complex_query_complexity():
    ...
```

```yaml
# In GitHub Actions
- name: Run E2E Tests with Category Reporting
  run: |
    pytest tests/e2e/ tests/integration/ -v --tb=short \
      --junit-xml=e2e-results.xml

    # Parse results and show failed categories
    python scripts/summarize_test_failures.py e2e-results.xml
```

#### FR-8.3: Require E2E Gate Before Merge
**The system must** configure GitHub branch protection to require E2E tests.

**Specification:**
- Branch: `main`
- Required status checks: `e2e-tests (Python 3.10)`
- Cannot merge if E2E tests fail

**Success Criteria:**
- E2E tests run automatically on PR
- Pipeline fails if E2E tests fail
- Test report shows which category failed
- Branch protection blocks merge on failure

---

## Non-Goals (Out of Scope)

### Explicitly NOT Included in Phase 2A

1. **Performance Optimization**
   - Query response time improvements
   - Database query optimization beyond correctness
   - Caching strategies
   - *Rationale*: Focus on correctness first, performance later

2. **Advanced Error Recovery**
   - Retry logic for transient failures
   - Graceful degradation strategies beyond basic fallbacks
   - Circuit breaker patterns
   - *Rationale*: Basic error handling sufficient for v0.2.1

3. **User-Facing Documentation**
   - CLI_USAGE_GUIDE.md updates
   - User-facing examples
   - Tutorial updates
   - *Rationale*: No user-visible behavior changes

4. **New Features**
   - New CLI commands
   - New E2E test coverage areas
   - Enhanced SOAR capabilities
   - *Rationale*: Strictly remediation phase

5. **MCP-Specific Work**
   - MCP tool improvements
   - Claude Desktop integration enhancements
   - MCP server optimizations
   - *Rationale*: Separate PRD (Phase 2B)

6. **Comprehensive Logging Framework**
   - Structured logging (JSON)
   - Log aggregation
   - Detailed debug instrumentation
   - *Rationale*: Basic logging sufficient

---

## Technical Considerations

### Architecture Constraints

1. **Database Access Pattern**
   - SQLiteStore uses `_transaction()` context manager
   - Direct SQL queries require `hasattr(store, '_transaction')` check
   - Graceful fallback required for alternative store implementations

2. **Git Repository Requirements**
   - GitSignalExtractor requires pygit2 library
   - Must handle non-git directories gracefully
   - Shallow clones have limited history

3. **Backward Compatibility**
   - Existing unit tests must continue passing
   - No breaking changes to public APIs
   - Config file format unchanged

### Technology Stack

- **Language**: Python 3.10+ (currently 3.10, 3.11, 3.12 supported)
- **Database**: SQLite with JSON metadata columns
- **Git Library**: pygit2
- **Testing**: pytest with E2E fixtures
- **CI/CD**: GitHub Actions

### Performance Targets

- Stats queries: <100ms (database queries are fast)
- Complexity assessment: No degradation from current performance
- Git BLA initialization: <5s for typical repo (acceptable for indexing)
- E2E test suite: <10 minutes total (acceptable for CI/CD)

### Security Considerations

- **SQL Injection**: Use parameterized queries (already standard practice)
- **Path Traversal**: Validate repo paths before accessing filesystem
- **Error Information Leakage**: Don't expose internal paths in user-facing errors

### Dependencies

**New Dependencies**: None (all required libraries already in use)

**Version Constraints**:
- pygit2: >=1.12.0 (existing)
- sqlite3: Built-in to Python (no version constraint)

### Integration Points

1. **MemoryManager ↔ SQLiteStore**: Direct SQL query access via `_transaction()`
2. **MemoryManager ↔ GitSignalExtractor**: Explicit repo path parameter
3. **Complexity Assessment ↔ Query Executor**: Return format unchanged
4. **Config Loader ↔ Environment**: AURORA_HOME env var

### Migration Strategy

**No data migration required** - All changes are code-only:
- Database schema unchanged
- Config file format unchanged
- Existing data compatible

### Rollback Plan

If Phase 2A introduces regressions:
1. Revert specific fix (fixes are independent)
2. Re-run E2E tests to confirm revert
3. Document issue in OPEN_QUESTIONS.md
4. Address in hotfix if critical

---

## Implementation Strategy

### Sequential Execution Order (Selected Strategy)

**Rationale**: Safer, tracks progress clearly, easier debugging, single developer

### Phase 2A Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 2A: E2E Test Failure Remediation (Sequential)        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: Pre-Fix Baseline (1 hour)                         │
│  ├─ Run full E2E suite, capture failures                   │
│  ├─ Generate baseline report                               │
│  └─ Document initial state                                 │
│                                                             │
│  Step 2: Database Schema Validation (1 hour)               │
│  ├─ Audit SQLite schema                                    │
│  ├─ Document assumptions                                   │
│  └─ Validate required tables/columns exist                 │
│                                                             │
│  Step 3: Fix #2 - Stats Methods (2 hours)                  │
│  ├─ Write E2E tests if missing                             │
│  ├─ Implement _count_total_chunks()                        │
│  ├─ Implement _count_unique_files()                        │
│  ├─ Implement _get_language_distribution()                 │
│  └─ Verify: pytest tests/e2e/test_e2e_database_persistence │
│                                                             │
│  Step 4: Fix #5 - Query/Search (1 hour)                    │
│  ├─ Verify dependent fixes worked                          │
│  ├─ Run pytest tests/e2e/test_e2e_query_uses_index.py      │
│  └─ Debug if tests still fail                              │
│                                                             │
│  Step 5: Fix #1 - Complexity Assessment (3 hours)          │
│  ├─ Write E2E tests if missing                             │
│  ├─ Implement domain keyword override                      │
│  ├─ Implement multi-question detection                     │
│  ├─ Add scope indicator keywords                           │
│  └─ Verify: pytest tests/e2e/test_e2e_complexity_assessment│
│                                                             │
│  Step 6: Fix #6 - Auto-Escalation (1 hour)                 │
│  ├─ Verify escalation logic exists                         │
│  ├─ Add logging for escalation decisions                   │
│  └─ Verify: pytest tests/integration/test_auto_escalation  │
│                                                             │
│  Step 7: Fix #3 - Git BLA (4 hours)                        │
│  ├─ Write E2E tests if missing                             │
│  ├─ Fix GitSignalExtractor initialization                  │
│  ├─ Improve error handling in MemoryManager                │
│  ├─ Implement fallback BLA=0.5 strategy                    │
│  ├─ Handle edge cases (shallow, detached HEAD)             │
│  └─ Verify: pytest tests/e2e/test_e2e_git_bla_initialization│
│                                                             │
│  Step 8: Fix #4 - Config Search Order (2 hours)            │
│  ├─ Write E2E tests if missing                             │
│  ├─ Update config search order                             │
│  ├─ Add config source logging                              │
│  └─ Verify: pytest tests/e2e/test_e2e_new_user_workflow    │
│                                                             │
│  Step 9: Placeholder Audit (3 hours)                       │
│  ├─ Run automated placeholder detection                    │
│  ├─ Generate PLACEHOLDER_AUDIT.md report                   │
│  ├─ Fix high-priority placeholders                         │
│  ├─ Document intentional placeholders                      │
│  └─ Verify: No new E2E failures                            │
│                                                             │
│  Step 10: CI/CD E2E Gate (2 hours)                         │
│  ├─ Add e2e-tests job to .github/workflows/test.yml        │
│  ├─ Add test failure categorization                        │
│  ├─ Update branch protection rules                         │
│  └─ Verify: Trigger test run, confirm gate works           │
│                                                             │
│  Step 11: Full Regression Check (2 hours)                  │
│  ├─ Run: pytest tests/e2e/ tests/integration/ -v           │
│  ├─ Run: pytest tests/unit/ -v                             │
│  ├─ Run: make quality-check                                │
│  └─ Verify: All gates pass                                 │
│                                                             │
│  Step 12: Documentation (2 hours)                          │
│  ├─ Update docs/development/TESTING.md                     │
│  ├─ Update docs/TROUBLESHOOTING.md                         │
│  ├─ Create docs/architecture/DATABASE_SCHEMA.md            │
│  └─ Update this PRD with final results                     │
│                                                             │
│  Total Estimated Time: 24 hours                            │
└─────────────────────────────────────────────────────────────┘
```

### Checkpoint Gates

**Gate 1** (After Step 4): P0 fixes complete
- ✅ Stats methods working
- ✅ Query/search working
- ✅ 19+ E2E tests passing

**Gate 2** (After Step 6): P1 fixes complete
- ✅ Complexity assessment working
- ✅ Auto-escalation working
- ✅ 11+ E2E tests passing

**Gate 3** (After Step 8): All category fixes complete
- ✅ Git BLA working
- ✅ Config search working
- ✅ All 48+ E2E tests passing

**Gate 4** (After Step 11): Full quality gates
- ✅ All E2E tests pass
- ✅ All unit tests pass
- ✅ make quality-check passes
- ✅ No placeholders in affected files

---

## Success Metrics

### Primary Success Criteria (Must Achieve)

1. **E2E Test Success Rate**: 100% (all 48+ tests pass)
   - Current: ~0% (48+ failures)
   - Target: 100%
   - Measurement: `pytest tests/e2e/ tests/integration/ --tb=short`

2. **Placeholder Elimination**: 0 placeholders in critical paths
   - Current: 6 known categories
   - Target: 0 in affected files
   - Measurement: Grep for `return 0  # TODO` patterns

3. **Full Test Suite**: 100% pass rate
   - Current: 97% (2,369 tests, ~70 failures)
   - Target: 100%
   - Measurement: `pytest tests/`

4. **Quality Check**: PASS
   - Current: Lint ✅, Type ✅, Security ✅, Tests ❌
   - Target: All ✅
   - Measurement: `make quality-check`

### Secondary Success Criteria (Should Achieve)

5. **Coverage Maintenance**: ≥80%
   - Current: 81.06%
   - Target: ≥80% (no regression)
   - Measurement: `pytest --cov=packages`

6. **CI/CD E2E Gate**: ACTIVE
   - Current: Not enforced
   - Target: Enforced in GitHub Actions
   - Measurement: Check branch protection rules

7. **Documentation Completeness**: Updated
   - Current: Gaps in TESTING.md, missing DATABASE_SCHEMA.md
   - Target: All developer docs updated
   - Measurement: Manual review

### Acceptance Criteria by Category

| Category | Current | Target | Test Command |
|----------|---------|--------|--------------|
| Database Persistence | 0/6 pass | 6/6 pass | `pytest tests/e2e/test_e2e_database_persistence.py` |
| Complexity Assessment | 0/9 pass | 9/9 pass | `pytest tests/e2e/test_e2e_complexity_assessment.py` |
| Git BLA Initialization | 0/11 pass | 11/11 pass | `pytest tests/e2e/test_e2e_git_bla_initialization.py` |
| New User Workflow | 0/7 pass | 7/7 pass | `pytest tests/e2e/test_e2e_new_user_workflow.py` |
| Query/Search | 0/13 pass | 13/13 pass | `pytest tests/e2e/test_e2e_query_uses_index.py` |
| Auto-Escalation | 0/2 pass | 2/2 pass | `pytest tests/integration/test_auto_escalation.py` |

### Performance Criteria (Should Not Degrade)

- E2E test suite runtime: <10 minutes
- Stats query performance: <100ms
- Git BLA initialization: <5s for typical repo

### Definition of Done

**Phase 2A is complete when:**

1. ✅ All 48+ E2E/integration tests pass
2. ✅ All unit tests pass (no regression)
3. ✅ `make quality-check` passes (lint, type, security, tests)
4. ✅ No placeholder implementations remain in:
   - `aurora_cli/memory_manager.py` (stats methods)
   - `aurora_soar/phases/assess.py` (complexity assessment)
   - `aurora_context_code/git.py` (GitSignalExtractor)
   - `aurora_cli/config.py` (config loading)
5. ✅ CI/CD E2E gate active and enforced
6. ✅ Developer documentation updated:
   - `docs/development/TESTING.md`
   - `docs/TROUBLESHOOTING.md`
   - `docs/architecture/DATABASE_SCHEMA.md` (new)
   - `docs/development/aurora_fixes/PLACEHOLDER_AUDIT.md` (new)
7. ✅ Code review passed (self-review checklist complete)
8. ✅ User can complete full workflow without E2E failures:
   - `aur init`
   - `aur mem index .`
   - `aur mem stats` (shows real data)
   - `aur mem search "test"` (varied results)
   - `aur query "How does SOAR work?"` (MEDIUM complexity)

---

## Testing Strategy

### Test-Driven Development Approach (Selected)

**Rationale**: Write failing E2E tests BEFORE implementing fixes to ensure complete coverage.

### Testing Workflow Per Fix

```
For each fix category:
1. Audit existing E2E tests
2. Write new E2E tests if gaps exist
3. Run tests → Confirm FAIL (proves bug exists)
4. Implement fix
5. Run tests → Confirm PASS (proves fix works)
6. Run full regression → Confirm no breakage
```

### E2E Test Coverage Requirements

#### Category 1: Database Persistence (6 tests)

**Existing tests to verify:**
- `test_data_persists_across_sessions` - Data survives CLI restarts
- `test_stats_reflect_indexed_data` - Stats show real chunk counts
- `test_database_path_from_config` - Config DB path respected

**New tests to write (if missing):**
- `test_stats_methods_query_real_database` - All 3 stats methods return real data
- `test_language_distribution_matches_indexed_files` - Language breakdown correct
- `test_unique_file_count_accurate` - File count matches indexed files

#### Category 2: Complexity Assessment (9 tests)

**Existing tests to verify:**
- `test_complex_query_complexity` - Multi-part queries → COMPLEX
- `test_moderate_query_complexity` - Domain queries → MEDIUM
- `test_simple_query_complexity` - Basic queries → SIMPLE

**New tests to write (if missing):**
- `test_domain_keyword_override` - "SOAR" → MEDIUM minimum
- `test_multi_question_detection` - Multiple "?" → complexity boost
- `test_scope_indicator_keywords` - "research", "analyze" → MEDIUM
- `test_confidence_scores_above_threshold` - Domain queries → confidence ≥0.6

#### Category 3: Git BLA Initialization (11 tests)

**Existing tests to verify:**
- `test_bla_values_initialized_from_git` - Chunks have BLA >0.0
- `test_activation_decay_over_time` - Older commits → lower BLA
- `test_commit_count_tracking` - Commit count tracked per chunk

**New tests to write (if missing):**
- `test_git_extractor_accepts_repo_path` - Explicit path parameter works
- `test_non_git_directory_uses_fallback` - BLA=0.5 for non-git
- `test_shallow_clone_handled_gracefully` - Warning logged, fallback used
- `test_empty_repo_no_crash` - Zero commits → BLA=0.5
- `test_git_error_message_helpful` - Clear guidance in error message

#### Category 4: Config Search Order (7 tests)

**Existing tests to verify:**
- `test_first_time_setup` - Config created in correct location
- `test_config_creation` - Config file format correct
- `test_directory_initialization` - Directories created

**New tests to write (if missing):**
- `test_aurora_home_env_var_prioritized` - AURORA_HOME → highest priority
- `test_config_source_logged` - Log shows which config loaded
- `test_cwd_config_ignored_when_aurora_home_set` - Isolation works

#### Category 5: Query/Search (13+ tests)

**Existing tests to verify:**
- `test_query_uses_memory` - Query retrieves indexed chunks
- `test_direct_llm_includes_context` - Context passed to LLM
- `test_different_queries_return_different_results` - Varied results
- `test_activation_scores_have_variance` - Not all 1.0
- `test_semantic_scores_vary_by_relevance` - Not all 1.0

**New tests to write (if missing):**
- `test_search_uses_populated_database` - Searches correct DB
- `test_search_results_ranked_by_relevance` - Hybrid scoring works
- `test_query_context_includes_file_paths` - Source attribution

#### Category 6: Auto-Escalation (2 tests)

**Existing tests to verify:**
- `test_auto_escalation_threshold` - Low confidence → SOAR
- `test_retrieval_context_passing` - Context passed through escalation

**New tests to write (if missing):**
- `test_escalation_decision_logged` - Log explains why escalated

### Unit Test Maintenance

**Requirement**: All existing unit tests must continue passing (no regression).

**Strategy**:
1. Run unit tests before each fix: `pytest tests/unit/`
2. If unit test breaks, analyze why (valid break vs regression)
3. Update mocks if behavior change is intentional
4. Do NOT delete unit tests to make E2E pass

### Integration Test Coverage

**Requirement**: Integration tests verify multi-component interactions.

**Focus areas**:
- MemoryManager + SQLiteStore integration
- Complexity assessment + Query executor integration
- GitSignalExtractor + MemoryManager integration
- Config loader + CLI commands integration

### Test Execution Order

1. **Before each fix**: Run category E2E tests → Confirm FAIL
2. **After each fix**: Run category E2E tests → Confirm PASS
3. **After each fix**: Run full unit tests → Confirm no regression
4. **After Gate 1/2/3**: Run full E2E suite → Confirm cumulative progress
5. **After Gate 4**: Run `make quality-check` → Confirm all gates pass

### Test Isolation

**Requirement**: E2E tests must not interfere with each other.

**Best practices**:
- Use pytest fixtures for temp directories
- Set AURORA_HOME env var per test
- Clean up databases after each test
- Don't rely on test execution order

### Manual Testing Checklist

After all automated tests pass, manual verification:

```bash
# Clean slate
rm -rf ~/.aurora
unset AURORA_HOME

# Test 1: Fresh install workflow
aur init
# Expected: Config created, no errors

# Test 2: Indexing
cd ~/PycharmProjects/aurora
aur mem index .
# Expected: >4000 chunks indexed, no errors

# Test 3: Stats
aur mem stats
# Expected: Shows real chunk counts (not 0), language distribution

# Test 4: Search
aur mem search "SOAR"
# Expected: Varied results, not all identical scores

# Test 5: Query
aur query "How does SOAR orchestration work?"
# Expected: Classified as MEDIUM/COMPLEX, uses indexed data

# Test 6: Git BLA
aur mem index . --verbose
# Expected: Logs show git BLA calculation, no silent failures

# Test 7: Config isolation
export AURORA_HOME=/tmp/test-aurora
aur init
# Expected: Config created in /tmp/test-aurora, not ~/.aurora
```

---

## Documentation Requirements

### Technical Documentation (Code-Level)

#### FR-DOC-1: Code Comments
**Requirement**: All fixed methods must have clear docstrings and inline comments.

**Specification**:
- Docstrings: Google style, include Args, Returns, Raises
- Inline comments: Explain WHY, not WHAT (code is self-documenting)
- TODOs: None in final code (either fix or remove)

**Example**:
```python
def _count_total_chunks(self) -> int:
    """Count total chunks in memory store.

    Executes SQL query against the store's database to get accurate count.
    Falls back to 0 if store doesn't support direct SQL access.

    Returns:
        Total number of chunks in database, or 0 if query fails.

    Note:
        Requires store to implement _transaction() context manager.
        Used by get_stats() for user-facing statistics.
    """
```

#### FR-DOC-2: Database Schema Documentation
**Requirement**: Create comprehensive database schema documentation.

**Specification**:
- File: `docs/architecture/DATABASE_SCHEMA.md`
- Contents:
  - Table definitions (chunks, activations, metadata)
  - Column types and constraints
  - JSON metadata structure
  - Indexing strategy
  - Query patterns used by stats methods
  - Migration strategy (if schema changes)

### Developer Documentation (Process-Level)

#### FR-DOC-3: Testing Guide Updates
**Requirement**: Update TESTING.md with E2E test guidance.

**Specification**:
- File: `docs/development/TESTING.md`
- Add section: "E2E Test Development"
  - When to write E2E tests (new CLI commands, core workflows)
  - How to structure E2E tests (fixtures, isolation)
  - E2E test naming conventions
  - E2E test debugging tips
- Add section: "CI/CD Test Gates"
  - What gates exist (unit, integration, E2E)
  - How to run locally before pushing
  - How to interpret CI/CD failures

#### FR-DOC-4: Troubleshooting Guide Updates
**Requirement**: Update TROUBLESHOOTING.md with common E2E issues.

**Specification**:
- File: `docs/TROUBLESHOOTING.md`
- Add section: "E2E Test Failures"
  - Stats showing 0 chunks → Check DB path
  - Search returning identical results → Check activation tracking
  - Git BLA errors → Check if directory is git repo
  - Config not loading → Check AURORA_HOME env var
- Add section: "Database Issues"
  - How to inspect SQLite database
  - How to reset database (rm ~/.aurora/memory.db)
  - How to validate schema

#### FR-DOC-5: Placeholder Audit Report
**Requirement**: Document all found placeholders and disposition.

**Specification**:
- File: `docs/development/aurora_fixes/PLACEHOLDER_AUDIT.md`
- Format:
  ```markdown
  # Placeholder Audit Report

  **Date**: 2025-12-29
  **Scope**: All Python files in packages/*/src/

  ## Summary
  - Total placeholders found: X
  - Fixed: Y
  - Documented as intentional: Z
  - Remaining (non-critical): W

  ## High-Priority Fixes (Critical Paths)
  | File | Line | Pattern | Status | Fix Description |
  |------|------|---------|--------|-----------------|
  | memory_manager.py | 568 | return 0 # TODO | ✅ Fixed | Implemented SQL query |

  ## Intentional Placeholders (Acceptable)
  | File | Line | Pattern | Justification |
  |------|------|---------|---------------|
  | base.py | 42 | pass # TODO | Abstract method, subclass implements |

  ## Low-Priority Placeholders (Non-Critical)
  | File | Line | Pattern | Reason Not Fixed |
  |------|------|---------|------------------|
  | optional_feature.py | 123 | return {} # TODO | Optional feature, not in scope |
  ```

### Documentation Update Checklist

- [ ] All fixed methods have docstrings
- [ ] Inline comments explain non-obvious logic
- [ ] DATABASE_SCHEMA.md created and comprehensive
- [ ] TESTING.md updated with E2E guidance
- [ ] TROUBLESHOOTING.md updated with E2E issues
- [ ] PLACEHOLDER_AUDIT.md generated and complete
- [ ] This PRD updated with final results (Appendix A)

---

## Open Questions

### Pre-Implementation Questions

1. **Database Schema Validation** (Priority: HIGH)
   - Q: Does SQLiteStore schema match what stats methods expect?
   - A: TBD - Will audit in Step 2 (Database Schema Validation)
   - Impact: May need schema migration if mismatch

2. **Embeddings During Indexing** (Priority: MEDIUM)
   - Q: Are embeddings actually computed during indexing, or just placeholders?
   - A: TBD - Will verify in Step 4 (Query/Search fix)
   - Impact: May need to fix embedding generation if missing

3. **Activation Score Normalization** (Priority: MEDIUM)
   - Q: Is normalization in HybridRetriever causing identical scores?
   - A: TBD - Will investigate if Step 4 tests still fail
   - Impact: May need to fix normalization logic

4. **Config File Precedence** (Priority: LOW)
   - Q: Should explicit `--config` flag override AURORA_HOME?
   - A: YES (assumed) - Explicit always wins
   - Impact: None, clarifies behavior

### Implementation-Discovered Questions

*This section will be populated during implementation as new questions arise.*

### Post-Implementation Review Questions

*This section will be populated after Phase 2A completes.*

---

## Appendix A: Implementation Results

*This section will be populated after Phase 2A completes with:*
- Final test results (pass/fail counts)
- Actual time spent per step
- Issues encountered and resolutions
- Metrics comparison (before/after)
- Lessons learned

---

## Appendix B: Code Review Checklist

Use this checklist before marking Phase 2A as complete:

### Functional Correctness
- [ ] All 48+ E2E tests pass
- [ ] All unit tests pass (no regression)
- [ ] `make quality-check` passes
- [ ] Manual testing checklist completed

### Code Quality
- [ ] No placeholder implementations in critical paths
- [ ] All methods have docstrings
- [ ] Error handling present (try/except with logging)
- [ ] No hardcoded values (except reasonable defaults)
- [ ] No TODOs in final code

### Testing
- [ ] E2E tests exist for all 6 categories
- [ ] Test coverage maintained (≥80%)
- [ ] Tests are isolated (no cross-test dependencies)
- [ ] Tests have clear names and descriptions

### CI/CD
- [ ] E2E test job added to GitHub Actions
- [ ] E2E gate enforced (branch protection)
- [ ] Test failure categorization working
- [ ] CI/CD pipeline passes end-to-end

### Documentation
- [ ] DATABASE_SCHEMA.md created
- [ ] TESTING.md updated
- [ ] TROUBLESHOOTING.md updated
- [ ] PLACEHOLDER_AUDIT.md generated
- [ ] Code comments adequate

### Performance
- [ ] E2E test suite runtime <10 minutes
- [ ] Stats queries <100ms
- [ ] No significant performance degradation

### Security
- [ ] No SQL injection vulnerabilities
- [ ] No path traversal vulnerabilities
- [ ] No sensitive data in error messages

---

## Appendix C: Effort Estimates vs Actuals

*This table will be updated after implementation:*

| Step | Estimated | Actual | Variance | Notes |
|------|-----------|--------|----------|-------|
| 1. Pre-Fix Baseline | 1h | - | - | - |
| 2. Schema Validation | 1h | - | - | - |
| 3. Fix #2 (Stats) | 2h | - | - | - |
| 4. Fix #5 (Query) | 1h | - | - | - |
| 5. Fix #1 (Complexity) | 3h | - | - | - |
| 6. Fix #6 (Auto-Escalate) | 1h | - | - | - |
| 7. Fix #3 (Git BLA) | 4h | - | - | - |
| 8. Fix #4 (Config) | 2h | - | - | - |
| 9. Placeholder Audit | 3h | - | - | - |
| 10. CI/CD E2E Gate | 2h | - | - | - |
| 11. Full Regression | 2h | - | - | - |
| 12. Documentation | 2h | - | - | - |
| **Total** | **24h** | **-** | **-** | **-** |

---

## Appendix D: Related Documents

- **Root Cause Analysis**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/E2E_FAILURE_REMEDIATION_PLAN.md`
- **Phase 1 Summary**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/PHASE1_COMPLETION_SUMMARY.md`
- **Original Analysis**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/MCP_TESTING_ANALYSIS.md`
- **Testing Guide**: `/home/hamr/PycharmProjects/aurora/docs/development/TESTING.md`
- **Architecture**: `/home/hamr/PycharmProjects/aurora/docs/architecture/SOAR_ARCHITECTURE.md`

---

**END OF PRD**

---

## Self-Verification Checklist (For PRD Author)

- [x] Functional requirements numbered and specific
- [x] User stories follow "As a X, I want Y, so that Z" format
- [x] Non-goals explicitly stated
- [x] Success metrics measurable
- [x] Language clear for junior developer (technical but not assuming deep context)
- [x] Correct filename: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/PHASE2A_E2E_REMEDIATION_PRD.md`
- [x] No implementation details (only requirements) - WAIT: This PRD includes implementation examples. This is INTENTIONAL because:
  - Junior developers benefit from seeing SQL query patterns
  - Error handling patterns are specified in requirements
  - Code examples clarify ambiguous requirements
  - Examples are prescriptive (MUST implement this way), not descriptive
- [x] All user answers incorporated:
  - [x] Sequential implementation (1A)
  - [x] Test-driven approach (2A)
  - [x] Audit all placeholders (3B)
  - [x] Add CI/CD gate with reporting (4C)
  - [x] Document schema assumptions (5C)
  - [x] Fix GitSignalExtractor properly with fallback (6: custom answer)
  - [x] All E2E + no placeholders (7B)
  - [x] Technical + developer docs (8B)
  - [x] Basic error handling + logging (9B)
  - [x] Fix 6 + audit patterns (10B, estimated 18-20h, actual 24h with overhead)
