#!/bin/bash
# Local CI equivalent - runs all checks that GitHub CI runs
# This gives you the same signal as CI without waiting 20 minutes

set -e  # Exit on error

echo "🔍 Running Local CI Checks..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# 1. Pre-commit hooks (what modifies your code)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Running pre-commit hooks (format, lint, validate)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if pre-commit run --all-files; then
    echo -e "${GREEN}✅ Pre-commit hooks passed${NC}"
else
    echo -e "${YELLOW}⚠️  Pre-commit hooks modified files or failed${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 2. Run tests (same as CI - excluding ML and real_api)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Running tests (excluding ML and real_api markers)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if pytest -m "not ml and not real_api" --cov=packages --cov-report=term --cov-report=html -v; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 3. Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Local CI Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED - Safe to push!${NC}"
    echo ""
    echo "Coverage report: htmlcov/index.html"
    exit 0
else
    echo -e "${RED}❌ $FAILURES check(s) failed${NC}"
    echo ""
    echo "Fix issues above before pushing to avoid CI failures."
    exit 1
fi
