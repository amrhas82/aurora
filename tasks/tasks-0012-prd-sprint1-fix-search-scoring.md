# Tasks: Sprint 1 - Fix Search Scoring

**Generated from PRD**: `0012-prd-sprint1-fix-search-scoring.md`
**Date**: 2025-12-29
**Sprint Duration**: 1-2 days (8-16 hours)
**Priority**: CRITICAL (P1)

---

## Relevant Files

### Core Scoring Pipeline
- `packages/core/src/aurora_core/store/sqlite.py` - SQLite store with `record_access()`, `retrieve_by_activation()`, activation table management
- `packages/core/src/aurora_core/activation/engine.py` - ACT-R activation calculation engine
- `packages/core/src/aurora_core/activation/base_level.py` - Base-level activation (BLA) calculation with `calculate_bla()` function
- `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - Hybrid retrieval with `_normalize_scores()`, `_blend_scores()`, `retrieve()`
- `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py` - Embedding generation and cosine similarity

### Git BLA Integration
- `packages/context-code/src/aurora_context_code/git.py` - GitSignalExtractor class for function-level commit history extraction
- `packages/cli/src/aurora_cli/memory_manager.py` - MemoryManager with `index_path()`, `search()` methods that should integrate Git BLA

### Chunk Models
- `packages/core/src/aurora_core/chunks/code_chunk.py` - CodeChunk model with `line_start`, `line_end`, `metadata` fields
- `packages/core/src/aurora_core/chunks/base.py` - Base Chunk class

### Test Files
- `tests/e2e/test_e2e_search_scoring.py` - NEW: E2E tests for search score variance (to be created)
- `tests/e2e/test_e2e_search_accuracy.py` - Existing E2E tests for search accuracy (reference patterns)
- `tests/e2e/test_e2e_git_bla_initialization.py` - Existing E2E tests for Git BLA (reference patterns)
- `tests/e2e/conftest.py` - E2E test utilities (`run_cli_command`, `get_cli_env`)

### Documentation
- `docs/development/aurora_fixes/search_scoring_investigation.md` - NEW: Investigation report (to be created)
- `docs/development/aurora_fixes/MANUAL_CLI_TEST_REPORT.md` - Manual test report to update (TEST 9)
- `docs/development/aurora_fixes/AURORA_MAJOR_FIXES.md` - Sprint status tracking

### Notes

**Testing Framework**:
- Use `pytest` with `pytest.mark.e2e` marker for E2E tests
- Use `run_cli_command()` from `conftest.py` for CLI subprocess calls
- Use `clean_aurora_home` fixture pattern for isolated test environments
- E2E tests should use temporary directories and clean up after

**Key Architecture Patterns**:
- Scoring pipeline: `search()` -> `HybridRetriever.retrieve()` -> `_normalize_scores()` -> `_blend_scores()`
- Git BLA: `GitSignalExtractor.get_function_commit_times()` -> `calculate_bla()` during indexing
- Access tracking: `store.record_access()` should be called in `MemoryManager.search()` after retrieval
- Hybrid formula: `0.6 * activation_score + 0.4 * semantic_score`

**Database Schema** (activations table):
- `chunk_id` - Foreign key to chunks
- `base_level` - BLA value (should vary based on Git history)
- `access_count` - Number of accesses (should match commit count initially)
- `last_access` - Timestamp of last access
- `access_history` - JSON array of access records

**Critical Constraints**:
- DO NOT modify test parsing or output formatting
- DO NOT change expected values in tests to match broken behavior
- DO NOT add sleep() or retry logic to mask failures
- All fixes must be in production code, not test infrastructure

---

## Tasks

- [x] 1.0 Root Cause Investigation
  - [x] 1.1 Read and analyze the complete scoring pipeline by examining these files in order: `packages/core/src/aurora_core/store/sqlite.py` (retrieve_by_activation), `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (retrieve, _normalize_scores, _blend_scores), `packages/core/src/aurora_core/activation/engine.py` (ACT-R calculation)
  - [x] 1.2 Investigate Hypothesis 1 (Activation Tracking) by querying the database: run `sqlite3 ~/.aurora/memory.db "SELECT chunk_id, base_level, access_count FROM activations LIMIT 10"` and document whether base_level values are all 0.0 and access_count all 0
  - [x] 1.3 Investigate Hypothesis 1 (Git BLA) by checking if `GitSignalExtractor` is being called during indexing - trace the code path in `memory_manager.py` `index_path()` method and verify Git commit extraction actually runs
  - [x] 1.4 Investigate Hypothesis 2 (Semantic Embeddings) by writing a Python script to inspect stored embeddings - query chunks table, extract embedding bytes, convert to numpy array, and verify embeddings are different vectors (not all identical or None)
  - [x] 1.5 Investigate Hypothesis 3 (Hybrid Blending) by adding temporary debug logging to `hybrid_retriever.py` `retrieve()` method to print activation_scores, semantic_scores before/after normalization, and after blending
  - [x] 1.6 Investigate Hypothesis 4 (Normalization Bug) by testing `_normalize_scores()` directly with equal inputs: call `_normalize_scores([0.5, 0.5, 0.5])` and verify whether it returns `[1.0, 1.0, 1.0]` (bug) or `[0.5, 0.5, 0.5]` (expected)
  - [x] 1.7 Create investigation report at `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/search_scoring_investigation.md` documenting: root cause identification, specific file paths and line numbers, minimal reproduction test case, proposed fix approach, evidence from each hypothesis investigation

- [ ] 2.0 Fix Git-Based BLA Initialization (if root cause includes activation tracking)
  - [ ] 2.1 Verify `GitSignalExtractor` class in `packages/context-code/src/aurora_context_code/git.py` has correct implementation of `get_function_commit_times()` that uses `git blame -L <start>,<end>` for function-level tracking
  - [ ] 2.2 Verify `GitSignalExtractor.calculate_bla()` correctly implements ACT-R formula: `BLA = ln(sum(t_j^(-d)))` where t_j is time since commit and d is decay rate (0.5)
  - [ ] 2.3 Trace the indexing code path in `memory_manager.py` `index_path()` to verify `GitSignalExtractor` is instantiated and `get_function_commit_times()` is called for each chunk with correct `line_start` and `line_end` parameters
  - [ ] 2.4 Fix any silent failures in Git BLA extraction by adding proper error logging when `git blame` commands fail - ensure fallback to `base_level=0.5` (not 0.0) for non-Git directories
  - [ ] 2.5 Verify the activation initialization in `index_path()` correctly updates the activations table with Git-derived `base_level` and `commit_count` as `access_count` - check the SQL UPDATE statement after `save_chunk()`
  - [ ] 2.6 Ensure Git metadata (`git_hash`, `last_modified`, `commit_count`) is stored in chunk.metadata dictionary before calling `save_chunk()`
  - [ ] 2.7 Test Git BLA fix manually by indexing the Aurora repo and querying: `sqlite3 ~/.aurora/memory.db "SELECT c.name, a.base_level, a.access_count FROM chunks c JOIN activations a ON c.id = a.chunk_id WHERE c.type='code' LIMIT 10"` - verify varied base_level values

- [ ] 3.0 Fix Runtime Access Tracking (if root cause includes missing record_access calls)
  - [ ] 3.1 Examine `memory_manager.py` `search()` method and verify `record_access()` is called for each returned result after the retrieval completes
  - [ ] 3.2 If `record_access()` calls are missing or commented out, add them in a loop after retrieval: `for result in results: self.memory_store.record_access(chunk_id=result.chunk_id, access_time=datetime.now(timezone.utc), context=query)`
  - [ ] 3.3 Verify `sqlite.py` `record_access()` method correctly updates both `access_count` and recalculates `base_level` using `calculate_bla()` from access history
  - [ ] 3.4 Test runtime access tracking by performing multiple searches and querying: `sqlite3 ~/.aurora/memory.db "SELECT COUNT(*) FROM activations WHERE access_count > 0"` - should show increasing access counts
  - [ ] 3.5 Verify access tracking does not fail silently by checking exception handling in the `record_access()` loop - errors should be logged but not crash the search

- [ ] 4.0 Fix Normalization and Blending Issues (if root cause includes normalization bug)
  - [ ] 4.1 Examine `_normalize_scores()` in `hybrid_retriever.py` and fix the edge case where all input scores are equal - change behavior from returning `[1.0, 1.0, ...]` to returning original scores as-is when `max_score - min_score < epsilon`
  - [ ] 4.2 Verify the `_normalize_scores()` fix handles these edge cases: empty list returns empty list, single score returns `[1.0]`, all equal scores returns original scores, normal case uses min-max normalization
  - [ ] 4.3 Verify hybrid blending formula in `retrieve()` method correctly calculates: `hybrid_score = 0.6 * activation_norm + 0.4 * semantic_norm` and scores are normalized BEFORE blending
  - [ ] 4.4 Verify cosine similarity calculation in `embedding_provider.py` is correct and handles edge cases (zero vectors, same vectors)
  - [ ] 4.5 Add unit test for `_normalize_scores()` edge cases in `tests/unit/context_code/test_hybrid_retriever.py` if not already present
  - [ ] 4.6 Remove any temporary debug logging added during investigation phase

- [ ] 5.0 E2E Tests and Verification
  - [ ] 5.1 Create `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_search_scoring.py` with imports, fixtures, and test class structure following patterns from `test_e2e_search_accuracy.py`
  - [ ] 5.2 Implement `test_search_returns_varied_activation_scores()` that indexes diverse code, searches, and asserts `max(activation_scores) != min(activation_scores)` with clear failure message
  - [ ] 5.3 Implement `test_search_returns_varied_semantic_scores()` that searches and asserts semantic scores vary (stddev > 0.05) based on query relevance
  - [ ] 5.4 Implement `test_search_returns_varied_hybrid_scores()` that asserts hybrid scores vary and are in valid range [0.0, 1.0]
  - [ ] 5.5 Implement `test_search_ranks_relevant_results_higher()` that searches for specific topic and asserts top result contains query-relevant content
  - [ ] 5.6 Implement `test_activation_frequency_affects_score()` that performs repeated searches and verifies activation scores increase with access frequency
  - [ ] 5.7 Implement `test_git_bla_initialization_varies_by_function()` that indexes Git repo and queries database to verify functions in same file have different base_level values
  - [ ] 5.8 Run E2E tests before applying fixes to confirm they FAIL (proves bug exists): `pytest tests/e2e/test_e2e_search_scoring.py -v`
  - [ ] 5.9 Apply all fixes from tasks 2.0, 3.0, 4.0 based on investigation results
  - [ ] 5.10 Run E2E tests after fixes to confirm they PASS: `pytest tests/e2e/test_e2e_search_scoring.py -v`
  - [ ] 5.11 Run full regression test suite: `make test` and verify all 2,369 existing tests still pass
  - [ ] 5.12 Run type checking: `make type-check` and verify no new mypy errors introduced
  - [ ] 5.13 Perform manual verification by running: `rm -rf ~/.aurora && aur init && aur mem index /home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/ && aur mem search "activation scoring"`
  - [ ] 5.14 Capture manual test output showing varied scores (not all 1.000) and save as evidence
  - [ ] 5.15 Update `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/MANUAL_CLI_TEST_REPORT.md` changing TEST 9 status from `PARTIAL` to `PASSED` with verification notes
  - [ ] 5.16 Verify all 10 acceptance criteria from PRD Section 8.3 are met before marking sprint complete

---

## Acceptance Criteria Checklist (from PRD)

Before marking this sprint complete, verify ALL of these:

- [ ] Root cause identified and documented in investigation report
- [ ] Bug fixed in production code (NOT test parsing or formatting)
- [ ] E2E tests pass - All 6 new tests verify score variance
- [ ] Manual testing shows varied scores - Command output captured
- [ ] Top-ranked results are relevant - Query terms appear in top results
- [ ] No regression - All 2,369 existing tests still pass
- [ ] Database activation tracking works - SQLite queries show varied base_level values
- [ ] Git BLA initialization works - Base-level activation varies based on Git commit history
- [ ] Function-level tracking works - Functions in same file have different activation scores
- [ ] Manual test report updated - TEST 9 status changed to PASSED

---

## Evidence Required (from PRD Section 8.4)

Collect these before sprint completion:

1. **Varied Scores in CLI Output**: `aur mem search "SOAR"` shows activation/semantic/hybrid != 1.000
2. **Database Shows Activation Tracking**: `sqlite3 ~/.aurora/memory.db "SELECT AVG(base_level), COUNT(DISTINCT base_level) FROM activations WHERE base_level > 0"` returns Average > 0.0, Distinct > 10
3. **E2E Tests Pass**: `pytest tests/e2e/test_e2e_search_scoring.py -v` shows 6/6 PASSED
4. **Git BLA Function-Level**: Query shows functions in same file with different base_level values
5. **No Regressions**: `make test` shows 2,369 passed, 14 skipped

---

## Red Flags (STOP if any occur)

- Modifying test parsing instead of production code
- Changing expected values in tests to match broken behavior
- Adding `|| true` or similar to mask failures
- Removing assertions from tests
- Tests pass but feature doesn't work when tested manually
- Adding sleep() or retry logic to make tests pass
- Skipping manual verification step
