#!/bin/bash
# Bump version in all required files
# Usage: ./scripts/bump-version.sh <new-version>
# Example: ./scripts/bump-version.sh 0.5.1

set -e

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
    CURRENT=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "Current version: $CURRENT"
    echo ""
    echo "Usage: ./scripts/bump-version.sh <new-version>"
    echo "Example: ./scripts/bump-version.sh 0.5.1"
    exit 1
fi

echo "Bumping version to $VERSION..."

# Update version in pyproject.toml
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
echo "✓ Updated pyproject.toml"

# Update CLI version in main.py
sed -i "s/@click.version_option(version=\".*\"/@click.version_option(version=\"$VERSION\"/" packages/cli/src/aurora_cli/main.py
echo "✓ Updated packages/cli/src/aurora_cli/main.py"

echo ""
echo "Version bumped to $VERSION"
echo ""
echo "Next steps:"
echo "  1. Run ./install.sh to test locally"
echo "  2. Commit: git commit -am 'chore: bump version to $VERSION'"
echo "  3. Release: ./scripts/release.sh $VERSION"
