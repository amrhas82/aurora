# Test Migration Checklist

**Purpose**: Step-by-step guide for safely refactoring Aurora's codebase while maintaining test integrity.

**Last Updated**: January 6, 2026
**Related Documents**:
- `/docs/TESTING.md` - Test classification criteria and guidelines
- `/docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md` - Lessons learned from 2025 breakage
- `/docs/TESTING_TECHNICAL_DEBT.md` - Current testing status and coverage

---

## Overview

This checklist codifies the systematic approach used in **tasks-0023** (Testing Infrastructure Overhaul) to prevent test breakage during large-scale refactorings. Follow these steps whenever you:

- Rename packages or modules
- Restructure directory hierarchies
- Change import patterns
- Migrate between testing frameworks
- Update CI/CD configurations

**Key Principle**: **Verify at every step. Never proceed without confirmation tests still pass.**

---

## Before Refactoring

### 1. Establish Baseline

- [ ] **Run full test suite**: `pytest tests/ -v > baseline-results.txt`
  - Record total test count: \_\_\_\_\_
  - Record pass count: \_\_\_\_\_
  - Record failure count: \_\_\_\_\_
  - Record collection errors: \_\_\_\_\_

- [ ] **Measure code coverage**: `pytest tests/ --cov=packages --cov-report=term`
  - Record total coverage: \_\_\_\_\_%
  - Record package-specific coverage:
    ```
    core:         ____%
    cli:          ____%
    planning:     ____%
    reasoning:    ____%
    memory:       ____%
    ```

- [ ] **Check CI status**: Verify GitHub Actions passing on all Python versions
  - [ ] Python 3.10
  - [ ] Python 3.11
  - [ ] Python 3.12
  - [ ] Python 3.13

- [ ] **Document test pyramid distribution**:
  ```bash
  find tests/unit -name "test_*.py" | wc -l        # Unit count: _____
  find tests/integration -name "test_*.py" | wc -l # Integration count: _____
  find tests/e2e -name "test_*.py" | wc -l         # E2E count: _____
  ```

- [ ] **Create baseline branch**: `git checkout -b baseline-[refactoring-name]`

### 2. Identify Affected Files

- [ ] **Scan for import patterns** (if renaming packages):
  ```bash
  # Example: Find all files importing old package name
  grep -r "from aurora\." packages/ tests/ > affected-imports.txt
  grep -r "import aurora\." packages/ tests/ >> affected-imports.txt
  ```

- [ ] **Identify test files directly affected**:
  ```bash
  # Files importing the module being refactored
  grep -l "from [old_module]" tests/**/*.py > affected-tests.txt
  ```

- [ ] **Analyze test dependencies** (if moving test files):
  ```bash
  python scripts/analyze_test_dependencies.py --files affected-tests.txt > dependency-graph.json
  ```

- [ ] **Count affected files**:
  - Production files: \_\_\_\_\_
  - Test files: \_\_\_\_\_
  - CI/build files: \_\_\_\_\_

### 3. Plan Migration Batches

- [ ] **Group files by dependency order** (if applicable):
  - Batch 1 (no dependencies): \_\_\_\_\_ files
  - Batch 2 (depends on Batch 1): \_\_\_\_\_ files
  - Batch 3 (depends on Batch 2): \_\_\_\_\_ files

- [ ] **Identify circular dependencies** (if any):
  ```bash
  python scripts/analyze_test_dependencies.py --detect-cycles
  ```

- [ ] **Create migration plan document**: `migration-plan-[date].md`
  - List all batches
  - Document dependencies
  - Note any edge cases or special handling

---

## During Refactoring

### 4. Prepare Automation (Recommended)

- [ ] **Create migration script** (if automatable):
  - Script location: `scripts/migrate_[refactoring-name].py`
  - [ ] Supports `--dry-run` mode
  - [ ] Logs all changes
  - [ ] Exits non-zero on errors
  - [ ] Includes `--help` documentation

- [ ] **Test script in dry-run mode**:
  ```bash
  python scripts/migrate_[refactoring-name].py --dry-run > migration-preview.txt
  ```

- [ ] **Review dry-run output**:
  - [ ] No false positives
  - [ ] All expected changes present
  - [ ] No unexpected changes
  - [ ] Edge cases handled correctly

### 5. Create Safety Branches

- [ ] **Create backup branch**: `git checkout -b backup-[refactoring-name]`
- [ ] **Create working branch**: `git checkout -b [refactoring-name]`
- [ ] **Document branch strategy**: Note branch names in migration plan

### 6. Apply Changes (Batch by Batch)

For each batch:

#### 6.1 Apply Changes

- [ ] **Run migration** (automated or manual):
  ```bash
  # Automated
  python scripts/migrate_[refactoring-name].py --batch 1

  # Manual
  # Make changes carefully, one file at a time
  ```

- [ ] **Review changes**:
  ```bash
  git diff --staged
  # Verify changes are correct
  ```

#### 6.2 Verify Tests Still Collect

- [ ] **Run collection check**:
  ```bash
  pytest --collect-only 2>&1 | tee batch-collection.txt
  ```

- [ ] **Check for collection errors**:
  ```bash
  grep -i "error" batch-collection.txt
  # Should return nothing
  ```

- [ ] **Count tests collected**:
  ```bash
  grep "test session starts" batch-collection.txt
  # Should match baseline count
  ```

#### 6.3 Run Tests

- [ ] **Run full test suite**:
  ```bash
  pytest tests/ -v 2>&1 | tee batch-test-results.txt
  ```

- [ ] **Compare results to baseline**:
  - Total tests: \_\_\_\_\_ (baseline: \_\_\_\_\_)
  - Pass count: \_\_\_\_\_ (baseline: \_\_\_\_\_)
  - Failure count: \_\_\_\_\_ (baseline: \_\_\_\_\_)
  - **New failures**: \_\_\_\_\_ (must be 0)

- [ ] **If new failures appear**:
  - [ ] Investigate root cause
  - [ ] Fix issues
  - [ ] Re-run tests
  - [ ] Document fix in migration notes

#### 6.4 Commit Changes

- [ ] **Stage changes**:
  ```bash
  git add -A
  ```

- [ ] **Create granular commit**:
  ```bash
  git commit -m "refactor(scope): [descriptive message for batch X]

  - Change 1
  - Change 2
  - Change 3

  Tests: [pass count]/[total count] passing
  Batch: X/Y complete"
  ```

#### 6.5 Repeat for Next Batch

- [ ] Mark batch complete: Batch \_\_\_\_\_ / \_\_\_\_\_ ✓
- [ ] Proceed to next batch (return to 6.1)

### 7. Verify Complete Migration

After all batches complete:

- [ ] **Run full test suite again**:
  ```bash
  pytest tests/ -v --tb=short > final-test-results.txt
  ```

- [ ] **Compare to baseline**:
  - [ ] Total test count matches
  - [ ] Pass rate same or better
  - [ ] No new collection errors
  - [ ] No new test failures

- [ ] **Run coverage check**:
  ```bash
  pytest tests/ --cov=packages --cov-report=term
  ```

- [ ] **Compare coverage to baseline**:
  - [ ] Total coverage maintained or improved
  - [ ] No significant drops in package-specific coverage

- [ ] **Run static analysis** (if applicable):
  ```bash
  mypy packages/
  flake8 packages/ tests/
  ```

- [ ] **Verify CI passes**:
  ```bash
  git push origin [refactoring-name]
  # Monitor GitHub Actions
  ```

---

## After Refactoring

### 8. Update Documentation

- [ ] **Update TESTING.md** (if patterns changed):
  - [ ] Import patterns section
  - [ ] Test classification criteria
  - [ ] Marker usage guidelines
  - [ ] Test pyramid distribution

- [ ] **Update README.md** (if user-facing changes):
  - [ ] Installation instructions
  - [ ] Development setup
  - [ ] Running tests

- [ ] **Update CI/CD documentation** (if CI changed):
  - [ ] Workflow descriptions
  - [ ] Branch protection rules
  - [ ] Required checks

- [ ] **Create migration notes**: `docs/migrations/[refactoring-name]-[date].md`
  - Timeline
  - Changes made
  - Files affected
  - Lessons learned

### 9. Update Pre-Commit Hooks

If refactoring introduced new patterns to validate:

- [ ] **Create validation script**: `scripts/validate_[pattern].py`
- [ ] **Add to .pre-commit-config.yaml**:
  ```yaml
  - id: validate-[pattern]
    name: Validate [Pattern]
    entry: python scripts/validate_[pattern].py
    language: system
    pass_filenames: true
    types: [python]
  ```

- [ ] **Test hook with violations**:
  ```bash
  # Create file with violation
  # Try to commit
  git add test-file.py
  git commit -m "test"
  # Should fail with clear error
  ```

- [ ] **Install hooks** (if not already):
  ```bash
  pre-commit install
  ```

### 10. Create Pull Request

- [ ] **Write comprehensive PR description**:
  - **What**: Brief summary of refactoring
  - **Why**: Motivation and benefits
  - **How**: Approach and key changes
  - **Testing**: Verification steps taken
  - **Risks**: Any potential issues or rollback plan

- [ ] **Include metrics**:
  ```
  Tests: [before] → [after]
  Coverage: [before]% → [after]%
  Files changed: [count]
  Lines changed: [count]
  ```

- [ ] **Link to related documents**:
  - Migration plan
  - Test results
  - Coverage reports

- [ ] **Request reviews** from:
  - [ ] Code owner
  - [ ] Test infrastructure maintainer
  - [ ] Domain expert (if applicable)

### 11. Monitor Post-Merge

- [ ] **Monitor CI for 24 hours post-merge**:
  - [ ] All PRs using updated code
  - [ ] No test flakiness reported
  - [ ] No increased failure rates

- [ ] **Monitor for 7 days** (if major refactoring):
  - [ ] Weekly test pass rate
  - [ ] Test execution time trends
  - [ ] Coverage stability

- [ ] **Document any issues found**:
  - Create follow-up issues
  - Update migration notes
  - Add to lessons learned

---

## Rollback Procedures

### If Tests Fail During Migration

1. **Identify failure type**:
   - Collection error → Import or syntax issue
   - Test failure → Behavior change or broken test
   - Timeout → Performance regression

2. **For collection errors**:
   ```bash
   # Revert last batch
   git reset --hard HEAD~1
   # Fix issue
   # Re-apply batch manually
   ```

3. **For test failures**:
   ```bash
   # Run failing test in isolation
   pytest tests/path/to/test_file.py::test_name -vv
   # Investigate root cause
   # Fix and verify
   pytest tests/path/to/test_file.py::test_name -vv
   ```

4. **For persistent issues**:
   ```bash
   # Rollback to backup branch
   git checkout backup-[refactoring-name]
   # Review migration plan
   # Identify issue
   # Create new working branch
   git checkout -b [refactoring-name]-v2
   ```

### If CI Fails Post-Merge

1. **Immediate assessment**:
   - Is failure reproducible locally?
   - Does it fail on all Python versions?
   - Is it a test issue or production bug?

2. **Quick fix** (if possible):
   ```bash
   # Create hotfix branch
   git checkout -b hotfix-[issue]
   # Apply fix
   # Verify locally
   pytest tests/ -v
   # Push and merge immediately
   ```

3. **Revert merge** (if fix not obvious):
   ```bash
   git revert [merge-commit-sha]
   git push origin main
   # Investigate thoroughly
   # Re-apply with fix
   ```

### If Coverage Drops Significantly

1. **Investigate dropped coverage**:
   ```bash
   pytest tests/ --cov=packages --cov-report=html
   open htmlcov/index.html
   # Identify newly uncovered lines
   ```

2. **Determine cause**:
   - Tests removed accidentally?
   - Tests skipped due to import errors?
   - Production code added without tests?

3. **Remediate**:
   - Restore removed tests
   - Fix import errors
   - Add missing tests
   - Document in migration notes

---

## Lessons Learned from 2025 Breakage

### What Went Wrong

1. **No baseline measurement** - Didn't document test count/coverage before refactoring
2. **No verification between steps** - Applied all changes at once, hard to isolate failures
3. **Incomplete import migration** - Missed edge cases, especially in test files
4. **No pre-commit validation** - Regressions not caught until CI
5. **Test classification drift** - Integration tests in unit/, pyramid inverted

### What Worked Well (tasks-0023)

1. **Dry-run mode** - Caught issues before applying changes
2. **Batch migrations** - Isolated failures to specific batches
3. **Granular commits** - Easy rollback of individual changes
4. **Parallel CI** - New CI validated changes without breaking existing workflow
5. **Verification gates** - Forced confirmation before proceeding
6. **Automation scripts** - Consistent, auditable changes
7. **Pre-commit hooks** - Prevented regressions from re-occurring

### Key Principles

- **Verify at every step** - Never proceed without passing tests
- **Automate when possible** - Scripts reduce human error
- **Validate early** - Pre-commit hooks catch issues before CI
- **Document everything** - Migration plans, test results, lessons learned
- **Granular commits** - One logical change per commit
- **Parallel safety nets** - Run new CI alongside legacy until stable

---

## Checklist Summary

Use this quick reference during migrations:

**Before**:
- [ ] Baseline tests, coverage, CI
- [ ] Identify affected files
- [ ] Plan batches
- [ ] Create safety branches

**During**:
- [ ] Dry-run automation
- [ ] Apply batch
- [ ] Verify collection
- [ ] Run tests
- [ ] Commit if passing
- [ ] Repeat for next batch

**After**:
- [ ] Update docs
- [ ] Update hooks
- [ ] Create PR
- [ ] Monitor post-merge

**Rollback** (if needed):
- [ ] Assess failure type
- [ ] Fix or revert
- [ ] Document lesson

---

## References

- **tasks-0023**: Testing Infrastructure Overhaul (5-phase migration, January 2026)
- **TESTING.md**: Test classification criteria and guidelines
- **ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md**: Detailed RCA of 2025 breakage
- **TESTING_TECHNICAL_DEBT.md**: Current testing status and coverage metrics

---

**Version**: 1.0
**Last Updated**: January 6, 2026
**Next Review**: Quarterly (April 2026)
