# Tasks: PRD-0023 - Aurora Testing Infrastructure Overhaul

**Status**: Phase 1 - High-Level Planning Complete
**Created**: 2026-01-06
**PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0023-prd-testing-infrastructure-overhaul.md`
**Timeline**: 2-3 weeks (phased execution)
**Philosophy**: Long-term sustainable solutions over quick fixes

---

## Overview

This task list implements a comprehensive, methodical overhaul of Aurora's testing infrastructure delivered in 5 independent, verifiable phases. Each phase includes verification gates, rollback procedures, and clear acceptance criteria.

**Critical Requirements**:
- Each phase must be independently deployable
- Verification gate required between phases
- No phase should break existing functionality
- All automation includes dry-run → approve → apply workflow

---

## Parent Tasks

- [ ] 1.0 **PHASE 1 (CRITICAL)**: Restore CI - Fix Import Paths and Missing Modules
  - **Timeline**: 2-3 hours
  - **Priority**: CRITICAL - Blocks all other work
  - **Goal**: Get CI passing on Python 3.10-3.13, all tests collecting, coverage measurable
  - **Verification Gate**: CI green, 0 test collection errors, coverage ≥80%

- [ ] 2.0 **PHASE 2 (HIGH)**: Reclassify Tests - Fix Test Pyramid
  - **Timeline**: 4-5 hours
  - **Priority**: HIGH - Improves test reliability and organization
  - **Goal**: Achieve 60/30/10 test pyramid distribution
  - **Verification Gate**: Test pyramid correct, 0 new failures, all tests still pass

- [ ] 3.0 **PHASE 3 (MEDIUM)**: Clean Marker Bloat - Simplify to 3 Essential Markers
  - **Timeline**: 1 hour
  - **Priority**: MEDIUM - Reduces cognitive overhead
  - **Goal**: Reduce from 14 markers to 3 (ml, slow, real_api)
  - **Verification Gate**: 3 markers defined, 100% used appropriately, tests pass

- [ ] 4.0 **PHASE 4 (OPTIONAL)**: Add Missing Tests - Fill Critical Coverage Gaps
  - **Timeline**: 6-8 hours
  - **Priority**: OPTIONAL but recommended
  - **Goal**: Fill critical test gaps for core algorithms, boundaries, and e2e workflows
  - **Verification Gate**: Coverage ≥82%, critical gaps filled, all tests pass

- [ ] 5.0 **PHASE 5 (HIGH)**: Document and Prevent - Regression Prevention
  - **Timeline**: 1-2 hours
  - **Priority**: HIGH - Prevents future regressions
  - **Goal**: Pre-commit hooks, migration guides, comprehensive documentation
  - **Verification Gate**: Hooks working, documentation complete, switchover plan ready

- [ ] 6.0 **POST-PHASES**: CI Switchover and Final Verification
  - **Timeline**: 1 hour + 7 days monitoring
  - **Priority**: HIGH - Complete the migration
  - **Goal**: Switch from legacy to new CI, verify stability
  - **Verification Gate**: New CI stable for 7+ days, stakeholder approval

---

## Phase Dependencies

```
Phase 1 (Restore CI)
    ↓ [VERIFICATION GATE: CI green, tests collect]
Phase 2 (Reclassify Tests) ← Can run in parallel → Phase 3 (Clean Markers)
    ↓ [VERIFICATION GATE: Pyramid correct, tests pass]
Phase 4 (Add Tests) [OPTIONAL - Can skip if time-constrained]
    ↓ [VERIFICATION GATE: Coverage ≥82%]
Phase 5 (Document & Prevent)
    ↓ [VERIFICATION GATE: Hooks working, docs complete]
Phase 6 (CI Switchover)
    ↓ [VERIFICATION GATE: 7 days stable]
COMPLETE
```

---

## Verification Gates (Required Between Phases)

### Gate 1: After Phase 1
- [ ] `pytest --collect-only` shows 0 errors
- [ ] All 73 previously broken test files now import successfully
- [ ] CI passes on Python 3.10, 3.11, 3.12, 3.13
- [ ] Coverage report generated showing ≥80%
- [ ] Module `aurora_planning.configurators.base` exists and is functional
- [ ] Migration script available with dry-run mode

### Gate 2: After Phase 2
- [ ] All tests still pass (0 new failures)
- [ ] Test pyramid is 60/30/10 ± 5%
- [ ] No integration tests remain in tests/unit/
- [ ] No e2e tests remain in tests/unit/ or tests/integration/
- [ ] Migration performed in batches with per-batch verification

### Gate 3: After Phase 3
- [ ] pytest.ini contains exactly 3 markers (ml, slow, real_api)
- [ ] All tests still pass
- [ ] CI updated to use new marker strategy
- [ ] No redundant markers in test files
- [ ] CI run time reduced or unchanged

### Gate 4: After Phase 4 (if executed)
- [ ] 15-20 pure unit tests added for core algorithms
- [ ] 8-10 contract tests added for package boundaries
- [ ] 6-8 e2e tests added for user journeys
- [ ] Coverage ≥82%
- [ ] No regressions in existing tests

### Gate 5: After Phase 5
- [ ] Pre-commit hooks installed and working
- [ ] Hooks tested with intentional violations (all caught)
- [ ] TEST_MIGRATION_CHECKLIST.md created
- [ ] TESTING.md updated with new patterns
- [ ] Root cause analysis document created
- [ ] CI switchover plan documented

### Gate 6: After CI Switchover
- [ ] New CI passing consistently for 7+ days
- [ ] All PRs using new CI exclusively
- [ ] No increase in false positives/negatives
- [ ] Stakeholder approval obtained
- [ ] Legacy CI disabled or removed

---

## Rollback Procedures

### Phase 1 Rollback
- Migration script creates backup branch before changes
- Git commit per logical change (module creation, import migration, CI update)
- Can revert individual commits
- Backup directory: `.migration-backup/`

### Phase 2 Rollback
- Each batch is separate git commit
- Can revert individual batches
- Dependency analysis ensures partial rollback safe

### Phase 3 Rollback
- Backup pytest.ini before changes
- Git commit per logical change
- No test behavior changes (only organizational)

### Phase 4 Rollback
- Tests added incrementally (commit per test file)
- Can skip entire phase if needed
- No changes to production code

### Phase 5 Rollback
- Pre-commit hooks can be disabled: `pre-commit uninstall`
- Documentation changes are low-risk
- Parallel CI ensures no downtime

### Phase 6 Rollback
- Rename files back to restore legacy CI
- Update branch protection rules
- Documented rollback procedure in CI_SWITCHOVER_PLAN.md

---

## Success Metrics

| Metric | Before | After | Measurement |
|--------|--------|-------|-------------|
| CI Status | 20 consecutive failures | 0 failures | GitHub Actions |
| Test Collection | 73 errors | 0 errors | `pytest --collect-only` |
| Test Pyramid | 80/16/4 (inverted) | 60/30/10 ± 5% | Directory counts |
| Marker Count | 14 defined, ~5% used | 3 defined, 100% used | pytest.ini + grep |
| Coverage | Unmeasurable | 82%+ measured | `pytest --cov` |
| Test Count | ~2,482 (when fixed) | 2,550+ | Pytest summary |
| Pre-commit | N/A | 100% on commit | Hook logs |

---

## Notes

**STOP HERE - Phase 1 Complete**

This is the high-level task breakdown. The next step (Phase 2) will generate detailed sub-tasks for each parent task.

**To proceed**: Review the parent tasks above, then respond with **"Go"** to generate detailed sub-tasks, or request modifications to the high-level plan.

**Key Decision Points Before Sub-Task Generation**:
1. Do you want to execute Phase 4 (Add Missing Tests), or skip it to save 6-8 hours?
2. Should we include property-based testing (Hypothesis) in Phase 4, or stick to traditional unit tests?
3. Do you want the migration to be automated (scripted) or manual (checklist-driven)?

**Estimated Total Timeline**:
- With Phase 4: 15-18 hours of active work + 7 days monitoring
- Without Phase 4: 9-10 hours of active work + 7 days monitoring

---

**Status Update**: Phase 2 complete - Detailed sub-tasks generated below.

---

## Relevant Files

### Phase 1: Import Migration & CI Restoration
- `/home/hamr/PycharmProjects/aurora/scripts/migrate_imports.py` - Existing migration script (needs updating for new patterns)
- `/home/hamr/PycharmProjects/aurora/scripts/validate_imports.py` - NEW: Import validation script for pre-commit
- `/home/hamr/PycharmProjects/aurora/pytest.ini` - Pytest configuration with marker definitions
- `/home/hamr/PycharmProjects/aurora/tests/` - All test files (220 files across unit/, integration/, e2e/)
- `/home/hamr/PycharmProjects/aurora/packages/aurora_planning/configurators/base.py` - NEW: Missing module to create
- `/home/hamr/PycharmProjects/aurora/.github/workflows/testing-infrastructure-new.yml` - NEW: Updated CI workflow

### Phase 2: Test Reclassification
- `/home/hamr/PycharmProjects/aurora/scripts/analyze_test_dependencies.py` - NEW: Dependency analysis script
- `/home/hamr/PycharmProjects/aurora/scripts/classify_tests.py` - NEW: Test classification detection script
- `/home/hamr/PycharmProjects/aurora/scripts/migrate_tests.py` - NEW: Batch test migration script
- `/home/hamr/PycharmProjects/aurora/tests/unit/` - Unit tests directory (currently has misclassified tests)
- `/home/hamr/PycharmProjects/aurora/tests/integration/` - Integration tests directory
- `/home/hamr/PycharmProjects/aurora/tests/e2e/` - E2E tests directory

### Phase 3: Marker Cleanup
- `/home/hamr/PycharmProjects/aurora/scripts/validate_marker_usage.py` - NEW: Marker validation script
- `/home/hamr/PycharmProjects/aurora/scripts/remove_redundant_markers.py` - NEW: Automated marker removal
- `/home/hamr/PycharmProjects/aurora/pytest.ini` - Update marker definitions (14 → 3)
- `/home/hamr/PycharmProjects/aurora/.github/workflows/testing-infrastructure-new.yml` - Update CI marker usage

### Phase 4: Add Missing Tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/aurora_memory/test_activation_formulas.py` - NEW: Core algorithm tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/aurora_memory/test_parsing_logic.py` - NEW: Parsing edge case tests
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_memory_store_contract.py` - NEW: Contract tests
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_planning_contract.py` - NEW: Contract tests
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_cli_contract.py` - NEW: Contract tests
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_full_memory_workflow.py` - NEW: E2E user journey
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_planning_workflow.py` - NEW: E2E user journey
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_mcp_workflow.py` - NEW: E2E user journey

### Phase 5: Documentation & Prevention
- `/home/hamr/PycharmProjects/aurora/.pre-commit-config.yaml` - NEW: Pre-commit hook configuration
- `/home/hamr/PycharmProjects/aurora/scripts/validate_imports.py` - Pre-commit hook script
- `/home/hamr/PycharmProjects/aurora/scripts/validate_test_classification.py` - NEW: Pre-commit hook script
- `/home/hamr/PycharmProjects/aurora/scripts/validate_marker_usage.py` - Pre-commit hook script (reused from Phase 3)
- `/home/hamr/PycharmProjects/aurora/docs/TEST_MIGRATION_CHECKLIST.md` - NEW: Migration guide
- `/home/hamr/PycharmProjects/aurora/docs/TESTING.md` - Update with new patterns and criteria
- `/home/hamr/PycharmProjects/aurora/docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md` - NEW: RCA document
- `/home/hamr/PycharmProjects/aurora/docs/CI_SWITCHOVER_PLAN.md` - NEW: CI migration plan

### Notes

**Testing Framework**: pytest 7.0+ with coverage plugin
**Python Versions**: 3.10, 3.11, 3.12, 3.13
**Current Marker Count**: 14 markers defined in pytest.ini (lines 17-31)
**Current Test Count**: 220 test files across unit/, integration/, e2e/ directories
**Existing Scripts**: migrate_imports.py exists but needs updating for reverse direction (aurora.* → aurora_*)

---

## Tasks

- [ ] 1.0 **PHASE 1 (CRITICAL)**: Restore CI - Fix Import Paths and Missing Modules
  - [x] 1.1 Investigate and create missing `aurora_planning.configurators.base` module
    - **Effort**: 30 minutes
    - **Description**: Search codebase for references to `configurators.base`, determine intended functionality, create proper module with base classes/protocols
    - **Commands**:
      ```bash
      # Search for references
      grep -r "from aurora_planning.configurators.base" /home/hamr/PycharmProjects/aurora/
      grep -r "import aurora_planning.configurators.base" /home/hamr/PycharmProjects/aurora/
      ```
    - **Acceptance**: Module exists at `/home/hamr/PycharmProjects/aurora/packages/aurora_planning/configurators/base.py`, all imports resolve, contains necessary base classes
    - **Rollback**: Delete module if issues found, git revert commit

  - [x] 1.2 Update import migration script for reverse direction (aurora.* → aurora_*)
    - **Effort**: 45 minutes
    - **Description**: Modify existing `/home/hamr/PycharmProjects/aurora/scripts/migrate_imports.py` to handle OLD pattern (aurora.*) → NEW pattern (aurora_*)
    - **Current Mappings**: Script currently maps aurora_core → aurora.core (we need REVERSE)
    - **New Mappings**:
      ```python
      PACKAGE_MAPPINGS = {
          "aurora.memory": "aurora_memory",
          "aurora.planning": "aurora_planning",
          "aurora.cli": "aurora_cli",
          # Add all old → new mappings
      }
      ```
    - **Acceptance**: Script supports --dry-run mode, shows line-by-line diffs, logs all changes
    - **Rollback**: Git revert script changes, original script preserved in git history

  - [x] 1.3 Run import migration in dry-run mode and review changes
    - **Effort**: 20 minutes
    - **Description**: Execute migration script with --dry-run, review all proposed changes, verify correctness
    - **Commands**:
      ```bash
      cd /home/hamr/PycharmProjects/aurora
      python scripts/migrate_imports.py --dry-run --path tests/ > migration-preview.txt
      # Review migration-preview.txt for accuracy
      ```
    - **Acceptance**: All 73 broken test files identified, changes look correct, no false positives
    - **Rollback**: No changes applied yet (dry-run only)

  - [x] 1.4 Create backup and apply import migration
    - **Effort**: 15 minutes
    - **Description**: Create git branch for backup, apply import migration, commit changes
    - **Commands**:
      ```bash
      git checkout -b phase1-import-migration-backup
      git checkout -b phase1-import-migration
      python scripts/migrate_imports.py --path tests/
      git add -A
      git commit -m "fix(tests): migrate import paths from aurora.* to aurora_* packages"
      ```
    - **Acceptance**: All test files updated, git commit created, backup branch exists
    - **Rollback**: `git checkout phase1-import-migration-backup`

  - [x] 1.5 Verify test collection after import migration
    - **Effort**: 10 minutes
    - **Description**: Run pytest collection, verify 0 errors, identify any edge cases missed by automation
    - **Commands**:
      ```bash
      pytest --collect-only 2>&1 | tee test-collection-results.txt
      # Check for collection errors
      grep -i "error" test-collection-results.txt
      ```
    - **Acceptance**: `pytest --collect-only` completes with 0 errors, all ~2,482 tests collect successfully
    - **Rollback**: Fix any edge cases manually, or rollback to backup branch

  - [ ] 1.6 Restore coverage measurement and establish baseline
    - **Effort**: 15 minutes
    - **Description**: Run full test suite with coverage, verify coverage measurable, document baseline
    - **Commands**:
      ```bash
      pytest --cov=packages --cov-report=term-missing --cov-report=html --cov-report=xml
      # Check coverage percentage
      grep "TOTAL" htmlcov/index.html
      ```
    - **Acceptance**: Coverage report generated, coverage ≥80%, baseline documented in commit message
    - **Rollback**: N/A (measurement only, no changes)

  - [x] 1.7 Create new CI workflow file (parallel to legacy)
    - **Effort**: 30 minutes
    - **Description**: Create `.github/workflows/testing-infrastructure-new.yml` that runs in parallel with legacy CI
    - **Template**:
      ```yaml
      name: Testing Infrastructure (New)
      on: [push, pull_request]
      jobs:
        test:
          strategy:
            matrix:
              python-version: ['3.10', '3.11', '3.12', '3.13']
          steps:
            - uses: actions/checkout@v3
            - name: Set up Python
              uses: actions/setup-python@v4
              with:
                python-version: ${{ matrix.python-version }}
            - name: Install dependencies
              run: pip install -e ".[dev]"
            - name: Run tests
              run: pytest --cov=packages --cov-report=xml
            - name: Upload coverage
              uses: codecov/codecov-action@v3
      ```
    - **Acceptance**: New workflow file created, runs on all Python versions, uploads coverage
    - **Rollback**: Delete workflow file

  - [ ] 1.8 Verify new CI passes on all Python versions
    - **Effort**: 15 minutes
    - **Description**: Push changes, monitor CI, verify new workflow passes while legacy may still fail
    - **Commands**:
      ```bash
      git push origin phase1-import-migration
      # Monitor GitHub Actions dashboard
      ```
    - **Acceptance**: New CI workflow passes on Python 3.10-3.13, coverage report uploaded
    - **Rollback**: Fix any CI-specific issues, or disable new workflow temporarily

  - [ ] 1.9 **VERIFICATION GATE 1**: Complete Phase 1 verification checklist
    - **Effort**: 10 minutes
    - **Description**: Verify all Gate 1 criteria met before proceeding to Phase 2
    - **Checklist**: See "Gate 1: After Phase 1" section above
    - **Acceptance**: All 6 Gate 1 criteria checked and verified
    - **Rollback**: If any criteria not met, fix issues before proceeding

- [ ] 2.0 **PHASE 2 (HIGH)**: Reclassify Tests - Fix Test Pyramid
  - [ ] 2.1 Document test classification criteria in TESTING.md
    - **Effort**: 30 minutes
    - **Description**: Create clear, objective criteria for unit/integration/e2e classification with decision tree
    - **Criteria**:
      - **Unit**: Single function/class, DI mocks, no I/O, <1s, deterministic
      - **Integration**: Multiple components, may use subprocess/SQLiteStore, <10s, isolated state
      - **E2E**: Complete workflows, real CLI/DB/files, <60s, cleanup after
    - **Acceptance**: TESTING.md section created with decision tree diagram, 5+ examples per category
    - **Rollback**: Git revert documentation changes

  - [ ] 2.2 Create test dependency analysis script
    - **Effort**: 1 hour
    - **Description**: Build script to analyze test file dependencies and generate migration order
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/analyze_test_dependencies.py`
    - **Features**: Parse imports, build dependency graph, detect circular deps, output move order batches
    - **Acceptance**: Script outputs JSON with batches and dependency graph, identifies circular deps
    - **Rollback**: Delete script (no changes to tests yet)

  - [ ] 2.3 Create test classification detection script
    - **Effort**: 45 minutes
    - **Description**: Build script to detect misclassified tests using heuristics (subprocess, SQLiteStore, docstrings)
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/classify_tests.py`
    - **Heuristics**:
      - Uses `subprocess.run` → integration or e2e
      - Uses `SQLiteStore(` (not mocked) → integration
      - Docstring contains "Integration" → integration
      - Uses `tmp_path` + multi-step workflow → e2e
    - **Acceptance**: Script outputs report: file, current location, proposed location, reason
    - **Rollback**: Delete script

  - [ ] 2.4 Run classification analysis and generate migration report
    - **Effort**: 20 minutes
    - **Description**: Execute classification script, review output, identify all misclassified tests
    - **Commands**:
      ```bash
      python scripts/classify_tests.py > test-classification-report.txt
      # Review report, verify recommendations
      ```
    - **Acceptance**: Report identifies 18+ integration tests in unit/, 15+ e2e tests in unit/, reasons documented
    - **Rollback**: N/A (analysis only)

  - [ ] 2.5 Run dependency analysis for migration batching
    - **Effort**: 15 minutes
    - **Description**: Execute dependency analysis script with list of files to move, generate batch plan
    - **Commands**:
      ```bash
      python scripts/analyze_test_dependencies.py > test-migration-plan.json
      # Review batches, verify dependency order
      ```
    - **Acceptance**: Migration plan with 3-5 batches, dependencies respected, plan saved to JSON
    - **Rollback**: N/A (analysis only)

  - [ ] 2.6 Create batch test migration script
    - **Effort**: 45 minutes
    - **Description**: Build script to migrate tests in batches with verification between each batch
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/migrate_tests.py`
    - **Features**: Read batch plan JSON, move files in order, update imports if needed, run pytest after each batch
    - **Acceptance**: Script supports --batch N flag, verifies tests pass after each batch, logs all moves
    - **Rollback**: Delete script

  - [ ] 2.7 Execute Batch 1 migration and verify
    - **Effort**: 20 minutes
    - **Description**: Move first batch of tests (no dependencies), run full test suite, verify 0 new failures
    - **Commands**:
      ```bash
      python scripts/migrate_tests.py --batch 1
      pytest tests/unit/ tests/integration/ tests/e2e/
      git add -A && git commit -m "refactor(tests): reclassify batch 1 - move tests with no dependencies"
      ```
    - **Acceptance**: Batch 1 tests moved, all tests pass, git commit created
    - **Rollback**: `git revert HEAD`

  - [ ] 2.8 Execute Batch 2 migration and verify
    - **Effort**: 20 minutes
    - **Description**: Move second batch of tests, run full test suite, verify 0 new failures
    - **Commands**: Same as 2.7 but --batch 2
    - **Acceptance**: Batch 2 tests moved, all tests pass, git commit created
    - **Rollback**: `git revert HEAD`

  - [ ] 2.9 Execute remaining batches (3-N) and verify each
    - **Effort**: 20 minutes per batch (estimate 3-5 batches total)
    - **Description**: Continue batch migration until all misclassified tests moved
    - **Commands**: Same as 2.7 but --batch 3, 4, 5, etc.
    - **Acceptance**: All batches complete, all tests pass, git commit per batch
    - **Rollback**: `git revert HEAD` for each batch

  - [ ] 2.10 Verify test pyramid distribution (60/30/10 target)
    - **Effort**: 15 minutes
    - **Description**: Count tests in each directory, calculate percentages, verify pyramid
    - **Commands**:
      ```bash
      find tests/unit -name "test_*.py" | wc -l
      find tests/integration -name "test_*.py" | wc -l
      find tests/e2e -name "test_*.py" | wc -l
      # Calculate percentages
      ```
    - **Acceptance**: Distribution is 60/30/10 ± 5%, documented in commit message
    - **Rollback**: N/A (measurement only)

  - [ ] 2.11 **VERIFICATION GATE 2**: Complete Phase 2 verification checklist
    - **Effort**: 10 minutes
    - **Description**: Verify all Gate 2 criteria met before proceeding to Phase 3
    - **Checklist**: See "Gate 2: After Phase 2" section above
    - **Acceptance**: All 5 Gate 2 criteria checked and verified
    - **Rollback**: Fix any issues before proceeding

- [ ] 3.0 **PHASE 3 (MEDIUM)**: Clean Marker Bloat - Simplify to 3 Essential Markers
  - [ ] 3.1 Audit current marker usage across all test files
    - **Effort**: 15 minutes
    - **Description**: Generate report of marker definitions vs actual usage in test files
    - **Commands**:
      ```bash
      # Extract defined markers from pytest.ini
      grep -A 15 "^markers =" pytest.ini

      # Count usage of each marker
      for marker in unit integration e2e ml slow real_api critical safety cli mcp soar core fast performance; do
        count=$(grep -r "@pytest.mark.$marker" tests/ | wc -l)
        echo "$marker: $count uses"
      done
      ```
    - **Acceptance**: Usage report shows marker name, definition location, usage count, files using each
    - **Rollback**: N/A (analysis only)

  - [ ] 3.2 Create marker cleanup validation script
    - **Effort**: 30 minutes
    - **Description**: Build script to detect redundant markers (unit in unit/, etc.)
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/validate_marker_usage.py`
    - **Detection Logic**:
      - Test in `tests/unit/` with `@pytest.mark.unit` → redundant
      - Test in `tests/integration/` with `@pytest.mark.integration` → redundant
      - Test in `tests/e2e/` with `@pytest.mark.e2e` → redundant
    - **Acceptance**: Script outputs report of redundant markers, supports use as pre-commit hook
    - **Rollback**: Delete script

  - [ ] 3.3 Create automated redundant marker removal script
    - **Effort**: 30 minutes
    - **Description**: Build script to automatically remove redundant markers from test files
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/remove_redundant_markers.py`
    - **Features**: Dry-run mode, AST-based removal, preserve other decorators, log all removals
    - **Acceptance**: Script supports --dry-run, outputs diff, safely removes only redundant markers
    - **Rollback**: Delete script

  - [ ] 3.4 Run redundant marker removal in dry-run mode
    - **Effort**: 10 minutes
    - **Description**: Execute removal script with --dry-run, review proposed changes
    - **Commands**:
      ```bash
      python scripts/remove_redundant_markers.py --dry-run > marker-removal-preview.txt
      # Review changes
      ```
    - **Acceptance**: Dry-run output shows all redundant markers to be removed, no false positives
    - **Rollback**: N/A (dry-run only)

  - [ ] 3.5 Apply redundant marker removal
    - **Effort**: 10 minutes
    - **Description**: Execute removal script to remove redundant markers, commit changes
    - **Commands**:
      ```bash
      python scripts/remove_redundant_markers.py
      pytest tests/  # Verify tests still pass
      git add -A && git commit -m "refactor(tests): remove redundant markers (unit, integration, e2e)"
      ```
    - **Acceptance**: Redundant markers removed, all tests pass, git commit created
    - **Rollback**: `git revert HEAD`

  - [ ] 3.6 Update pytest.ini to keep only 3 essential markers
    - **Effort**: 15 minutes
    - **Description**: Backup pytest.ini, update to keep only ml, slow, real_api markers with clear descriptions
    - **Commands**:
      ```bash
      cp pytest.ini pytest.ini.backup
      # Edit pytest.ini manually or with script
      ```
    - **New Markers Section**:
      ```ini
      markers =
          ml: Tests requiring ML dependencies (torch, transformers) - skip if not installed
          slow: Tests with runtime >5s - tracked for optimization opportunities
          real_api: Tests calling external APIs - skip in CI, run manually for integration verification
      ```
    - **Acceptance**: pytest.ini updated, exactly 3 markers defined, clear descriptions
    - **Rollback**: `cp pytest.ini.backup pytest.ini`

  - [ ] 3.7 Update CI workflow to use new marker strategy
    - **Effort**: 20 minutes
    - **Description**: Update `.github/workflows/testing-infrastructure-new.yml` to skip ml/real_api, report slow tests
    - **Updates**:
      ```yaml
      - name: Run tests (excluding ML and real API)
        run: pytest -m "not ml and not real_api" --cov --cov-report=xml

      - name: Report slow tests
        run: pytest -m "slow" --durations=10
        continue-on-error: true
      ```
    - **Acceptance**: CI updated, skips ml/real_api by default, reports slow tests
    - **Rollback**: Git revert CI changes

  - [ ] 3.8 Verify tests still pass after marker cleanup
    - **Effort**: 10 minutes
    - **Description**: Run full test suite, verify 0 failures, check for unknown marker warnings
    - **Commands**:
      ```bash
      pytest tests/ -v 2>&1 | tee marker-cleanup-verification.txt
      # Check for warnings about unknown markers
      grep -i "unknown marker" marker-cleanup-verification.txt
      ```
    - **Acceptance**: All tests pass, 0 warnings about unknown markers
    - **Rollback**: Fix any issues or rollback changes

  - [ ] 3.9 **VERIFICATION GATE 3**: Complete Phase 3 verification checklist
    - **Effort**: 10 minutes
    - **Description**: Verify all Gate 3 criteria met before proceeding to Phase 4
    - **Checklist**: See "Gate 3: After Phase 3" section above
    - **Acceptance**: All 6 Gate 3 criteria checked and verified
    - **Rollback**: Fix any issues before proceeding

- [ ] 4.0 **PHASE 4 (OPTIONAL)**: Add Missing Tests - Fill Critical Coverage Gaps
  - [ ] 4.1 Conduct risk assessment for untested code areas
    - **Effort**: 45 minutes
    - **Description**: Analyze codebase for high-risk areas lacking tests using complexity, coverage, and impact
    - **Analysis Areas**:
      - Code complexity (cyclomatic complexity)
      - Coverage gaps (uncovered critical code)
      - Historical bugs (past failures)
      - Business impact (core algorithms, data integrity)
    - **Commands**:
      ```bash
      # Check current coverage
      pytest --cov=packages --cov-report=html
      # Review htmlcov/ for uncovered critical code

      # Identify complex functions (manual review)
      # Review ACT-R formulas, parsing logic, CLI commands
      ```
    - **Acceptance**: Risk profile document created, top 10 highest-risk areas identified, test gaps documented
    - **Rollback**: N/A (analysis only)

  - [ ] 4.2 Add pure unit tests for ACT-R activation formulas (5-7 tests)
    - **Effort**: 1.5 hours
    - **Description**: Create tests for base-level learning, spreading activation, decay calculations with edge cases
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/unit/aurora_memory/test_activation_formulas.py`
    - **Test Cases**:
      - Base-level learning with zero references
      - Spreading activation with multiple sources
      - Decay with extreme time values
      - Activation with missing/invalid parameters
      - Boundary conditions (min/max activation)
    - **Acceptance**: 5-7 tests added, 100% coverage of core formulas, tests run in <1s, all pass
    - **Rollback**: Delete test file

  - [ ] 4.3 Add pure unit tests for parsing logic (10-15 tests)
    - **Effort**: 2 hours
    - **Description**: Create tests for chunk parsing, context extraction, AST parsing with edge cases
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/unit/aurora_memory/test_parsing_logic.py`
    - **Test Cases**:
      - Chunk parsing with malformed input
      - Context extraction with edge cases
      - Import statement parsing with complex scenarios
      - AST parsing with Python 3.10-3.13 variations
      - Unicode handling, empty inputs, large inputs
    - **Acceptance**: 10-15 tests added, edge cases covered, tests run in <1s, all pass
    - **Rollback**: Delete test file

  - [ ] 4.4 Add contract tests for aurora_memory package (3-4 tests)
    - **Effort**: 1 hour
    - **Description**: Create tests verifying public API contracts (input types, output shapes, errors)
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/integration/test_memory_store_contract.py`
    - **Test Cases**:
      - MemoryStore.search returns correct type/shape
      - MemoryStore.search rejects invalid input
      - MemoryStore.query contract verification
      - Error handling for malformed queries
    - **Acceptance**: 3-4 contract tests added, tests fail if contracts broken, all pass
    - **Rollback**: Delete test file

  - [ ] 4.5 Add contract tests for aurora_planning package (3-4 tests)
    - **Effort**: 1 hour
    - **Description**: Create tests verifying Plan, Task, schema contracts
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/integration/test_planning_contract.py`
    - **Test Cases**:
      - Plan schema validation
      - Task schema validation
      - Planning workflow contract
      - Error handling for invalid inputs
    - **Acceptance**: 3-4 contract tests added, backward compatibility verified, all pass
    - **Rollback**: Delete test file

  - [ ] 4.6 Add contract tests for aurora_cli package (2-3 tests)
    - **Effort**: 45 minutes
    - **Description**: Create tests verifying CLI command interfaces and formatters
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/integration/test_cli_contract.py`
    - **Test Cases**:
      - Command interface contracts
      - Formatter output contracts
      - Error message format contracts
    - **Acceptance**: 2-3 contract tests added, CLI contracts verified, all pass
    - **Rollback**: Delete test file

  - [ ] 4.7 Add e2e test for full memory workflow (init → learn → search → query)
    - **Effort**: 1 hour
    - **Description**: Create end-to-end test covering complete user journey
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_full_memory_workflow.py`
    - **Test Steps**:
      1. `aur init` in tmp_path
      2. Add test file and `aur learn`
      3. `aur search` and verify results
      4. `aur query` and verify response
      5. Verify database state and cleanup
    - **Acceptance**: E2E test added, covers full workflow, runs in <60s, cleanup verified, passes
    - **Rollback**: Delete test file

  - [ ] 4.8 Add e2e test for planning workflow (create → edit → archive)
    - **Effort**: 1 hour
    - **Description**: Create end-to-end test for planning user journey
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_planning_workflow.py`
    - **Test Steps**:
      1. Create plan via CLI
      2. Edit plan (add tasks, update status)
      3. Archive plan
      4. Verify file system and database state
    - **Acceptance**: E2E test added, covers planning workflow, runs in <60s, passes
    - **Rollback**: Delete test file

  - [ ] 4.9 Add e2e test for MCP server workflow
    - **Effort**: 1 hour
    - **Description**: Create end-to-end test for MCP server interaction
    - **File**: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_mcp_workflow.py`
    - **Test Steps**:
      1. Start MCP server in test mode
      2. Send query via MCP protocol
      3. Verify response format
      4. Test error handling
      5. Shutdown and cleanup
    - **Acceptance**: E2E test added, covers MCP workflow, runs in <60s, passes
    - **Rollback**: Delete test file

  - [ ] 4.10 Verify coverage reached ≥82% target
    - **Effort**: 15 minutes
    - **Description**: Run coverage report, verify target met, document coverage improvements
    - **Commands**:
      ```bash
      pytest --cov=packages --cov-report=html --cov-report=term
      # Check total coverage percentage
      ```
    - **Acceptance**: Coverage ≥82%, improvement documented, critical gaps filled
    - **Rollback**: N/A (measurement only)

  - [ ] 4.11 **VERIFICATION GATE 4**: Complete Phase 4 verification checklist
    - **Effort**: 10 minutes
    - **Description**: Verify all Gate 4 criteria met before proceeding to Phase 5
    - **Checklist**: See "Gate 4: After Phase 4" section above
    - **Acceptance**: All 5 Gate 4 criteria checked and verified
    - **Rollback**: Fix any issues before proceeding

- [ ] 5.0 **PHASE 5 (HIGH)**: Document and Prevent - Regression Prevention
  - [ ] 5.1 Create import validation script for pre-commit hook
    - **Effort**: 30 minutes
    - **Description**: Build script to detect old aurora.* import patterns
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/validate_imports.py`
    - **Detection Logic**:
      ```python
      if re.search(r'from aurora\.', file_content):
          print(f"ERROR: Old import pattern in {filepath}")
          print("  Use 'aurora_memory' not 'aurora.memory'")
          sys.exit(1)
      ```
    - **Acceptance**: Script detects old patterns, provides actionable errors, runs in <1s, exits non-zero on violations
    - **Rollback**: Delete script

  - [ ] 5.2 Create test classification validation script for pre-commit hook
    - **Effort**: 30 minutes
    - **Description**: Build script to detect integration/e2e tests in unit/ directory
    - **File**: `/home/hamr/PycharmProjects/aurora/scripts/validate_test_classification.py`
    - **Detection Logic**:
      ```python
      if filepath.startswith("tests/unit/"):
          if "subprocess" in content or "SQLiteStore(" in content:
              print(f"ERROR: Integration test in unit/ directory")
              sys.exit(1)
      ```
    - **Acceptance**: Script detects misclassified tests, provides clear errors, runs in <1s
    - **Rollback**: Delete script

  - [ ] 5.3 Create .pre-commit-config.yaml with all validation hooks
    - **Effort**: 20 minutes
    - **Description**: Configure pre-commit framework with import, classification, and marker validation
    - **File**: `/home/hamr/PycharmProjects/aurora/.pre-commit-config.yaml`
    - **Hooks**: validate_imports.py, validate_test_classification.py, validate_marker_usage.py
    - **Acceptance**: Config file created, 3 custom hooks + standard hooks (trailing-whitespace, etc.)
    - **Rollback**: Delete config file

  - [ ] 5.4 Install and test pre-commit hooks
    - **Effort**: 20 minutes
    - **Description**: Install hooks, test with intentional violations, verify all caught
    - **Commands**:
      ```bash
      pip install pre-commit
      pre-commit install

      # Test with intentional violation
      echo "from aurora.memory import X" > test_violation.py
      git add test_violation.py
      git commit -m "test"  # Should fail

      # Cleanup
      rm test_violation.py
      ```
    - **Acceptance**: Hooks installed, violations caught, actionable error messages, total runtime <2s
    - **Rollback**: `pre-commit uninstall`

  - [ ] 5.5 Create TEST_MIGRATION_CHECKLIST.md document
    - **Effort**: 45 minutes
    - **Description**: Document step-by-step guide for future refactorings to prevent similar breakage
    - **File**: `/home/hamr/PycharmProjects/aurora/docs/TEST_MIGRATION_CHECKLIST.md`
    - **Sections**:
      - Before Refactoring (baseline, identify affected files)
      - During Refactoring (dry-run, review, apply, verify)
      - After Refactoring (update docs, hooks, PR notes)
      - Rollback Plan (backup branches, granular commits)
    - **Acceptance**: Checklist complete, tested by walking through this migration, approved
    - **Rollback**: Delete or revert document

  - [ ] 5.6 Update TESTING.md with new import patterns and classification criteria
    - **Effort**: 1 hour
    - **Description**: Comprehensive update with import patterns, test classification criteria, marker guidelines, lessons learned
    - **File**: `/home/hamr/PycharmProjects/aurora/docs/TESTING.md`
    - **New Sections**:
      - Import Patterns (correct aurora_* usage)
      - Test Classification Criteria (decision tree)
      - Marker Usage Guidelines (ml, slow, real_api)
      - Test Pyramid (updated diagram 60/30/10)
      - Migration Lessons Learned
    - **Acceptance**: TESTING.md updated, all sections accurate, reviewed and approved
    - **Rollback**: Git revert documentation changes

  - [ ] 5.7 Create ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md
    - **Effort**: 45 minutes
    - **Description**: Document timeline, root causes, prevention strategies, lessons learned
    - **File**: `/home/hamr/PycharmProjects/aurora/docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md`
    - **Sections**:
      - Timeline (Dec 2025 → Jan 2026)
      - Symptoms (73 errors, coverage unmeasurable)
      - Root Causes (import breakage, misclassification, marker bloat)
      - Prevention Strategies (pre-commit hooks, migration checklist)
      - Lessons Learned (5-6 key lessons)
      - Recommendations (quarterly audits, validation in CI)
    - **Acceptance**: RCA document complete, captures all learnings, reviewed and approved
    - **Rollback**: Delete or revert document

  - [ ] 5.8 Create CI_SWITCHOVER_PLAN.md
    - **Effort**: 30 minutes
    - **Description**: Document switchover process from legacy to new CI
    - **File**: `/home/hamr/PycharmProjects/aurora/docs/CI_SWITCHOVER_PLAN.md`
    - **Sections**:
      - Current State (legacy + new running in parallel)
      - Switchover Criteria (7 days stable, all pass, approval)
      - Switchover Steps (rename files, update branch protection)
      - Rollback Procedure (restore legacy if issues)
      - Success Criteria (all PRs use new CI)
    - **Acceptance**: Switchover plan documented, criteria clear, rollback tested (dry-run)
    - **Rollback**: Delete or revert document

  - [ ] 5.9 **VERIFICATION GATE 5**: Complete Phase 5 verification checklist
    - **Effort**: 10 minutes
    - **Description**: Verify all Gate 5 criteria met before proceeding to Phase 6
    - **Checklist**: See "Gate 5: After Phase 5" section above
    - **Acceptance**: All 6 Gate 5 criteria checked and verified
    - **Rollback**: Fix any issues before proceeding

- [ ] 6.0 **POST-PHASES**: CI Switchover and Final Verification
  - [ ] 6.1 Verify new CI has been passing consistently for 7+ days
    - **Effort**: 5 minutes (plus 7 days waiting)
    - **Description**: Monitor GitHub Actions, verify new CI stable, no intermittent failures
    - **Monitoring**: Check GitHub Actions dashboard daily, document any failures
    - **Acceptance**: New CI green for 7+ consecutive days across all Python versions
    - **Rollback**: Extend monitoring period if issues found

  - [ ] 6.2 Obtain stakeholder approval for CI switchover
    - **Effort**: 15 minutes
    - **Description**: Present switchover plan and CI stability evidence, get approval to proceed
    - **Materials**: CI_SWITCHOVER_PLAN.md, CI logs showing 7+ days stability
    - **Acceptance**: Stakeholder reviews and approves switchover
    - **Rollback**: N/A (approval gate)

  - [ ] 6.3 Execute CI switchover (disable legacy, enable new as primary)
    - **Effort**: 20 minutes
    - **Description**: Rename workflow files, update branch protection rules
    - **Commands**:
      ```bash
      cd .github/workflows
      mv testing-infrastructure-legacy.yml testing-infrastructure-legacy.yml.disabled
      mv testing-infrastructure-new.yml testing-infrastructure.yml
      git add -A
      git commit -m "chore(ci): switch to new testing infrastructure"
      git push
      # Update branch protection rules in GitHub UI
      ```
    - **Acceptance**: Legacy CI disabled, new CI is primary, branch protection updated
    - **Rollback**: Reverse renames, revert commit

  - [ ] 6.4 Monitor new CI for 24 hours post-switchover
    - **Effort**: 10 minutes (plus 24 hours monitoring)
    - **Description**: Verify all PRs use new CI, no issues reported
    - **Monitoring**: Check all new PRs, verify CI runs and passes
    - **Acceptance**: All PRs use new CI, no increase in failures, no team complaints
    - **Rollback**: Execute rollback procedure from CI_SWITCHOVER_PLAN.md if issues

  - [ ] 6.5 Schedule legacy CI cleanup (30 days post-switchover)
    - **Effort**: 5 minutes
    - **Description**: Create calendar reminder to delete legacy CI file after 30 day safety period
    - **Action**: Set reminder for 30 days from switchover date
    - **Acceptance**: Reminder created, date documented
    - **Rollback**: N/A (scheduling only)

  - [ ] 6.6 **VERIFICATION GATE 6**: Complete final verification checklist
    - **Effort**: 10 minutes
    - **Description**: Verify all Gate 6 criteria met, migration complete
    - **Checklist**: See "Gate 6: After CI Switchover" section above
    - **Acceptance**: All 5 Gate 6 criteria checked and verified
    - **Rollback**: Fix any issues or extend monitoring

  - [ ] 6.7 Create final migration summary and close
    - **Effort**: 30 minutes
    - **Description**: Document final metrics, lessons learned, archive all migration artifacts
    - **Deliverables**:
      - Final metrics comparison (before/after)
      - Migration timeline and effort actuals
      - Key lessons and recommendations
      - Archive of all scripts, reports, and plans
    - **Acceptance**: Summary document complete, all artifacts archived, PRD marked complete
    - **Rollback**: N/A (completion task)

---

## Implementation Notes

### Automation Strategy
All migration scripts follow the pattern:
1. **Analysis** - Read codebase, generate report
2. **Dry-run** - Show proposed changes, no modifications
3. **Review** - Human approval of changes
4. **Apply** - Execute changes with logging
5. **Verify** - Run tests, confirm success
6. **Commit** - Granular git commits for rollback

### Script Reusability
Several scripts serve dual purposes:
- **validate_imports.py**: Migration analysis + pre-commit hook
- **validate_marker_usage.py**: Cleanup detection + pre-commit hook
- **classify_tests.py**: Migration planning + future audits

### Error Handling
All scripts must:
- Exit with non-zero status on errors
- Provide actionable error messages
- Support --help flag with usage examples
- Log all changes for audit trail

### Testing Strategy
After each phase:
1. Run `pytest --collect-only` (verify collection)
2. Run `pytest tests/` (verify all pass)
3. Run `pytest --cov=packages` (verify coverage)
4. Commit with descriptive message

### Git Workflow
- Create feature branch per phase: `phase1-import-migration`, `phase2-reclassify`, etc.
- Granular commits within phase (per batch, per logical change)
- Merge to main after verification gate passed
- Tag releases: `testing-infra-phase1-complete`, etc.

---

**Phase 2 Complete**: Detailed sub-tasks generated for all 6 phases.

**Total Sub-Tasks**: 60+ actionable tasks across 6 phases
**Estimated Total Effort**: 15-18 hours active work + 7 days monitoring
**Ready for Execution**: All tasks have clear acceptance criteria, rollback procedures, and effort estimates

**Next Steps**: Begin Phase 1 execution or use task list for tracking with your preferred task management system.
