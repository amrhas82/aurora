# PRD-0023: Aurora Testing Infrastructure Overhaul

**Status**: Draft
**Created**: 2026-01-06
**Owner**: Solo Developer
**Target Completion**: 2-3 weeks (phased releases)
**Complexity**: High
**Priority**: Critical (Phase 1), High (Phases 2-3), Medium (Phases 4-5)

---

## Executive Summary

Aurora's testing infrastructure is in a critical state with 20 consecutive CI failures since December 30, 2025. The root cause is a module refactoring that changed package names from `aurora.*` to `aurora_*`, breaking 73 test files. Beyond this immediate crisis, the test suite suffers from systemic issues: an inverted test pyramid (80% unit / 16% integration / 4% e2e instead of 60/30/10), marker bloat (14 markers defined, only 1 used), and test misclassification that masks true coverage gaps.

This PRD outlines a **comprehensive, methodical overhaul** delivered in 5 phases with verification gates between each phase:

1. **Phase 1 (CRITICAL)**: Restore CI - Fix import paths, create missing modules
2. **Phase 2 (HIGH)**: Reclassify Tests - Correct the test pyramid
3. **Phase 3 (MEDIUM)**: Clean Markers - Reduce from 14 to 3 markers
4. **Phase 4 (OPTIONAL)**: Add Missing Tests - Fill critical coverage gaps
5. **Phase 5 (HIGH)**: Document & Prevent - Ensure this never happens again

**Success Criteria**: CI passes on Python 3.10-3.13, proper 60/30/10 test pyramid, 82%+ measured coverage, zero test collection errors, comprehensive migration documentation.

**Philosophy**: Long-term sustainable solutions over quick fixes. Root cause resolution with regression prevention. Methodical execution with per-phase verification gates.

---

## Problem Statement

### Current Crisis

**Symptom**: 20 consecutive CI failures, 73 test files unable to load, coverage unmeasurable.

**Root Cause Analysis**:

1. **Import Path Breakage** (CRITICAL)
   - **What happened**: Module refactoring changed `aurora.*` → `aurora_*` package names
   - **Impact**: 73 test files still use old import paths (e.g., `from aurora.memory import ...`)
   - **Why it happened**: Automated refactoring tools updated production code but missed test files
   - **Why it wasn't caught**: CI was already in failing state, no pre-commit hooks for import validation
   - **Production bug**: Missing `aurora_planning.configurators.base` module (referenced but never created)

2. **Test Misclassification** (HIGH)
   - **What happened**: Tests placed in wrong directories despite proper behavior classification
   - **Impact**: 18+ integration tests in `tests/unit/`, 15+ e2e tests in `tests/unit/`
   - **Evidence**: Tests marked with docstrings saying "Integration tests" but in unit/ directory
   - **Why it happened**: Organic growth without enforcement of classification criteria
   - **Result**: Inverted pyramid (80/16/4) instead of healthy pyramid (60/30/10)

3. **Marker Bloat** (MEDIUM)
   - **What happened**: 14 markers defined in pytest.ini, only 1 (`ml`) used in CI
   - **Impact**: 0% adoption for most markers (unit, integration, e2e, critical, slow, etc.)
   - **Why it happened**: Over-engineering during initial test infrastructure setup
   - **Why it persists**: Directory structure makes markers redundant (tests/unit/ vs @pytest.mark.unit)

4. **Coverage Measurement Breakdown** (CASCADING)
   - **What happened**: Test collection errors prevent coverage calculation
   - **Impact**: Cannot measure progress, cannot verify regressions
   - **Why critical**: Previous PRD-0009 achieved 81.93% coverage, now unmeasurable

### Historical Context

**PRD-0009 (December 2025)**: Test Suite Systematic Cleanup
- Converted 79 @patch tests to DI pattern
- Added 26 integration tests
- Achieved 81.93% coverage
- Created comprehensive documentation (TESTING.md, TESTING_TECHNICAL_DEBT.md)

**Gap**: PRD-0009 did not account for:
- Module refactoring impact on test imports
- Test classification enforcement
- Regression prevention mechanisms
- Import validation automation

**Lesson**: Quality improvements without regression prevention are fragile.

### User Requirements

From stakeholder (solo developer):
- "Long-term clean fixes, not band-aids"
- "Fix why it broke, not just symptoms"
- "Not in a hurry - comprehensive solution over quick fix"
- "Sustainable - prevent future regressions"

**Translation**: Invest time upfront in root cause analysis, automation, and prevention rather than iterative fire-fighting.

---

## Goals & Success Metrics

### Goals

1. **Restore CI Stability** - 100% green builds across Python 3.10-3.13
2. **Correct Test Pyramid** - Achieve industry-standard 60/30/10 distribution
3. **Simplify Marker Strategy** - Reduce cognitive overhead, increase adoption
4. **Measurable Coverage** - Restore and improve coverage measurement (82%+ target)
5. **Prevent Recurrence** - Automation and documentation to prevent future breakage
6. **Fill Critical Gaps** - Add tests for high-risk areas (ACT-R formulas, parsing, boundaries)

### Success Metrics

| Metric | Before | After | Measurement |
|--------|--------|-------|-------------|
| **CI Status** | 20 consecutive failures | 0 failures | GitHub Actions dashboard |
| **Test Collection** | 73 errors | 0 errors | `pytest --collect-only` |
| **Test Pyramid** | 80/16/4 (inverted) | 60/30/10 ± 5% | Directory file counts |
| **Marker Adoption** | 14 defined, 5% used | 3 defined, 100% used | `pytest --markers` + grep |
| **Coverage** | Unmeasurable | 82%+ measured | `pytest --cov` |
| **Test Count** | 2,482 (when fixed) | 2,550+ | Pytest summary |
| **Pre-commit Pass** | N/A (doesn't exist) | 100% on commit | Pre-commit hook logs |
| **Documentation** | Outdated (pre-refactor) | Current + migration guide | Manual review |

### Non-Functional Requirements

- **Maintainability**: Tests should be easy to classify, find, and run
- **Developer Experience**: Clear error messages, fast feedback loops
- **Stability**: Tests should be deterministic, not flaky
- **Performance**: Unit tests <1s, integration tests <10s, e2e tests <60s
- **Portability**: Tests pass on Python 3.10, 3.11, 3.12, 3.13

---

## User Stories

### Epic 1: Restore CI Stability

**US-1.1**: As a developer, I want all tests to be collected without errors so that I can run the test suite.
- **Acceptance Criteria**:
  - `pytest --collect-only` completes with 0 errors
  - All 73 previously broken test files now import successfully
  - Missing `aurora_planning.configurators.base` module exists and is functional
  - Import path migration script available with dry-run mode

**US-1.2**: As a developer, I want CI to pass on all supported Python versions so that I can merge PRs confidently.
- **Acceptance Criteria**:
  - CI passes on Python 3.10, 3.11, 3.12, 3.13
  - No test failures, no collection errors
  - Coverage measurement working and reported
  - CI run time ≤ 10 minutes

### Epic 2: Correct Test Classification

**US-2.1**: As a developer, I want tests organized by their actual behavior (unit/integration/e2e) so that I can run the appropriate test level.
- **Acceptance Criteria**:
  - All subprocess-using tests moved to integration/ or e2e/
  - All SQLiteStore-using tests moved to integration/
  - Tests in unit/ have no external dependencies (pure functions, DI mocks)
  - Test pyramid is 60/30/10 ± 5%

**US-2.2**: As a developer, I want test dependencies analyzed before migration so that I don't break dependent tests.
- **Acceptance Criteria**:
  - Dependency analysis script identifies all cross-file dependencies
  - Tests moved in dependency order (dependencies first)
  - 0 new test failures introduced during migration
  - Verification script confirms all tests still pass after each batch move

### Epic 3: Simplify Marker Strategy

**US-3.1**: As a developer, I want a minimal set of markers that are actually useful so that I don't waste time applying unused markers.
- **Acceptance Criteria**:
  - pytest.ini defines exactly 3 markers: `ml`, `slow`, `real_api`
  - All 11 unused markers removed from pytest.ini
  - CI uses markers appropriately (skip `ml` without deps, skip `real_api` in CI, report `slow` tests)
  - Documentation explains when to use each marker

**US-3.2**: As a developer, I want directory structure to convey test type so that markers are only for special cases.
- **Acceptance Criteria**:
  - No `@pytest.mark.unit` (redundant with tests/unit/ directory)
  - No `@pytest.mark.integration` (redundant with tests/integration/ directory)
  - No `@pytest.mark.e2e` (redundant with tests/e2e/ directory)
  - Documentation explains directory-based test classification

### Epic 4: Fill Critical Test Gaps

**US-4.1**: As a developer, I want pure unit tests for core algorithms so that I can refactor confidently without breaking business logic.
- **Acceptance Criteria**:
  - 15-20 pure unit tests for ACT-R formulas (activation, base-level learning, spreading activation)
  - 10-15 pure unit tests for parsing logic (chunk parsing, context extraction)
  - Tests use property-based testing (Hypothesis) where appropriate
  - 100% coverage of core algorithm edge cases

**US-4.2**: As a developer, I want contract tests for package boundaries so that I detect breaking changes early.
- **Acceptance Criteria**:
  - 8-10 contract tests for public APIs (aurora_memory, aurora_planning, aurora_cli)
  - Tests verify input/output contracts (types, shapes, constraints)
  - Tests fail if breaking changes introduced to public interfaces
  - Documentation explains contract test philosophy

**US-4.3**: As a developer, I want e2e tests for complete user journeys so that I verify real-world workflows.
- **Acceptance Criteria**:
  - 6-8 e2e tests covering: init → search → query → plan → archive
  - Tests use temporary directories, no shared state
  - Tests verify CLI output, file creation, database state
  - Tests complete in <60s each

### Epic 5: Prevent Future Regressions

**US-5.1**: As a developer, I want pre-commit hooks to catch import path errors so that I never break tests again.
- **Acceptance Criteria**:
  - Pre-commit hook validates import paths (detects old `aurora.*` patterns)
  - Pre-commit hook validates test classification (detects integration tests in unit/)
  - Pre-commit hook validates marker usage (detects redundant markers)
  - Hook runs in <2s, provides actionable error messages

**US-5.2**: As a developer, I want comprehensive migration documentation so that future refactorings don't break tests.
- **Acceptance Criteria**:
  - TEST_MIGRATION_CHECKLIST.md created with step-by-step guide
  - TESTING.md updated with new import patterns and test classification criteria
  - Root cause analysis document explains what went wrong and why
  - Documentation reviewed and approved by stakeholder

**US-5.3**: As a developer, I want parallel CI during migration so that I can verify changes without downtime.
- **Acceptance Criteria**:
  - Legacy CI workflow (current) continues running
  - New CI workflow created and runs in parallel
  - Both workflows report status, clearly labeled
  - Switchover plan documented, ready to execute when Phase 1 complete

---

## Detailed Requirements

### Phase 1: FIX - Restore CI (CRITICAL)

**Timeline**: 2-3 hours
**Verification Gate**: CI passes, all tests collected, coverage measurable

#### FR-1.1: Create Missing Module
- **Description**: The module `aurora_planning.configurators.base` is referenced but doesn't exist
- **Implementation**:
  1. **Code Archaeology**: Search codebase for references to `configurators.base`
  2. **Intent Discovery**: Analyze what the module was supposed to contain (base classes? protocols?)
  3. **Implementation**: Create proper module with necessary base classes/protocols
  4. **Validation**: Verify all references now resolve correctly
- **Acceptance Criteria**:
  - Module `aurora_planning/configurators/base.py` exists
  - All imports from `aurora_planning.configurators.base` succeed
  - Module contains necessary base classes/protocols (not empty stub)
  - Documentation explains module purpose

#### FR-1.2: Automated Import Path Migration
- **Description**: Update 73 test files from old `aurora.*` imports to new `aurora_*` imports
- **Implementation**:
  1. **Create Migration Script**: Python script using AST parsing to identify and update imports
  2. **Dry-Run Mode**: Generate diff output showing all proposed changes
  3. **User Approval**: Review diff, approve changes
  4. **Apply Changes**: Execute migration script
  5. **Verification**: Run `pytest --collect-only`, verify 0 errors
- **Acceptance Criteria**:
  - Migration script supports dry-run mode (no changes applied)
  - Script output shows: file path, old import, new import, line number
  - User can review and approve changes before applying
  - Script logs all changes made (for rollback if needed)
  - All 73 test files successfully collect after migration
- **Migration Patterns**:
  ```python
  # OLD (before)
  from aurora.memory import MemoryStore
  from aurora.planning.schemas import Plan
  import aurora.cli.commands as commands

  # NEW (after)
  from aurora_memory import MemoryStore
  from aurora_planning.schemas import Plan
  import aurora_cli.commands as commands
  ```

#### FR-1.3: Verify Test Collection
- **Description**: Ensure all tests can be collected without errors
- **Implementation**:
  1. Run `pytest --collect-only` across all test directories
  2. Parse output, identify any remaining collection errors
  3. Fix any edge cases not caught by automated migration
  4. Document any manual fixes required
- **Acceptance Criteria**:
  - `pytest --collect-only` completes with 0 errors
  - All 2,482+ tests successfully collected
  - Test count matches or exceeds baseline (2,482)
  - No deprecation warnings related to imports

#### FR-1.4: Restore Coverage Measurement
- **Description**: Verify coverage can be measured again
- **Implementation**:
  1. Run `pytest --cov=aurora_memory --cov=aurora_planning --cov=aurora_cli`
  2. Verify coverage report generated
  3. Establish baseline coverage (should be ~81.93% from PRD-0009)
  4. Document any coverage drops and reasons
- **Acceptance Criteria**:
  - Coverage report generated successfully
  - Coverage ≥ 80% (allowing for minor regression)
  - Coverage delta tracked (difference from 81.93% baseline)
  - Coverage report includes all production packages

#### FR-1.5: CI Restoration
- **Description**: Get CI passing on all Python versions
- **Implementation**:
  1. Create new CI workflow (`testing-infrastructure-new.yml`)
  2. Configure to run on Python 3.10, 3.11, 3.12, 3.13
  3. Run tests with coverage
  4. Upload coverage reports
  5. Run in parallel with legacy CI (don't replace yet)
- **Acceptance Criteria**:
  - New CI workflow passes on all Python versions
  - CI run time ≤ 10 minutes
  - Coverage reports uploaded to codecov or similar
  - Legacy CI still running (for comparison)

**Rollback Plan (Phase 1)**:
- Migration script creates backup branch before applying changes
- Git commit per logical change (module creation, import migration, CI update)
- Can revert individual commits if issues found
- Backup of original test files in `.migration-backup/` directory

**Verification Checklist (Phase 1)**:
- [ ] `pytest --collect-only` shows 0 errors
- [ ] All 73 previously broken test files now import
- [ ] `aurora_planning.configurators.base` module exists and is functional
- [ ] CI passes on Python 3.10, 3.11, 3.12, 3.13
- [ ] Coverage report generated showing ≥80%
- [ ] Migration script available for future use
- [ ] All changes committed with clear messages

---

### Phase 2: RECLASSIFY - Fix Test Pyramid (HIGH)

**Timeline**: 4-5 hours
**Verification Gate**: Test pyramid 60/30/10 ± 5%, all tests still pass

#### FR-2.1: Test Dependency Analysis
- **Description**: Analyze test dependencies before moving files to prevent breakage
- **Implementation**:
  1. **Create Analysis Script**: Parse imports in all test files, build dependency graph
  2. **Identify Clusters**: Group tests by shared dependencies
  3. **Determine Move Order**: Move tests in dependency order (dependencies first)
  4. **Generate Migration Plan**: Document which tests move in which order
- **Acceptance Criteria**:
  - Dependency analysis script outputs graph (JSON or DOT format)
  - Script identifies circular dependencies (if any)
  - Migration plan documents move order: batch 1, batch 2, etc.
  - Plan reviewed and approved before execution

#### FR-2.2: Define Test Classification Criteria
- **Description**: Clear, objective criteria for unit vs integration vs e2e
- **Implementation**:
  - Document criteria in TESTING.md
  - Create classification decision tree
  - Provide examples of each category
- **Criteria**:

  **Unit Tests**:
  - ✅ Test single function/class in isolation
  - ✅ Use dependency injection with test doubles (mocks, fakes)
  - ✅ No file I/O, no subprocess, no network, no database
  - ✅ Fast (<1s total runtime)
  - ✅ Deterministic (same input → same output)

  **Integration Tests**:
  - ✅ Test multiple components working together
  - ✅ May use real implementations of some dependencies (e.g., SQLiteStore)
  - ✅ May use subprocess to test CLI commands
  - ✅ May use temporary files/directories
  - ✅ Medium speed (<10s total runtime)
  - ✅ Still deterministic (isolated state)

  **E2E Tests**:
  - ✅ Test complete user workflows end-to-end
  - ✅ Use real CLI, real file system, real database
  - ✅ May test multi-step processes (init → search → query → plan)
  - ✅ Slower (<60s per test)
  - ✅ Clean up state after each test

- **Acceptance Criteria**:
  - Classification criteria documented in TESTING.md
  - Decision tree diagram created
  - 5+ examples provided for each category
  - Criteria reviewed and approved

#### FR-2.3: Identify Misclassified Tests
- **Description**: Find all tests in wrong directories
- **Implementation**:
  1. **Create Analysis Script**: Parse test files, detect integration/e2e signals
  2. **Detection Heuristics**:
     - Uses `subprocess` → integration or e2e
     - Uses `SQLiteStore` (not mocked) → integration
     - Uses `tmp_path` + multi-step workflow → e2e
     - Docstring says "Integration" but in unit/ → integration
  3. **Generate Report**: List of misclassified tests with rationale
  4. **Manual Review**: Stakeholder reviews and approves list
- **Acceptance Criteria**:
  - Analysis script outputs report: test file, current location, proposed location, reason
  - Report identifies at least 18+ integration tests in unit/
  - Report identifies at least 15+ e2e tests in unit/
  - Report reviewed and approved before migration

#### FR-2.4: Migrate Tests (Batch Processing)
- **Description**: Move tests to correct directories in dependency order
- **Implementation**:
  1. **Batch 1**: Move tests with no dependencies on tests being moved
  2. **Verify**: Run full test suite, ensure 0 new failures
  3. **Batch 2**: Move next group based on dependency order
  4. **Verify**: Run full test suite, ensure 0 new failures
  5. **Repeat**: Until all tests moved
- **Migration Process** (per batch):
  ```bash
  # 1. Create branch for batch
  git checkout -b phase2-reclassify-batch-N

  # 2. Move test files
  mv tests/unit/test_foo.py tests/integration/test_foo.py

  # 3. Update imports in moved files (if needed)
  # 4. Run tests
  pytest tests/unit/ tests/integration/ tests/e2e/

  # 5. Verify 0 new failures
  # 6. Commit batch
  git add -A
  git commit -m "refactor(tests): reclassify batch N - move integration tests"

  # 7. Merge to main (or phase2 branch)
  ```
- **Acceptance Criteria**:
  - Tests moved in batches (not all at once)
  - Each batch verified before next batch
  - 0 new test failures introduced
  - All moved tests have updated imports (if needed)
  - Git history shows clear batch-by-batch migration

#### FR-2.5: Verify Test Pyramid
- **Description**: Confirm test distribution matches 60/30/10 target
- **Implementation**:
  1. Count tests in each directory
  2. Calculate percentages
  3. Compare to target (60% unit, 30% integration, 10% e2e)
  4. Document any deviations and rationale
- **Acceptance Criteria**:
  - Test count script outputs: unit count, integration count, e2e count, percentages
  - Distribution is 60/30/10 ± 5%
  - Any deviations documented and justified
  - Test pyramid visualization updated in TESTING.md

**Rollback Plan (Phase 2)**:
- Each batch is a separate git commit
- Can revert individual batches if issues found
- Dependency analysis ensures partial rollback doesn't break tests
- Test count script can verify pyramid at any point

**Verification Checklist (Phase 2)**:
- [ ] All tests still pass (0 new failures)
- [ ] Test pyramid is 60/30/10 ± 5%
- [ ] No integration tests remain in tests/unit/
- [ ] No e2e tests remain in tests/unit/ or tests/integration/
- [ ] Dependency analysis script available for future use
- [ ] Migration batches documented with clear commit messages
- [ ] TESTING.md updated with classification criteria

---

### Phase 3: CLEAN - Remove Marker Bloat (MEDIUM)

**Timeline**: 1 hour
**Verification Gate**: 3 markers defined, 100% used appropriately, tests still pass

#### FR-3.1: Audit Current Marker Usage
- **Description**: Identify which markers are actually used vs defined
- **Implementation**:
  1. Parse pytest.ini, extract all defined markers
  2. Grep test files for `@pytest.mark.*` usage
  3. Cross-reference with CI workflows
  4. Generate usage report
- **Acceptance Criteria**:
  - Usage report shows: marker name, definition location, usage count, files using it
  - Report confirms only `ml` marker used in CI
  - Report confirms 0% adoption for most markers
  - Report identifies redundant markers (unit, integration, e2e)

#### FR-3.2: Define Minimal Marker Set
- **Description**: Reduce from 14 markers to 3 essential markers
- **Implementation**:
  - **Keep**: `ml` (tests requiring ML dependencies), `slow` (tests >5s), `real_api` (tests calling external APIs)
  - **Remove**: `unit`, `integration`, `e2e` (redundant with directory structure)
  - **Remove**: `critical`, `smoke`, `regression` (unused, unclear criteria)
  - **Remove**: `security`, `performance`, `flaky` (unused, wrong approach)
- **Rationale**:
  - Directory structure conveys test type (tests/unit/ → unit test)
  - Markers should be for special cases not covered by directory structure
  - `ml`: tests that fail without torch/transformers installed
  - `slow`: tests that need to be tracked/optimized (>5s runtime)
  - `real_api`: tests that call external services (skip in CI)
- **Acceptance Criteria**:
  - Marker philosophy documented in TESTING.md
  - Criteria for each marker documented (when to use, when not to use)
  - Decision rationale captured (why 3 markers, not 14)

#### FR-3.3: Update pytest.ini
- **Description**: Remove unused markers from pytest.ini
- **Implementation**:
  1. Backup current pytest.ini
  2. Remove 11 unused marker definitions
  3. Keep 3 essential markers with clear descriptions
  4. Run tests, verify no warnings about unknown markers
- **New pytest.ini markers section**:
  ```ini
  [tool:pytest]
  markers =
      ml: Tests requiring ML dependencies (torch, transformers) - skip if not installed
      slow: Tests with runtime >5s - tracked for optimization opportunities
      real_api: Tests calling external APIs - skip in CI, run manually for integration verification
  ```
- **Acceptance Criteria**:
  - pytest.ini contains exactly 3 marker definitions
  - Each marker has clear description
  - Running tests produces 0 warnings about unknown markers

#### FR-3.4: Update CI Workflows
- **Description**: Update CI to use minimal marker set appropriately
- **Implementation**:
  1. Update CI to skip `ml` tests by default (run in separate job if deps installed)
  2. Update CI to skip `real_api` tests (external dependencies)
  3. Update CI to report `slow` tests (informational, not skip)
  4. Remove references to unused markers
- **CI Configuration**:
  ```yaml
  # Main test job (fast feedback)
  - name: Run tests (excluding ML and real API)
    run: pytest -m "not ml and not real_api" --cov --cov-report=xml

  # Optional ML test job (only if deps installed)
  - name: Run ML tests
    run: pytest -m "ml"
    continue-on-error: true  # Don't block PR if ML deps not available

  # Report slow tests (informational)
  - name: Report slow tests
    run: pytest -m "slow" --durations=10
  ```
- **Acceptance Criteria**:
  - CI skips `ml` tests by default
  - CI skips `real_api` tests always
  - CI reports `slow` tests but doesn't skip them
  - CI run time reduced (no unnecessary test runs)

#### FR-3.5: Remove Redundant Markers from Test Files
- **Description**: Remove `@pytest.mark.unit`, etc. from test files (redundant with directory)
- **Implementation**:
  1. Create script to detect redundant markers
  2. Script outputs list of files with redundant markers
  3. Automated removal (with dry-run mode)
  4. Manual review and approval
  5. Apply changes
- **Detection Logic**:
  - Test in `tests/unit/` with `@pytest.mark.unit` → redundant
  - Test in `tests/integration/` with `@pytest.mark.integration` → redundant
  - Test in `tests/e2e/` with `@pytest.mark.e2e` → redundant
- **Acceptance Criteria**:
  - Script identifies all redundant markers
  - Script supports dry-run mode
  - All redundant markers removed
  - Tests still pass after removal

**Rollback Plan (Phase 3)**:
- Backup pytest.ini before changes
- Git commit per logical change (pytest.ini, CI update, marker removal)
- Can revert individual commits if issues found
- No test behavior changes (only organizational)

**Verification Checklist (Phase 3)**:
- [ ] pytest.ini contains exactly 3 markers
- [ ] All tests still pass
- [ ] CI updated to use new marker strategy
- [ ] No redundant markers in test files
- [ ] TESTING.md documents marker philosophy
- [ ] CI run time reduced or unchanged

---

### Phase 4: ADD MISSING - Fill Critical Test Gaps (OPTIONAL)

**Timeline**: 6-8 hours
**Verification Gate**: Critical gaps filled, coverage ≥82%, all tests pass

**Note**: This phase is optional but recommended. Tests added based on risk-based priority (highest risk areas first).

#### FR-4.1: Risk Assessment
- **Description**: Identify highest-risk areas lacking test coverage
- **Implementation**:
  1. **Code Complexity Analysis**: Identify complex functions/modules (cyclomatic complexity)
  2. **Coverage Gap Analysis**: Identify uncovered or under-covered critical code
  3. **Historical Bug Analysis**: Review past bugs, identify patterns
  4. **Business Impact Analysis**: Identify core functionality (ACT-R, parsing, memory operations)
  5. **Generate Risk Profile**: Rank areas by risk score (complexity × impact × coverage gap)
- **Risk Categories**:
  - **Critical**: Core algorithms, data integrity, security
  - **High**: CLI commands, API boundaries, error handling
  - **Medium**: Utilities, formatters, helpers
  - **Low**: UI polish, non-critical features
- **Acceptance Criteria**:
  - Risk profile document created
  - All production modules ranked by risk
  - Top 10 highest-risk areas identified
  - Test gaps documented for each high-risk area

#### FR-4.2: Pure Unit Tests for Core Algorithms
- **Description**: Add tests for ACT-R formulas, parsing logic (highest risk)
- **Implementation**:
  1. **ACT-R Activation Tests** (5-7 tests):
     - Base-level learning formula edge cases
     - Spreading activation with multiple sources
     - Decay calculations with extreme time values
     - Activation with missing/invalid parameters
  2. **Parsing Logic Tests** (10-15 tests):
     - Chunk parsing with malformed input
     - Context extraction with edge cases
     - Import statement parsing with complex scenarios
     - AST parsing with Python 3.10-3.13 variations
  3. **Property-Based Tests** (where appropriate):
     - Use Hypothesis for mathematical properties
     - Ensure formulas satisfy invariants (e.g., activation monotonically decreases over time)
- **Example Test**:
  ```python
  # tests/unit/aurora_memory/test_activation_formulas.py

  def test_base_level_learning_with_zero_references():
      """Edge case: activation with zero references should return minimum activation."""
      result = calculate_base_level_learning(references=0, decay=0.5)
      assert result == MIN_ACTIVATION

  @given(st.floats(min_value=0, max_value=1000), st.floats(min_value=0.1, max_value=1.0))
  def test_base_level_learning_decreases_with_time(time_delta, decay):
      """Property: activation decreases as time increases."""
      activation_t1 = calculate_base_level_learning(references=10, decay=decay, time_since=time_delta)
      activation_t2 = calculate_base_level_learning(references=10, decay=decay, time_since=time_delta + 100)
      assert activation_t1 >= activation_t2
  ```
- **Acceptance Criteria**:
  - 15-20 pure unit tests added for core algorithms
  - Tests cover edge cases (zero, negative, extreme values)
  - Tests use property-based testing where appropriate
  - Tests run in <1s total
  - Coverage of core algorithms reaches 100%

#### FR-4.3: Contract Tests for Package Boundaries
- **Description**: Add tests verifying public API contracts
- **Implementation**:
  1. **Identify Public APIs**:
     - `aurora_memory`: MemoryStore, search, query
     - `aurora_planning`: Plan, Task, schemas
     - `aurora_cli`: Command interface, formatters
  2. **Define Contracts**:
     - Input types, output types
     - Required parameters, optional parameters
     - Error conditions, error types
     - Performance constraints (if any)
  3. **Create Contract Tests** (8-10 tests):
     - Test input validation (reject invalid types)
     - Test output shape (correct structure, types)
     - Test error handling (raise expected exceptions)
     - Test backward compatibility (don't break existing usage)
- **Example Test**:
  ```python
  # tests/integration/test_memory_store_contract.py

  def test_memory_store_search_contract():
      """Contract: search returns list of SearchResult with required fields."""
      store = MemoryStore(":memory:")
      results = store.search("test query")

      # Output type contract
      assert isinstance(results, list)
      for result in results:
          assert hasattr(result, "chunk_id")
          assert hasattr(result, "content")
          assert hasattr(result, "score")
          assert isinstance(result.score, float)
          assert 0 <= result.score <= 1

  def test_memory_store_search_rejects_invalid_input():
      """Contract: search rejects non-string queries with TypeError."""
      store = MemoryStore(":memory:")
      with pytest.raises(TypeError):
          store.search(12345)  # Not a string
  ```
- **Acceptance Criteria**:
  - 8-10 contract tests added
  - Tests cover input validation, output shape, error handling
  - Tests fail if contracts broken (e.g., type changes, field removal)
  - Tests documented with clear contract descriptions

#### FR-4.4: E2E Tests for User Journeys
- **Description**: Add tests for complete workflows (init → search → query → plan)
- **Implementation**:
  1. **Identify Key Journeys**:
     - New project setup: `aur init` → verify files created
     - Memory workflow: `aur learn` → `aur search` → `aur query` → verify results
     - Planning workflow: create plan → edit plan → archive plan → verify state
     - MCP workflow: start MCP server → query via MCP → verify response
  2. **Create E2E Tests** (6-8 tests):
     - Use `tmp_path` for isolated test environments
     - Use real CLI via subprocess
     - Verify file system state, database state, CLI output
     - Clean up after each test
- **Example Test**:
  ```python
  # tests/e2e/test_init_search_query_journey.py

  def test_full_memory_workflow(tmp_path):
      """E2E: User can init, learn, search, and query successfully."""
      # Setup
      os.chdir(tmp_path)

      # Step 1: Init
      result = subprocess.run(["aur", "init"], capture_output=True, text=True)
      assert result.returncode == 0
      assert (tmp_path / ".aurora" / "memory.db").exists()

      # Step 2: Learn (add test file)
      test_file = tmp_path / "test.py"
      test_file.write_text("def foo(): pass")
      result = subprocess.run(["aur", "learn", "test.py"], capture_output=True, text=True)
      assert result.returncode == 0

      # Step 3: Search
      result = subprocess.run(["aur", "search", "foo"], capture_output=True, text=True)
      assert result.returncode == 0
      assert "foo" in result.stdout

      # Step 4: Query
      result = subprocess.run(["aur", "query", "what is foo?"], capture_output=True, text=True)
      assert result.returncode == 0
      assert len(result.stdout) > 0
  ```
- **Acceptance Criteria**:
  - 6-8 e2e tests added covering key user journeys
  - Tests use isolated environments (tmp_path)
  - Tests clean up after themselves
  - Tests run in <60s each
  - Tests verify file system, database, and CLI output

**Rollback Plan (Phase 4)**:
- Tests added incrementally (commit after each test file)
- Can skip entire phase if timeline constraints
- Can skip individual test categories if time-limited
- No changes to production code (only test additions)

**Verification Checklist (Phase 4)**:
- [ ] Risk assessment completed
- [ ] 15-20 pure unit tests added for core algorithms
- [ ] 8-10 contract tests added for package boundaries
- [ ] 6-8 e2e tests added for user journeys
- [ ] All new tests pass
- [ ] Coverage ≥ 82%
- [ ] No regressions in existing tests

---

### Phase 5: DOCUMENT - Prevent Future Regressions (HIGH)

**Timeline**: 1-2 hours
**Verification Gate**: Documentation complete, pre-commit hooks working, migration guide tested

#### FR-5.1: Create Pre-commit Hooks
- **Description**: Automated validation to prevent import path errors, misclassification, marker bloat
- **Implementation**:
  1. **Create `.pre-commit-config.yaml`**:
     ```yaml
     repos:
       - repo: local
         hooks:
           - id: validate-imports
             name: Validate import paths
             entry: scripts/validate_imports.py
             language: python
             files: \.(py)$

           - id: validate-test-classification
             name: Validate test classification
             entry: scripts/validate_test_classification.py
             language: python
             files: ^tests/.*\.py$

           - id: validate-marker-usage
             name: Validate marker usage
             entry: scripts/validate_marker_usage.py
             language: python
             files: ^tests/.*\.py$
     ```
  2. **Create Validation Scripts**:
     - `scripts/validate_imports.py`: Detect old `aurora.*` import patterns
     - `scripts/validate_test_classification.py`: Detect integration/e2e tests in unit/
     - `scripts/validate_marker_usage.py`: Detect redundant markers
  3. **Install Hooks**: `pre-commit install`
  4. **Test Hooks**: Intentionally create violations, verify hooks catch them
- **Validation Logic**:

  **validate_imports.py**:
  ```python
  # Detect old import patterns
  if re.search(r'from aurora\.', file_content):
      print(f"ERROR: Old import pattern detected in {filepath}")
      print("  Use 'aurora_memory' not 'aurora.memory'")
      sys.exit(1)
  ```

  **validate_test_classification.py**:
  ```python
  # Detect integration tests in unit/
  if filepath.startswith("tests/unit/"):
      if "subprocess" in file_content or "SQLiteStore(" in file_content:
          print(f"ERROR: Integration test in unit/ directory: {filepath}")
          print("  Move to tests/integration/")
          sys.exit(1)
  ```

  **validate_marker_usage.py**:
  ```python
  # Detect redundant markers
  if filepath.startswith("tests/unit/") and "@pytest.mark.unit" in file_content:
      print(f"ERROR: Redundant marker in {filepath}")
      print("  Remove @pytest.mark.unit (directory already indicates unit test)")
      sys.exit(1)
  ```

- **Acceptance Criteria**:
  - Pre-commit hooks installed and active
  - Hooks run in <2s total
  - Hooks provide actionable error messages
  - Hooks tested with intentional violations (all caught correctly)
  - Hooks documented in CONTRIBUTING.md (if exists) or TESTING.md

#### FR-5.2: Create Migration Checklist
- **Description**: Step-by-step guide for future refactorings to prevent similar breakage
- **Implementation**:
  - Create `docs/TEST_MIGRATION_CHECKLIST.md`
  - Document lessons learned from this migration
  - Provide checklist for future refactorings
- **Checklist Contents**:
  ```markdown
  # Test Migration Checklist

  Use this checklist when performing module refactorings that may affect test imports.

  ## Before Refactoring
  - [ ] Document current import patterns (baseline)
  - [ ] Identify all test files importing from affected modules
  - [ ] Create migration branch
  - [ ] Ensure CI is green

  ## During Refactoring
  - [ ] Update production code first
  - [ ] Run automated import migration script (dry-run mode)
  - [ ] Review proposed changes
  - [ ] Apply import migration
  - [ ] Run `pytest --collect-only` (verify 0 errors)
  - [ ] Run full test suite (verify 0 new failures)
  - [ ] Check coverage (verify no drops)

  ## After Refactoring
  - [ ] Update TESTING.md with new import patterns
  - [ ] Update pre-commit hooks if needed
  - [ ] Document any manual fixes required
  - [ ] Create PR with clear migration notes

  ## Rollback Plan
  - [ ] Migration script creates backup branch
  - [ ] Git commits are granular (easy to revert)
  - [ ] Rollback documented and tested
  ```
- **Acceptance Criteria**:
  - Checklist covers all steps from this migration
  - Checklist tested by walking through it with this migration as example
  - Checklist reviewed and approved
  - Checklist referenced in TESTING.md

#### FR-5.3: Update TESTING.md
- **Description**: Comprehensive update with new patterns, criteria, and lessons learned
- **Implementation**:
  - Add section: "Import Patterns" (correct patterns for aurora_* packages)
  - Add section: "Test Classification Criteria" (unit/integration/e2e decision tree)
  - Add section: "Marker Usage Guidelines" (when to use ml, slow, real_api)
  - Add section: "Migration Lessons Learned" (what went wrong, how we fixed it)
  - Update test pyramid diagram
  - Update coverage reporting section
- **New Sections**:

  **Import Patterns**:
  ```markdown
  ## Import Patterns

  Aurora uses a package-based structure. Always import from top-level packages:

  ✅ Correct:
  - `from aurora_memory import MemoryStore`
  - `from aurora_planning.schemas import Plan`
  - `import aurora_cli.commands as commands`

  ❌ Incorrect (old pattern, will fail):
  - `from aurora.memory import MemoryStore`
  - `from aurora.planning.schemas import Plan`
  - `import aurora.cli.commands as commands`

  The pre-commit hook will catch old patterns and prevent commits.
  ```

  **Test Classification Criteria**:
  ```markdown
  ## Test Classification Criteria

  Use this decision tree to classify tests:

  1. Does the test use subprocess, real file I/O, or real database?
     - Yes → Integration or E2E (see step 2)
     - No → Unit test (place in tests/unit/)

  2. Does the test cover a complete user workflow (multiple commands)?
     - Yes → E2E test (place in tests/e2e/)
     - No → Integration test (place in tests/integration/)

  Examples:
  - Test pure function with mock dependencies → Unit
  - Test CLI command using subprocess → Integration
  - Test init → learn → search → query workflow → E2E
  ```

  **Marker Usage Guidelines**:
  ```markdown
  ## Marker Usage Guidelines

  Aurora uses 3 markers for special cases:

  - `@pytest.mark.ml`: Tests requiring ML dependencies (torch, transformers)
    - Use when: Test imports torch/transformers and fails without them
    - Don't use when: Test uses ML features but doesn't require deps

  - `@pytest.mark.slow`: Tests with runtime >5s
    - Use when: Test takes >5s and should be tracked for optimization
    - Don't use when: Test is slow due to bug (fix the bug instead)

  - `@pytest.mark.real_api`: Tests calling external APIs
    - Use when: Test makes HTTP requests to real external services
    - Don't use when: Test uses mocked API responses

  DO NOT use markers for test type (unit/integration/e2e) - directory structure conveys this.
  ```

- **Acceptance Criteria**:
  - TESTING.md updated with all new sections
  - Existing sections updated for accuracy
  - Test pyramid diagram updated (60/30/10)
  - Document reviewed and approved

#### FR-5.4: Root Cause Analysis Document
- **Description**: Capture what went wrong, why, and how to prevent it
- **Implementation**:
  - Create `docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md`
  - Document timeline of events
  - Document root causes (not just symptoms)
  - Document prevention strategies
  - Document lessons learned
- **Document Structure**:
  ```markdown
  # Root Cause Analysis: Testing Infrastructure Breakage (Dec 2025)

  ## Timeline
  - Dec 2025: PRD-0009 completed, 81.93% coverage achieved
  - Dec 30, 2025: Module refactoring (aurora.* → aurora_*)
  - Dec 30, 2025: CI starts failing (20 consecutive failures)
  - Jan 6, 2026: Root cause analysis initiated

  ## Symptoms
  - 73 test files unable to load
  - Coverage unmeasurable
  - Test pyramid inverted (80/16/4)

  ## Root Causes
  1. **Import Path Breakage**
     - What: Automated refactoring missed test files
     - Why: No validation step in refactoring process
     - Why no catch: CI already in failing state, no pre-commit hooks

  2. **Test Misclassification**
     - What: Tests in wrong directories despite correct behavior
     - Why: No enforcement of classification criteria
     - Why it persists: Organic growth without systematic audits

  3. **Marker Bloat**
     - What: 14 markers defined, only 1 used
     - Why: Over-engineering during initial setup
     - Why it persists: No one questioned the value

  ## Prevention Strategies (Implemented)
  - Pre-commit hooks for import validation
  - Pre-commit hooks for test classification
  - Migration checklist for refactorings
  - Parallel CI during transitions
  - Per-phase verification gates

  ## Lessons Learned
  1. Quality improvements without regression prevention are fragile
  2. Automation must include validation steps
  3. Pre-commit hooks catch issues before CI
  4. Test classification requires enforcement, not just documentation
  5. Markers should be minimal and purposeful

  ## Recommendations
  - Run test classification audit quarterly
  - Review marker usage quarterly
  - Update migration checklist as we learn
  - Consider test metadata validation in CI (belt and suspenders)
  ```
- **Acceptance Criteria**:
  - Root cause analysis document created
  - Document captures timeline, causes, prevention, lessons
  - Document reviewed and approved
  - Document referenced in TESTING.md

#### FR-5.5: Parallel CI Switchover Plan
- **Description**: Document how to switch from legacy CI to new CI
- **Implementation**:
  - Create `docs/CI_SWITCHOVER_PLAN.md`
  - Document current state (legacy + new running in parallel)
  - Document switchover steps
  - Document rollback procedure
  - Document success criteria
- **Switchover Steps**:
  ```markdown
  # CI Switchover Plan

  ## Current State
  - Legacy CI: `.github/workflows/testing-infrastructure-legacy.yml` (failing)
  - New CI: `.github/workflows/testing-infrastructure-new.yml` (passing)
  - Both running in parallel for verification

  ## Switchover Criteria (all must be met)
  - [ ] New CI passes on all Python versions (3.10, 3.11, 3.12, 3.13)
  - [ ] New CI has been passing consistently for 7+ days
  - [ ] Coverage reports match or exceed legacy CI baseline
  - [ ] No known issues with new CI configuration
  - [ ] Stakeholder approval obtained

  ## Switchover Steps
  1. Verify all switchover criteria met
  2. Rename legacy CI: `testing-infrastructure-legacy.yml` → `testing-infrastructure-legacy.yml.disabled`
  3. Rename new CI: `testing-infrastructure-new.yml` → `testing-infrastructure.yml`
  4. Update branch protection rules to require new CI
  5. Monitor for 24 hours, verify all PRs use new CI
  6. If successful, delete legacy CI file after 30 days

  ## Rollback Procedure
  If issues discovered after switchover:
  1. Rename files back: `testing-infrastructure.yml` → `testing-infrastructure-new.yml`
  2. Re-enable legacy: `testing-infrastructure-legacy.yml.disabled` → `testing-infrastructure-legacy.yml`
  3. Update branch protection rules
  4. Investigate issue, fix in new CI
  5. Retry switchover when ready

  ## Success Criteria
  - All PRs use new CI exclusively
  - CI passes consistently
  - No increase in false positives/negatives
  - Team confidence in new CI
  ```
- **Acceptance Criteria**:
  - Switchover plan documented
  - Switchover criteria clear and measurable
  - Rollback procedure tested (dry-run)
  - Plan reviewed and approved

**Rollback Plan (Phase 5)**:
- Documentation changes are low-risk (can update at any time)
- Pre-commit hooks can be disabled if causing issues: `pre-commit uninstall`
- Parallel CI ensures no downtime during migration
- Can delay switchover if issues found

**Verification Checklist (Phase 5)**:
- [ ] Pre-commit hooks installed and working
- [ ] Pre-commit hooks tested with intentional violations
- [ ] TEST_MIGRATION_CHECKLIST.md created and tested
- [ ] TESTING.md updated with new patterns and criteria
- [ ] Root cause analysis document created
- [ ] CI switchover plan documented
- [ ] All documentation reviewed and approved

---

## Technical Approach

### Phase 1: Import Migration Strategy

**Automated AST-Based Migration**:
```python
# scripts/migrate_imports.py

import ast
import sys
from pathlib import Path
from typing import List, Tuple

class ImportRewriter(ast.NodeTransformer):
    """Rewrite old aurora.* imports to new aurora_* imports."""

    MAPPING = {
        "aurora.memory": "aurora_memory",
        "aurora.planning": "aurora_planning",
        "aurora.cli": "aurora_cli",
    }

    def __init__(self):
        self.changes = []

    def visit_Import(self, node):
        """Rewrite: import aurora.memory → import aurora_memory"""
        for alias in node.names:
            for old, new in self.MAPPING.items():
                if alias.name.startswith(old):
                    old_name = alias.name
                    new_name = alias.name.replace(old, new)
                    alias.name = new_name
                    self.changes.append((node.lineno, old_name, new_name))
        return node

    def visit_ImportFrom(self, node):
        """Rewrite: from aurora.memory import X → from aurora_memory import X"""
        if node.module:
            for old, new in self.MAPPING.items():
                if node.module.startswith(old):
                    old_module = node.module
                    new_module = node.module.replace(old, new)
                    node.module = new_module
                    self.changes.append((node.lineno, old_module, new_module))
        return node

def migrate_file(filepath: Path, dry_run: bool = True) -> List[Tuple[int, str, str]]:
    """Migrate imports in a single file."""
    source = filepath.read_text()
    tree = ast.parse(source)

    rewriter = ImportRewriter()
    new_tree = rewriter.visit(tree)

    if not dry_run and rewriter.changes:
        new_source = ast.unparse(new_tree)
        filepath.write_text(new_source)

    return rewriter.changes

def main(dry_run: bool = True):
    """Migrate all test files."""
    test_dir = Path("tests")
    all_changes = {}

    for test_file in test_dir.rglob("test_*.py"):
        changes = migrate_file(test_file, dry_run=dry_run)
        if changes:
            all_changes[test_file] = changes

    # Print report
    print(f"{'DRY RUN - ' if dry_run else ''}Import Migration Report")
    print("=" * 80)
    for filepath, changes in all_changes.items():
        print(f"\n{filepath}:")
        for lineno, old, new in changes:
            print(f"  Line {lineno}: {old} → {new}")

    print(f"\nTotal files affected: {len(all_changes)}")
    print(f"Total changes: {sum(len(c) for c in all_changes.values())}")

    if dry_run:
        print("\nRun with --apply to apply changes")
    else:
        print("\nChanges applied successfully")

if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv
    main(dry_run=dry_run)
```

**Usage**:
```bash
# Dry-run (see changes without applying)
python scripts/migrate_imports.py

# Review output, then apply
python scripts/migrate_imports.py --apply

# Verify
pytest --collect-only
```

### Phase 2: Test Dependency Analysis

**Dependency Graph Generation**:
```python
# scripts/analyze_test_dependencies.py

import ast
from pathlib import Path
from typing import Dict, Set
import json

def extract_imports(filepath: Path) -> Set[str]:
    """Extract all import statements from a test file."""
    source = filepath.read_text()
    tree = ast.parse(source)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports

def build_dependency_graph(test_dir: Path) -> Dict[str, Set[str]]:
    """Build dependency graph for all test files."""
    graph = {}

    for test_file in test_dir.rglob("test_*.py"):
        imports = extract_imports(test_file)
        # Only track dependencies on other test files
        test_deps = {imp for imp in imports if "test_" in imp or imp.startswith("tests.")}
        graph[str(test_file.relative_to(test_dir))] = test_deps

    return graph

def find_move_order(graph: Dict[str, Set[str]], files_to_move: Set[str]) -> List[List[str]]:
    """Determine order to move files (dependencies first)."""
    # Simplified topological sort
    batches = []
    remaining = set(files_to_move)

    while remaining:
        # Find files with no dependencies on remaining files
        batch = {f for f in remaining if not (graph.get(f, set()) & remaining)}
        if not batch:
            # Circular dependency, move all remaining together
            batch = remaining
        batches.append(sorted(batch))
        remaining -= batch

    return batches

def main():
    test_dir = Path("tests")
    graph = build_dependency_graph(test_dir)

    # Example: files to move from unit/ to integration/
    files_to_move = {
        "unit/test_cli_search.py",  # Uses subprocess
        "unit/test_memory_store.py",  # Uses SQLiteStore
        # ... (identified during FR-2.3)
    }

    batches = find_move_order(graph, files_to_move)

    # Output migration plan
    print("Test Migration Plan")
    print("=" * 80)
    for i, batch in enumerate(batches, 1):
        print(f"\nBatch {i}:")
        for filepath in batch:
            print(f"  - {filepath}")
            deps = graph.get(filepath, set())
            if deps:
                print(f"    Dependencies: {', '.join(deps)}")

    # Save for later use
    with open("test-migration-plan.json", "w") as f:
        json.dump({"batches": batches, "graph": {k: list(v) for k, v in graph.items()}}, f, indent=2)

if __name__ == "__main__":
    main()
```

### Phase 3: Marker Cleanup Strategy

**Redundant Marker Detection**:
```python
# scripts/validate_marker_usage.py

import ast
import sys
from pathlib import Path

REDUNDANT_MARKERS = {
    "tests/unit/": ["unit"],
    "tests/integration/": ["integration"],
    "tests/e2e/": ["e2e"],
}

def detect_redundant_markers(filepath: Path) -> List[str]:
    """Detect redundant markers in a test file."""
    source = filepath.read_text()
    tree = ast.parse(source)

    redundant = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and
                node.func.attr == "mark" and
                isinstance(node.func.value, ast.Attribute) and
                node.func.value.attr == "pytest"):

                # Found @pytest.mark.X
                if node.args and isinstance(node.args[0], ast.Name):
                    marker = node.args[0].id

                    # Check if redundant based on directory
                    for directory, markers in REDUNDANT_MARKERS.items():
                        if str(filepath).startswith(directory) and marker in markers:
                            redundant.append((node.lineno, marker))

    return redundant

def main():
    test_dir = Path("tests")
    issues = {}

    for test_file in test_dir.rglob("test_*.py"):
        redundant = detect_redundant_markers(test_file)
        if redundant:
            issues[test_file] = redundant

    if issues:
        print("Redundant Marker Report")
        print("=" * 80)
        for filepath, markers in issues.items():
            print(f"\n{filepath}:")
            for lineno, marker in markers:
                print(f"  Line {lineno}: @pytest.mark.{marker} (redundant with directory)")

        print(f"\nTotal files with issues: {len(issues)}")
        sys.exit(1)
    else:
        print("No redundant markers found")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### Pre-commit Hook Integration

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: local
    hooks:
      - id: validate-imports
        name: Validate import paths (no aurora.*)
        entry: python scripts/validate_imports.py
        language: python
        files: \.py$
        pass_filenames: true

      - id: validate-test-classification
        name: Validate test classification (no integration in unit/)
        entry: python scripts/validate_test_classification.py
        language: python
        files: ^tests/.*\.py$
        pass_filenames: true

      - id: validate-marker-usage
        name: Validate marker usage (no redundant markers)
        entry: python scripts/validate_marker_usage.py
        language: python
        files: ^tests/.*\.py$

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

**Installation**:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Test on all files
```

---

## Risk Assessment & Mitigation

### High Risks

**Risk 1: Import migration breaks tests in unexpected ways**
- **Likelihood**: Medium
- **Impact**: High (entire test suite broken)
- **Mitigation**:
  - Dry-run mode with human review before applying
  - AST-based migration (more reliable than regex)
  - Verification step: `pytest --collect-only` after migration
  - Backup branch created before changes
  - Per-file commits (easy to revert specific changes)

**Risk 2: Moving tests breaks dependencies**
- **Likelihood**: Medium
- **Impact**: Medium (some tests fail)
- **Mitigation**:
  - Dependency analysis before moving (FR-2.1)
  - Move in dependency order (dependencies first)
  - Batch-by-batch verification (run tests after each batch)
  - Git commits per batch (easy to identify and revert problematic batch)

**Risk 3: Pre-commit hooks are too slow, developers disable them**
- **Likelihood**: Low (hooks designed to be fast)
- **Impact**: Medium (loss of regression prevention)
- **Mitigation**:
  - Design hooks to run in <2s total
  - Use fast detection heuristics (regex, not full AST parsing)
  - Allow bypass for emergencies: `git commit --no-verify`
  - Monitor hook performance, optimize if needed

### Medium Risks

**Risk 4: Coverage drops during migration due to test reclassification**
- **Likelihood**: Medium
- **Impact**: Low (temporary, not real coverage loss)
- **Mitigation**:
  - Track coverage delta, not absolute coverage
  - Document expected fluctuations
  - Verify coverage after all phases complete
  - Use baseline from PRD-0009 (81.93%) as reference

**Risk 5: Phase 4 (optional tests) takes longer than estimated**
- **Likelihood**: High (adding tests is time-consuming)
- **Impact**: Low (phase is optional)
- **Mitigation**:
  - Phase 4 is explicitly optional
  - Risk-based prioritization (highest risk first)
  - Can skip Phase 4 entirely if timeline constraints
  - Can add tests incrementally over time

**Risk 6: Documentation becomes outdated again**
- **Likelihood**: Medium (organic drift over time)
- **Impact**: Medium (future confusion)
- **Mitigation**:
  - Pre-commit hooks enforce documented patterns
  - Quarterly audits scheduled (calendar reminder)
  - Migration checklist ensures docs updated during refactorings
  - Root cause analysis captures institutional knowledge

### Low Risks

**Risk 7: New CI has different behavior than legacy CI**
- **Likelihood**: Low (both use same pytest commands)
- **Impact**: Low (caught during parallel testing)
- **Mitigation**:
  - Parallel CI runs both configurations
  - Verify outputs match before switchover
  - 7-day stabilization period before switchover
  - Rollback plan if issues discovered

**Risk 8: Marker reduction causes confusion**
- **Likelihood**: Low (markers are low-use currently)
- **Impact**: Low (documentation clarifies)
- **Mitigation**:
  - Document rationale for 3-marker strategy
  - Update TESTING.md with clear guidelines
  - Pre-commit hooks prevent misuse
  - Can add markers back if needed (unlikely)

---

## Testing & Validation Strategy

### Meta-Testing: Testing the Tests

**Philosophy**: We are changing the test infrastructure itself. How do we verify the changes are correct? Answer: Meta-testing.

#### Phase 1 Validation

**Test Collection Validation**:
```bash
# Before migration
pytest --collect-only 2>&1 | tee collection-before.log
# Expected: 73 errors

# After migration
pytest --collect-only 2>&1 | tee collection-after.log
# Expected: 0 errors

# Compare
diff collection-before.log collection-after.log
# Should show 73 errors resolved
```

**Coverage Delta Validation**:
```bash
# Baseline (from PRD-0009)
# Coverage: 81.93%

# After Phase 1
pytest --cov=aurora_memory --cov=aurora_planning --cov=aurora_cli --cov-report=term
# Expected: ≥80% (allowing for minor regression)

# Track delta
echo "Baseline: 81.93%, Current: <actual>%, Delta: <difference>%"
```

**Import Pattern Validation**:
```bash
# Verify no old patterns remain
grep -r "from aurora\." tests/
# Expected: no matches

# Verify new patterns used
grep -r "from aurora_" tests/ | wc -l
# Expected: >0 matches
```

#### Phase 2 Validation

**Test Count Validation**:
```bash
# Before reclassification
find tests/unit/ -name "test_*.py" | wc -l  # Example: 2000
find tests/integration/ -name "test_*.py" | wc -l  # Example: 400
find tests/e2e/ -name "test_*.py" | wc -l  # Example: 100

# After reclassification
find tests/unit/ -name "test_*.py" | wc -l  # Expected: ~1500 (60%)
find tests/integration/ -name "test_*.py" | wc -l  # Expected: ~750 (30%)
find tests/e2e/ -name "test_*.py" | wc -l  # Expected: ~250 (10%)
```

**Test Pyramid Validation**:
```python
# scripts/validate_test_pyramid.py

def calculate_pyramid():
    unit_count = len(list(Path("tests/unit").rglob("test_*.py")))
    integration_count = len(list(Path("tests/integration").rglob("test_*.py")))
    e2e_count = len(list(Path("tests/e2e").rglob("test_*.py")))

    total = unit_count + integration_count + e2e_count

    unit_pct = (unit_count / total) * 100
    integration_pct = (integration_count / total) * 100
    e2e_pct = (e2e_count / total) * 100

    print(f"Test Pyramid: {unit_pct:.1f}% / {integration_pct:.1f}% / {e2e_pct:.1f}%")

    # Validate
    assert 55 <= unit_pct <= 65, f"Unit tests should be 60±5%, got {unit_pct:.1f}%"
    assert 25 <= integration_pct <= 35, f"Integration tests should be 30±5%, got {integration_pct:.1f}%"
    assert 5 <= e2e_pct <= 15, f"E2E tests should be 10±5%, got {e2e_pct:.1f}%"

    print("✅ Test pyramid is healthy")
```

**Behavioral Validation**:
```bash
# Verify no new test failures after reclassification
pytest --maxfail=1 -x
# Expected: 0 failures

# Verify subprocess usage only in integration/e2e
grep -r "subprocess" tests/unit/
# Expected: no matches

# Verify SQLiteStore usage only in integration/e2e
grep -r "SQLiteStore" tests/unit/ | grep -v "mock"
# Expected: no matches (or only mocked usage)
```

#### Phase 3 Validation

**Marker Count Validation**:
```bash
# Before marker cleanup
grep -h "^    " pytest.ini | grep ":" | wc -l
# Expected: 14 markers

# After marker cleanup
grep -h "^    " pytest.ini | grep ":" | wc -l
# Expected: 3 markers
```

**Marker Usage Validation**:
```bash
# Verify no redundant markers in test files
python scripts/validate_marker_usage.py
# Expected: exit code 0 (no issues)

# Verify markers used appropriately
grep -r "@pytest.mark.ml" tests/ | wc -l
# Expected: >0 (ML tests exist)

grep -r "@pytest.mark.unit" tests/unit/
# Expected: no matches (redundant)
```

#### Phase 4 Validation

**New Test Validation**:
```bash
# Run only new tests
pytest tests/unit/aurora_memory/test_activation_formulas.py -v
pytest tests/integration/test_memory_store_contract.py -v
pytest tests/e2e/test_init_search_query_journey.py -v

# All should pass
```

**Coverage Validation**:
```bash
# Measure coverage of new test targets
pytest --cov=aurora_memory.activation --cov-report=term
# Expected: 100% coverage

pytest --cov=aurora_memory --cov-report=term | grep "aurora_memory/__init__.py"
# Expected: contract tests cover public APIs
```

#### Phase 5 Validation

**Pre-commit Hook Validation**:
```bash
# Test with intentional violations

# Test 1: Old import pattern
echo "from aurora.memory import MemoryStore" > test_violation.py
git add test_violation.py
git commit -m "test"
# Expected: pre-commit hook fails, commit rejected

# Test 2: Integration test in unit/
echo "import subprocess" > tests/unit/test_violation.py
git add tests/unit/test_violation.py
git commit -m "test"
# Expected: pre-commit hook fails, commit rejected

# Test 3: Redundant marker
echo "@pytest.mark.unit" > tests/unit/test_violation.py
git add tests/unit/test_violation.py
git commit -m "test"
# Expected: pre-commit hook fails, commit rejected

# Cleanup
git reset --hard HEAD
```

**Documentation Validation**:
```bash
# Verify links in TESTING.md are valid
markdown-link-check docs/TESTING.md

# Verify migration checklist is complete
# (Manual review: walk through checklist with this migration as test case)

# Verify root cause analysis is accurate
# (Manual review: stakeholder approval)
```

---

## Rollback Plan

### Per-Phase Rollback Strategy

**Philosophy**: Each phase is independently reversible without losing work from previous phases.

#### Phase 1 Rollback

**Scenario**: Import migration breaks tests in unexpected ways

**Steps**:
1. Identify problematic changes (which files/imports)
2. Revert specific commits:
   ```bash
   git log --oneline --grep="Phase 1"
   git revert <commit-hash>  # Revert specific commit
   ```
3. Or revert to backup branch:
   ```bash
   git checkout phase1-backup
   git branch -D main
   git checkout -b main
   ```
4. Fix issues manually or adjust migration script
5. Retry migration

**Backup Strategy**:
- Migration script creates `phase1-backup` branch before changes
- Each logical change is a separate commit (module creation, import migration, CI update)
- Original test files backed up in `.migration-backup/` directory

#### Phase 2 Rollback

**Scenario**: Test reclassification breaks dependencies

**Steps**:
1. Identify problematic batch (which batch introduced failures)
2. Revert that batch:
   ```bash
   git log --oneline --grep="Phase 2: batch"
   git revert <batch-N-commit-hash>
   ```
3. Tests from that batch remain in original location
4. Fix dependency issues
5. Retry that batch

**Backup Strategy**:
- Each batch is a separate commit
- Batch N can be reverted without affecting batches 1..N-1
- Dependency analysis ensures partial rollback doesn't break tests

#### Phase 3 Rollback

**Scenario**: Marker cleanup causes CI issues

**Steps**:
1. Revert pytest.ini changes:
   ```bash
   git checkout HEAD~1 pytest.ini
   ```
2. Revert CI workflow changes:
   ```bash
   git checkout HEAD~1 .github/workflows/
   ```
3. Keep marker removal from test files (harmless)
4. Investigate issues
5. Retry with adjusted marker strategy

**Backup Strategy**:
- pytest.ini backed up before changes
- CI changes are separate commits from test file changes
- Low risk (markers are metadata, not behavior)

#### Phase 4 Rollback

**Scenario**: New tests are flaky or incorrectly implemented

**Steps**:
1. Identify problematic tests
2. Remove those tests:
   ```bash
   git rm tests/unit/aurora_memory/test_activation_formulas.py
   git commit -m "rollback: remove flaky activation tests"
   ```
3. Keep other new tests (independently useful)
4. Fix flaky tests offline
5. Re-add when fixed

**Backup Strategy**:
- Each test file is independently added (separate commits)
- Can remove individual test files without affecting others
- No production code changes (only test additions)

#### Phase 5 Rollback

**Scenario**: Pre-commit hooks are too slow or have false positives

**Steps**:
1. Disable hooks temporarily:
   ```bash
   pre-commit uninstall
   ```
2. Fix hook issues (performance, false positives)
3. Test hooks on sample files
4. Re-enable when fixed:
   ```bash
   pre-commit install
   ```

**Backup Strategy**:
- Hooks can be disabled without affecting code
- Documentation changes are low-risk (can update at any time)
- CI switchover has separate rollback plan (see FR-5.5)

### Full Rollback (Nuclear Option)

**Scenario**: Migration is fundamentally flawed, need to start over

**Steps**:
1. Revert all commits since start of migration:
   ```bash
   git log --oneline --since="2026-01-06"  # Migration start date
   git revert <first-migration-commit>^..<last-migration-commit>
   ```
2. Or hard reset to pre-migration state:
   ```bash
   git reset --hard <commit-before-migration>
   git push --force-with-lease
   ```
3. Return to planning phase, adjust approach
4. Retry migration with lessons learned

**When to Use**:
- Multiple phases have critical issues
- Approach is fundamentally wrong
- Need to redesign strategy

**Risk**: Lose all work from migration. Should be last resort.

---

## Documentation Requirements

### Documents to Create

1. **TEST_MIGRATION_CHECKLIST.md** (FR-5.2)
   - Audience: Future developers performing refactorings
   - Purpose: Prevent similar import breakage
   - Location: `docs/TEST_MIGRATION_CHECKLIST.md`
   - Review: Stakeholder approval required

2. **ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md** (FR-5.4)
   - Audience: All developers, institutional knowledge
   - Purpose: Learn from mistakes, prevent recurrence
   - Location: `docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md`
   - Review: Stakeholder approval required

3. **CI_SWITCHOVER_PLAN.md** (FR-5.5)
   - Audience: Operator performing switchover
   - Purpose: Safe transition from legacy to new CI
   - Location: `docs/CI_SWITCHOVER_PLAN.md`
   - Review: Stakeholder approval required

### Documents to Update

1. **TESTING.md** (FR-5.3)
   - Add: Import Patterns section
   - Add: Test Classification Criteria section
   - Add: Marker Usage Guidelines section
   - Add: Migration Lessons Learned section
   - Update: Test pyramid diagram (60/30/10)
   - Update: Coverage reporting section
   - Review: Stakeholder approval required

2. **pytest.ini** (FR-3.3)
   - Update: Reduce from 14 markers to 3
   - Update: Add clear descriptions for each marker
   - Review: Automated validation (hooks)

3. **.pre-commit-config.yaml** (FR-5.1)
   - Create: New file with 3 validation hooks
   - Review: Tested with intentional violations

4. **README.md** (if exists)
   - Update: Testing section to reference TESTING.md
   - Update: CI status badge (point to new CI workflow)
   - Review: Stakeholder approval required

### Documentation Standards

**Formatting**:
- Use markdown for all documentation
- Include table of contents for docs >2 pages
- Use code blocks with syntax highlighting
- Include examples liberally

**Versioning**:
- Date all documents (created/updated)
- Track major revisions in git history
- Reference specific PRD/phase when applicable

**Accessibility**:
- Write for multiple audiences (solo dev, future contributors, open source community)
- Avoid jargon, or define when necessary
- Provide both "what" and "why" (not just instructions)

**Maintenance**:
- Review quarterly (calendar reminder)
- Update during refactorings (migration checklist enforces this)
- Archive outdated docs (move to `docs/archive/` with date)

---

## Success Criteria (Comprehensive)

### Phase 1 Success Criteria

**Technical**:
- [ ] `pytest --collect-only` completes with 0 errors
- [ ] All 73 previously broken test files successfully import
- [ ] `aurora_planning.configurators.base` module exists and is functional
- [ ] CI passes on Python 3.10, 3.11, 3.12, 3.13
- [ ] Coverage report generated showing ≥80%
- [ ] Migration script available with dry-run mode

**Process**:
- [ ] Migration script tested with dry-run
- [ ] Changes reviewed and approved before applying
- [ ] All changes committed with clear messages
- [ ] Backup branch created
- [ ] Verification checklist completed

**Documentation**:
- [ ] Migration script usage documented
- [ ] Changes logged in git history
- [ ] Any manual fixes documented

### Phase 2 Success Criteria

**Technical**:
- [ ] All tests still pass (0 new failures)
- [ ] Test pyramid is 60/30/10 ± 5%
- [ ] No integration tests remain in `tests/unit/`
- [ ] No e2e tests remain in `tests/unit/` or `tests/integration/`
- [ ] No subprocess usage in `tests/unit/` (except mocked)
- [ ] No SQLiteStore usage in `tests/unit/` (except mocked)

**Process**:
- [ ] Dependency analysis completed
- [ ] Migration plan generated and approved
- [ ] Tests moved in dependency order
- [ ] Each batch verified before next batch
- [ ] All batches committed separately

**Documentation**:
- [ ] Test classification criteria documented in TESTING.md
- [ ] Migration batches documented in git history
- [ ] Test pyramid visualization updated

### Phase 3 Success Criteria

**Technical**:
- [ ] pytest.ini contains exactly 3 markers
- [ ] All tests still pass
- [ ] CI updated to use new marker strategy
- [ ] No redundant markers in test files (`@pytest.mark.unit` in `tests/unit/`)
- [ ] Marker validation hook working

**Process**:
- [ ] Marker usage audit completed
- [ ] Unused markers removed from pytest.ini
- [ ] Redundant markers removed from test files
- [ ] CI tested with new marker configuration

**Documentation**:
- [ ] Marker philosophy documented in TESTING.md
- [ ] Marker usage guidelines provided
- [ ] Decision rationale captured

### Phase 4 Success Criteria (Optional)

**Technical**:
- [ ] Risk assessment completed
- [ ] 15-20 pure unit tests added for core algorithms
- [ ] 8-10 contract tests added for package boundaries
- [ ] 6-8 e2e tests added for user journeys
- [ ] All new tests pass
- [ ] Coverage ≥ 82%
- [ ] No regressions in existing tests

**Process**:
- [ ] Risk profile generated
- [ ] Highest-risk areas prioritized
- [ ] Tests added incrementally
- [ ] Each test file verified independently

**Documentation**:
- [ ] Risk profile documented
- [ ] Test rationale captured (why these tests)

### Phase 5 Success Criteria

**Technical**:
- [ ] Pre-commit hooks installed and working
- [ ] Pre-commit hooks run in <2s
- [ ] Pre-commit hooks tested with intentional violations (all caught)
- [ ] Parallel CI running successfully
- [ ] CI switchover plan ready to execute

**Process**:
- [ ] Pre-commit hooks tested thoroughly
- [ ] Documentation reviewed and approved
- [ ] CI switchover criteria defined
- [ ] Rollback procedures tested (dry-run)

**Documentation**:
- [ ] TEST_MIGRATION_CHECKLIST.md created
- [ ] TESTING.md updated comprehensively
- [ ] ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md created
- [ ] CI_SWITCHOVER_PLAN.md created
- [ ] All documentation reviewed and approved

### Overall Success Criteria

**Quantitative**:
- [ ] CI: 0 failures across Python 3.10-3.13
- [ ] Test collection: 0 errors
- [ ] Test pyramid: 60/30/10 ± 5%
- [ ] Markers: 3 defined, 100% used appropriately
- [ ] Coverage: ≥82% measured
- [ ] Test count: 2,550+ (2,482 baseline + ~68 new)
- [ ] Pre-commit hook pass rate: 100% on valid commits

**Qualitative**:
- [ ] Tests are easy to find and understand
- [ ] Test classification is clear and enforced
- [ ] Marker usage is purposeful, not boilerplate
- [ ] Coverage measurement is accurate and reliable
- [ ] Documentation is comprehensive and current
- [ ] Migration process is repeatable and documented
- [ ] Team (solo dev) has confidence in test infrastructure

**Sustainability**:
- [ ] Pre-commit hooks prevent regressions
- [ ] Migration checklist ensures safe refactorings
- [ ] Quarterly audits scheduled
- [ ] Root cause analysis captures lessons learned
- [ ] Parallel CI enables safe transitions
- [ ] Rollback plans tested and ready

---

## Timeline & Milestones

### Phase 1: FIX (CRITICAL) - Week 1, Days 1-2

**Day 1 (2 hours)**:
- [ ] Code archaeology: Investigate `aurora_planning.configurators.base` (30 min)
- [ ] Create missing module with proper implementation (30 min)
- [ ] Create import migration script (45 min)
- [ ] Run dry-run, review output (15 min)

**Day 2 (1 hour)**:
- [ ] Apply import migration (15 min)
- [ ] Verify test collection: `pytest --collect-only` (15 min)
- [ ] Restore coverage measurement (15 min)
- [ ] Create new CI workflow, run in parallel (15 min)

**Verification Gate**:
- [ ] All Phase 1 success criteria met
- [ ] Stakeholder approval to proceed to Phase 2

---

### Phase 2: RECLASSIFY (HIGH) - Week 1, Days 3-5

**Day 3 (2 hours)**:
- [ ] Create test dependency analysis script (45 min)
- [ ] Run analysis, generate dependency graph (15 min)
- [ ] Define test classification criteria (30 min)
- [ ] Document criteria in TESTING.md (30 min)

**Day 4 (2 hours)**:
- [ ] Create test classification analysis script (45 min)
- [ ] Run analysis, generate report (15 min)
- [ ] Review report, approve migration plan (30 min)
- [ ] Migrate Batch 1, verify (30 min)

**Day 5 (1 hour)**:
- [ ] Migrate remaining batches, verify each (45 min)
- [ ] Verify test pyramid: run validation script (15 min)

**Verification Gate**:
- [ ] All Phase 2 success criteria met
- [ ] Stakeholder approval to proceed to Phase 3

---

### Phase 3: CLEAN (MEDIUM) - Week 2, Day 1

**Day 6 (1 hour)**:
- [ ] Audit current marker usage (15 min)
- [ ] Update pytest.ini (3 markers) (15 min)
- [ ] Update CI workflows (15 min)
- [ ] Remove redundant markers from test files (15 min)

**Verification Gate**:
- [ ] All Phase 3 success criteria met
- [ ] Stakeholder approval to proceed to Phase 4 (or skip if timeline constraints)

---

### Phase 4: ADD MISSING (OPTIONAL) - Week 2, Days 2-4

**Day 7 (3 hours)**:
- [ ] Create risk assessment script (30 min)
- [ ] Run risk analysis, generate risk profile (30 min)
- [ ] Add pure unit tests for ACT-R formulas (90 min)
- [ ] Verify tests pass, measure coverage (30 min)

**Day 8 (2 hours)**:
- [ ] Add pure unit tests for parsing logic (60 min)
- [ ] Add contract tests for package boundaries (60 min)

**Day 9 (2 hours)**:
- [ ] Add e2e tests for user journeys (90 min)
- [ ] Verify all new tests pass (15 min)
- [ ] Measure final coverage (15 min)

**Verification Gate**:
- [ ] All Phase 4 success criteria met
- [ ] Stakeholder approval to proceed to Phase 5

---

### Phase 5: DOCUMENT (HIGH) - Week 2, Day 5 + Week 3, Day 1

**Day 10 (1 hour)**:
- [ ] Create pre-commit hook validation scripts (30 min)
- [ ] Create `.pre-commit-config.yaml` (15 min)
- [ ] Install hooks, test with intentional violations (15 min)

**Day 11 (1 hour)**:
- [ ] Create TEST_MIGRATION_CHECKLIST.md (20 min)
- [ ] Update TESTING.md comprehensively (30 min)
- [ ] Create ROOT_CAUSE_ANALYSIS document (30 min)
- [ ] Create CI_SWITCHOVER_PLAN.md (20 min)

**Verification Gate**:
- [ ] All Phase 5 success criteria met
- [ ] All documentation reviewed and approved
- [ ] Ready for CI switchover

---

### CI Switchover - Week 3, Day 2

**Day 12 (30 min)**:
- [ ] Verify all switchover criteria met
- [ ] Execute switchover steps
- [ ] Monitor for 24 hours
- [ ] Declare success or rollback

---

### Total Timeline

**Optimistic**: 11 days (if no issues, Phase 4 skipped)
**Realistic**: 14-16 days (some issues, Phase 4 included)
**Pessimistic**: 21 days (significant issues, multiple retries)

**Effort**: 14-19 hours total

---

## Future Considerations

### Beyond This PRD

**Test Infrastructure Enhancements** (Future PRDs):
1. **Mutation Testing**: Use `mutmut` to verify test quality (do tests actually catch bugs?)
2. **Property-Based Testing Expansion**: Use Hypothesis more widely for algorithm tests
3. **Performance Benchmarking**: Track test runtime, optimize slow tests
4. **Flakiness Detection**: Automated detection of non-deterministic tests
5. **Test Impact Analysis**: Only run tests affected by code changes (speed up CI)

**Process Improvements**:
1. **Quarterly Test Audits**: Schedule recurring audits (classification, markers, coverage)
2. **Test Metrics Dashboard**: Visualize test pyramid, coverage, runtime over time
3. **Test Debt Tracking**: Create backlog of missing tests, prioritize by risk
4. **Test Review Guidelines**: Add test review criteria to PR template

**Automation Opportunities**:
1. **Auto-Classification**: ML model to suggest test classification based on code
2. **Auto-Marker Suggestion**: Analyze test code, suggest appropriate markers
3. **Coverage Diff Bot**: Comment on PRs with coverage changes
4. **Test Generation**: Use LLM to generate boilerplate test cases

### Lessons for Future Refactorings

**What Worked**:
- Phased approach with verification gates
- Automated migration scripts with dry-run mode
- Parallel CI during transitions
- Per-phase rollback capability
- Comprehensive documentation

**What to Improve**:
- Earlier investment in pre-commit hooks (prevent issues before they occur)
- More frequent audits (quarterly vs ad-hoc)
- Better integration of test metadata validation in CI (catch issues in CI, not just pre-commit)
- Proactive test gap analysis (don't wait for coverage to break)

**What to Avoid**:
- Automated refactoring without validation steps
- Organic growth of technical debt without periodic cleanup
- Over-engineering (14 markers when 3 suffice)
- Assuming documentation will keep itself updated (needs active maintenance)

---

## Appendix

### A. Test Classification Decision Tree

```
┌─────────────────────────────────────┐
│   Is this a test?                   │
└─────────────┬───────────────────────┘
              │ Yes
              ▼
┌─────────────────────────────────────┐
│   Does it use subprocess?           │
│   Does it use real file I/O?        │
│   Does it use real database?        │
└─────────────┬───────────────────────┘
              │
        ┌─────┴─────┐
        │           │
       Yes          No
        │           │
        ▼           ▼
┌──────────────┐  ┌──────────────┐
│ Integration  │  │ Unit Test    │
│ or E2E       │  │              │
│ (see next)   │  │ Place in:    │
└──────┬───────┘  │ tests/unit/  │
       │          └──────────────┘
       ▼
┌──────────────────────────────────────┐
│  Does it test a complete user        │
│  workflow (multiple commands)?       │
└──────────────┬───────────────────────┘
               │
         ┌─────┴─────┐
         │           │
        Yes          No
         │           │
         ▼           ▼
┌──────────────┐  ┌──────────────┐
│ E2E Test     │  │ Integration  │
│              │  │ Test         │
│ Place in:    │  │              │
│ tests/e2e/   │  │ Place in:    │
│              │  │ tests/       │
│              │  │ integration/ │
└──────────────┘  └──────────────┘
```

### B. Import Pattern Reference

**Correct Patterns** (aurora_*):
```python
# Package imports
from aurora_memory import MemoryStore, SearchResult
from aurora_planning import Plan, Task
from aurora_cli import CommandRegistry

# Module imports
from aurora_memory.store import SQLiteStore
from aurora_planning.schemas import PlanSchema
from aurora_cli.commands.search import SearchCommand

# Subpackage imports
from aurora_planning.configurators.base import BaseConfigurator
```

**Incorrect Patterns** (aurora.*):
```python
# ❌ These will fail
from aurora.memory import MemoryStore
from aurora.planning import Plan
from aurora.cli import CommandRegistry

# ❌ These will also fail
from aurora.memory.store import SQLiteStore
from aurora.planning.schemas import PlanSchema
```

### C. Marker Usage Examples

**@pytest.mark.ml** (requires ML dependencies):
```python
@pytest.mark.ml
def test_embedding_generation():
    """Test that requires torch/transformers installed."""
    from transformers import AutoModel
    model = AutoModel.from_pretrained("bert-base-uncased")
    # ... test logic
```

**@pytest.mark.slow** (runtime >5s):
```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with 10,000 items, takes ~8 seconds."""
    items = generate_large_dataset(10000)
    results = process_all(items)
    assert len(results) == 10000
```

**@pytest.mark.real_api** (calls external services):
```python
@pytest.mark.real_api
def test_github_api_integration():
    """Test that calls real GitHub API (skip in CI)."""
    response = requests.get("https://api.github.com/users/octocat")
    assert response.status_code == 200
```

### D. Coverage Delta Tracking Template

```markdown
# Coverage Delta Report

**Baseline** (PRD-0009, Dec 2025): 81.93%

| Phase | Coverage | Delta | Notes |
|-------|----------|-------|-------|
| Phase 1 (Fix) | 80.5% | -1.43% | Expected due to test collection errors resolved |
| Phase 2 (Reclassify) | 80.8% | +0.3% | Minor fluctuation, tests reorganized |
| Phase 3 (Clean) | 80.8% | 0% | No change (markers are metadata) |
| Phase 4 (Add Missing) | 82.4% | +1.6% | New tests added for core algorithms |
| **Final** | **82.4%** | **+0.47%** | ✅ Target met (≥82%) |

**Coverage by Package**:
- aurora_memory: 85.2% (was 84.1%, +1.1%)
- aurora_planning: 78.9% (was 79.2%, -0.3%)
- aurora_cli: 83.5% (was 82.4%, +1.1%)
```

### E. Pre-commit Hook Error Message Examples

**validate_imports.py**:
```
ERROR: Old import pattern detected in tests/unit/test_memory.py
  Line 5: from aurora.memory import MemoryStore

  Fix: Use 'from aurora_memory import MemoryStore'

  The aurora.* import pattern is deprecated. Aurora now uses
  package-based imports (aurora_memory, aurora_planning, etc.).

  See docs/TESTING.md#import-patterns for details.
```

**validate_test_classification.py**:
```
ERROR: Integration test detected in unit/ directory: tests/unit/test_cli_search.py
  Line 42: subprocess.run(["aur", "search", "test"])

  Fix: Move to tests/integration/

  Tests using subprocess are integration tests and should be in
  tests/integration/ directory, not tests/unit/.

  See docs/TESTING.md#test-classification-criteria for details.
```

**validate_marker_usage.py**:
```
ERROR: Redundant marker in tests/unit/test_activation.py
  Line 10: @pytest.mark.unit

  Fix: Remove the marker

  Tests in tests/unit/ directory are automatically unit tests.
  The @pytest.mark.unit marker is redundant.

  See docs/TESTING.md#marker-usage-guidelines for details.
```

### F. Risk Assessment Template (Phase 4)

```markdown
# Test Risk Assessment

| Module/Function | Complexity | Impact | Coverage | Risk Score | Priority |
|-----------------|------------|--------|----------|------------|----------|
| aurora_memory.activation.calculate_base_level_learning | High (math) | Critical | 60% | 9.6 | 1 |
| aurora_memory.parsing.parse_chunk | Medium | High | 45% | 6.75 | 2 |
| aurora_planning.schemas.validate_plan | Low | High | 80% | 4.0 | 3 |
| aurora_cli.commands.search.execute | Medium | Medium | 70% | 4.2 | 4 |

**Risk Score Calculation**: (Complexity × Impact × (100 - Coverage)) / 100

**Complexity**:
- Low: 1-2 (simple logic, few branches)
- Medium: 3-5 (moderate logic, some branches)
- High: 6-10 (complex logic, many branches, math)

**Impact**:
- Low: 1-2 (UI polish, non-critical features)
- Medium: 3-5 (CLI commands, utilities)
- High: 6-8 (APIs, error handling)
- Critical: 9-10 (core algorithms, data integrity, security)

**Coverage**: Current test coverage percentage

**Priority**: Rank by risk score (highest first)
```

### G. Git Commit Message Templates

**Phase 1 Commits**:
```
feat(tests): create missing aurora_planning.configurators.base module

Resolves production bug where module was referenced but didn't exist.
Implemented based on code archaeology of references throughout codebase.

Part of PRD-0023 Phase 1 (Fix).
```

```
refactor(tests): migrate import paths from aurora.* to aurora_*

Automated migration of 73 test files using AST-based script.
Changes reviewed in dry-run mode before applying.

Before: from aurora.memory import MemoryStore
After: from aurora_memory import MemoryStore

Part of PRD-0023 Phase 1 (Fix).
```

**Phase 2 Commits**:
```
refactor(tests): reclassify batch 1 - move integration tests from unit/

Moved 12 test files from tests/unit/ to tests/integration/ based on
subprocess/SQLiteStore usage. Dependency analysis ensured safe move order.

Files moved:
- test_cli_search.py (uses subprocess)
- test_memory_store.py (uses real SQLiteStore)
- ... (see full list in commit)

Part of PRD-0023 Phase 2 (Reclassify).
```

**Phase 3 Commits**:
```
refactor(tests): reduce pytest markers from 14 to 3

Removed unused markers (unit, integration, e2e, critical, smoke, etc.).
Kept only: ml, slow, real_api (markers for special cases).

Rationale: Directory structure conveys test type, markers should be
for special cases not covered by directory structure.

Part of PRD-0023 Phase 3 (Clean).
```

**Phase 4 Commits**:
```
test(memory): add pure unit tests for ACT-R activation formulas

Added 15 tests covering edge cases: zero references, extreme decay values,
property-based tests for monotonic decrease. Coverage: 60% → 100%.

Part of PRD-0023 Phase 4 (Add Missing).
```

**Phase 5 Commits**:
```
chore(ci): add pre-commit hooks for import and classification validation

Hooks prevent:
- Old aurora.* import patterns
- Integration tests in unit/ directory
- Redundant markers (e.g., @pytest.mark.unit in tests/unit/)

Hooks run in <2s, provide actionable error messages.

Part of PRD-0023 Phase 5 (Document).
```

---

## Glossary

**ACT-R**: Adaptive Control of Thought-Rational, a cognitive architecture used in Aurora for memory activation calculations

**AST**: Abstract Syntax Tree, a tree representation of source code structure used for automated code analysis/transformation

**Base-Level Learning**: ACT-R mechanism for calculating how activation decays over time based on usage history

**Contract Test**: Test that verifies input/output contracts of public APIs (types, shapes, error conditions)

**Coverage Delta**: Relative change in coverage percentage (e.g., +1.5%) rather than absolute coverage (e.g., 82%)

**Dependency Injection (DI)**: Design pattern where dependencies are provided externally rather than created internally

**E2E Test**: End-to-end test that verifies complete user workflows from start to finish

**Integration Test**: Test that verifies multiple components working together, may use real implementations

**Marker Bloat**: Having many defined pytest markers that are rarely or never used

**Meta-Testing**: Testing the test infrastructure itself (e.g., verifying pre-commit hooks catch violations)

**Property-Based Testing**: Testing approach where properties/invariants are verified across many generated inputs (e.g., Hypothesis library)

**Test Pyramid**: Model for test distribution: 60% unit (fast, isolated), 30% integration (medium, some real dependencies), 10% e2e (slow, full stack)

**Unit Test**: Test that verifies a single function/class in isolation with no external dependencies

---

## Sign-off

**PRD Author**: AI Assistant (Claude Sonnet 4.5)
**Stakeholder**: Solo Developer
**Review Date**: 2026-01-06
**Status**: Awaiting Approval

**Approval**:
- [ ] Stakeholder review complete
- [ ] Technical approach validated
- [ ] Timeline realistic
- [ ] Success criteria clear
- [ ] Ready to proceed to implementation

---

**End of PRD-0023**
