#!/bin/bash
# Task 12 Comment Removal - Execution Script
# Run this when baseline test completes

set -e  # Exit on error

echo "=================================================="
echo "Task 12: Comment Removal Execution"
echo "=================================================="
echo ""

# Verify we're on the right branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "feature/phase2b-cleanup" ]; then
    echo "❌ ERROR: Not on feature/phase2b-cleanup branch"
    echo "Current branch: $BRANCH"
    exit 1
fi

echo "✅ On correct branch: $BRANCH"
echo ""

# Verify baseline exists
if [ ! -f "phase2b_baseline_tests.txt" ]; then
    echo "❌ ERROR: phase2b_baseline_tests.txt not found"
    exit 1
fi

echo "✅ Baseline test results found"
echo ""

# Pop stash
echo "📦 Restoring changes from stash..."
git stash pop
echo ""

# Verify changes restored
echo "📋 Verifying changes..."
CHANGED_FILES=$(git status --short | wc -l)
echo "   Changed files: $CHANGED_FILES"

if [ "$CHANGED_FILES" -lt 30 ]; then
    echo "❌ WARNING: Expected ~40 changed files, got $CHANGED_FILES"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Task 12.4: packages/cli
echo "=================================================="
echo "Task 12.4: Remove commented code in packages/cli"
echo "=================================================="
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

echo "✅ Task 12.4 committed"
ruff check packages/cli/ --select ERA001 2>&1 | head -5
echo ""

# Task 12.5: packages/soar
echo "=================================================="
echo "Task 12.5: Remove commented code in packages/soar"
echo "=================================================="
git add packages/soar/tests/test_orchestrator.py

git commit -m "fix: remove commented code in packages/soar (Task 12.5)

Removed 4 commented assert statements in test_orchestrator.py.
These were old test assertions that are no longer relevant.

Verified with: ruff check packages/soar/ --select ERA001
"

echo "✅ Task 12.5 committed"
ruff check packages/soar/ --select ERA001 2>&1 | head -5
echo ""

# Task 12.6: packages/context-code
echo "=================================================="
echo "Task 12.6: Remove commented code in packages/context-code"
echo "=================================================="
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

echo "✅ Task 12.6 committed"
ruff check packages/context-code/ --select ERA001 2>&1 | head -5
echo ""

# Task 12.7: packages/core
echo "=================================================="
echo "Task 12.7: Remove commented code in remaining packages"
echo "=================================================="
git add packages/core/src/aurora_core/activation/base_level.py

git commit -m "fix: remove commented code in remaining packages (Task 12.7)

Removed commented code in packages/core:
- base_level.py: Old activation calculation logic

Verified with: ruff check packages/ --select ERA001
"

echo "✅ Task 12.7 committed"
ruff check packages/ --select ERA001 2>&1 | head -5
echo ""

# Task 12.8: tests/
echo "=================================================="
echo "Task 12.8: Remove commented code in tests/"
echo "=================================================="
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

echo "✅ Task 12.8 committed"
ruff check tests/ --select ERA001 2>&1 | head -5
echo ""

# Task 12.10: Final verification
echo "=================================================="
echo "Task 12.10: Final ERA001 verification"
echo "=================================================="
ruff check packages/ tests/ --select ERA001

if [ $? -eq 0 ]; then
    echo "✅ All ERA001 violations cleared!"
else
    echo "⚠️  Some ERA001 violations remain - review above"
fi
echo ""

# Show commit log
echo "=================================================="
echo "Commits created:"
echo "=================================================="
git log --oneline -5
echo ""

# Summary
echo "=================================================="
echo "Task 12 Complete! Next steps:"
echo "=================================================="
echo "1. Review commits: git log -5 --stat"
echo "2. Run validation: make test > phase2b_validation_tests.txt"
echo "3. Compare results: diff phase2b_baseline_tests.txt phase2b_validation_tests.txt"
echo "4. If all good, proceed to Task 13 (unused arguments)"
echo ""
echo "To run validation now, execute:"
echo "  nohup make test > phase2b_validation_tests.txt 2>&1 &"
echo ""
