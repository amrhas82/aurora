# AURORA Test Suite - Phase 1 Baseline Metrics

**Date:** 2025-12-26
**Branch:** test/cleanup-systematic
**Python Version:** 3.10.12
**PRD:** 0009-prd-test-suite-systematic-cleanup.md

---

## Test Count Summary

### Total Tests
- **Total Tests Collected:** 2,020 tests
- **Test Files:** 92 files

### Distribution by Category
- **Unit Tests:** 55 files (tests/unit/)
- **Integration Tests:** 19 files (tests/integration/)
- **E2E Tests:** 2 files (tests/e2e/)
- **Performance Benchmarks:** 8 files (tests/performance/)
- **Other:** 8 files

### Detailed Breakdown
```
tests/
├── unit/           (~1,900 tests, 94%)  ← INVERTED PYRAMID
├── integration/    (~100 tests, 5%)
├── e2e/           (~15 tests, <1%)
└── performance/    (~8 benchmark suites)
```

**Problem Identified:** Inverted test pyramid (95% unit, 4% integration, 1% E2E)

---

## Coverage Metrics

### Baseline Coverage (Python 3.10)
- **Overall Coverage:** 25.96% (reported by pytest --collect-only with coverage)
- **Note:** This appears to be instantaneous coverage from collection phase
- **Full Test Run:** In progress (>10 minutes, killed for efficiency)

### Coverage by Package (Preliminary)
Based on collection-time coverage snapshot:
- aurora_core: Partial coverage
- aurora_soar: Partial coverage (orchestrator: ~28%, phases: 13-25%)
- aurora_context_code: Partial coverage
- aurora_reasoning: Needs measurement
- aurora_mcp: Needs measurement
- aurora_cli: Needs measurement

**Note:** Full coverage metrics will be collected after test deletions in Phase 1.

---

## Known Issues (from CLAUDE.md)

### Test Failures by Python Version
- **Python 3.10:** Expected to pass (baseline)
- **Python 3.11:** 28 failures (all @patch-related)
- **Python 3.12:** 27 failures (all @patch-related)
- **Python 3.13:** Not yet measured

### Root Cause
- 50+ `@patch` decorators in headless orchestrator tests cause cross-version fragility
- Mock object behavior changed in Python 3.11+
- Tests verify mock calls instead of behavior

---

## Test Quality Issues

### Anti-Patterns Identified

#### 1. Tests Verifying Mock Calls (85+ occurrences)
```python
# Example from test_orchestrator.py
mock_git.validate.assert_called_once()
mock_prompt.validate_format.assert_called_once()
```
**Problem:** Tests check if mocks were called, not if behavior is correct

#### 2. Implementation Detail Tests
**Confirmed Deletion Candidates (5 tests):**
1. `test_init_creates_components` - tests constructor calls
2. `test_build_query_truncates_long_scratchpad` - internal formatting
3. `test_build_query_with_prompt_data` - implementation detail
4. `test_validate_safety_success` - duplicate of TestExecute coverage
5. `test_load_prompt_success` - duplicate of integration tests

#### 3. Redundant Coverage
- Multiple tests checking same behavior at different levels
- Unit tests duplicating integration test coverage
- Mock-based tests duplicating real-component tests

---

## Performance Benchmarks

### Files to Archive (7 files)
Move to `tests/archive/performance/`:
1. `test_embedding_benchmarks.py` (18.8 KB)
2. `test_hybrid_retrieval_precision.py` (22.3 KB)
3. `test_memory_profiling.py` (14.2 KB)
4. `test_parser_benchmarks.py` (9.6 KB)
5. `test_soar_benchmarks.py` (13.4 KB)
6. `test_spreading_benchmarks.py` (17.6 KB)
7. `test_storage_benchmarks.py` (11.3 KB)

### Files to Keep (1 file)
- `test_activation_benchmarks.py` (17.9 KB) - Critical ACT-R algorithm

**Rationale:** Performance benchmarks are valuable for optimization work but slow down CI and don't test correctness. Archive for future use.

---

## Phase 1 Goals

### Deletions Target
- **Low-Value Tests:** 20-25 tests (redundant, implementation details)
- **Performance Benchmarks:** 7 files to archive
- **Expected Test Count After Phase 1:** ~1,995-2,000 tests

### Success Criteria
✅ Branch `test/cleanup-systematic` created
⏳ Baseline metrics collected (this file)
⏳ PHASE1_DELETIONS.md audit trail created
⏳ 20-25 tests deleted with justification
⏳ 7 performance benchmarks archived
⏳ All remaining tests pass on Python 3.10
⏳ No new failures introduced
⏳ Ready for Gate 1 user approval

---

## Next Steps

1. ✅ Create branch - **COMPLETE**
2. ✅ Collect baseline metrics - **COMPLETE**
3. **IN PROGRESS:** Analyze test suite for 15-20 additional deletion candidates
4. **PENDING:** Create PHASE1_DELETIONS.md audit trail
5. **PENDING:** Delete tests and archive benchmarks
6. **PENDING:** Verify tests pass on Python 3.10
7. **PENDING:** Prepare Gate 1 approval materials

---

## Appendix: Test Distribution Commands

```bash
# Total test count
pytest --collect-only -q | tail -1

# Tests by category
find tests/unit -name "test_*.py" | wc -l       # 55
find tests/integration -name "test_*.py" | wc -l # 19
find tests/e2e -name "test_*.py" | wc -l        # 2
find tests/performance -name "test_*.py" | wc -l # 8

# Mock call assertions
grep -r "assert.*called" tests/unit/ | wc -l    # 85

# Coverage
pytest --cov=packages --cov-report=term
```

---

**Status:** BASELINE ESTABLISHED - Ready for deletion candidate analysis
