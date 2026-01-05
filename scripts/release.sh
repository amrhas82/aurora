#!/bin/bash
# Release to PyPI
# Usage: ./scripts/release.sh [version]
# Example: ./scripts/release.sh 0.4.3

set -e

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
    CURRENT=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "Current version: $CURRENT"
    echo "Usage: ./scripts/release.sh <new-version>"
    echo "Example: ./scripts/release.sh 0.4.3"
    exit 1
fi

echo "Releasing v$VERSION..."

# Update version in pyproject.toml
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Update CLI version
sed -i "s/@click.version_option(version=\".*\"/@click.version_option(version=\"$VERSION\"/" packages/cli/src/aurora_cli/main.py

# Clean and build
rm -rf dist/ build/ src/*.egg-info
python3 -m build

# Upload
python3 -m twine upload dist/*

# Git
git add -A
git commit -m "chore: release v$VERSION"
git tag "v$VERSION"
git push origin main --tags

echo ""
echo "✓ Released v$VERSION"
echo "  https://pypi.org/project/aurora-actr/$VERSION/"
