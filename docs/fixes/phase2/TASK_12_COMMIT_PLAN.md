# Task 12 Comment Removal - Commit Plan

**Status:** Ready to execute when baseline completes
**Stash:** stash@{0} - "Task 12 comment removal - to re-apply after baseline"
**Total Files:** 40 changed (13 packages, 27 tests)

---

## Overview

All changes are currently stashed. When baseline completes, we'll:
1. Pop the stash
2. Apply changes in 5 organized commits (Tasks 12.4-12.8)
3. Run validation (Task 12.9)

---

## Task 12.4: Delete commented code in packages/cli

**Files (6):**
```
packages/cli/src/aurora_cli/commands/doctor.py
packages/cli/src/aurora_cli/concurrent_executor.py
packages/cli/src/aurora_cli/escalation.py
packages/cli/src/aurora_cli/memory_manager.py
packages/cli/src/aurora_cli/planning/decompose.py
packages/cli/src/aurora_cli/policies/engine.py
```

**Commands:**
```bash
git add packages/cli/src/aurora_cli/commands/doctor.py
git add packages/cli/src/aurora_cli/concurrent_executor.py
git add packages/cli/src/aurora_cli/escalation.py
git add packages/cli/src/aurora_cli/memory_manager.py
git add packages/cli/src/aurora_cli/planning/decompose.py
git add packages/cli/src/aurora_cli/policies/engine.py
git commit -m "fix: remove commented code in packages/cli (Task 12.4)

Removed deprecated MCP implementation and other commented-out code:
- doctor.py: MCP tool checks (deprecated, migration documented)
- concurrent_executor.py: Old execution logic
- escalation.py: Debug/alternative implementations
- memory_manager.py: Legacy patterns
- decompose.py: Old decomposition approaches
- engine.py: Alternative policy logic

Verified with: ruff check packages/cli/ --select ERA001
"
```

**Verify:**
```bash
ruff check packages/cli/ --select ERA001
# Expected: No violations (or reduced count)
```

---

## Task 12.5: Delete commented code in packages/soar

**Files (1):**
```
packages/soar/tests/test_orchestrator.py
```

**Commands:**
```bash
git add packages/soar/tests/test_orchestrator.py
git commit -m "fix: remove commented code in packages/soar (Task 12.5)

Removed 4 commented assert statements in test_orchestrator.py.
These were old test assertions that are no longer relevant.

Verified with: ruff check packages/soar/ --select ERA001
"
```

**Verify:**
```bash
ruff check packages/soar/ --select ERA001
# Expected: 0 violations
```

---

## Task 12.6: Delete commented code in packages/context-code

**Files (3):**
```
packages/context-code/src/aurora_context_code/git.py
packages/context-code/src/aurora_context_code/knowledge_parser.py
packages/context-code/src/aurora_context_code/languages/python.py
```

**Commands:**
```bash
git add packages/context-code/src/aurora_context_code/git.py
git add packages/context-code/src/aurora_context_code/knowledge_parser.py
git add packages/context-code/src/aurora_context_code/languages/python.py
git commit -m "fix: remove commented code in packages/context-code (Task 12.6)

Removed 4 example/documentation comments flagged as code:
- git.py: Example command patterns
- knowledge_parser.py: Old parsing examples
- python.py: Legacy extraction patterns

Verified with: ruff check packages/context-code/ --select ERA001
"
```

**Verify:**
```bash
ruff check packages/context-code/ --select ERA001
# Expected: 0 violations
```

---

## Task 12.7: Delete commented code in remaining packages

**Files (1):**
```
packages/core/src/aurora_core/activation/base_level.py
```

**Commands:**
```bash
git add packages/core/src/aurora_core/activation/base_level.py
git commit -m "fix: remove commented code in remaining packages (Task 12.7)

Removed commented code in packages/core:
- base_level.py: Old activation calculation logic

Verified with: ruff check packages/ --select ERA001
"
```

**Verify:**
```bash
ruff check packages/ --select ERA001
# Expected: 0 violations in packages/
```

---

## Task 12.8: Delete commented code in tests/

**Files (27):**
```
tests/archive/performance/test_hybrid_retrieval_precision.py
tests/archive/performance/test_soar_benchmarks.py
tests/e2e/test_e2e_complexity_assessment.py
tests/integration/cli/test_doctor_mcp_checks.py
tests/integration/cli/test_headless_multi_tool.py
tests/integration/core/store/test_sqlite_schema_migration.py
tests/integration/test_actr_retrieval_precision.py
tests/integration/test_integration_auto_escalation.py
tests/integration/test_integration_budget_enforcement.py
tests/integration/test_integration_git_signal_extraction.py
tests/integration/test_semantic_retrieval.py
tests/performance/test_concurrent_execution_benchmarks.py
tests/performance/test_decomposition_cache_benchmarks.py
tests/unit/cli/test_concurrent_edge_cases.py
tests/unit/cli/test_concurrent_executor.py
tests/unit/cli/test_conflict_detection_resolution.py
tests/unit/cli/test_resource_isolation.py
tests/unit/cli/test_tool_orchestrator.py
tests/unit/cli/test_tool_providers.py
tests/unit/core/activation/test_actr_literature_validation.py
tests/unit/core/activation/test_base_level.py
tests/unit/core/activation/test_context_boost.py
tests/unit/core/activation/test_spreading.py
tests/unit/core/test_conversation_logger.py
tests/unit/reasoning/test_verify.py
tests/unit/soar/test_corpus_assess.py
tests/unit/spawner/test_recovery_scenarios.py
```

**Commands:**
```bash
git add tests/archive/performance/test_hybrid_retrieval_precision.py
git add tests/archive/performance/test_soar_benchmarks.py
git add tests/e2e/test_e2e_complexity_assessment.py
git add tests/integration/cli/test_doctor_mcp_checks.py
git add tests/integration/cli/test_headless_multi_tool.py
git add tests/integration/core/store/test_sqlite_schema_migration.py
git add tests/integration/test_actr_retrieval_precision.py
git add tests/integration/test_integration_auto_escalation.py
git add tests/integration/test_integration_budget_enforcement.py
git add tests/integration/test_integration_git_signal_extraction.py
git add tests/integration/test_semantic_retrieval.py
git add tests/performance/test_concurrent_execution_benchmarks.py
git add tests/performance/test_decomposition_cache_benchmarks.py
git add tests/unit/cli/test_concurrent_edge_cases.py
git add tests/unit/cli/test_concurrent_executor.py
git add tests/unit/cli/test_conflict_detection_resolution.py
git add tests/unit/cli/test_resource_isolation.py
git add tests/unit/cli/test_tool_orchestrator.py
git add tests/unit/cli/test_tool_providers.py
git add tests/unit/core/activation/test_actr_literature_validation.py
git add tests/unit/core/activation/test_base_level.py
git add tests/unit/core/activation/test_context_boost.py
git add tests/unit/core/activation/test_spreading.py
git add tests/unit/core/test_conversation_logger.py
git add tests/unit/reasoning/test_verify.py
git add tests/unit/soar/test_corpus_assess.py
git add tests/unit/spawner/test_recovery_scenarios.py

git commit -m "fix: remove commented code in tests/ (Task 12.8)

Removed 57 documentation/example comments across 27 test files.
These were primarily:
- Old test assertions
- Example usage patterns
- Debugging statements
- Alternative test implementations

Verified with: ruff check tests/ --select ERA001
"
```

**Verify:**
```bash
ruff check tests/ --select ERA001
# Expected: 0 violations
```

---

## Task 12.9: Validate No Functionality Lost

**After all commits, run validation:**
```bash
make test > phase2b_validation_tests.txt
```

**Compare with baseline:**
```bash
# Extract summaries
grep -E "passed|failed|skipped" phase2b_baseline_tests.txt | tail -1
grep -E "passed|failed|skipped" phase2b_validation_tests.txt | tail -1

# Count changes
diff <(grep "FAILED" phase2b_baseline_tests.txt | cut -d: -f1-2 | sort) \
     <(grep "FAILED" phase2b_validation_tests.txt | cut -d: -f1-2 | sort)
```

**Expected:** Same pass/fail counts (comment removal should not affect functionality)

---

## Task 12.10: Final Verification

**Commands:**
```bash
ruff check packages/ tests/ --select ERA001
```

**Expected:** All checks passed!

---

## Quick Reference Commands

### When Baseline Completes:

```bash
# 1. Pop stash
git stash pop

# 2. Verify changes
git status --short

# 3. Follow commit sequence above (Tasks 12.4-12.8)

# 4. Run validation
make test > phase2b_validation_tests.txt

# 5. Compare results
diff <(tail -20 phase2b_baseline_tests.txt) <(tail -20 phase2b_validation_tests.txt)
```

---

## Rollback Plan (If Needed)

If validation shows new failures:

```bash
# Reset to before changes
git reset --hard cceaf4b

# Re-stash if needed
git stash apply stash@{0}

# Investigate specific failures
# Fix issues
# Re-apply with fixes
```

---

**Prepared:** 2026-01-23 10:25
**Ready to execute when:** Baseline test completes (ETA ~13:00-14:00)
