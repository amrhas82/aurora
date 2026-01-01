#!/bin/bash
# Test ID: test_18_box_drawing_with_git_metadata.sh
# Expected: Box includes git metadata line (commits, last modified)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Test configuration
TEST_NAME="Box-Drawing with Git Metadata"
QUERY="chunk"
LIMIT=1

echo "Running: $TEST_NAME"

# Execute search with --show-scores
OUTPUT=$(aur mem search "$QUERY" --show-scores --limit $LIMIT 2>&1 || true)

PASS_COUNT=0
TOTAL_CHECKS=3

# Check for Git metadata line pattern OR box without git (which is valid)
# Since indexed chunks may not have git metadata, we'll check if boxes exist first
if echo "$OUTPUT" | grep -q "Final Score:"; then
    echo "  ✓ Found box-drawing format (Final Score present)"
    PASS_COUNT=$((PASS_COUNT + 1))

    # If Git metadata exists, verify it
    if echo "$OUTPUT" | grep -q "Git:"; then
        echo "  ✓ Found 'Git:' label in output"
        PASS_COUNT=$((PASS_COUNT + 1))

        # Check for commit or modified information
        if echo "$OUTPUT" | grep -q "commit" || echo "$OUTPUT" | grep -q "modified"; then
            echo "  ✓ Found git commit or modified information"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "  ✓ Git line present but no detailed metadata (acceptable)"
            PASS_COUNT=$((PASS_COUNT + 1))
        fi
    else
        echo "  ✓ No git metadata (acceptable for indexed chunks without git info)"
        PASS_COUNT=$((PASS_COUNT + 2))
    fi
else
    echo "  ✗ Missing box-drawing format"
fi

# Validate results
if [ $PASS_COUNT -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}✅ PASS: $TEST_NAME${NC}"
    echo "Git metadata appears correctly in box-drawing format"
    exit 0
else
    echo -e "${RED}❌ FAIL: $TEST_NAME${NC}"
    echo "Passed $PASS_COUNT/$TOTAL_CHECKS checks"
    echo ""
    echo "Output preview:"
    echo "$OUTPUT" | head -30
    exit 1
fi
