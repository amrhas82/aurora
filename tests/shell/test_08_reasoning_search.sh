#!/usr/bin/env bash
# Shell Test ST-08: Reasoning Chunk Search
# Validates that reasoning chunks can be searched (if they exist)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "ST-08: Testing reasoning chunk search..."

# This test is a placeholder since reasoning chunks are created by SOAR pipeline
# For now, just verify that search doesn't crash when looking for reasoning patterns

cd "$PROJECT_ROOT"

# Search for a reasoning pattern (may return 0 results, which is OK)
aur mem search "decompose query into subgoals" --limit 3 2>&1 | tee /tmp/st08_output.txt

# Validate that search completed without errors
if grep -qi "results\|No results\|Found" /tmp/st08_output.txt; then
    echo "✅ ST-08 PASSED: Reasoning search executed without errors"
    rm -f /tmp/st08_output.txt
    exit 0
else
    echo "❌ ST-08 FAILED: Search did not complete properly"
    cat /tmp/st08_output.txt
    rm -f /tmp/st08_output.txt
    exit 1
fi
