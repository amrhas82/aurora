#!/bin/bash
# Test ID: test_16_box_drawing_format.sh
# Expected: Box-drawing format appears in --show-scores output

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Test configuration
TEST_NAME="Box-Drawing Format Display"
QUERY="chunk"
LIMIT=3

echo "Running: $TEST_NAME"

# Execute search with --show-scores
OUTPUT=$(aur mem search "$QUERY" --show-scores --limit $LIMIT 2>&1 || true)

# Check for box-drawing characters
PASS_COUNT=0
TOTAL_CHECKS=7

# Check for top-left corner
if echo "$OUTPUT" | grep -q "┌"; then
    echo "  ✓ Found top-left corner (┌)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing top-left corner (┌)"
fi

# Check for vertical line
if echo "$OUTPUT" | grep -q "│"; then
    echo "  ✓ Found vertical line (│)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing vertical line (│)"
fi

# Check for branch character
if echo "$OUTPUT" | grep -q "├"; then
    echo "  ✓ Found branch character (├)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing branch character (├)"
fi

# Check for bottom-left corner
if echo "$OUTPUT" | grep -q "└"; then
    echo "  ✓ Found bottom-left corner (└)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing bottom-left corner (└)"
fi

# Check for horizontal line
if echo "$OUTPUT" | grep -q "─"; then
    echo "  ✓ Found horizontal line (─)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing horizontal line (─)"
fi

# Check for "Final Score:" header
if echo "$OUTPUT" | grep -q "Final Score:"; then
    echo "  ✓ Found 'Final Score:' header"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing 'Final Score:' header"
fi

# Check for individual score lines (BM25, Semantic, Activation)
if echo "$OUTPUT" | grep -q "BM25:" && echo "$OUTPUT" | grep -q "Semantic:" && echo "$OUTPUT" | grep -q "Activation:"; then
    echo "  ✓ Found all score component lines (BM25, Semantic, Activation)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "  ✗ Missing score component lines"
fi

# Validate results
if [ $PASS_COUNT -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}✅ PASS: $TEST_NAME${NC}"
    echo "All $TOTAL_CHECKS checks passed"
    exit 0
else
    echo -e "${RED}❌ FAIL: $TEST_NAME${NC}"
    echo "Passed $PASS_COUNT/$TOTAL_CHECKS checks"
    echo ""
    echo "Output preview:"
    echo "$OUTPUT" | head -20
    exit 1
fi
