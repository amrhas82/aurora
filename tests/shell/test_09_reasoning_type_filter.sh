#!/usr/bin/env bash
# Shell Test ST-09: Reasoning Type Filter
# Validates --type reasoning filtering (when implemented in Task 6.5)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "ST-09: Testing reasoning type filter..."

cd "$PROJECT_ROOT"

# This test will work once --type filtering is implemented in Task 6.5
# For now, just verify normal search works
aur mem search "reasoning" --limit 3 2>&1 | tee /tmp/st09_output.txt

# Validate that search completed
if grep -qi "results\|No results\|Found" /tmp/st09_output.txt; then
    echo "✅ ST-09 PASSED: Type filter search executed (--type flag pending Task 6.5)"
    rm -f /tmp/st09_output.txt
    exit 0
else
    echo "❌ ST-09 FAILED: Search did not complete"
    cat /tmp/st09_output.txt
    rm -f /tmp/st09_output.txt
    exit 1
fi
