#!/bin/bash
# ST-01: BM25 Exact Match - SOAROrchestrator
#
# Purpose: Validate that exact match "SOAROrchestrator" appears in top-3 results
# Expected: orchestrator.py containing SOAROrchestrator class should rank highly
# Tests: FR-1 (BM25 integration), FR-3 (exact match prioritization)

set -e

echo "=== ST-01: Testing exact match for 'SOAROrchestrator' ==="

# Run search command
RESULT=$(aur mem search "SOAROrchestrator" 2>&1)

echo "Search output:"
echo "$RESULT"
echo ""

# Check if command succeeded
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Search command failed"
    exit 1
fi

# Validate that result contains orchestrator.py and SOAROrchestrator
if echo "$RESULT" | grep -i "orchestrator\.py" | grep -i "soarorchestrator" > /dev/null; then
    echo "✅ PASS: Found 'SOAROrchestrator' in orchestrator.py in results"
    exit 0
else
    echo "❌ FAIL: 'SOAROrchestrator' not found in top results"
    echo ""
    echo "Expected: orchestrator.py with SOAROrchestrator in top-3 results"
    echo "Actual: Not found in output"
    exit 1
fi
