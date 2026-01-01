#!/bin/bash
# Test ID: test_19_bm25_exact_match_explanation.sh
# Expected: BM25 explanation shows "exact keyword match" for verbatim query term

set -e

# Setup: Index the Aurora codebase
echo "Indexing codebase..."
aur mem index /home/hamr/PycharmProjects/aurora/packages > /dev/null 2>&1

# Execute: Search for specific identifier with --show-scores
echo "Searching for 'authenticate'..."
OUTPUT=$(aur mem search "authenticate" --show-scores --limit 1 2>&1)

# Validate: Output contains "exact keyword match" in BM25 explanation
if echo "$OUTPUT" | grep -i "BM25:" | grep -q "exact keyword match"; then
    echo "✅ PASS: BM25 exact match explanation present"
    exit 0
else
    echo "❌ FAIL: BM25 exact match explanation missing"
    echo "Expected: BM25 line to contain 'exact keyword match on'"
    echo "Got:"
    echo "$OUTPUT" | grep -i "BM25:" || echo "(no BM25 line found)"
    exit 1
fi
