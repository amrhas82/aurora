#!/bin/bash
# Test ID: test_20_bm25_strong_overlap_explanation.sh
# Expected: BM25 explanation shows "strong term overlap" when ≥50% query terms present

set -e

# Setup: Index the Aurora codebase
echo "Indexing codebase..."
aur mem index /home/hamr/PycharmProjects/aurora/packages > /dev/null 2>&1

# Execute: Search with multi-word query where 2/3 terms match
echo "Searching for 'user authentication flow'..."
OUTPUT=$(aur mem search "user authentication flow" --show-scores --limit 3 2>&1)

# Validate: At least one result contains "strong term overlap" in BM25 explanation
if echo "$OUTPUT" | grep -i "BM25:" | grep -q "strong term overlap"; then
    echo "✅ PASS: BM25 strong term overlap explanation present"
    exit 0
else
    echo "❌ FAIL: BM25 strong term overlap explanation missing"
    echo "Expected: At least one BM25 line to contain 'strong term overlap'"
    echo "Got:"
    echo "$OUTPUT" | grep -i "BM25:" || echo "(no BM25 lines found)"
    exit 1
fi
