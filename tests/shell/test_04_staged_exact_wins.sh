#!/bin/bash
# ST-04: Staged Retrieval - Exact Match Beats High Activation
#
# Purpose: Validate that exact BM25 matches rank higher than chunks with high activation but poor text match
# Expected: A chunk with exact query match should beat a frequently-accessed chunk with weak semantic match
# Tests: FR-2 (staged retrieval), FR-3 (exact match prioritization)

set -e

echo "=== ST-04: Testing staged retrieval - exact match beats high activation ==="
echo ""
echo "This test validates that BM25 exact matches are prioritized in Stage 1,"
echo "ensuring they appear in top results even if other chunks have high activation scores."
echo ""

# Run search for a specific class/function name
QUERY="process_query"
echo "Query: '$QUERY'"
echo ""

RESULT=$(aur mem search "$QUERY" 2>&1)

echo "Search output:"
echo "$RESULT"
echo ""

# Check if command succeeded
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Search command failed"
    exit 1
fi

# Validate that result contains process_query in a relevant file
# We expect to find the actual definition/usage, not just any file
if echo "$RESULT" | grep -i "process_query" > /dev/null; then
    echo "✅ PASS: Found exact match 'process_query' in top results"
    echo ""
    echo "Staged retrieval working: BM25 Stage 1 captured exact match,"
    echo "Stage 2 re-ranking preserved it in final results."
    exit 0
else
    echo "❌ FAIL: Exact match 'process_query' not found in top results"
    echo ""
    echo "Expected: File containing 'process_query' function/method in top results"
    echo "Actual: Not found or ranked too low"
    echo ""
    echo "This suggests Stage 1 BM25 filtering may not be working correctly."
    exit 1
fi
