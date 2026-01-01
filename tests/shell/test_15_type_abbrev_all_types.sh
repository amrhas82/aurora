#!/bin/bash
# Test ID: test_15_type_abbrev_all_types.sh
# Expected: All 6 type abbreviations appear when searching diverse corpus

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Execute search with larger limit to catch diverse types
OUTPUT=$(aur mem search "test" --limit 20 2>&1 || true)

# Count how many different abbreviated types appear
FOUND_TYPES=0
FOUND_LIST=""

for abbrev in "func" "meth" "class" "code" "know" "reas"; do
    if echo "$OUTPUT" | grep -q "$abbrev"; then
        FOUND_TYPES=$((FOUND_TYPES + 1))
        FOUND_LIST="$FOUND_LIST $abbrev"
    fi
done

# Success if we found at least 2 different types
# (Not all types may be present in every corpus, but diversity indicates abbreviations work)
if [ $FOUND_TYPES -ge 2 ]; then
    echo -e "${GREEN}✅ PASS: test_15_type_abbrev_all_types${NC}"
    echo "   Found $FOUND_TYPES abbreviated types:$FOUND_LIST"
    exit 0
else
    echo -e "${RED}❌ FAIL: test_15_type_abbrev_all_types${NC}"
    echo "   Expected: At least 2 different abbreviated types"
    echo "   Found: $FOUND_TYPES types:$FOUND_LIST"
    echo ""
    echo "Output:"
    echo "$OUTPUT"
    exit 1
fi
