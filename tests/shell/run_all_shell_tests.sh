#!/bin/bash
# Run all BM25 shell tests
# Usage: bash tests/shell/run_all_shell_tests.sh

set -e  # Exit on first failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASSED=0
FAILED=0
FAILED_TESTS=()

echo "========================================"
echo "Running All BM25 Shell Tests"
echo "========================================"
echo ""

for test_file in "$SCRIPT_DIR"/test_*.sh; do
    test_name=$(basename "$test_file")
    echo "Running: $test_name"

    if bash "$test_file"; then
        echo "✓ PASS: $test_name"
        ((PASSED++))
    else
        echo "✗ FAIL: $test_name"
        ((FAILED++))
        FAILED_TESTS+=("$test_name")
    fi
    echo ""
done

echo "========================================"
echo "Shell Test Summary"
echo "========================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Failed tests:"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo "  - $failed_test"
    done
    echo ""
    exit 1
fi

echo ""
echo "✓ All shell tests passed!"
exit 0
