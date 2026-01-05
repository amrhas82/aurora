#!/bin/bash
# Local development install
# Usage: ./install.sh

set -e

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

echo "  $(pip show aurora-actr | grep Version)"
echo "  CLI: $(which aur)"
