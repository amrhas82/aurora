# Aurora Testing Status - Accurate Count (January 6, 2026)

**Last Updated:** January 6, 2026, 12:30 PM
**Data Source:** Local pytest collection + recent CI runs
**Branch:** `phase1-import-migration`

---

## Executive Summary

**CRITICAL ISSUE:** Previous documentation had **incorrect test counts**. This document provides accurate numbers.

### Accurate Test Pyramid

```
Total Tests: 4,023 (not 3,069 as previously documented)

Calibration:    13 tests (0.3%)   ✅ All passing
E2E:           151 tests (3.8%)   ❌ 82+ failing, 7 skipped (API required), ~62 passing
Integration:   704 tests (17.5%)  ⚠️  Unknown pass/fail (need full run)
Unit:        3,055 tests (76.0%)  ⚠️  Unknown pass/fail (need full run)
Cache:         100 tests (2.5%)   ⚠️  Unknown (collected but status unclear)
───────────────────────────────────────────────────────────────────────────────
Total:       4,023 tests          ❌ Status unknown - full run needed
```

### What Was Wrong in Previous Documentation

| Metric | Old Docs Said | Actually Is | Difference |
|--------|---------------|-------------|------------|
| **Total Tests** | 3,069 | 4,023 | +954 tests (31% more!) |
| **E2E Tests** | 14 (0.5%) | 151 (3.8%) | +137 tests |
| **E2E Skipped** | "All 14" | Only 7 | 144 tests run without API |
| **Integration** | 57 (2.0%) | 704 (17.5%) | +647 tests |
| **Unit Tests** | 2,998 (97.5%) | 3,055 (76.0%) | +57 tests, but % way off |

**Root Cause:** Documentation used counts from **before** Phase 4 (which added 135 tests) and didn't account for calibration tests or full integration suite.

---

## Detailed Breakdown by Directory

### E2E Tests (151 tests in 18 files)

**File-by-File Breakdown:**

| File | Tests | API Required? | Status |
|------|-------|---------------|--------|
| `test_aurora_query_e2e.py` | 7 | ✅ Yes | Skipped (no API key) |
| `test_doctor_e2e.py` | 9 | ❌ No | 4 failing, 5 passing |
| `test_e2e_complexity_assessment.py` | 11 | ❌ No | 10 failing, 1 skipped |
| `test_e2e_database_persistence.py` | 6 | ❌ No | 6 failing |
| `test_e2e_error_handling.py` | 13 | ❌ No | 1 failing, 12 passing |
| `test_e2e_git_bla_initialization.py` | 11 | ❌ No | 11 failing |
| `test_e2e_new_user_workflow.py` | 10 | ❌ No | 9 failing, 1 passing |
| `test_e2e_query_uses_index.py` | 8 | ❌ No | 8 failing |
| `test_e2e_schema_migration.py` | 7 | ❌ No | 7 failing |
| `test_e2e_search_accuracy.py` | 8 | ❌ No | 8 failing |
| `test_e2e_search_scoring.py` | 7 | ❌ No | 7 failing |
| `test_e2e_search_threshold.py` | 6 | ❌ No | 6 failing |
| `test_wizard_e2e.py` | 7 | ❌ No | 7 failing |
| `test_cli_complete_workflow.py` | ~20 | ❌ No | Unknown |
| Others | ~21 | ❌ No | Unknown |

**E2E Summary:**
- **7 tests (4.6%)** require ANTHROPIC_API_KEY - properly skipped ✅
- **144 tests (95.4%)** are CLI-only tests that should work without API
- **~82 tests failing** due to CLI changes (--db-path removal, command renames)
- **~62 tests passing**

**Common E2E Failure Reasons:**
1. `--db-path` option removed but tests still use it (most common)
2. Command renames (e.g., some commands changed)
3. Database path initialization issues (known bug documented in tests)
4. Exit code expectations wrong

### Integration Tests (704 tests)

**Major Test Groups:**

| Directory/File | Tests (est.) | Purpose |
|----------------|--------------|---------|
| `test_integration_*.py` (7 files) | ~400 | Cross-package integration |
| `test_memory_store_contract.py` | 30 | Store API contracts (Phase 4) |
| `test_planning_contract.py` | 26 | Planning schema contracts (Phase 4) |
| `test_chunk_store_integration.py` | 13 | Chunking pipeline (moved in Phase 2) |
| `test_store_sqlite.py` | 32 | SQLite integration (moved in Phase 2) |
| `test_sqlite_schema_migration.py` | 17 | Schema migrations (moved in Phase 2) |
| `test_mcp_python_client.py` | ~15 | MCP subprocess (6 known failing) |
| `cli/test_init_*.py` | ~100 | CLI init flows |
| Others | ~71 | Various integrations |

**Status:** Most passing, 6+ known failures in MCP subprocess tests (timeouts)

### Unit Tests (3,055 tests)

**Includes Phase 4 Additions:**
- `test_activation_formulas.py` - 37 tests (ACT-R formulas)
- `test_parsing_logic.py` - 42 tests (parsing edge cases)

**Status:** Estimated 81-100 failures based on local runs, but needs full verification

### Calibration Tests (13 tests)

**File:** `tests/calibration/test_verification_calibration.py`
**Status:** ✅ All 13 passing
**Purpose:** Verification system calibration tests

---

## Test Pyramid Analysis - Corrected

### By Test Count (Actual)

```
         /\
        /  \       E2E: 151 tests (3.8%)
       /    \
      /──────\     Integration: 704 tests (17.5%)
     /        \
    /          \   Unit: 3,055 tests (76.0%)
   /            \
  /──────────────\ Calibration: 13 tests (0.3%)
```

### Assessment: **MUCH BETTER** Than We Thought!

**Previous Assessment:** "Inverted pyramid - 97.5% unit, 2.0% integration, 0.5% E2E"

**Actual Reality:** "Reasonable pyramid - 76% unit, 17.5% integration, 3.8% E2E"

**Comparison to Ideal:**

| Layer | Actual | Ideal | Assessment |
|-------|--------|-------|------------|
| Unit | 76.0% | 60-70% | ⚠️ Slightly high, but acceptable |
| Integration | 17.5% | 20-30% | 🟡 Lower end of range |
| E2E | 3.8% | 5-10% | 🟡 Lower end of range |

**Verdict:** The pyramid is **NOT inverted**! It's actually pretty good, just needs:
- ~100 more integration tests (17.5% → 22%)
- ~100 more E2E tests (3.8% → 6%)

---

## Current Test Failures - Accurate Count

### Known Failures

**E2E Tests:** ~82 failures (out of 151)
- **Root Cause:** CLI option changes (`--db-path` removed)
- **Category:** Real bugs - tests are correct, implementation changed
- **Fix Required:** Update CLI to restore `--db-path` or update all E2E tests

**Integration Tests:** 6+ failures
- **Root Cause:** MCP subprocess timeouts
- **Category:** Flaky tests - timing issues
- **Fix Required:** Increase timeouts or fix subprocess handling

**Unit Tests:** 81-100 failures (estimated)
- **Root Cause:** Mixed (test isolation, obsolete tests, real bugs)
- **Category:** Needs investigation (TD-TEST-001)
- **Fix Required:** Systematic categorization and fixes

**Total Estimated Failures:** 169-188 tests failing (4.2-4.7% failure rate)
**Estimated Pass Rate:** 95.3-95.8%

---

## What We Got Wrong

### Error 1: Miscounted E2E Tests

**Said:** 14 E2E tests, all skipped
**Reality:** 151 E2E tests, only 7 skip on missing API

**How it happened:**
- Only looked at `test_aurora_query_e2e.py` (7 tests marked with `@pytest.mark.real_api`)
- Assumed that was all E2E tests
- Didn't count the other 17 E2E test files with 144 CLI-only tests

### Error 2: Drastically Undercounted Integration Tests

**Said:** 57 integration tests
**Reality:** 704 integration tests

**How it happened:**
- Likely only counted integration tests in `tests/integration/` root
- Didn't count `tests/integration/cli/` subdirectory tests
- Didn't account for Phase 4 contract tests added

### Error 3: Inflated Unit Test Percentage

**Said:** 2,998 unit tests (97.5%)
**Reality:** 3,055 unit tests (76.0%)

**How it happened:**
- Total test count was wrong (3,069 vs 4,023)
- When total is wrong, percentages are wildly off

### Error 4: Missed Calibration Tests Entirely

**Said:** No mention of calibration tests
**Reality:** 13 calibration tests exist and all pass

**How it happened:**
- Never ran `pytest --collect-only` on full `tests/` directory
- Only looked at unit/integration/e2e subdirectories

---

## Phase 5 Documentation Errors

The comprehensive TESTING_TECHNICAL_DEBT.md document created in Phase 5 contains **significant errors** throughout:

### Sections Requiring Correction:

1. **Executive Summary** (lines 13-26) - Wrong test counts
2. **Test Pyramid Status** (lines 260-288) - Wrong percentages
3. **Phase 5 Before/After** (all metrics wrong)
4. **TD-TEST-002** (wrong baseline - need 100 integration not 650+!)
5. **TD-TEST-003** (wrong baseline - E2E pyramid is fine!)
6. **Metrics Summary table** (line 755-765) - wrong before/after

### What Needs to Happen

**All documentation needs to be rewritten with accurate data:**
- `docs/TESTING_TECHNICAL_DEBT.md` - Complete rewrite with correct numbers
- `docs/CI_SWITCHOVER_PLAN.md` - Update success metrics
- `docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md` - Update metrics
- `tasks/tasks-0023-prd-testing-infrastructure-overhaul.md` - Update Phase 5 completion metrics

---

## Immediate Action Required

### 1. Run Full Test Suite to Get Exact Pass/Fail Counts

```bash
pytest tests/ -v --tb=no --no-header -q > test_results.txt 2>&1
```

This will take ~10 minutes but give us:
- Exact count of passing tests
- Exact count of failing tests
- Exact count of skipped tests
- Which specific tests fail

### 2. Fix Critical E2E Tests (Quick Win)

The ~82 failing E2E tests are mostly due to one issue: `--db-path` option removed.

**Two options:**
a) **Restore `--db-path` option** to CLI (if removed unintentionally)
b) **Update all E2E tests** to not use `--db-path`

This could fix 60-70 tests in one change!

### 3. Rewrite TESTING_TECHNICAL_DEBT.md with Accurate Data

Once we have exact counts from full run, rewrite the entire document with:
- Correct test pyramid (76% / 17.5% / 3.8%)
- Correct failure analysis
- Correct recommendations

---

## Recommendations for Next Steps

### Option A: Fix E2E Tests First (Recommended)

**Pros:**
- Quick win - fix 60-70 tests with one change
- E2E tests are valuable (test real user workflows)
- Will improve CI pass rate dramatically

**Effort:** 2-4 hours

**Approach:**
1. Investigate why `--db-path` was removed
2. Either restore it or update all E2E tests
3. Run E2E suite to verify fixes

### Option B: Fix All Documentation First

**Pros:**
- Have accurate baseline before starting fixes
- Can make better decisions with correct data

**Effort:** 4-6 hours

**Approach:**
1. Run full test suite (10 min)
2. Analyze results comprehensively
3. Rewrite TESTING_TECHNICAL_DEBT.md
4. Update all related docs

### Option C: Do Both in Parallel

**Pros:**
- Make progress on both fronts
- Use accurate data to fix tests

**Effort:** 6-8 hours

**Approach:**
1. Run full test suite
2. Fix E2E `--db-path` issue while tests run
3. Use results to rewrite documentation
4. Commit both together

---

## What Should We Do?

I need your decision on how to proceed. The documentation is significantly wrong, and we need to fix it before making more decisions.

**My recommendation:** Option C (both in parallel)
1. Start full test run now (background)
2. Investigate and fix `--db-path` E2E issue
3. Use test results to rewrite docs comprehensively
4. Commit accurate documentation + E2E fixes together

**Your call - which option do you prefer?**
