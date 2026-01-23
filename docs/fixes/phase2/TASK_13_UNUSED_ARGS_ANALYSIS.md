# Task 13.0: Unused Arguments - Analysis & Strategy

**Status:** Prepared for execution after Task 12 completes
**Report Generated:** 2026-01-23 10:30
**Total Violations:** 266 (102 ARG001 + 104 ARG002 + 59 ARG005 + 1 ARG004)

---

## Executive Summary

**Violation Breakdown:**
- **ARG001:** 102 unused function arguments
- **ARG002:** 104 unused method arguments ⚠️ (ABC/Protocol risk)
- **ARG005:** 59 unused lambda arguments
- **ARG004:** 1 unused static method argument

**Location Distribution:**
```
Tests (170 violations, 64%):
  - packages/soar/tests: 75
  - packages/cli/tests: 48
  - packages/spawner/tests: 44
  - packages/core/tests: 3
  - tests/ directory: 5

Source Code (96 violations, 36%):
  - packages/cli/src: 31
  - packages/context-code/src: 7
  - packages/soar/src: 6
  - packages/spawner/src: 4
  - packages/planning/src: 3
  - packages/testing/src: 1
```

---

## Risk Assessment

### 🔴 High Risk: ARG002 (Method Arguments)

**Why risky:**
- Methods may implement ABC/Protocol interfaces
- Removing args breaks interface contracts
- Requires careful review of base classes

**Strategy:**
1. Search for `@abstractmethod`, `Protocol`, inheritance
2. Keep args that match parent signatures (prefix with `_`)
3. Only remove truly unused args

**Example patterns to watch:**
```python
# DON'T remove if it matches parent
class Derived(Base):
    def process(self, data, config):  # ARG002: config unused
        # But Base.process() requires config!
        pass

# DO prefix with underscore
class Derived(Base):
    def process(self, data, _config):  # Keeps interface, signals unused
        pass
```

### 🟡 Medium Risk: ARG001 (Function Arguments)

**Click callbacks are special:**
```python
# These MUST keep ctx, param even if unused (Click interface)
def _parse_tools_callback(ctx, param, value):  # ARG001: ctx, param
    return value

# Fix: Prefix with underscore
def _parse_tools_callback(_ctx, _param, value):
    return value
```

**Other patterns:**
- Compatibility shims: May need args for API consistency
- Public APIs: Consider deprecation path before removal

### 🟢 Low Risk: ARG005 (Lambda Arguments)

**Simple fixes:**
```python
# Before
lambda x, y: x + 1  # ARG005: y unused

# After
lambda x, _: x + 1
```

---

## Execution Strategy

### Phase 1: Low-Risk Cleanup (ARG005 + ARG004)

**Scope:** 60 violations (59 ARG005 + 1 ARG004)
**Time:** ~15-30 minutes
**Risk:** Low

**Approach:**
```bash
# Automated fix for lambdas
ruff check packages/ tests/ --select ARG005 --fix

# Manual review for ARG004
# (only 1 violation, quick fix)
```

**Commit:**
```
fix: replace unused lambda arguments with _ (Task 13.4)

Replaced 59 unused lambda arguments with underscore to signal
intentional non-use. No functional changes.

Verified with: ruff check packages/ tests/ --select ARG005
```

### Phase 2: Function Arguments (ARG001)

**Scope:** 102 violations
**Time:** ~1-2 hours
**Risk:** Medium (Click callbacks need care)

**Approach:**
1. **Click callbacks first** (~20 violations)
   - Pattern: `def *_callback(ctx, param, value)`
   - Fix: Prefix unused with `_`
   - Verify: Click still works

2. **Test fixtures** (~40 violations in tests/)
   - Often required by pytest/unittest signatures
   - Prefix with `_` if required, remove if not

3. **Internal functions** (~42 violations in src/)
   - Safe to remove if truly internal
   - Review callers first

**Commits:** 3-4 commits by category

### Phase 3: Method Arguments (ARG002) - CAREFUL!

**Scope:** 104 violations
**Time:** ~2-3 hours
**Risk:** High

**Approach:**
1. **Identify interface methods** (grep for ABC, Protocol, inheritance)
2. **Test methods first** (~50 violations in tests/)
   - unittest setUp/tearDown signatures
   - pytest fixtures
   - Mock method implementations
3. **Source methods** (~54 violations in src/)
   - **Manual review each one**
   - Check inheritance chain
   - Verify not part of public API

**Commits:** 4-5 commits by package + risk level

---

## Detailed Fix Patterns

### Pattern 1: Click Callbacks

**Detection:**
```bash
grep -A5 "def.*_callback" unused_args_report.txt
```

**Fix:**
```python
# Before
@click.option("--tool", callback=validate_tool)
def validate_tool(ctx, param, value):  # ARG001: ctx, param
    return value.lower()

# After
@click.option("--tool", callback=validate_tool)
def validate_tool(_ctx, _param, value):  # Explicit non-use
    return value.lower()
```

### Pattern 2: Test Fixtures

**Detection:**
```bash
grep "def test_" unused_args_report.txt | head -20
```

**Fix:**
```python
# Before
def test_something(mock_config, mock_db):  # ARG001: mock_config
    assert mock_db.exists()

# After - Option A: Remove
def test_something(mock_db):
    assert mock_db.exists()

# After - Option B: If fixture required for setup side-effects
def test_something(_mock_config, mock_db):  # Kept for side-effects
    assert mock_db.exists()
```

### Pattern 3: ABC/Protocol Methods

**Detection:**
```bash
# Find potential interface implementations
grep "class.*(" unused_args_report.txt -B10 | grep -E "ABC|Protocol|Base"
```

**Fix:**
```python
# Before
class ConcreteStore(BaseStore):
    def save(self, data, metadata):  # ARG002: metadata
        return self._write(data)

# After - Keep for interface compatibility
class ConcreteStore(BaseStore):
    def save(self, data, _metadata):  # Interface requires it
        return self._write(data)
```

### Pattern 4: Lambdas (Simple)

**Fix:**
```python
# Before
sorted(items, key=lambda x, y: x.name)  # ARG005: y

# After
sorted(items, key=lambda x, _: x.name)
```

---

## Verification Commands

### After Each Batch:
```bash
# Check remaining violations
ruff check packages/cli/ --select ARG001 | wc -l

# Run affected tests
pytest tests/unit/cli/ -v

# Type check (ensure no interface breakage)
mypy packages/cli/src --strict
```

### After All Changes:
```bash
# Verify all ARG violations resolved
ruff check packages/ tests/ --select ARG

# Full test suite
make test > task_13_validation.txt

# Compare with Task 12 validation
diff <(grep "passed" phase2b_validation_tests.txt) \
     <(grep "passed" task_13_validation.txt)
```

---

## Files Requiring Special Attention

### Click Callbacks (packages/cli/src/aurora_cli/commands/)
```
headless.py:23 - _parse_tools_callback
headless.py:37 - _parse_tool_flags_callback
headless.py:55 - _parse_tool_env_callback
```

**Action:** Prefix unused `ctx`, `param` with underscore

### Test Fixtures (All test files)

**Pattern:** Test methods with unused fixtures
**Action:**
1. Check if fixture has side-effects (setup/teardown)
2. If yes: prefix with `_`
3. If no: remove from signature

### Potential Interface Methods

**Packages to review:**
- `packages/core/src/aurora_core/store/` - BaseStore implementations
- `packages/reasoning/src/aurora_reasoning/` - LLM client interfaces
- `packages/spawner/src/aurora_spawner/` - Executor interfaces

**Action:** Manual review of each ARG002 violation in these packages

---

## Commit Structure (Proposed)

```
Task 13.2: Fix ARG001 - Click callbacks (packages/cli)
Task 13.3: Fix ARG001 - Test fixtures (tests/)
Task 13.4: Fix ARG001 - Internal functions (all packages)
Task 13.5: Fix ARG005 - Lambda arguments (all locations)
Task 13.6: Fix ARG004 - Static method (1 file)
Task 13.7: Fix ARG002 - Test methods (tests/)
Task 13.8: Fix ARG002 - Interface implementations (careful review)
Task 13.9: Fix ARG002 - Internal methods (safe to remove)
Task 13.10: Verify all ARG violations resolved
```

---

## Time Estimates

- **Phase 1 (ARG005 + ARG004):** 30 minutes
- **Phase 2 (ARG001):** 2 hours
- **Phase 3 (ARG002):** 3 hours
- **Testing/Verification:** 2 hours (per test suite run)
- **Total:** ~8-10 hours of work + 4-6 hours of test runs

---

## Rollback Strategy

If tests fail after ARG fixes:

```bash
# Identify which commit caused failures
git bisect start
git bisect bad HEAD
git bisect good <last-known-good-commit>

# Revert specific commit
git revert <failing-commit>

# Or reset entire Task 13
git reset --hard <commit-before-task-13>
```

---

**Prepared:** 2026-01-23 10:30
**Ready to execute when:** Task 12 validation completes successfully
**Estimated completion:** Task 13 will take 2-3 days with proper testing
