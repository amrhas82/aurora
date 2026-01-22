# PRD: Aurora Phase 2 Code Quality Improvements

**Created:** 2026-01-22
**Status:** Ready for Implementation
**Owner:** Code Quality Initiative
**Target:** Phase 2A (2-3 days) + Phase 2B (2-3 days)

---

## Overview

Aurora has successfully completed Stages 0 and 1, fixing 4,678 auto-fixable issues (19.9% of total) with measurable performance improvements. Phase 2 shifts focus to **critical fixes requiring manual work and architectural decisions**: type errors that could cause runtime failures, complex functions that are hard to maintain and test, and code cleanup that improves maintainability.

Phase 2 is split into two sub-phases to enable milestone validation and risk management:
- **Phase 2A (Critical):** Type safety and complexity reduction
- **Phase 2B (Cleanup):** Dead code removal and API hygiene

---

## Goals

1. **Eliminate Runtime Risk:** Fix all 47 mypy type errors to prevent AttributeError, TypeError, and type inconsistency bugs in production
2. **Reduce Complexity:** Refactor top 10 complex functions (C90 > 15) to improve testability, debuggability, and performance optimization potential
3. **Improve Maintainability:** Remove 264 unused arguments and 79 commented code blocks to reduce cognitive load and maintenance burden
4. **Maintain Performance:** Preserve or improve startup time benchmarks (current: ~1.835s import time, 17% improvement from Stage 0)

---

## User Stories

**As a developer:**
- I want type errors fixed so I can trust mypy to catch bugs before runtime
- I want complex functions broken down so I can understand and modify CLI commands without fear
- I want unused arguments clearly marked so I know what's intentional vs dead code

**As a CI/CD pipeline:**
- I want `make type-check` to pass without errors so type safety is enforced
- I want all tests to remain passing after refactoring so correctness is preserved

**As a performance monitor:**
- I want startup benchmarks to remain under 3.0s total (preferably improving) so user experience stays fast
- I want complexity-reduced functions to be JIT-optimizable so hot paths run faster

---

## Requirements

### Phase 2A: Critical Fixes (2-3 days)

#### 1. Type Error Resolution (47 errors)

**Priority Order:** packages/context-code → packages/soar → packages/core

**1.1 packages/context-code (10 errors):**
- MUST fix `languages/typescript.py:94` - None check before `.parse()` call to prevent AttributeError
- MUST fix `semantic/embedding_provider.py:252` - None check before function call to prevent TypeError
- MUST fix `semantic/hybrid_retriever.py:493,610` - Add type parameters to dict: `dict[str, Any]`
- MUST add type annotations to `__init__.py:20`

**1.2 packages/soar (13 errors):**
- MUST fix `phases/assess.py:415` - Cast float to int or change target type for complexity scoring
- MUST fix `phases/assess.py:429` - Validate string value or use proper Literal type for assessment levels
- MUST fix `phases/retrieve.py:126` - Accept base Store type or cast properly for type compatibility
- MUST fix `phases/assess.py:55,57,871` - Add type parameters: `dict[str, Any]`
- MUST fix `phases/collect.py:35,46` - Add type parameters: `dict[str, Any]`
- MUST add type annotations to `phases/collect.py:94` (_get_agent_matcher)
- MUST add type annotations to `orchestrator.py:209,220,234,1618` (helper methods)

**1.3 packages/core (remaining errors):**
- MUST resolve all remaining type errors in core package
- MUST ensure Store base class compatibility with SQLiteStore

**1.4 Verification:**
- MUST run `make type-check` and achieve zero errors in packages/context-code, packages/soar, packages/core
- MUST maintain all existing type hints (no regressions)
- MUST add tests for fixed None-handling edge cases

#### 2. Complexity Reduction (Top 10 functions with C90 > 15)

**Target:** Reduce all targeted functions to C90 ≤ 15

**2.1 Critical Functions:**

1. **headless_command** (C90=53 → target ≤15)
   - File: `packages/cli/src/aurora_cli/commands/headless.py:212`
   - MUST extract argument parsing logic into separate function
   - MUST extract validation logic into separate function
   - MUST extract execution loop into separate function
   - MUST maintain existing CLI behavior exactly
   - MUST add unit tests for extracted functions

2. **goals_command** (C90=26 → target ≤15)
   - File: `packages/cli/src/aurora_cli/commands/goals.py:161`
   - MUST extract planning logic into separate function
   - MUST extract SOAR pipeline invocation into separate function
   - MUST simplify error handling paths
   - MUST maintain existing CLI behavior exactly
   - MUST add unit tests for extracted functions

3. **_handle_auto_fix** (C90=12 → target ≤10)
   - File: `packages/cli/src/aurora_cli/commands/doctor.py:197`
   - SHOULD use strategy pattern for different fix types
   - MUST reduce nested conditionals
   - MUST maintain existing auto-fix behavior

4. **list_command** (C90=12 → target ≤10)
   - File: `packages/cli/src/aurora_cli/commands/agents.py:169`
   - MUST extract filtering logic into separate function
   - MUST extract formatting logic into separate function

5. **parse_file** (C90=11 → target ≤10)
   - File: `packages/cli/src/aurora_cli/agent_discovery/parser.py:50`
   - SHOULD consider state machine or parser combinator pattern
   - MUST simplify parsing branches

**2.2 Remaining Top 10 (functions 6-10 with C90 > 15):**
- MUST identify from ruff output: `ruff check packages/ --select C90 | grep "C901" | sort -k3 -n -r | head -10`
- MUST refactor using same principles: extract functions, reduce nesting, simplify conditionals
- MUST maintain existing behavior exactly

**2.3 Verification:**
- MUST run `ruff check packages/ --select C90` and confirm all targeted functions ≤ 15
- MUST achieve 100% test coverage on new extracted functions
- MUST run `make benchmark-startup` and confirm no regression (ideally improvement)

### Phase 2B: Cleanup (2-3 days)

#### 3. Unused Argument Treatment (264 issues)

**Policy:**
- Remove obvious dead code (argument never referenced, no interface requirement)
- Prefix interface/callback requirements with `_` (e.g., Click callbacks, ABC implementations)

**3.1 Function Arguments (100 issues, ARG001):**
- MUST review each instance in packages/cli/src/aurora_cli/commands/
- MUST remove truly unused arguments where signature can be changed
- MUST prefix with `_` where required by framework (Click, callbacks)

**3.2 Method Arguments (104 issues, ARG002):**
- MUST review abstract base class implementations
- MUST prefix with `_` where required by parent class signature
- MUST remove where method signature can be simplified

**3.3 Lambda Arguments (59 issues, ARG005):**
- MUST review lambda expressions
- MUST use `_` instead of named variable for unused lambda args

**3.4 Static Method Arguments (1 issue, ARG004):**
- MUST fix single static method issue

**3.5 Verification:**
- MUST run `ruff check packages/ --select ARG` and achieve zero violations or document all remaining with inline comments
- MUST ensure all tests still pass
- MUST update docstrings where function signatures change

#### 4. Commented Code Removal (79 issues)

**Policy:** Delete all commented-out code (version control preserves history)

**4.1 Systematic Removal:**
- MUST identify all 79 blocks: `ruff check packages/ tests/ --select ERA001`
- MUST delete each commented code block
- MUST preserve explanatory comments (non-code text)
- MUST NOT delete TODO/FIXME/NOTE comments

**4.2 Special Cases:**
- If commented code contains valuable context, MUST convert to proper documentation or issue tracker reference
- MUST review `packages/cli/src/aurora_cli/commands/doctor.py:114-117` (MCP checks) - create issue if feature needed later

**4.3 Verification:**
- MUST run `ruff check packages/ tests/ --select ERA001` and achieve zero violations
- MUST ensure no functionality lost (all necessary code is active)

---

## Non-Goals (Deferred to Phase 3)

1. **Missing Type Annotations (11,408 issues):** Too large for Phase 2, requires dedicated effort
2. **Print Statement Migration (867 issues):** Logging migration is lower priority than correctness
3. **Assert Statement Refactoring (2,036 issues):** Low risk, can be addressed later
4. **Magic Value Extraction (492 issues):** Code quality improvement, not critical
5. **Long Parameter Lists (69 issues):** Maintainability improvement, defer to Phase 3
6. **Performance Optimization Beyond Complexity:** No additional optimization work beyond complexity reduction

---

## Constraints

### Technical Constraints
- **No Breaking API Changes:** All public API signatures must remain backward compatible
- **Zero Test Regressions:** All existing tests must continue passing
- **Type Safety:** Must use proper type hints, no `# type: ignore` without justification
- **Performance Baseline:** Startup time must not regress beyond 3.0s total (current: ~1.835s import)

### Time Constraints
- **Phase 2A:** 2-3 days focused work
- **Phase 2B:** 2-3 days focused work
- **Total Phase 2:** Maximum 6 days

### Quality Constraints
- **Test Coverage:** New extracted functions must have 100% test coverage
- **Incremental Merges:** Phase 2A must merge before Phase 2B begins
- **Documentation:** Complex refactorings must update docstrings and comments
- **Benchmark Validation:** Performance benchmarks must run after each phase

---

## Success Metrics

### Phase 2A Success Criteria

**Type Errors (Blocker for completion):**
- [ ] Zero mypy errors in packages/context-code: `mypy packages/context-code/src --strict`
- [ ] Zero mypy errors in packages/soar: `mypy packages/soar/src --strict`
- [ ] Zero mypy errors in packages/core: `mypy packages/core/src --strict`
- [ ] All new None checks have corresponding test cases

**Complexity Reduction (Blocker for completion):**
- [ ] All top 10 functions (C90 > 15) reduced to ≤ 15
- [ ] 100% test coverage on newly extracted functions
- [ ] `make test` passes with zero failures
- [ ] Performance benchmarks maintained or improved:
  - `MAX_IMPORT_TIME ≤ 2.0s`
  - `MAX_TOTAL_STARTUP_TIME ≤ 3.0s`

**Quality Gates:**
- [ ] `make quality-check` passes (lint + type + test)
- [ ] No new TODO/FIXME comments without issue references
- [ ] All docstrings updated for refactored functions

### Phase 2B Success Criteria

**Unused Arguments (Blocker for completion):**
- [ ] Zero ARG001/ARG002/ARG005/ARG004 violations: `ruff check packages/ tests/ --select ARG`
- [ ] All intentionally unused arguments prefixed with `_`
- [ ] All removed arguments documented in commit messages

**Commented Code (Blocker for completion):**
- [ ] Zero ERA001 violations: `ruff check packages/ tests/ --select ERA001`
- [ ] All valuable context converted to documentation or issues
- [ ] No functionality lost (verified through test suite)

**Quality Gates:**
- [ ] `make test` passes with zero failures
- [ ] `make quality-check` passes
- [ ] Code review completed and approved

### Overall Phase 2 Success Criteria

**Quantitative:**
- Fixed: 47 type errors + 10 complex functions + 264 unused args + 79 commented blocks = **400 critical issues resolved**
- Remaining issues: 18,811 → 18,411 (2.1% additional progress)
- Type coverage in critical packages: context-code, soar, core at 100% mypy compliance

**Qualitative:**
- Codebase is easier to understand and modify
- Developer confidence in type safety increases
- Hot paths (CLI commands, SOAR pipeline) are more maintainable
- Technical debt visibly reduced

---

## Dependencies & Sequencing

### Phase 2A Internal Dependencies

1. **First:** Fix type errors in packages/context-code (foundation for soar)
2. **Second:** Fix type errors in packages/soar (depends on context-code types)
3. **Third:** Fix type errors in packages/core (minimal dependencies)
4. **Fourth:** Refactor complex functions (after types are solid)

**Rationale:** Type safety must be established before refactoring complex functions to avoid cascading type errors.

### Phase 2B Internal Dependencies

1. **First:** Remove commented code (no dependencies)
2. **Second:** Fix unused arguments (may depend on commented code removal revealing more unused args)

**Rationale:** Cleaning up commented code first provides clearer view of actual code paths.

### Cross-Phase Dependencies

- **Blocker:** Phase 2B cannot start until Phase 2A is merged and validated
- **Checkpoint:** Run full benchmark suite between phases
- **Validation:** Each phase requires separate PR review and approval

---

## Risk Mitigation

### High-Risk Areas

**1. Type Error Fixes (Medium Risk)**
- **Risk:** Fixing None handling could expose real bugs or change behavior
- **Mitigation:**
  - Add tests for all new None checks before fixing
  - Review with `git diff` to ensure only type annotations changed
  - Run integration tests, not just unit tests

**2. Complexity Refactoring (High Risk)**
- **Risk:** Breaking down complex functions could introduce bugs
- **Mitigation:**
  - Extract functions with pure logic first (no side effects)
  - Maintain 100% test coverage on extracted code
  - Use incremental refactoring: extract → test → extract → test
  - Keep original function as thin orchestrator

**3. Unused Argument Removal (Medium Risk)**
- **Risk:** Removing "unused" argument that's actually required by interface
- **Mitigation:**
  - Review all ARG002 issues carefully (method overrides)
  - Check for ABC/Protocol implementations
  - Prefix with `_` when uncertain

**4. Performance Regression (Low Risk)**
- **Risk:** Refactoring could slow down hot paths
- **Mitigation:**
  - Run benchmarks after each phase
  - Profile complex functions before/after with cProfile
  - Revert if regression > 5%

### Rollback Strategy

**Per-Phase Rollback:**
- Each phase is a separate branch and PR
- Can revert individual phase without affecting others
- Maintain baseline benchmarks for each phase

**Incremental Merge:**
- Phase 2A: Merge after validation
- Phase 2B: Merge after validation
- No "big bang" merge of all changes

---

## Testing Strategy

### Test Requirements

**For Type Errors:**
- Add test cases for all new None checks (e.g., `test_parse_handles_none_parser`)
- Add test cases for type consistency (e.g., `test_assessment_level_validation`)
- Run mypy in CI: `make type-check` must pass

**For Complexity Reduction:**
- Maintain existing test coverage for refactored functions
- Add unit tests for all newly extracted functions
- Add integration tests for CLI commands (headless, goals)
- Verify behavior equivalence with property-based tests where feasible

**For Unused Arguments:**
- Ensure all tests still pass after argument removal
- Add regression tests if removing argument revealed a bug

**For Commented Code:**
- No new tests required (just deletion)
- Verify all tests still pass (no hidden dependencies)

### Regression Testing

**Before Phase 2A:**
```bash
make test > phase2a_baseline_tests.txt
make benchmark-startup > phase2a_baseline_perf.txt
```

**After Phase 2A:**
```bash
make test > phase2a_final_tests.txt
make benchmark-startup > phase2a_final_perf.txt
diff phase2a_baseline_tests.txt phase2a_final_tests.txt
diff phase2a_baseline_perf.txt phase2a_final_perf.txt
```

**Repeat for Phase 2B**

---

## Implementation Plan

### Phase 2A: Critical Fixes (Days 1-3)

**Day 1: Type Errors - packages/context-code**
- [ ] Run `make type-check` to confirm current state
- [ ] Fix `languages/typescript.py:94` (None check)
- [ ] Fix `semantic/embedding_provider.py:252` (None check)
- [ ] Fix `semantic/hybrid_retriever.py:493,610` (dict type params)
- [ ] Add type annotations to `__init__.py:20`
- [ ] Add tests for None handling
- [ ] Verify: `mypy packages/context-code/src --strict` passes

**Day 2: Type Errors - packages/soar**
- [ ] Fix `phases/assess.py:415,429` (complexity scoring types)
- [ ] Fix `phases/retrieve.py:126` (Store compatibility)
- [ ] Fix `phases/assess.py:55,57,871` (dict type params)
- [ ] Fix `phases/collect.py:35,46,94` (dict types + annotations)
- [ ] Fix `orchestrator.py:209,220,234,1618` (helper annotations)
- [ ] Add tests for type consistency
- [ ] Verify: `mypy packages/soar/src --strict` passes

**Day 2-3: Type Errors - packages/core + Complexity Reduction**
- [ ] Fix remaining core type errors
- [ ] Run full type-check: `make type-check` passes
- [ ] Identify top 10 complex functions: `ruff check packages/ --select C90 | grep "C901" | sort -k3 -n -r | head -10`
- [ ] Refactor `headless_command` (C90=53 → ≤15)
- [ ] Refactor `goals_command` (C90=26 → ≤15)
- [ ] Refactor remaining top 8 functions
- [ ] Add tests for all extracted functions
- [ ] Verify: `ruff check packages/ --select C90` shows all ≤15
- [ ] Run benchmarks: `make benchmark-startup`
- [ ] **Checkpoint:** Merge Phase 2A PR

### Phase 2B: Cleanup (Days 4-6)

**Day 4: Commented Code Removal**
- [ ] Identify all blocks: `ruff check packages/ tests/ --select ERA001 > commented_code.txt`
- [ ] Review each block for valuable context
- [ ] Convert valuable context to documentation/issues
- [ ] Delete all 79 commented code blocks
- [ ] Verify: `ruff check packages/ tests/ --select ERA001` shows zero
- [ ] Run tests: `make test`

**Day 5-6: Unused Arguments**
- [ ] Identify all unused args: `ruff check packages/ tests/ --select ARG > unused_args.txt`
- [ ] Categorize: dead code vs interface requirement
- [ ] Remove obvious dead code (update callers)
- [ ] Prefix interface requirements with `_`
- [ ] Update docstrings where signatures changed
- [ ] Verify: `ruff check packages/ tests/ --select ARG` shows zero
- [ ] Run tests: `make test`
- [ ] Run benchmarks: `make benchmark-startup`
- [ ] **Checkpoint:** Merge Phase 2B PR

**Day 6: Final Validation**
- [ ] Run full quality check: `make quality-check`
- [ ] Run full benchmark suite: `make benchmark`
- [ ] Compare baseline vs final performance
- [ ] Update CODE_QUALITY_REPORT.md with Phase 2 results
- [ ] Document lessons learned

---

## Open Questions

1. **Type Error Severity:** Do any of the 47 type errors correspond to known production bugs? (Investigation during Day 1)

2. **Complexity Targets:** Should we set stricter targets (C90 ≤ 10) for CLI entry points like `headless_command` and `goals_command`? (Decision during refactoring)

3. **Unused Arguments in Tests:** Should test fixtures with unused arguments be treated differently than production code? (Current policy: prefix with `_`)

4. **Performance Baseline:** Should we add complexity metrics to performance regression tests? (e.g., fail if any function exceeds C90 > 20)

5. **mypy Strict Mode:** Should Phase 2A enable `--strict` mode in CI permanently, or just validate it passes? (Decision after Phase 2A completion)

6. **Refactoring Patterns:** Should we establish coding standards for common patterns discovered during complexity reduction? (e.g., "Always extract validation logic into `_validate_*` functions")

---

## Appendix: Commands Reference

### Analysis Commands

```bash
# Identify type errors
make type-check
mypy packages/context-code/src --strict
mypy packages/soar/src --strict
mypy packages/core/src --strict

# Identify complex functions (top 10)
ruff check packages/ --select C90 | grep "C901" | sort -k3 -n -r | head -10

# Identify unused arguments
ruff check packages/ tests/ --select ARG > unused_args.txt

# Identify commented code
ruff check packages/ tests/ --select ERA001 > commented_code.txt
```

### Execution Commands

```bash
# Run quality checks
make quality-check  # lint + type + test
make lint           # ruff check
make type-check     # mypy
make test           # pytest

# Run benchmarks
make benchmark-startup      # Startup time benchmarks
make benchmark-soar         # SOAR-specific benchmarks
make benchmark              # Full benchmark suite

# Fix auto-fixable issues
ruff check packages/ tests/ --select ARG --fix  # Some unused args auto-fixable
ruff check packages/ tests/ --select ERA001 --fix  # Some commented code auto-fixable
```

### Validation Commands

```bash
# Verify Phase 2A completion
make type-check  # Must pass
ruff check packages/ --select C90 | grep -E "C90[12][0-9]|C90[3-9][0-9]"  # Must be empty
make test  # Must pass
make benchmark-startup  # Must not regress

# Verify Phase 2B completion
ruff check packages/ tests/ --select ARG  # Must show zero violations
ruff check packages/ tests/ --select ERA001  # Must show zero violations
make test  # Must pass
make quality-check  # Must pass
```

---

## Success Definition

**Phase 2 is complete when:**

1. ✅ All 47 type errors fixed and `make type-check` passes
2. ✅ Top 10 complex functions reduced to C90 ≤ 15
3. ✅ All 264 unused arguments either removed or prefixed with `_`
4. ✅ All 79 commented code blocks deleted
5. ✅ All tests passing: `make test`
6. ✅ Performance maintained: `make benchmark-startup` ≤ 3.0s total
7. ✅ Quality gates passed: `make quality-check`
8. ✅ Both Phase 2A and Phase 2B PRs merged to main
9. ✅ CODE_QUALITY_REPORT.md updated with results
10. ✅ Zero regressions in functionality or performance

**Quantitative Impact:**
- Issues fixed: 400 (2.1% additional progress)
- Total progress: 5,078 / 23,489 = 21.6%
- Critical issues remaining: 0 type errors, 0 C90 > 15 functions
- Maintainability: Significantly improved in hot paths

**Qualitative Impact:**
- Type safety enforced in critical packages
- CLI commands easier to understand and modify
- SOAR pipeline complexity reduced
- Codebase ready for Phase 3 (type annotation coverage)
