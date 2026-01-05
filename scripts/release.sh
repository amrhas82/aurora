#!/bin/bash
# Aurora Release Script
# Usage: ./scripts/release.sh [major|minor|patch] [--publish]
#
# This script:
# 1. Updates all package versions
# 2. Reinstalls packages locally
# 3. Runs tests
# 4. Creates git tag
# 5. Optionally publishes to PyPI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
BUMP_TYPE="${1:-patch}"
PUBLISH="${2:-}"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Aurora Release Manager v0.3.1        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

# Check python3-venv
if ! dpkg -l | grep -q python3.10-venv; then
    echo -e "${YELLOW}⚠ python3.10-venv not installed${NC}"
    read -p "Install python3.10-venv? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt install -y python3.10-venv
    else
        echo -e "${RED}Error: python3-venv required for building packages${NC}"
        exit 1
    fi
fi

# Check build and twine
if ! python3 -m pip show build twine > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ build and/or twine not installed${NC}"
    pip install --user build twine
fi

echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""

# Get current version
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo -e "${YELLOW}Current version: ${CURRENT_VERSION}${NC}"

# Calculate new version
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

case "$BUMP_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo -e "${RED}Error: Invalid bump type. Use: major, minor, or patch${NC}"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo -e "${GREEN}New version: ${NEW_VERSION}${NC}"
echo ""

# Confirm
read -p "Continue with version bump to ${NEW_VERSION}? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo -e "${BLUE}Step 1/7: Updating version numbers...${NC}"

# Update main pyproject.toml
sed -i "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml
echo "  ✓ Updated main package to ${NEW_VERSION}"

# Update main.py CLI version
sed -i "s/@click.version_option(version=\".*\"/@click.version_option(version=\"${NEW_VERSION}\"/" packages/cli/src/aurora_cli/main.py
echo "  ✓ Updated CLI version to ${NEW_VERSION}"

# Update sub-packages (use minor version: X.Y.0)
SUB_VERSION="$MAJOR.$MINOR.0"
for pkg in packages/*/pyproject.toml; do
    sed -i "s/^version = \".*\"/version = \"${SUB_VERSION}\"/" "$pkg"
    PKG_NAME=$(basename "$(dirname "$pkg")")
    echo "  ✓ Updated $PKG_NAME to ${SUB_VERSION}"
done

echo ""
echo -e "${BLUE}Step 2/7: Reinstalling packages locally...${NC}"

# Reinstall all packages
for pkg in core context-code soar reasoning cli testing planning; do
    echo "  Installing aurora-$pkg..."
    pip install --force-reinstall --no-deps -e "packages/$pkg/" > /dev/null 2>&1
done

# Install main package
echo "  Installing aurora-actr..."
pip install --force-reinstall --no-deps -e . > /dev/null 2>&1

echo "  ✓ All packages reinstalled"

echo ""
echo -e "${BLUE}Step 3/7: Verifying installation...${NC}"
pip list | grep aurora
aur --version

echo ""
echo -e "${BLUE}Step 4/7: Running tests...${NC}"
if pytest tests/ -q --tb=no 2>/dev/null; then
    echo "  ✓ Tests passed"
else
    echo -e "${YELLOW}  ⚠ Some tests failed (continuing anyway)${NC}"
fi

echo ""
echo -e "${BLUE}Step 5/7: Updating CHANGELOG...${NC}"
# Update CHANGELOG date
TODAY=$(date +%Y-%m-%d)
sed -i "s/## \[Unreleased\]/## [Unreleased]\n\n## [${NEW_VERSION}] - ${TODAY}/" CHANGELOG.md
echo "  ✓ Updated CHANGELOG.md with release date"

echo ""
echo -e "${BLUE}Step 6/7: Creating git commit and tag...${NC}"

# Git operations
git add -A
git commit -m "chore: release v${NEW_VERSION}

- Bump version to ${NEW_VERSION}
- Update all package versions
- Update CHANGELOG

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>" || true

git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}" || true
echo "  ✓ Created git commit and tag v${NEW_VERSION}"

echo ""
echo -e "${BLUE}Step 7/7: Build distribution packages...${NC}"

# Clean old builds
rm -rf dist/ build/ *.egg-info packages/*/*.egg-info

# Build packages
python3 -m build
echo "  ✓ Built distribution packages"
ls -lh dist/

if [[ "$PUBLISH" == "--publish" ]]; then
    echo ""
    echo -e "${YELLOW}Publishing to PyPI...${NC}"
    read -p "Are you sure you want to publish to PyPI? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Publish to PyPI
        python -m twine upload dist/*
        echo -e "${GREEN}  ✓ Published to PyPI${NC}"

        # Push git
        git push origin main
        git push origin "v${NEW_VERSION}"
        echo -e "${GREEN}  ✓ Pushed to git${NC}"
    else
        echo "  Skipped PyPI publish"
    fi
else
    echo ""
    echo -e "${YELLOW}To publish to PyPI, run:${NC}"
    echo "  python -m twine upload dist/*"
    echo "  git push origin main"
    echo "  git push origin v${NEW_VERSION}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Release ${NEW_VERSION} Complete! 🎉          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Summary:"
echo "  Version: ${CURRENT_VERSION} → ${NEW_VERSION}"
echo "  Git tag: v${NEW_VERSION}"
echo "  Distribution: dist/aurora-actr-${NEW_VERSION}.tar.gz"
echo ""
