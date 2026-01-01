#!/bin/bash
# Test ID: test_14_type_abbreviations.sh
# Expected: Type abbreviations display correctly in search results

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Execute search
OUTPUT=$(aur mem search "chunk" --limit 10 2>&1 || true)

# Validate: Output contains abbreviated types
HAS_ABBREV=false
for abbrev in "func" "meth" "class" "code" "know" "doc" "reas"; do
    if echo "$OUTPUT" | grep -q "$abbrev"; then
        HAS_ABBREV=true
        break
    fi
done

# Validate: Output does NOT contain full names (except in special contexts)
HAS_FULL_NAMES=false
# Check for "function", "method", "knowledge", "document" in Type column context
# We need to be careful not to match these words in content or file names
if echo "$OUTPUT" | grep -E '\s+(function|method|knowledge|document|reasoning)\s+' | grep -v "Filter\|Type\|help" > /dev/null 2>&1; then
    HAS_FULL_NAMES=true
fi

if [ "$HAS_ABBREV" = true ] && [ "$HAS_FULL_NAMES" = false ]; then
    echo -e "${GREEN}✅ PASS: test_14_type_abbreviations${NC}"
    echo "   Found abbreviated types in output"
    exit 0
else
    echo -e "${RED}❌ FAIL: test_14_type_abbreviations${NC}"
    echo "   Expected: Abbreviated types (func, meth, class, code, know, doc, reas)"
    echo "   Expected: NO full type names (function, method, knowledge, document, reasoning)"
    echo "   Has abbreviations: $HAS_ABBREV"
    echo "   Has full names: $HAS_FULL_NAMES"
    echo ""
    echo "Output:"
    echo "$OUTPUT"
    exit 1
fi
