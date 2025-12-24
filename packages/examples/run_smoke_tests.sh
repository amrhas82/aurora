#!/bin/bash
#
# Master Smoke Test Runner
#
# Executes all smoke tests sequentially and reports results in a summary table.
# Exit codes: 0 if all non-skipped tests pass, 1 if any test fails
#

set -e  # Exit on error (but we'll catch test failures)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "===== AURORA SMOKE TEST SUITE ====="
echo "Project root: ${PROJECT_ROOT}"
echo ""

# Initialize counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Array to store test results
declare -A TEST_RESULTS
declare -A TEST_STATUS

# Function to run a single test
run_test() {
    local test_name="$1"
    local test_script="$2"

    echo "Running: ${test_name}..."

    # Run the test and capture exit code
    if python3 "${test_script}" > /tmp/smoke_test_$$.log 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi

    # Check the output for SKIP indicator
    if grep -q "⊗.*SKIP" /tmp/smoke_test_$$.log; then
        TEST_RESULTS["${test_name}"]="SKIP"
        TEST_STATUS["${test_name}"]="⊗"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    elif [ $exit_code -eq 0 ]; then
        TEST_RESULTS["${test_name}"]="PASS"
        TEST_STATUS["${test_name}"]="✓"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        TEST_RESULTS["${test_name}"]="FAIL"
        TEST_STATUS["${test_name}"]="✗"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        # Show error output
        echo ""
        echo "Error output:"
        cat /tmp/smoke_test_$$.log
        echo ""
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    rm -f /tmp/smoke_test_$$.log
}

# Change to project root
cd "${PROJECT_ROOT}"

# Run each smoke test
run_test "Memory Store" "${SCRIPT_DIR}/smoke_test_memory.py"
run_test "SOAR Orchestrator" "${SCRIPT_DIR}/smoke_test_soar.py"
run_test "LLM Client" "${SCRIPT_DIR}/smoke_test_llm.py"

# Display summary table
echo ""
echo "===== SMOKE TEST RESULTS ====="
printf "%-20s %s\n" "Memory Store:" "${TEST_STATUS[Memory Store]} ${TEST_RESULTS[Memory Store]}"
printf "%-20s %s\n" "SOAR Orchestrator:" "${TEST_STATUS[SOAR Orchestrator]} ${TEST_RESULTS[SOAR Orchestrator]}"
printf "%-20s %s\n" "LLM Client:" "${TEST_STATUS[LLM Client]} ${TEST_RESULTS[LLM Client]}"
echo "=============================="
echo ""

# Display summary counts
echo "Summary:"
echo "  Tests run:     ${TESTS_RUN}"
echo "  Tests passed:  ${TESTS_PASSED}"
echo "  Tests failed:  ${TESTS_FAILED}"
echo "  Tests skipped: ${TESTS_SKIPPED}"
echo ""

# Exit with appropriate code
if [ ${TESTS_FAILED} -gt 0 ]; then
    echo -e "${RED}FAILED${NC}: ${TESTS_FAILED} test(s) failed"
    exit 1
elif [ ${TESTS_PASSED} -eq 0 ] && [ ${TESTS_SKIPPED} -eq ${TESTS_RUN} ]; then
    echo -e "${YELLOW}ALL SKIPPED${NC}: All tests were skipped (no API key?)"
    exit 0
else
    echo -e "${GREEN}SUCCESS${NC}: All tests passed (${TESTS_SKIPPED} skipped)"
    exit 0
fi
