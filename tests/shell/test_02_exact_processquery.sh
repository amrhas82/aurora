#!/bin/bash
# ST-02: BM25 Exact Match - process_query
#
# Purpose: Validate that exact match "process_query" appears in top-3 results
# Expected: Files containing process_query function/method should rank highly
# Tests: FR-1 (BM25 integration), FR-3 (snake_case tokenization)

set -e

echo "=== ST-02: Testing exact match for 'process_query' ==="

# Run search command
RESULT=$(aur mem search "process_query" 2>&1)

echo "Search output:"
echo "$RESULT"
echo ""

# Check if command succeeded
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Search command failed"
    exit 1
fi

# Validate that result contains process_query
if echo "$RESULT" | grep -i "process_query" > /dev/null; then
    echo "✅ PASS: Found 'process_query' in results"
    exit 0
else
    echo "❌ FAIL: 'process_query' not found in top results"
    echo ""
    echo "Expected: Files with process_query function in top-3 results"
    echo "Actual: Not found in output"
    exit 1
fi
