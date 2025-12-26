#!/usr/bin/env bash
#
# Pre-Push CI/CD Validation Script
#
# Run this locally before pushing to ensure CI/CD will pass.
# This script mirrors the GitHub Actions workflow checks.
#
# Usage:
#   ./scripts/pre-push-checks.sh [--quick]
#
# Options:
#   --quick: Skip slow tests, only run linting and type-checking
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

QUICK_MODE=false
if [[ "${1:-}" == "--quick" ]]; then
    QUICK_MODE=true
fi

echo "========================================="
echo "AURORA Pre-Push CI/CD Validation"
echo "========================================="
echo ""

# Step 1: Code Formatting (ruff format)
echo -e "${YELLOW}[1/5] Checking code formatting...${NC}"
if ruff format --check . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Code formatting passed${NC}"
else
    echo -e "${RED}✗ Code formatting failed. Run: ruff format .${NC}"
    exit 1
fi
echo ""

# Step 2: Linting (ruff check)
echo -e "${YELLOW}[2/5] Running linter...${NC}"
if ruff check . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Linting passed${NC}"
else
    echo -e "${RED}✗ Linting failed. Run: ruff check . --fix${NC}"
    exit 1
fi
echo ""

# Step 3: Type Checking (mypy)
echo -e "${YELLOW}[3/5] Running type checker...${NC}"
if make type-check > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Type checking passed${NC}"
else
    echo -e "${RED}✗ Type checking failed. Run: make type-check${NC}"
    exit 1
fi
echo ""

if [[ "$QUICK_MODE" == true ]]; then
    echo -e "${GREEN}✓ Quick checks passed! (skipped tests)${NC}"
    echo ""
    echo "To run full validation including tests, run without --quick"
    exit 0
fi

# Step 4: Unit Tests (fast)
echo -e "${YELLOW}[4/5] Running unit tests...${NC}"
if python3 -m pytest tests/unit/ -m "not ml" --tb=line -q > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed. Run: pytest tests/unit/ -m 'not ml' -v${NC}"
    exit 1
fi
echo ""

# Step 5: Integration Tests (slower)
echo -e "${YELLOW}[5/5] Running integration tests...${NC}"
if python3 -m pytest tests/integration/ -m "not ml" --tb=line -q > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed. Run: pytest tests/integration/ -m 'not ml' -v${NC}"
    exit 1
fi
echo ""

# Summary
echo "========================================="
echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
echo "========================================="
echo ""
echo "Your code is ready to push."
echo ""
echo "Tip: Add this to your pre-push git hook:"
echo "  ln -sf ../../scripts/pre-push-checks.sh .git/hooks/pre-push"
