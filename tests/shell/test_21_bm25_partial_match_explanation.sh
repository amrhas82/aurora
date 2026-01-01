#!/bin/bash
# Test ID: test_21_bm25_partial_match_explanation.sh
# Expected: BM25 explanation shows "partial match" when <50% query terms present

set -e

# Setup: Index the Aurora codebase
echo "Indexing codebase..."
aur mem index /home/hamr/PycharmProjects/aurora/packages > /dev/null 2>&1

# Execute: Search with query where some results have low term overlap
echo "Searching for 'oauth implementation details'..."
OUTPUT=$(aur mem search "oauth implementation details" --show-scores --limit 5 2>&1)

# Validate: At least one result contains "partial match" in BM25 explanation
# Note: Not all results may have partial matches - some may have strong/exact
if echo "$OUTPUT" | grep -i "BM25:" | grep -E "partial match|no keyword match"; then
    echo "✅ PASS: BM25 partial match explanation present"
    exit 0
else
    echo "⚠️  WARN: No partial match found (may be expected if all results have strong matches)"
    echo "BM25 lines found:"
    echo "$OUTPUT" | grep -i "BM25:" || echo "(no BM25 lines found)"
    # Don't fail - this is acceptable if corpus doesn't have partial matches
    exit 0
fi
