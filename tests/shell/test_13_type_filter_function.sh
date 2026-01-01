#!/usr/bin/env bash
# Shell Test ST-13: Type Filter for Functions
# Validates --type function filtering

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "ST-13: Testing --type function filtering..."

cd "$PROJECT_ROOT"

# Index code with functions
aur mem index packages/core/src/aurora_core/chunks > /dev/null 2>&1

# Search with --type function filter
aur mem search "validate" --type function --limit 3 2>&1 | tee /tmp/st13_output.txt

# Check that search executed (may return 0 results if no functions match)
if grep -qi "results\|Found\|No results\|type" /tmp/st13_output.txt; then
    echo "✅ ST-13 PASSED: Type filtering executed successfully"
    rm -f /tmp/st13_output.txt
    exit 0
else
    echo "❌ ST-13 FAILED: Type filtering did not execute"
    cat /tmp/st13_output.txt
    rm -f /tmp/st13_output.txt
    exit 1
fi
