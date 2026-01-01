#!/bin/bash
# Test ID: test_17_box_drawing_multiple_results.sh
# Expected: Each result has its own box (5 boxes total), properly separated

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Test configuration
TEST_NAME="Box-Drawing Multiple Results"
QUERY="test"
LIMIT=5

echo "Running: $TEST_NAME"

# Execute search with --show-scores
OUTPUT=$(aur mem search "$QUERY" --show-scores --limit $LIMIT 2>&1 || true)

# Count number of top-left corners (one per box - only count box headers, not table)
# Box headers start with "┌─" and are followed by filename
TOP_CORNER_COUNT=$(echo "$OUTPUT" | grep -c "^┌─" || echo "0")

# Count number of bottom corners (one per box footer - lines with only ─ between corners)
# Box footers have the pattern: └───...───┘ (only dashes between corners, no other characters)
# Table footer has other characters mixed in
BOTTOM_CORNER_COUNT=$(echo "$OUTPUT" | grep -E "^└─+┘$" -c || echo "0")

# Count number of "Final Score:" headers (one per result)
FINAL_SCORE_COUNT=$(echo "$OUTPUT" | grep -c "Final Score:" || echo "0")

PASS_COUNT=0
TOTAL_CHECKS=3

# Check if we have at least 3 boxes (may have fewer results than limit)
if [ "$TOP_CORNER_COUNT" -ge 3 ]; then
    echo "  ✓ Found $TOP_CORNER_COUNT top corners (expecting ≥3)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Found only $TOP_CORNER_COUNT top corners (expecting ≥3)"
fi

# Check if bottom corners match top corners
if [ "$BOTTOM_CORNER_COUNT" -eq "$TOP_CORNER_COUNT" ]; then
    echo "  ✓ Bottom corners match top corners ($BOTTOM_CORNER_COUNT)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Bottom corners ($BOTTOM_CORNER_COUNT) don't match top corners ($TOP_CORNER_COUNT)"
fi

# Check if Final Score count matches corner count
if [ "$FINAL_SCORE_COUNT" -eq "$TOP_CORNER_COUNT" ]; then
    echo "  ✓ Final Score headers match box count ($FINAL_SCORE_COUNT)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Final Score count ($FINAL_SCORE_COUNT) doesn't match boxes ($TOP_CORNER_COUNT)"
fi

# Validate results
if [ $PASS_COUNT -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}✅ PASS: $TEST_NAME${NC}"
    echo "Found $TOP_CORNER_COUNT properly formatted boxes"
    exit 0
else
    echo -e "${RED}❌ FAIL: $TEST_NAME${NC}"
    echo "Passed $PASS_COUNT/$TOTAL_CHECKS checks"
    echo ""
    echo "Statistics:"
    echo "  Top corners: $TOP_CORNER_COUNT"
    echo "  Bottom corners: $BOTTOM_CORNER_COUNT"
    echo "  Final Score headers: $FINAL_SCORE_COUNT"
    exit 1
fi
