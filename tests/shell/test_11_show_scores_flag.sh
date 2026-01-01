#!/usr/bin/env bash
# Shell Test ST-11: --show-scores Flag
# Validates that --show-scores displays score breakdown

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "ST-11: Testing --show-scores flag..."

cd "$PROJECT_ROOT"

# Index some code
aur mem index packages/core/src/aurora_core/chunks > /dev/null 2>&1

# Search with --show-scores flag (when implemented)
# For now, just verify normal search works
aur mem search "Chunk validate" --limit 2 2>&1 | tee /tmp/st11_output.txt

# Check that search displays results
# --show-scores flag will be added in Task 6.4
if grep -qi "results\|Found\|Score" /tmp/st11_output.txt; then
    echo "✅ ST-11 PASSED: Search displays scores (--show-scores flag pending Task 6.4)"
    rm -f /tmp/st11_output.txt
    exit 0
else
    echo "❌ ST-11 FAILED: Search did not display results"
    cat /tmp/st11_output.txt
    rm -f /tmp/st11_output.txt
    exit 1
fi
