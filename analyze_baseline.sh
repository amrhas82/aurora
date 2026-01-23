#!/bin/bash
# Baseline Test Analysis Script
# Run this when baseline completes to understand failures

set -e

echo "=================================================="
echo "Phase 2B Baseline Analysis"
echo "=================================================="
echo ""

# Check baseline exists
if [ ! -f "phase2b_baseline_tests.txt" ]; then
    echo "❌ ERROR: phase2b_baseline_tests.txt not found"
    exit 1
fi

# Extract summary
echo "1. Test Summary"
echo "=================================================="
tail -50 phase2b_baseline_tests.txt | grep -E "passed|failed|skipped|error" | tail -5
echo ""

# Count by result type
echo "2. Result Counts"
echo "=================================================="
PASSED=$(grep "PASSED" phase2b_baseline_tests.txt | wc -l)
FAILED=$(grep "FAILED" phase2b_baseline_tests.txt | wc -l)
SKIPPED=$(grep "SKIPPED" phase2b_baseline_tests.txt | wc -l)
ERRORS=$(grep "ERROR" phase2b_baseline_tests.txt | wc -l)

echo "PASSED:  $PASSED"
echo "FAILED:  $FAILED"
echo "SKIPPED: $SKIPPED"
echo "ERRORS:  $ERRORS"
echo ""

# Failure rate
TOTAL=$((PASSED + FAILED + SKIPPED + ERRORS))
if [ $TOTAL -gt 0 ]; then
    FAIL_RATE=$(awk "BEGIN {printf \"%.1f\", ($FAILED / $TOTAL) * 100}")
    echo "Failure rate: $FAIL_RATE%"
fi
echo ""

# Categorize failures by test type
echo "3. Failures by Test Type"
echo "=================================================="
grep "FAILED" phase2b_baseline_tests.txt | grep -oE "tests/[^/]+/" | sort | uniq -c | sort -rn
echo ""

# Top 10 failing test files
echo "4. Top 10 Failing Test Files"
echo "=================================================="
grep "FAILED" phase2b_baseline_tests.txt | cut -d':' -f1 | sort | uniq -c | sort -rn | head -10
echo ""

# Check if failures are in files we're modifying
echo "5. Failures in Files We're Modifying (Task 12)"
echo "=================================================="
echo "Checking if any failures are in Task 12 target files..."

# Get list of files we're modifying from stash
MODIFIED_FILES=$(git stash show stash@{0} --name-only | grep "\.py$")

CONFLICTS=0
for file in $MODIFIED_FILES; do
    # Check if any failures mention this file
    if grep "FAILED.*$file" phase2b_baseline_tests.txt > /dev/null 2>&1; then
        echo "⚠️  CONFLICT: $file has failing tests"
        grep "FAILED.*$file" phase2b_baseline_tests.txt | head -3
        CONFLICTS=$((CONFLICTS + 1))
    fi
done

if [ $CONFLICTS -eq 0 ]; then
    echo "✅ No conflicts: None of our Task 12 files have failing tests"
else
    echo ""
    echo "⚠️  WARNING: $CONFLICTS Task 12 files have failing tests"
    echo "   This might complicate validation comparison"
fi
echo ""

# Check for patterns in failures
echo "6. Failure Patterns"
echo "=================================================="
echo "MCP-related failures:"
grep "FAILED.*mcp" phase2b_baseline_tests.txt | wc -l
echo ""

echo "Planning-related failures:"
grep "FAILED.*planning" phase2b_baseline_tests.txt | wc -l
echo ""

echo "SOAR-related failures:"
grep "FAILED.*soar" phase2b_baseline_tests.txt | wc -l
echo ""

echo "Spawn/parallel failures:"
grep "FAILED.*spawn" phase2b_baseline_tests.txt | wc -l
echo ""

# Check for import/initialization errors
echo "7. Import/Initialization Errors"
echo "=================================================="
grep -E "ImportError|ModuleNotFoundError|AttributeError.*import" phase2b_baseline_tests.txt | wc -l
echo ""

# Extract actual error messages for top failures
echo "8. Sample Error Messages (First 5 Failures)"
echo "=================================================="
grep "FAILED" phase2b_baseline_tests.txt | head -5 | while read line; do
    echo "---"
    echo "$line"
done
echo ""

# Decision matrix
echo "=================================================="
echo "9. Decision Matrix"
echo "=================================================="
echo ""

if [ $CONFLICTS -gt 0 ]; then
    echo "⚠️  RECOMMENDATION: INVESTIGATE CONFLICTS"
    echo ""
    echo "   $CONFLICTS files we're modifying have failing tests."
    echo "   Options:"
    echo "   A. Fix those specific failures first (safe)"
    echo "   B. Proceed carefully, document expected failures"
    echo "   C. Exclude those files from Task 12"
    echo ""
else
    echo "✅ RECOMMENDATION: PROCEED WITH TASK 12"
    echo ""
    echo "   No conflicts detected. Failures are in unrelated areas."
    echo "   Our comment removal should not affect existing failures."
    echo ""
fi

if [ $FAILED -gt 1000 ]; then
    echo "⚠️  HIGH FAILURE COUNT: $FAILED failures"
    echo "   Consider:"
    echo "   - Are these all pre-existing?"
    echo "   - Should we stabilize tests before Phase 2B?"
    echo "   - Can we proceed with this baseline?"
    echo ""
elif [ $FAILED -gt 500 ]; then
    echo "⚠️  MODERATE FAILURE COUNT: $FAILED failures"
    echo "   Acceptable baseline, but monitor closely."
    echo ""
else
    echo "✅ REASONABLE FAILURE COUNT: $FAILED failures"
    echo "   Good baseline for comparison."
    echo ""
fi

# Generate failure report
echo "10. Generating Detailed Failure Report"
echo "=================================================="
grep "FAILED" phase2b_baseline_tests.txt > phase2b_baseline_failures.txt
echo "✅ Detailed failures saved to: phase2b_baseline_failures.txt"
echo "   Lines: $(wc -l < phase2b_baseline_failures.txt)"
echo ""

# Summary recommendation
echo "=================================================="
echo "FINAL RECOMMENDATION"
echo "=================================================="
echo ""

if [ $CONFLICTS -eq 0 ] && [ $FAILED -lt 1000 ]; then
    echo "✅ PROCEED: Execute Task 12"
    echo ""
    echo "Next steps:"
    echo "1. Review this analysis"
    echo "2. Run: ./execute_task12.sh"
    echo "3. Run: nohup make test > phase2b_validation_tests.txt 2>&1 &"
    echo "4. Compare: baseline vs validation"
    echo ""
else
    echo "⚠️  CAUTION: Review conflicts and failure count"
    echo ""
    echo "Next steps:"
    echo "1. Review conflicts in detail"
    echo "2. Decide: Fix first, proceed carefully, or adjust scope"
    echo "3. Document decision"
    echo "4. Then proceed with Task 12"
    echo ""
fi

echo "=================================================="
echo "Analysis complete!"
echo "=================================================="
