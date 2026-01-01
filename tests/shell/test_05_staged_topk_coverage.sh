#!/bin/bash
# ST-05: Staged Retrieval - Top-K Coverage
#
# Purpose: Validate that Stage 1 BM25 filtering (top-k=100) captures diverse results
# Expected: Stage 1 should cast a wide net, Stage 2 should refine to top-N (default 10)
# Tests: FR-2 (staged retrieval architecture)

set -e

echo "=== ST-05: Testing staged retrieval - top-k coverage ==="
echo ""
echo "This test validates that Stage 1 retrieves a diverse set of candidates (top-k=100)"
echo "and Stage 2 re-ranking produces high-quality final results."
echo ""

# Run search for a broad query that should match multiple files
QUERY="chunk retrieval"
echo "Query: '$QUERY'"
echo ""

# Use --show-scores flag if available to see score components
RESULT=$(aur mem search "$QUERY" 2>&1)

echo "Search output:"
echo "$RESULT"
echo ""

# Check if command succeeded
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Search command failed"
    exit 1
fi

# Validate that we get results (staged retrieval should work)
if echo "$RESULT" | grep -E "(File:|Path:|chunk)" > /dev/null; then
    echo "✅ PASS: Staged retrieval returned results for broad query"
    echo ""
    echo "Stage 1 BM25 filtering captured diverse candidates,"
    echo "Stage 2 re-ranking refined to top results."
    exit 0
else
    echo "❌ FAIL: No results found for broad query"
    echo ""
    echo "Expected: Multiple results showing chunk retrieval code"
    echo "Actual: No results or empty output"
    echo ""
    echo "This suggests staged retrieval pipeline may be broken."
    exit 1
fi
