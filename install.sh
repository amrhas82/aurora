#!/bin/bash
# Aurora installation script - installs all packages in editable mode

set -e  # Exit on error

echo "Installing Aurora packages..."
echo ""

# Uninstall all packages first to clear metadata cache
echo "Cleaning old installations..."
pip uninstall -y aurora-actr aurora-cli aurora-context-code aurora-core aurora-reasoning aurora-soar aurora-testing aurora-planning 2>/dev/null || true

# Remove stale metadata from source directories
find packages/ -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove stale metadata from site-packages
rm -rf ~/.local/lib/python*/site-packages/aurora*.dist-info 2>/dev/null || true
rm -rf ~/.local/lib/python*/site-packages/*aurora*.pth 2>/dev/null || true
rm -rf ~/.local/lib/python*/site-packages/*.egg-link 2>/dev/null || true

echo ""
echo "Installing sub-packages..."

# Install all sub-packages
for pkg in core context-code soar reasoning cli testing planning; do
    echo "  Installing aurora-$pkg..."
    pip install -e "packages/$pkg/" > /dev/null 2>&1
done

# Install main package
echo ""
echo "Installing main package..."
echo "  Installing aurora-actr..."
pip install -e . > /dev/null 2>&1

echo ""
echo "✓ Installation complete!"
echo ""
echo "Installed packages:"
pip list | grep aurora | sort
echo ""
echo "CLI version:"
aur --version
