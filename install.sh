#!/bin/bash
# Local development install
# Usage: ./install.sh [version]
# Examples:
#   ./install.sh           # Install current version from source (editable)
#   ./install.sh 0.5.1     # Bump to 0.5.1 and install

set -e

VERSION="${1:-}"

# If version provided, bump it first
if [ -n "$VERSION" ]; then
    echo "Bumping version to $VERSION..."

    # Update version in pyproject.toml
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

    # Update CLI version in main.py
    sed -i "s/@click.version_option(version=\".*\"/@click.version_option(version=\"$VERSION\"/" packages/cli/src/aurora_cli/main.py

    echo "✓ Version bumped to $VERSION"
    echo ""
fi

# Clean stale metadata (prevents permission/timestamp errors)
rm -rf src/*.egg-info build/ 2>/dev/null || true

echo "Installing aurora-actr..."

# Try editable install first, fallback to wheel if pip is old
if pip install -e . 2>/dev/null; then
    echo "✓ Installed (editable mode)"
else
    echo "Editable install failed (old pip?), building wheel..."
    python3 -m build -w -q
    pip install dist/*.whl --force-reinstall
    rm -rf dist/ build/
    echo "✓ Installed (wheel mode)"
fi

# Verify installation
echo ""
echo "Installed:"
pip show aurora-actr | grep -E "^(Version|Location):"
echo ""
echo "CLI:"
aur --version
